# Gmail API Kullanım Talimatları

## Gmail Mesaj Subject Bilgisini Almak İçin:

1. **Önce mesaj listesini al:**
   ```
   GET /oauth2/google/gmail/messages?user_id=USER_ID&max_results=1
   ```

2. **Mesaj ID'sini al ve detayları çek:**
   ```
   GET /oauth2/google/gmail/messages/{MESSAGE_ID}?user_id=USER_ID
   ```

3. **Subject bilgisini bul:**
   ```
   message.payload.headers[] dizisinde name="Subject" olan öğenin value değeri
   ```

## Örnek İşlem Akışı:

1. Gmail mesaj listesi API'sini çağır
2. İlk mesajın ID'sini al  
3. O mesajın detay API'sini çağır
4. Headers dizisinde Subject'i bul
5. Subject değerini kullanıcıya ver

## Önemli Notlar:

- Her zaman USER_ID olarak `ahmetbahar.minor@gmail.com` kullan
- Mesaj detaylarını almadan subject bilgisini alamazsın
- Headers dizisinde From, Date, Subject gibi bilgiler var
- Subject bulunamazsa "Subject bulunamadı" de

## API Endpoints:

- Liste: `/oauth2/google/gmail/messages`
- Detay: `/oauth2/google/gmail/messages/{id}`
- Drive: `/oauth2/google/drive/files`  
- Calendar: `/oauth2/google/calendar/events`