# Proje Devamlılık Dokümanı
## Proje Genel Bilgileri

**Proje Adı:** Metis Agent  
**Başlangıç Tarihi:** (Belirtilmemiş)  
**Amaç ve Kapsam:** İşletim sistemi fonksiyonlarına erişim sağlayan, Flask tabanlı bir araç setinin geliştirilmesi. Bu araç, dosya yönetimi, kullanıcı yönetimi, ağ yönetimi, zamanlayıcı ve arşiv yönetimi gibi çeşitli sistem operasyonlarını API üzerinden erişilebilir hale getirmektedir. LLM entegrasyonu ile bu operasyonlar doğal dil komutlarıyla otomatize edilebilmektedir.  
**Kullanıcı/İstemci:** Sistem yöneticileri, geliştiriciler ve otomasyon araçları için tasarlanmıştır.

## Teknik Altyapı

**Kullanılan Teknolojiler:** RESTful API, MCP (Model-Controller-Protocol) mimari yapısı, Progressive Web App (PWA), WebSocket, LLM Entegrasyonu  
**Programlama Dilleri:** Python, JavaScript (React)  
**Frameworkler/Kütüphaneler:**

- **Backend:**
  - Flask (Web API)
  - Flask-Sock (WebSocket desteği)
  - Requests (HTTP istekleri)
  - Psutil (Sistem kaynakları izleme)
  - Shutil (Dosya işlemleri)
  - JSON (Şablon depolama)
  - Selenium (Web scraping LLM entegrasyonu için)

- **Frontend:**
  - React (UI framework)
  - React Router (Sayfa yönlendirme)
  - Bootstrap (UI framework)
  - React Bootstrap (React için Bootstrap bileşenleri)
  - React Bootstrap Icons (İkonlar)
  - Lucide React (Modern ikonlar)
  - Monaco Editor (Kod editörü ve diff görüntüleyici)
  - Service Worker (PWA desteği)
  - React DnD (Sürükle-bırak işlevselliği)
  - WebSocket API (Streaming LLM yanıtları için)

**Veritabanı:** Şu anda kullanılmıyor  
**Mimari Yapı:** MCP (Model-Controller-Protocol) yapısı ile modüler bir tasarım. Her araç kendi blueprint'ine sahiptir ve araçlar registry üzerinden yönetilmektedir.

## Mevcut Durum

### Tamamlanan Bölümler:

**Backend:**
- Dosya Yönetimi (file_manager.py)
- Sistem Bilgisi (system_info.py)
- Kullanıcı Yönetimi (user_manager.py)
- Ağ Yönetimi (network_manager.py)
- Zamanlayıcı (scheduler.py)
- Arşiv Yönetimi (archive_manager.py)
- Komut Çalıştırıcı (command_executor.py)
- API yapısı (app.py)
- MCP Çekirdek yapısı (mcp_core/)
- Koordinasyon mekanizması (coordination/)
- MCP mimarisine dönüştürülmüş araçlar (tools/)
- In-memory editor entegrasyonu
- In-memory editor için disk kalıcılık özellikleri (save_to_disk, load_from_disk)
- In-memory editor için metin arama/değiştirme fonksiyonları
- LLM kod değişiklik şablonları için saklama ve uygulama mekanizması
- LLM entegrasyonu ve görev çalıştırma API'leri
- LLM değişiklik önizleme mekanizması (dry-run modu)
- Çapraz platform komut desteği (Windows ve Linux)
- WebSocket desteği ile LLM streaming entegrasyonu
- Çoklu LLM sağlayıcı desteği (OpenAI, Anthropic, Gemini, DeepSeek)
- Web scraping LLM entegrasyonu (ChatGPT, Claude)
- Yerel LLM entegrasyonu (Ollama, LM Studio)

