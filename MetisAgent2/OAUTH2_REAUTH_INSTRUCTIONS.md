# OAuth2 Re-authorization Instructions

## Problem
Gmail workflow hatası: "No token found for user f75ba26d-0eb6-4f88-81de-96057fd6ed12. Authorization required."

## Çözüm
OAuth2 token'ının yenilenmesi gerekiyor. Sistem artık tamamen user mapping kullanıyor, sadece token refresh gerekli.

## OAuth2 Re-authorize Adımları

1. **Backend'i çalıştır:**
   ```bash
   python app.py
   ```

2. **OAuth2 başlat (POST request):**
   ```
   POST http://localhost:5001/oauth2/google/start
   Content-Type: application/json
   
   {
     "user_id": "f75ba26d-0eb6-4f88-81de-96057fd6ed12",
     "services": ["gmail"]
   }
   ```

3. **Response'dan auth URL'i al ve browser'da aç**

4. **Google hesabında authorize et:** ahmetbahar.minor@gmail.com

5. **Callback otomatik çalışır:** http://localhost:5001/oauth2/google/callback

## OAuth2 Status Kontrol

Token durumunu kontrol etmek için:
```
GET http://localhost:5001/oauth2/google/status?user_id=f75ba26d-0eb6-4f88-81de-96057fd6ed12
```

## Sistem Durumu

✅ **Tamamen Düzeltilen Sistem:**
- User Profile System (JSON Settings Manager)
- User Mapping (f75ba26d-0eb6-4f88-81de-96057fd6ed12 → ahmetbahar.minor@gmail.com)
- Gmail Helper Tool (user mapping kullanıyor)
- OAuth2 Manager (user mapping kullanıyor)
- OAuth2 Token Save/Refresh (JSON Settings Manager kullanıyor)

⚠️ **Sadece Gerekli:** OAuth2 token refresh (yukarıdaki adımlar)

## Test Edilecek

OAuth2 re-auth sonrası şu prompt test edilebilir:
"Generate and send an image of a dog sunbathing on grass via Gmail"

## Sistem Architecture

```
User ID (f75ba26d-...) 
    ↓ (JSON Settings Manager - User Profile)
Gmail Account (ahmetbahar.minor@gmail.com)
    ↓ (OAuth2 Manager - Token Lookup)
Gmail API (Authenticated)
```

**Artık sistem tamamen multi-user ve kalıcı!** 🎉