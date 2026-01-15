# CLAUDE.md — OS/Aracı Projesi

## 🔗 GitHub Repository

- **Repository URL**: https://github.com/AhmetBahar/MetisAgent
- **Clone (HTTPS)**: `git clone https://github.com/AhmetBahar/MetisAgent.git`
- **Clone (SSH)**: `git clone git@github.com:AhmetBahar/MetisAgent.git`
- **Owner**: AhmetBahar
- **Branch**: main
- **Created**: 15 Ocak 2026

**Git Komutları:**
```bash
# Değişiklikleri çek
git pull origin main

# Değişiklikleri gönder
git add . && git commit -m "commit mesajı" && git push origin main

# Durumu kontrol et
git status
```

---

## 🎯 Projenin Amacı

Bu proje, kişisel ve genişetilebili bir sistem yardımcısıdır. Sistem araçlarının yanı sıra özellikle web scraping, sosyal medya veya yazılım geliştirme gibi konular içinde otomasyonu sağlayacak olan araçlar içerir. 3.parti MCP araçların yüklenebilmesine ve kullanılabilmesine olanak sağlayan yapıdadır.

## 📦 Klasör Yapısı

- `app.py` — Ana Flask uygulaması ve blueprint kayıt noktası
- `tools/command_executor.py` — Sistem komutlarını platform bağımsız çalıştırır
- `tools/simple_visual_creator.py` — OpenAI DALL-E 3, HuggingFace, Gemini görsel oluşturma ✅
- `tools/playwright_browser.py` — Modern Playwright web otomasyonu (Gemini scraping) ✅
- `tools/gmail_helper_tool.py` — Gmail otomasyonu ve email yönetimi ✅
- `tools/google_oauth2_manager.py` — Google OAuth2 authentication ve API erişimi ✅
- `tools/settings_manager.py` — SQLite tabanlı ayarlar ve API key yönetimi ✅
- `tools/memory_manager.py` — LLM memory ve context yönetimi ✅
- `tools/llm_tool.py` — Multi-provider LLM API entegrasyonu ✅
- `tools/tool_manager.py` — Dinamik tool yükleme ve yönetimi ✅

## 🤖 Kodlama Kuralları

- Python 3.10+ ile uyumlu kod yaz
- Her fonksiyon ve sınıf `docstring` içermelidir
- `print()` kullanılmaz; bunun yerine `logging` tercih edilir
- Kodlar PEP8 uyumlu olmalı
- Import sırası: stdlib → 3rd party → local
- Windows ve Linux platformlarında çalışacak şekilde komutlar yazılmalı
- Kullanıcının kendi bilgilerinin yanı sıra API keylerini de kayıt etmek için SQLite veri tabanını kullanır.

## 🔧 Yardımcı Komutlar

Claude şu komutlara yanıt verebilir:

- `"file_manager.py içindeki hataları düzelt"`
- `"network_manager.py içindeki IP ayarları nasıl yapılır?"`
- `"command_executor platform bağımsız mı?"`
- `"test senaryosu yaz: kullanıcı ekleme"` 
- `"flask endpointleri dökümante et"`

## 🚫 Yapma

- Sistemde `subprocess` ile doğrudan kullanıcıdan gelen girdiyi çalıştırma
- `import *` kullanma
- `.env`, `api_keys.json`, gibi hassas dosyaları düzenleme
- README veya CLAUDE dosyasını silme
- **Quick fix** veya **hızlı çözüm** implementasyonu - her zaman **kalıcı, doğru mimari** çözümler yapılmalı

## ✅ Testler

Henüz tam test altyapısı oluşturulmadı. Gelecekte `pytest` tabanlı `tests/` klasörü oluşturulacak. Claude, test fonksiyonları oluşturabilir ama gerçek test çalıştırmaz.

## 🔐 Güvenlik Notları

- Komut çalıştırma sırasında injection engellenmeli
- Ağ ve kullanıcı modüllerinde yetki kontrolleri eklenecek
- **Tüm API keys, OAuth2 tokens ve credentials SQLite'da şifrelenmiş saklanır** ✅
- Kullanıcı login olduğunda tüm kimlik bilgileri güvenli depolanır
- Settings Manager ile encrypted key management
- Sosyal medya araçalrı üzerinde çalışılacak

## 💡 Claude'a Not