**Frontend:**
- React tabanlı PWA arayüzü temel yapılandırması
- Bootstrap entegrasyonu ile modern UI tasarımı
- Daraltılabilir sidebar navigasyon
- Responsive tasarım ile mobil uyumluluk
- Dashboard bileşeni ve sistem monitör göstergeleri
- Service Worker kaydı ile PWA desteği
- File Manager bileşeni
- Editor bileşeni (Monaco Editor entegrasyonu)
- Gelişmiş Editor önizleme ve diff görünümü (LLM değişiklik onaylama)
- Chat bileşeni (LLM sohbet arayüzü)
- Settings bileşeni
- Task Runner bileşeni (LLM görev yürütme)
- API servisleri için modüler yapı
- TaskRunner için gelişmiş görev yönetim arayüzü
- Görev sürükle-bırak ile yeniden sıralama
- Görev detayı görüntüleme ve düzenleme
- Görev çalıştırma modları (sıralı, paralel, manuel)
- Görev bağımlılık yönetimi
- Log kayıt ve indirme sistemi
- Görev setlerini kaydetme ve yükleme
- LLM ayarları için konfigürasyon modalı
- WebSocket streaming ile gerçek zamanlı LLM yanıtları
- Çoklu LLM sağlayıcı desteği UI

### Devam Eden Çalışmalar:

- Uzak MCP araçları entegrasyonu
- Eksik frontend bileşenlerinin (UserManager, NetworkManager, ArchiveManager, Scheduler) tamamlanması
- LLM entegrasyonu için gelişmiş metin işleme yeteneklerinin uygulanması
- PWA özelliklerinin geliştirilmesi (çevrimdışı çalışma, bildirimler)
- Authentication/Authorization mekanizmasının eklenmesi
- ChatRunner ve Editor entegrasyonunun tamamlanması

### Son Oturum Tarihi: 03.04.2025
### Son Oturumda Ulaşılan Nokta: 
- LLM Tool tamamen yeniden tasarlandı
- Çoklu LLM sağlayıcı entegrasyonu eklendi (OpenAI, Anthropic, Gemini, DeepSeek)
- Web scraping ve yerel LLM desteği eklendi (ChatGPT, Claude, Ollama, LM Studio)
- WebSocket streaming desteği eklendi
- TaskRunner bileşeni LLM entegrasyonu ile genişletildi
- LLM ayarları için UI bileşenleri oluşturuldu

## İlerleme Günlüğü

### Oturum 1-12: (Önceki oturumlar)

### Oturum 13 (03.04.2025, 14:00-16:30):
**Belirlenen hedefler:** LLM entegrasyonunu geliştirme ve WebSocket streaming desteği ekleme
**Tamamlanan hedefler:** LLM Tool yeniden yapılandırıldı, çoklu LLM sağlayıcı desteği ve WebSocket streaming eklendi
**Yapılan işlemler:**
- LLM Tool tamamen yeniden tasarlandı
- OpenAI, Anthropic, Gemini, DeepSeek API entegrasyonları eklendi
- Web scraping ile ChatGPT ve Claude desteği eklendi
- Ollama ve LM Studio ile yerel LLM desteği eklendi
- WebSocket üzerinden streaming desteği eklendi
- Backend için WebSocket endpointleri oluşturuldu
- Frontend LLM servisi genişletildi
- TaskRunner bileşeni LLM entegrasyonu ile güncellendi
- LLM ayarları için modal bileşeni eklendi

**Önemli kod değişiklikleri (özet):**
- Yeni LLM Tool implementasyonu (`llm_tool.py`)
- WebSocket desteği için Flask-Sock entegrasyonu (`app.py`)
- LLM servislerini yöneten frontend modülü (`llmService.js`)
- TaskRunner bileşeninde LLM ayarları ve streaming desteği (`TaskRunner.js`)
- Generic LLMProvider ve spesifik sağlayıcı sınıfları
- LLM Factory pattern implementasyonu
- WebSocket streaming için client-server iletişimi

**Alınan kararlar:**
- RESTful API yerine WebSocket kullanarak streaming LLM yanıtlarını destekleme
- Tüm ana LLM sağlayıcılarını tek bir araç üzerinden entegre etme
- Web scraping yoluyla browser-based LLM'lere erişimi destekleme
- Yerel/self-hosted LLM'leri de aynı arayüzle entegre etme
- LLM sağlayıcılarını dinamik olarak yapılandırmak için UI oluşturma

