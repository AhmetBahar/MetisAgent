import unittest
from unittest.mock import patch, Mock, MagicMock
import sys
import os
import hashlib
import secrets
import json

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from os_araci.auth.auth_manager import AuthManager


class TestAuthManager(unittest.TestCase):
    """Comprehensive unit tests for AuthManager"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset the singleton instance for each test
        AuthManager._instance = None

    def tearDown(self):
        """Clean up after each test"""
        # Reset the singleton instance
        AuthManager._instance = None

    @patch('os_araci.auth.auth_manager.ChromaManager')
    @patch('os_araci.auth.auth_manager.logger')
    def test_singleton_pattern(self, mock_logger, mock_chroma_manager):
        """Test that AuthManager follows singleton pattern"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_chroma_manager.return_value = mock_db
        
        auth1 = AuthManager()
        auth2 = AuthManager()
        
        self.assertIs(auth1, auth2)

    @patch('os_araci.auth.auth_manager.ChromaManager')
    @patch('os_araci.auth.auth_manager.logger')
    def test_init_creates_admin_user(self, mock_logger, mock_chroma_manager):
        """Test that initialization creates admin user if not exists"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None  # Admin doesn't exist
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        
        mock_db.get_user.assert_called_with("admin")
        mock_db.create_user.assert_called_once()
        mock_logger.info.assert_any_call("Admin kullanıcısı oluşturuldu")

    @patch('os_araci.auth.auth_manager.ChromaManager')
    @patch('os_araci.auth.auth_manager.logger')
    def test_init_admin_user_exists(self, mock_logger, mock_chroma_manager):
        """Test initialization when admin user already exists"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = {"user_id": "admin_id", "username": "admin"}
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        
        mock_db.get_user.assert_called_with("admin")
        mock_db.create_user.assert_not_called()

    @patch('os_araci.auth.auth_manager.ChromaManager')
    def test_get_user(self, mock_chroma_manager):
        """Test getting user"""
        mock_db = MagicMock()
        mock_user = {"user_id": "123", "username": "testuser"}
        mock_db.get_user.return_value = mock_user
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.get_user("testuser")
        
        self.assertEqual(result, mock_user)
        mock_db.get_user.assert_called_with("testuser")

    def test_hash_password(self):
        """Test password hashing"""
        auth_manager = AuthManager.__new__(AuthManager)
        auth_manager._initialized = True
        
        password = "test_password"
        hashed = auth_manager._hash_password(password)
        
        self.assertIn('$', hashed)
        salt, hash_value = hashed.split('$')
        self.assertEqual(len(salt), 32)  # 16 bytes hex = 32 chars
        self.assertEqual(len(hash_value), 64)  # SHA256 hex = 64 chars

    def test_hash_password_different_salts(self):
        """Test that password hashing produces different salts"""
        auth_manager = AuthManager.__new__(AuthManager)
        auth_manager._initialized = True
        
        password = "test_password"
        hash1 = auth_manager._hash_password(password)
        hash2 = auth_manager._hash_password(password)
        
        self.assertNotEqual(hash1, hash2)
        salt1, _ = hash1.split('$')
        salt2, _ = hash2.split('$')
        self.assertNotEqual(salt1, salt2)

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        auth_manager = AuthManager.__new__(AuthManager)
        auth_manager._initialized = True
        
        password = "test_password"
        stored_hash = auth_manager._hash_password(password)
        
        result = auth_manager._verify_password(stored_hash, password)
        
        self.assertTrue(result)

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        auth_manager = AuthManager.__new__(AuthManager)
        auth_manager._initialized = True
        
        password = "test_password"
        wrong_password = "wrong_password"
        stored_hash = auth_manager._hash_password(password)
        
        result = auth_manager._verify_password(stored_hash, wrong_password)
        
        self.assertFalse(result)

    @patch('os_araci.auth.auth_manager.ChromaManager')
    @patch('os_araci.auth.auth_manager.logger')
    def test_create_user_success(self, mock_logger, mock_chroma_manager):
        """Test successful user creation"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None  # Admin doesn't exist initially
        mock_db.create_user.side_effect = [
            {"status": "success", "user_id": "admin_id"},  # Admin creation
            {"status": "success", "user_id": "new_user_id"}  # New user creation
        ]
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.create_user("newuser", "password123", ["read", "write"])
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["user_id"], "new_user_id")
        mock_logger.info.assert_any_call("Yeni kullanıcı oluşturuldu: newuser")

    @patch('os_araci.auth.auth_manager.ChromaManager')
    @patch('os_araci.auth.auth_manager.logger')
    def test_create_user_failure(self, mock_logger, mock_chroma_manager):
        """Test user creation failure"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.side_effect = [
            {"status": "success", "user_id": "admin_id"},  # Admin creation
            {"status": "error", "message": "User already exists"}  # New user creation fails
        ]
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.create_user("existinguser", "password123")
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "User already exists")
        mock_logger.warning.assert_called_with("Kullanıcı oluşturma başarısız: existinguser, User already exists")

    @patch('os_araci.auth.auth_manager.ChromaManager')
    @patch('os_araci.auth.auth_manager.logger')
    def test_authenticate_user_success(self, mock_logger, mock_chroma_manager):
        """Test successful user authentication"""
        password = "test_password"
        
        # Create real hash
        auth_manager_temp = AuthManager.__new__(AuthManager)
        auth_manager_temp._initialized = True
        password_hash = auth_manager_temp._hash_password(password)
        
        mock_user = {
            "user_id": "user123",
            "username": "testuser",
            "password_hash": password_hash,
            "permissions": ["read", "write"]
        }
        
        mock_db = MagicMock()
        mock_db.get_user.side_effect = [None, mock_user]  # First for admin check, second for auth
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.update_user_login.return_value = True
        mock_db.create_session.return_value = "session_token_123"
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.authenticate_user("testuser", password)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["user_id"], "user123")
        self.assertEqual(result["username"], "testuser")
        self.assertEqual(result["session_token"], "session_token_123")
        self.assertEqual(result["permissions"], ["read", "write"])
        mock_db.update_user_login.assert_called_with("testuser")
        mock_db.create_session.assert_called_with("user123")
        mock_logger.info.assert_any_call("Kullanıcı oturum açtı: testuser")

    @patch('os_araci.auth.auth_manager.ChromaManager')
    @patch('os_araci.auth.auth_manager.logger')
    def test_authenticate_user_not_found(self, mock_logger, mock_chroma_manager):
        """Test authentication with non-existent user"""
        mock_db = MagicMock()
        mock_db.get_user.side_effect = [None, None]  # Admin check, then user check
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.authenticate_user("nonexistent", "password")
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Invalid credentials")
        mock_logger.warning.assert_called_with("Kimlik doğrulama başarısız (kullanıcı yok): nonexistent")

    @patch('os_araci.auth.auth_manager.ChromaManager')
    @patch('os_araci.auth.auth_manager.logger')
    def test_authenticate_user_wrong_password(self, mock_logger, mock_chroma_manager):
        """Test authentication with wrong password"""
        password = "correct_password"
        wrong_password = "wrong_password"
        
        # Create real hash
        auth_manager_temp = AuthManager.__new__(AuthManager)
        auth_manager_temp._initialized = True
        password_hash = auth_manager_temp._hash_password(password)
        
        mock_user = {
            "user_id": "user123",
            "username": "testuser",
            "password_hash": password_hash,
            "permissions": ["read"]
        }
        
        mock_db = MagicMock()
        mock_db.get_user.side_effect = [None, mock_user]
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.authenticate_user("testuser", wrong_password)
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Invalid credentials")
        mock_logger.warning.assert_called_with("Kimlik doğrulama başarısız (yanlış parola): testuser")

    @patch('os_araci.auth.auth_manager.ChromaManager')
    @patch('os_araci.auth.auth_manager.logger')
    def test_create_api_key_success(self, mock_logger, mock_chroma_manager):
        """Test successful API key creation"""
        mock_user = {"user_id": "user123", "username": "testuser"}
        mock_db = MagicMock()
        mock_db.get_user.side_effect = [None, mock_user]
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.create_api_key.return_value = "metis_abc123def456"
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.create_api_key("testuser", ["read", "write"])
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["api_key"], "metis_abc123def456")
        mock_db.create_api_key.assert_called_with("user123", ["read", "write"])
        mock_logger.info.assert_any_call("Yeni API anahtarı oluşturuldu: testuser")

    @patch('os_araci.auth.auth_manager.ChromaManager')
    @patch('os_araci.auth.auth_manager.logger')
    def test_create_api_key_user_not_found(self, mock_logger, mock_chroma_manager):
        """Test API key creation for non-existent user"""
        mock_db = MagicMock()
        mock_db.get_user.side_effect = [None, None]
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.create_api_key("nonexistent", ["read"])
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "User not found")
        mock_logger.warning.assert_called_with("API anahtarı oluşturma başarısız (kullanıcı yok): nonexistent")

    @patch('os_araci.auth.auth_manager.ChromaManager')
    def test_validate_api_key(self, mock_chroma_manager):
        """Test API key validation"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.validate_api_key.return_value = True
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.validate_api_key("metis_abc123")
        
        self.assertTrue(result)
        mock_db.validate_api_key.assert_called_with("metis_abc123")

    @patch('os_araci.auth.auth_manager.ChromaManager')
    def test_validate_session(self, mock_chroma_manager):
        """Test session validation"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.validate_session.return_value = "user123"
        
        # Mock the users collection query
        mock_users_collection = MagicMock()
        mock_users_collection.get.return_value = {
            "ids": ["user123"],
            "metadatas": [{
                "username": "testuser",
                "permissions": '["read", "write"]'
            }]
        }
        mock_db.users_collection = mock_users_collection
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.validate_session("session_token_123")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["user_id"], "user123")
        self.assertEqual(result["username"], "testuser")
        self.assertEqual(result["permissions"], ["read", "write"])

    @patch('os_araci.auth.auth_manager.ChromaManager')
    def test_validate_session_invalid(self, mock_chroma_manager):
        """Test validation of invalid session"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.validate_session.return_value = None
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.validate_session("invalid_session")
        
        self.assertIsNone(result)

    @patch('os_araci.auth.auth_manager.ChromaManager')
    def test_validate_session_user_not_found(self, mock_chroma_manager):
        """Test session validation when user is not found"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.validate_session.return_value = "user123"
        
        # Mock the users collection query - user not found
        mock_users_collection = MagicMock()
        mock_users_collection.get.return_value = {
            "ids": [],
            "metadatas": []
        }
        mock_db.users_collection = mock_users_collection
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.validate_session("session_token_123")
        
        self.assertIsNone(result)

    @patch('os_araci.auth.auth_manager.ChromaManager')
    def test_check_permission_with_wildcard(self, mock_chroma_manager):
        """Test permission check with wildcard permission"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.get_api_key_info.return_value = {
            "permissions": ["*"]
        }
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.check_permission("api_key", "any_permission")
        
        self.assertTrue(result)

    @patch('os_araci.auth.auth_manager.ChromaManager')
    def test_check_permission_specific(self, mock_chroma_manager):
        """Test permission check with specific permission"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.get_api_key_info.return_value = {
            "permissions": ["read", "write"]
        }
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result_has = auth_manager.check_permission("api_key", "read")
        result_not_has = auth_manager.check_permission("api_key", "admin")
        
        self.assertTrue(result_has)
        self.assertFalse(result_not_has)

    @patch('os_araci.auth.auth_manager.ChromaManager')
    def test_check_permission_invalid_key(self, mock_chroma_manager):
        """Test permission check with invalid API key"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.get_api_key_info.return_value = None
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.check_permission("invalid_api_key", "read")
        
        self.assertFalse(result)

    @patch('os_araci.auth.auth_manager.ChromaManager')
    def test_revoke_api_key(self, mock_chroma_manager):
        """Test API key revocation"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.revoke_api_key.return_value = True
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.revoke_api_key("api_key_to_revoke")
        
        self.assertTrue(result)
        mock_db.revoke_api_key.assert_called_with("api_key_to_revoke")

    @patch('os_araci.auth.auth_manager.ChromaManager')
    def test_logout_user(self, mock_chroma_manager):
        """Test user logout"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.end_session.return_value = True
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.logout_user("session_token")
        
        self.assertTrue(result)
        mock_db.end_session.assert_called_with("session_token")

    @patch('os_araci.auth.auth_manager.ChromaManager')
    def test_cleanup_sessions(self, mock_chroma_manager):
        """Test session cleanup"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None
        mock_db.create_user.return_value = {"status": "success", "user_id": "admin_id"}
        mock_db.cleanup_sessions.return_value = 5  # 5 expired sessions cleaned
        mock_chroma_manager.return_value = mock_db
        
        auth_manager = AuthManager()
        result = auth_manager.cleanup_sessions()
        
        self.assertEqual(result, 5)
        mock_db.cleanup_sessions.assert_called_once()

    def test_hash_verification_roundtrip(self):
        """Test complete hash and verification roundtrip"""
        auth_manager = AuthManager.__new__(AuthManager)
        auth_manager._initialized = True
        
        test_passwords = ["simple", "complex!@#$%^&*()", "unicode_çğıöşü", ""]
        
        for password in test_passwords:
            with self.subTest(password=password):
                hashed = auth_manager._hash_password(password)
                self.assertTrue(auth_manager._verify_password(hashed, password))
                self.assertFalse(auth_manager._verify_password(hashed, password + "wrong"))


if __name__ == '__main__':
    unittest.main()