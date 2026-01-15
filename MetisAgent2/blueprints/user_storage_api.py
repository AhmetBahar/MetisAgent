"""
User Storage API Blueprint - EAV model için RESTful API
"""

from flask import Blueprint, request, jsonify
import logging
import sys
import os

# User Storage import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.internal.user_storage import get_user_storage

logger = logging.getLogger(__name__)

user_storage_api = Blueprint('user_storage_api', __name__, url_prefix='/api/user-storage')

@user_storage_api.route('/properties/<user_id>', methods=['GET'])
def get_user_properties(user_id):
    """Kullanıcının tüm property'lerini getir"""
    try:
        storage = get_user_storage()
        
        if not storage.user_exists(user_id):
            return jsonify({'error': 'User not found'}), 404
            
        properties = storage.get_all_properties(user_id)
        
        # Property metadata'sını da al
        detailed_properties = {}
        for prop_name, prop_value in properties.items():
            # SQLite'dan metadata al
            import sqlite3
            with sqlite3.connect(storage.db_path) as conn:
                cursor = conn.execute('''
                    SELECT property_type, is_encrypted, created_at, updated_at
                    FROM user_properties 
                    WHERE user_id = ? AND property_name = ?
                ''', (user_id, prop_name))
                row = cursor.fetchone()
                
                if row:
                    # API key object'leri için özel formatting
                    if isinstance(prop_value, dict) and 'api_key' in prop_value:
                        # API key object'leri için sadece gerekli bilgileri göster
                        formatted_value = prop_value.copy()
                    else:
                        formatted_value = prop_value
                        
                    detailed_properties[prop_name] = {
                        'property_value': formatted_value,
                        'property_type': row[0],
                        'is_encrypted': bool(row[1]),
                        'created_at': row[2],
                        'updated_at': row[3]
                    }
        
        return jsonify({
            'user_id': user_id,
            'properties': detailed_properties
        })
        
    except Exception as e:
        logger.error(f"Error getting user properties {user_id}: {e}")
        return jsonify({'error': 'Failed to get user properties'}), 500

@user_storage_api.route('/property/<user_id>', methods=['POST'])
def create_user_property(user_id):
    """Yeni property oluştur"""
    try:
        data = request.get_json()
        
        if not data or 'property_name' not in data or 'property_value' not in data:
            return jsonify({'error': 'property_name and property_value required'}), 400
        
        property_name = data['property_name']
        property_value = data['property_value']
        property_type = data.get('property_type', 'string')
        encrypt = data.get('encrypt', False)
        
        # Validation
        if property_type not in ['string', 'json', 'int', 'bool']:
            return jsonify({'error': 'Invalid property_type'}), 400
            
        # Type conversion
        if property_type == 'int':
            try:
                property_value = int(property_value)
            except ValueError:
                return jsonify({'error': 'Invalid integer value'}), 400
        elif property_type == 'bool':
            property_value = str(property_value).lower() in ('true', '1', 'yes')
        elif property_type == 'json':
            try:
                import json
                json.loads(str(property_value))  # Validate JSON
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON value'}), 400
        
        storage = get_user_storage()
        
        # Check if property already exists
        existing = storage.get_property(user_id, property_name)
        if existing is not None:
            return jsonify({'error': 'Property already exists'}), 409
        
        success = storage.set_property(
            user_id=user_id,
            property_name=property_name,
            property_value=property_value,
            encrypt=encrypt,
            property_type=property_type
        )
        
        if success:
            return jsonify({
                'message': 'Property created successfully',
                'property_name': property_name
            }), 201
        else:
            return jsonify({'error': 'Failed to create property'}), 500
            
    except Exception as e:
        logger.error(f"Error creating property for {user_id}: {e}")
        return jsonify({'error': 'Failed to create property'}), 500

@user_storage_api.route('/property/<user_id>/<property_name>', methods=['PUT'])
def update_user_property(user_id, property_name):
    """Property'yi güncelle"""
    try:
        data = request.get_json()
        
        if not data or 'property_value' not in data:
            return jsonify({'error': 'property_value required'}), 400
        
        property_value = data['property_value']
        property_type = data.get('property_type', 'string')
        encrypt = data.get('encrypt', False)
        
        # Validation
        if property_type not in ['string', 'json', 'int', 'bool']:
            return jsonify({'error': 'Invalid property_type'}), 400
            
        # Type conversion
        if property_type == 'int':
            try:
                property_value = int(property_value)
            except ValueError:
                return jsonify({'error': 'Invalid integer value'}), 400
        elif property_type == 'bool':
            property_value = str(property_value).lower() in ('true', '1', 'yes')
        elif property_type == 'json':
            try:
                import json
                json.loads(str(property_value))  # Validate JSON
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON value'}), 400
        
        storage = get_user_storage()
        
        # Check if property exists
        existing = storage.get_property(user_id, property_name)
        if existing is None:
            return jsonify({'error': 'Property not found'}), 404
        
        success = storage.set_property(
            user_id=user_id,
            property_name=property_name,
            property_value=property_value,
            encrypt=encrypt,
            property_type=property_type
        )
        
        if success:
            return jsonify({
                'message': 'Property updated successfully',
                'property_name': property_name
            })
        else:
            return jsonify({'error': 'Failed to update property'}), 500
            
    except Exception as e:
        logger.error(f"Error updating property {user_id}.{property_name}: {e}")
        return jsonify({'error': 'Failed to update property'}), 500

