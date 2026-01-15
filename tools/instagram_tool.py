"""
Instagram Tool - instagrapi tabanlı Instagram otomasyonu

Bu modül Instagram API fonksiyonlarını MCP tool olarak sağlar.
Kullanıcı login, post oluşturma, story paylaşımı, medya indirme vb.
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, FeedbackRequired
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('/home/ahmet/MetisAgent/MetisAgent2/app')
from mcp_core import MCPTool, MCPToolResult

# Try to import settings_manager
try:
    from .settings_manager import settings_manager
except ImportError:
    try:
        from settings_manager import settings_manager
    except ImportError:
        try:
            sys.path.append('/home/ahmet/MetisAgent/MetisAgent2/tools')
            from settings_manager import settings_manager
        except ImportError:
            settings_manager = None

logger = logging.getLogger(__name__)

class InstagramTool(MCPTool):
    """Instagram otomasyonu için MCP tool"""
    
    def __init__(self):
        """Instagram Tool başlatır"""
        super().__init__(
            name="instagram_tool",
            description="Instagram otomasyonu - login, post, story, medya indirme",
            version="1.0.0"
        )
        
        self.client = Client()
        self.logged_in_user = None
        self.session_info = None
        
        # Register Instagram tool actions
        self._register_actions()
    
    def _register_actions(self):
        """Register all Instagram actions"""
        self.register_action("login", self.login, 
                           required_params=["username", "password", "user_id"])
        self.register_action("logout", self.logout)
        self.register_action("upload_photo", self.upload_photo,
                           required_params=["image_path"], 
                           optional_params=["caption"])
        self.register_action("upload_story", self.upload_story,
                           required_params=["media_path"],
                           optional_params=["story_type"])
        self.register_action("get_user_info", self.get_user_info,
                           required_params=["username"])
        self.register_action("get_followers", self.get_followers,
                           required_params=["user_id"],
                           optional_params=["amount"])
        self.register_action("like_media", self.like_media,
                           required_params=["media_id"])
        self.register_action("comment_media", self.comment_media,
                           required_params=["media_id", "text"])
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """MCP tool tanımını döner"""
        return {
            "name": "instagram_tool",
            "description": "Instagram otomasyonu - login, post, story, medya indirme",
            "methods": [
                {
                    "name": "login",
                    "description": "Instagram hesabına giriş yap",
                    "parameters": {
                        "username": {"type": "string", "description": "Instagram kullanıcı adı"},
                        "password": {"type": "string", "description": "Instagram şifresi"},
                        "user_id": {"type": "string", "description": "MetisAgent kullanıcı ID'si"}
                    }
                },
                {
                    "name": "logout",
                    "description": "Instagram hesabından çıkış yap",
                    "parameters": {}
                },
                {
                    "name": "upload_photo",
                    "description": "Fotoğraf paylaş",
                    "parameters": {
                        "image_path": {"type": "string", "description": "Paylaşılacak fotoğraf yolu"},
                        "caption": {"type": "string", "description": "Fotoğraf açıklaması"}
                    }
                },
                {
                    "name": "upload_story",
                    "description": "Story paylaş",
                    "parameters": {
                        "media_path": {"type": "string", "description": "Story medya yolu"},
                        "story_type": {"type": "string", "description": "photo veya video"}
                    }
                },
                {
                    "name": "get_user_info",
                    "description": "Kullanıcı bilgilerini getir",
                    "parameters": {
                        "username": {"type": "string", "description": "Instagram kullanıcı adı"}
                    }
                },
                {
                    "name": "download_media",
                    "description": "Medya indir",
                    "parameters": {
                        "media_url": {"type": "string", "description": "Instagram medya URL'i"},
                        "save_path": {"type": "string", "description": "Kayıt yolu"}
                    }
                },
                {
                    "name": "get_followers",
                    "description": "Takipçi listesi getir",
                    "parameters": {
                        "user_id": {"type": "string", "description": "Instagram user ID"},
                        "amount": {"type": "integer", "description": "Getir sayısı (default: 50)"}
                    }
                },
                {
                    "name": "get_following",
                    "description": "Takip edilen listesi getir",
                    "parameters": {
                        "user_id": {"type": "string", "description": "Instagram user ID"},
                        "amount": {"type": "integer", "description": "Getir sayısı (default: 50)"}
                    }
                },
                {
                    "name": "like_media",
                    "description": "Medyayı beğen",
                    "parameters": {
                        "media_id": {"type": "string", "description": "Medya ID'si"}
                    }
                },
                {
                    "name": "unlike_media",
                    "description": "Medya beğenisini kaldır",
                    "parameters": {
                        "media_id": {"type": "string", "description": "Medya ID'si"}
                    }
                },
                {
                    "name": "comment_media",
                    "description": "Medyaya yorum yap",
                    "parameters": {
                        "media_id": {"type": "string", "description": "Medya ID'si"},
                        "text": {"type": "string", "description": "Yorum metni"}
                    }
                }
            ]
        }
    
    def _save_instagram_credentials(self, user_id: str, username: str, password: str) -> bool:
        """Instagram credentials'ı güvenli kaydet"""
        try:
            additional_info = {
                "username": username,
                "login_date": datetime.now().isoformat(),
                "platform": "instagram"
            }
            
            return settings_manager.save_api_key(
                user_id=user_id,
                service="instagram", 
                api_key=password,
                additional_info=additional_info
            )
        except Exception as e:
            logger.error(f"Instagram credentials kaydetme hatası: {e}")
            return False
    
    def _get_instagram_credentials(self, user_id: str) -> Optional[Dict[str, str]]:
        """Instagram credentials'ı getir"""
        try:
            creds = settings_manager.get_api_key(user_id, "instagram")
            if not creds:
                return None
                
            return {
                "username": creds["additional_info"]["username"],
                "password": creds["api_key"]
            }
        except Exception as e:
            logger.error(f"Instagram credentials getirme hatası: {e}")
            return None
    
    def login(self, username: str, password: str, user_id: str, **kwargs) -> MCPToolResult:
        """Instagram hesabına giriş yap"""
        try:
            # Önceki session'ı temizle
            self.client = Client()
            
            # Giriş yap
            logger.info(f"Instagram login başlatılıyor: {username}")
            
            # Session dosyası varsa yükle
            session_file = f"/tmp/instagram_session_{username}.json"
            if os.path.exists(session_file):
                try:
                    self.client.load_settings(session_file)
                    logger.info("Instagram session dosyası yüklendi")
                except:
                    pass
            
            # Login işlemi
            login_result = self.client.login(username, password)
            
            if login_result:
                self.logged_in_user = username
                
                # Session'ı kaydet
                try:
                    self.client.dump_settings(session_file)
                    logger.info("Instagram session kaydedildi")
                except:
                    pass
                
                # Credentials'ı güvenli kaydet
                self._save_instagram_credentials(user_id, username, password)
                
                # Kullanıcı bilgilerini al
                try:
                    user_info = self.client.account_info()
                    user_data = {
                        "username": getattr(user_info, 'username', username),
                        "full_name": getattr(user_info, 'full_name', ''),
                        "follower_count": getattr(user_info, 'follower_count', 0),
                        "following_count": getattr(user_info, 'following_count', 0),
                        "media_count": getattr(user_info, 'media_count', 0),
                        "is_verified": getattr(user_info, 'is_verified', False),
                        "is_private": getattr(user_info, 'is_private', False)
                    }
                except Exception as info_error:
                    logger.warning(f"Kullanıcı bilgileri alınamadı: {info_error}")
                    user_data = {
                        "username": username,
                        "full_name": "",
                        "follower_count": 0,
                        "following_count": 0,
                        "media_count": 0,
                        "is_verified": False,
                        "is_private": False
                    }
                
                return MCPToolResult(
                    success=True,
                    data={
                        "message": f"Instagram'a giriş başarılı: {username}",
                        "user_info": user_data
                    }
                )
            else:
                return MCPToolResult(
                    success=False,
                    error="Instagram login başarısız"
                )
                
        except ChallengeRequired as e:
            logger.error(f"Instagram challenge gerekli: {e}")
            return MCPToolResult(
                success=False,
                error=f"Instagram güvenlik doğrulaması gerekli: {str(e)}"
            )
        except LoginRequired as e:
            logger.error(f"Instagram login gerekli: {e}")
            return MCPToolResult(
                success=False,
                error=f"Instagram login gerekli: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Instagram login hatası: {e}")
            return MCPToolResult(
                success=False,
                error=f"Instagram login hatası: {str(e)}"
            )
    
    def logout(self, **kwargs) -> MCPToolResult:
        """Instagram hesabından çıkış yap"""
        try:
            if self.logged_in_user:
                self.client.logout()
                self.logged_in_user = None
                logger.info("Instagram logout başarılı")
                
                return MCPToolResult(
                    success=True,
                    data={"message": "Instagram'dan çıkış yapıldı"}
                )
            else:
                return MCPToolResult(
                    success=False,
                    error="Aktif Instagram session bulunamadı"
                )
        except Exception as e:
            logger.error(f"Instagram logout hatası: {e}")
            return MCPToolResult(
                success=False,
                error=f"Logout hatası: {str(e)}"
            )
    
    def upload_photo(self, image_path: str, caption: str = "") -> Dict[str, Any]:
        """Fotoğraf paylaş"""
        try:
            if not self.logged_in_user:
                return {
                    "success": False,
                    "message": "Instagram'a giriş yapılmamış",
                    "error": "not_logged_in"
                }
            
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "message": f"Fotoğraf bulunamadı: {image_path}",
                    "error": "file_not_found"
                }
            
            logger.info(f"Instagram fotoğraf paylaşımı başlatılıyor: {image_path}")
            
            # Fotoğraf paylaş
            media = self.client.photo_upload(image_path, caption)
            
            return {
                "success": True,
                "message": "Fotoğraf başarıyla paylaşıldı",
                "media_info": {
                    "media_id": media.id,
                    "code": media.code,
                    "taken_at": media.taken_at.isoformat() if media.taken_at else None,
                    "like_count": media.like_count,
                    "caption": caption
                }
            }
            
        except Exception as e:
            logger.error(f"Instagram fotoğraf paylaşım hatası: {e}")
            return {
                "success": False,
                "message": f"Fotoğraf paylaşım hatası: {str(e)}",
                "error": "upload_error"
            }
    
    def upload_story(self, media_path: str, story_type: str = "photo") -> Dict[str, Any]:
        """Story paylaş"""
        try:
            if not self.logged_in_user:
                return {
                    "success": False,
                    "message": "Instagram'a giriş yapılmamış",
                    "error": "not_logged_in"
                }
            
            if not os.path.exists(media_path):
                return {
                    "success": False,
                    "message": f"Medya bulunamadı: {media_path}",
                    "error": "file_not_found"
                }
            
            logger.info(f"Instagram story paylaşımı başlatılıyor: {media_path}")
            
            # Story paylaş
            if story_type.lower() == "video":
                media = self.client.video_upload_to_story(media_path)
            else:
                media = self.client.photo_upload_to_story(media_path)
            
            return {
                "success": True,
                "message": "Story başarıyla paylaşıldı",
                "media_info": {
                    "media_id": media.id,
                    "taken_at": media.taken_at.isoformat() if media.taken_at else None,
                    "story_type": story_type
                }
            }
            
        except Exception as e:
            logger.error(f"Instagram story paylaşım hatası: {e}")
            return {
                "success": False,
                "message": f"Story paylaşım hatası: {str(e)}",
                "error": "story_upload_error"
            }
    
    def get_user_info(self, username: str) -> Dict[str, Any]:
        """Kullanıcı bilgilerini getir"""
        try:
            if not self.logged_in_user:
                return {
                    "success": False,
                    "message": "Instagram'a giriş yapılmamış",
                    "error": "not_logged_in"
                }
            
            logger.info(f"Instagram kullanıcı bilgisi getiriliyor: {username}")
            
            # Kullanıcı bilgilerini al
            user_info = self.client.user_info_by_username(username)
            
            return {
                "success": True,
                "user_info": {
                    "user_id": user_info.pk,
                    "username": user_info.username,
                    "full_name": user_info.full_name,
                    "biography": user_info.biography,
                    "follower_count": user_info.follower_count,
                    "following_count": user_info.following_count,
                    "media_count": user_info.media_count,
                    "is_verified": user_info.is_verified,
                    "is_private": user_info.is_private,
                    "is_business": user_info.is_business,
                    "profile_pic_url": user_info.profile_pic_url,
                    "external_url": user_info.external_url
                }
            }
            
        except Exception as e:
            logger.error(f"Instagram kullanıcı bilgisi hatası: {e}")
            return {
                "success": False,
                "message": f"Kullanıcı bilgisi getirme hatası: {str(e)}",
                "error": "user_info_error"
            }
    
    def get_followers(self, user_id: str, amount: int = 50) -> Dict[str, Any]:
        """Takipçi listesi getir"""
        try:
            if not self.logged_in_user:
                return {
                    "success": False,
                    "message": "Instagram'a giriş yapılmamış",
                    "error": "not_logged_in"
                }
            
            logger.info(f"Instagram takipçi listesi getiriliyor: {user_id}")
            
            # Takipçi listesi al
            followers = self.client.user_followers(int(user_id), amount=amount)
            
            follower_list = []
            for follower_id, follower in followers.items():
                follower_list.append({
                    "user_id": follower.pk,
                    "username": follower.username,
                    "full_name": follower.full_name,
                    "is_verified": follower.is_verified,
                    "is_private": follower.is_private,
                    "profile_pic_url": follower.profile_pic_url
                })
            
            return {
                "success": True,
                "followers": follower_list,
                "count": len(follower_list)
            }
            
        except Exception as e:
            logger.error(f"Instagram takipçi listesi hatası: {e}")
            return {
                "success": False,
                "message": f"Takipçi listesi getirme hatası: {str(e)}",
                "error": "followers_error"
            }
    
    def like_media(self, media_id: str) -> Dict[str, Any]:
        """Medyayı beğen"""
        try:
            if not self.logged_in_user:
                return {
                    "success": False,
                    "message": "Instagram'a giriş yapılmamış",
                    "error": "not_logged_in"
                }
            
            logger.info(f"Instagram medya beğeniliyor: {media_id}")
            
            # Medyayı beğen
            result = self.client.media_like(media_id)
            
            return {
                "success": result,
                "message": "Medya beğenildi" if result else "Medya beğenme başarısız",
                "media_id": media_id
            }
            
        except Exception as e:
            logger.error(f"Instagram medya beğenme hatası: {e}")
            return {
                "success": False,
                "message": f"Medya beğenme hatası: {str(e)}",
                "error": "like_error"
            }
    
    def comment_media(self, media_id: str, text: str) -> Dict[str, Any]:
        """Medyaya yorum yap"""
        try:
            if not self.logged_in_user:
                return {
                    "success": False,
                    "message": "Instagram'a giriş yapılmamış",
                    "error": "not_logged_in"
                }
            
            logger.info(f"Instagram medya yorumu yapılıyor: {media_id}")
            
            # Yorum yap
            comment = self.client.media_comment(media_id, text)
            
            return {
                "success": True,
                "message": "Yorum başarıyla eklendi",
                "comment_info": {
                    "comment_id": comment.pk,
                    "text": comment.text,
                    "created_at": comment.created_at.isoformat() if comment.created_at else None,
                    "media_id": media_id
                }
            }
            
        except Exception as e:
            logger.error(f"Instagram yorum hatası: {e}")
            return {
                "success": False,
                "message": f"Yorum ekleme hatası: {str(e)}",
                "error": "comment_error"
            }

# Global instance
instagram_tool = InstagramTool()

def register_tool(registry):
    """Register Instagram tool with the registry"""
    try:
        tool = InstagramTool()
        registry.register_tool(tool)
        logger.info(f"Instagram tool registered successfully: {tool.name}")
        return True
    except Exception as e:
        logger.error(f"Error registering Instagram tool: {e}")
        return False

# Export for MCP tool loading
__all__ = ['InstagramTool', 'register_tool', 'instagram_tool']