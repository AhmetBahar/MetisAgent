# Proje Devamlılık Dokümanı
## Proje Genel Bilgileri

**Proje Adı:** Metis Agent  
**Başlangıç Tarihi:** (Belirtilmemiş)  
**Amaç ve Kapsam:** İşletim sistemi fonksiyonlarına erişim sağlayan, Flask tabanlı bir araç setinin geliştirilmesi. Bu araç, dosya yönetimi, kullanıcı yönetimi, ağ yönetimi, zamanlayıcı ve arşiv yönetimi gibi çeşitli sistem operasyonlarını API üzerinden erişilebilir hale getirmektedir.  
**Kullanıcı/İstemci:** Sistem yöneticileri, geliştiriciler ve otomasyon araçları için tasarlanmıştır.

## Teknik Altyapı

**Kullanılan Teknolojiler:** RESTful API, MCP (Model-Controller-Protocol) mimari yapısı, Progressive Web App (PWA)  
**Programlama Dilleri:** Python, JavaScript (React)  
**Frameworkler/Kütüphaneler:**

- **Backend:**
  - Flask (Web API)
  - Requests (HTTP istekleri)
  - Psutil (Sistem kaynakları izleme)
  - Shutil (Dosya işlemleri)
  - JSON (Şablon depolama)
  - OpenAI API, Selenium (LLM entegrasyonu)

- **Frontend:**
  - React (UI framework)
  - React Router (Sayfa yönlendirme)
  - Bootstrap (UI framework)
  - React Bootstrap (React için Bootstrap bileşenleri)
  - React Bootstrap Icons (İkonlar)
  - Monaco Editor (Kod editörü ve diff görüntüleyici)
  - Service Worker (PWA desteği)
  - React DnD (Sürükle-bırak işlevselliği)

**Veritabanı:** Şu anda localStorage kullanılıyor, ileride backend depolama sistemine geçiş planlanıyor  
**Mimari Yapı:** MCP (Model-Controller-Protocol) yapısı ile modüler bir tasarım. Her araç kendi işleyicilerine sahiptir ve araçlar merkezi registry üzerinden yönetilmektedir.

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
- LLM entegrasyonu için çoklu sağlayıcı desteği (OpenAI, Web Scraper, Ollama, LM Studio)

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
- TaskRunner bileşeninin ana sayfa olarak yapılandırılması
- LLM sağlayıcıları için yapılandırma arayüzü

### Devam Eden Çalışmalar:

- Frontend ve backend MCP entegrasyonunun tamamlanması
- Uzak MCP araçları entegrasyonu
- Eksik frontend bileşenlerinin (UserManager, NetworkManager, ArchiveManager, Scheduler) tamamlanması
- LLM entegrasyonu için gelişmiş metin işleme yeteneklerinin uygulanması
- PWA özelliklerinin geliştirilmesi (çevrimdışı çalışma, bildirimler)
- Authentication/Authorization mekanizmasının eklenmesi
- TaskRunner ve Editor entegrasyonunun tamamlanması
- LLM Task yönetimi için WebSocket desteği eklenmesi

### Son Oturum Tarihi: 03.04.2025
### Son Oturumda Ulaşılan Nokta: 
- Flask blueprint kullanımından MCP mimarisine tam geçiş yapıldı
- LLM entegrasyonu için çoklu sağlayıcı desteği eklendi (OpenAI, Web Scraper, Ollama, LM Studio)
- MCPRegistry ve MCPTool sınıfları güncellendi
- Frontend API servisleri MCP mimarisine uygun hale getirildi
- TaskRunner arayüzüne LLM sağlayıcı seçimi ve yapılandırma arayüzü eklendi
- TaskRunner'ın başlangıç ekranı olarak ayarlanması sağlandı

## İlerleme Günlüğü

### Oturum 1-9: (Önceki oturumlar)

### Oturum 10 (01.04.2025, 23:00-00:00):
**Belirlenen hedefler:** LLM değişiklik önizleme ve onay mekanizmasının geliştirilmesi
**Tamamlanan hedefler:** Backend LLM değişiklik önizleme API'si ve frontend önizleme/onay arayüzü
**Yapılan işlemler:**
- Backend'de `/api/editor/preview-changes` endpoint'i oluşturuldu
- In-memory editor'e dry-run modu eklendi
- Frontend Editor bileşenine önizleme/onay arayüzü eklendi
- Diff görüntüleme özelliği eklendi
- API servis modülüne previewChanges metodu eklendi

**Önemli kod değişiklikleri (özet):**
- Backend'de LLM değişikliklerini simüle eden dry-run fonksiyonu
- Değişiklik önizleme için API endpoint
- Frontend'de değişiklik listesi ve diff görüntüleme paneli
- Değişiklikleri kabul/ret mekanizması
- Monaco Editor diff görüntüleyici entegrasyonu