**Karşılaşılan zorluklar:**
- Farklı LLM API formatlarının standardizasyonu
- Web tarayıcısında oturum açma ve web scraping güvenilirliği
- WebSocket bağlantılarının etkin yönetimi
- LLM yanıtlarının güvenli bir şekilde JSON'a dönüştürülmesi
- Streaming ve non-streaming LLM yanıtlarının tek bir arayüzle yönetilmesi
- Çoklu sağlayıcıların authentication mekanizmalarının farklılıkları

## Bekleyen Görevler

### Öncelikli Maddeler:

1. **TaskRunner ve Editor Entegrasyonu:**
   - TaskRunner'dan kod değişikliği görevleri için Editor'a yönlendirme
   - Editor'daki değişikliklerin TaskRunner'a bildirilmesi
   - Kod değişikliği görevleri için onay mekanizmasının iyileştirilmesi

2. **LLM Entegrasyonu İyileştirmeleri:**
   - Sağlayıcı bağlantı durumu izleme ve otomatik yeniden bağlanma
   - Uzun bağlam desteği için bölünmüş görev oluşturma
   - LLM başarısızlıklarını daha güçlü hata işleme ile yönetme
   - LLM sağlayıcıları için daha güvenli API anahtarı yönetimi

3. **Frontend Bileşenleri Tamamlama:**
   - UserManager bileşeni
   - NetworkManager bileşeni
   - SchedulerManager bileşeni
   - ArchiveManager bileşeni
   - LLM ayarları sayfasının genişletilmesi

4. **Güvenlik ve Yetkilendirme:**
   - Authentication sistemi eklemesi
   - Kullanıcı bazlı yetkilendirme
   - API güvenliği iyileştirmeleri
   - API anahtarlarının güvenli depolanması

5. **PWA Özellikleri Geliştirme:**
   - Çevrimdışı çalışma desteğinin geliştirilmesi
   - Bildirim sistemi
   - Otomatik güncelleme mekanizması

### Sonraki Adımlar:

- WebSocket bağlantılarının izlenmesi ve yönetimi
- LLM sistemlerine daha geniş format desteği ekleme (imajlar, dosyalar)
- Docker konteyner desteği
- CI/CD pipeline entegrasyonu
- Test kapsamının artırılması
- Dokümantasyon geliştirme
- LLM şablonlarının iyileştirilmesi
- Farklı LLM sağlayıcıları için sistem promptlarının optimizasyonu

## Çözülmesi Gereken Sorunlar:

- Web scraping güvenilirliği ve oturum sürekliliği
- LLM streaming bağlantıları için düşük gecikme süreli iletişim
- Uzak LLM bağlantılarında sona eren isteklerin yönetimi
- LLM çıktılarının standartlaştırılması ve metin değişikliklerinin güvenli şekilde uygulanması
- Şablonların sürümlenmesi ve değişiklik geçmişinin izlenmesi
- MCP araçları arasında veri paylaşımı için güvenli mekanizma
- Kompleks görevlerin yönetimi ve izlenmesi için arayüz
- Uzak MCP sunucularına güvenli erişim
- In-memory dosyaların otomatik periyodik yedeklenmesi
- PWA ve Flask backend arasında güvenli veri iletişimi
- PWA'nın farklı tarayıcılarda uyumluluğu
- TaskRunner bağımlılık kontrolünün karmaşık ağaçlarda doğru çalışması
- Görev setlerini Cloud/Backend depolama sistemine taşıma
- API anahtarlarının güvenli bir şekilde saklanması

## Alınan Kararlar

### Tasarım Tercihleri:

- Flask Blueprint'leri yerine MCP mimarisi kullanılacak
- Modüler, genişletilebilir yapı için MCPTool ve MCPRegistry sınıfları
- Karmaşık görevlerin yönetimi için MCPCoordinator kullanımı
- API tabanlı mimari
- In-memory editor için disk kalıcılık mekanizması
- LLM entegrasyonu için standardize edilmiş kod değişiklik şablonları
- Şablonların in-memory dosya sistemi içinde JSON formatında saklanması
- Frontend için PWA yaklaşımının benimsenmesi
- React ile modüler bileşen yapısı
- Bootstrap framework kullanımı
- Backend entegrasyonu için servis tabanlı API yapısı
- LLM değişiklik önizleme ve onay mekanizması
- Daraltılabilir sidebar ile ekran alanı optimizasyonu
- Responsive tasarım ile mobil uyumluluk
- TaskRunner için iki kolonlu layout (görev listesi ve detaylar)
- Sürükle-bırak görev sıralama için React DnD kullanımı
- Görev çalıştırma için üç farklı mod (sıralı, paralel, manuel)
- Log kayıtları için indirilebilir format desteği
- Görev setlerini localStorage'da saklama
- WebSocket üzerinden LLM streaming yanıtları
- Farklı LLM sağlayıcıları için tek bir arayüz
- LLM Factory pattern ile esnek sağlayıcı yönetimi
- LLM provider'lar için abstract base class ve interface
- Web scraping için headless browser otomasyonu
- Yerel LLM'ler için Ollama ve LM Studio entegrasyonu

### Uygulama Yaklaşımları:

- Merkezi registry ile araçların yönetimi
- Dinamik modül yükleme ve araç kaydetme
- Araçlar arası koordinasyon için görev yönetim sistemi
- React + MonacoEditor ile kullanıcı dostu arayüz
- Bellek içi ve disk tabanlı işlemlerin entegrasyonu
- LLM çıktıları için standartlaştırılmış metin işleme protokolleri
- Kod değişiklik şablonları için JSON temelli depolama
- PWA ile masaüstü benzeri uygulama deneyimi
- Service worker ile çevrimdışı erişim yetenekleri
- Çapraz platform desteği için işletim sistemine özel komut yapıları
- LLM değişikliklerinin dry-run modu ile simülasyonu
- Değişiklik önizleme ve diff görüntüleme için kullanıcı arayüzü
- Bootstrap kartlar ve bileşenler ile modern UI
- Lucide React ile tutarlı ikon seti
- Görevler arası bağımlılık kontrol mekanizması
- Görev yürütme stratejileri için çeşitli modlar
- Hata yönetimi için farklı stratejiler (devam, durdur, sor)
- WebSocket bağlantıları üzerinden LLM yanıtlarının streaming iletimi
- LLM yanıtlarının reaktif işlenmesi
- Factory pattern ile LLM sağlayıcılarının dinamik oluşturulması
- Soyut sınıflar ve arayüzlerle farklı LLM sağlayıcıları için tutarlı API

### Reddedilen Alternatifler:

- Doğrudan Python kütüphanesi yerine API yaklaşımı tercih edildi
- Karmaşık veritabanı yapısı yerine dosya tabanlı kayıt sistemi
- Monolitik yapı yerine modüler, servis tabanlı yaklaşım
- Tüm metin değişikliklerinin tek bir write_file fonksiyonu ile yapılması yerine, granüler metin işleme fonksiyonları
- Şablonlar için ayrı bir depolama mekanizması yerine mevcut in-memory dosya sisteminin kullanılması
- Electron veya Tauri yerine PWA yaklaşımı (kurulum gerektirmemesi ve platform bağımsızlığı nedeniyle)
- Single-page application yerine modüler bileşen mimarisi
- Doğrudan frontend'den LLM API çağrısı yerine backend üzerinden iletişim
- LLM değişikliklerinin otomatik uygulanması yerine kullanıcı onayı gerektiren yaklaşım
- Tailwind CSS yerine Bootstrap kullanımı (yapılandırma zorlukları nedeniyle)
- TaskRunner için tek kolonlu layout yerine iki kolonlu layout
- Backend tabanlı görev seti saklama yerine localStorage kullanımı (ilk aşamada)
- RESTful API üzerinden polling yerine WebSocket ile gerçek zamanlı veri iletimi
- Farklı LLM sağlayıcıları için ayrı araçlar yerine tek bir LLM aracı
- Doğrudan browser otomasyonu yerine backend üzerinden Web scraping

