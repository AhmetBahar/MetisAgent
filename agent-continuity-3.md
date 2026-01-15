Proje Devamlılık Dokümanı
Proje Genel Bilgileri

Proje Adı: Metis Agent
Başlangıç Tarihi: (Belirtilmemiş)
Amaç ve Kapsam: İşletim sistemi fonksiyonlarına erişim sağlayan, Flask tabanlı bir araç setinin geliştirilmesi. Bu araç, dosya yönetimi, kullanıcı yönetimi, ağ yönetimi, zamanlayıcı ve arşiv yönetimi gibi çeşitli sistem operasyonlarını API üzerinden erişilebilir hale getirmektedir.
Kullanıcı/İstemci: Sistem yöneticileri, geliştiriciler ve otomasyon araçları için tasarlanmıştır.

Teknik Altyapı

Kullanılan Teknolojiler: RESTful API, MCP (Model-Controller-Protocol) mimari yapısı
Programlama Dilleri: Python
Frameworkler/Kütüphaneler:

Flask (Web API)
Requests (HTTP istekleri)
Psutil (Sistem kaynakları izleme)
Shutil (Dosya işlemleri)
JSON (Şablon depolama)


Veritabanı: Şu anda kullanılmıyor
Mimari Yapı: MCP (Model-Controller-Protocol) yapısı ile modüler bir tasarım. Her araç kendi blueprint'ine sahiptir ve araçlar registry üzerinden yönetilmektedir.

Mevcut Durum

Tamamlanan Bölümler:

Dosya Yönetimi (file_manager.py)
Sistem Bilgisi (system_info.py)
Kullanıcı Yönetimi (user_manager.py)
Ağ Yönetimi (network_manager.py)
Zamanlayıcı (scheduler.py)
Arşiv Yönetimi (archive_manager.py)
Komut Çalıştırıcı (command_executor.py)
API yapısı (app.py)
MCP Çekirdek yapısı (mcp_core/)
Koordinasyon mekanizması (coordination/)
MCP mimarisine dönüştürülmüş araçlar (tools/)
In-memory editor entegrasyonu
In-memory editor için disk kalıcılık özellikleri (save_to_disk, load_from_disk)
In-memory editor için metin arama/değiştirme fonksiyonları
LLM kod değişiklik şablonları için saklama ve uygulama mekanizması


Devam Eden Çalışmalar:

Uzak MCP araçları entegrasyonu
React tabanlı kullanıcı arayüzü geliştirilmesi
MonacoEditor entegrasyonu
LLM entegrasyonu için gelişmiş metin işleme yeteneklerinin uygulanması


Son Oturum Tarihi: 31.03.2025
Son Oturumda Ulaşılan Nokta: In-memory editor'e LLM kod değişiklik şablonları için saklama ve uygulama mekanizması eklenmesi

İlerleme Günlüğü

Oturum 1-5: (Önceki oturumlar)
Oturum 6 (31.03.2025, 21:00-22:00):

Belirlenen hedefler: In-memory editor'ün LLM entegrasyonu için metin işleme yeteneklerinin değerlendirilmesi
Tamamlanan hedefler: Mevcut metin arama ve değiştirme fonksiyonlarının değerlendirilmesi, LLM kod değişiklik şablonları için mekanizma tasarlanması
Yapılan işlemler:

find, find_and_replace, select_lines, go_to_line fonksiyonlarının gözden geçirilmesi
LLM entegrasyonu için potansiyel geliştirme alanlarının belirlenmesi
LLM kod değişiklik şablonlarını saklama ve uygulama mekanizması tasarlanması ve uygulanması


Önemli kod değişiklikleri (özet):

initialize_change_templates, save_change_template, get_change_template, list_change_templates, delete_change_template ve apply_llm_change fonksiyonları eklendi
.change_templates.json dosyası ile şablonların in-memory depolanması sağlandı
JSON formatında kod değişiklik şablonları için standart format belirlendi


Alınan kararlar:

Kod değişiklik şablonlarının JSON formatında saklanması
Mevcut in-memory dosya sistemi içinde özel bir dosyada şablonların depolanması
LLM ile standart bir değişiklik formatı kullanılması


Karşılaşılan zorluklar:

In-memory dosya sistemi ile JSON formatında veri saklanmasının entegrasyonu
Değişiklik uygulamalarında satır numaralarının doğru yönetilmesi gerekliliği





Bekleyen Görevler

Öncelikli Maddeler:

In-memory editor için gelişmiş metin işleme fonksiyonlarının eklenmesi:

Regex ile arama ve değiştirme
Belirli satır aralığında metin değiştirme
Belirli konuma metin ekleme/çıkarma


LLM kod değişiklik şablonları için disk kalıcılığının eklenmesi
Diğer araçların (sistem bilgisi, kullanıcı yönetimi, ağ yönetimi) MCP yapısına dönüştürülmesi
Uzak MCP araçları için güvenli iletişim protokolünün oluşturulması


Sonraki Adımlar:

React tabanlı kullanıcı arayüzünün geliştirilmesi
MonacoEditor entegrasyonunun tamamlanması
LLM entegrasyonu için API genişletilmesi
Authentication/Authorization mekanizmasının eklenmesi
Görev planlama ve çalıştırma için web arayüzü geliştirme
Docker konteyner desteği
WebSocket desteği ile gerçek zamanlı görev takibi
In-memory editor için daha gelişmiş metin işleme özellikleri


