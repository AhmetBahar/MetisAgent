# Metis Agent - Proje Devamlılık Dokümanı
## Proje Genel Bilgileri

**Proje Adı:** Metis Agent  
**Başlangıç Tarihi:** 31.03.2025  
**Amaç ve Kapsam:** İşletim sistemi fonksiyonlarına erişim sağlayan, Flask tabanlı bir araç setinin geliştirilmesi. Bu araç, dosya yönetimi, kullanıcı yönetimi, ağ yönetimi, zamanlayıcı ve arşiv yönetimi gibi çeşitli sistem operasyonlarını API üzerinden erişilebilir hale getirmektedir. LLM entegrasyonu ile bu operasyonlar doğal dil komutlarıyla otomatize edilebilmektedir.  
**Kullanıcı/İstemci:** Sistem yöneticileri, geliştiriciler ve otomasyon araçları için tasarlanmıştır.

## Teknik Altyapı

**Kullanılan Teknolojiler:** RESTful API, MCP (Model-Controller-Protocol) mimari yapısı, Progressive Web App (PWA), WebSocket, LLM Entegrasyonu, A2A (Agent-to-Agent) protokolü  
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
**Mimari Yapı:** MCP (Model-Controller-Protocol) yapısı ile modüler bir tasarım. Her araç kendi blueprint'ine sahiptir ve araçlar registry üzerinden yönetilmektedir. A2A protokolü ile personalar arası mesajlaşma ve görev dağılımı sağlanmaktadır.

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
- LLM ile araç-bazlı görev çalıştırma (tool-action-params) mekanizması

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
- LLM yanıt işleme ve format dönüştürme geliştirmeleri

### Devam Eden Çalışmalar:

- A2A protokolü implementasyonu
- Persona bazlı ajan mimarisi geliştirme
- Genişletilmiş MCP Registry ile dış kaynak araçlar entegrasyonu
- Uzak MCP araçları entegrasyonu
- Eksik frontend bileşenlerinin (UserManager, NetworkManager, ArchiveManager, Scheduler) tamamlanması
- LLM entegrasyonu için gelişmiş metin işleme yeteneklerinin uygulanması
- PWA özelliklerinin geliştirilmesi (çevrimdışı çalışma, bildirimler)
- Authentication/Authorization mekanizmasının eklenmesi
- ChatRunner ve Editor entegrasyonunun tamamlanması

### Son Oturum Tarihi: 06.04.2025
### Son Oturumda Ulaşılan Nokta: 
- LLM Tool içinde araç-bazlı görev üretme system prompt'u optimize edildi
- TaskRunner.js'de LLM yanıt işleme mantığı geliştirildi
- Frontend ve Backend arasındaki format uyumsuzlukları giderildi
- WebSocket streaming ve non-streaming modların sorunsuz çalışması sağlandı
- JSON yanıt format hataları çözüldü
- A2A protokolü ve Persona mimarisi tasarımı tamamlandı

## İlerleme Günlüğü

### Oturum 1-15: (Önceki oturumlar)

### Oturum 16 (31.03.2025, 09:30-11:45):
**Belirlenen hedefler:** Frontend ve backend arasındaki fonksiyonları uyumlu hale getirmek, MCP mimarisine tam geçişi tamamlayıp görevler arası çıktı iletimini sağlamlaştırmak
**Tamamlanan hedefler:** Backend tarafında context yönetimi için API endpoint'leri eklendi, frontend tarafında TaskRunnerAPI genişletildi, görevler arası placeholder kullanımı düzeltildi
**Yapılan işlemler:**
- Backend ve Frontend Ayrımının Netleştirilmesi
- TaskRunner'da task çalıştırma mantığını backend'e taşıdık
- Placeholder güncellemelerini MCPCoordinator sınıfında merkezileştirdik
- LLM değerlendirme işlemini backend tarafında gerçekleştirdik
- Frontend'i sadece kullanıcı arayüzü ve tetikleyici olarak konumlandırdık

- API Servisleri Geliştirilmesi
- TaskRunnerAPI servisini MCP mimarisine uygun olarak genişlettik
- Context yönetimi için yeni API endpoint'leri ekledik:
  - /api/task/execute_with_context: Placeholder güncelleme ile görev çalıştırma
  - /api/tasks/execute_sequential: Context'i güncelleyerek sıralı görev çalıştırma
  - /api/context/get: Mevcut context değerlerini alma
  - /api/context/update: Context değerlerini güncelleme