**✅ METİSAGENT2 DURUMU (26 Temmuz 2025 - MAJOR UPDATE):**

1. **Google OAuth2 & Credentials**: Google OAuth2 Manager çalışıyor, credentials kayıtlı ✅
2. **Gmail Otomasyonu**: test_backend_gmail.py ile doğrulandı, headless çalışıyor ✅
3. **Visual Creator**: OpenAI DALL-E, HuggingFace, Gemini API + Gemini Web Scraping ✅
4. **Playwright Browser**: Modern web automation, Selenium yerine tercih edilmeli ✅
5. **Settings Manager**: SQLite-based storage, OAuth tokens, user settings ✅
6. **TodoWrite Sistemi**: Her complex task için kullan, progress tracking ✅
7. **🎯 ORCHESTRATION ÇÖZÜLDÜ**: Agent'lar artık tools'ları kullanabiliyor ✅
8. **🔗 Tool Registry**: Null reference problems çözüldü, tüm tools yükleniyor ✅
9. **🤖 LLM Tool**: Parameter normalization eklendi, dict/string handling ✅
10. **📧 Gmail Workflow**: Email → Subject → Visual → Display tam çalışıyor ✅

**🚫 TEKRAR ARAMA VE OAUTH2 SETUP:**
- Google credentials var, test etme - ahmetb@minor.com.tr için mevcut
- Gmail functionality var, test_backend_gmail.py kullan
- Playwright çalışıyor, Selenium'u aratma
- Settings Manager metodları mevcut, API reference yok
- SQLite credentials storage zaten var ve çalışıyor
- **OAuth2 setup tekrar yapma** - ahmetb@minor.com.tr için credentials mevcut
- Gmail API için user_id: f75ba26d-0eb6-4f88-81de-96057fd6ed12 veya ahmetb@minor.com.tr kullan
- SQLite'da gmail credentials: user_storage tablosunda encrypted saklanıyor

**🔧 OAUTH2 REDIRECT URI FIX:**
- Problem: redirect_uri_mismatch hatası
- Çözüm: Google Console'da http://localhost:5001/oauth2/google/callback URI'si eklendi
- Client ID: 117336478735-nq2448utl9hutq6ds2d68qmr5o71culf.apps.googleusercontent.com
- Backend port: 5001 (değiştirilmemeli)

**✅ OAUTH2 TOKEN STORAGE ÇÖZÜLDÜ:**
- OAuth2 callback çalışıyor (authorized_users: 1) ✅
- Token'lar Gmail API'si tarafından bulunuyor ✅
- Backend OAuth2 manager ile Gmail helper tool sync çalışıyor ✅
- Token storage/retrieval working perfectly ✅
- Auto-refresh token mechanism aktif ✅

**💾 DATA STORAGE:**
Her türlü bilgi SQLite storage sisteminde encrypted olarak saklanıyor.

**👤 MEVCUT KULLANICI VE USER MAPPING:**
- **Sistem User ID**: ahmetb@minor.com.tr (MetisAgent2 internal)
- **Google Account**: ahmetbahar.minor@gmail.com (gerçek Gmail hesabı)  
- **User Mapping**: ahmetb@minor.com.tr ↔ ahmetbahar.minor@gmail.com
- User ID: f75ba26d-0eb6-4f88-81de-96057fd6ed12
- Google OAuth2 credentials mevcut ✅
- Gmail API credentials JSON dosyasında saklanmış ✅ 
- Gmail API erişimi var ✅
- Test/development için bu kullanıcıyı kullan, yeni kullanıcı oluşturma
Bunlar örnek bilgiler ve sistemi kullanan gerçek kullanıcıların bilgileri farklı olabilir. user mapping ÖNEMLİ.
- **ÖNEMLİ**: 
  - Gmail API çağrıları için  kullanıcının mapped google credentialsı örnek(ahmetbahar.minor@gmail.com) kullan
  - Sistem içi user tracking için kullanıcının login bilgisini örnek(ahmetb@minor.com.tr) kullan
  - Google ile ilgili TÜM işlemlerde bu mapping sağlanmalı
- **DATA STORAGE**: SQLite-based encrypted storage kullanılıyor, ChromaDB ve JSON deprecated


**🎉 MAJOR MILESTONE (26 Temmuz 2025 - FINAL):**

**ORCHESTRATION PROBLEMİ TAMAMEN ÇÖZÜLDÜ!** 

