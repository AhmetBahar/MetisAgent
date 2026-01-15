"""
OAuth2 Routes - Google OAuth2 callback ve management endpoints
"""

from flask import Blueprint, request, jsonify, redirect, render_template_string
import logging
from .mcp_core import registry

logger = logging.getLogger(__name__)

# Create OAuth2 blueprint
oauth2_bp = Blueprint('oauth2', __name__, url_prefix='/oauth2')

def get_oauth_token_for_gmail(user_email: str):
    """Helper function to get OAuth2 token for Gmail user"""
    from tools.internal.user_storage import get_user_storage
    storage = get_user_storage()
    
    # OAuth2 tokens are now stored under Google email, not system user
    oauth_token = storage.get_oauth_token(user_email, 'google')
    
    if oauth_token:
        # Find system user from reverse mapping
        system_user = storage.get_user_mapping(user_email, 'system')
        return oauth_token, system_user
    
    # Fallback: search by mapping (legacy compatibility)
    for user_id in storage.list_users():
        user_mapping = storage.get_user_mapping(user_id, 'google')
        if user_mapping == user_email:
            # Try to find token under system user (legacy)
            token = storage.get_oauth_token(user_id, 'google')
            if token:
                return token, user_id
    
    return None, f'No OAuth2 token found for Gmail account: {user_email}'

@oauth2_bp.route('/google/start', methods=['POST'])
def start_google_oauth():
    """Google OAuth2 flow başlat"""
    try:
        data = request.get_json() or {}
        
        # Gerekli parametreler
        services = data.get('services', ['basic'])  # default: basic user info
        user_id = data.get('user_id')
        
        # If no user_id provided, try to get from session/auth
        if not user_id:
            # Try to get current user from session or request headers
            from .session_manager import get_current_user
            current_user = get_current_user(request)
            if current_user:
                user_id = current_user.get('user_id')
        
        logger.info(f"OAuth2 start request: services={services}, user_id={user_id}, data={data}")
        
        if not services:
            return jsonify({'error': 'Services parameter required'}), 400
        
        # OAuth2 manager'dan auth URL al
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'get_auth_url',
            services=services,
            user_id=user_id
        )
        
        if result.success:
            response_data = {
                'success': True,
                'auth_url': result.data.get('auth_url'),
                'state': result.data.get('state'),
                'services': result.data.get('services', ['gmail']),
                'expires_in': result.data.get('expires_in', 600)
            }
            
            # Handle already authenticated case
            if result.data.get('already_authenticated'):
                response_data['already_authenticated'] = True
                response_data['message'] = result.data.get('message', 'User already authenticated')
            
            return jsonify(response_data)
        else:
            return jsonify({'error': result.error}), 400
            
    except Exception as e:
        logger.error(f"OAuth2 start error: {e}")
        return jsonify({'error': str(e)}), 500

@oauth2_bp.route('/google/callback', methods=['GET'])
def google_oauth_callback():
    """Google OAuth2 callback handler"""
    try:
        # Callback parametrelerini al
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            return render_template_string(OAUTH_ERROR_TEMPLATE, 
                                        error=error, 
                                        error_description=request.args.get('error_description', ''))
        
        if not code:
            return render_template_string(OAUTH_ERROR_TEMPLATE, 
                                        error='missing_code',
                                        error_description='Authorization code not provided')
        
        # Authorization code'u token ile değiştir
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'exchange_code',
            code=code,
            state=state
        )
        
        if result.success:
            return render_template_string(OAUTH_SUCCESS_TEMPLATE,
                                        user_id=result.data.get('google_email', result.data['user_id']),
                                        user_email=result.data['user_info'].get('email'),
                                        user_name=result.data['user_info'].get('name'),
                                        services=', '.join(result.data['services']),
                                        expires_in=result.data['expires_in'])
        else:
            return render_template_string(OAUTH_ERROR_TEMPLATE,
                                        error='exchange_failed',
                                        error_description=result.error)
            
    except Exception as e:
        logger.error(f"OAuth2 callback error: {e}")
        return render_template_string(OAUTH_ERROR_TEMPLATE,
                                    error='server_error', 
                                    error_description=str(e))