@user_storage_api.route('/property/<user_id>/<property_name>', methods=['DELETE'])
def delete_user_property(user_id, property_name):
    """Property'yi sil"""
    try:
        storage = get_user_storage()
        
        # Check if property exists
        existing = storage.get_property(user_id, property_name)
        if existing is None:
            return jsonify({'error': 'Property not found'}), 404
        
        success = storage.delete_property(user_id, property_name)
        
        if success:
            return jsonify({
                'message': 'Property deleted successfully',
                'property_name': property_name
            })
        else:
            return jsonify({'error': 'Failed to delete property'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting property {user_id}.{property_name}: {e}")
        return jsonify({'error': 'Failed to delete property'}), 500

@user_storage_api.route('/property/<user_id>/<property_name>', methods=['GET'])
def get_user_property(user_id, property_name):
    """Tek bir property getir"""
    try:
        storage = get_user_storage()
        
        property_value = storage.get_property(user_id, property_name)
        
        if property_value is None:
            return jsonify({'error': 'Property not found'}), 404
        
        # Metadata al
        import sqlite3
        with sqlite3.connect(storage.db_path) as conn:
            cursor = conn.execute('''
                SELECT property_type, is_encrypted, created_at, updated_at
                FROM user_properties 
                WHERE user_id = ? AND property_name = ?
            ''', (user_id, property_name))
            row = cursor.fetchone()
        
        if row:
            return jsonify({
                'property_name': property_name,
                'property_value': property_value,
                'property_type': row[0],
                'is_encrypted': bool(row[1]),
                'created_at': row[2],
                'updated_at': row[3]
            })
        else:
            return jsonify({'error': 'Property metadata not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting property {user_id}.{property_name}: {e}")
        return jsonify({'error': 'Failed to get property'}), 500

@user_storage_api.route('/users', methods=['GET'])
def list_users():
    """Tüm kullanıcıları listele"""
    try:
        storage = get_user_storage()
        users = storage.list_users()
        
        return jsonify({
            'users': users,
            'total': len(users)
        })
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({'error': 'Failed to list users'}), 500

@user_storage_api.route('/user/<user_id>', methods=['POST'])
def create_user(user_id):
    """Yeni kullanıcı oluştur"""
    try:
        storage = get_user_storage()
        
        if storage.user_exists(user_id):
            return jsonify({'error': 'User already exists'}), 409
        
        success = storage.create_user(user_id)
        
        if success:
            return jsonify({
                'message': 'User created successfully',
                'user_id': user_id
            }), 201
        else:
            return jsonify({'error': 'Failed to create user'}), 500
            
    except Exception as e:
        logger.error(f"Error creating user {user_id}: {e}")
        return jsonify({'error': 'Failed to create user'}), 500

@user_storage_api.route('/user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Kullanıcıyı ve tüm property'lerini sil"""
    try:
        storage = get_user_storage()
        
        if not storage.user_exists(user_id):
            return jsonify({'error': 'User not found'}), 404
        
        success = storage.delete_user(user_id)
        
        if success:
            return jsonify({
                'message': 'User deleted successfully',
                'user_id': user_id
            })
        else:
            return jsonify({'error': 'Failed to delete user'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({'error': 'Failed to delete user'}), 500

# Convenience endpoints for common property types

@user_storage_api.route('/api-key/<user_id>/<provider>', methods=['POST'])
def set_api_key(user_id, provider):
    """API key kaydet (shortcut endpoint)"""
    try:
        data = request.get_json()
        
        if not data or 'api_key' not in data:
            return jsonify({'error': 'api_key required'}), 400
        
        api_key = data['api_key']
        metadata = data.get('metadata', {})
        
        storage = get_user_storage()
        success = storage.set_api_key(user_id, provider, api_key, **metadata)
        
        if success:
            return jsonify({
                'message': f'{provider} API key saved successfully'
            })
        else:
            return jsonify({'error': 'Failed to save API key'}), 500
            
    except Exception as e:
        logger.error(f"Error setting API key {user_id}.{provider}: {e}")
        return jsonify({'error': 'Failed to save API key'}), 500

@user_storage_api.route('/api-key/<user_id>/<provider>', methods=['GET'])
def get_api_key(user_id, provider):
    """API key getir (shortcut endpoint)"""
    try:
        storage = get_user_storage()
        api_data = storage.get_api_key(user_id, provider)
        
        if api_data:
            return jsonify(api_data)
        else:
            return jsonify({'error': 'API key not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting API key {user_id}.{provider}: {e}")
        return jsonify({'error': 'Failed to get API key'}), 500

@user_storage_api.route('/mapping/<user_id>/<service>', methods=['POST'])
def set_user_mapping(user_id, service):
    """User mapping kaydet (shortcut endpoint)"""
    try:
        data = request.get_json()
        
        if not data or 'external_id' not in data:
            return jsonify({'error': 'external_id required'}), 400
        
        external_id = data['external_id']
        
        storage = get_user_storage()
        success = storage.set_user_mapping(user_id, service, external_id)
        
        if success:
            return jsonify({
                'message': f'{service} mapping saved successfully'
            })
        else:
            return jsonify({'error': 'Failed to save mapping'}), 500
            
    except Exception as e:
        logger.error(f"Error setting mapping {user_id}.{service}: {e}")
        return jsonify({'error': 'Failed to save mapping'}), 500

@user_storage_api.route('/mapping/<user_id>/<service>', methods=['GET'])
def get_user_mapping(user_id, service):
    """User mapping getir (shortcut endpoint)"""
    try:
        storage = get_user_storage()
        mapping = storage.get_user_mapping(user_id, service)
        
        if mapping:
            return jsonify({
                'user_id': user_id,
                'service': service,
                'external_id': mapping
            })
        else:
            return jsonify({'error': 'Mapping not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting mapping {user_id}.{service}: {e}")
        return jsonify({'error': 'Failed to get mapping'}), 500