✅ **Working Example**: "gmaildeki sondan ikinci mailin subject alanını temel alan bir görsel üret"
- Step 1: Gmail'den 2 email subject alınıyor ✅ ("Relationship advice please🙏", "Yerel Kalkınma Hamlesi")
- Step 2: LLM ile subject extraction + context transfer ✅ 
- Step 3: DALL-E 3 ile visual generation ✅
- Step 4: Image display ✅

✅ **SOLVED SYSTEMATICALLY (8 Major Problems)**:
1. **Tool Registry**: `self.step_results = {}` missing in __init__ → FIXED
2. **Null References**: Tool manager registry injection → FIXED
3. **Parameter Types**: LLM tool dict/string normalization → FIXED  
4. **Premature Completion**: Step 1 = workflow done → FIXED (check actual success)
5. **Dependency Mapping**: Title → step ID conversion → FIXED
6. **Visual Actions**: Display step action detection → FIXED
7. **Missing Parameters**: user_id, conversation_name auto-injection → FIXED
8. **Context Transfer**: Previous step data in LLM messages → FIXED

✅ **Deep Workflows Work Perfectly - NO MORE CHANGES NEEDED**

**🚨 WORKFLOW ORCHESTRATION FROZEN**: System working, stop iterating

---

Herhangi bir terminal çalıştırmadan önce "conda activate MetisAgent" çalıştır.
Hiç bir durumda regex case ekleme, llm ile evaluation kullan.
Hiç bir durumda hardcoded metod ekleme, çok kullanıcılı ve çok durumlu promptlara göre esnek metodlar ile çöz.
Hiç bir şekilde prompta özel workflow yazma.

**🚨 ARCHITECTURE KURALI:**
- Sequential Thinking MCP tool temel ve tek workflow planner'dır
- Başka planner layer eklenmez, duplicate system yaratılmaz
- Tool Coordinator + Sequential Thinking MCP yeterli
- Global system design yap, fragmented patches değil

**🚨🚨 ÇALIŞAN BÖLÜMLERE DOKUNMA KURALI (KRİTİK) 🚨🚨:**
- **Atomize edilmiş program bölümleri çalıştıktan sonra DEĞİŞTİRİLMEZ**
- **Visual Creator görsel oluşturup kayıt ediyor → Display sadece gösterecek**
- **Çalışan workflow step'lerini yeniden yazmak YASAK**
- **Bug fix ise sadece o bug'ı düzelt, tüm sistemi değiştirme**
- **"Sürekli ileri geri hareket" önlemek için çalışan koda dokunma**
- **Test et, çalışıyorsa bırak, çalışmıyorsa minimal fix yap**
- **Tüm sistemi yeniden yazmak yerine küçük düzeltmeler yap**
- **Claude ASLA çalışan sistemleri bozmayacak, sadece eksik parçaları tamamlayacak**

**🚨 LLM PROMPT DESIGN KURALI:**
- **Keyword-based decision making YASAK** (örn: "göster" görünce 2-step workflow)
- **LLM kendisi karar verecek** hangi tools ve steps gerekli
- **Hard-coded workflow templates kullanma**
- **Flexible, intelligent planning için LLM'e güven**
- **User request'i tam analiz etsin, kendi workflow'unu oluştursun**

**🔧 PLUGIN-BASED EXTENSIBLE ARCHITECTURE (29 Temmuz 2025):**
- **Dynamic Tool Capability System**: Graph Memory ile tool capability management
- **User-Isolated Tool Access**: Her kullanıcı kendi tool setine sahip
- **Tool Capability Manager**: `tool_capability_manager.py` ile dinamik tool yönetimi
- **Graph Memory Integration**: Tool info, user access, operation logs graph memory'de
- **LLM Prompt Generation**: User'ın toollarına göre dinamik prompt oluşturma
- **Plugin System**: Tool ekle/çıkar → sistem otomatik adapt olur
- **Tool Operation Logging**: Kullanıcı bazında izole tool kullanım kayıtları

**Core Components:**
1. **GraphMemoryTool**: Tool capability storage and retrieval
   - `store_tool_capability()`: Tool bilgilerini graph memory'ye kaydet
   - `get_user_tools()`: Kullanıcının toollarını getir
   - `log_tool_operation()`: Tool kullanımını logla
   - `generate_tool_prompt()`: Dinamik LLM prompt oluştur