@oauth2_bp.route('/google/token/<user_id>', methods=['GET'])
def get_user_token(user_id):
    """Get OAuth2 access token for user"""
    try:
        logger.info(f"Token request for user: {user_id}")
        
        # Get token using OAuth2 manager
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'get_user_token',
            user_id=user_id
        )
        
        if result.success:
            return jsonify({
                'access_token': result.data.get('access_token'),
                'token_type': 'Bearer',
                'expires_in': result.data.get('expires_in'),
                'scope': result.data.get('scope')
            })
        else:
            logger.error(f"Token fetch failed for {user_id}: {result.error}")
            return jsonify({'error': result.error}), 401
            
    except Exception as e:
        logger.error(f"Token endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

@oauth2_bp.route('/google/health', methods=['GET'])
def oauth2_health():
    """OAuth2 service health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'oauth2',
        'endpoints': ['callback', 'token', 'status']
    })

@oauth2_bp.route('/google/status', methods=['GET'])
def get_oauth_status():
    """OAuth2 durumunu kontrol et"""
    try:
        user_id = request.args.get('user_id')
        
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'get_oauth2_status',
            user_id=user_id
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"OAuth2 status error: {e}")
        return jsonify({'error': str(e)}), 500

@oauth2_bp.route('/google/users', methods=['GET'])
def list_authorized_users():
    """Authorize olmuş kullanıcıları listele"""
    try:
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'list_authorized_users'
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        return jsonify({'error': str(e)}), 500

@oauth2_bp.route('/google/refresh', methods=['POST'])
def refresh_token():
    """Token'ı yenile"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'refresh_token',
            user_id=user_id
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({'error': str(e)}), 500

@oauth2_bp.route('/google/revoke', methods=['POST'])
def revoke_token():
    """Token'ı iptal et"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'revoke_token',
            user_id=user_id
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Token revoke error: {e}")
        return jsonify({'error': str(e)}), 500

@oauth2_bp.route('/google/setup', methods=['POST'])
def setup_oauth2():
    """OAuth2 credentials setup"""
    try:
        data = request.get_json() or {}
        
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        redirect_uri = data.get('redirect_uri')
        
        if not client_id or not client_secret:
            return jsonify({'error': 'client_id and client_secret required'}), 400
        
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'setup_oauth2',
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"OAuth2 setup error: {e}")
        return jsonify({'error': str(e)}), 500

# API Endpoints for Google Services

@oauth2_bp.route('/google/gmail/messages', methods=['GET'])
def gmail_list_messages():
    """Gmail mesajlarını listele - Direct Google API call"""
    try:
        user_email = request.args.get('user_id')  # This is actually Gmail email
        query = request.args.get('query', '')
        max_results = int(request.args.get('max_results', 10))
        
        if not user_email:
            return jsonify({'error': 'user_id (Gmail email) required'}), 400
        
        # Get OAuth2 token using helper function
        oauth_token, system_user = get_oauth_token_for_gmail(user_email)
        
        if oauth_token is None:
            return jsonify({
                'success': False,
                'error': system_user  # Error message in this case
            }), 401
        
        # Ensure token is valid (auto-refresh if needed)
        oauth2_manager = registry.get_tool('google_oauth2_manager')
        if oauth2_manager:
            token_valid = oauth2_manager._ensure_valid_token(system_user)
            if not token_valid:
                return jsonify({
                    'success': False,
                    'error': 'Unable to refresh OAuth2 token'
                }), 401
            
            # Get refreshed token
            oauth_token, _ = get_oauth_token_for_gmail(user_email)
        
        # Direct Google Gmail API call
        import requests
        
        gmail_api_url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages'
        headers = {
            'Authorization': f'Bearer {oauth_token["access_token"]}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'maxResults': max_results
        }
        if query:
            params['q'] = query
        
        response = requests.get(gmail_api_url, headers=headers, params=params)
        response.raise_for_status()
        
        gmail_data = response.json()
        
        # Get full details for each message (for better UX)
        detailed_messages = {}
        if 'messages' in gmail_data:
            message_ids = gmail_data['messages'][:max_results]  # Limit to max_results
            
            for msg in message_ids:
                msg_id = msg['id']
                try:
                    # Get message details
                    detail_url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}'
                    detail_params = {'format': 'full'}
                    detail_response = requests.get(detail_url, headers=headers, params=detail_params)
                    detail_response.raise_for_status()
                    
                    message_detail = detail_response.json()
                    
                    # Extract useful info
                    headers_list = message_detail.get('payload', {}).get('headers', [])
                    from_header = next((h['value'] for h in headers_list if h['name'].lower() == 'from'), 'Unknown sender')
                    subject_header = next((h['value'] for h in headers_list if h['name'].lower() == 'subject'), 'No subject')
                    date_header = next((h['value'] for h in headers_list if h['name'].lower() == 'date'), 'No date')
                    
                    detailed_messages[msg_id] = {
                        'id': msg_id,
                        'threadId': msg.get('threadId', ''),
                        'from': from_header,
                        'subject': subject_header,
                        'date': date_header,
                        'snippet': message_detail.get('snippet', '')
                    }
                    
                except Exception as detail_error:
                    logger.warning(f"Failed to get details for message {msg_id}: {detail_error}")
                    # Fallback to basic info
                    detailed_messages[msg_id] = {
                        'id': msg_id,
                        'threadId': msg.get('threadId', ''),
                        'from': f'Message ID: {msg_id}',
                        'subject': f'Thread ID: {msg.get("threadId", "N/A")}',
                        'date': 'Details unavailable'
                    }
        
        return jsonify({
            'success': True,
            'data': {
                'messages': detailed_messages,
                'user_email': user_email,
                'system_user': system_user
            }
        })
        
    except Exception as e:
        logger.error(f"Gmail list messages error: {e}")
        return jsonify({'error': str(e)}), 500

@oauth2_bp.route('/google/gmail/messages/<message_id>', methods=['GET'])
def gmail_get_message(message_id):
    """Gmail mesaj detayını al - Direct Google API call"""
    try:
        user_email = request.args.get('user_id')  # This is actually Gmail email
        format_type = request.args.get('format', 'full')
        
        if not user_email:
            return jsonify({'error': 'user_id (Gmail email) required'}), 400
        
        # Get OAuth2 token using helper function
        oauth_token, system_user = get_oauth_token_for_gmail(user_email)
        
        if oauth_token is None:
            return jsonify({
                'success': False,
                'error': system_user  # Error message in this case
            }), 401
        
        # Ensure token is valid (auto-refresh if needed)
        oauth2_manager = registry.get_tool('google_oauth2_manager')
        if oauth2_manager:
            token_valid = oauth2_manager._ensure_valid_token(system_user)
            if not token_valid:
                return jsonify({
                    'success': False,
                    'error': 'Unable to refresh OAuth2 token'
                }), 401
            
            # Get refreshed token
            oauth_token, _ = get_oauth_token_for_gmail(user_email)
        
        # Direct Google Gmail API call
        import requests
        
        gmail_api_url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}'
        headers = {
            'Authorization': f'Bearer {oauth_token["access_token"]}',
            'Content-Type': 'application/json'
        }
        
        params = {'format': format_type}
        
        response = requests.get(gmail_api_url, headers=headers, params=params)
        response.raise_for_status()
        
        gmail_data = response.json()
        
        return jsonify({
            'success': True,
            'data': {
                'message': gmail_data,
                'user_email': user_email,
                'system_user': system_user
            }
        })
        
    except Exception as e:
        logger.error(f"Gmail get message error: {e}")
        return jsonify({'error': str(e)}), 500

@oauth2_bp.route('/google/gmail/send', methods=['POST'])
def gmail_send_message():
    """Gmail ile email gönder"""
    try:
        data = request.get_json() or {}
        
        user_id = data.get('user_id')
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        cc = data.get('cc')
        bcc = data.get('bcc')
        
        if not all([user_id, to, subject, body]):
            return jsonify({'error': 'user_id, to, subject, and body required'}), 400
        
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'gmail_send_message',
            user_id=user_id,
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Gmail send message error: {e}")
        return jsonify({'error': str(e)}), 500

@oauth2_bp.route('/google/gmail/send_with_attachment', methods=['POST'])
def gmail_send_message_with_attachment():
    """Gmail ile attachment'lı email gönder"""
    try:
        data = request.get_json() or {}
        
        user_id = data.get('user_id')
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        attachment_path = data.get('attachment_path')
        cc = data.get('cc')
        bcc = data.get('bcc')
        attachment_name = data.get('attachment_name')
        
        if not all([user_id, to, subject, body, attachment_path]):
            return jsonify({'error': 'user_id, to, subject, body, and attachment_path required'}), 400
        
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'gmail_send_message_with_attachment',
            user_id=user_id,
            to=to,
            subject=subject,
            body=body,
            attachment_path=attachment_path,
            cc=cc,
            bcc=bcc,
            attachment_name=attachment_name
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Gmail send message with attachment error: {e}")
        return jsonify({'error': str(e)}), 500

@oauth2_bp.route('/google/drive/files', methods=['GET'])
def drive_list_files():
    """Google Drive dosyalarını listele"""
    try:
        user_id = request.args.get('user_id')
        query = request.args.get('query', '')
        max_results = int(request.args.get('max_results', 10))
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'drive_list_files',
            user_id=user_id,
            query=query,
            max_results=max_results
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Drive list files error: {e}")
        return jsonify({'error': str(e)}), 500

@oauth2_bp.route('/google/calendar/events', methods=['GET'])
def calendar_list_events():
    """Google Calendar etkinliklerini listele"""
    try:
        user_id = request.args.get('user_id')
        calendar_id = request.args.get('calendar_id', 'primary')
        time_min = request.args.get('time_min')
        time_max = request.args.get('time_max')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        result = registry.execute_tool_action(
            'google_oauth2_manager',
            'calendar_list_events',
            user_id=user_id,
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max
        )
        
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"Calendar list events error: {e}")
        return jsonify({'error': str(e)}), 500