- TaskRunner Komponenti İyileştirmeleri
- Frontend task çalıştırma mantığını backend API çağrılarına yönlendirdik
- Görevler arası bağımlılık kontrolünü ID bazlı çalışacak şekilde düzelttik
- Placeholder güncellemelerini backend'den almayı sağladık
- LLM değerlendirmelerini backend'den almak için kodu güncelledik

**Alınan kararlar:**
- Task çalıştırma ve koordinasyon mantığını backend'de merkezileştirme
- Placeholder ve context yönetimini backend'de yapma
- LLM değerlendirmelerini backend tarafında gerçekleştirme
- Frontend'in sadece kullanıcı arayüzü ve tetikleyici olarak çalışması
- TaskRunnerAPI servisini genişleterek MCP mimarisine tam geçişi sağlama

### Oturum 17 (07.04.2025, 14:00-16:30):
**Belirlenen hedefler:** A2A protokolü ve Persona mimarisi için altyapı tasarımı ve implementasyon planlaması
**Tamamlanan hedefler:** A2A protokolü modellemesi, Persona registry yapısı, dış kaynak araçlar için genişletilmiş MCP Registry tasarımı
**Yapılan işlemler:**
- A2A mesajlaşma protokolü için temel sınıfların tasarlanması:
  - A2AMessage sınıfı (mesaj yapısı ve serileştirme)
  - A2ARegistry sınıfı (mesaj yönlendirme ve persona yönetimi)
  - PersonaAgent sınıfı (A2A protokolünü destekleyen ajan yapısı)

- Genişletilmiş MCP Registry yapısının tasarlanması:
  - Dış kaynak araçların (external tools) registry'e kaydedilebilmesi
  - Araç yeteneklerinin dinamik olarak keşfedilebilmesi
  - Uzak MCP sunucularındaki araçların proxy üzerinden erişilebilmesi

- Persona modelinin oluşturulması:
  - JSON bazlı persona tanımları
  - Persona'ların görev tiplerine göre otomatik seçilmesi
  - Persona performans izleme ve optimizasyonu
  - Persona öncelik ve yetki mekanizmaları

- MCPCoordinator'un A2A protokolü ile entegrasyonu:
  - Görevlerin uygun persona'lara dağıtılması
  - Karmaşık görev zincirlerinin oluşturulması
  - Asenkron görev işleme ve sonuç toplama

**Alınan kararlar:**
- A2A protokolünün persona yapısının temeli olarak kullanılması
- Dış kaynak araçların entegrasyonu için genişletilmiş MCP Registry'nin oluşturulması
- Persona'ların JSON dosyaları olarak yönetilmesi
- MCPCoordinator'un merkezi mesaj yönlendirici olarak kullanılması
- Mesaj yönlendirme için asenkron kuyruk sisteminin kullanılması

**Karşılaşılan zorluklar:**
- A2A protokolü için message routing sisteminin güvenli ve ölçeklenebilir tasarımı
- Dış kaynak araçlar için güvenlik mekanizmaları
- Persona'lar arası yetkilendirme ve izolasyon sağlanması
- Karmaşık görev zincirlerinde döngüsel bağımlılıkların önlenmesi

## Bekleyen Görevler

### Öncelikli Maddeler:

1. **A2A Protokolü ve Persona Mimarisi İmplementasyonu:**
   - A2AMessage sınıfı implementasyonu
   - A2ARegistry sınıfı implementasyonu
   - PersonaAgent sınıfı implementasyonu
   - Temel persona JSON şablonlarının oluşturulması
   - MCPCoordinator'un A2A entegrasyonu

2. **Genişletilmiş MCP Registry İmplementasyonu:**
   - Uzak MCP araçları için proxy mekanizması
   - Dış kaynak araçlar için adaptör mekanizması
   - Dinamik araç keşfi için servisler
   - Araç yetenekleri (capabilities) sorgulama sistemi

3. **TaskRunner ve Editor Entegrasyonu:**
   - TaskRunner'dan kod değişikliği görevleri için Editor'a yönlendirme
   - Editor'daki değişikliklerin TaskRunner'a bildirilmesi
   - Kod değişikliği görevleri için onay mekanizmasının iyileştirilmesi

