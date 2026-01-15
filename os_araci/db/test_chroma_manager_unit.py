import unittest
from unittest.mock import patch, Mock, MagicMock, mock_open
import sys
import os
import json
import time
import uuid
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from os_araci.db.chroma_manager import ChromaManager


class TestChromaManager(unittest.TestCase):
    """Comprehensive unit tests for ChromaManager"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset the singleton instance for each test
        ChromaManager._instance = None

    def tearDown(self):
        """Clean up after each test"""
        # Reset the singleton instance
        ChromaManager._instance = None

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_singleton_pattern(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test that ChromaManager follows singleton pattern"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        
        # Mock collections
        for collection_name in ['users', 'api_keys', 'sessions', 'personas']:
            mock_collection = MagicMock()
            mock_chroma_client.get_or_create_collection.return_value = mock_collection
        
        manager1 = ChromaManager()
        manager2 = ChromaManager()
        
        self.assertIs(manager1, manager2)

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_init_with_base_path(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test initialization with custom base path"""
        custom_path = "/custom/path"
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        
        manager = ChromaManager(base_path=custom_path)
        
        self.assertEqual(manager.base_path, custom_path)
        mock_makedirs.assert_called_with(custom_path, exist_ok=True)

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_init_vector_search_available(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test initialization with vector search available"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_model = MagicMock()
        mock_sentence_transformer.return_value = mock_model
        
        manager = ChromaManager()
        
        self.assertTrue(manager.vector_search_available)
        self.assertEqual(manager.embedding_model, mock_model)

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('builtins.print')
    def test_init_vector_search_unavailable(self, mock_print, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test initialization when SentenceTransformer is not available"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.side_effect = ImportError("SentenceTransformer not found")
        
        manager = ChromaManager()
        
        self.assertFalse(manager.vector_search_available)
        self.assertIsNone(manager.embedding_model)
        mock_print.assert_called_with("SentenceTransformer yüklenemedi, vektör araması devre dışı.")

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_get_memory_collection_new(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test getting memory collection for new user"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_memory_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_memory_collection
        
        manager = ChromaManager()
        result = manager.get_memory_collection("testuser")
        
        self.assertEqual(result, mock_memory_collection)
        self.assertIn("testuser", manager.memories_collection)
        mock_chroma_client.get_or_create_collection.assert_called_with("memories_testuser")

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_get_memory_collection_existing(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test getting memory collection for existing user"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_memory_collection = MagicMock()
        
        manager = ChromaManager()
        manager.memories_collection["testuser"] = mock_memory_collection
        
        result = manager.get_memory_collection("testuser")
        
        self.assertEqual(result, mock_memory_collection)

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_create_user_success(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test successful user creation"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_users_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_users_collection
        
        manager = ChromaManager()
        manager.get_user = MagicMock(return_value=None)  # User doesn't exist
        
        result = manager.create_user("testuser", "password_hash", ["read", "write"])
        
        self.assertEqual(result["status"], "success")
        self.assertIn("user_id", result)
        mock_users_collection.add.assert_called_once()

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_create_user_already_exists(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test user creation when user already exists"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        
        manager = ChromaManager()
        manager.get_user = MagicMock(return_value={"user_id": "existing_id"})
        
        result = manager.create_user("testuser", "password_hash", ["read"])
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Kullanıcı zaten mevcut")

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_create_user_exception(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test user creation with exception"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_users_collection = MagicMock()
        mock_users_collection.add.side_effect = Exception("Database error")
        mock_chroma_client.get_or_create_collection.return_value = mock_users_collection
        
        manager = ChromaManager()
        manager.get_user = MagicMock(return_value=None)
        
        result = manager.create_user("testuser", "password_hash", ["read"])
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Database error")
        mock_logger.error.assert_called()

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_get_user_found(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test getting existing user"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_users_collection = MagicMock()
        
        mock_users_collection.get.return_value = {
            "ids": ["user123"],
            "metadatas": [{
                "username": "testuser",
                "password_hash": "hash123",
                "permissions": '["read", "write"]',
                "created_at": "2025-01-01T00:00:00",
                "last_login": "2025-01-02T00:00:00"
            }]
        }
        mock_chroma_client.get_or_create_collection.return_value = mock_users_collection
        
        manager = ChromaManager()
        result = manager.get_user("testuser")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["user_id"], "user123")
        self.assertEqual(result["username"], "testuser")
        self.assertEqual(result["permissions"], ["read", "write"])

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_get_user_not_found(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test getting non-existing user"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_users_collection = MagicMock()
        
        mock_users_collection.get.return_value = {"ids": [], "metadatas": []}
        mock_chroma_client.get_or_create_collection.return_value = mock_users_collection
        
        manager = ChromaManager()
        result = manager.get_user("nonexistent")
        
        self.assertIsNone(result)

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_get_user_exception(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test getting user with exception"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_users_collection = MagicMock()
        
        mock_users_collection.get.side_effect = Exception("Database error")
        mock_chroma_client.get_or_create_collection.return_value = mock_users_collection
        
        manager = ChromaManager()
        result = manager.get_user("testuser")
        
        self.assertIsNone(result)
        mock_logger.error.assert_called()

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_create_api_key(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test API key creation"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_api_keys_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_api_keys_collection
        
        manager = ChromaManager()
        manager.vector_search_available = True
        
        result = manager.create_api_key("user123", ["read", "write"])
        
        self.assertTrue(result.startswith("metis_"))
        mock_api_keys_collection.add.assert_called_once()

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_validate_api_key_valid(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test validation of valid API key"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_api_keys_collection = MagicMock()
        
        mock_api_keys_collection.get.return_value = {
            "ids": ["metis_abc123"]
        }
        mock_chroma_client.get_or_create_collection.return_value = mock_api_keys_collection
        
        manager = ChromaManager()
        result = manager.validate_api_key("metis_abc123")
        
        self.assertTrue(result)

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_validate_api_key_invalid(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test validation of invalid API key"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_api_keys_collection = MagicMock()
        
        mock_api_keys_collection.get.return_value = {"ids": []}
        mock_chroma_client.get_or_create_collection.return_value = mock_api_keys_collection
        
        manager = ChromaManager()
        result = manager.validate_api_key("invalid_key")
        
        self.assertFalse(result)

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_create_session(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test session creation"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_sessions_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_sessions_collection
        
        manager = ChromaManager()
        result = manager.create_session("user123", expires_in=1800)
        
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)  # 32 bytes hex = 64 chars
        mock_sessions_collection.add.assert_called_once()

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_validate_session_valid(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test validation of valid session"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_sessions_collection = MagicMock()
        
        future_time = datetime.now().isoformat()
        mock_sessions_collection.query.return_value = {
            "ids": [["session123"]],
            "metadatas": [[{
                "user_id": "user123",
                "expires_at": future_time
            }]]
        }
        mock_chroma_client.get_or_create_collection.return_value = mock_sessions_collection
        
        manager = ChromaManager()
        
        with patch('os_araci.db.chroma_manager.datetime') as mock_datetime:
            mock_datetime.fromisoformat.return_value = datetime.now()
            mock_datetime.now.return_value = datetime.now()
            
            result = manager.validate_session("session_token")
            
            self.assertEqual(result, "user123")

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_validate_session_invalid(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test validation of invalid session"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_sessions_collection = MagicMock()
        
        mock_sessions_collection.query.return_value = {"ids": [[]], "metadatas": [[]]}
        mock_chroma_client.get_or_create_collection.return_value = mock_sessions_collection
        
        manager = ChromaManager()
        result = manager.validate_session("invalid_session")
        
        self.assertIsNone(result)

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_create_persona_success(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test successful persona creation"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_personas_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_personas_collection
        
        persona_data = {
            "name": "Test Persona",
            "description": "A test persona",
            "class_name": "TestPersona"
        }
        
        manager = ChromaManager()
        manager.get_persona = MagicMock(return_value=None)  # Persona doesn't exist
        
        result = manager.create_persona(persona_data)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("persona_id", result)
        mock_personas_collection.add.assert_called_once()

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_create_persona_already_exists(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test persona creation when persona already exists"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        
        persona_data = {"id": "existing_persona"}
        
        manager = ChromaManager()
        manager.get_persona = MagicMock(return_value={"id": "existing_persona"})
        
        result = manager.create_persona(persona_data)
        
        self.assertEqual(result["status"], "error")
        self.assertIn("zaten mevcut", result["message"])

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_get_persona_found(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test getting existing persona"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_personas_collection = MagicMock()
        
        persona_data = {
            "id": "test_persona",
            "name": "Test Persona",
            "description": "Test description"
        }
        
        mock_personas_collection.get.return_value = {
            "ids": ["test_persona"],
            "documents": [json.dumps(persona_data)],
            "metadatas": [{
                "persona_id": "test_persona",
                "name": "Test Persona"
            }]
        }
        mock_chroma_client.get_or_create_collection.return_value = mock_personas_collection
        
        manager = ChromaManager()
        result = manager.get_persona("test_persona")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "test_persona")
        self.assertEqual(result["name"], "Test Persona")

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_get_persona_not_found(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test getting non-existing persona"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_personas_collection = MagicMock()
        
        mock_personas_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        mock_chroma_client.get_or_create_collection.return_value = mock_personas_collection
        
        manager = ChromaManager()
        result = manager.get_persona("nonexistent")
        
        self.assertIsNone(result)

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_get_all_personas(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test getting all personas"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_personas_collection = MagicMock()
        
        persona1_data = {"id": "persona1", "name": "Persona 1"}
        persona2_data = {"id": "persona2", "name": "Persona 2"}
        
        mock_personas_collection.get.return_value = {
            "ids": ["persona1", "persona2"],
            "documents": [json.dumps(persona1_data), json.dumps(persona2_data)],
            "metadatas": [
                {"persona_id": "persona1", "name": "Persona 1"},
                {"persona_id": "persona2", "name": "Persona 2"}
            ]
        }
        mock_chroma_client.get_or_create_collection.return_value = mock_personas_collection
        
        manager = ChromaManager()
        result = manager.get_all_personas()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "persona1")
        self.assertEqual(result[1]["id"], "persona2")

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_delete_persona_success(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test successful persona deletion"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_personas_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_personas_collection
        
        manager = ChromaManager()
        manager.get_persona = MagicMock(return_value={"id": "custom_persona"})
        
        result = manager.delete_persona("custom_persona")
        
        self.assertEqual(result["status"], "success")
        mock_personas_collection.delete.assert_called_once()

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_delete_persona_default_protected(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test deletion of protected default persona"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        
        manager = ChromaManager()
        result = manager.delete_persona("assistant")  # Default persona
        
        self.assertEqual(result["status"], "error")
        self.assertIn("Varsayılan personalar silinemez", result["message"])

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_delete_persona_not_found(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test deletion of non-existing persona"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        
        manager = ChromaManager()
        manager.get_persona = MagicMock(return_value=None)
        
        result = manager.delete_persona("nonexistent")
        
        self.assertEqual(result["status"], "error")
        self.assertIn("bulunamadı", result["message"])

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_update_persona_success(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test successful persona update"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_personas_collection = MagicMock()
        mock_chroma_client.get_or_create_collection.return_value = mock_personas_collection
        
        existing_persona = {
            "id": "test_persona",
            "name": "Old Name",
            "description": "Old description"
        }
        
        update_data = {
            "name": "New Name",
            "description": "New description"
        }
        
        manager = ChromaManager()
        manager.get_persona = MagicMock(return_value=existing_persona)
        
        result = manager.update_persona("test_persona", update_data)
        
        self.assertEqual(result["status"], "success")
        mock_personas_collection.delete.assert_called_once()
        mock_personas_collection.add.assert_called_once()

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    @patch('os_araci.db.chroma_manager.logger')
    def test_init_default_personas(self, mock_logger, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test initialization of default personas"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        
        manager = ChromaManager()
        manager.get_persona = MagicMock(return_value=None)  # No personas exist
        manager.create_persona = MagicMock(return_value={"status": "success"})
        
        count = manager.init_default_personas()
        
        self.assertGreater(count, 0)
        self.assertGreaterEqual(manager.create_persona.call_count, 3)  # At least 3 default personas

    @patch('os_araci.db.chroma_manager.chromadb.PersistentClient')
    @patch('os_araci.db.chroma_manager.os.makedirs')
    @patch('os_araci.db.chroma_manager.SentenceTransformer')
    def test_cleanup_sessions(self, mock_sentence_transformer, mock_makedirs, mock_client):
        """Test cleanup of expired sessions"""
        mock_chroma_client = MagicMock()
        mock_client.return_value = mock_chroma_client
        mock_sentence_transformer.return_value = MagicMock()
        mock_sessions_collection = MagicMock()
        
        current_time = time.time()
        expired_time = str(current_time - 3600)  # 1 hour ago
        valid_time = str(current_time + 3600)    # 1 hour from now
        
        mock_sessions_collection.get.return_value = {
            "ids": ["session1", "session2", "session3"],
            "metadatas": [
                {"expires_at": expired_time},    # Expired
                {"expires_at": valid_time},      # Valid
                {"expires_at": expired_time}     # Expired
            ]
        }
        mock_chroma_client.get_or_create_collection.return_value = mock_sessions_collection
        
        manager = ChromaManager()
        
        with patch('os_araci.db.chroma_manager.time.time', return_value=current_time):
            expired_count = manager.cleanup_sessions()
        
        self.assertEqual(expired_count, 2)  # 2 expired sessions
        self.assertEqual(mock_sessions_collection.delete.call_count, 2)

    def test_complex_workflow(self):
        """Test a complex workflow involving multiple operations"""
        with patch('os_araci.db.chroma_manager.chromadb.PersistentClient') as mock_client, \
             patch('os_araci.db.chroma_manager.os.makedirs'), \
             patch('os_araci.db.chroma_manager.SentenceTransformer'):
            
            mock_chroma_client = MagicMock()
            mock_client.return_value = mock_chroma_client
            
            # Mock collections
            collections = {}
            for name in ['users', 'api_keys', 'sessions', 'personas']:
                collections[name] = MagicMock()
            
            def get_collection(name):
                return collections[name.split('_')[0]]  # Handle memory collections
            
            mock_chroma_client.get_or_create_collection.side_effect = get_collection
            
            manager = ChromaManager()
            
            # Test user operations
            manager.get_user = MagicMock(return_value=None)
            result = manager.create_user("testuser", "hash", ["read"])
            self.assertEqual(result["status"], "success")
            
            # Test persona operations
            manager.get_persona = MagicMock(return_value=None)
            persona_data = {"name": "Test", "description": "Test persona"}
            result = manager.create_persona(persona_data)
            self.assertEqual(result["status"], "success")


if __name__ == '__main__':
    unittest.main()