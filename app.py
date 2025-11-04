# app.py
import os
from datetime import datetime
from typing import Dict, Any

from flask import Flask, jsonify, request, abort
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, auth
from google.cloud import firestore
from google.api_core.exceptions import NotFound as GcpNotFound

# ---------------- ENV & Firebase init ----------------
load_dotenv()

def _log(msg: str):
    print(f"[BOOT] {msg}")

cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
project_id = os.getenv("FIREBASE_PROJECT_ID")

try:
    if not firebase_admin._apps:
        if cred_path:
            if not os.path.exists(cred_path):
                raise FileNotFoundError(
                    f"GOOGLE_APPLICATION_CREDENTIALS yolu bulunamadı: {cred_path}"
                )
            _log(f"Firebase initialize (service account): {cred_path}")
            firebase_admin.initialize_app(credentials.Certificate(cred_path))
        else:
            _log("Firebase initialize (Application Default Credentials)")
            firebase_admin.initialize_app()
except Exception as e:
    _log(f"Firebase init HATASI: {e}")
    raise

try:
    _log(f"Firestore client init. project={project_id or '(auto)'}")
    db = firestore.Client(project=project_id)
except Exception as e:
    _log(f"Firestore client HATASI: {e}")
    raise

app = Flask(__name__)
REQUIRE_AUTH = os.getenv("FLASK_REQUIRE_AUTH", "true").lower() == "true"

# ---------------- Helpers ----------------
def now_iso() -> str:
    return datetime.utcnow().isoformat()

def user_tasks_col(uid: str):
    return db.collection("users").document(uid).collection("tasks")

def task_doc_ref(uid: str, task_id: int):
    return user_tasks_col(uid).document(str(task_id))

def require_firebase_user() -> Dict[str, Any]:
    if not REQUIRE_AUTH:
        return {"uid": "dev-local"}  # geliştirme için serbest bırakmak istersen
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        abort(401, description="Missing Authorization header")
    try:
        scheme, token = auth_header.split(" ", 1)
        if scheme.lower() != "bearer":
            abort(401, description="Invalid auth scheme (expect Bearer)")
        decoded = auth.verify_id_token(token)
        uid = decoded.get("uid") or decoded.get("user_id")
        if not uid:
            abort(401, description="Token decode edildi ama UID yok")
        return {"uid": uid, "decoded": decoded}
    except Exception as e:
        abort(401, description=f"Invalid or expired Firebase ID token: {e}")

def get_next_task_id(uid: str) -> int:
    counters_doc = db.collection("meta").document(f"counter_{uid}")
    snap = counters_doc.get()
    current = 0
    if snap.exists:
        current = int((snap.to_dict() or {}).get("tasks", 0))
    new_value = current + 1
    counters_doc.set({"tasks": new_value}, merge=True)
    return new_value

# ---------------- Error handlers (JSON) ----------------
@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(404)
@app.errorhandler(500)
def json_error(err):
    code = getattr(err, "code", 500)
    msg = getattr(err, "description", str(err))
    return jsonify({"error": msg, "status": code}), code

# ---------------- Health check ----------------
@app.route("/healthz", methods=["GET"])
def healthz():
    info: Dict[str, Any] = {
        "require_auth": REQUIRE_AUTH,
        "project_id": project_id,
        "has_service_account": bool(cred_path),
    }
    try:
        _ = db.collections()  # basit erişim testi
        info["firestore_ok"] = True
    except Exception as e:
        info["firestore_ok"] = False
        info["firestore_error"] = str(e)
    return jsonify(info)

# ---------------- CRUD ----------------
@app.route("/tasks", methods=["POST"])
def create_task():
    user = require_firebase_user()
    uid = user["uid"]

    body = request.get_json(silent=True) or {}
    task_name = body.get("task_name")
    if not task_name:
        abort(400, description="task_name is required")

    new_id = get_next_task_id(uid)
    data = {
        "id": new_id,
        "task_name": task_name,
        "task_comment": body.get("task_comment"),
        "created_date": now_iso(),
        "edit_date": None,
        "is_pinned": int(body.get("is_pinned", 0)),
    }
    try:
        user_tasks_col(uid).document(str(new_id)).set(data)
    except GcpNotFound as nf:
        abort(500, description=f"Firestore NotFound: {nf}")
    except Exception as e:
        abort(500, description=f"Firestore write error: {e}")

    return jsonify(data), 201

@app.route("/tasks", methods=["GET"])
def list_tasks():
    user = require_firebase_user()
    uid = user["uid"]

    try:
        docs = user_tasks_col(uid).stream()
        items = [d.to_dict() for d in docs if d.exists]
    except GcpNotFound as nf:
        abort(500, description=f"Firestore NotFound: {nf}")
    except Exception as e:
        abort(500, description=f"Firestore read error: {e}")

    items.sort(
        key=lambda x: (
            int(x.get("is_pinned", 0)),
            x.get("created_date") or "",
            int(x.get("id", 0)),
        ),
        reverse=True,
    )
    limit = int(request.args.get("limit", 200))
    return jsonify(items[:limit])

@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id: int):
    user = require_firebase_user()
    uid = user["uid"]

    doc = task_doc_ref(uid, task_id).get()
    if not doc.exists:
        abort(404, description="Task not found")
    return jsonify(doc.to_dict() or {})

@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id: int):
    user = require_firebase_user()
    uid = user["uid"]

    ref = task_doc_ref(uid, task_id)
    snap = ref.get()
    if not snap.exists:
        abort(404, description="Task not found")

    body = request.get_json(silent=True) or {}
    update_data: Dict[str, Any] = {}
    if "task_name" in body:
        if not body["task_name"]:
            abort(400, description="task_name cannot be empty")
        update_data["task_name"] = body["task_name"]
    if "task_comment" in body:
        update_data["task_comment"] = body["task_comment"]
    if "is_pinned" in body:
        update_data["is_pinned"] = int(body["is_pinned"])
    update_data["edit_date"] = now_iso()

    try:
        if update_data:
            ref.update(update_data)
    except Exception as e:
        abort(500, description=f"Firestore update error: {e}")

    return jsonify(ref.get().to_dict() or {})

@app.route("/tasks/<int:task_id>/toggle-pin", methods=["PATCH"])
def toggle_pin(task_id: int):
    user = require_firebase_user()
    uid = user["uid"]

    ref = task_doc_ref(uid, task_id)
    snap = ref.get()
    if not snap.exists:
        abort(404, description="Task not found")

    data = snap.to_dict() or {}
    current = int(data.get("is_pinned", 0))
    new_value = 0 if current == 1 else 1

    try:
        ref.update({"is_pinned": new_value, "edit_date": now_iso()})
    except Exception as e:
        abort(500, description=f"Firestore update error: {e}")

    return jsonify(ref.get().to_dict() or {})

@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id: int):
    user = require_firebase_user()
    uid = user["uid"]

    ref = task_doc_ref(uid, task_id)
    if not ref.get().exists:
        abort(404, description="Task not found")
    try:
        ref.delete()
    except Exception as e:
        abort(500, description=f"Firestore delete error: {e}")
    return ("", 204)

# ---------------- Main ----------------
if __name__ == "__main__":
    # Gerekirse portu değiştir: port=8080
    app.run(host="0.0.0.0", port=8000, debug=True)
