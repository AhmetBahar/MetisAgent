import unittest
from unittest.mock import patch, Mock, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from os_araci.coordination.context_manager import MCPContextManager


class TestMCPContextManager(unittest.TestCase):
    """Comprehensive unit tests for MCPContextManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.context_manager = MCPContextManager()

    @patch('os_araci.coordination.context_manager.logger')
    def test_init(self, mock_logger):
        """Test initialization of MCPContextManager"""
        manager = MCPContextManager()
        
        self.assertEqual(manager.context, {})
        mock_logger.info.assert_called_with("MCPContextManager başlatıldı")

    @patch('os_araci.coordination.context_manager.logger')
    def test_set_value_string(self, mock_logger):
        """Test setting a string value in context"""
        key = "test_key"
        value = "test_value"
        
        self.context_manager.set_value(key, value)
        
        self.assertEqual(self.context_manager.context[key], value)
        mock_logger.debug.assert_called_with(f"Context güncellendi: {key} = {value}")

    @patch('os_araci.coordination.context_manager.logger')
    def test_set_value_long_string(self, mock_logger):
        """Test setting a long string value in context"""
        key = "long_key"
        value = "a" * 150  # String longer than 100 characters
        
        self.context_manager.set_value(key, value)
        
        self.assertEqual(self.context_manager.context[key], value)
        mock_logger.debug.assert_called_with(f"Context güncellendi: {key} = {value[:100]}")

    @patch('os_araci.coordination.context_manager.logger')
    def test_set_value_non_string(self, mock_logger):
        """Test setting a non-string value in context"""
        key = "number_key"
        value = 42
        
        self.context_manager.set_value(key, value)
        
        self.assertEqual(self.context_manager.context[key], value)
        mock_logger.debug.assert_called_with(f"Context güncellendi: {key} = {value}")

    @patch('os_araci.coordination.context_manager.logger')
    def test_set_value_list(self, mock_logger):
        """Test setting a list value in context"""
        key = "list_key"
        value = [1, 2, 3, "test"]
        
        self.context_manager.set_value(key, value)
        
        self.assertEqual(self.context_manager.context[key], value)
        mock_logger.debug.assert_called_with(f"Context güncellendi: {key} = {value}")

    @patch('os_araci.coordination.context_manager.logger')
    def test_set_value_dict(self, mock_logger):
        """Test setting a dictionary value in context"""
        key = "dict_key"
        value = {"nested": "value", "number": 123}
        
        self.context_manager.set_value(key, value)
        
        self.assertEqual(self.context_manager.context[key], value)
        mock_logger.debug.assert_called_with(f"Context güncellendi: {key} = {value}")

    @patch('os_araci.coordination.context_manager.logger')
    def test_set_value_overwrite(self, mock_logger):
        """Test overwriting an existing value in context"""
        key = "overwrite_key"
        value1 = "first_value"
        value2 = "second_value"
        
        self.context_manager.set_value(key, value1)
        self.context_manager.set_value(key, value2)
        
        self.assertEqual(self.context_manager.context[key], value2)
        self.assertEqual(mock_logger.debug.call_count, 2)

    def test_get_value_existing(self):
        """Test getting an existing value from context"""
        key = "existing_key"
        value = "existing_value"
        
        self.context_manager.context[key] = value
        result = self.context_manager.get_value(key)
        
        self.assertEqual(result, value)

    def test_get_value_non_existing_with_default(self):
        """Test getting a non-existing value with default"""
        key = "non_existing_key"
        default = "default_value"
        
        result = self.context_manager.get_value(key, default)
        
        self.assertEqual(result, default)

    def test_get_value_non_existing_without_default(self):
        """Test getting a non-existing value without default"""
        key = "non_existing_key"
        
        result = self.context_manager.get_value(key)
        
        self.assertIsNone(result)

    def test_get_value_with_none_default(self):
        """Test getting a non-existing value with None as default"""
        key = "non_existing_key"
        
        result = self.context_manager.get_value(key, None)
        
        self.assertIsNone(result)

    def test_get_value_with_empty_string_default(self):
        """Test getting a non-existing value with empty string as default"""
        key = "non_existing_key"
        default = ""
        
        result = self.context_manager.get_value(key, default)
        
        self.assertEqual(result, default)

    @patch('os_araci.coordination.context_manager.logger')
    def test_apply_template_no_placeholders(self, mock_logger):
        """Test applying template without placeholders"""
        template = "This is a simple string without placeholders"
        
        result = self.context_manager.apply_template(template)
        
        self.assertEqual(result, template)
        mock_logger.debug.assert_not_called()
        mock_logger.info.assert_not_called()

    @patch('os_araci.coordination.context_manager.logger')
    def test_apply_template_single_placeholder(self, mock_logger):
        """Test applying template with single placeholder"""
        self.context_manager.context["name"] = "John"
        template = "Hello <name>!"
        expected = "Hello John!"
        
        result = self.context_manager.apply_template(template)
        
        self.assertEqual(result, expected)
        mock_logger.debug.assert_called_with("Placeholder değiştirildi: <name> -> John...")
        mock_logger.info.assert_called_with(f"Şablon değiştirildi: {template[:50]}... -> {expected[:50]}...")

    @patch('os_araci.coordination.context_manager.logger')
    def test_apply_template_multiple_placeholders(self, mock_logger):
        """Test applying template with multiple placeholders"""
        self.context_manager.context["name"] = "Alice"
        self.context_manager.context["age"] = 30
        self.context_manager.context["city"] = "New York"
        template = "Hello <name>, you are <age> years old and live in <city>."
        expected = "Hello Alice, you are 30 years old and live in New York."
        
        result = self.context_manager.apply_template(template)
        
        self.assertEqual(result, expected)
        self.assertEqual(mock_logger.debug.call_count, 3)

    @patch('os_araci.coordination.context_manager.logger')
    def test_apply_template_repeated_placeholder(self, mock_logger):
        """Test applying template with repeated placeholder"""
        self.context_manager.context["word"] = "test"
        template = "This is a <word> and another <word> example."
        expected = "This is a test and another test example."
        
        result = self.context_manager.apply_template(template)
        
        self.assertEqual(result, expected)

    @patch('os_araci.coordination.context_manager.logger')
    def test_apply_template_missing_placeholder(self, mock_logger):
        """Test applying template with missing placeholder"""
        self.context_manager.context["name"] = "Bob"
        template = "Hello <name>, your score is <score>."
        expected = "Hello Bob, your score is <score>."
        
        result = self.context_manager.apply_template(template)
        
        self.assertEqual(result, expected)
        mock_logger.debug.assert_called_once_with("Placeholder değiştirildi: <name> -> Bob...")

    @patch('os_araci.coordination.context_manager.logger')
    def test_apply_template_long_value(self, mock_logger):
        """Test applying template with long value"""
        long_value = "a" * 100
        self.context_manager.context["long_value"] = long_value
        template = "Value: <long_value>"
        expected = f"Value: {long_value}"
        
        result = self.context_manager.apply_template(template)
        
        self.assertEqual(result, expected)
        mock_logger.debug.assert_called_with(f"Placeholder değiştirildi: <long_value> -> {long_value[:50]}...")

    @patch('os_araci.coordination.context_manager.logger')
    def test_apply_template_non_string_value(self, mock_logger):
        """Test applying template with non-string value"""
        self.context_manager.context["number"] = 42
        self.context_manager.context["boolean"] = True
        template = "Number: <number>, Boolean: <boolean>"
        expected = "Number: 42, Boolean: True"
        
        result = self.context_manager.apply_template(template)
        
        self.assertEqual(result, expected)

    def test_apply_template_non_string_input(self):
        """Test applying template with non-string input"""
        non_string_input = 123
        
        result = self.context_manager.apply_template(non_string_input)
        
        self.assertEqual(result, non_string_input)

    def test_apply_template_none_input(self):
        """Test applying template with None input"""
        result = self.context_manager.apply_template(None)
        
        self.assertIsNone(result)

    def test_apply_template_empty_string(self):
        """Test applying template with empty string"""
        result = self.context_manager.apply_template("")
        
        self.assertEqual(result, "")

    @patch('os_araci.coordination.context_manager.logger')
    def test_apply_template_complex_placeholders(self, mock_logger):
        """Test applying template with complex placeholder patterns"""
        self.context_manager.context["user_name"] = "admin"
        self.context_manager.context["user-id"] = "123"
        template = "User: <user_name>, ID: <user-id>"
        expected = "User: admin, ID: 123"
        
        result = self.context_manager.apply_template(template)
        
        self.assertEqual(result, expected)

    @patch('os_araci.coordination.context_manager.logger')
    def test_apply_template_nested_placeholders(self, mock_logger):
        """Test applying template with nested-like placeholders"""
        self.context_manager.context["inner"] = "value"
        template = "<<inner>>"
        expected = "<value>"
        
        result = self.context_manager.apply_template(template)
        
        self.assertEqual(result, expected)

    @patch('os_araci.coordination.context_manager.logger')
    def test_clear_context(self, mock_logger):
        """Test clearing the context"""
        self.context_manager.context["key1"] = "value1"
        self.context_manager.context["key2"] = "value2"
        
        self.context_manager.clear()
        
        self.assertEqual(self.context_manager.context, {})
        mock_logger.info.assert_called_with("Context temizlendi")

    @patch('os_araci.coordination.context_manager.logger')
    def test_clear_empty_context(self, mock_logger):
        """Test clearing an already empty context"""
        self.context_manager.clear()
        
        self.assertEqual(self.context_manager.context, {})
        mock_logger.info.assert_called_with("Context temizlendi")

    def test_context_persistence_across_operations(self):
        """Test that context persists across multiple operations"""
        # Set multiple values
        self.context_manager.set_value("key1", "value1")
        self.context_manager.set_value("key2", "value2")
        
        # Get values
        result1 = self.context_manager.get_value("key1")
        result2 = self.context_manager.get_value("key2")
        
        # Apply template
        template_result = self.context_manager.apply_template("Template: <key1> and <key2>")
        
        # Verify all operations worked with the same context
        self.assertEqual(result1, "value1")
        self.assertEqual(result2, "value2")
        self.assertEqual(template_result, "Template: value1 and value2")
        self.assertEqual(len(self.context_manager.context), 2)

    def test_context_isolation(self):
        """Test that different instances have isolated contexts"""
        manager1 = MCPContextManager()
        manager2 = MCPContextManager()
        
        manager1.set_value("key", "value1")
        manager2.set_value("key", "value2")
        
        self.assertEqual(manager1.get_value("key"), "value1")
        self.assertEqual(manager2.get_value("key"), "value2")

    def tearDown(self):
        """Clean up after each test"""
        pass


if __name__ == '__main__':
    unittest.main()