# 📝 ConnectInno Notes API

Basit bir **Flask + Firebase Firestore** tabanlı backend servisi.  
Kullanıcılar **Firebase Auth** ile kimlik doğrulaması yapar ve sadece kendi görevlerini (tasks) yönetebilir.

---

## 🚀 Özellikler

- Firebase Authentication (Email/Password)
- Kullanıcı bazlı görev yönetimi (`users/{uid}/tasks`)
- CRUD işlemleri (Create, Read, Update, Delete)
- Pin (sabitlenmiş görev) desteği
- Firestore bağlantı kontrolü (`/healthz`)
- JSON formatında hatalar ve yanıtlar

---

## 🧩 Gereksinimler

- Python 3.9+
- Firebase projesi (Firestore aktif)
- `service_account.json` (Firebase Admin SDK)
- Ortam değişkenleri (.env dosyası)

---

## ⚙️ Kurulum

1. **Projeyi klonla veya indir:**
   ```bash
   git clone https://github.com/kullanici/notes-api.git
   cd notes-api
   ```

2. **Sanal ortam oluştur ve etkinleştir:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # macOS / Linux
   # veya
   venv\Scripts\activate     # Windows
   ```

3. **Gerekli paketleri yükle:**
   ```bash
   pip install -r requirements.txt
   ```

4. **.env dosyasını oluştur:**
   ```
   GOOGLE_APPLICATION_CREDENTIALS=/ABSOLUTE/path/to/service_account.json
   FIREBASE_PROJECT_ID=connectinnonotes-xxxx
   FLASK_REQUIRE_AUTH=true
   ```

5. **Uygulamayı başlat:**
   ```bash
   python app.py
   ```
   Tarayıcıdan veya Postman/curl ile eriş:
   ```
   http://127.0.0.1:8000
   ```

---

## 🔐 Kimlik Doğrulama

Tüm endpoint’ler `Authorization: Bearer <Firebase_ID_Token>` header’ı ister.  
Token, Flutter veya başka bir istemciden `FirebaseAuth.instance.currentUser!.getIdToken()` ile alınabilir.

---

## 🔗 API Endpointleri

| HTTP | Endpoint | Açıklama |
|------|-----------|----------|
| `POST` | `/tasks` | Yeni görev oluşturur |
| `GET` | `/tasks` | Tüm görevleri listeler |
| `GET` | `/tasks/<id>` | Tek görevi getirir |
| `PUT` | `/tasks/<id>` | Görevi günceller |
| `PATCH` | `/tasks/<id>/toggle-pin` | Pin durumunu değiştirir |
| `DELETE` | `/tasks/<id>` | Görevi siler |
| `GET` | `/healthz` | Servis durumunu kontrol eder |
| `GET` | `/whoami` | Mevcut kullanıcının UID’sini döner |

---

## 🧪 Test (örnek `curl` komutu)

```bash
curl -X POST http://127.0.0.1:8000/tasks   -H "Content-Type: application/json"   -H "Authorization: Bearer <FIREBASE_ID_TOKEN>"   -d '{"task_name": "Yeni görev", "task_comment": "Test", "is_pinned": 0}'
```

---

## 🧰 Proje Yapısı

```
notes-api/
├── app.py                  # Flask uygulaması
├── requirements.txt        # Bağımlılıklar
├── .env                    # Ortam değişkenleri
└── README.md               # Bu dosya
```

---

## 🧑‍💻 Geliştirici Notları

- `FLASK_REQUIRE_AUTH=false` yaparsan, auth kontrolü devre dışı kalır (test amaçlı).  
- Firestore’da veriler şu yapıda tutulur:
  ```
  users/{uid}/tasks/{taskId}
  meta/counter_{uid}
  ```
- Her kullanıcı kendi `uid`’ine ait görevleri görebilir.

---

## 📄 Lisans

MIT License — Ömer Sarı © 2025