# HTML Templates

OAUTH_SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OAuth2 Authorization Successful</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        .success { color: #28a745; background: #d4edda; padding: 15px; border-radius: 5px; border: 1px solid #c3e6cb; }
        .info { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .button { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="success">
        <h2>🎉 Google OAuth2 Authorization Successful!</h2>
        <p>Your Google account has been successfully connected to MetisAgent.</p>
    </div>
    
    <div class="info">
        <h3>Account Information:</h3>
        <p><strong>User ID:</strong> {{ user_id }}</p>
        <p><strong>Email:</strong> {{ user_email }}</p>
        <p><strong>Name:</strong> {{ user_name }}</p>
        <p><strong>Authorized Services:</strong> {{ services }}</p>
        <p><strong>Token Expires In:</strong> {{ expires_in }} seconds</p>
    </div>
    
    <p>You can now close this window and return to MetisAgent.</p>
    
    <script>
        // Auto close after 5 seconds
        setTimeout(() => {
            window.close();
        }, 5000);
    </script>
</body>
</html>
"""

OAUTH_ERROR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OAuth2 Authorization Error</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        .error { color: #dc3545; background: #f8d7da; padding: 15px; border-radius: 5px; border: 1px solid #f5c6cb; }
        .info { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .button { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="error">
        <h2>❌ OAuth2 Authorization Error</h2>
        <p>There was an error during the authorization process.</p>
    </div>
    
    <div class="info">
        <h3>Error Details:</h3>
        <p><strong>Error:</strong> {{ error }}</p>
        <p><strong>Description:</strong> {{ error_description }}</p>
    </div>
    
    <p>Please try again or contact support if the problem persists.</p>
    
    <script>
        // Auto close after 10 seconds
        setTimeout(() => {
            window.close();
        }, 10000);
    </script>
</body>
</html>
"""