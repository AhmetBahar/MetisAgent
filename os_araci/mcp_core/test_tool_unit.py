import unittest
from unittest.mock import patch, Mock, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from os_araci.mcp_core.tool import MCPTool


class TestMCPTool(unittest.TestCase):
    """Comprehensive unit tests for MCPTool"""

    def setUp(self):
        """Set up test fixtures"""
        self.tool = MCPTool(
            name="test_tool",
            description="Test tool for unit testing",
            version="1.0.0",
            category="test"
        )

    def test_init_with_all_parameters(self):
        """Test initialization with all parameters"""
        tool = MCPTool(
            name="custom_tool",
            description="Custom test tool",
            version="2.0.0",
            category="custom"
        )
        
        self.assertEqual(tool.name, "custom_tool")
        self.assertEqual(tool.description, "Custom test tool")
        self.assertEqual(tool.version, "2.0.0")
        self.assertEqual(tool.category, "custom")
        self.assertEqual(tool._actions, {})
        self.assertEqual(tool._capabilities, [])

    def test_init_with_default_parameters(self):
        """Test initialization with default parameters"""
        tool = MCPTool(
            name="minimal_tool",
            description="Minimal test tool"
        )
        
        self.assertEqual(tool.name, "minimal_tool")
        self.assertEqual(tool.description, "Minimal test tool")
        self.assertEqual(tool.version, "1.0.0")
        self.assertEqual(tool.category, "general")

    @patch('os_araci.mcp_core.tool.logger')
    def test_register_action_success(self, mock_logger):
        """Test successful action registration"""
        def test_handler(**kwargs):
            return "test result"
        
        result = self.tool.register_action(
            name="test_action",
            handler=test_handler,
            params=["param1", "param2"],
            description="Test action",
            required_capabilities=["test_capability"]
        )
        
        self.assertTrue(result)
        self.assertIn("test_action", self.tool._actions)
        action = self.tool._actions["test_action"]
        self.assertEqual(action["func"], test_handler)
        self.assertEqual(action["params"], ["param1", "param2"])
        self.assertEqual(action["description"], "Test action")
        self.assertEqual(action["required_capabilities"], ["test_capability"])
        mock_logger.info.assert_called_with("Aksiyon kaydedildi: test_action, araç: test_tool")

    @patch('os_araci.mcp_core.tool.logger')
    def test_register_action_with_defaults(self, mock_logger):
        """Test action registration with default parameters"""
        def test_handler():
            return "test result"
        
        result = self.tool.register_action("simple_action", test_handler)
        
        self.assertTrue(result)
        action = self.tool._actions["simple_action"]
        self.assertEqual(action["params"], [])
        self.assertEqual(action["description"], "")
        self.assertEqual(action["required_capabilities"], [])

    @patch('os_araci.mcp_core.tool.logger')
    def test_register_action_duplicate(self, mock_logger):
        """Test registering duplicate action"""
        def test_handler():
            return "test result"
        
        # Register first time
        result1 = self.tool.register_action("duplicate_action", test_handler)
        # Try to register again
        result2 = self.tool.register_action("duplicate_action", test_handler)
        
        self.assertTrue(result1)
        self.assertFalse(result2)
        mock_logger.warning.assert_called_with("Aksiyon zaten kayıtlı: duplicate_action, araç: test_tool")

    @patch('os_araci.mcp_core.tool.logger')
    def test_register_capability_success(self, mock_logger):
        """Test successful capability registration"""
        result = self.tool.register_capability("test_capability", "Test capability description")
        
        self.assertTrue(result)
        self.assertIn("test_capability", self.tool._capabilities)
        mock_logger.info.assert_called_with("Yetenek kaydedildi: test_capability, araç: test_tool")

    @patch('os_araci.mcp_core.tool.logger')
    def test_register_capability_with_empty_description(self, mock_logger):
        """Test capability registration with empty description"""
        result = self.tool.register_capability("simple_capability")
        
        self.assertTrue(result)
        self.assertIn("simple_capability", self.tool._capabilities)

    @patch('os_araci.mcp_core.tool.logger')
    def test_register_capability_duplicate(self, mock_logger):
        """Test registering duplicate capability"""
        # Register first time
        result1 = self.tool.register_capability("duplicate_capability")
        # Try to register again
        result2 = self.tool.register_capability("duplicate_capability")
        
        self.assertTrue(result1)
        self.assertFalse(result2)
        mock_logger.warning.assert_called_with("Yetenek zaten kayıtlı: duplicate_capability, araç: test_tool")

    def test_has_capability_existing(self):
        """Test checking for existing capability"""
        self.tool.register_capability("existing_capability")
        
        result = self.tool.has_capability("existing_capability")
        
        self.assertTrue(result)

    def test_has_capability_non_existing(self):
        """Test checking for non-existing capability"""
        result = self.tool.has_capability("non_existing_capability")
        
        self.assertFalse(result)

    def test_get_capabilities(self):
        """Test getting all capabilities"""
        self.tool.register_capability("capability1")
        self.tool.register_capability("capability2")
        
        capabilities = self.tool.get_capabilities()
        
        self.assertEqual(set(capabilities), {"capability1", "capability2"})
        # Ensure it returns a copy, not the original list
        capabilities.append("new_capability")
        self.assertNotIn("new_capability", self.tool._capabilities)

    def test_get_capabilities_empty(self):
        """Test getting capabilities when none are registered"""
        capabilities = self.tool.get_capabilities()
        
        self.assertEqual(capabilities, [])

    def test_standardize_result_already_standard(self):
        """Test standardizing result that's already in standard format"""
        result = {"status": "success", "result": "data", "message": "Done"}
        
        standardized = self.tool.standardize_result(result)
        
        self.assertEqual(standardized, result)

    def test_standardize_result_simple_data(self):
        """Test standardizing simple data"""
        result = "simple string result"
        
        standardized = self.tool.standardize_result(result)
        
        expected = {
            "status": "success",
            "result": result
        }
        self.assertEqual(standardized, expected)

    def test_standardize_result_with_custom_status(self):
        """Test standardizing result with custom status"""
        result = {"data": "test"}
        
        standardized = self.tool.standardize_result(result, status="error")
        
        expected = {
            "status": "error",
            "result": result
        }
        self.assertEqual(standardized, expected)

    def test_standardize_result_with_message(self):
        """Test standardizing result with message"""
        result = [1, 2, 3]
        
        standardized = self.tool.standardize_result(result, message="List of numbers")
        
        expected = {
            "status": "success",
            "result": result,
            "message": "List of numbers"
        }
        self.assertEqual(standardized, expected)

    def test_standardize_result_with_all_parameters(self):
        """Test standardizing result with all parameters"""
        result = 42
        
        standardized = self.tool.standardize_result(result, status="warning", message="Test message")
        
        expected = {
            "status": "warning",
            "result": result,
            "message": "Test message"
        }
        self.assertEqual(standardized, expected)

    def test_execute_action_success(self):
        """Test successful action execution"""
        def test_action(param1, param2="default"):
            return f"result: {param1}, {param2}"
        
        self.tool.register_action("test_action", test_action)
        
        result = self.tool.execute_action("test_action", param1="value1", param2="value2")
        
        self.assertEqual(result, "result: value1, value2")

    def test_execute_action_with_capability_requirement(self):
        """Test action execution with capability requirement"""
        def test_action():
            return "success"
        
        self.tool.register_capability("required_capability")
        self.tool.register_action("test_action", test_action, required_capabilities=["required_capability"])
        
        result = self.tool.execute_action("test_action")
        
        self.assertEqual(result, "success")

    def test_execute_action_missing_capability(self):
        """Test action execution with missing capability"""
        def test_action():
            return "success"
        
        self.tool.register_action("test_action", test_action, required_capabilities=["missing_capability"])
        
        with self.assertRaises(ValueError) as context:
            self.tool.execute_action("test_action")
        
        self.assertIn("Aksiyon test_action için gerekli yetenek eksik: missing_capability", str(context.exception))

    def test_execute_action_non_existing(self):
        """Test execution of non-existing action"""
        with self.assertRaises(ValueError) as context:
            self.tool.execute_action("non_existing_action")
        
        self.assertIn("Aksiyon bulunamadı: non_existing_action", str(context.exception))

    def test_execute_action_with_kwargs(self):
        """Test action execution with keyword arguments"""
        def test_action(**kwargs):
            return kwargs
        
        self.tool.register_action("test_action", test_action)
        
        result = self.tool.execute_action("test_action", key1="value1", key2="value2")
        
        self.assertEqual(result, {"key1": "value1", "key2": "value2"})

    def test_get_action_existing(self):
        """Test getting existing action function"""
        def test_action():
            return "test"
        
        self.tool.register_action("test_action", test_action)
        
        retrieved_action = self.tool.get_action("test_action")
        
        self.assertEqual(retrieved_action, test_action)

    def test_get_action_non_existing(self):
        """Test getting non-existing action"""
        result = self.tool.get_action("non_existing_action")
        
        self.assertIsNone(result)

    def test_get_action_info_existing(self):
        """Test getting existing action info"""
        def test_action():
            return "test"
        
        self.tool.register_action(
            "test_action", 
            test_action, 
            params=["param1"], 
            description="Test action",
            required_capabilities=["cap1"]
        )
        
        action_info = self.tool.get_action_info("test_action")
        
        expected = {
            "params": ["param1"],
            "description": "Test action",
            "required_capabilities": ["cap1"]
        }
        self.assertEqual(action_info, expected)
        self.assertNotIn("func", action_info)

    def test_get_action_info_non_existing(self):
        """Test getting info for non-existing action"""
        result = self.tool.get_action_info("non_existing_action")
        
        self.assertIsNone(result)

    def test_get_all_actions(self):
        """Test getting all actions"""
        def action1():
            return "action1"
        
        def action2():
            return "action2"
        
        self.tool.register_action("action1", action1, params=["p1"], description="First action")
        self.tool.register_action("action2", action2, params=["p2"], description="Second action")
        
        all_actions = self.tool.get_all_actions()
        
        self.assertEqual(len(all_actions), 2)
        self.assertIn("action1", all_actions)
        self.assertIn("action2", all_actions)
        self.assertEqual(all_actions["action1"]["params"], ["p1"])
        self.assertEqual(all_actions["action2"]["description"], "Second action")
        # Ensure functions are not included
        self.assertNotIn("func", all_actions["action1"])
        self.assertNotIn("func", all_actions["action2"])

    def test_get_all_actions_empty(self):
        """Test getting all actions when none are registered"""
        all_actions = self.tool.get_all_actions()
        
        self.assertEqual(all_actions, {})

    def test_get_metadata(self):
        """Test getting tool metadata"""
        self.tool.register_capability("capability1")
        self.tool.register_capability("capability2")
        self.tool.register_action("action1", lambda: None)
        
        metadata = self.tool.get_metadata()
        
        expected = {
            "name": "test_tool",
            "description": "Test tool for unit testing",
            "version": "1.0.0",
            "category": "test",
            "capabilities": ["capability1", "capability2"],
            "actions": ["action1"]
        }
        self.assertEqual(metadata, expected)

    def test_describe(self):
        """Test tool description"""
        def test_action():
            return "test"
        
        self.tool.register_capability("test_capability")
        self.tool.register_action("test_action", test_action, description="Test action")
        
        description = self.tool.describe()
        
        self.assertIn("metadata", description)
        self.assertIn("actions", description)
        self.assertEqual(description["metadata"]["name"], "test_tool")
        self.assertIn("test_action", description["actions"])

    @patch('os_araci.mcp_core.tool.logger')
    def test_initialize(self, mock_logger):
        """Test tool initialization"""
        result = self.tool.initialize()
        
        self.assertTrue(result)
        mock_logger.info.assert_called_with("Araç başlatıldı: test_tool")

    @patch('os_araci.mcp_core.tool.logger')
    def test_shutdown(self, mock_logger):
        """Test tool shutdown"""
        result = self.tool.shutdown()
        
        self.assertTrue(result)
        mock_logger.info.assert_called_with("Araç kapatıldı: test_tool")

    def test_check_health(self):
        """Test health check"""
        health_status = self.tool.check_health()
        
        expected = {
            "status": "healthy",
            "message": "test_tool aracı çalışıyor",
            "version": "1.0.0"
        }
        self.assertEqual(health_status, expected)

    def test_repr(self):
        """Test string representation of the tool"""
        self.tool.register_capability("cap1")
        self.tool.register_action("action1", lambda: None)
        
        repr_str = repr(self.tool)
        
        self.assertIn("MCPTool", repr_str)
        self.assertIn("name=test_tool", repr_str)
        self.assertIn("version=1.0.0", repr_str)
        self.assertIn("capabilities=['cap1']", repr_str)
        self.assertIn("actions=['action1']", repr_str)

    def test_repr_empty_tool(self):
        """Test string representation of empty tool"""
        repr_str = repr(self.tool)
        
        self.assertIn("MCPTool", repr_str)
        self.assertIn("name=test_tool", repr_str)
        self.assertIn("capabilities=[]", repr_str)
        self.assertIn("actions=[]", repr_str)

    def test_complex_action_workflow(self):
        """Test complex workflow with multiple actions and capabilities"""
        # Register capabilities
        self.tool.register_capability("read")
        self.tool.register_capability("write")
        
        # Register actions with different capability requirements
        def read_action(file_name):
            return f"Reading {file_name}"
        
        def write_action(file_name, content):
            return f"Writing '{content}' to {file_name}"
        
        def admin_action():
            return "Admin operation"
        
        self.tool.register_action("read", read_action, required_capabilities=["read"])
        self.tool.register_action("write", write_action, required_capabilities=["write"])
        self.tool.register_action("admin", admin_action, required_capabilities=["admin"])
        
        # Test successful executions
        read_result = self.tool.execute_action("read", file_name="test.txt")
        write_result = self.tool.execute_action("write", file_name="output.txt", content="Hello")
        
        self.assertEqual(read_result, "Reading test.txt")
        self.assertEqual(write_result, "Writing 'Hello' to output.txt")
        
        # Test failed execution due to missing capability
        with self.assertRaises(ValueError):
            self.tool.execute_action("admin")

    def tearDown(self):
        """Clean up after each test"""
        pass


if __name__ == '__main__':
    unittest.main()