**Alınan kararlar:**
- LLM değişikliklerinin kullanıcı onayı olmadan uygulanmaması
- Değişikliklerin görsel olarak sınıflandırılması (ekleme, silme, değiştirme)
- Orijinal ve değiştirilmiş kod arasında karşılaştırma imkanı sağlanması
- Değişiklik listesinin detaylı açıklamalarla gösterilmesi

**Karşılaşılan zorluklar:**
- Monaco Editor'ün diff görüntüleyici modunun yapılandırılması
- Değişiklik türlerinin doğru şekilde görselleştirilmesi
- Önizleme ve normal mod arasındaki geçişlerin yönetimi

### Oturum 11 (02.04.2025, 20:00-22:00):
**Belirlenen hedefler:** Frontend UI yapısının Bootstrap ile modernizasyonu ve PWA desteği
**Tamamlanan hedefler:** Bootstrap entegrasyonu, modern arayüz tasarımı, PWA yapılandırması
**Yapılan işlemler:**
- Bootstrap ve React Bootstrap kütüphaneleri entegre edildi
- React Bootstrap Icons kütüphanesi eklendi
- Daraltılabilir sidebar navigasyon tasarlandı
- Responsive tasarım ile mobil uyumluluk sağlandı
- Dashboard bileşeni sistem monitör göstergeleri ile geliştirildi
- PWA için Service Worker kaydı etkinleştirildi

**Önemli kod değişiklikleri (özet):**
- App.js yeniden tasarlandı, daraltılabilir sidebar eklendi
- Bootstrap tabanlı layout yapısı kuruldu
- Modern UI için gradyan ve gölgeler eklendi
- Dashboard bileşeni için sistem istatistik kartları eklendi
- Responsive tasarım için media query kuralları eklendi
- Service Worker kaydı için serviceWorkerRegistration.register() çağrısı etkinleştirildi

**Alınan kararlar:**
- Tailwind CSS yerine Bootstrap framework'ünün kullanılması
- PWA için Service Worker'ın etkinleştirilmesi
- Daraltılabilir sidebar ile ekran alanı optimizasyonu
- Sistem monitör göstergeleri için kartlar ve grafikler kullanımı
- Renk şeması olarak mavi-koyu mavi gradyan tema seçimi

**Karşılaşılan zorluklar:**
- Tailwind CSS yapılandırma sorunları
- Bootstrap ve Create React App entegrasyon sorunları
- Responsive tasarımın her cihazda doğru çalışmasının sağlanması
- PWA yapılandırmasının güncellenmesi

### Oturum 12 (02.04.2025, 22:00-23:30):
**Belirlenen hedefler:** TaskRunner bileşeninin yeniden tasarlanması ve geliştirilmesi
**Tamamlanan hedefler:** Gelişmiş görev yönetimi arayüzü, log sistemi, görev seti yönetimi
**Yapılan işlemler:**
- TaskRunner bileşeni tamamen yeniden tasarlandı
- Görevleri sürükle-bırak ile yeniden sıralama özelliği eklendi
- Görev düzenleme ve silme işlevleri eklendi
- Görev bağımlılık yönetim arayüzü eklendi
- Görev çalıştırma modları (sıralı, paralel, manuel) eklendi
- Log kayıt ve görüntüleme sistemi eklendi
- Görev setlerini kaydetme ve yükleme fonksiyonu eklendi

**Önemli kod değişiklikleri (özet):**
- TaskItem bileşeni eklendi (sürükle-bırak için)
- TaskEditModal bileşeni eklendi (görev düzenleme için)
- Paralel ve sıralı çalıştırma fonksiyonları güncellendi
- Bağımlılık kontrolü için canRun() fonksiyonu eklendi
- Log kayıt sistemi eklendi (addLog, downloadLog)
- Görev seti kaydetme ve yükleme fonksiyonları eklendi (saveTaskSet, loadTaskSet)
- Hata stratejisi yönetimi eklendi (handleTaskFailure)

**Alınan kararlar:**
- TaskRunner'ın kullanıcı arayüzünün iki kolonlu yapıya geçirilmesi
- Görev listesi ve detayların ayrı panellerde gösterilmesi
- Sürükle-bırak için React DnD kütüphanesinin kullanılması
- Görev işleme sürecinin adım adım izlenebilir hale getirilmesi
- Log kayıtlarının hem görüntülenebilir hem de indirilebilir olması
- Görev setlerinin localStorage'da saklanması

**Karşılaşılan zorluklar:**
- React DnD entegrasyon sorunları
- Görev bağımlılıklarının doğru yönetilmesi
- Paralel görev yürütmede senkronizasyon sorunları
- Kod değişikliği görevlerinin simülasyonu

