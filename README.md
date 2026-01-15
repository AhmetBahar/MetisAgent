
# OS/Aracı

OS/Aracı, Flask tabanlı bir Python uygulamasıdır. İşletim sistemi komutlarını çalıştırmak, sistem bilgilerini almak, dosya yönetimi yapmak, ağ bağlantılarını test etmek ve daha fazlası için API desteği sağlar.

## **Kurulum**

1. **Gerekli Bağımlılıkları Yükleyin**
   ```bash
   pip install -r requirements.txt
   ```

2. **Flask Sunucusunu Çalıştırın**
   ```bash
   python app.py
   ```

3. **Sunucu Çalıştırma**
   Varsayılan olarak uygulama `http://localhost:5000` adresinde çalışır.

---

## **API Route'ları**

### **1. Dosya Yönetimi**

#### Dosya Listeleme
- **Endpoint:** `GET /file/list`
- **Parametreler:**
  - `path` (opsiyonel): Listelenecek dizinin yolu.
- **CURL:**
  ```bash
  curl -X GET "http://localhost:5000/file/list?path=/home/user"
  ```

#### Klasör Oluşturma
- **Endpoint:** `POST /file/create_folder`
- **JSON Gövdesi:**
  ```json
  {
      "path": "/home/user/new_folder"
  }
  ```

#### Klasör Silme
- **Endpoint:** `DELETE /file/delete_folder`
- **JSON Gövdesi:**
  ```json
  {
      "path": "/home/user/new_folder"
  }
  ```

---

### **2. Sistem Bilgisi**

#### Sistem Kaynakları
- **Endpoint:** `GET /system/resources`
- **CURL:**
  ```bash
  curl -X GET http://localhost:5000/system/resources
  ```

---

### **3. Kullanıcı Yönetimi**

#### Kullanıcı Ekleme
- **Endpoint:** `POST /user/create`
- **JSON Gövdesi:**
  ```json
  {
      "username": "testuser",
      "password": "securepassword"
  }
  ```

#### Kullanıcı Silme
- **Endpoint:** `DELETE /user/delete`
- **JSON Gövdesi:**
  ```json
  {
      "username": "testuser"
  }
  ```

---

### **4. Ağ Yönetimi**

#### Ping Testi
- **Endpoint:** `GET /network/ping`
- **Parametreler:**
  - `host`: Ping atılacak hedef (varsayılan: `google.com`).
- **CURL:**
  ```bash
  curl -X GET "http://localhost:5000/network/ping?host=8.8.8.8"
  ```

---

### **5. Görev Zamanlayıcı**

#### Yinelenen Görev Zamanlama
- **Endpoint:** `POST /schedule_recurring`
- **JSON Gövdesi:**
  ```json
  {
      "command": "python /path/to/script.py",
      "schedule_type": "daily",
      "time": "14:30"
  }
  ```

---

### **6. Arşiv Yönetimi**

#### Dosya/Klasör Sıkıştırma
- **Endpoint:** `POST /compress`
- **JSON Gövdesi:**
  ```json
  {
      "source": "./example_folder",
      "destination": "./example_archive.zip"
  }
  ```

---

## **Lisans**
Bu proje MIT Lisansı altında sunulmaktadır.
