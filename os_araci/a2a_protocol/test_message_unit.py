import unittest
from unittest.mock import patch, Mock, MagicMock
import sys
import os
import json
import time
import uuid

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from os_araci.a2a_protocol.message import A2AMessage


class TestA2AMessage(unittest.TestCase):
    """Comprehensive unit tests for A2AMessage"""

    def setUp(self):
        """Set up test fixtures"""
        self.sender = "agent1"
        self.receiver = "agent2"
        self.message_type = "request"
        self.content = {"action": "ping", "data": "test"}

    def test_init_with_required_parameters(self):
        """Test initialization with required parameters only"""
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content
        )
        
        self.assertEqual(message.sender, self.sender)
        self.assertEqual(message.receiver, self.receiver)
        self.assertEqual(message.message_type, self.message_type)
        self.assertEqual(message.content, self.content)
        self.assertIsNotNone(message.message_id)
        self.assertIsNone(message.correlation_id)
        self.assertIsNone(message.reply_to)
        self.assertIsNone(message.expires_at)
        self.assertEqual(message.priority, 5)
        self.assertEqual(message.headers, {})
        self.assertIsInstance(message.created_at, float)

    def test_init_with_all_parameters(self):
        """Test initialization with all parameters"""
        message_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        reply_to = str(uuid.uuid4())
        expires_at = time.time() + 3600
        priority = 8
        headers = {"source": "test", "version": "1.0"}
        
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            message_id=message_id,
            correlation_id=correlation_id,
            reply_to=reply_to,
            expires_at=expires_at,
            priority=priority,
            headers=headers
        )
        
        self.assertEqual(message.message_id, message_id)
        self.assertEqual(message.correlation_id, correlation_id)
        self.assertEqual(message.reply_to, reply_to)
        self.assertEqual(message.expires_at, expires_at)
        self.assertEqual(message.priority, priority)
        self.assertEqual(message.headers, headers)

    def test_priority_bounds(self):
        """Test priority bounds enforcement"""
        # Test priority lower bound
        message_low = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            priority=-5
        )
        self.assertEqual(message_low.priority, 1)
        
        # Test priority upper bound
        message_high = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            priority=15
        )
        self.assertEqual(message_high.priority, 10)
        
        # Test valid priority
        message_valid = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            priority=7
        )
        self.assertEqual(message_valid.priority, 7)

    def test_auto_generated_message_id(self):
        """Test auto-generated message ID"""
        message1 = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content
        )
        
        message2 = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content
        )
        
        self.assertIsNotNone(message1.message_id)
        self.assertIsNotNone(message2.message_id)
        self.assertNotEqual(message1.message_id, message2.message_id)

    def test_none_headers_default(self):
        """Test that None headers defaults to empty dict"""
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            headers=None
        )
        
        self.assertEqual(message.headers, {})

    def test_to_dict(self):
        """Test converting message to dictionary"""
        message_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        reply_to = str(uuid.uuid4())
        expires_at = time.time() + 3600
        priority = 7
        headers = {"test": "value"}
        
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            message_id=message_id,
            correlation_id=correlation_id,
            reply_to=reply_to,
            expires_at=expires_at,
            priority=priority,
            headers=headers
        )
        
        result_dict = message.to_dict()
        
        expected_dict = {
            "message_id": message_id,
            "correlation_id": correlation_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "content": self.content,
            "reply_to": reply_to,
            "created_at": message.created_at,
            "expires_at": expires_at,
            "priority": priority,
            "headers": headers
        }
        
        self.assertEqual(result_dict, expected_dict)

    def test_from_dict(self):
        """Test creating message from dictionary"""
        message_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        reply_to = str(uuid.uuid4())
        created_at = time.time()
        expires_at = time.time() + 3600
        priority = 7
        headers = {"test": "value"}
        
        message_dict = {
            "message_id": message_id,
            "correlation_id": correlation_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "content": self.content,
            "reply_to": reply_to,
            "created_at": created_at,
            "expires_at": expires_at,
            "priority": priority,
            "headers": headers
        }
        
        message = A2AMessage.from_dict(message_dict)
        
        self.assertEqual(message.message_id, message_id)
        self.assertEqual(message.correlation_id, correlation_id)
        self.assertEqual(message.sender, self.sender)
        self.assertEqual(message.receiver, self.receiver)
        self.assertEqual(message.message_type, self.message_type)
        self.assertEqual(message.content, self.content)
        self.assertEqual(message.reply_to, reply_to)
        self.assertEqual(message.expires_at, expires_at)
        self.assertEqual(message.priority, priority)
        self.assertEqual(message.headers, headers)

    def test_from_dict_partial(self):
        """Test creating message from partial dictionary"""
        partial_dict = {
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type
        }
        
        message = A2AMessage.from_dict(partial_dict)
        
        self.assertEqual(message.sender, self.sender)
        self.assertEqual(message.receiver, self.receiver)
        self.assertEqual(message.message_type, self.message_type)
        self.assertEqual(message.content, {})  # Default empty dict
        self.assertIsNone(message.message_id)  # None in dict
        self.assertIsNone(message.correlation_id)
        self.assertIsNone(message.reply_to)
        self.assertIsNone(message.expires_at)
        self.assertEqual(message.priority, 5)  # Default value
        self.assertEqual(message.headers, {})  # Default empty dict

    def test_from_dict_empty_content(self):
        """Test creating message from dict with missing content"""
        message_dict = {
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type
        }
        
        message = A2AMessage.from_dict(message_dict)
        
        self.assertEqual(message.content, {})

    def test_from_dict_empty_headers(self):
        """Test creating message from dict with missing headers"""
        message_dict = {
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "content": self.content
        }
        
        message = A2AMessage.from_dict(message_dict)
        
        self.assertEqual(message.headers, {})

    def test_to_json(self):
        """Test converting message to JSON"""
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content
        )
        
        json_str = message.to_json()
        
        # Parse the JSON to verify it's valid
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed["sender"], self.sender)
        self.assertEqual(parsed["receiver"], self.receiver)
        self.assertEqual(parsed["message_type"], self.message_type)
        self.assertEqual(parsed["content"], self.content)

    def test_from_json(self):
        """Test creating message from JSON"""
        message_dict = {
            "message_id": str(uuid.uuid4()),
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "content": self.content,
            "priority": 7
        }
        
        json_str = json.dumps(message_dict)
        message = A2AMessage.from_json(json_str)
        
        self.assertEqual(message.sender, self.sender)
        self.assertEqual(message.receiver, self.receiver)
        self.assertEqual(message.message_type, self.message_type)
        self.assertEqual(message.content, self.content)
        self.assertEqual(message.priority, 7)

    def test_json_roundtrip(self):
        """Test JSON serialization roundtrip"""
        original_message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            priority=8,
            headers={"test": "value"}
        )
        
        json_str = original_message.to_json()
        recreated_message = A2AMessage.from_json(json_str)
        
        self.assertEqual(original_message.sender, recreated_message.sender)
        self.assertEqual(original_message.receiver, recreated_message.receiver)
        self.assertEqual(original_message.message_type, recreated_message.message_type)
        self.assertEqual(original_message.content, recreated_message.content)
        self.assertEqual(original_message.priority, recreated_message.priority)
        self.assertEqual(original_message.headers, recreated_message.headers)

    def test_create_reply(self):
        """Test creating a reply message"""
        original_message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            priority=7
        )
        
        reply_content = {"status": "success", "result": "pong"}
        reply_message = original_message.create_reply(reply_content)
        
        self.assertEqual(reply_message.sender, self.receiver)  # Swapped
        self.assertEqual(reply_message.receiver, self.sender)  # Swapped
        self.assertEqual(reply_message.message_type, f"reply:{self.message_type}")
        self.assertEqual(reply_message.content, reply_content)
        self.assertEqual(reply_message.correlation_id, original_message.message_id)
        self.assertEqual(reply_message.reply_to, original_message.message_id)
        self.assertEqual(reply_message.priority, original_message.priority)

    def test_create_reply_with_custom_message_type(self):
        """Test creating a reply with custom message type"""
        original_message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content
        )
        
        reply_content = {"status": "error", "message": "Failed"}
        custom_type = "error_response"
        reply_message = original_message.create_reply(reply_content, custom_type)
        
        self.assertEqual(reply_message.message_type, custom_type)
        self.assertEqual(reply_message.content, reply_content)

    def test_create_reply_preserves_priority(self):
        """Test that reply preserves original message priority"""
        original_message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            priority=9
        )
        
        reply_message = original_message.create_reply({"result": "ok"})
        
        self.assertEqual(reply_message.priority, 9)

    def test_is_expired_no_expiry(self):
        """Test is_expired when no expiry is set"""
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content
        )
        
        self.assertFalse(message.is_expired())

    def test_is_expired_not_yet_expired(self):
        """Test is_expired when message is not yet expired"""
        future_time = time.time() + 3600  # 1 hour in the future
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            expires_at=future_time
        )
        
        self.assertFalse(message.is_expired())

    def test_is_expired_already_expired(self):
        """Test is_expired when message is already expired"""
        past_time = time.time() - 3600  # 1 hour in the past
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            expires_at=past_time
        )
        
        self.assertTrue(message.is_expired())

    @patch('os_araci.a2a_protocol.message.time.time')
    def test_is_expired_exactly_at_expiry(self, mock_time):
        """Test is_expired when current time is exactly at expiry"""
        expiry_time = 1000000.0
        mock_time.return_value = expiry_time + 0.001  # Slightly past expiry
        
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            expires_at=expiry_time
        )
        
        self.assertTrue(message.is_expired())

    def test_dict_roundtrip(self):
        """Test dictionary serialization roundtrip"""
        original_message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            priority=6,
            headers={"custom": "header"}
        )
        
        message_dict = original_message.to_dict()
        recreated_message = A2AMessage.from_dict(message_dict)
        
        self.assertEqual(original_message.sender, recreated_message.sender)
        self.assertEqual(original_message.receiver, recreated_message.receiver)
        self.assertEqual(original_message.message_type, recreated_message.message_type)
        self.assertEqual(original_message.content, recreated_message.content)
        self.assertEqual(original_message.priority, recreated_message.priority)
        self.assertEqual(original_message.headers, recreated_message.headers)

    def test_complex_content(self):
        """Test message with complex nested content"""
        complex_content = {
            "action": "complex_operation",
            "parameters": {
                "nested_list": [1, 2, {"inner": "value"}],
                "boolean_flag": True,
                "null_value": None
            },
            "metadata": {
                "timestamp": time.time(),
                "source": "test_suite"
            }
        }
        
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=complex_content
        )
        
        # Test JSON roundtrip with complex content
        json_str = message.to_json()
        recreated_message = A2AMessage.from_json(json_str)
        
        self.assertEqual(message.content, recreated_message.content)

    def test_empty_content(self):
        """Test message with empty content"""
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content={}
        )
        
        self.assertEqual(message.content, {})

    def test_none_optional_fields(self):
        """Test message with explicitly None optional fields"""
        message = A2AMessage(
            sender=self.sender,
            receiver=self.receiver,
            message_type=self.message_type,
            content=self.content,
            message_id=None,
            correlation_id=None,
            reply_to=None,
            expires_at=None,
            headers=None
        )
        
        self.assertIsNotNone(message.message_id)  # Auto-generated
        self.assertIsNone(message.correlation_id)
        self.assertIsNone(message.reply_to)
        self.assertIsNone(message.expires_at)
        self.assertEqual(message.headers, {})

    def tearDown(self):
        """Clean up after each test"""
        pass


if __name__ == '__main__':
    unittest.main()