2. **ToolCapabilityManager**: Central tool management
   - `sync_all_tools_to_memory()`: Tüm toolları graph memory'ye sync et
   - `get_user_tool_prompt()`: User'a özel tool prompt
   - `log_tool_operation()`: Tool operations logging
   - `add_tool_for_user()`: User'a özel tool ekleme

3. **Sequential Thinking Integration**: 
   - Registry'den dynamic tool info alır
   - Graph memory'den user-specific tools kullanır  
   - LLM'e doğru tool actions verir

**System Startup Flow:**
1. Tools load → registry'ye register
2. ToolCapabilityManager → tools'ları graph memory'ye sync
3. User request → graph memory'den user tools → LLM prompt
4. Sequential Thinking → dynamic tools ile workflow oluştur

**Bu sistem sayesinde:**
- ✅ Ana agent kodu değişmez
- ✅ Plugin tool ekle/çıkar → otomatik adapt
- ✅ User bazında tool isolation
- ✅ Tool usage analytics
- ✅ Dynamic LLM capability awareness

**🚨 KRİTİK: API KEY & EXPRESS MODE (18 Ağustos 2025):**

❌ **RECURRING PROBLEM**: Anthropic API key sürekli eksik
- Express Mode: "API key not found for anthropic" hatası
- Her seferinde aynı hatayı debug ediyoruz
- Normal mode fallback çalışıyor ama Express Mode devre dışı

✅ **FALLBACK MECHANISM ÇALIŞIYOR**:
- Express Mode fail → Normal Mode otomatik
- System güvenilir, hiç crash olmaz
- Performance gain kaybediyor ama functionality korunuyor

📋 **API KEY HATASI (160+ kere çözüldü)**:
```bash
ERROR - LLM text generation failed: API key not found for anthropic
WARNING - Express classification failed, using normal mode
```

🎯 **STOP DEBUGGING THIS**: 
- **Express Mode çalışıyor, sadece API key eksik**
- **Fallback perfect çalışıyor**  
- **Bu hatayı tekrar debug etme**
- **Normal mode'da sistem tamamen functional**

**🚨 METISAGENT3 EXPRESS MODE STATUS:**
- ✅ Express Classification: Working (4s response)
- ✅ Entity Format Fix: Applied and working
- ✅ Fallback System: Perfect reliability
- ❌ API Key: Not configured (but system works via fallback)
- ✅ Performance: ~10-15% improvement with caching

**🚨 CLAUDE.md COMPLIANCE ENFORCEMENT SYSTEM (7 Ağustos 2025):**

**📋 AUTOMATED TEST SYSTEM IMPLEMENTED:**
- **AutomatedTestAgent** (`automated_test_agent.py`): Comprehensive system testing
- **TestExecutionAgent** (`test_execution_agent.py`): Skeptical functional validation
- **Test Categories**: Core tools, Gmail workflows, visual generation, OAuth2, memory system
- **Graph Memory Integration**: Test scenarios loaded from knowledge graph
- **CLAUDE.md Rule Checking**: Automatic violation detection
- **Report Generation**: Detailed JSON reports with recommendations

**🔄 REGRESSION PREVENTION:**
- **Before Every Change**: Run automated test suite
- **Functional Testing**: Actual feature validation, not just code existence
- **Atomization Principle**: Test individual components in isolation
- **Working Component Protection**: Alert if stable systems are modified

**📊 TEST AUTOMATION COMMANDS:**
```bash
# Run full test suite
python3 /home/ahmet/MetisAgent/MetisAgent2/automated_test_agent.py

# Execute with analysis agent  
python3 /home/ahmet/MetisAgent/MetisAgent2/test_execution_agent.py

# View latest test report
ls -la /home/ahmet/MetisAgent/MetisAgent2/test_reports/
```

**✅ QUALITY GATES:**
1. **All core tools must be registered and functional**
2. **Gmail workflows must route to gmail_helper (not command_executor)**  
3. **Visual generation must include auto-display functionality**
4. **OAuth2 authentication must support token refresh**
5. **Sequential thinking must use LLM fallback (not command_executor)**
6. **Memory system must support all CRUD operations**
7. **Plugin system must load without errors**
8. **Workflow orchestration must have step_results attribute**