### Oturum 13 (03.04.2025, 20:00-22:30):
**Belirlenen hedefler:** LLM entegrasyonu ve MCP mimarisine tam geçiş
**Tamamlanan hedefler:** LLM entegrasyonu için çoklu sağlayıcı desteği, MCP mimarisi entegrasyonu
**Yapılan işlemler:**
- LLM Tool sınıfı oluşturuldu (MCP mimarisi ile uyumlu)
- OpenAI, Web Scraper, Ollama ve LM Studio için LLM sağlayıcıları eklendi
- MCPRegistry ve MCPTool sınıfları güncellendi
- Flask uygulaması MCP mimarisine uyarlandı
- Frontend API servisleri MCP yapısı ile çalışacak şekilde güncellendi
- TaskRunner bileşeninde LLM sağlayıcı seçimi ve ayarları için arayüz eklendi
- React Router konfigürasyonu güncellenerek TaskRunner ana sayfa yapıldı

**Önemli kod değişiklikleri (özet):**
- LLMProvider temel sınıfı ve alt sınıfları (OpenAIProvider, WebScraperLLM, LocalLLMProvider)
- LLMFactory factory pattern uygulaması
- LLMTool MCP aracı uygulaması 
- MCPRegistry merkezi araç yönetim sistemi
- MCPTool temel araç sınıfı
- API servis sınıfları için MCP uyumlu wrapper
- TaskRunner'a LLM sağlayıcı seçim ve yapılandırma modülü

**Alınan kararlar:**
- Blueprint yaklaşımı yerine MCP mimarisinin benimsenmesi
- LLM sağlayıcıları için factory pattern kullanımı
- Farklı LLM sağlayıcıları için ortak arayüz tasarımı
- Merkezi registry mekanizması ile araç yönetimi
- Yerel LLM seçenekleri için Ollama ve LM Studio desteği
- Frontend API servis katmanında MCP yapısı için adapter pattern

**Karşılaşılan zorluklar:**
- Flask blueprint'lerinden MCP mimarisine geçiş
- Farklı LLM sağlayıcılarının ortak bir arayüz ile yönetilmesi
- Selenium WebDriver ile web scraping yapılandırması
- Yerel LLM API'leri ile iletişim kurma
- Frontend API servislerinin yeni mimari ile uyumlu hale getirilmesi

## Bekleyen Görevler

### Öncelikli Maddeler:

1. **TaskRunner ve Editor Entegrasyonu:**
   - TaskRunner'dan Editor bileşenine kod değişikliği görevleri için geçiş mekanizması
   - Editor üzerinde yapılan değişikliklerin TaskRunner'a geri bildirilmesi
   - Kod değişikliği onay/red mekanizması

2. **WebSocket Desteği:**
   - LLM yanıtlarının gerçek zamanlı alınması için WebSocket entegrasyonu
   - Görev durumlarının gerçek zamanlı güncellenmesi
   - Uzun süreli görevlerin asenkron izlenmesi

3. **Frontend Bileşenleri Tamamlama:**
   - UserManager bileşeni
   - NetworkManager bileşeni
   - SchedulerManager bileşeni
   - ArchiveManager bileşeni

4. **LLM Entegrasyonu Geliştirme:**
   - LLM şablonlarının iyileştirilmesi
   - Yerel LLM entegrasyonu için optimizasyonlar
   - Web Scraper modunun iyileştirilmesi

5. **Güvenlik ve Yetkilendirme:**
   - Authentication sistemi eklemesi
   - Kullanıcı bazlı yetkilendirme
   - API güvenliği iyileştirmeleri

### Sonraki Adımlar:

- PWA özelliklerinin genişletilmesi (çevrimdışı mod, bildirimler)
- Docker konteyner desteği
- CI/CD pipeline entegrasyonu
- Test kapsamının artırılması
- Dokümantasyon geliştirme
- Görev setlerini backend'de saklama mekanizması
- Uzak MCP araçları entegrasyonu

## Çözülmesi Gereken Sorunlar:

- WebSocket ile gerçek zamanlı görev takibi
- LLM yanıtlarının formatlama ve doğrulama mekanizması
- Yerel LLM entegrasyonu için performans optimizasyonu
- MCP araçları arasında veri paylaşımı için güvenli mekanizma
- Kompleks görevlerin yönetimi ve izlenmesi için arayüz
- Uzak MCP sunucularına güvenli erişim
- In-memory dosyaların otomatik periyodik yedeklenmesi
- PWA ve Flask backend arasında güvenli veri iletişimi
- PWA'nın farklı tarayıcılarda uyumluluğu
- TaskRunner bağımlılık kontrolünün karmaşık ağaçlarda doğru çalışması
- Görev setlerini Cloud/Backend depolama sistemine taşıma

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
- Tailwind CSS yerine Bootstrap framework kullanımı
- Backend entegrasyonu için servis tabanlı API yapısı
- LLM değişiklik önizleme ve onay mekanizması
- Daraltılabilir sidebar ile ekran alanı optimizasyonu
- Responsive tasarım ile mobil uyumluluk
- TaskRunner için iki kolonlu layout (görev listesi ve detaylar)
- Sürükle-bırak görev sıralama için React DnD kullanımı
- Görev çalıştırma için üç farklı mod (sıralı, paralel, manuel)
- Log kayıtları için indirilebilir format desteği
- Görev setlerini localStorage'da saklama
- LLM sağlayıcıları için factory pattern kullanımı
- Merkezi registry ile araçların dinamik yüklenmesi

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
- React Bootstrap Icons ile tutarlı ikon seti
- Görevler arası bağımlılık kontrol mekanizması
- Görev yürütme stratejileri için çeşitli modlar
- Hata yönetimi için farklı stratejiler (devam, durdur, sor)
- LLM sağlayıcı seçimi ve yapılandırması için modüler arayüz
- API iletişimi için adapter pattern

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
- Tek LLM sağlayıcısı yerine çoklu sağlayıcı desteği
- Flask blueprint'leri yerine MCP mimarisi (genişletilebilirlik için)

## Kaynaklar ve Referanslar

### Kullanılan Dokümanlar:

- Flask dokümantasyonu
- Psutil dokümantasyonu
- React dokümantasyonu
- Bootstrap dokümantasyonu
- React Bootstrap dokümantasyonu
- Monaco Editor dokümantasyonu
- Monaco diff editor dokümantasyonu
- Service Worker dokümantasyonu
- Web App Manifest dokümantasyonu
- LLM API (OpenAI, Anthropic) dokümantasyonu
- React DnD dokümantasyonu
- Selenium WebDriver dokümantasyonu
- Ollama API dokümantasyonu
- LM Studio API dokümantasyonu

### API Referansları:

- Flask API
- React API
- React Bootstrap API
- Monaco Editor API
- Monaco Diff Editor API
- Service Worker API
- Web App Manifest API
- OpenAI API
- React DnD API
- Selenium API
- Ollama API
- LM Studio API
- Subprocess ve sistem komutları

### Örnek Kodlar/Snippetler:

- mcp_core/tool.py (MCP Tool temel sınıfı)
- mcp_core/registry.py (MCP Registry yapısı)
- coordination/coordinator.py (Görev koordinasyonu)
- tools/in_memory_editor.py (metin işleme fonksiyonları ve şablon mekanizması)
- tools/llm_tool.py (LLM entegrasyonu)
- frontend/src/App.js (Ana uygulama düzeni)
- frontend/src/App.css (Ana uygulama stilleri)
- frontend/src/serviceWorkerRegistration.js (PWA service worker kaydı)
- frontend/public/manifest.json (PWA manifest dosyası)
- frontend/src/services/api.js (API servis modülü)
- frontend/src/pages/Dashboard.js (Dashboard bileşeni)
- frontend/src/pages/TaskRunner.js (LLM görev yürütücü)
- frontend/src/pages/Editor.js (Editor ve diff görüntüleyici)
- backend LLM entegrasyonu ve görev yürütme API'leri
- backend metin değişiklik önizleme API'si

## Notlar

### Önemli Hatırlatmalar:

- Proje MCP mimarisine geçiş sürecini tamamlıyor
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
- LLM entegrasyonu için çoklu sağlayıcı desteği eklendi
- TaskRunner ana sayfa olarak yapılandırıldı

### Dikkat Edilmesi Gerekenler:

- LLM çıktılarının güvenli şekilde işlenmesi ve uygulanması
- JSON şablon formatının tutarlılığının korunması
- MCP araçlarının doğru şekilde kaydedilmesi ve yönetilmesi
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
- Web scraper'ın doğru şekilde yapılandırılması ve yönetilmesi
- Yerel LLM araçlarıyla iletişim sorunlarının çözülmesi

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
│   │   │   ├── TaskRunner.js
│   │   │   └── Settings.js
│   │   ├── services/             # API servis modülleri
│   │   │   └── api.js
│   │   ├── serviceWorkerRegistration.js  # Service worker kayıt
│   │   ├── service-worker.js     # Service worker yapılandırması
│   │   ├── App.js                # Ana uygulama bileşeni
│   │   ├── App.css               # Ana uygulama stilleri
│   │   └── index.js              # Uygulama giriş noktası
├── app.py                        # Ana Flask uygulaması
└── requirements.txt              # Bağımlılıklar
```