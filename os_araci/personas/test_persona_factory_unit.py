import unittest
from unittest.mock import patch, Mock, MagicMock, mock_open
import sys
import os
import json
import tempfile

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from os_araci.personas.persona_factory import PersonaFactory


# Mock PersonaAgent class for testing
class MockPersonaAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockValidPersona(MockPersonaAgent):
    pass


class MockInvalidPersona:
    pass


class TestPersonaFactory(unittest.TestCase):
    """Comprehensive unit tests for PersonaFactory"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset the singleton instance for each test
        PersonaFactory._instance = None

    def tearDown(self):
        """Clean up after each test"""
        # Reset the singleton instance
        PersonaFactory._instance = None

    @patch('os_araci.personas.persona_factory.logger')
    def test_singleton_pattern(self, mock_logger):
        """Test that PersonaFactory follows singleton pattern"""
        factory1 = PersonaFactory()
        factory2 = PersonaFactory()
        
        self.assertIs(factory1, factory2)
        mock_logger.info.assert_called_once_with("PersonaFactory başlatılıyor...")

    @patch('os_araci.personas.persona_factory.logger')
    def test_init(self, mock_logger):
        """Test factory initialization"""
        factory = PersonaFactory()
        
        self.assertEqual(factory._persona_templates, {})
        self.assertEqual(factory._persona_classes, {})
        mock_logger.info.assert_called_with("PersonaFactory başlatılıyor...")

    @patch('os_araci.personas.persona_factory.logger')
    @patch('os_araci.personas.persona_factory.issubclass')
    def test_register_persona_class_success(self, mock_issubclass, mock_logger):
        """Test successful persona class registration"""
        mock_issubclass.return_value = True
        
        factory = PersonaFactory()
        result = factory.register_persona_class("TestPersona", MockValidPersona)
        
        self.assertTrue(result)
        self.assertIn("TestPersona", factory._persona_classes)
        self.assertEqual(factory._persona_classes["TestPersona"], MockValidPersona)
        mock_logger.info.assert_any_call("Persona sınıfı kaydedildi: TestPersona")

    @patch('os_araci.personas.persona_factory.logger')
    @patch('os_araci.personas.persona_factory.issubclass')
    def test_register_persona_class_duplicate(self, mock_issubclass, mock_logger):
        """Test registering duplicate persona class"""
        mock_issubclass.return_value = True
        
        factory = PersonaFactory()
        # Register first time
        result1 = factory.register_persona_class("TestPersona", MockValidPersona)
        # Try to register again
        result2 = factory.register_persona_class("TestPersona", MockValidPersona)
        
        self.assertTrue(result1)
        self.assertFalse(result2)
        mock_logger.warning.assert_called_with("Persona sınıfı zaten kayıtlı: TestPersona")

    @patch('os_araci.personas.persona_factory.logger')
    @patch('os_araci.personas.persona_factory.issubclass')
    def test_register_persona_class_invalid(self, mock_issubclass, mock_logger):
        """Test registering invalid persona class"""
        mock_issubclass.return_value = False
        
        factory = PersonaFactory()
        result = factory.register_persona_class("InvalidPersona", MockInvalidPersona)
        
        self.assertFalse(result)
        mock_logger.error.assert_called_with("Geçersiz persona sınıfı, PersonaAgent'tan türemeli: InvalidPersona")

    @patch('os_araci.personas.persona_factory.logger')
    @patch('os_araci.personas.persona_factory.issubclass')
    def test_register_template_success(self, mock_issubclass, mock_logger):
        """Test successful template registration"""
        mock_issubclass.return_value = True
        
        factory = PersonaFactory()
        factory.register_persona_class("TestPersona", MockValidPersona)
        
        template = {
            "persona_id": "test_persona",
            "name": "Test Persona",
            "class_name": "TestPersona",
            "description": "Test description"
        }
        
        result = factory.register_template("test_template", template)
        
        self.assertTrue(result)
        self.assertIn("test_template", factory._persona_templates)
        mock_logger.info.assert_any_call("Persona şablonu kaydedildi: test_template")

    @patch('os_araci.personas.persona_factory.logger')
    def test_register_template_duplicate(self, mock_logger):
        """Test registering duplicate template"""
        factory = PersonaFactory()
        
        template = {
            "persona_id": "test_persona",
            "name": "Test Persona",
            "class_name": "TestPersona"
        }
        
        # Register first time
        result1 = factory.register_template("test_template", template)
        # Try to register again
        result2 = factory.register_template("test_template", template)
        
        self.assertFalse(result1)  # Will fail due to missing class
        self.assertFalse(result2)
        mock_logger.warning.assert_called_with("Persona şablonu zaten kayıtlı: test_template")

    @patch('os_araci.personas.persona_factory.logger')
    def test_register_template_missing_required_fields(self, mock_logger):
        """Test registering template with missing required fields"""
        factory = PersonaFactory()
        
        # Missing persona_id
        template1 = {
            "name": "Test Persona",
            "class_name": "TestPersona"
        }
        result1 = factory.register_template("incomplete1", template1)
        
        # Missing name
        template2 = {
            "persona_id": "test_persona",
            "class_name": "TestPersona"
        }
        result2 = factory.register_template("incomplete2", template2)
        
        # Missing class_name
        template3 = {
            "persona_id": "test_persona",
            "name": "Test Persona"
        }
        result3 = factory.register_template("incomplete3", template3)
        
        self.assertFalse(result1)
        self.assertFalse(result2)
        self.assertFalse(result3)

    @patch('os_araci.personas.persona_factory.logger')
    def test_register_template_class_not_found(self, mock_logger):
        """Test registering template with non-existent class"""
        factory = PersonaFactory()
        
        template = {
            "persona_id": "test_persona",
            "name": "Test Persona",
            "class_name": "NonExistentClass"
        }
        
        result = factory.register_template("test_template", template)
        
        self.assertFalse(result)
        mock_logger.error.assert_called_with("Persona şablonu için sınıf bulunamadı: NonExistentClass")

    @patch('os_araci.personas.persona_factory.logger')
    @patch('os_araci.personas.persona_factory.issubclass')
    def test_create_persona_success(self, mock_issubclass, mock_logger):
        """Test successful persona creation"""
        mock_issubclass.return_value = True
        
        factory = PersonaFactory()
        factory.register_persona_class("TestPersona", MockValidPersona)
        
        template = {
            "persona_id": "test_persona",
            "name": "Test Persona",
            "class_name": "TestPersona",
            "description": "Test description"
        }
        factory.register_template("test_template", template)
        
        persona = factory.create_persona("test_template", extra_param="value")
        
        self.assertIsNotNone(persona)
        self.assertIsInstance(persona, MockValidPersona)
        self.assertEqual(persona.persona_id, "test_persona")
        self.assertEqual(persona.name, "Test Persona")
        self.assertEqual(persona.extra_param, "value")

    @patch('os_araci.personas.persona_factory.logger')
    def test_create_persona_template_not_found(self, mock_logger):
        """Test persona creation with non-existent template"""
        factory = PersonaFactory()
        
        persona = factory.create_persona("non_existent_template")
        
        self.assertIsNone(persona)
        mock_logger.error.assert_called_with("Persona şablonu bulunamadı: non_existent_template")

    @patch('os_araci.personas.persona_factory.logger')
    @patch('os_araci.personas.persona_factory.issubclass')
    def test_create_persona_class_not_found(self, mock_issubclass, mock_logger):
        """Test persona creation when class is not found"""
        mock_issubclass.return_value = True
        
        factory = PersonaFactory()
        
        template = {
            "persona_id": "test_persona",
            "name": "Test Persona",
            "class_name": "NonExistentClass"
        }
        factory._persona_templates["test_template"] = template
        
        persona = factory.create_persona("test_template")
        
        self.assertIsNone(persona)
        mock_logger.error.assert_called_with("Persona sınıfı bulunamadı: NonExistentClass")

    @patch('os_araci.personas.persona_factory.logger')
    @patch('os_araci.personas.persona_factory.issubclass')
    def test_create_persona_exception(self, mock_issubclass, mock_logger):
        """Test persona creation with exception"""
        mock_issubclass.return_value = True
        
        # Mock class that raises exception on instantiation
        class FailingPersona(MockPersonaAgent):
            def __init__(self, **kwargs):
                raise ValueError("Instantiation failed")
        
        factory = PersonaFactory()
        factory.register_persona_class("FailingPersona", FailingPersona)
        
        template = {
            "persona_id": "test_persona",
            "name": "Test Persona",
            "class_name": "FailingPersona"
        }
        factory.register_template("failing_template", template)
        
        persona = factory.create_persona("failing_template")
        
        self.assertIsNone(persona)
        mock_logger.error.assert_called_with("Persona oluşturma hatası: Instantiation failed")

    @patch('os_araci.personas.persona_factory.os.path.exists')
    @patch('os_araci.personas.persona_factory.os.path.isdir')
    @patch('os_araci.personas.persona_factory.logger')
    def test_load_templates_from_directory_not_exists(self, mock_logger, mock_isdir, mock_exists):
        """Test loading templates from non-existent directory"""
        mock_exists.return_value = False
        mock_isdir.return_value = False
        
        factory = PersonaFactory()
        count = factory.load_templates_from_directory("/non/existent/path")
        
        self.assertEqual(count, 0)
        mock_logger.error.assert_called_with("Dizin bulunamadı: /non/existent/path")

    @patch('os_araci.personas.persona_factory.os.path.exists')
    @patch('os_araci.personas.persona_factory.os.path.isdir')
    @patch('os_araci.personas.persona_factory.os.listdir')
    @patch('os_araci.personas.persona_factory.logger')
    @patch('os_araci.personas.persona_factory.issubclass')
    def test_load_templates_from_directory_success(self, mock_issubclass, mock_logger, mock_listdir, mock_isdir, mock_exists):
        """Test successful template loading from directory"""
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_listdir.return_value = ["template1.json", "template2.json", "not_json.txt"]
        mock_issubclass.return_value = True
        
        template_data = {
            "persona_id": "test_persona",
            "name": "Test Persona",
            "class_name": "TestPersona"
        }
        
        factory = PersonaFactory()
        factory.register_persona_class("TestPersona", MockValidPersona)
        
        with patch('builtins.open', mock_open(read_data=json.dumps(template_data))):
            count = factory.load_templates_from_directory("/test/directory")
        
        self.assertEqual(count, 2)  # 2 JSON files
        mock_logger.info.assert_any_call("2 adet persona şablonu yüklendi: /test/directory")

    @patch('os_araci.personas.persona_factory.os.path.exists')
    @patch('os_araci.personas.persona_factory.os.path.isdir')
    @patch('os_araci.personas.persona_factory.os.listdir')
    @patch('os_araci.personas.persona_factory.logger')
    def test_load_templates_from_directory_invalid_json(self, mock_logger, mock_listdir, mock_isdir, mock_exists):
        """Test template loading with invalid JSON"""
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_listdir.return_value = ["invalid.json"]
        
        factory = PersonaFactory()
        
        with patch('builtins.open', mock_open(read_data="invalid json")):
            count = factory.load_templates_from_directory("/test/directory")
        
        self.assertEqual(count, 0)
        mock_logger.error.assert_called()

    @patch('os_araci.personas.persona_factory.importlib.import_module')
    @patch('os_araci.personas.persona_factory.pkgutil.iter_modules')
    @patch('os_araci.personas.persona_factory.inspect.getmembers')
    @patch('os_araci.personas.persona_factory.inspect.isclass')
    @patch('os_araci.personas.persona_factory.issubclass')
    @patch('os_araci.personas.persona_factory.logger')
    def test_discover_persona_classes_success(self, mock_logger, mock_issubclass, mock_isclass, mock_getmembers, mock_iter_modules, mock_import_module):
        """Test successful persona class discovery"""
        # Mock package structure
        mock_package = MagicMock()
        mock_package.__path__ = ["/test/path"]
        mock_import_module.return_value = mock_package
        
        # Mock module iteration
        mock_iter_modules.return_value = [
            (None, "personas.test_persona", False),
            (None, "personas.another_persona", False)
        ]
        
        # Mock module with persona class
        mock_module = MagicMock()
        mock_module.__name__ = "personas.test_persona"
        mock_import_module.side_effect = [mock_package, mock_module, mock_module]
        
        # Mock class inspection
        mock_getmembers.return_value = [
            ("TestPersona", MockValidPersona),
            ("NotPersona", str)
        ]
        mock_isclass.side_effect = [True, True]
        mock_issubclass.side_effect = [True, False]  # Only first class is PersonaAgent subclass
        
        factory = PersonaFactory()
        count = factory.discover_persona_classes("personas")
        
        self.assertEqual(count, 2)  # 2 modules processed, but only 1 valid persona class per module
        mock_logger.info.assert_any_call("2 adet persona sınıfı keşfedildi: personas")

    @patch('os_araci.personas.persona_factory.importlib.import_module')
    @patch('os_araci.personas.persona_factory.logger')
    def test_discover_persona_classes_import_error(self, mock_logger, mock_import_module):
        """Test persona class discovery with import error"""
        mock_import_module.side_effect = ImportError("Package not found")
        
        factory = PersonaFactory()
        count = factory.discover_persona_classes("non_existent_package")
        
        self.assertEqual(count, 0)
        mock_logger.error.assert_called_with("Paket yüklenemedi: non_existent_package, Package not found")

    @patch('os_araci.personas.persona_factory.logger')
    @patch('os_araci.personas.persona_factory.issubclass')
    def test_list_available_templates(self, mock_issubclass, mock_logger):
        """Test listing available templates"""
        mock_issubclass.return_value = True
        
        factory = PersonaFactory()
        factory.register_persona_class("TestPersona", MockValidPersona)
        
        template1 = {
            "persona_id": "persona1",
            "name": "Persona 1",
            "description": "First persona",
            "class_name": "TestPersona",
            "capabilities": ["cap1", "cap2"]
        }
        
        template2 = {
            "persona_id": "persona2",
            "name": "Persona 2",
            "description": "Second persona",
            "class_name": "TestPersona",
            "capabilities": ["cap3"]
        }
        
        factory.register_template("template1", template1)
        factory.register_template("template2", template2)
        
        templates = factory.list_available_templates()
        
        self.assertEqual(len(templates), 2)
        self.assertEqual(templates[0]["template_id"], "template1")
        self.assertEqual(templates[0]["name"], "Persona 1")
        self.assertEqual(templates[1]["template_id"], "template2")
        self.assertEqual(templates[1]["capabilities"], ["cap3"])

    @patch('os_araci.personas.persona_factory.issubclass')
    def test_list_available_classes(self, mock_issubclass):
        """Test listing available persona classes"""
        mock_issubclass.return_value = True
        
        factory = PersonaFactory()
        factory.register_persona_class("TestPersona1", MockValidPersona)
        factory.register_persona_class("TestPersona2", MockValidPersona)
        
        classes = factory.list_available_classes()
        
        self.assertEqual(len(classes), 2)
        self.assertIn("TestPersona1", classes)
        self.assertIn("TestPersona2", classes)

    @patch('os_araci.personas.persona_factory.issubclass')
    def test_get_template(self, mock_issubclass):
        """Test getting specific template"""
        mock_issubclass.return_value = True
        
        factory = PersonaFactory()
        factory.register_persona_class("TestPersona", MockValidPersona)
        
        template = {
            "persona_id": "test_persona",
            "name": "Test Persona",
            "class_name": "TestPersona"
        }
        factory.register_template("test_template", template)
        
        retrieved_template = factory.get_template("test_template")
        non_existent_template = factory.get_template("non_existent")
        
        self.assertEqual(retrieved_template, template)
        self.assertIsNone(non_existent_template)

    @patch('os_araci.personas.persona_factory.importlib.import_module')
    @patch('os_araci.personas.persona_factory.logger')
    def test_auto_discover_and_register_with_function(self, mock_logger, mock_import_module):
        """Test auto discovery when package has register_all_personas function"""
        mock_package = MagicMock()
        mock_package.register_all_personas.return_value = 5
        mock_import_module.return_value = mock_package
        
        factory = PersonaFactory()
        count = factory.auto_discover_and_register("test_package")
        
        self.assertEqual(count, 5)
        mock_package.register_all_personas.assert_called_with(factory)
        mock_logger.info.assert_called_with("5 persona sınıfı otomatik kaydedildi")

    @patch('os_araci.personas.persona_factory.importlib.import_module')
    @patch('os_araci.personas.persona_factory.logger')
    def test_auto_discover_and_register_fallback(self, mock_logger, mock_import_module):
        """Test auto discovery fallback to old method"""
        mock_package = MagicMock()
        # Package doesn't have register_all_personas function
        del mock_package.register_all_personas
        mock_import_module.return_value = mock_package
        
        factory = PersonaFactory()
        # Mock the discover_persona_classes method
        factory.discover_persona_classes = MagicMock(return_value=3)
        
        count = factory.auto_discover_and_register("test_package")
        
        self.assertEqual(count, 3)
        factory.discover_persona_classes.assert_called_with("test_package")

    @patch('os_araci.personas.persona_factory.importlib.import_module')
    @patch('os_araci.personas.persona_factory.logger')
    def test_auto_discover_and_register_import_error(self, mock_logger, mock_import_module):
        """Test auto discovery with import error"""
        mock_import_module.side_effect = ImportError("Package not found")
        
        factory = PersonaFactory()
        count = factory.auto_discover_and_register("non_existent_package")
        
        self.assertEqual(count, 0)
        mock_logger.error.assert_called_with("Persona paketi yüklenemedi: non_existent_package, Package not found")

    def test_complex_workflow(self):
        """Test complex workflow with multiple operations"""
        with patch('os_araci.personas.persona_factory.issubclass', return_value=True), \
             patch('os_araci.personas.persona_factory.logger'):
            
            factory = PersonaFactory()
            
            # Register persona classes
            factory.register_persona_class("PersonaA", MockValidPersona)
            factory.register_persona_class("PersonaB", MockValidPersona)
            
            # Register templates
            template_a = {
                "persona_id": "persona_a",
                "name": "Persona A",
                "class_name": "PersonaA",
                "description": "First persona",
                "capabilities": ["cap1"]
            }
            
            template_b = {
                "persona_id": "persona_b",
                "name": "Persona B",
                "class_name": "PersonaB",
                "description": "Second persona",
                "capabilities": ["cap2"]
            }
            
            factory.register_template("template_a", template_a)
            factory.register_template("template_b", template_b)
            
            # List templates and classes
            templates = factory.list_available_templates()
            classes = factory.list_available_classes()
            
            self.assertEqual(len(templates), 2)
            self.assertEqual(len(classes), 2)
            
            # Create personas
            persona_a = factory.create_persona("template_a", extra_param="value_a")
            persona_b = factory.create_persona("template_b", extra_param="value_b")
            
            self.assertIsNotNone(persona_a)
            self.assertIsNotNone(persona_b)
            self.assertEqual(persona_a.persona_id, "persona_a")
            self.assertEqual(persona_b.persona_id, "persona_b")
            self.assertEqual(persona_a.extra_param, "value_a")
            self.assertEqual(persona_b.extra_param, "value_b")


if __name__ == '__main__':
    unittest.main()