## Kaynaklar ve Referanslar

### Kullanılan Dokümanlar:

- Flask dokümantasyonu
- Flask-Sock dokümantasyonu
- Psutil dokümantasyonu
- React dokümantasyonu
- Bootstrap dokümantasyonu
- React Bootstrap dokümantasyonu
- Monaco Editor dokümantasyonu
- Monaco diff editor dokümantasyonu
- Service Worker dokümantasyonu
- Web App Manifest dokümantasyonu
- LLM API (OpenAI, Anthropic, Gemini, DeepSeek) dokümantasyonları
- React DnD dokümantasyonu
- Selenium WebDriver dokümantasyonu
- WebSocket API dokümantasyonu
- Ollama API dokümantasyonu
- LM Studio API dokümantasyonu

### API Referansları:

- Flask API
- WebSocket API
- React API
- React Bootstrap API
- Monaco Editor API
- Monaco Diff Editor API
- Service Worker API
- Web App Manifest API
- OpenAI API
- Anthropic API
- Google Gemini API
- DeepSeek API
- Ollama API
- React DnD API
- Subprocess ve sistem komutları

### Örnek Kodlar/Snippetler:

- mcp_core/tool.py (MCP Tool temel sınıfı)
- mcp_core/registry.py (MCP Registry yapısı)
- coordination/coordinator.py (Görev koordinasyonu)
- tools/llm_tool.py (LLM entegrasyonu ve sağlayıcılar)
- tools/in_memory_editor.py (metin işleme fonksiyonları ve şablon mekanizması)
- app.py (Ana Flask uygulaması ve WebSocket desteği)
- frontend/src/App.js (Ana uygulama düzeni)
- frontend/src/App.css (Ana uygulama stilleri)
- frontend/src/serviceWorkerRegistration.js (PWA service worker kaydı)
- frontend/public/manifest.json (PWA manifest dosyası)
- frontend/src/services/api.js (API servis modülü)
- frontend/src/services/llmService.js (LLM servis modülü)
- frontend/src/pages/Dashboard.js (Dashboard bileşeni)
- frontend/src/pages/TaskRunner.js (LLM görev yürütücü)
- frontend/src/pages/Editor.js (Editor ve diff görüntüleyici)
- backend LLM entegrasyonu ve görev yürütme API'leri
- backend WebSocket streaming API'leri
- backend metin değişiklik önizleme API'si

## Notlar

### Önemli Hatırlatmalar:

- Proje şu anda modüler MCP yapısına geçiş aşamasında
- In-memory editor disk kalıcılık özellikleri eklendi
- LLM kod değişiklik şablonları için mekanizma eklendi
- Frontend PWA temel bileşenleri tamamlandı
- Bootstrap tabanlı modern UI tasarımı eklendi
- LLM entegrasyonu backend üzerinden yapılandırıldı
- Çapraz platform destek sistemi kuruldu
- LLM değişiklik önizleme ve onay sistemi eklendi
- PWA için Service Worker kaydı etkinleştirildi
- TaskRunner bileşeni yeniden tasarlandı ve geliştirildi
- Görev yönetimi için sürükle-bırak işlevselliği eklendi
- Log kayıt ve indirme sistemi eklendi
- WebSocket ile LLM streaming desteği eklendi
- Çoklu LLM sağlayıcı desteği eklendi
- Web scraping ve yerel LLM entegrasyonu eklendi

### Dikkat Edilmesi Gerekenler:

- LLM çıktılarının güvenli şekilde işlenmesi ve uygulanması
- JSON şablon formatının tutarlılığının korunması
- Dönüştürülen araçların eski blueprint'ler ile uyumluluğunun sağlanması
- MCP yapısının API güvenliği (yetkilendirme sistemi henüz eklenmedi)
- Uzak MCP araçları için proxy mekanizmasının güvenliği
- In-memory dosyaların disk dönüşümlerinde karakter kodlaması sorunları
- PWA'nın farklı tarayıcılarda test edilmesi
- Service worker güncellemelerinin yönetilmesi
- LLM API anahtarlarının güvenliği
- İşletim sistemine özgü komutların uygun yönetimi
- Değişiklik önizleme mekanizmasında büyük dosyaların performansı
- Bootstrap ile tasarlanan UI'ın küçük ekranlarda doğru görüntülenmesi
- PWA bildirim sisteminin izin yönetimi
- TaskRunner görev bağımlılık yönetiminin doğruluğu
- Karmaşık bağımlılık ağaçlarında döngüsel bağımlılık kontrolü
- Parallel görev çalıştırmada CPU ve bellek kullanımının optimize edilmesi
- Hata durumunda uygun stratejinin belirlenmesi
- Web scraping için gerekli bağımlılıkların kurulumu (Chrome WebDriver)
- LLM streaming için WebSocket bağlantı stabilitesi
- API anahtarlarının güvenli saklanması için yöntem geliştirilmesi
- Farklı LLM sağlayıcılarının farklı hata davranışlarının yönetilmesi

### Ekstra Bilgiler:

- MCP mimarisi, modüler yapısıyla gelecekte yeni araçların kolayca eklenebilmesini sağlar
- Araçlar arası koordinasyon, karmaşık görevlerin otomatize edilmesini mümkün kılar
- React arayüzü, sistem yönetimini ve otomasyonu kolaylaştıracak
- In-memory editor için disk kalıcılık özellikleri, uzun süreli projelerde çalışmayı destekler
- LLM entegrasyonu, karmaşık metin işleme ihtiyaçlarını otomatize edebilir
- Kod değişiklik şablonları, LLM'in tutarlı şekilde kod değişiklikleri yapmasını sağlar
- PWA yaklaşımı, uygulamanın kurulum gerektirmeden masaüstü deneyimi sunmasını sağlar
- Service worker, uygulamanın çevrimdışı çalışabilmesini ve performans iyileştirmelerini destekler
- TaskRunner bileşeni, LLM aracılığıyla otomasyon görevlerini kolaylıkla yürütmeyi sağlar
- Çapraz platform desteği, aynı kodu Windows ve Linux sistemlerinde kullanmayı mümkün kılar
- Önizleme ve onay mekanizması, LLM'den gelen değişikliklerin güvenli bir şekilde uygulanmasını sağlar
- Monaco Editor'ün diff görüntüleyicisi, değişiklikleri görsel ve anlaşılır şekilde göstermeyi sağlar
- Bootstrap framework'ü, modern ve responsive bir kullanıcı arayüzü sağlar
- Daraltılabilir sidebar, sınırlı ekran alanına sahip cihazlarda daha fazla içerik görüntülemeyi sağlar
- Dashboard sistem göstergeleri, sistem kaynaklarının gerçek zamanlı takibini kolaylaştırır
- TaskRunner'daki sürükle-bırak özellikleri, görevleri kolay yeniden düzenlemeyi sağlar
- Görev bağımlılık yönetimi, karmaşık iş akışlarının otomatizasyonunu mümkün kılar
- Log sistemi, sorun giderme ve görev takibi için önemli bilgileri saklar
- WebSocket streaming, uzun yanıtların gerçek zamanlı alınmasını sağlar
- Çoklu LLM sağlayıcı desteği, farklı LLM modellerinin güçlü yanlarından faydalanmayı sağlar
- Web scraping desteği, API anahtarı olmadan da LLM'lere erişim imkanı sunar
- Yerel LLM desteği, internet bağlantısı olmadan da LLM yeteneklerinin kullanılmasını sağlar

