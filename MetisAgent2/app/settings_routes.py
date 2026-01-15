"""
Settings API Routes - Kullanıcı ayarları ve API key yönetimi

Bu blueprint settings ve authentication işlemlerini yönetir
"""

import logging
import os
from flask import Blueprint, request, jsonify, session, redirect, url_for
from functools import wraps
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.internal.settings_manager import get_settings_manager

logger = logging.getLogger(__name__)

# Blueprint oluştur
settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

@settings_bp.after_request
def after_request(response):
    """Her response'a CORS header'ları ekle"""
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

def require_auth(f):
    """Authentication gerekli endpoint'ler için decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # İlk önce session'da user_id kontrol et (Google OAuth için)
        if 'user_id' in session:
            return f(*args, **kwargs)
        
        # Session yoksa, Authorization header'dan token kontrol et (Normal login için)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
            
            # Token'ı doğrula
            from .auth_manager import auth_manager
            user_info = auth_manager.validate_session(session_token)
            
            if user_info:
                # Session'a kullanıcı bilgilerini ekle (compat için)
                session['user_id'] = user_info.get('email', user_info['user_id'])  # Email'i user_id olarak kullan
                session['username'] = user_info['username'] 
                session['user_email'] = user_info.get('email', '')
                return f(*args, **kwargs)
        
        return jsonify({'error': 'Authentication required'}), 401
    return decorated_function

@settings_bp.route('/user/settings', methods=['GET'])
@require_auth
def get_user_settings():
    """Kullanıcı ayarlarını getirir"""
    try:
        user_id = session['user_id']
        settings_manager = get_settings_manager()
        # Get user profile and settings
        profile = settings_manager.get_user_profile(user_id) or {}
        settings = profile.get('settings', {})
        
        if settings:
            return jsonify({
                'success': True,
                'settings': settings
            })
        else:
            return jsonify({
                'success': True,
                'settings': {}  # Boş ayarlar
            })
            
    except Exception as e:
        logger.error(f"Ayarları getirme hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/user/settings', methods=['POST'])
@require_auth
def save_user_settings():
    """Kullanıcı ayarlarını kaydeder"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        settings = data.get('settings', {})
        settings_manager = get_settings_manager()
        success = settings_manager.set_user_setting(user_id, 'user_settings', settings)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Settings saved successfully'
            })
        else:
            return jsonify({'error': 'Failed to save settings'}), 500
            
    except Exception as e:
        logger.error(f"Ayarları kaydetme hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/api-keys', methods=['GET'])
@require_auth
def list_api_keys():
    """Kullanıcının API keylerini listeler"""
    try:
        user_id = session['user_id']
        settings_manager = get_settings_manager()
        # Get all properties and filter API keys
        all_properties = settings_manager.storage.get_all_properties(user_id)
        api_keys = {k.replace('api_key_', ''): v for k, v in all_properties.items() if k.startswith('api_key_')}
        
        return jsonify({
            'success': True,
            'api_keys': api_keys
        })
        
    except Exception as e:
        logger.error(f"API key listesi hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/api-keys', methods=['POST'])
@require_auth
def save_api_key():
    """API key kaydeder"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        service = data.get('service')
        api_key = data.get('api_key')
        additional_info = data.get('additional_info', {})
        
        if not service or not api_key:
            return jsonify({'error': 'Service and API key required'}), 400
        
        settings_manager = get_settings_manager()
        success = settings_manager.set_api_key(user_id, service, api_key)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'API key saved for {service}'
            })
        else:
            return jsonify({'error': 'Failed to save API key'}), 500
            
    except Exception as e:
        logger.error(f"API key kaydetme hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/api-keys/<service>', methods=['GET'])
@require_auth
def get_api_key(service):
    """Belirli bir servis için API key getirir"""
    try:
        user_id = session['user_id']
        settings_manager = get_settings_manager()
        api_key_data = settings_manager.storage.get_api_key(user_id, service)
        
        if api_key_data:
            # Güvenlik için API key'i kısalt
            api_key = api_key_data['api_key']
            masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
            
            return jsonify({
                'success': True,
                'service': service,
                'api_key_masked': masked_key,
                'has_key': True,
                'metadata': api_key_data['metadata'],
                'additional_info': api_key_data.get('additional_info', {})
            })
        else:
            return jsonify({
                'success': True,
                'service': service,
                'has_key': False
            })
            
    except Exception as e:
        logger.error(f"API key getirme hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/api-keys/<service>', methods=['DELETE'])
@require_auth
def delete_api_key(service):
    """API key siler"""
    try:
        user_id = session['user_id']
        settings_manager = get_settings_manager()
        success = settings_manager.storage.delete_property(user_id, f'api_key_{service}')
        
        if success:
            return jsonify({
                'success': True,
                'message': f'API key deleted for {service}'
            })
        else:
            return jsonify({'error': 'Failed to delete API key'}), 500
            
    except Exception as e:
        logger.error(f"API key silme hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Google OAuth Routes
@settings_bp.route('/auth/google/setup', methods=['POST'])
def setup_google_oauth():
    """Google OAuth ayarlarını yapılandırır (Admin only)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        redirect_uri = data.get('redirect_uri')
        
        if not client_id or not client_secret:
            return jsonify({'error': 'Client ID and secret required'}), 400
        
        settings_manager = get_settings_manager()
        success = settings_manager.set_google_client_credentials(client_id, client_secret)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Google OAuth configured successfully'
            })
        else:
            return jsonify({'error': 'Failed to configure Google OAuth'}), 500
            
    except Exception as e:
        logger.error(f"Google OAuth setup hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/auth/google/login', methods=['GET', 'OPTIONS'])
def google_login():
    """Google OAuth giriş başlatır"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        settings_manager = get_settings_manager()
        google_creds = settings_manager.get_google_client_credentials()
        auth_url = f"https://accounts.google.com/o/oauth2/auth?client_id={google_creds['client_id']}&redirect_uri=http://localhost:5001/oauth2/google/callback&scope=openid email profile&response_type=code"
        
        if auth_url:
            return jsonify({
                'success': True,
                'auth_url': auth_url
            })
        else:
            return jsonify({'error': 'Google OAuth not configured'}), 500
            
    except Exception as e:
        logger.error(f"Google login hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/auth/google/callback', methods=['GET'])
def google_callback():
    """Google OAuth callback işler"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        # Frontend URL'i settings'den al
        settings_manager = get_settings_manager()
        frontend_config = settings_manager.storage.get_api_key('admin', 'frontend_config')
        frontend_url = 'http://localhost:3000'
        if frontend_config and 'metadata' in frontend_config:
            frontend_url = frontend_config['metadata'].get('url', frontend_url)
        
        if error:
            logger.error(f"Google OAuth error: {error}")
            return redirect(f'{frontend_url}/?error=oauth_error')
        
        if not code or not state:
            return redirect(f'{frontend_url}/?error=missing_params')
        
        # OAuth2 callback handling would be done via GoogleOAuth2Manager tool
        success, user_info = False, None
        
        if success and user_info:
            # Google OAuth ile gelen kullanıcıyı sistem kullanıcılarıyla eşleştir
            from .auth_manager import auth_manager
            
            # Email ile mevcut kullanıcıyı bul veya yeni oluştur
            google_email = user_info['email']
            google_name = user_info.get('name', '')
            google_id = user_info['id']
            
            # Önce email ile mevcut kullanıcı ara
            existing_user = auth_manager.get_user_by_email(google_email)
            
            if existing_user:
                # Mevcut kullanıcı var, session token oluştur
                session_token = auth_manager.create_session_token(existing_user['user_id'])
                user_id = existing_user['user_id']
                logger.info(f"Google OAuth mevcut kullanıcı: {google_email}")
            else:
                # Yeni kullanıcı oluştur
                username = google_email.split('@')[0]  # Email'den username yap
                # Google OAuth kullanıcıları için özel şifre
                temp_password = f"google_oauth_{google_id}"
                
                user_result = auth_manager.create_user(username, temp_password, google_email, permissions=["user"])
                
                if user_result.get("status") == "success":
                    user_id = user_result["user_id"]
                    session_token = auth_manager.create_session_token(user_id)
                    logger.info(f"Google OAuth yeni kullanıcı oluşturuldu: {google_email}")
                else:
                    logger.error(f"Google OAuth kullanıcı oluşturma hatası: {user_result}")
                    return redirect(f'{frontend_url}/?error=user_creation_failed')
            
            # Session'da kullanıcı bilgilerini sakla (compat için)
            session['user_id'] = user_id
            session['user_email'] = google_email
            session['user_name'] = google_name
            session['user_picture'] = user_info.get('picture', '')
            session['session_token'] = session_token
            
            logger.info(f"Google OAuth başarılı: {google_email}")
            return redirect(f'{frontend_url}/?login=success&token={session_token}')
        else:
            logger.error("Google OAuth callback başarısız")
            return redirect(f'{frontend_url}/?error=callback_failed')
            
    except Exception as e:
        logger.error(f"Google callback hatası: {e}")
        return redirect(f'{frontend_url}/?error=internal_error')

@settings_bp.route('/auth/status', methods=['GET', 'OPTIONS'])
def auth_status():
    """Kullanıcı authentication durumunu kontrol et"""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        # Session token'ı kontrol et
        session_token = None
        
        # Authorization header'dan token'ı al
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
        
        # Session token varsa doğrula
        if session_token:
            from .auth_manager import auth_manager
            user_info = auth_manager.validate_session(session_token)
            
            if user_info:
                return jsonify({
                    'authenticated': True,
                    'user': {
                        'id': user_info['user_id'],
                        'username': user_info['username'],
                        'email': user_info.get('email', ''),
                        'name': user_info.get('username', ''),
                        'picture': ''
                    }
                })
        
        # Session fallback (Google OAuth için)
        if 'user_id' in session:
            return jsonify({
                'authenticated': True,
                'user': {
                    'id': session['user_id'],
                    'email': session.get('user_email', ''),
                    'name': session.get('user_name', ''),
                    'picture': session.get('user_picture', '')
                }
            })
        else:
            return jsonify({'authenticated': False})
            
    except Exception as e:
        logger.error(f"Auth status kontrolü hatası: {e}")
        return jsonify({'authenticated': False, 'error': str(e)}), 500

@settings_bp.route('/auth/logout', methods=['POST'])
def logout():
    """Kullanıcıyı çıkış yapar"""
    try:
        user_id = session.get('user_id')
        
        if user_id:
            # Logout handling via settings_manager
            settings_manager = get_settings_manager()
            # Remove OAuth tokens
            settings_manager.storage.delete_property(user_id, 'oauth_google')
        
        # Session'ı temizle
        session.clear()
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })
        
    except Exception as e:
        logger.error(f"Logout hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/auth/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """Kullanıcı profil bilgilerini getirir"""
    try:
        user_id = session['user_id']
        
        # Session'dan bilgileri al
        profile = {
            'id': user_id,
            'email': session.get('user_email'),
            'name': session.get('user_name'),
            'picture': session.get('user_picture')
        }
        
        # Settings manager'dan profil bilgilerini al
        settings_manager = get_settings_manager()
        stored_profile = settings_manager.get_user_profile(user_id)
        if stored_profile:
            profile.update(stored_profile)
        
        return jsonify({
            'success': True,
            'profile': profile
        })
        
    except Exception as e:
        logger.error(f"Profil getirme hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/auth/status', methods=['GET'])
def get_auth_status():
    """Authentication durumunu kontrol eder"""
    try:
        if 'user_id' in session:
            user_id = session['user_id']
            settings_manager = get_settings_manager()
            oauth_token = settings_manager.get_oauth2_credentials(user_id, 'google')
            is_authenticated = bool(oauth_token)
            
            return jsonify({
                'success': True,
                'authenticated': is_authenticated,
                'user_id': user_id if is_authenticated else None,
                'user_email': session.get('user_email') if is_authenticated else None
            })
        else:
            return jsonify({
                'success': True,
                'authenticated': False
            })
            
    except Exception as e:
        logger.error(f"Auth status hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@settings_bp.route('/oauth/google', methods=['GET', 'POST'])
@require_auth
def manage_google_oauth():
    """Google OAuth ayarlarını yönet"""
    if request.method == 'GET':
        # Mevcut Google OAuth ayarlarını getir
        try:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'error': 'User not authenticated'}), 401
            
            # Admin kullanıcısından Google OAuth ayarlarını al
            settings_manager = get_settings_manager()
            google_oauth = settings_manager.storage.get_api_key('admin', 'google_oauth')
            
            if google_oauth:
                metadata = google_oauth.get('metadata', {})
                return jsonify({
                    'success': True,
                    'oauth_config': {
                        'client_id': metadata.get('client_id', ''),
                        'redirect_uri': metadata.get('redirect_uri', ''),
                        'configured': True
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'oauth_config': {
                        'client_id': '',
                        'redirect_uri': 'http://localhost:5001/api/settings/auth/google/callback',
                        'configured': False
                    }
                })
                
        except Exception as e:
            logger.error(f"Google OAuth ayarları getirme hatası: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    elif request.method == 'POST':
        # Google OAuth ayarlarını kaydet
        try:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'error': 'User not authenticated'}), 401
            
            data = request.get_json()
            client_id = data.get('client_id')
            client_secret = data.get('client_secret')
            redirect_uri = data.get('redirect_uri', 'http://localhost:5001/api/settings/auth/google/callback')
            
            if not client_id or not client_secret:
                return jsonify({'error': 'Client ID and Client Secret required'}), 400
            
            # Google OAuth ayarlarını kaydet
            settings_manager = get_settings_manager()
            success = settings_manager.storage.set_api_key('admin', 'google_oauth', client_secret, 
                client_id=client_id, redirect_uri=redirect_uri, project_id='metis-agent')
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Google OAuth configuration saved successfully'
                })
            else:
                return jsonify({'error': 'Failed to save Google OAuth configuration'}), 500
                
        except Exception as e:
            logger.error(f"Google OAuth kaydetme hatası: {e}")
            return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/cleanup', methods=['POST'])
@require_auth
def cleanup_expired_tokens():
    """Süresi dolmuş tokenları temizler (Admin only)"""
    try:
        # Basit admin kontrolü - gerçek uygulamada daha güvenli olmalı
        user_id = session['user_id']
        if user_id != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        settings_manager = get_settings_manager()
        # Basic cleanup - remove properties older than 30 days without activity
        cleaned_count = 0  # Not implemented in new storage yet
        
        return jsonify({
            'success': True,
            'cleaned_tokens': cleaned_count,
            'message': f'{cleaned_count} expired tokens cleaned'
        })
        
    except Exception as e:
        logger.error(f"Token cleanup hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/google-credentials', methods=['POST'])
@require_auth
def save_google_credentials():
    """Google hesap bilgilerini kaydeder"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        credentials = {
            'email': data.get('email'),
            'password': data.get('password'),
            'recovery_email': data.get('recovery_email', ''),
            'phone_number': data.get('phone_number', '')
        }
        
        # Settings manager'da API key olarak kaydet (şifrelenmiş)
        settings_manager = get_settings_manager()
        success = settings_manager.storage.set_api_key(
            user_id, 
            'google_credentials', 
            credentials['password'],  # Şifre
            email=credentials['email'],
            recovery_email=credentials['recovery_email'],
            phone_number=credentials['phone_number'],
            type='google_account_credentials'
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Google credentials saved successfully'
            })
        else:
            return jsonify({'error': 'Failed to save Google credentials'}), 500
            
    except Exception as e:
        logger.error(f"Google credentials kaydetme hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/google-credentials', methods=['GET'])
@require_auth  
def get_google_credentials():
    """Google hesap bilgilerini getirir"""
    try:
        user_id = session['user_id']
        
        # Settings manager'dan şifrelenmiş credentials getir
        settings_manager = get_settings_manager()
        credentials_data = settings_manager.storage.get_api_key(user_id, 'google_credentials')
        
        if credentials_data:
            metadata = credentials_data.get('metadata', {})
            
            return jsonify({
                'success': True,
                'credentials': {
                    'email': metadata.get('email', ''),
                    'recovery_email': metadata.get('recovery_email', ''),
                    'phone_number': metadata.get('phone_number', ''),
                    # Şifreyi güvenlik amacıyla göndermiyoruz
                }
            })
        else:
            return jsonify({'error': 'Google credentials not found'}), 404
            
    except Exception as e:
        logger.error(f"Google credentials getirme hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/google-credentials', methods=['DELETE'])
@require_auth
def delete_google_credentials():
    """Google hesap bilgilerini siler"""
    try:
        user_id = session['user_id']
        
        # Settings manager'dan sil
        settings_manager = get_settings_manager()
        success = settings_manager.storage.delete_property(user_id, 'api_key_google_credentials')
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Google credentials deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete Google credentials'}), 500
            
    except Exception as e:
        logger.error(f"Google credentials silme hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Error handlers
@settings_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@settings_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500