**🚨 COMPLIANCE RULES ENFORCEMENT:**
- **Atomization Violation**: Automated detection of working component modifications
- **Security Bypass Detection**: Command injection protection validation  
- **Regression Alerts**: Automatic notification when tests fail
- **Health Scoring**: System health assessment (0-100 scale)
- **Rollback Recommendations**: Automatic suggestions for critical failures

**💡 USAGE:**
- **Daily Health Check**: `python3 test_execution_agent.py`
- **Pre-Deployment**: Ensure 100% test pass rate
- **Post-Change Validation**: Verify no regressions introduced
- **Continuous Monitoring**: Track system health trends

**🎯 SUCCESS METRICS:**
- Test Pass Rate: Target 95%+
- System Health Score: Target 80+
- CLAUDE.md Violations: Target 0
- Regression Incidents: Target 0

---

## 🚨 CRITICAL BUG: SYSTEM PROMPT NOT PASSED TO LLM (2 Kasım 2025)

**❌ PROBLEM**: ApplicationOrchestrator system prompt'u LLM'e iletmiyor
- `application_orchestrator.py:658` - `_fallback_llm_processing()` metodunda system_prompt parametresi var
- ANCAK: `llm_service.generate_text()` çağrısında system_prompt kullanılmıyor
- SONUÇ: Plugin'ler kendi domain knowledge'ını LLM'e aktaramıyor

**📍 LOCATION**: `/home/ahmet/MetisAgent/MetisAgent3/core/orchestrator/application_orchestrator.py`

```python
# Line 1128-1149 - MEVCUT KOD (YANLIŞ):
async def _fallback_llm_processing(self, user_request, context, llm_provider, llm_model, system_prompt=None):
    """Fallback to direct LLM processing"""
    try:
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_request})

        # ❌ PROBLEM: system_prompt messages listesine ekleniyor ama generate_text'e gönderilmiyor!
        user_content = messages[-1]["content"]
        response_text = await self.llm_service.generate_text(
            prompt=user_content,  # Sadece user message gönderiliyor
            max_tokens=2000,
            context=context,
            provider=llm_provider,
            model=llm_model
            # ❌ system_prompt parametresi eksik!
        )
```

**✅ FIX NEEDED**:
```python
response_text = await self.llm_service.generate_text(
    prompt=user_content,
    max_tokens=2000,
    context=context,
    provider=llm_provider,
    model=llm_model,
    system_prompt=system_prompt  # ✅ Bu parametre eklenmeli
)
```

**🔍 IMPACT**:
- ❌ Ecostar Tool: Knowledge base bilgileri LLM'e ulaşmıyor
- ❌ Google Tool: Domain-specific instructions çalışmıyor
- ❌ Gmail Tool: Email context aktarılamıyor
- ❌ Tüm custom plugin'ler: System prompt'ları ignore ediliyor

**📋 ÖRNEK HATA**:
```
Query: "Ecostar ne zaman kuruldu?"
System Prompt: "Ecostar 1967'de kuruldu..." (knowledge base'den)
LLM Response: "Ecostar 2000 yılında kuruldu"  ❌ YANLIŞ (system prompt kullanılmadı)
Expected: "Ecostar 1967 yılında kuruldu" ✅ DOĞRU
```

**🎯 ACTION ITEMS**:
1. ✅ Ecostar demo için workaround yapıldı: `ecostar_api.py` direkt OpenAI kullanıyor
2. ❌ `application_orchestrator.py` düzeltilmeli (kalıcı çözüm)
3. ❌ `llm_service.generate_text()` metodunun signature'ını kontrol et
4. ❌ Test: Gmail, Google, diğer plugin'lerin system prompt'ları çalışıyor mu?

**⚠️ WORKAROUND (Ecostar Demo)**:
- `/home/ahmet/Ecostar/ecostar-chatbot-demo/ecostar_api.py`
- Direkt OpenAI client ile system prompt kullanılıyor
- MetisAgent orchestrator bypass ediliyor
- Bu TEMPORARY çözüm, MetisAgent fix edilmeli

**🔧 RELATED FILES**:
- `/home/ahmet/MetisAgent/MetisAgent3/core/orchestrator/application_orchestrator.py:1128-1149`
- `/home/ahmet/MetisAgent/MetisAgent3/core/services/llm_service.py` (generate_text metodu)
- `/home/ahmet/Ecostar/ecostar-chatbot-demo/ecostar_api.py` (workaround)

---