## MCP Mimarisi Güncel Dizin Yapısı
```
MetisAgent/
├── os_araci/
│   ├── mcp_core/                 # MCP çekirdek yapısı
│   │   ├── __init__.py
│   │   ├── registry.py           # Araç kayıt sistemi
│   │   └── tool.py               # MCP araç temel sınıfı
│   ├── tools/                    # MCP araçları
│   │   ├── __init__.py
│   │   ├── file_manager.py       # Dosya yönetimi aracı
│   │   ├── in_memory_editor.py   # Bellek içi editör (disk kalıcılık desteği eklenmiş)
│   │   ├── llm_tool.py           # LLM entegrasyonu (çoklu sağlayıcı desteği eklendi)
│   │   └── ... (diğer araçlar)
│   ├── coordination/             # Koordinasyon mekanizması
│   │   ├── __init__.py
│   │   └── coordinator.py        # Görev koordinatörü
│   ├── routes/                   # Eski blueprint yapısı (geçiş sürecinde)
│   ├── llm/                      # LLM entegrasyon modülü
│   │   ├── __init__.py
│   │   ├── task_generator.py     # LLM görev üretici
│   │   └── templates.py          # Sistem promptları
├── frontend/                     # React arayüzü (PWA desteği ile)
│   ├── public/
│   │   ├── manifest.json         # PWA manifest dosyası
│   │   ├── logo192.png           # PWA ikon (192x192)
│   │   └── logo512.png           # PWA ikon (512x512)
│   ├── src/
│   │   ├── components/           # Ortak UI bileşenleri
│   │   │   ├── Layout.js
│   │   │   ├── Sidebar.js
│   │   │   └── Header.js
│   │   ├── pages/                # Sayfa bileşenleri
│   │   │   ├── Dashboard.js
│   │   │   ├── FileManager.js
│   │   │   ├── Editor.js
│   │   │   ├── Chat.js
│   │   │   ├── TaskRunner.js     # Görev yürütücü (WebSocket streaming desteği eklenmiş)
│   │   │   └── Settings.js
│   │   ├── services/             # API servis modülleri
│   │   │   ├── api.js
│   │   │   └── llmService.js     # LLM servisi (çoklu sağlayıcı ve streaming desteği)
│   │   ├── serviceWorkerRegistration.js  # Service worker kayıt
│   │   ├── service-worker.js     # Service worker yapılandırması
│   │   ├── App.js                # Ana uygulama bileşeni
│   │   ├── App.css               # Ana uygulama stilleri
│   │   └── index.js              # Uygulama giriş noktası
├── app.py                        # Ana Flask uygulaması (WebSocket desteği eklenmiş)
└── requirements.txt              # Bağımlılıklar (flask-sock, selenium, vs eklendi)
```

## Yeni API Endpointleri ve WebSocket Servisleri

### RESTful API Endpoints

| Endpoint | Metot | Açıklama |
|----------|-------|----------|
| `/api/llm_tool/generate_tasks` | POST | Metin açıklamadan görev listesi oluşturur |
| `/api/llm_tool/generate_text` | POST | LLM'den metin yanıtı oluşturur |
| `/api/llm_tool/get_models` | GET | Seçilen sağlayıcının modellerini listeler |
| `/api/llm_tool/get_providers` | GET | Desteklenen tüm LLM sağlayıcılarını listeler |
| `/api/llm_tool/check_status` | GET | LLM sağlayıcısının durumunu kontrol eder |
| `/api/llm_tool/setup_provider` | POST | LLM sağlayıcısını yapılandırır |
| `/api/llm_tool/stream_start` | POST | Streaming LLM yanıtını başlatır ve WebSocket ID verir |
| `/api/llm_tool/stream_stop` | POST | Streaming LLM yanıtını durdurur |

### WebSocket Servisleri

| WebSocket Endpoint | Açıklama |
|--------------------|----------|
| `/api/llm/stream/<ws_id>` | LLM streaming yanıtlarını almak için WebSocket bağlantısı |

### Mesaj Formatları

#### LLM Stream Mesajları

```json
// İstemciden sunucuya yapılandırma mesajı
{
  "provider_type": "openai",
  "model": "gpt-4o",
  "prompt": "Kullanıcı talebi...",
  "temperature": 0.7,
  "system_prompt": "LLM için sistem prompt..."
}

// Sunucudan istemciye içerik mesajı
{
  "type": "content",
  "content": "Mesaj parçası..."
}

// Sunucudan istemciye tamamlanma mesajı
{
  "type": "done",
  "content": "Tam içerik..."
}

// Sunucudan istemciye hata mesajı
{
  "type": "error",
  "content": "Hata açıklaması..."
}
```

