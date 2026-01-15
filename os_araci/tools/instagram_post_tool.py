# tools/instagram_post_tool.py
import time
import logging
import json
import os
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

from os_araci.mcp_core.tool import MCPTool

logger = logging.getLogger(__name__)

class InstagramPoster(MCPTool):
    """
    Metis Agent Instagram post oluşturma ve yönetme aracı.
    
    Toplanan verilerle otomatik olarak Instagram paylaşımı oluşturur, 
    hashtagler ekler, görsel ile ilişkilendirir ve onay sonrası yayınlar.
    """
    
    def __init__(self, **kwargs):
        """Instagram posteri aracını başlat"""
        super().__init__(
            name="instagram_poster",
            description="Instagram post oluşturma ve yönetme aracı",
            version="1.0.0",
            category="social_media",
            capabilities=["post_creation", "caption_generation", "hashtag_management", "post_scheduling", "auto_posting"],
            **kwargs
        )
        
        # Ayarlar ve saklama klasörleri
        self.posts_storage_path = kwargs.get('posts_storage_path', './instagram_posts')
        self.default_hashtags_per_post = kwargs.get('default_hashtags', 5)
        self.max_post_length = kwargs.get('max_post_length', 2200)  # Instagram karakter limiti
        self.webhook_url = kwargs.get('webhook_url', None)  # Dış sistem entegrasyonu için webhook
        
        # Instagram API bilgileri
        self.instagram_access_token = kwargs.get('instagram_access_token', os.environ.get('INSTAGRAM_ACCESS_TOKEN'))
        self.instagram_user_id = kwargs.get('instagram_user_id', os.environ.get('INSTAGRAM_USER_ID'))
        
        # Eğer API bilgileri belirtilmemişse, çevre değişkenlerinden kontrol et
        if not self.instagram_access_token:
            self.instagram_access_token = os.environ.get('INSTAGRAM_ACCESS_TOKEN')
            if not self.instagram_access_token:
                logger.warning("Instagram Access Token bulunamadı. Instagram API kullanılamayacak.")
        
        if not self.instagram_user_id:
            self.instagram_user_id = os.environ.get('INSTAGRAM_USER_ID')
            if not self.instagram_user_id:
                logger.warning("Instagram User ID bulunamadı. Instagram API kullanılamayacak.")
        
        # Post, taslak ve zamanlanan içerikler
        self.posts = {}  # Onaylanmış ve yayınlanmış postlar
        self.drafts = {}  # Taslak postlar
        self.scheduled_posts = {}  # Zaman planlamalı postlar
        
        # Klasörü oluştur
        if not os.path.exists(self.posts_storage_path):
            os.makedirs(self.posts_storage_path, exist_ok=True)
            logger.info(f"Instagram post depolama klasörü oluşturuldu: {self.posts_storage_path}")
            
        # Önceki verileri yükle (gerçek uygulamada)
        self._load_data()
    
    def get_all_actions(self) -> Dict[str, Dict[str, Any]]:
        """Aracın desteklediği tüm aksiyonları döndürür"""
        return {
            "create_post": {
                "description": "Post taslağı oluşturur",
                "parameters": {
                    "post_data": {"type": "object", "description": "Post bilgileri", "required": True},
                },
                "returns": {
                    "type": "object", 
                    "description": "Oluşturulan post bilgileri"
                }
            },
            "generate_caption": {
                "description": "Post için otomatik caption oluşturur",
                "parameters": {
                    "post_id": {"type": "string", "description": "Post ID", "required": True},
                    "tone": {"type": "string", "description": "Yazım tonu (eğlenceli, profesyonel, samimi vb.)", "required": False}
                },
                "returns": {
                    "type": "object", 
                    "description": "Oluşturulan caption ve güncellenen post"
                }
            },
            "generate_hashtags": {
                "description": "Post için hashtag önerileri oluşturur",
                "parameters": {
                    "post_id": {"type": "string", "description": "Post ID", "required": True},
                    "count": {"type": "integer", "description": "Oluşturulacak hashtag sayısı", "required": False}
                },
                "returns": {
                    "type": "object", 
                    "description": "Oluşturulan hashtagler ve güncellenen post"
                }
            },
            "set_visual": {
                "description": "Post'a görsel atar",
                "parameters": {
                    "post_id": {"type": "string", "description": "Post ID", "required": True},
                    "visual_id": {"type": "string", "description": "Görsel ID", "required": True}
                },
                "returns": {
                    "type": "object", 
                    "description": "Görsel atama sonucu"
                }
            },
            "schedule_post": {
                "description": "Post'u belirli bir zamanda yayınlanacak şekilde planlar",
                "parameters": {
                    "post_id": {"type": "string", "description": "Post ID", "required": True},
                    "schedule_time": {"type": "string", "description": "Planlanan zaman (ISO formatı)", "required": True}
                },
                "returns": {
                    "type": "object", 
                    "description": "Planlama sonucu"
                }
            },
            "approve_post": {
                "description": "Post'u onaylar ve yayına hazır hale getirir",
                "parameters": {
                    "post_id": {"type": "string", "description": "Post ID", "required": True}
                },
                "returns": {
                    "type": "object", 
                    "description": "Onay sonucu"
                }
            },
            "publish_post": {
                "description": "Post'u hemen yayınlar",
                "parameters": {
                    "post_id": {"type": "string", "description": "Post ID", "required": True}
                },
                "returns": {
                    "type": "object", 
                    "description": "Yayınlama sonucu"
                }
            },
            "get_post": {
                "description": "Post detaylarını getirir",
                "parameters": {
                    "post_id": {"type": "string", "description": "Post ID", "required": True}
                },
                "returns": {
                    "type": "object", 
                    "description": "Post detayları"
                }
            },
            "get_all_posts": {
                "description": "Tüm postları listeler",
                "parameters": {
                    "status": {"type": "string", "description": "Filtrelenecek post durumu (draft, approved, published, scheduled)", "required": False},
                    "limit": {"type": "integer", "description": "Listelenecek post sayısı", "required": False}
                },
                "returns": {
                    "type": "object", 
                    "description": "Post listesi"
                }
            }
        }
    
    def create_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Instagram post taslağı oluşturur.
        
        Args:
            post_data: Post bilgileri (konu, içerik teması, hedef kitle vb.)
            
        Returns:
            Oluşturulan post bilgileri
        """
        try:
            # Post temel bilgilerini kontrol et
            if not isinstance(post_data, dict):
                return {"status": "error", "message": "post_data bir dict olmalıdır"}
            
            # Post ID oluştur
            post_id = post_data.get("post_id") or f"post_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            
            # Post taslağını oluştur
            now = time.time()
            post = {
                "post_id": post_id,
                "platform": "instagram",
                "created_at": now,
                "updated_at": now,
                "status": "draft",
                "author": post_data.get("author", "Metis Agent"),
                "content": {
                    "caption": post_data.get("caption", ""),
                    "hashtags": post_data.get("hashtags", []),
                },
                "metadata": {
                    "topic": post_data.get("topic", ""),
                    "content_theme": post_data.get("content_theme", ""),
                    "target_audience": post_data.get("target_audience", ""),
                    "tone": post_data.get("tone", "professional"),
                    "main_message": post_data.get("main_message", "")
                },
                "visual": post_data.get("visual", None),
                "analytics": {
                    "creation_time": now
                }
            }
            
            # Eğer henüz caption yoksa ve yeterli metadata varsa, otomatik oluştur
            if not post["content"]["caption"] and post["metadata"]["topic"]:
                caption_result = self._auto_generate_caption(
                    topic=post["metadata"]["topic"],
                    tone=post["metadata"]["tone"],
                    target_audience=post["metadata"]["target_audience"],
                    main_message=post["metadata"]["main_message"]
                )
                
                if caption_result.get("status") == "success":
                    post["content"]["caption"] = caption_result.get("caption", "")
            
            # Eğer hashtag yoksa ve yeterli metadata varsa, otomatik oluştur
            if not post["content"]["hashtags"] and post["metadata"]["topic"]:
                hashtag_result = self._auto_generate_hashtags(
                    topic=post["metadata"]["topic"],
                    count=self.default_hashtags_per_post
                )
                
                if hashtag_result.get("status") == "success":
                    post["content"]["hashtags"] = hashtag_result.get("hashtags", [])
            
            # Taslağı kaydet
            self.drafts[post_id] = post
            self._save_data()
            
            return {
                "status": "success",
                "message": "Post taslağı oluşturuldu",
                "post": post
            }
            
        except Exception as e:
            logger.error(f"Post oluşturma hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def generate_caption(self, post_id: str, tone: str = None) -> Dict[str, Any]:
        """
        Post için otomatik caption oluşturur.
        
        Args:
            post_id: Post ID
            tone: Yazım tonu (eğlenceli, profesyonel, samimi vb.)
            
        Returns:
            Oluşturulan caption ve güncellenen post
        """
        try:
            # Post'u kontrol et
            post = self._get_post_by_id(post_id)
            if not post:
                return {"status": "error", "message": f"Post bulunamadı: {post_id}"}
            
            # Tone belirtilmemişse, post metadatasından al
            if not tone:
                tone = post["metadata"].get("tone", "professional")
            
            # Caption oluştur
            caption_result = self._auto_generate_caption(
                topic=post["metadata"].get("topic", ""),
                tone=tone,
                target_audience=post["metadata"].get("target_audience", ""),
                main_message=post["metadata"].get("main_message", "")
            )
            
            if caption_result.get("status") != "success":
                return caption_result
            
            # Post'u güncelle
            post["content"]["caption"] = caption_result.get("caption", "")
            post["updated_at"] = time.time()
            
            # Veri kaydet
            self._save_post(post)
            
            return {
                "status": "success",
                "message": "Caption başarıyla oluşturuldu",
                "caption": post["content"]["caption"],
                "post": post
            }
            
        except Exception as e:
            logger.error(f"Caption oluşturma hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def generate_hashtags(self, post_id: str, count: int = None) -> Dict[str, Any]:
        """
        Post için hashtag önerileri oluşturur.
        
        Args:
            post_id: Post ID
            count: Oluşturulacak hashtag sayısı
            
        Returns:
            Oluşturulan hashtagler ve güncellenen post
        """
        try:
            # Post'u kontrol et
            post = self._get_post_by_id(post_id)
            if not post:
                return {"status": "error", "message": f"Post bulunamadı: {post_id}"}
            
            # Count belirtilmemişse, varsayılanı kullan
            if not count:
                count = self.default_hashtags_per_post
            
            # Hashtag oluştur
            hashtag_result = self._auto_generate_hashtags(
                topic=post["metadata"].get("topic", ""),
                count=count
            )
            
            if hashtag_result.get("status") != "success":
                return hashtag_result
            
            # Post'u güncelle
            post["content"]["hashtags"] = hashtag_result.get("hashtags", [])
            post["updated_at"] = time.time()
            
            # Veri kaydet
            self._save_post(post)
            
            return {
                "status": "success",
                "message": "Hashtagler başarıyla oluşturuldu",
                "hashtags": post["content"]["hashtags"],
                "post": post
            }
            
        except Exception as e:
            logger.error(f"Hashtag oluşturma hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def set_visual(self, post_id: str, visual_id: str) -> Dict[str, Any]:
        """
        Post'a görsel atar.
        
        Args:
            post_id: Post ID
            visual_id: Görsel ID
            
        Returns:
            Görsel atama sonucu
        """
        try:
            # Post'u kontrol et
            post = self._get_post_by_id(post_id)
            if not post:
                return {"status": "error", "message": f"Post bulunamadı: {post_id}"}
            
            # Görsel ID'yi kontrol et - VisualCreator aracından alınacak
            visual_creator = self._get_visual_creator()
            visual_info = None
            
            if visual_creator:
                visual_result = visual_creator.get_visual_by_id(visual_id)
                if visual_result.get("status") == "success":
                    visual_info = visual_result.get("visual", {})
            
            if not visual_info:
                # VisualCreator yoksa veya görsel bulunamadıysa basit bilgi kullan
                visual_info = {
                    "visual_id": visual_id,
                    "image_url": f"/api/images/{visual_id}"
                }
            
            # Post'u güncelle
            post["visual"] = visual_info
            post["updated_at"] = time.time()
            
            # Veri kaydet
            self._save_post(post)
            
            return {
                "status": "success",
                "message": "Görsel başarıyla atandı",
                "visual": post["visual"],
                "post": post
            }
            
        except Exception as e:
            logger.error(f"Görsel atama hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def schedule_post(self, post_id: str, schedule_time: str) -> Dict[str, Any]:
        """
        Post'u belirli bir zamanda yayınlanacak şekilde planlar.
        
        Args:
            post_id: Post ID
            schedule_time: Planlanan zaman (ISO formatı)
            
        Returns:
            Planlama sonucu
        """
        try:
            # Post'u kontrol et
            post = self._get_post_by_id(post_id)
            if not post:
                return {"status": "error", "message": f"Post bulunamadı: {post_id}"}
            
            # Post içeriğini kontrol et
            if not post["content"]["caption"]:
                return {"status": "error", "message": "Post caption boş olamaz"}
            
            # Görsel kontrolü
            if not post.get("visual"):
                return {"status": "error", "message": "Instagram postunda görsel gereklidir"}
            
            # Zamanı işle
            try:
                # ISO formatını datetime'a çevir
                schedule_datetime = datetime.fromisoformat(schedule_time.replace("Z", "+00:00"))
                now = datetime.now()
                
                # Geçmiş tarihe planlama yapılamaz
                if schedule_datetime < now:
                    return {"status": "error", "message": "Geçmiş bir tarihe planlama yapılamaz"}
                
                # Timestamp'e çevir
                schedule_timestamp = schedule_datetime.timestamp()
            except Exception as date_error:
                return {"status": "error", "message": f"Geçersiz tarih formatı: {str(date_error)}"}
            
            # Post'u güncelle
            post["schedule_time"] = schedule_timestamp
            post["status"] = "scheduled"
            post["updated_at"] = time.time()
            
            # Taslaktan çıkar, planlananlara ekle
            if post_id in self.drafts:
                del self.drafts[post_id]
            
            self.scheduled_posts[post_id] = post
            self._save_data()
            
            # Webhook entegrasyonu (gerçek uygulamada)
            if self.webhook_url:
                self._trigger_webhook("schedule", post)
            
            return {
                "status": "success",
                "message": f"Post {schedule_time} tarihine planlandı",
                "scheduled_time": schedule_time,
                "post": post
            }
            
        except Exception as e:
            logger.error(f"Post planlama hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def approve_post(self, post_id: str) -> Dict[str, Any]:
        """
        Post'u onaylar ve yayına hazır hale getirir.
        
        Args:
            post_id: Post ID
            
        Returns:
            Onay sonucu
        """
        try:
            # Post'u kontrol et
            post = self._get_post_by_id(post_id)
            if not post:
                return {"status": "error", "message": f"Post bulunamadı: {post_id}"}
            
            # Post içeriğini kontrol et
            if not post["content"]["caption"]:
                return {"status": "error", "message": "Post caption boş olamaz"}
            
            # Görsel kontrolü
            if not post.get("visual"):
                return {"status": "error", "message": "Instagram postunda görsel gereklidir"}
            
            # Post'u güncelle
            post["status"] = "approved"
            post["approved_at"] = time.time()
            post["updated_at"] = time.time()
            
            # Taslaktan çıkar, onaylanmışlara ekle
            if post_id in self.drafts:
                del self.drafts[post_id]
            
            self.posts[post_id] = post
            self._save_data()
            
            # Webhook entegrasyonu (gerçek uygulamada)
            if self.webhook_url:
                self._trigger_webhook("approve", post)
            
            return {
                "status": "success",
                "message": "Post onaylandı ve yayına hazır",
                "post": post,
                "approval_id": f"approval_{int(time.time())}",
                "publish_url": f"/api/instagram_poster/publish/{post_id}",
                "schedule_url": f"/api/instagram_poster/schedule/{post_id}"
            }
            
        except Exception as e:
            logger.error(f"Post onaylama hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def publish_post(self, post_id: str) -> Dict[str, Any]:
        """
        Post'u hemen yayınlar.
        
        Args:
            post_id: Post ID
            
        Returns:
            Yayınlama sonucu
        """
        try:
            # Post'u kontrol et
            post = self._get_post_by_id(post_id)
            if not post:
                return {"status": "error", "message": f"Post bulunamadı: {post_id}"}
            
            # Post durumunu kontrol et
            if post["status"] not in ["approved", "scheduled"]:
                return {"status": "error", "message": "Sadece onaylanmış veya planlanmış postlar yayınlanabilir"}
            
            # Instagram API entegrasyonu
            publish_result = self._publish_to_instagram(post)
            
            if publish_result.get("status") != "success":
                return publish_result
            
            # Post'u güncelle
            post["status"] = "published"
            post["published_at"] = time.time()
            post["updated_at"] = time.time()
            post["instagram_post_id"] = publish_result.get("instagram_post_id", "")
            post["instagram_post_url"] = publish_result.get("instagram_post_url", "")
            
            # Planlananlardan çıkar, yayınlananlara ekle
            if post_id in self.scheduled_posts:
                del self.scheduled_posts[post_id]
            
            self.posts[post_id] = post
            self._save_data()
            
            # Webhook entegrasyonu (gerçek uygulamada)
            if self.webhook_url:
                self._trigger_webhook("publish", post)
            
            return {
                "status": "success",
                "message": "Post başarıyla yayınlandı",
                "post": post,
                "instagram_post_id": post["instagram_post_id"],
                "instagram_post_url": post["instagram_post_url"]
            }
            
        except Exception as e:
            logger.error(f"Post yayınlama hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_post(self, post_id: str) -> Dict[str, Any]:
        """
        Post detaylarını getirir.
        
        Args:
            post_id: Post ID
            
        Returns:
            Post detayları
        """
        try:
            # Post'u kontrol et
            post = self._get_post_by_id(post_id)
            if not post:
                return {"status": "error", "message": f"Post bulunamadı: {post_id}"}
            
            return {
                "status": "success",
                "post": post
            }
            
        except Exception as e:
            logger.error(f"Post alma hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_all_posts(self, status: str = None, limit: int = 20) -> Dict[str, Any]:
        """
        Tüm postları listeler.
        
        Args:
            status: Filtrelenecek post durumu (draft, approved, published, scheduled)
            limit: Listelenecek post sayısı
            
        Returns:
            Post listesi
        """
        try:
            all_posts = []
            
            # Duruma göre filtrele
            if status == "draft":
                all_posts = list(self.drafts.values())
            elif status == "scheduled":
                all_posts = list(self.scheduled_posts.values())
            elif status in ["approved", "published"]:
                all_posts = [post for post in self.posts.values() if post["status"] == status]
            else:
                # Tüm postları birleştir
                all_posts = list(self.drafts.values()) + list(self.scheduled_posts.values()) + list(self.posts.values())
            
            # Tarihe göre sırala (yeniden eskiye)
            sorted_posts = sorted(all_posts, key=lambda x: x.get("updated_at", 0), reverse=True)
            
            # Limitle
            limited_posts = sorted_posts[:limit]
            
            return {
                "status": "success",
                "count": len(limited_posts),
                "total": len(all_posts),
                "posts": limited_posts
            }
            
        except Exception as e:
            logger.error(f"Tüm postları alma hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _get_post_by_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        ID'ye göre postu bulur.
        
        Args:
            post_id: Post ID
            
        Returns:
            Post veya None
        """
        # Önce taslaklar içinde ara
        if post_id in self.drafts:
            return self.drafts[post_id]
        
        # Sonra planlanmışlar içinde ara
        if post_id in self.scheduled_posts:
            return self.scheduled_posts[post_id]
        
        # Son olarak yayınlanmışlar içinde ara
        if post_id in self.posts:
            return self.posts[post_id]
        
        return None
    
    def _save_post(self, post: Dict[str, Any]) -> None:
        """
        Post'u uygun koleksiyona kaydeder.
        
        Args:
            post: Kaydedilecek post
        """
        post_id = post["post_id"]
        status = post["status"]
        
        if status == "draft":
            self.drafts[post_id] = post
        elif status == "scheduled":
            self.scheduled_posts[post_id] = post
        else:
            self.posts[post_id] = post
        
        self._save_data()
    
    def _save_data(self) -> None:
        """
        Tüm post verilerini diske kaydeder.
        Gerçek uygulamada veritabanına kaydedilecektir.
        """
        try:
            # Taslakları kaydet
            with open(os.path.join(self.posts_storage_path, "drafts.json"), "w", encoding="utf-8") as f:
                json.dump(self.drafts, f, ensure_ascii=False, indent=2)
            
            # Planlanmışları kaydet
            with open(os.path.join(self.posts_storage_path, "scheduled.json"), "w", encoding="utf-8") as f:
                json.dump(self.scheduled_posts, f, ensure_ascii=False, indent=2)
            
            # Yayınlanmışları kaydet
            with open(os.path.join(self.posts_storage_path, "posts.json"), "w", encoding="utf-8") as f:
                json.dump(self.posts, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Veri kaydetme hatası: {str(e)}")
    
    def _load_data(self) -> None:
        """
        Tüm post verilerini diskten yükler.
        Gerçek uygulamada veritabanından yüklenecektir.
        """
        try:
            # Taslakları yükle
            drafts_path = os.path.join(self.posts_storage_path, "drafts.json")
            if os.path.exists(drafts_path):
                with open(drafts_path, "r", encoding="utf-8") as f:
                    self.drafts = json.load(f)
            
            # Planlanmışları yükle
            scheduled_path = os.path.join(self.posts_storage_path, "scheduled.json")
            if os.path.exists(scheduled_path):
                with open(scheduled_path, "r", encoding="utf-8") as f:
                    self.scheduled_posts = json.load(f)
            
            # Yayınlanmışları yükle
            posts_path = os.path.join(self.posts_storage_path, "posts.json")
            if os.path.exists(posts_path):
                with open(posts_path, "r", encoding="utf-8") as f:
                    self.posts = json.load(f)
                    
            logger.info(f"Instagram post verileri yüklendi: {len(self.drafts)} taslak, {len(self.scheduled_posts)} planlanmış, {len(self.posts)} yayınlanmış")
            
        except Exception as e:
            logger.error(f"Veri yükleme hatası: {str(e)}")
    
    def _auto_generate_caption(self, topic: str, tone: str = "professional", 
                             target_audience: str = None, main_message: str = None) -> Dict[str, Any]:
        """
        Verilen bilgilere göre otomatik caption oluşturur.
        
        Args:
            topic: Ana konu
            tone: Yazım tonu
            target_audience: Hedef kitle
            main_message: Ana mesaj
            
        Returns:
            Oluşturulan caption
        """
        try:
            # LLM aracını al
            llm_tool = self._get_llm_tool()
            if not llm_tool:
                return {"status": "error", "message": "LLM aracı bulunamadı"}
            
            # Prompt oluştur
            system_prompt = """Sen bir profesyonel sosyal medya içerik üreticisisin.
            Instagram içerikleri için etkileyici, dikkat çekici ve kullanıcı etkileşimi yüksek
            caption metinleri yazıyorsun. Metinler istenen tona uygun, hedef kitleye hitap eden
            ve ana mesajı net olarak ileten bir yapıda olmalı."""
            
            prompt = f"""
            Lütfen aşağıdaki bilgilere göre Instagram için bir caption metni oluştur:
            
            Konu: {topic}
            Ton: {tone}
            {"Hedef kitle: " + target_audience if target_audience else ""}
            {"Ana mesaj: " + main_message if main_message else ""}
            
            Önemli Kurallar:
            1. Caption Instagram'ın 2200 karakter limitini geçmemeli
            2. Emoji kullanımı uygun şekilde olmalı (aşırıya kaçmadan)
            3. Metnin formatı iyi düzenlenmiş olmalı (paragraflar, satır araları)
            4. İlk 2-3 cümle dikkat çekici olmalı (carousel görsellerde ekranda görünen kısım)
            5. Metinde bir çağrı (call-to-action) olmalı
            
            Sadece caption metnini döndür, başka açıklama yapma.
            """
            
            # LLM ile caption oluştur
            result = llm_tool.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            caption_text = result.get("text", "") if isinstance(result, dict) else str(result)
            
            # Karakter limitini kontrol et
            if len(caption_text) > self.max_post_length:
                caption_text = caption_text[:self.max_post_length]
            
            return {
                "status": "success",
                "caption": caption_text
            }
            
        except Exception as e:
            logger.error(f"Caption oluşturma hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _auto_generate_hashtags(self, topic: str, count: int = 5) -> Dict[str, Any]:
        """
        Verilen konuya göre otomatik hashtag oluşturur.
        
        Args:
            topic: Ana konu
            count: Hashtag sayısı
            
        Returns:
            Oluşturulan hashtagler
        """
        try:
            # LLM aracını al
            llm_tool = self._get_llm_tool()
            if not llm_tool:
                return {"status": "error", "message": "LLM aracı bulunamadı"}
            
            # Prompt oluştur
            system_prompt = """Sen bir sosyal medya hashtag uzmanısın.
            Instagram için etkili, popüler ve konuyla ilgili hashtagler öneriyorsun.
            Hashtaglerin doğru formatlanması, aşırı uzun olmaması ve hedef kitleye uygun olması önemli."""
            
            prompt = f"""
            Lütfen aşağıdaki konu için {count} adet etkili Instagram hashtag'i öner:
            
            Konu: {topic}
            
            Önemli Kurallar:
            1. Hashtagler '#' işareti dahil olmalı ('#örnek' formatında)
            2. Çok genel değil, nişanlı ve konuyla alakalı hashtagler olmalı
            3. Hem popüler hem de orta seviye hashtagler karışık olmalı
            4. Türkçe ve İngilizce hashtagler karışık olabilir
            5. Boşluk içermemeli, çok uzun olmamalı
            
            Sonucu sadece hashtag listesi olarak, JSON formatında döndür:
            
            ```json
            ["#örnek1", "#örnek2", "#örnek3"]
            ```
            
            Sadece hashtag listesini döndür, başka açıklama yapma.
            """
            
            # LLM ile hashtag oluştur
            result = llm_tool.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            text_output = result.get("text", "") if isinstance(result, dict) else str(result)
            
            # JSON çıktıyı temizle ve parse et
            if "```json" in text_output:
                json_text = text_output.split("```json")[1].split("```")[0].strip()
            elif "```" in text_output:
                json_text = text_output.split("```")[1].strip()
            else:
                json_text = text_output.strip()
                
            hashtags = json.loads(json_text)
            
            # Hashtag sayısını kontrol et
            if len(hashtags) > count:
                hashtags = hashtags[:count]
            
            return {
                "status": "success",
                "hashtags": hashtags
            }
            
        except Exception as e:
            logger.error(f"Hashtag oluşturma hatası: {str(e)}")
            return {"status": "error", "message": str(e), "hashtags": [f"#{topic.replace(' ', '')}"]}
    
    def _get_llm_tool(self):
        """LLM aracını almak için yardımcı fonksiyon"""
        try:
            # LLM aracını registry'den al
            for tool_id, metadata in self._registry.get_all_metadata().items():
                if metadata.name == 'llm_tool':
                    return self._registry.get_tool_by_id(tool_id)
            
            logger.warning("LLM aracı bulunamadı")
            return None
        except Exception as e:
            logger.error(f"LLM aracı alınırken hata: {str(e)}")
            return None
    
    def _get_visual_creator(self):
        """VisualCreator aracını almak için yardımcı fonksiyon"""
        try:
            # VisualCreator aracını registry'den al
            for tool_id, metadata in self._registry.get_all_metadata().items():
                if metadata.name == 'visual_creator':
                    return self._registry.get_tool_by_id(tool_id)
            
            logger.warning("VisualCreator aracı bulunamadı")
            return None
        except Exception as e:
            logger.error(f"VisualCreator aracı alınırken hata: {str(e)}")
            return None
    
    def _publish_to_instagram(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Instagram API kullanarak post yayınlar.
        
        Args:
            post: Yayınlanacak post
            
        Returns:
            Yayınlama sonucu
        """
        try:
            # Gerekli kontroller
            if not post["content"]["caption"]:
                return {"status": "error", "message": "Caption boş olamaz"}
            
            if not post.get("visual"):
                return {"status": "error", "message": "Görsel gereklidir"}
            
            # Instagram API bilgilerini kontrol et
            access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
            ig_user_id = os.environ.get("INSTAGRAM_USER_ID")
            
            if not access_token or not ig_user_id:
                return {"status": "error", "message": "Instagram API bilgileri eksik. INSTAGRAM_ACCESS_TOKEN ve INSTAGRAM_USER_ID gereklidir."}
            
            # Görsel URL'sini al - bu dış erişilebilir bir URL olmalı
            image_url = post["visual"].get("image_url")
            local_path = post["visual"].get("local_path")
            
            if not image_url and not local_path:
                return {"status": "error", "message": "Geçerli bir görsel URL'si veya yerel dosya yolu gereklidir"}
            
            # Eğer yerel dosya varsa, bunu Instagram API için bir CDN'e yükleyin
            # Bu örnek için, görsel zaten bir URL'de olduğunu varsayıyoruz
            
            # Instagram Graph API'si üzerinden Post oluşturma
            # 1. Önce medyayı yükle (Container)
            import requests
            
            # Caption ve hashtag'leri birleştir
            caption = post["content"]["caption"]
            hashtags = " ".join(post["content"]["hashtags"]) if post["content"]["hashtags"] else ""
            full_caption = f"{caption}\n\n{hashtags}" if hashtags else caption
            
            # 1. İlk olarak medya container'ı oluştur
            container_url = f"https://graph.facebook.com/v17.0/{ig_user_id}/media"
            container_params = {
                "image_url": image_url,
                "caption": full_caption,
                "access_token": access_token
            }
            
            container_response = requests.post(container_url, params=container_params)
            
            if container_response.status_code != 200:
                logger.error(f"Instagram container oluşturma hatası: {container_response.text}")
                return {"status": "error", "message": f"Instagram container oluşturma hatası: {container_response.text}"}
            
            container_data = container_response.json()
            creation_id = container_data.get("id")
            
            if not creation_id:
                logger.error("Instagram container ID alınamadı")
                return {"status": "error", "message": "Instagram container ID alınamadı"}
            
            # 2. Container'ı kullanarak postu yayınla
            publish_url = f"https://graph.facebook.com/v17.0/{ig_user_id}/media_publish"
            publish_params = {
                "creation_id": creation_id,
                "access_token": access_token
            }
            
            publish_response = requests.post(publish_url, params=publish_params)
            
            if publish_response.status_code != 200:
                logger.error(f"Instagram publish hatası: {publish_response.text}")
                return {"status": "error", "message": f"Instagram publish hatası: {publish_response.text}"}
            
            publish_data = publish_response.json()
            instagram_post_id = publish_data.get("id")
            
            if not instagram_post_id:
                logger.error("Instagram post ID alınamadı")
                return {"status": "error", "message": "Instagram post ID alınamadı"}
            
            # 3. Yayınlanan post bilgilerini al
            media_url = f"https://graph.facebook.com/v17.0/{instagram_post_id}"
            media_params = {
                "fields": "id,permalink",
                "access_token": access_token
            }
            
            media_response = requests.get(media_url, params=media_params)
            
            if media_response.status_code != 200:
                logger.error(f"Instagram medya bilgisi alınamadı: {media_response.text}")
                return {
                    "status": "success",
                    "instagram_post_id": instagram_post_id, 
                    "instagram_post_url": f"https://instagram.com/p/{instagram_post_id}"
                }
            
            media_data = media_response.json()
            instagram_permalink = media_data.get("permalink", f"https://instagram.com/p/{instagram_post_id}")
            
            return {
                "status": "success",
                "instagram_post_id": instagram_post_id,
                "instagram_post_url": instagram_permalink,
                "published_at": time.time()
            }
            
        except Exception as e:
            logger.error(f"Instagram yayınlama hatası: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _trigger_webhook(self, action: str, post: Dict[str, Any]) -> None:
        """
        Webhook'u tetikler (gerçek uygulamada).
        
        Args:
            action: Tetikleme aksiyonu (create, approve, schedule, publish)
            post: İlgili post
        """
        if not self.webhook_url:
            return
        
        try:
            # Webhook veri yapısı
            webhook_data = {
                "action": action,
                "post_id": post["post_id"],
                "status": post["status"],
                "timestamp": time.time(),
                "post_data": post
            }
            
            # Gerçek uygulamada webhook'a HTTP isteği gönderilecek
            logger.info(f"Webhook tetiklendi: {action} - {post['post_id']}")
            
            # Bu kısım gerçek uygulamada HTTP isteği olacak
            # import requests
            # response = requests.post(self.webhook_url, json=webhook_data)
            # logger.info(f"Webhook yanıtı: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Webhook tetikleme hatası: {str(e)}")