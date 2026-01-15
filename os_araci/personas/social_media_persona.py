# personas/social_media_persona.py - Tam kod
import asyncio
import logging
import time
import json
import os
from typing import Dict, Any, List, Optional, Union
from os_araci.personas.persona_agent import PersonaAgent
from os_araci.a2a_protocol.message import A2AMessage

logger = logging.getLogger(__name__)

class SocialMediaPersona(PersonaAgent):
    """Sosyal medya içerik oluşturma ve yönetme için özelleştirilmiş persona"""
    
    def __init__(self, 
                persona_id: str, 
                name: str,
                description: str,
                supported_platforms: List[str] = None,
                content_tone: str = "professional",
                default_language: str = "tr",
                max_posts_per_day: int = 15,
                content_preferences: Dict[str, Any] = None,
                **kwargs):
        
        # Ana sınıfın başlatıcısını çağır
        capabilities = ["content_creation", "image_generation", "content_scheduling", 
                       "hashtag_management", "trend_analysis", "audience_engagement", 
                       "task_execution", "ai_image_generation"]
        
        super().__init__(
            persona_id=persona_id,
            name=name,
            description=description,
            capabilities=capabilities,
            **kwargs
        )
        
        # Sosyal medya özellikleri
        self.supported_platforms = supported_platforms or ["instagram", "facebook", "linkedin", "twitter", "tiktok"]
        self.content_tone = content_tone
        self.default_language = default_language
        self.max_posts_per_day = max_posts_per_day
        self.content_preferences = content_preferences or {
            "use_emojis": True,
            "max_hashtags": 5,
            "preferred_media_ratio": 0.7,
            "audience_targeting": "professional"
        }
        
        # İçerik takibi
        self.post_history = []
        self.scheduled_posts = []
        self.content_drafts = {}
        
        # UX İyileştirmeleri için cache
        self.response_cache = {}
        self.last_analysis_time = 0
        
        # Hızlı yanıt şablonları
        self.quick_responses = {
            "greeting": [
                "Merhaba! Sosyal medya içeriği oluşturmak için buradayım. 🎨",
                "Hangi platform için içerik hazırlamak istiyorsun?",
                "Instagram, Facebook, LinkedIn veya Twitter'dan hangisini tercih edersin?"
            ],
            "platform_selected": [
                "Harika seçim! {platform} için mükemmel içerikler oluşturabiliriz.",
                "Bu platform için hangi tür içerik düşünüyorsun? (Görsel, video, carousel...)"
            ],
            "audience_question": [
                "Hedef kitlen kimler? (Örn: Genç yetişkinler, profesyoneller, anneler...)",
                "Bu içeriği kimlerin görmesini istiyorsun?"
            ],
            "content_theme": [
                "İçeriğin ana teması nedir?",
                "Hangi konuda bir şeyler paylaşmak istiyorsun?"
            ],
            "completion_ready": [
                "✅ Harika! Artık postu oluşturmaya hazırız.",
                "Toplanan bilgilerle mükemmel bir post hazırlayabilirim."
            ]
        }
        
        # Post üretim adımları - iş akışı
        self.workflow_steps = [
            {
                "step_id": "briefing",
                "name": "Brifing",
                "description": "Amacı, hedef kitleyi, ana mesajı ve platformları tanımlama",
                "required_inputs": ["purpose", "target_audience", "main_message", "platforms"],
                "responsible_roles": ["Müşteri", "Marka Yöneticisi", "Pazarlama Ekibi", "Stratejist"]
            },
            {
                "step_id": "creative_idea",
                "name": "Yaratıcı Fikir Üretimi",
                "description": "Gönderi türünü, konsepti, tonu ve görselleri belirleme",
                "required_inputs": ["post_type", "concept", "tone", "visual_ideas", "formats"],
                "responsible_roles": ["Sosyal Medya Uzmanı", "Yazar", "Sanat Yönetmeni"]
            },
            {
                "step_id": "post_content",
                "name": "Post İçeriği",
                "description": "Gönderi başlığı/mesajı yazma, video senaryosu hazırlama, görsel tanımlama",
                "required_inputs": ["post_title", "post_message", "video_script", "visual_description"],
                "responsible_roles": ["Yazar", "İçerik Yöneticisi", "Yaratıcı Ekip"]
            },
            {
                "step_id": "sharing_content",
                "name": "Paylaşım İçeriği",
                "description": "Paylaşım metnini yazma, emojileri ve hashtagleri ekleme",
                "required_inputs": ["share_text", "emojis", "hashtags"],
                "responsible_roles": ["Sosyal Medya Uzmanı", "İçerik Yöneticisi"]
            },
            {
                "step_id": "visual_production",
                "name": "Görsel Prodüksiyon",
                "description": "Statik post bileşenlerini tasarlama, video planlama, kurgu yapma",
                "required_inputs": ["static_designs", "video_plan", "subtitles"],
                "responsible_roles": ["SM Tasarımcısı", "Motion Designer"]
            },
            {
                "step_id": "approval",
                "name": "Onay",
                "description": "Brif ve yönlendirmelere uygunluğu kontrol etme, müşteri onayı alma",
                "required_inputs": ["validation_points", "client_approval"],
                "responsible_roles": ["SM Uzmanı", "Kreatif Direktör", "Marka Yöneticisi", "Müşteri"]
            },
            {
                "step_id": "scheduling",
                "name": "Planlama ve Yayınlama",
                "description": "Programlama araçlarına giriş ve yükleme, zamanlama, kontrol",
                "required_inputs": ["publishing_tool", "schedule_time", "links_tags_check"],
                "responsible_roles": ["Sosyal Medya Uzmanı"]
            },
            {
                "step_id": "monitoring",
                "name": "İzleme ve Etkileşim",
                "description": "Yorumlara yanıt verme, uygunsuz içeriği denetleme, geri bildirimleri işaretleme",
                "required_inputs": ["response_strategy", "moderation_rules"],
                "responsible_roles": ["SM Uzmanı", "Müşteri Yöneticisi"]
            },
            {
                "step_id": "reporting",
                "name": "Raporlama ve Analiz",
                "description": "Ölçümleri değerlendirme, karşılaştırma, rapor hazırlama",
                "required_inputs": ["metrics", "benchmarks", "report_template"],
                "responsible_roles": ["SM Uzmanı", "Medya Planlama Uzmanı"]
            }
        ]
    
    async def _initialize(self) -> bool:
        """SocialMedia persona başlatma"""
        try:
            # Çalışma dizinini kontrol et/oluştur
            working_dir = self.settings.get("working_dir", "./social_media")
            if not os.path.exists(working_dir):
                os.makedirs(working_dir)
                logger.info(f"Çalışma dizini oluşturuldu: {working_dir}")
            
            # İçerik arşivi dizinini oluştur
            content_dir = os.path.join(working_dir, "content")
            if not os.path.exists(content_dir):
                os.makedirs(content_dir)
            
            # Cache dosyalarını yükle
            await self._load_cache_data()
            
            logger.info(f"Sosyal medya personası başlatıldı: {self.persona_id}")
            return True
        except Exception as e:
            logger.error(f"Sosyal medya personası başlatma hatası: {str(e)}")
            return False

    async def _load_cache_data(self):
        """Cache verilerini yükle"""
        try:
            working_dir = self.settings.get("working_dir", "./social_media")
            
            # Post geçmişini yükle
            history_file = os.path.join(working_dir, "post_history.json")
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.post_history = json.load(f)
                logger.info(f"{len(self.post_history)} adet post geçmişi yüklendi")
            
            # Planlanmış içerikleri yükle
            scheduled_file = os.path.join(working_dir, "scheduled_posts.json")
            if os.path.exists(scheduled_file):
                with open(scheduled_file, 'r', encoding='utf-8') as f:
                    self.scheduled_posts = json.load(f)
                logger.info(f"{len(self.scheduled_posts)} adet planlanmış post yüklendi")
            
            # Taslakları yükle
            drafts_file = os.path.join(working_dir, "content_drafts.json")
            if os.path.exists(drafts_file):
                with open(drafts_file, 'r', encoding='utf-8') as f:
                    self.content_drafts = json.load(f)
                logger.info(f"{len(self.content_drafts)} adet içerik taslağı yüklendi")
                
        except Exception as e:
            logger.warning(f"Cache verileri yüklenirken hata: {str(e)}")

    async def _shutdown(self) -> bool:
        """Persona kapanırken çağrılır"""
        try:
            await self._save_data_async()
            logger.info(f"Sosyal medya personası verileri kaydedildi: {self.persona_id}")
            return True
        except Exception as e:
            logger.error(f"Sosyal medya personası verileri kaydedilirken hata: {str(e)}")
            return False

    async def _save_data_async(self):
        """Verileri asenkron kaydet"""
        try:
            working_dir = self.settings.get("working_dir", "./social_media")
            
            # Post geçmişini kaydet
            history_file = os.path.join(working_dir, "post_history.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.post_history, f, ensure_ascii=False, indent=2)
            
            # Planlanmış içerikleri kaydet
            scheduled_file = os.path.join(working_dir, "scheduled_posts.json")
            with open(scheduled_file, 'w', encoding='utf-8') as f:
                json.dump(self.scheduled_posts, f, ensure_ascii=False, indent=2)
            
            # Taslakları kaydet
            drafts_file = os.path.join(working_dir, "content_drafts.json")
            with open(drafts_file, 'w', encoding='utf-8') as f:
                json.dump(self.content_drafts, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Veri kaydetme hatası: {str(e)}")
        
    def format_conversation_history(self, conversation_history, limit=3):
        """Konuşma geçmişini formatlayarak string olarak döndürür"""
        messages = []
        if conversation_history:
            for item in conversation_history[-limit:]:
                if item.get('role') in ['assistant', 'user']:
                    # Mesajları kısalt
                    message = item['message'][:100] + "..." if len(item['message']) > 100 else item['message']
                    messages.append(f"- {item['role']}: {message}")
        return "\n".join(messages)

    async def handle_chat_request(self, message: A2AMessage) -> None:
        """Chat isteğini doğal dil anlamasıyla işleyen LLM odaklı yaklaşım."""
        try:
            user_message = message.content.get('message', '')
            user_id = message.content.get('user_id', 'default')
            
            # Memory'den stored context'i al
            stored_context = await self._get_stored_context(user_id)
            logger.info(f"🔍 CONTEXT DEBUG - User: {user_id}, Stored: {stored_context}")
            
            # Hızlı yanıt kontrolü
            quick_response = await self._check_quick_response(user_message)
            if quick_response:
                await self._send_quick_reply(message, quick_response)
                return
            
            # Aktif post taslağını bul veya oluştur
            current_post_id = await self._get_or_create_draft(user_message, stored_context)
            draft = self.content_drafts[current_post_id]
            
            # user_id'yi draft'a ekle
            draft['user_id'] = user_id
            
            # Mesaj geçmişini güncelle
            self._update_conversation_history(draft, user_message)
            
            # LLM analizini yap (cache kontrolü ile)
            current_time = time.time()
            cache_key = f"{current_post_id}_{hash(user_message)}"
            
            if (cache_key in self.response_cache and 
                current_time - self.response_cache[cache_key]['timestamp'] < 300):  # 5 dakika cache
                
                # Cache'den yanıt al
                analysis_result = self.response_cache[cache_key]['response']
                logger.info("Cache'den yanıt alındı")
                
            else:
                # Yeni LLM analizi
                analysis_result = await self._analyze_with_llm(draft, user_message)
                
                # Cache'e kaydet
                self.response_cache[cache_key] = {
                    'response': analysis_result,
                    'timestamp': current_time
                }
            
            # Context güncellemelerini uygula
            context_updates = await self._apply_analysis_results(draft, analysis_result)
            
            # Context'i memory'ye kaydet/güncelle
            if context_updates:
                await self._update_context(user_id, context_updates)
                logger.info(f"💾 CONTEXT SAVE - User: {user_id}, Updates: {context_updates}")
            
            # Yanıt gönder
            await self._send_chat_reply(message, analysis_result, context_updates)
            
        except Exception as e:
            logger.error(f"handle_chat_request hatası: {str(e)}")
            await self._send_error_reply(message, str(e))

    async def _check_quick_response(self, user_message: str) -> Optional[str]:
        """Platform-aware hızlı yanıt kontrolü"""
        message_lower = user_message.lower()
        
        # Platform detection for quick responses
        detected_platform = None
        platform_keywords = {
            'instagram': ['instagram', 'insta', 'ig', 'story', 'reel', 'igtv'],
            'linkedin': ['linkedin', 'profesyonel', 'professional', 'career', 'business'],
            'twitter': ['twitter', 'tweet', 'x.com', 'trending', 'thread'],
            'facebook': ['facebook', 'fb', 'community', 'group', 'event'],
            'tiktok': ['tiktok', 'viral', 'trend', 'challenge', 'duet']
        }
        
        for platform, keywords in platform_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_platform = platform
                break
        
        # Platform-specific quick responses
        platform_responses = {
            'instagram': {
                'greeting': "Merhaba! Instagram için görsel odaklı içerik oluşturmaya hazırım. 📸 Story, Reel, Feed Post - hangisi olsun?",
                'content_type': {
                    'story': "Instagram Story için harika! Hangi konuda story paylaşmak istiyorsun? (Behind-the-scenes, günlük yaşam, duyuru...)",
                    'reel': "Instagram Reel için mükemmel seçim! 🎬 Trending audio ile mi, orijinal içerik mi düşünüyorsun?",
                    'post': "Instagram feed postu için hazırım! 📱 Hangi türde post? (Fotoğraf, carousel, video post)",
                    'carousel': "Carousel post süper fikir! 🗂️ Kaç slayt düşünüyorsun? Hangi konuda bilgi vereceğiz?"
                }
            },
            'linkedin': {
                'greeting': "Merhaba! LinkedIn için profesyonel içerik oluşturmaya hazırım. 💼 Hangi sektörde ve konuda yazalım?",
                'content_type': {
                    'article': "LinkedIn makalesi harika fikir! 📝 Hangi profesyonel konuda expertise paylaşalım?",
                    'post': "LinkedIn postu için hazırım! 🚀 Thought leadership mi, industry insight mi, career advice mi?",
                    'professional': "Profesyonel içerik için mükemmel! 👔 Hedef kitlen kimler? (HR, Sales, Tech, Management...)"
                }
            },
            'twitter': {
                'greeting': "Merhaba! Twitter/X için real-time içerik oluşturmaya hazırım. ⚡ Hangi konuda tweet atalım?",
                'content_type': {
                    'tweet': "Twitter postu için hazırım! 🐦 280 karakterde etkili mesaj mı, yoksa thread mi?",
                    'thread': "Thread harika fikir! 🧵 Hangi konuyu detaylandıralım? Kaç tweet düşünüyorsun?",
                    'trending': "Trending topic'e katılalım! 📈 Hangi güncel konuya perspektif katmak istiyorsun?"
                }
            },
            'facebook': {
                'greeting': "Merhaba! Facebook için community odaklı içerik oluşturmaya hazırım. 👥 Hangi konuda paylaşım yapalım?",
                'content_type': {
                    'post': "Facebook postu için hazırım! 📢 Community engagement odaklı mı, yoksa bilgilendirici mi?",
                    'event': "Facebook event için süper! 🎉 Hangi türde etkinlik organize ediyorsun?",
                    'group': "Grup paylaşımı için mükemmel! 👫 Hangi community'de paylaşacağız?"
                }
            },
            'tiktok': {
                'greeting': "Merhaba! TikTok için viral içerik oluşturmaya hazırım. 🎵 Hangi trend'i takip edelim?",
                'content_type': {
                    'video': "TikTok videosu için harika! 📹 Educational content mi, entertainment mi, trend participation mı?",
                    'trend': "Trend takibi süper fikir! 🔥 Hangi viral challenge'ı adapt edelim?",
                    'duet': "Duet içeriği için mükemmel! 🎭 Hangi creator'ın hangi videosuna response verelim?"
                }
            }
        }
        
        # Greeting kontrolü - platform-aware
        greetings = ["merhaba", "selam", "hello", "hi", "hey", "merhabalar"]
        if any(greeting in message_lower for greeting in greetings):
            if detected_platform:
                return platform_responses[detected_platform]['greeting']
            else:
                return "Merhaba! Sosyal medya içeriği oluşturmak için buradayım. 🎨 Hangi platform için başlayalım? (Instagram, LinkedIn, Twitter, Facebook, TikTok)"
        
        # Platform selection response
        if detected_platform:
            return platform_responses[detected_platform]['greeting']
        
        # Content type detection within platform context
        if detected_platform:
            platform_content_types = platform_responses[detected_platform]['content_type']
            for content_type, response in platform_content_types.items():
                if content_type in message_lower:
                    return response
        
        # General content type responses
        content_type_keywords = {
            'video': "Video içeriği için harika! 🎬 Hangi platform için hazırlayalım?",
            'photo': "Fotoğraf içeriği süper! 📸 Hangi style düşünüyorsun?",
            'carousel': "Carousel post mükemmel seçim! 🗂️ Hangi konuda bilgi aktaralım?",
            'story': "Story içeriği için hazırım! ⏰ Hangi platformda paylaşacağız?",
            'reel': "Reel içeriği harika! 🎵 Instagram için mi?",
            'post': "Post hazırlığı için buradayım! 📝 Hangi platform için yazalım?"
        }
        
        for keyword, response in content_type_keywords.items():
            if keyword in message_lower:
                return response
        
        # Audience targeting detection
        audience_keywords = ['hedef kitle', 'audience', 'target', 'kimler', 'yaş grubu', 'demographic']
        if any(keyword in message_lower for keyword in audience_keywords):
            return "Hedef kitle belirleme süper! 🎯 Hangi yaş grubu ve demografiye odaklanıyoruz? (Örn: 18-25 genç yetişkinler, 25-35 profesyoneller...)"
        
        # Engagement tactics
        engagement_keywords = ['engagement', 'etkileşim', 'like', 'comment', 'share', 'viral']
        if any(keyword in message_lower for keyword in engagement_keywords):
            return "Engagement artırma stratejileri için buradayım! 🚀 Hangi platform için engagement taktikleri geliştirelim?"
        
        # Hashtag related
        hashtag_keywords = ['hashtag', 'tag', 'etiket', '#']
        if any(keyword in message_lower for keyword in hashtag_keywords):
            return "Hashtag stratejisi için mükemmel! #️⃣ Hangi platform için ve hangi konuda hashtag önerileri hazırlayalım?"
        
        # Trend related
        trend_keywords = ['trend', 'trending', 'viral', 'popüler', 'gündem']
        if any(keyword in message_lower for keyword in trend_keywords):
            return "Trend takibi için buradayım! 📈 Hangi platformdaki trendleri takip etmek istiyorsun?"
        
        return None

    async def _get_or_create_draft(self, user_message: str = "", stored_context: Dict[str, Any] = None) -> str:
        """Aktif taslağı al veya yeni oluştur - memory context ile entegre"""
        if stored_context is None:
            stored_context = {}
            
        # Sıfırlama komutları kontrolü
        reset_phrases = ["yeni post", "baştan başla", "yeni bir post", "sıfırla", "yeniden başla", "post hazırla"]
        should_reset = any(phrase in user_message.lower() for phrase in reset_phrases)
        
        if not should_reset:
            # Aktif taslak var mı kontrol et
            active_drafts = [
                post_id for post_id, draft in self.content_drafts.items()
                if draft.get('status') == 'active' and 
                   time.time() - draft.get('created_at', 0) < 7200  # 2 saat
            ]
            
            if active_drafts:
                # Mevcut draft'a stored context'i merge et
                draft = self.content_drafts[active_drafts[0]]
                if stored_context:
                    draft['post_data'].update(stored_context)
                    logger.info(f"Merged stored context into existing draft: {list(stored_context.keys())}")
                return active_drafts[0]
        
        # Yeni taslak oluştur
        post_id = f"post_{int(time.time())}"
        
        # Stored context'ten başlangıç verilerini al
        initial_post_data = {}
        if stored_context:
            # Context'ten platform ve workflow bilgilerini aktar
            if 'platform' in stored_context:
                initial_post_data['platform'] = stored_context['platform']
            if 'post_type' in stored_context:
                initial_post_data['post_type'] = stored_context['post_type']
            if 'target_audience' in stored_context:
                initial_post_data['target_audience'] = stored_context['target_audience']
            if 'tone' in stored_context:
                initial_post_data['tone'] = stored_context['tone']
            
            logger.info(f"Created new draft with stored context: {list(initial_post_data.keys())}")
        
        self.content_drafts[post_id] = {
            'created_at': time.time(),
            'status': 'active',
            'workflow_stage': 'initial',
            'conversation_history': [],
            'post_data': initial_post_data,
            'message_count': 0,
            'seen_values': {}
        }
        
        return post_id

    def _update_conversation_history(self, draft: Dict, user_message: str):
        """Konuşma geçmişini güncelle"""
        if 'conversation_history' not in draft:
            draft['conversation_history'] = []
        
        draft['conversation_history'].append({
            'role': 'user',
            'message': user_message,
            'timestamp': time.time()
        })
        
        draft['message_count'] = draft.get('message_count', 0) + 1
        
        # Geçmişi sınırla (performans için)
        if len(draft['conversation_history']) > 10:
            draft['conversation_history'] = draft['conversation_history'][-10:]

    def _get_platform_specific_prompts(self) -> Dict[str, Dict]:
        """Platform-specific prompt templates ve optimizasyon kuralları"""
        return {
            "instagram": {
                "characteristics": {
                    "visual_focus": True,
                    "max_caption_length": 2200,
                    "max_hashtags": 30,
                    "optimal_hashtags": "5-10",
                    "story_lifespan": "24 hours",
                    "post_types": ["feed_post", "story", "reel", "carousel", "igtv"],
                    "algorithm_factors": ["engagement_rate", "time_spent", "shares", "saves", "comments"],
                    "peak_times": ["11:00-13:00", "19:00-21:00"],
                    "content_pillars": ["educational", "entertaining", "inspirational", "promotional"]
                },
                "prompts": {
                    "analysis": """Instagram uzmanı olarak analiz et:
                    
                    PLATFORM ÖZELLİKLERİ:
                    - Görsel odaklı platform (fotoğraf/video öncelikli)
                    - Hashtag stratejisi kritik (5-10 optimal)
                    - Stories/Reels algoritma avantajı
                    - Engagement rate en önemli metrik
                    - Aesthetic tutarlılık şart
                    
                    CONTENT OPTIMIZATION:
                    - Hook ilk 3 saniyede yakalama
                    - User-generated content teşvik
                    - Behind-the-scenes içerik
                    - Carousel posts için storytelling
                    - Call-to-action save/share odaklı
                    
                    AUDIENCE BEHAVIOR:
                    - Mobile-first deneyim
                    - Visual aesthetic önemli
                    - Story interactions yüksek
                    - Discovery hashtag tabanlı""",
                    
                    "content_generation": """Instagram feed postu için optimize et:
                    
                    FORMAT REQUIREMENTS:
                    - Kare format (1080x1080) ideal
                    - İlk satır hook olmalı
                    - Caption max 2200 karakter
                    - 5-10 strategic hashtag
                    - CTA belirtilmeli
                    
                    ENGAGEMENT TACTICS:
                    - Soru sorarak comment teşvik
                    - Save-worthy content (listicle, tip)
                    - Share için relatable content
                    - Story cross-promotion
                    - Reels için trending audio
                    
                    IMAGE GENERATION:
                    - Instagram aesthetic öncelik
                    - Vibrant colors ve good lighting
                    - Brand identity consistent
                    - Mobile viewing optimized
                    - User-generated content style"""
                }
            },
            
            "linkedin": {
                "characteristics": {
                    "professional_focus": True,
                    "max_post_length": 3000,
                    "max_hashtags": 5,
                    "optimal_hashtags": "3-5",
                    "content_types": ["text_post", "article", "document", "video", "poll"],
                    "algorithm_factors": ["professional_relevance", "engagement_quality", "network_reach"],
                    "peak_times": ["08:00-10:00", "12:00-14:00", "17:00-18:00"],
                    "content_pillars": ["thought_leadership", "industry_insights", "career_advice", "company_updates"]
                },
                "prompts": {
                    "analysis": """LinkedIn uzmanı olarak profesyonel analiz yap:
                    
                    PLATFORM ÖZELLİKLERİ:
                    - B2B odaklı profesyonel network
                    - Thought leadership içerik değerli
                    - Industry insights ve career advice popüler
                    - Long-form content destekleniyor
                    - Professional credibility kritik
                    
                    CONTENT STRATEGY:
                    - Industry-specific konular
                    - Professional development
                    - Business insights ve trends
                    - Company culture ve values
                    - Career advancement tips
                    
                    ENGAGEMENT APPROACH:
                    - Professional discussion başlat
                    - Industry expertise göster
                    - Network değeri sağla
                    - Meaningful connections kur""",
                    
                    "content_generation": """LinkedIn postu için profesyonel optimize et:
                    
                    STRUCTURE:
                    - Professional headline
                    - Value-driven content
                    - Industry-relevant insights
                    - Call-to-professional-action
                    - 3-5 strategic hashtag
                    
                    TONE & STYLE:
                    - Professional ama approachable
                    - Industry expertise yansıt
                    - Data ve examples kullan
                    - Professional storytelling
                    - Network value sağla"""
                }
            },
            
            "twitter": {
                "characteristics": {
                    "real_time_focus": True,
                    "max_characters": 280,
                    "max_hashtags": 3,
                    "optimal_hashtags": "1-2",
                    "content_types": ["tweet", "thread", "reply", "quote_tweet", "space"],
                    "algorithm_factors": ["recency", "engagement_velocity", "trending_topics"],
                    "peak_times": ["09:00-10:00", "12:00-15:00", "17:00-18:00"],
                    "content_pillars": ["news_commentary", "real_time_updates", "conversation_starters", "quick_insights"]
                },
                "prompts": {
                    "analysis": """Twitter/X uzmanı olarak real-time analiz yap:
                    
                    PLATFORM ÖZELLİKLERİ:
                    - Real-time conversation hub
                    - 280 karakter limit
                    - Thread format güçlü
                    - Trending topics kritik
                    - News ve commentary odaklı
                    
                    CONTENT APPROACH:
                    - Güncel olaylarla bağlantı
                    - Quick insights ve hot takes
                    - Thread için story breakdown
                    - Community engagement
                    - Viral potential evaluation
                    
                    ENGAGEMENT TACTICS:
                    - Reply chain başlat
                    - Retweet ile reach artır
                    - Trending hashtag kullan
                    - Quick response ile recency kazan""",
                    
                    "content_generation": """Twitter/X postu için optimize et:
                    
                    FORMAT:
                    - 280 karakter max
                    - Punchy ve direct
                    - 1-2 hashtag max
                    - Thread potential var mı?
                    - Reply bait include et
                    
                    ENGAGEMENT:
                    - Hot take veya insight
                    - Question sorarak reply al
                    - Controversial ama respectful
                    - Retweet-worthy content
                    - Trending topic connection"""
                }
            },
            
            "facebook": {
                "characteristics": {
                    "community_focus": True,
                    "max_post_length": 63206,
                    "max_hashtags": 5,
                    "optimal_hashtags": "2-3",
                    "content_types": ["status", "photo", "video", "link", "event", "poll"],
                    "algorithm_factors": ["meaningful_interactions", "time_spent", "family_friends_priority"],
                    "peak_times": ["13:00-15:00", "19:00-21:00"],
                    "content_pillars": ["community_building", "family_content", "local_events", "group_discussions"]
                },
                "prompts": {
                    "analysis": """Facebook uzmanı olarak community-focused analiz yap:
                    
                    PLATFORM ÖZELLİKLERİ:
                    - Family ve friends öncelikli
                    - Group dynamics güçlü
                    - Local community odaklı
                    - Longer-form content destekleniyor
                    - Meaningful interaction algoritması
                    
                    CONTENT STRATEGY:
                    - Community building
                    - Family-friendly content
                    - Local relevance
                    - Group engagement
                    - Event ve gathering promotion
                    
                    ENGAGEMENT APPROACH:
                    - Discussion başlat
                    - Community value sağla
                    - Local connection kur
                    - Family-oriented content""",
                    
                    "content_generation": """Facebook postu için community optimize et:
                    
                    APPROACH:
                    - Community conversation başlat
                    - Local relevance dahil et
                    - Family-friendly tone
                    - Group engagement encourage
                    - Event/gathering promote
                    
                    FORMAT:
                    - Longer descriptive text
                    - Community question sor
                    - Local hashtag kullan
                    - Share-worthy family content
                    - Group cross-post potential"""
                }
            },
            
            "tiktok": {
                "characteristics": {
                    "video_only": True,
                    "max_duration": "10 minutes",
                    "optimal_duration": "15-60 seconds",
                    "max_caption": 2200,
                    "max_hashtags": 20,
                    "algorithm_factors": ["completion_rate", "engagement_rate", "trending_audio", "discover_optimization"],
                    "peak_times": ["18:00-24:00"],
                    "content_pillars": ["entertainment", "education", "trends", "challenges"]
                },
                "prompts": {
                    "analysis": """TikTok uzmanı olarak viral analiz yap:
                    
                    PLATFORM ÖZELLİKLERİ:
                    - Video-only platform
                    - Algorithm çok güçlü
                    - Trending audio kritik
                    - 15-60 saniye optimal
                    - Gen Z dominant audience
                    
                    VIRAL FACTORS:
                    - Hook ilk 3 saniye
                    - Trending audio kullan
                    - Challenge participation
                    - Quick cut editing
                    - Completion rate maximize
                    
                    CONTENT TYPES:
                    - Educational (90-second rule)
                    - Entertainment skits
                    - Trend participation
                    - Behind-the-scenes
                    - Day-in-the-life""",
                    
                    "content_generation": """TikTok video içeriği için viral optimize et:
                    
                    VIDEO STRUCTURE:
                    - 3-saniye hook
                    - Trending audio overlay
                    - Quick transitions
                    - Visual variety
                    - Strong ending CTA
                    
                    VIRAL ELEMENTS:
                    - Current trend adaptation
                    - Challenge participation
                    - Duet/stitch potential
                    - Hashtag challenge
                    - Educational value
                    
                    OPTIMIZATION:
                    - Mobile vertical format
                    - Text overlay minimal
                    - Captions engaging
                    - Discovery hashtag mix"""
                }
            }
        }

    async def _analyze_with_llm(self, draft: Dict, user_message: str) -> Dict:
        """Gelişmiş platform-specific LLM analizi"""
        try:
            # Memory manager'dan mevcut context'i al
            user_id = draft.get('user_id', 'default')
            stored_context = await self._get_stored_context(user_id)
            
            # Platform detection - önce stored context'ten kontrol et
            if stored_context.get('platform') and stored_context.get('post_type'):
                detected_platform = stored_context['platform']
                logger.info(f"Platform loaded from memory: {detected_platform}")
            else:
                detected_platform = self._detect_platform_from_context(draft, user_message)
                logger.info(f"Platform detected from context: {detected_platform}")
            
            platform_config = self._get_platform_specific_prompts().get(detected_platform, {})
            
            # Mevcut context
            current_stage = draft.get('workflow_stage', 'initial')
            post_data = draft.get('post_data', {})
            message_count = draft.get('message_count', 0)
            previous_messages = self.format_conversation_history(draft.get('conversation_history', []))
            
            # Platform-specific analysis prompt
            platform_prompt = platform_config.get('prompts', {}).get('analysis', 
                "Sosyal medya uzmanı olarak genel analiz yap.")
            
            if current_stage == 'review':
                # Platform-specific completion analysis
                analysis_prompt = f"""
                {platform_prompt}
                
                GÖREV: Toplanan bilgileri platform özelliklerine göre optimize edip tamamla.
                
                Platform: {detected_platform.title()}
                Platform Özellikleri: {json.dumps(platform_config.get('characteristics', {}), indent=2, ensure_ascii=False)}
                
                Toplanan Bilgiler: {json.dumps(post_data, indent=2, ensure_ascii=False)}
                Kullanıcı Mesajı: "{user_message}"
                
                PLATFORM-SPECIFIC OPTIMIZATION:
                - Content format optimization
                - Hashtag strategy
                - Engagement tactics
                - Algorithm compatibility
                - Audience behavior alignment
                
                JSON Response:
                {{
                    "summary": "Platform-optimized content summary",
                    "missing_fields": ["eksik_alan"],
                    "post_description": "Platform-specific post description", 
                    "caption": "Platform-optimized caption",
                    "hashtags": ["#platform_specific_tags"],
                    "content_optimization": {{
                        "format_suggestions": [],
                        "engagement_tactics": [],
                        "algorithm_tips": []
                    }},
                    "platform_compliance": {{
                        "character_limit_ok": true,
                        "hashtag_count_ok": true,
                        "format_appropriate": true
                    }},
                    "is_complete": true/false,
                    "stage": "review",
                    "image_prompt": "Platform-optimized AI image prompt",
                    "posting_recommendations": {{
                        "optimal_time": "Best posting time",
                        "content_type": "Recommended content type",
                        "engagement_prediction": "High/Medium/Low"
                    }}
                }}
                """
            else:
                # Platform-aware information gathering
                analysis_prompt = f"""
                {platform_prompt}
                
                GÖREV: Kullanıcı mesajını platform özelliklerine göre analiz et.
                
                Platform: {detected_platform.title()}
                Platform Limits: {json.dumps(platform_config.get('characteristics', {}), indent=2, ensure_ascii=False)}
                
                Mevcut Bilgiler: {json.dumps(post_data, ensure_ascii=False)}
                Kullanıcı Mesajı: "{user_message}"
                Mesaj Sayısı: {message_count}
                Konuşma Geçmişi: {previous_messages}
                
                PLATFORM-AWARE ANALYSIS:
                - Extract platform-relevant information
                - Suggest platform-specific optimizations
                - Guide towards platform best practices
                - Detect content type suitability
                - Recommend engagement strategies
                
                JSON Response:
                {{
                    "detected_fields": {{}}, // Platform-optimized field extraction
                    "response": "Platform-aware natural response",
                    "next_question": "Platform-specific follow-up question",
                    "progress": {{"stage": "{current_stage}", "percentage": 0}},
                    "context_updates": {{}},
                    "platform_suggestions": {{
                        "content_type": "Recommended content type for platform",
                        "format_tips": ["Platform-specific formatting tips"],
                        "hashtag_strategy": "Platform hashtag approach",
                        "optimization_tips": ["Platform optimization suggestions"]
                    }},
                    "trusts_creativity": false,
                    "is_completion_request": false,
                    "platform_compliance_check": {{
                        "character_count": 0,
                        "hashtag_count": 0,
                        "format_suitable": true
                    }}
                }}
                """
            
            # Enhanced system prompt
            system_prompt = f"""Sen {detected_platform.title()} uzmanı bir sosyal medya profesyonelisin.
            
            Platform Expertise:
            - {detected_platform.title()} algoritması ve best practices
            - Platform-specific content optimization
            - Audience behavior patterns
            - Engagement strategies
            - Format requirements
            
            Response Format: Sadece valid JSON yanıt ver, açıklama yapma."""
            
            # LLM çağrısı
            response = self.llm_tool.generate_text(
                prompt=analysis_prompt,
                system_prompt=system_prompt,
                provider="openai",
                model=self.settings.get('llm_model', 'gpt-4o-mini'),
                temperature=0.2  # Biraz daha yaratıcı ama tutarlı
            )
            
            response_text = response.get("text", "") if isinstance(response, dict) else str(response)
            
            # JSON parse et
            try:
                if "```json" in response_text:
                    json_text = response_text.split("```json")[1].split("```")[0].strip()
                else:
                    json_text = response_text.strip()
                
                parsed_response = json.loads(json_text)
                
                # Platform compliance validation
                parsed_response = await self._validate_platform_compliance(
                    parsed_response, detected_platform, platform_config
                )
                
                return parsed_response
                
            except Exception as parse_error:
                logger.warning(f"JSON parse hatası: {parse_error}")
                # Fallback yanıt
                return await self._generate_fallback_response(current_stage, detected_platform)
                
        except Exception as e:
            logger.error(f"Platform-specific LLM analiz hatası: {str(e)}")
            return await self._generate_error_response(current_stage)

    def _detect_platform_from_context(self, draft: Dict, user_message: str) -> str:
        """Context'ten platform tespit et"""
        # Önce draft'tan platform bilgisi al
        if 'post_data' in draft and 'platforms' in draft['post_data']:
            platforms = draft['post_data']['platforms']
            if isinstance(platforms, list) and platforms:
                return platforms[0].lower()
            elif isinstance(platforms, str):
                return platforms.lower()
        
        # Mesajdan platform tespit et
        message_lower = user_message.lower()
        platform_keywords = {
            'instagram': ['instagram', 'insta', 'ig', 'story', 'reel', 'igtv'],
            'linkedin': ['linkedin', 'profesyonel', 'professional', 'career', 'business'],
            'twitter': ['twitter', 'tweet', 'x.com', 'trending', 'thread'],
            'facebook': ['facebook', 'fb', 'community', 'group', 'event'],
            'tiktok': ['tiktok', 'viral', 'trend', 'challenge', 'duet']
        }
        
        for platform, keywords in platform_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return platform
        
        # Default platform
        return 'instagram'

    async def _validate_platform_compliance(self, response: Dict, platform: str, config: Dict) -> Dict:
        """Platform compliance kontrolü ve optimizasyon"""
        try:
            characteristics = config.get('characteristics', {})
            
            # Caption uzunluk kontrolü
            if 'caption' in response:
                max_length = characteristics.get('max_caption_length', 2200)
                if len(response['caption']) > max_length:
                    response['caption'] = response['caption'][:max_length-10] + "..."
                    response['platform_compliance_check'] = response.get('platform_compliance_check', {})
                    response['platform_compliance_check']['caption_truncated'] = True
            
            # Hashtag count kontrolü
            if 'hashtags' in response:
                max_hashtags = characteristics.get('max_hashtags', 30)
                if len(response['hashtags']) > max_hashtags:
                    response['hashtags'] = response['hashtags'][:max_hashtags]
                    response['platform_compliance_check'] = response.get('platform_compliance_check', {})
                    response['platform_compliance_check']['hashtag_truncated'] = True
            
            # Platform-specific optimizations
            if platform == 'instagram' and 'content_optimization' in response:
                if 'format_suggestions' not in response['content_optimization']:
                    response['content_optimization']['format_suggestions'] = [
                        "Kare format (1080x1080) kullan",
                        "İlk 3 saniyede hook yakala",
                        "Carousel için storytelling uygula"
                    ]
            
            elif platform == 'linkedin' and 'platform_suggestions' in response:
                if 'professional_tone' not in response['platform_suggestions']:
                    response['platform_suggestions']['professional_tone'] = True
                    response['platform_suggestions']['industry_relevance'] = "High"
            
            elif platform == 'twitter' and 'detected_fields' in response:
                # Twitter için karakter optimizasyonu
                if 'caption' in response and len(response['caption']) > 280:
                    response['platform_suggestions'] = response.get('platform_suggestions', {})
                    response['platform_suggestions']['thread_recommendation'] = True
            
            return response
            
        except Exception as e:
            logger.error(f"Platform compliance validation error: {str(e)}")
            return response

    async def _generate_fallback_response(self, stage: str, platform: str) -> Dict:
        """Fallback response generator"""
        platform_questions = {
            'instagram': "Instagram için hangi tür içerik düşünüyorsun? (Story, Reel, Feed Post)",
            'linkedin': "LinkedIn için profesyonel hangi konuda paylaşım yapmak istiyorsun?",
            'twitter': "Twitter/X için hangi konuda tweet atmak istiyorsun?",
            'facebook': "Facebook için community'nle ne paylaşmak istiyorsun?",
            'tiktok': "TikTok için hangi trend'i takip etmek istiyorsun?"
        }
        
        return {
            "detected_fields": {},
            "response": f"Mesajınızı aldım. {platform.title()} için içerik hazırlayalım.",
            "next_question": platform_questions.get(platform, "Daha fazla detay verebilir misiniz?"),
            "progress": {"stage": stage, "percentage": 10},
            "context_updates": {"platform": platform},
            "platform_suggestions": {
                "content_type": "Henüz belirlenmedi",
                "format_tips": [f"{platform.title()} için optimize edilecek"],
                "optimization_tips": ["Platform-specific öneriler gelecek"]
            }
        }

    async def _generate_error_response(self, stage: str) -> Dict:
        """Error response generator"""
        return {
            "detected_fields": {},
            "response": "Anlayamadım, tekrar açıklayabilir misiniz?",
            "next_question": "Hangi platform için içerik hazırlamak istiyorsunuz?",
            "progress": {"stage": stage, "percentage": 0},
            "context_updates": {},
            "error": "LLM analysis failed"
        }

    async def _apply_analysis_results(self, draft: Dict, analysis: Dict) -> Dict:
        """Analiz sonuçlarını draft'a uygula"""
        context_updates = {}
        
        # Tespit edilen alanları ekle
        if "detected_fields" in analysis and analysis["detected_fields"]:
            draft['post_data'].update(analysis["detected_fields"])
            context_updates.update(analysis["detected_fields"])
        
        # İlerleme güncellemesi
        if "progress" in analysis:
            progress = analysis["progress"]
            if "stage" in progress:
                draft['workflow_stage'] = progress["stage"]
                context_updates['current_step'] = progress["stage"]
        
        # Context güncellemeleri
        if "context_updates" in analysis:
            context_updates.update(analysis["context_updates"])
        
        # Yaratıcı öneriler
        if analysis.get("trusts_creativity") and "creative_suggestions" in analysis:
            draft['post_data'].update(analysis["creative_suggestions"])
            context_updates.update(analysis["creative_suggestions"])
        
        # Workflow adımı geçişi kontrolü
        message_count = draft.get('message_count', 0)
        current_stage = draft.get('workflow_stage', 'initial')
        
        if message_count >= 2:
            if current_stage == 'initial' and len(draft['post_data']) >= 2:
                draft['workflow_stage'] = 'planning'
                context_updates['current_step'] = 'planning'
            elif current_stage == 'planning' and len(draft['post_data']) >= 4:
                draft['workflow_stage'] = 'details'
                context_updates['current_step'] = 'details'
            elif current_stage == 'details' and len(draft['post_data']) >= 6:
                draft['workflow_stage'] = 'review'
                context_updates['current_step'] = 'review'
            elif analysis.get("is_completion_request"):
                draft['workflow_stage'] = 'review'
                context_updates['current_step'] = 'review'
        
        return context_updates

    async def _send_quick_reply(self, original_message: A2AMessage, response_text: str):
        """Hızlı yanıt gönder"""
        reply = original_message.create_reply(
            content={
                "response": response_text,
                "metadata": {
                    "persona_id": self.persona_id,
                    "response_type": "quick",
                    "timestamp": time.time()
                }
            },
            message_type="chat.response"
        )
        
        await self._registry.send_message(reply)

    async def _send_chat_reply(self, original_message: A2AMessage, analysis: Dict, context_updates: Dict):
        """Chat yanıtı gönder"""
        response_text = analysis.get("response", "Mesajınızı aldım.")
        
        reply = original_message.create_reply(
            content={
                "response": response_text,
                "context_updates": context_updates,
                "metadata": {
                    "persona_id": self.persona_id,
                    "progress": analysis.get("progress", {}),
                    "timestamp": time.time()
                }
            },
            message_type="chat.response"
        )
        
        await self._registry.send_message(reply)

    async def _send_error_reply(self, original_message: A2AMessage, error_msg: str):
        """Hata yanıtı gönder"""
        reply = original_message.create_reply(
            content={
                "response": "Üzgünüm, bir şeyler yanlış gitti. Tekrar deneyebilir miyiz?",
                "error": error_msg,
                "metadata": {
                    "persona_id": self.persona_id,
                    "timestamp": time.time()
                }
            },
            message_type="chat.response"
        )
        
        await self._registry.send_message(reply)

    def _normalize_post_fields(self, post_data):
        """Post verilerini standardize eder"""
        normalized_data = post_data.copy()
        
        # Platform standardizasyonu
        if "platforms" in normalized_data:
            platform = normalized_data["platforms"].lower()
            if "insta" in platform:
                normalized_data["platforms"] = "Instagram"
            elif "face" in platform:
                normalized_data["platforms"] = "Facebook"
            elif "link" in platform:
                normalized_data["platforms"] = "LinkedIn"
            elif "twit" in platform or "x" == platform:
                normalized_data["platforms"] = "Twitter"
        
        # Post türü standardizasyonu
        if "post_type" in normalized_data:
            post_type = normalized_data["post_type"].lower()
            if "foto" in post_type or "fotoğraf" in post_type or "resim" in post_type or "görsel" in post_type:
                normalized_data["post_type"] = "image"
            elif "video" in post_type or "reel" in post_type:
                normalized_data["post_type"] = "video"
            elif "carousel" in post_type or "galeri" in post_type or "albüm" in post_type:
                normalized_data["post_type"] = "carousel"
            elif "story" in post_type or "hikaye" in post_type:
                normalized_data["post_type"] = "story"
        
        # Emoji kullanımı standardizasyonu
        if "use_emojis" in normalized_data:
            use_emojis = str(normalized_data["use_emojis"]).lower()
            if use_emojis in ["evet", "yes", "true", "1", "kullan", "kullanılsın"]:
                normalized_data["use_emojis"] = True
            elif use_emojis in ["hayır", "no", "false", "0", "kullanma", "kullanılmasın"]:
                normalized_data["use_emojis"] = False
        
        return normalized_data

    def generate_image_prompt(self, post_data):
        """Post verilerine dayanarak platform-specific görsel oluşturmak için AI prompt oluşturur"""
        platform = post_data.get('platform', 'instagram')
        theme = post_data.get('content_theme', '')
        visual_ideas = post_data.get('visual_ideas', '')
        target_audience = post_data.get('target_audience', '')
        tone = post_data.get('tone', 'professional')
        post_type = post_data.get('post_type', 'image')
        main_message = post_data.get('main_message', '')
        
        # Platform-specific temel prompt
        platform_prompts = {
            'instagram': "Create a stunning Instagram post",
            'linkedin': "Create a professional LinkedIn post visual",
            'twitter': "Create an engaging Twitter post image",
            'facebook': "Create a community-friendly Facebook post visual",
            'tiktok': "Create a viral TikTok video thumbnail"
        }
        
        prompt = platform_prompts.get(platform.lower(), "Create a social media post")
        
        # Visual ideas varsa ekle
        if visual_ideas:
            prompt += f" showing {visual_ideas}"
        elif main_message:
            prompt += f" representing the concept: {main_message}"
        
        # Tema varsa ekle
        if theme:
            prompt += f", with theme: {theme}"
        
        # Hedef kitle varsa ekle
        if target_audience:
            prompt += f", appealing to {target_audience}"
        
        # Ton varsa ekle
        if tone:
            prompt += f", in a {tone} style"
        
        # Platform-specific kalite belirteçleri
        platform_quality = {
            'instagram': ", high quality, professional photography, vibrant colors, Instagram aesthetic",
            'linkedin': ", professional, business-appropriate, corporate design, clean layout",
            'twitter': ", eye-catching, shareable, trending visual style, modern design",
            'facebook': ", community-friendly, family-appropriate, engaging visual",
            'tiktok': ", trendy, viral potential, Gen Z aesthetic, mobile-optimized"
        }
        
        prompt += platform_quality.get(platform.lower(), ", high quality, professional design")
        
        return prompt

    async def generate_smart_image_prompt(self, post_data):
        """LLM ile akıllı görsel prompt oluştur"""
        try:
            platform = post_data.get('platform', 'instagram')
            detected_platform = self._detect_platform_from_context({'post_data': post_data}, '')
            platform_config = self._get_platform_specific_prompts().get(detected_platform, {})
            
            # LLM ile akıllı prompt oluştur
            llm_prompt = f"""
            Sosyal medya görseli için optimized AI image prompt oluştur.
            
            Platform: {platform}
            Post Verisi: {json.dumps(post_data, ensure_ascii=False)}
            Platform Özellikleri: {json.dumps(platform_config.get('characteristics', {}), ensure_ascii=False)}
            
            Lütfen aşağıdaki kriterlere uygun bir AI image prompt oluştur:
            - Platform'un görsel standartlarına uygun
            - Hedef kitleye hitap eden
            - Markalama ve engagement optimized
            - AI image generator için net ve detaylı
            
            Sadece prompt metnini ver, açıklama yapma.
            """
            
            if hasattr(self, 'llm_tool') and self.llm_tool:
                response = self.llm_tool.generate_text(
                    prompt=llm_prompt,
                    system_prompt="Sen sosyal medya görsel uzmanısın. AI image prompt uzmanısın.",
                    provider="openai",
                    model=self.settings.get('llm_model', 'gpt-4o-mini'),
                    temperature=0.7
                )
                
                if isinstance(response, dict) and 'text' in response:
                    return response['text'].strip()
                else:
                    return str(response).strip() if response else self.generate_image_prompt(post_data)
            else:
                return self.generate_image_prompt(post_data)
                
        except Exception as e:
            logger.error(f"Smart image prompt generation error: {str(e)}")
            return self.generate_image_prompt(post_data)

    async def generate_chat_response(self, message: str) -> str:
        """Hızlı chat yanıtı oluştur"""
        try:
            # Basit pattern matching için hızlı kontrol
            message_lower = message.lower()
            
            if any(word in message_lower for word in ["merhaba", "selam", "hello"]):
                return "Merhaba! Sosyal medya içeriği oluşturmak için buradayım. Hangi platform için içerik hazırlamak istiyorsun?"
            
            if any(word in message_lower for word in ["instagram", "facebook", "linkedin", "twitter"]):
                return "Harika seçim! Bu platform için ne tür bir içerik düşünüyorsun?"
            
            # Fallback LLM yanıtı
            response = self.llm_tool.generate_text(
                prompt=f"Sosyal medya uzmanı olarak kısa yanıt ver: {message}",
                system_prompt="Sosyal medya uzmanı olarak samimi ve yardımsever ol.",
                provider="openai",
                model=self.settings.get('llm_model', 'gpt-4o-mini'),
                temperature=0.3
            )
            
            if isinstance(response, dict) and 'text' in response:
                return response['text']
            else:
                return str(response) if response else "Size nasıl yardımcı olabilirim?"
                    
        except Exception as e:
            logger.error(f"Chat yanıtı oluşturma hatası: {str(e)}")
            return f"Üzgünüm, bir hata oluştu. Size nasıl yardımcı olabilirim?"

    # Görev işleme metodları
    async def _handle_social_media_task(self, task: Dict[str, Any], context: Dict[str, Any], original_message: A2AMessage) -> None:
        """Sosyal medya görevlerini işle"""
        start_time = time.time()
        task_id = task.get("id") or original_message.message_id
        task_name = task.get("name", "Unnamed Task")
        action = task.get("action", "")
        
        try:
            # Metrikler
            self.task_metrics["total_tasks"] += 1
            self.task_metrics["last_task_time"] = start_time
            
            result = None
            
            # Görev aksiyonuna göre işle
            if action == "create_post":
                result = await self._action_create_post(task, context)
            elif action == "schedule_post":
                result = await self._action_schedule_post(task, context)
            elif action == "analyze_engagement":
                result = await self._action_analyze_engagement(task, context)
            elif action == "generate_hashtags":
                result = await self._action_generate_hashtags(task, context)
            elif action == "generate_image":
                result = await self._action_generate_image(task, context)
            elif action == "create_content_plan":
                result = await self._action_create_content_plan(task, context)
            elif action == "process_workflow_step":
                result = await self._action_process_workflow_step(task, context)
            else:
                # Desteklenmeyen aksiyon
                raise ValueError(f"Unsupported social media action: {action}")
            
            # Başarılı yanıt
            execution_time = time.time() - start_time
            
            # Metrikleri güncelle
            self.task_metrics["successful_tasks"] += 1
            # Ortalama yanıt süresini güncelle
            total_tasks = self.task_metrics["total_tasks"]
            current_avg = self.task_metrics["average_response_time"]
            new_avg = current_avg * (total_tasks - 1) / total_tasks + execution_time / total_tasks
            self.task_metrics["average_response_time"] = new_avg
            
            # Görev geçmişine ekle
            task_history_entry = {
                "task_id": task_id,
                "task_name": task_name,
                "action": action,
                "start_time": start_time,
                "execution_time": execution_time,
                "status": "success"
            }
            
            if len(self.post_history) >= 100:
                self.post_history.pop(0)  # En eski kaydı sil
            self.post_history.append(task_history_entry)
            
            # Yanıt mesajı
            reply = original_message.create_reply(
                content={
                    "status": "success",
                    "task_id": task_id,
                    "result": result,
                    "execution_time": execution_time,
                    "context_updates": context  # Context güncellemelerini ilet
                },
                message_type="task.response"
            )
            await self._registry.send_message(reply)
            logger.info(f"Sosyal medya görevi başarıyla tamamlandı: {task_id} - {action} ({execution_time:.2f}s)")
            
        except Exception as e:
            # Hatalı yanıt
            execution_time = time.time() - start_time
            
            # Metrikleri güncelle
            self.task_metrics["failed_tasks"] += 1
            
            # Görev geçmişine ekle
            task_history_entry = {
                "task_id": task_id,
                "task_name": task_name,
                "action": action,
                "start_time": start_time,
                "execution_time": execution_time,
                "status": "error",
                "error": str(e)
            }
            
            if len(self.post_history) >= 100:
                self.post_history.pop(0)  # En eski kaydı sil
            self.post_history.append(task_history_entry)
            
            # Yanıt mesajı
            reply = original_message.create_reply(
                content={
                    "status": "error",
                    "task_id": task_id,
                    "error": str(e),
                    "execution_time": execution_time
                },
                message_type="task.response"
            )
            await self._registry.send_message(reply)
            logger.error(f"Sosyal medya görevi başarısız: {task_id} - {action}, hata: {str(e)}")

    # Action metodları
    async def _action_create_post(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Sosyal medya gönderisi oluştur"""
        params = task.get("params", {})
        platform = params.get("platform", "instagram")
        post_type = params.get("post_type", "image")
        purpose = params.get("purpose", "engagement")
        target_audience = params.get("target_audience", "general")
        main_message = params.get("main_message", "")
        tone = params.get("tone", self.content_tone)
        
        if platform not in self.supported_platforms:
            raise ValueError(f"Unsupported platform: {platform}")
        
        post_id = f"post_{int(time.time())}_{platform}"
        
        post_content = {
            "post_id": post_id,
            "platform": platform,
            "post_type": post_type,
            "purpose": purpose,
            "target_audience": target_audience,
            "main_message": main_message,
            "tone": tone,
            "created_at": time.time(),
            "status": "draft",
            "workflow_step": "briefing",
            "workflow_data": {
                "briefing": {
                    "purpose": purpose,
                    "target_audience": target_audience,
                    "main_message": main_message,
                    "platforms": [platform]
                }
            }
        }
        
        self.content_drafts[post_id] = post_content
        context["current_post_id"] = post_id
        
        return {
            "post_id": post_id,
            "message": f"{platform} platformu için {post_type} türünde içerik taslağı oluşturuldu",
            "post_content": post_content,
            "next_step": "creative_idea"
        }

    async def _action_schedule_post(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Sosyal medya gönderisini zamanla"""
        params = task.get("params", {})
        post_id = params.get("post_id")
        schedule_time = params.get("schedule_time")
        
        if not post_id:
            raise ValueError("post_id required for scheduling")
        
        if not schedule_time:
            raise ValueError("schedule_time required for scheduling")
        
        if post_id not in self.content_drafts:
            raise ValueError(f"Post not found: {post_id}")
        
        post = self.content_drafts[post_id]
        
        post["status"] = "scheduled"
        post["schedule_time"] = schedule_time
        post["workflow_step"] = "scheduling"
        
        if "workflow_data" not in post:
            post["workflow_data"] = {}
        
        post["workflow_data"]["scheduling"] = {
            "publishing_tool": params.get("publishing_tool", "Meta Business Suite"),
            "schedule_time": schedule_time,
            "links_tags_check": params.get("links_tags_check", True)
        }
        
        scheduled_post = post.copy()
        self.scheduled_posts.append(scheduled_post)
        
        return {
            "post_id": post_id,
            "message": f"Post {schedule_time} tarihine planlandı",
            "scheduled_post": scheduled_post
        }

    async def _action_analyze_engagement(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Sosyal medya etkileşimlerini analiz et"""
        params = task.get("params", {})
        post_id = params.get("post_id")
        metrics = params.get("metrics", ["likes", "comments", "shares", "saves"])
        
        if not post_id:
            raise ValueError("post_id required for engagement analysis")
        
        found_post = None
        
        for post in self.post_history:
            if post.get("post_id") == post_id:
                found_post = post
                break
        
        if not found_post:
            for post in self.scheduled_posts:
                if post.get("post_id") == post_id:
                    found_post = post
                    break
        
        if not found_post:
            raise ValueError(f"Post not found for analysis: {post_id}")
        
        engagement_data = {
            "post_id": post_id,
            "platform": found_post.get("platform", "instagram"),
            "metrics": {
                "likes": 125,
                "comments": 14,
                "shares": 8,
                "saves": 32,
                "reach": 2450,
                "impressions": 3120
            },
            "analysis_time": time.time()
        }
        
        if found_post.get("status") == "published":
            found_post["workflow_step"] = "reporting"
            
            if "workflow_data" not in found_post:
                found_post["workflow_data"] = {}
            
            found_post["workflow_data"]["reporting"] = {
                "metrics": engagement_data["metrics"],
                "benchmarks": {
                    "average_likes": 100,
                    "average_comments": 10,
                    "average_shares": 5
                },
                "analysis_time": engagement_data["analysis_time"]
            }
        
        return {
            "post_id": post_id,
            "engagement_data": engagement_data,
            "insights": {
                "performance": "above_average",
                "strongest_metric": "saves",
                "suggestions": [
                    "Bu formatta içerik üretmeye devam edin",
                    "Benzer hedef kitleye daha fazla içerik yöneltin"
                ]
            }
        }

    async def _action_generate_image(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """AI ile görsel oluştur"""
        params = task.get("params", {})
        prompt = params.get("prompt", "")
        platform = params.get("platform", "instagram")
        content_type = params.get("content_type", "post")
        style = params.get("style", "social_media")
        
        if not prompt:
            raise ValueError("prompt required for image generation")
        
        # Image generator tool'unu al
        try:
            from os_araci.tools.image_generator import ImageGeneratorTool
            image_tool = ImageGeneratorTool()
            
            # Platform-specific image generation
            result = await image_tool.generate_social_media_image(
                prompt=prompt,
                platform=platform,
                content_type=content_type,
                style=style
            )
            
            if result.get("status") == "success":
                # Post'a image bilgilerini ekle
                post_id = params.get("post_id") or context.get("current_post_id")
                if post_id and post_id in self.content_drafts:
                    post = self.content_drafts[post_id]
                    post["generated_image"] = {
                        "image_path": result.get("image_path"),
                        "prompt_used": result.get("prompt_used"),
                        "platform": platform,
                        "content_type": content_type,
                        "generation_time": result.get("generation_time"),
                        "platform_optimized": result.get("platform_optimized", True)
                    }
                    
                    # Visual production workflow step'ini güncelle
                    if post.get("workflow_step") == "visual_production":
                        if "workflow_data" not in post:
                            post["workflow_data"] = {}
                        
                        if "visual_production" not in post["workflow_data"]:
                            post["workflow_data"]["visual_production"] = {}
                        
                        post["workflow_data"]["visual_production"]["ai_generated_image"] = result
                
                return {
                    "image_generated": True,
                    "image_path": result.get("image_path"),
                    "prompt_used": result.get("prompt_used"),
                    "platform": platform,
                    "content_type": content_type,
                    "message": f"{platform} için {content_type} görseli başarıyla oluşturuldu"
                }
            else:
                return {
                    "image_generated": False,
                    "error": result.get("message", "Görsel oluşturulamadı"),
                    "platform": platform,
                    "content_type": content_type
                }
                
        except Exception as e:
            logger.error(f"Image generation error: {str(e)}")
            return {
                "image_generated": False,
                "error": str(e),
                "platform": platform,
                "content_type": content_type
            }

    async def _action_generate_hashtags(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """İçerik için hashtag önerileri oluştur"""
        params = task.get("params", {})
        topic = params.get("topic", "")
        platform = params.get("platform", "instagram")
        count = params.get("count", self.content_preferences.get("max_hashtags", 5))
        
        if not topic:
            raise ValueError("topic required for hashtag generation")
        
        if platform not in self.supported_platforms:
            raise ValueError(f"Unsupported platform: {platform}")
        
        hashtag_suggestions = []
        
        if platform == "instagram":
            hashtag_suggestions = ["#instagood", "#photooftheday", "#fashion", "#beautiful", "#happy", 
                                  f"#{topic.replace(' ', '')}", f"#{topic.replace(' ', '_')}"]
        elif platform == "twitter":
            hashtag_suggestions = ["#trending", "#viral", "#followme", 
                                  f"#{topic.replace(' ', '')}", f"#{topic.replace(' ', '_')}"]
        elif platform == "linkedin":
            hashtag_suggestions = ["#business", "#leadership", "#innovation", "#career", 
                                  f"#{topic.replace(' ', '')}", f"#{topic.replace(' ', '_')}"]
        else:
            hashtag_suggestions = [f"#{topic.replace(' ', '')}", f"#{topic.replace(' ', '_')}"]
        
        hashtag_suggestions = hashtag_suggestions[:count]
        
        post_id = params.get("post_id") or context.get("current_post_id")
        if post_id and post_id in self.content_drafts:
            post = self.content_drafts[post_id]
            
            if "hashtags" not in post:
                post["hashtags"] = []
            
            post["hashtags"] = hashtag_suggestions
            
            if post.get("workflow_step") == "sharing_content":
                if "workflow_data" not in post:
                    post["workflow_data"] = {}
                
                if "sharing_content" not in post["workflow_data"]:
                    post["workflow_data"]["sharing_content"] = {}
                
                post["workflow_data"]["sharing_content"]["hashtags"] = hashtag_suggestions
        
        return {
            "topic": topic,
            "platform": platform,
            "hashtags": hashtag_suggestions,
            "suggestions_count": len(hashtag_suggestions)
        }

    async def _action_create_content_plan(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Sosyal medya içerik planı oluştur"""
        params = task.get("params", {})
        platform = params.get("platform", "all")
        duration = params.get("duration", 7)
        content_types = params.get("content_types", ["image", "carousel", "video", "story"])
        
        if platform != "all" and platform not in self.supported_platforms:
            raise ValueError(f"Unsupported platform: {platform}")
        
        platforms = self.supported_platforms if platform == "all" else [platform]
        
        content_plan = {
            "plan_id": f"plan_{int(time.time())}",
            "duration_days": duration,
            "platforms": platforms,
            "content_types": content_types,
            "created_at": time.time(),
            "posts": []
        }
        
        import random
        from datetime import datetime, timedelta
        
        start_date = datetime.now()
        
        for day in range(duration):
            post_date = start_date + timedelta(days=day)
            day_posts = []
            
            for platform in platforms:
                post_count = 1
                if platform == "instagram":
                    post_count = 1
                elif platform == "twitter":
                    post_count = 2
                elif platform == "linkedin":
                    post_count = 1
                
                for i in range(post_count):
                    content_type = random.choice(content_types)
                    hour = random.randint(9, 17)
                    minute = random.choice([0, 15, 30, 45])
                    
                    post_time = post_date.replace(hour=hour, minute=minute)
                    
                    post = {
                        "platform": platform,
                        "content_type": content_type,
                        "proposed_time": post_time.isoformat(),
                        "day_of_week": post_time.strftime("%A"),
                        "content_ideas": [
                            f"{platform} için {content_type} içerik önerisi"
                        ]
                    }
                    
                    day_posts.append(post)
            
            content_plan["posts"].append({
                "date": post_date.strftime("%Y-%m-%d"),
                "day_of_week": post_date.strftime("%A"),
                "posts": day_posts
            })
        
        return {
            "plan_id": content_plan["plan_id"],
            "message": f"{duration} günlük içerik planı oluşturuldu",
            "content_plan": content_plan
        }

    async def _action_process_workflow_step(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """İş akışı adımını işle"""
        params = task.get("params", {})
        post_id = params.get("post_id")
        step_id = params.get("step_id")
        step_data = params.get("step_data", {})
        
        if not post_id:
            raise ValueError("post_id required for workflow processing")
        
        if not step_id:
            raise ValueError("step_id required for workflow processing")
        
        if post_id not in self.content_drafts:
            raise ValueError(f"Post not found: {post_id}")
        
        post = self.content_drafts[post_id]
        
        valid_step = False
        step_info = None
        next_step_id = None
        
        for i, step in enumerate(self.workflow_steps):
            if step["step_id"] == step_id:
                valid_step = True
                step_info = step
                
                if i < len(self.workflow_steps) - 1:
                    next_step_id = self.workflow_steps[i + 1]["step_id"]
                break
        
        if not valid_step:
            raise ValueError(f"Invalid workflow step: {step_id}")
        
        missing_inputs = []
        for required_input in step_info["required_inputs"]:
            if required_input not in step_data:
                missing_inputs.append(required_input)
        
        if missing_inputs:
            raise ValueError(f"Missing required inputs for {step_id}: {', '.join(missing_inputs)}")
        
        if "workflow_data" not in post:
            post["workflow_data"] = {}
        
        post["workflow_data"][step_id] = step_data
        post["workflow_step"] = step_id
        
        # Özel adım işlemleri
        if step_id == "briefing":
            post["purpose"] = step_data.get("purpose")
            post["target_audience"] = step_data.get("target_audience")
            post["main_message"] = step_data.get("main_message")
            post["platforms"] = step_data.get("platforms", [post["platform"]])
        
        elif step_id == "creative_idea":
            post["post_type"] = step_data.get("post_type", post.get("post_type"))
            post["concept"] = step_data.get("concept")
            post["tone"] = step_data.get("tone", post.get("tone"))
            post["formats"] = step_data.get("formats", [])
        
        elif step_id == "post_content":
            post["post_title"] = step_data.get("post_title")
            post["post_message"] = step_data.get("post_message")
            if "video_script" in step_data:
                post["video_script"] = step_data.get("video_script")
            if "visual_description" in step_data:
                post["visual_description"] = step_data.get("visual_description")
        
        elif step_id == "sharing_content":
            post["share_text"] = step_data.get("share_text")
            post["emojis"] = step_data.get("emojis", [])
            post["hashtags"] = step_data.get("hashtags", [])
        
        elif step_id == "visual_production":
            post["static_designs"] = step_data.get("static_designs", [])
            if "video_plan" in step_data:
                post["video_plan"] = step_data.get("video_plan")
            if "subtitles" in step_data:
                post["subtitles"] = step_data.get("subtitles")
        
        elif step_id == "approval":
            post["is_approved"] = step_data.get("client_approval", False)
            post["approval_notes"] = step_data.get("approval_notes", "")
            post["approved_by"] = step_data.get("approved_by", "")
            post["approved_at"] = time.time() if step_data.get("client_approval", False) else None
        
        elif step_id == "scheduling":
            post["publishing_tool"] = step_data.get("publishing_tool", "")
            post["schedule_time"] = step_data.get("schedule_time")
            post["status"] = "scheduled" if step_data.get("schedule_time") else post.get("status", "draft")
            
            if step_data.get("schedule_time"):
                already_scheduled = False
                for i, scheduled_post in enumerate(self.scheduled_posts):
                    if scheduled_post.get("post_id") == post_id:
                        self.scheduled_posts[i] = post.copy()
                        already_scheduled = True
                        break
                
                if not already_scheduled:
                    self.scheduled_posts.append(post.copy())
        
        elif step_id == "monitoring":
            post["response_strategy"] = step_data.get("response_strategy", "")
            post["moderation_rules"] = step_data.get("moderation_rules", "")
            
            if post.get("status") == "scheduled" and step_data.get("published", False):
                post["status"] = "published"
                post["published_at"] = time.time()
        
        elif step_id == "reporting":
            post["metrics"] = step_data.get("metrics", {})
            post["benchmarks"] = step_data.get("benchmarks", {})
            post["report_created"] = True
            post["report_date"] = time.time()
        
        response = {
            "post_id": post_id,
            "step": step_id,
            "status": "completed",
            "message": f"{step_info['name']} adımı tamamlandı"
        }
        
        if next_step_id:
            response["next_step"] = next_step_id
            
            next_step_info = None
            for step in self.workflow_steps:
                if step["step_id"] == next_step_id:
                    next_step_info = step
                    break
            
            if next_step_info:
                response["next_step_info"] = {
                    "name": next_step_info["name"],
                    "description": next_step_info["description"],
                    "required_inputs": next_step_info["required_inputs"],
                    "responsible_roles": next_step_info["responsible_roles"]
                }
        else:
            response["message"] = f"{step_info['name']} adımı tamamlandı. Tüm iş akışı tamamlandı!"
            response["workflow_completed"] = True
        
        response["updated_post"] = post
        
        return response

    # Utility metodları
    def get_workflow_summary(self, post_id: str) -> Dict[str, Any]:
        """Post iş akışı durumunu özetle"""
        if post_id not in self.content_drafts:
            raise ValueError(f"Post not found: {post_id}")
        
        post = self.content_drafts[post_id]
        workflow_data = post.get("workflow_data", {})
        current_step = post.get("workflow_step", "")
        
        steps_status = {}
        completed_steps = []
        
        for step in self.workflow_steps:
            step_id = step["step_id"]
            
            if step_id in workflow_data:
                steps_status[step_id] = "completed"
                completed_steps.append(step_id)
            elif step_id == current_step:
                steps_status[step_id] = "in_progress"
            elif completed_steps and self.workflow_steps.index(step) > self.workflow_steps.index({"step_id": completed_steps[-1]}):
                steps_status[step_id] = "pending"
            else:
                steps_status[step_id] = "skipped"
        
        total_steps = len(self.workflow_steps)
        completed_count = len(completed_steps)
        progress_percentage = (completed_count / total_steps) * 100 if total_steps > 0 else 0
        
        return {
            "post_id": post_id,
            "current_step": current_step,
            "current_step_name": next((step["name"] for step in self.workflow_steps if step["step_id"] == current_step), ""),
            "steps_status": steps_status,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "progress_percentage": progress_percentage,
            "post_status": post.get("status", "draft")
        }

    def get_post_summary(self, post_id: str) -> Dict[str, Any]:
        """Post bilgilerini özetle"""
        if post_id not in self.content_drafts:
            raise ValueError(f"Post not found: {post_id}")
        
        post = self.content_drafts[post_id]
        
        summary = {
            "post_id": post_id,
            "platform": post.get("platform", ""),
            "post_type": post.get("post_type", ""),
            "status": post.get("status", "draft"),
            "created_at": post.get("created_at", 0),
            "current_step": post.get("workflow_step", "")
        }
        
        if post.get("workflow_step") in ["post_content", "sharing_content", "visual_production", "approval", "scheduling", "monitoring", "reporting"]:
            if "post_title" in post:
                summary["post_title"] = post["post_title"]
            if "post_message" in post:
                summary["post_message"] = post["post_message"]
        
        if post.get("workflow_step") in ["sharing_content", "visual_production", "approval", "scheduling", "monitoring", "reporting"]:
            if "share_text" in post:
                summary["share_text"] = post["share_text"]
            if "hashtags" in post:
                summary["hashtags"] = post["hashtags"]
        
        if post.get("status") == "scheduled" and "schedule_time" in post:
            summary["schedule_time"] = post["schedule_time"]
        
        if post.get("status") == "published" and "published_at" in post:
            summary["published_at"] = post["published_at"]
        
        if "is_approved" in post:
            summary["is_approved"] = post["is_approved"]
        
        return summary

    def _move_to_next_workflow_step(self, draft, current_step_info):
        """Bir sonraki iş akışı adımına geçer ve ilgili bilgileri döndürür."""
        try:
            next_index = self.workflow_steps.index(current_step_info) + 1
            if next_index < len(self.workflow_steps):
                next_step = self.workflow_steps[next_index]
                draft['workflow_step'] = next_step["step_id"]
                draft['step_progress'] = 0
                return next_step
            else:
                draft['status'] = 'completed'
                return None
        except Exception as e:
            logger.error(f"Workflow adımı geçiş hatası: {str(e)}")
            return None

    async def _evaluate_results_with_llm(self, results: List[Dict], original_task: Dict, context: Dict) -> Dict[str, Any]:
        """Sonuçları LLM ile değerlendir"""
        if not hasattr(self, 'llm_tool') or not self.llm_tool:
            return {"success": True, "summary": "LLM değerlendirmesi yapılamadı"}
        
        try:
            system_prompt = """Verilen görev sonuçlarını değerlendir. 
Başarılı olup olmadığını, nelerin iyi gittiğini, nelerin geliştirilebileceğini belirt.

Yanıtını şu JSON formatında ver:
{
    "success": true/false,
    "summary": "Genel değerlendirme",
    "improvements": ["İyileştirme önerisi 1", "İyileştirme önerisi 2"],
    "next_steps": ["Sonraki adım 1", "Sonraki adım 2"]
}
"""
            
            prompt = f"""
Orijinal Görev: {json.dumps(original_task, indent=2)}
Yürütülen Adımlar ve Sonuçları: {json.dumps(results, indent=2)}
Final Context: {json.dumps(context, indent=2)}

Bu görevin sonuçlarını değerlendir.
"""
            
            result = await self.llm_tool.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            response_text = result.get('text', '{}')
            
            if '```json' in response_text:
                json_text = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                json_text = response_text.split('```')[1].split('```')[0]
            else:
                json_text = response_text
            
            return json.loads(json_text)
            
        except Exception as e:
            logger.error(f"Sonuç değerlendirme hatası: {str(e)}")
            return {"success": True, "summary": "Değerlendirme yapılamadı", "error": str(e)}

    # ===========================================
    # MEMORY MANAGEMENT METHODS
    # ===========================================
    
    async def _get_stored_context(self, user_id: str) -> Dict[str, Any]:
        """Memory manager'dan persona context'ini al"""
        try:
            # Memory manager'a eriş - önce registry'den
            memory_manager = None
            
            # Registry'deki tüm araçları kontrol et
            if hasattr(self.coordinator, 'registry'):
                all_tools = self.coordinator.registry.get_all_metadata()
                logger.info(f"📋 Registry'deki araçlar: {[(k, v.name) for k, v in all_tools.items()]}")
                
                for tool_id, metadata in all_tools.items():
                    if metadata.name == 'memory_manager':  # Tam eşleşme
                        memory_manager = self.coordinator.registry.get_tool_by_id(tool_id)
                        logger.info(f"✅ Memory manager bulundu: {tool_id}")
                        break
            
            if not memory_manager:
                logger.warning("Memory manager not found, returning empty context")
                return {}
            
            # Context'i al
            result = memory_manager.get_persona_context(self.persona_id, user_id)
            
            if result["status"] == "success":
                context = result["context"]
                logger.info(f"Loaded context for {self.persona_id}_{user_id}: {len(context)} items")
                return context
            elif result["status"] == "not_found":
                logger.info(f"No stored context found for {self.persona_id}_{user_id}")
                return {}
            else:
                logger.error(f"Error loading context: {result.get('message', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get stored context: {str(e)}")
            return {}
    
    async def _save_context(self, user_id: str, context_data: Dict[str, Any]) -> bool:
        """Context'i memory manager'a kaydet"""
        try:
            # Memory manager'a eriş
            memory_manager = None
            for tool_id, metadata in self.coordinator.registry.get_all_metadata().items():
                if 'memory' in metadata.name.lower():
                    memory_manager = self.coordinator.registry.get_tool_by_id(tool_id)
                    break
                    
            if not memory_manager:
                logger.warning("Memory manager not found, cannot save context")
                return False
            
            # Context'i kaydet
            result = memory_manager.save_persona_context(self.persona_id, user_id, context_data)
            
            if result["status"] == "success":
                logger.info(f"Context saved for {self.persona_id}_{user_id}")
                return True
            else:
                logger.error(f"Error saving context: {result.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to save context: {str(e)}")
            return False
    
    async def _update_context(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Context'i kısmi güncelle"""
        try:
            # Memory manager'a eriş
            memory_manager = None
            for tool_id, metadata in self.coordinator.registry.get_all_metadata().items():
                if 'memory' in metadata.name.lower():
                    memory_manager = self.coordinator.registry.get_tool_by_id(tool_id)
                    break
                    
            if not memory_manager:
                logger.warning("Memory manager not found, cannot update context")
                return False
            
            # Context'i güncelle
            result = memory_manager.update_persona_state(self.persona_id, user_id, updates)
            
            if result["status"] == "success":
                logger.info(f"Context updated for {self.persona_id}_{user_id}: {list(updates.keys())}")
                return True
            else:
                logger.error(f"Error updating context: {result.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update context: {str(e)}")
            return False
    
    async def _clear_context(self, user_id: str) -> bool:
        """Persona session'ını temizle"""
        try:
            # Memory manager'a eriş
            memory_manager = None
            for tool_id, metadata in self.coordinator.registry.get_all_metadata().items():
                if 'memory' in metadata.name.lower():
                    memory_manager = self.coordinator.registry.get_tool_by_id(tool_id)
                    break
                    
            if not memory_manager:
                logger.warning("Memory manager not found, cannot clear context")
                return False
            
            # Session'ı temizle
            result = memory_manager.clear_persona_session(self.persona_id, user_id)
            
            if result["status"] == "success":
                logger.info(f"Context cleared for {self.persona_id}_{user_id}")
                return True
            else:
                logger.error(f"Error clearing context: {result.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to clear context: {str(e)}")
            return False