Çözülmesi Gereken Sorunlar:

LLM çıktılarının standartlaştırılması ve metin değişikliklerinin güvenli şekilde uygulanması
Şablonların sürümlenmesi ve değişiklik geçmişinin izlenmesi
MCP araçları arasında veri paylaşımı için güvenli mekanizma
Kompleks görevlerin yönetimi ve izlenmesi için arayüz
Uzak MCP sunucularına güvenli erişim
In-memory dosyaların otomatik periyodik yedeklenmesi



Alınan Kararlar

Tasarım Tercihleri:

Flask Blueprint'leri yerine MCP mimarisi kullanılacak
Modüler, genişletilebilir yapı için MCPTool ve MCPRegistry sınıfları
Karmaşık görevlerin yönetimi için MCPCoordinator kullanımı
API tabanlı mimari
In-memory editor için disk kalıcılık mekanizması
LLM entegrasyonu için standardize edilmiş kod değişiklik şablonları
Şablonların in-memory dosya sistemi içinde JSON formatında saklanması


Uygulama Yaklaşımları:

Merkezi registry ile araçların yönetimi
Dinamik modül yükleme ve araç kaydetme
Araçlar arası koordinasyon için görev yönetim sistemi
React + MonacoEditor ile kullanıcı dostu arayüz
Bellek içi ve disk tabanlı işlemlerin entegrasyonu
LLM çıktıları için standartlaştırılmış metin işleme protokolleri
Kod değişiklik şablonları için JSON temelli depolama


Reddedilen Alternatifler:

Doğrudan Python kütüphanesi yerine API yaklaşımı tercih edildi
Karmaşık veritabanı yapısı yerine dosya tabanlı kayıt sistemi
Monolitik yapı yerine modüler, servis tabanlı yaklaşım
Tüm metin değişikliklerinin tek bir write_file fonksiyonu ile yapılması yerine, granüler metin işleme fonksiyonları
Şablonlar için ayrı bir depolama mekanizması yerine mevcut in-memory dosya sisteminin kullanılması



Kaynaklar ve Referanslar

Kullanılan Dokümanlar:

Flask dokümantasyonu
Psutil dokümantasyonu
React ve MonacoEditor dokümantasyonu
Python regex modülü dokümantasyonu
Python JSON modülü dokümantasyonu


API Referansları:

Flask API
React API
Monaco Editor API


Örnek Kodlar/Snippetler:

mcp_core/tool.py (MCP Tool temel sınıfı)
mcp_core/registry.py (MCP Registry yapısı)
coordination/coordinator.py (Görev koordinasyonu)
tools/in_memory_editor.py (metin işleme fonksiyonları ve şablon mekanizması)



Notlar

Önemli Hatırlatmalar:

Proje şu anda modüler MCP yapısına geçiş aşamasında
In-memory editor disk kalıcılık özellikleri eklendi
LLM kod değişiklik şablonları için mekanizma eklendi
Uzak MCP araçları için güvenlik protokolü henüz eklenmedi


Dikkat Edilmesi Gerekenler:

LLM çıktılarının güvenli şekilde işlenmesi ve uygulanması
JSON şablon formatının tutarlılığının korunması
Dönüştürülen araçların eski blueprint'ler ile uyumluluğunun sağlanması
MCP yapısının API güvenliği (yetkilendirme sistemi henüz eklenmedi)
Uzak MCP araçları için proxy mekanizmasının güvenliği
In-memory dosyaların disk dönüşümlerinde karakter kodlaması sorunları


Ekstra Bilgiler:

MCP mimarisi, modüler yapısıyla gelecekte yeni araçların kolayca eklenebilmesini sağlar
Araçlar arası koordinasyon, karmaşık görevlerin otomatize edilmesini mümkün kılar
React arayüzü, sistem yönetimini ve otomasyonu kolaylaştıracak
In-memory editor için disk kalıcılık özellikleri, uzun süreli projelerde çalışmayı destekler
LLM entegrasyonu, karmaşık metin işleme ihtiyaçlarını otomatize edebilir
Kod değişiklik şablonları, LLM'in tutarlı şekilde kod değişiklikleri yapmasını sağlar



MCP Mimarisi Yeni Dizin Yapısı
MetisAgent/
├── os_araci/
│   ├── mcp_core/                 # MCP çekirdek yapısı
│   │   ├── init.py
│   │   ├── registry.py           # Araç kayıt sistemi
│   │   └── tool.py               # MCP araç temel sınıfı
│   ├── tools/                    # MCP araçları
│   │   ├── init.py
│   │   ├── file_manager.py       # Dosya yönetimi aracı
│   │   ├── in_memory_editor.py   # Bellek içi editör (disk kalıcılık desteği eklenmiş)
│   │   └── ... (diğer araçlar)
│   ├── coordination/             # Koordinasyon mekanizması
│   │   ├── init.py
│   │   └── coordinator.py        # Görev koordinatörü
│   └── routes/                   # Eski blueprint yapısı (geçiş sürecinde)
├── frontend/                     # React arayüzü (geliştirilecek)
├── app.py                        # Ana Flask uygulaması
└── requirements.txt              # Bağımlılıklar