4. **LLM Entegrasyonu İyileştirmeleri:**
   - Sağlayıcı bağlantı durumu izleme ve otomatik yeniden bağlanma
   - Uzun bağlam desteği için bölünmüş görev oluşturma
   - LLM başarısızlıklarını daha güçlü hata işleme ile yönetme
   - LLM sağlayıcıları için daha güvenli API anahtarı yönetimi
   - Araç-bazlı görev çalıştırma mekanizmasının iyileştirilmesi

5. **Frontend Bileşenleri Tamamlama:**
   - UserManager bileşeni
   - NetworkManager bileşeni
   - SchedulerManager bileşeni
   - ArchiveManager bileşeni
   - LLM ayarları sayfasının genişletilmesi
   - Persona yönetimi arayüzü

### Sonraki Adımlar:

- Persona performans izleme sistemi
- Persona A/B testi ve optimizasyon
- WebSocket bağlantılarının izlenmesi ve yönetimi
- LLM sistemlerine daha geniş format desteği ekleme (imajlar, dosyalar)
- Docker konteyner desteği
- CI/CD pipeline entegrasyonu
- Test kapsamının artırılması
- Dokümantasyon geliştirme
- LLM şablonlarının iyileştirilmesi
- Farklı LLM sağlayıcıları için sistem promptlarının optimizasyonu
- Kompleks görevler için örnek şablonlar oluşturma

## Çözülmesi Gereken Sorunlar:

- A2A protokolünde mesaj güvenliği ve izolasyonu
- Dış kaynak araçların güvenli entegrasyonu
- Persona'lar arası yetkilendirme ve izolasyon
- Karmaşık görev zincirlerinde döngüsel bağımlılıkların önlenmesi
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
- LLM'in tool-action-params formatıyla görev üretiminde tutarlılığın korunması

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
- Tool-action-params formatı ile araç-bazlı görev çalıştırma
- Emoji ve görsel ayırıcılar ile geliştirilmiş LLM system prompt tasarımı
- Persona mimarisi için A2A protokolünün kullanılması
- Dış kaynak araçların entegrasyonu için genişletilmiş MCP Registry
- Persona'ların JSON dosyaları olarak yönetilmesi
- Asenkron mesaj yönlendirme sistemi

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
- Araç odaklı görev tanımlama (tool-action-params) yaklaşımı
- Esnek sistem prompt tasarımı (MCP araçları öncelikli, gerekirse komut çalıştırma)
- A2A protokolü ile personalar arası mesajlaşma
- Uzak MCP araçları için proxy mekanizması
- Dış kaynak araçlar için adaptör mekanizması
- Persona performans izleme ve öncelik sistemi

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
- Katı "sadece MCP araçları kullan" yaklaşımı yerine, esnek "öncelikle MCP araçlarını tercih et, gerekirse command_executor kullan" yaklaşımı
- Sabit LLM yanıt formatı yerine cevap dönüştürme mantığı içeren esnek işleme
- Personalar için statik bir yönlendirme mekanizması yerine A2A protokolü
- Görev yönlendirme için merkezi yönetim yerine dağıtık mesajlaşma

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
- A2A protokolü ve ajanlar arası iletişim referansları

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
- a2a_protocol/message.py (A2A mesaj sınıfı)
- a2a_protocol/registry.py (A2A registry yapısı)
- personas/persona_agent.py (Persona ajanı sınıfı)

## Notlar

### Önemli Hatırlatmalar:

- Proje şu anda A2A protokolü ve genişletilmiş MCP Registry entegrasyonu aşamasında
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
- Araç-bazlı görev tanımlama (tool-action-params) mekanizması eklendi
- LLM system prompt tasarımı iyileştirildi
- Frontend yanıt işleme mekanizması güçlendirildi
- A2A protokolü tasarımı tamamlandı
- Persona registry yapısı tasarlandı
- Genişletilmiş MCP Registry tasarlandı

### Dikkat Edilmesi Gerekenler:

- A2A mesajlaşmasında güvenlik ve izolasyon
- Dış kaynak araçların güvenli entegrasyonu
- Persona'lar arası yetkilendirme ve mesajlaşma güvenliği
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