## LLM Sağlayıcı Entegrasyonu

### Desteklenen LLM Sağlayıcıları

| Sağlayıcı | Tip | API Gerektiriyor | Streaming Desteği |
|-----------|-----|------------------|-------------------|
| OpenAI | API | Evet | Evet |
| Anthropic | API | Evet | Evet |
| Google Gemini | API | Evet | Evet |
| DeepSeek | API | Evet | Evet |
| ChatGPT (Web) | Web Scraping | Hayır | Hayır |
| Claude (Web) | Web Scraping | Hayır | Hayır |
| Ollama | Yerel | Hayır | Evet |
| LM Studio | Yerel | Hayır | Evet |

### LLM Sağlayıcı Mimarisi

```
LLMProvider (Abstract Base Class)
├── OpenAIProvider
├── AnthropicProvider
├── GeminiProvider
├── DeepSeekProvider
├── WebScraperLLM
└── LocalLLMProvider
```

### Sağlayıcı Oluşturma Mimarisi

```
LLMFactory
└── create_provider(provider_type, **kwargs)
```

## TaskRunner Bileşeni Güncellenen Özellikleri

### Ana Özellikler:
- LLM entegrasyonu ile görev oluşturma
- LLM yanıtları için WebSocket streaming desteği
- Çoklu LLM sağlayıcı seçimi ve yapılandırması
- LLM ayarları için modal bileşeni
- Görev çalıştırma modları (sıralı, paralel, manuel)
- Görev bağımlılık yönetimi
- Hata stratejisi belirleme (devam, durdur, sor)
- Görev setlerini kaydetme ve yükleme

### Görev Yönetimi Özellikleri:
- Sürükle-bırak ile görev sıralama
- Görev kilitleme/kilidini açma
- Görev düzenleme modalı
- Görev detay görünümü
- Görev çıktılarını görüntüleme
- Log kayıtlarını görüntüleme ve indirme

## LLM Entegrasyonu İçin Konfigürasyon Gereksinimleri

### API Tabanlı Sağlayıcılar:
- OpenAI: API anahtarı (OPENAI_API_KEY)
- Anthropic: API anahtarı (ANTHROPIC_API_KEY)
- Gemini: API anahtarı (GEMINI_API_KEY)
- DeepSeek: API anahtarı (DEEPSEEK_API_KEY)

### Web Scraping Sağlayıcılar:
- Selenium WebDriver (Chrome)
- Chrome tarayıcı
- İnternet erişimi

### Yerel LLM Sağlayıcılar:
- Ollama veya LM Studio yerel kurulumu
- Modellerin önceden indirilmiş olması

## Örnek Kullanım Senaryoları

### Sistem Durum Kontrolü:
1. TaskRunner açılır
2. LLM ayarlarından uygun sağlayıcı ve model seçilir
3. Prompt alanına "Sistem durumunu kontrol et ve rapor oluştur" yazılır
4. LLM, disk alanı, bellek ve CPU kullanımını kontrol eden görevler oluşturur
5. Görevler sıralı veya paralel olarak çalıştırılır
6. Sistem durumu hakkında rapor elde edilir

### Kod Değişikliği Otomasyonu:
1. TaskRunner açılır
2. LLM ayarlarından uygun sağlayıcı ve model seçilir
3. Prompt alanına "src/ klasöründeki tüm JavaScript dosyalarında var yerine let/const kullan" yazılır
4. LLM, dosyaları bulma, içeriği değiştirme ve test etme görevleri oluşturur
5. Değişiklik görevleri Editor üzerinden önizleme ile onaylanır
6. Görevler çalıştırılır ve dönüşüm gerçekleştirilir

### Sistem Bakım Otomasyonu:
1. TaskRunner açılır
2. LLM ayarlarından uygun sağlayıcı ve model seçilir
3. Prompt alanına "Sistem bakımı yap: güncellemeleri kur, eski logları sil, diskleri optimize et" yazılır
4. LLM, bakım görevlerini oluşturur
5. Görevler çalıştırılır ve sistem bakımı otomatize edilir