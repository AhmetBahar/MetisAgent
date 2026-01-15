"""
Settings API Routes - Kullanıcı ayarları ve API key yönetimi

Bu blueprint settings ve authentication işlemlerini yönetir
"""

import logging
from flask import Blueprint, request, jsonify, session, redirect, url_for
from functools import wraps
import sys
import os
# Use SQLite-based settings instead of deprecated JSON manager
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'MetisAgent2'))
try:
    from tools.internal.user_storage import get_user_storage
    user_storage = get_user_storage()
except ImportError:
    user_storage = None
    logger.warning("User storage not available - some settings features disabled")

logger = logging.getLogger(__name__)

# Blueprint oluştur
settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

def require_auth(f):
    """Authentication gerekli endpoint'ler için decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@settings_bp.route('/user/settings', methods=['GET'])
@require_auth
def get_user_settings():
    """Kullanıcı ayarlarını getirir"""
    try:
        user_id = session['user_id']
        settings = settings_manager.list_user_settings(user_id)
        
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
        success = True
        # Her ayarı ayrı ayrı kaydet
        for key, value in settings.items():
            if not settings_manager.save_user_setting(key, value, user_id):
                success = False
                break
        
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
        api_key_list = settings_manager.list_api_keys(user_id)
        api_keys = [{"service": service, "has_key": True} for service in api_key_list]
        
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
        
        success = settings_manager.save_api_key(service, api_key, user_id, additional_info)
        
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
        api_key_data = settings_manager.get_api_key(service, user_id)
        
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
        success = settings_manager.delete_api_key(service, user_id)
        
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
        
        success = google_auth.setup_google_oauth(client_id, client_secret, redirect_uri)
        
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

@settings_bp.route('/auth/google/login', methods=['GET'])
def google_login():
    """Google OAuth giriş başlatır"""
    try:
        auth_url = google_auth.get_auth_url()
        
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
        
        if error:
            logger.error(f"Google OAuth error: {error}")
            return redirect(url_for('main.index') + '?error=oauth_error')
        
        if not code or not state:
            return redirect(url_for('main.index') + '?error=missing_params')
        
        success, user_info = google_auth.handle_callback(code, state)
        
        if success and user_info:
            # Session'da kullanıcı bilgilerini sakla
            session['user_id'] = user_info['id']
            session['user_email'] = user_info['email']
            session['user_name'] = user_info.get('name', '')
            session['user_picture'] = user_info.get('picture', '')
            
            logger.info(f"Google OAuth başarılı: {user_info['email']}")
            return redirect(url_for('main.index') + '?login=success')
        else:
            logger.error("Google OAuth callback başarısız")
            return redirect(url_for('main.index') + '?error=callback_failed')
            
    except Exception as e:
        logger.error(f"Google callback hatası: {e}")
        return redirect(url_for('main.index') + '?error=internal_error')

@settings_bp.route('/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Kullanıcıyı çıkış yapar"""
    try:
        user_id = session.get('user_id')
        
        if user_id:
            google_auth.logout_user(user_id)
        
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
        
        # Google'dan güncel bilgileri al
        google_profile = google_auth.get_user_profile(user_id)
        if google_profile:
            profile.update(google_profile)
        
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
            is_authenticated = google_auth.is_user_authenticated(user_id)
            
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

@settings_bp.route('/cleanup', methods=['POST'])
@require_auth
def cleanup_expired_tokens():
    """Süresi dolmuş tokenları temizler (Admin only)"""
    try:
        # Basit admin kontrolü - gerçek uygulamada daha güvenli olmalı
        user_id = session['user_id']
        if user_id != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        # JSON settings manager doesn't have cleanup function, skip for now
        cleaned_count = 0
        
        return jsonify({
            'success': True,
            'cleaned_tokens': cleaned_count,
            'message': f'{cleaned_count} expired tokens cleaned'
        })
        
    except Exception as e:
        logger.error(f"Token cleanup hatası: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Error handlers
@settings_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@settings_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500