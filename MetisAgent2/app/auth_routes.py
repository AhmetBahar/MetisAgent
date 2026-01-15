"""
Authentication routes - user registration, login, authentication
"""
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
from .auth_manager import auth_manager

logger = logging.getLogger(__name__)

# Create auth blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
@cross_origin()
def register_user():
    """Yeni kullanıcı kaydı"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({"status": "error", "message": "Tüm alanlar gereklidir"}), 400
        
        # Kullanıcı adı ve email validasyonu
        if len(username) < 3:
            return jsonify({"status": "error", "message": "Kullanıcı adı en az 3 karakter olmalıdır"}), 400
            
        if len(password) < 6:
            return jsonify({"status": "error", "message": "Şifre en az 6 karakter olmalıdır"}), 400
        
        logger.info(f"Kullanıcı kaydı isteği: {username}")
        result = auth_manager.create_user(username, password, email, permissions=["user"])
        
        if result.get("status") == "success":
            logger.info(f"Kullanıcı başarıyla kaydedildi: {username}")
            return jsonify({
                "status": "success",
                "message": "Kullanıcı başarıyla oluşturuldu",
                "user_id": result["user_id"]
            }), 201
        else:
            logger.warning(f"Kullanıcı kaydı başarısız: {username}, {result.get('message')}")
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Kullanıcı kaydı sırasında hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
@cross_origin()
def login_user():
    """Kullanıcı girişi"""
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"status": "error", "message": "Username and password required"}), 400
        
        logger.info(f"Login isteği: {username}")
        result = auth_manager.authenticate_user(username, password)
        
        if result.get("status") == "success":
            logger.info(f"Kullanıcı başarıyla giriş yaptı: {username}")
            
            # Session başladığında Google token refresh kontrol et
            try:
                # Tool manager üzerinden tools'ları al
                from app import app
                tool_manager = getattr(app, 'tool_manager', None)
                
                if tool_manager and hasattr(tool_manager, 'get_tool'):
                    oauth2_tool = tool_manager.get_tool('google_oauth2_manager')
                    settings_tool = tool_manager.get_tool('settings_manager')
                    
                    if oauth2_tool and settings_tool:
                        user_id = result["user_id"]
                        try:
                            # Google credentials'ı kontrol et
                            creds_result = settings_tool.invoke("_get_oauth2_credentials", {
                                "user_id": user_id,
                                "provider": "google"
                            })
                            
                            if (creds_result.get("success") and 
                                creds_result.get("credentials") and 
                                creds_result["credentials"].get("refresh_token")):
                                
                                logger.info(f"Google credentials bulundu, token refresh yapılıyor: {user_id}")
                                
                                # Token refresh yap
                                refresh_result = oauth2_tool.invoke("refresh_access_token", {
                                    "user_id": user_id
                                })
                                
                                if refresh_result.get("success"):
                                    logger.info(f"Google token başarıyla refresh edildi: {user_id}")
                                else:
                                    logger.warning(f"Google token refresh başarısız: {user_id} - {refresh_result.get('error', 'Unknown error')}")
                            else:
                                logger.debug(f"Google credentials bulunamadı veya refresh token yok: {user_id}")
                        except Exception as refresh_error:
                            logger.warning(f"Google token refresh sırasında hata: {user_id} - {str(refresh_error)}")
                
            except Exception as e:
                logger.warning(f"Google token refresh kontrolü sırasında hata: {str(e)}")
            
            return jsonify({
                "status": "success",
                "message": "Giriş başarılı",
                "user": {
                    "user_id": result["user_id"],
                    "username": result["username"],
                    "email": result.get("email"),
                    "permissions": result["permissions"]
                },
                "session_token": result["session_token"]
            }), 200
        else:
            logger.warning(f"Giriş başarısız: {username}")
            return jsonify(result), 401
        
    except Exception as e:
        logger.error(f"Kullanıcı girişi sırasında hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@cross_origin()
def logout_user():
    """Kullanıcı çıkışı"""
    try:
        # JSON'dan session token'ı al
        data = None
        session_token = None
        
        # Content-Type'a göre veri alma
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            data = request.get_json()
            session_token = data.get('session_token') if data else None
        
        # Header'dan da session token'ı kontrol et
        if not session_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                session_token = auth_header[7:]
        
        if not session_token:
            return jsonify({"status": "error", "message": "Session token required"}), 400
        
        result = auth_manager.logout_user(session_token)
        
        if result:
            return jsonify({"status": "success", "message": "Çıkış başarılı"}), 200
        else:
            return jsonify({"status": "error", "message": "Çıkış yapılamadı"}), 400
            
    except Exception as e:
        logger.error(f"Kullanıcı çıkışı sırasında hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@auth_bp.route('/validate', methods=['POST'])
@cross_origin()
def validate_session():
    """Session token doğrulama"""
    try:
        data = request.get_json()
        session_token = data.get('session_token') if data else None
        
        # Header'dan da session token'ı kontrol et
        if not session_token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                session_token = auth_header[7:]
        
        if not session_token:
            return jsonify({"status": "error", "message": "Session token required"}), 400
        
        user_info = auth_manager.validate_session(session_token)
        
        if user_info:
            # Session geçerliyse Google token refresh kontrol et
            try:
                # Tool manager üzerinden tools'ları al
                from app import app
                tool_manager = getattr(app, 'tool_manager', None)
                
                if tool_manager and hasattr(tool_manager, 'get_tool'):
                    oauth2_tool = tool_manager.get_tool('google_oauth2_manager')
                    settings_tool = tool_manager.get_tool('settings_manager')
                
                if oauth2_tool and settings_tool:
                    user_id = user_info.get("user_id")
                    if user_id:
                        try:
                            # Google credentials'ı kontrol et
                            creds_result = settings_tool.invoke("_get_oauth2_credentials", {
                                "user_id": user_id,
                                "provider": "google"
                            })
                            
                            if (creds_result.get("success") and 
                                creds_result.get("credentials") and 
                                creds_result["credentials"].get("refresh_token")):
                                
                                # Token refresh yap (sessiz, sadece log)
                                refresh_result = oauth2_tool.invoke("refresh_access_token", {
                                    "user_id": user_id
                                })
                                
                                if refresh_result.get("success"):
                                    logger.debug(f"Google token session validation sırasında refresh edildi: {user_id}")
                                else:
                                    logger.debug(f"Google token refresh (validation) başarısız: {user_id}")
                                    
                        except Exception as refresh_error:
                            logger.debug(f"Google token refresh (validation) hatası: {user_id} - {str(refresh_error)}")
                
            except Exception as e:
                logger.debug(f"Google token refresh kontrolü (validation) hatası: {str(e)}")
            
            return jsonify({
                "status": "success",
                "valid": True,
                "user": user_info
            }), 200
        else:
            return jsonify({
                "status": "error",
                "valid": False,
                "message": "Invalid or expired session"
            }), 401
            
    except Exception as e:
        logger.error(f"Session doğrulama sırasında hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
@cross_origin()
def get_current_user():
    """Mevcut kullanıcı bilgilerini getir"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"status": "error", "message": "Authorization header required"}), 401
        
        session_token = auth_header[7:]
        user_info = auth_manager.get_user_by_session(session_token)
        
        if user_info:
            return jsonify({
                "status": "success",
                "user": {
                    "user_id": user_info["user_id"],
                    "username": user_info["username"],
                    "email": user_info.get("email"),
                    "permissions": user_info["permissions"],
                    "status": user_info.get("status")
                }
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Invalid or expired session"
            }), 401
            
    except Exception as e:
        logger.error(f"Get current user sırasında hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
@cross_origin()
def change_password():
    """Kullanıcı şifresi değiştirme"""
    try:
        # Authorization header kontrolü
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"status": "error", "message": "Authorization header required"}), 401
        
        session_token = auth_header[7:]
        user_info = auth_manager.get_user_by_session(session_token)
        
        if not user_info:
            return jsonify({"status": "error", "message": "Invalid or expired session"}), 401
        
        # Request data validation
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not old_password or not new_password or not confirm_password:
            return jsonify({"status": "error", "message": "Tüm alanlar gereklidir"}), 400
        
        if new_password != confirm_password:
            return jsonify({"status": "error", "message": "Yeni şifreler eşleşmiyor"}), 400
        
        # Şifre güncelleme
        result = auth_manager.update_password(
            username=user_info["username"],
            old_password=old_password,
            new_password=new_password
        )
        
        if result["status"] == "success":
            logger.info(f"Şifre başarıyla güncellendi: {user_info['username']}")
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Şifre değiştirme sırasında hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@auth_bp.route('/create-api-key', methods=['POST'])
@cross_origin()
def create_api_key():
    """Yeni API anahtarı oluştur"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"status": "error", "message": "Authorization header required"}), 401
        
        session_token = auth_header[7:]
        user_info = auth_manager.get_user_by_session(session_token)
        
        if not user_info:
            return jsonify({"status": "error", "message": "Invalid session"}), 401
        
        data = request.get_json() or {}
        permissions = data.get('permissions', ['read'])
        
        result = auth_manager.create_api_key(user_info["username"], permissions)
        
        if result.get("status") == "success":
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"API key oluşturma sırasında hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@auth_bp.route('/check_user/<username>', methods=['GET'])
@cross_origin()
def check_user(username):
    """Kullanıcının varlığını kontrol et (geliştirme amaçlı)"""
    try:
        user = auth_manager.get_user(username)
        if user:
            return jsonify({
                "exists": True, 
                "message": f"Kullanıcı mevcut: {username}",
                "status": user.get("status")
            }), 200
        else:
            return jsonify({
                "exists": False, 
                "message": f"Kullanıcı bulunamadı: {username}"
            }), 200
    except Exception as e:
        logger.error(f"Kullanıcı kontrolü sırasında hata: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Session cleanup endpoint (admin only)
@auth_bp.route('/cleanup-sessions', methods=['POST'])
@cross_origin()
def cleanup_sessions():
    """Süresi dolmuş oturumları temizle"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"status": "error", "message": "Authorization header required"}), 401
        
        session_token = auth_header[7:]
        user_info = auth_manager.get_user_by_session(session_token)
        
        if not user_info or "*" not in user_info.get("permissions", []):
            return jsonify({"status": "error", "message": "Admin permission required"}), 403
        
        cleaned_count = auth_manager.cleanup_sessions()
        
        return jsonify({
            "status": "success",
            "message": f"{cleaned_count} oturum temizlendi"
        }), 200
        
    except Exception as e:
        logger.error(f"Session cleanup sırasında hata: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

logger.info("Auth routes registered")