# Google OAuth2 Setup Guide - MetisAgent2

## Problem: Error 401: invalid_client

Google Console'da OAuth2 client bulunamıyor veya yanlış yapılandırılmış.

## Çözüm Adımları:

### 1. Google Cloud Console'a Git
- https://console.cloud.google.com/
- Proje seç veya yeni proje oluştur

### 2. Gmail API'yi Etkinleştir
- **APIs & Services** > **Enable APIs and Services**
- "Gmail API" ara ve etkinleştir

### 3. OAuth Consent Screen Ayarla
- **APIs & Services** > **OAuth consent screen**
- **External** seç (test için)
- **App name**: MetisAgent2
- **User support email**: ahmetbahar.minor@gmail.com
- **Developer contact**: ahmetbahar.minor@gmail.com
- **Scopes**: 
  - `https://www.googleapis.com/auth/gmail.readonly`
  - `https://www.googleapis.com/auth/gmail.send`
  - `https://www.googleapis.com/auth/userinfo.email`
  - `https://www.googleapis.com/auth/userinfo.profile`

### 4. OAuth2 Client ID Oluştur
- **APIs & Services** > **Credentials** > **Create Credentials** > **OAuth client ID**
- **Application type**: Web application
- **Name**: MetisAgent2-OAuth
- **Authorized redirect URIs**:
  ```
  http://localhost:5001/oauth2/google/callback
  http://127.0.0.1:5001/oauth2/google/callback
  ```

### 5. Test Users Ekle
- **OAuth consent screen** > **Test users**
- **Add Users**: `ahmetbahar.minor@gmail.com`

### 6. Credentials'i Kopyala
```bash
# Environment variables olarak ekle:
export GOOGLE_CLIENT_ID="yeni-client-id"
export GOOGLE_CLIENT_SECRET="yeni-client-secret"
```

### 7. Backend'i Yeniden Başlat
```bash
python app.py
```

## Test Etme:
1. Frontend: `npm start` (MetisAgent2-Frontend dizininde)
2. UserSettings > Gmail Authorization > "Gmail'i Bağla"
3. Google OAuth penceresi açılmalı
4. ahmetbahar.minor@gmail.com ile authorize et

## Mevcut Client Bilgileri:
- **Client ID**: [GOOGLE_CLIENT_ID - .env dosyasından veya SQLite'dan alınır]
- **Client Secret**: [GOOGLE_CLIENT_SECRET - .env dosyasından veya SQLite'dan alınır]

## Troubleshooting:
- **invalid_client**: Client ID yanlış veya silinmiş
- **redirect_uri_mismatch**: Redirect URI Console'da tanımlı değil
- **access_denied**: User authorization'ı reddetti
- **unauthorized_client**: Client bu grant type için yetkili değil