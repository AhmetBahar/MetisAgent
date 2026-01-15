"""
Authentication routes - user registration, login, authentication
"""
from flask import request, jsonify
from flask_cors import cross_origin
import logging
from os_araci.auth.auth_manager import AuthManager

logger = logging.getLogger(__name__)

def register_auth_routes(app):
    """Register authentication routes"""
    
    # Initialize AuthManager
    auth_manager = AuthManager()

    @app.route('/api/auth/register', methods=['POST'])
    def register_user():
        """Yeni kullanıcı kaydı"""
        try:
            data = request.get_json()
            logger.info(f"Kayıt verisi: {data}")
            
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            
            if not username or not email or not password:
                logger.warning("Eksik alanlar var")
                return jsonify({"status": "error", "message": "Tüm alanlar gereklidir"}), 400
            
            logger.info(f"Kullanıcı oluşturuluyor: {username}")
            result = auth_manager.create_user(username, password, permissions=["user"])
            
            logger.info(f"Kullanıcı oluşturma sonucu: {result}")
            
            if result.get("status") == "success":
                return jsonify(result), 201
            else:
                logger.warning(f"Kullanıcı kaydı başarısız: {result.get('message')}")
                return jsonify(result), 400
            
        except Exception as e:
            logger.error(f"Kullanıcı kaydı sırasında hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
    @cross_origin(origins="http://localhost:3000", supports_credentials=True)
    def login_user():
        """Kullanıcı girişi"""
        if request.method == 'OPTIONS':
            return jsonify({"status": "ok"}), 200
            
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return jsonify({"status": "error", "message": "Username and password required"}), 400
            
            logger.info(f"Login isteği alındı: {username}")
            result = auth_manager.authenticate_user(username, password)
            logger.info(f"Doğrulama sonucu: {result}")
            
            if result.get("status") == "success":
                return jsonify(result), 200
            else:
                return jsonify(result), 401
            
        except Exception as e:
            logger.error(f"Kullanıcı girişi sırasında hata: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/auth/check_user/<username>', methods=['GET'])
    def check_user(username):
        """Test: Kullanıcının varlığını kontrol et"""
        try:
            user = auth_manager.get_user(username)
            if user:
                return jsonify({"exists": True, "message": f"Kullanıcı mevcut: {username}"}), 200
            else:
                return jsonify({"exists": False, "message": f"Kullanıcı bulunamadı: {username}"}), 200
        except Exception as e:
            logger.error(f"Kullanıcı kontrolü sırasında hata: {str(e)}")
            return jsonify({"error": str(e)}), 500

    logger.info("Auth routes registered")