import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import os
from in_memory_editor import InMemoryEditor


class TestInMemoryEditor(unittest.TestCase):
    
    def setUp(self):
        self.editor = InMemoryEditor()
    
    def test_create_file_success(self):
        """Test successful file creation"""
        result = self.editor.create_file("test.txt")
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'File test.txt created')
        self.assertIn('test.txt', self.editor.files)
        self.assertEqual(self.editor.files['test.txt'], [])
    
    def test_create_file_already_exists(self):
        """Test creating file that already exists"""
        self.editor.create_file("test.txt")
        result = self.editor.create_file("test.txt")
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'File test.txt already exists')
    
    def test_write_file_success(self):
        """Test successful file writing"""
        self.editor.create_file("test.txt")
        result = self.editor.write_file("test.txt", "Hello\nWorld")
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'Content written to test.txt')
        self.assertEqual(self.editor.files['test.txt'], ['Hello', 'World'])
    
    def test_write_file_not_exists(self):
        """Test writing to non-existent file"""
        result = self.editor.write_file("nonexistent.txt", "content")
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'File nonexistent.txt does not exist')
    
    def test_go_to_line_success(self):
        """Test successful line retrieval"""
        self.editor.create_file("test.txt")
        self.editor.write_file("test.txt", "Line 1\nLine 2\nLine 3")
        result = self.editor.go_to_line("test.txt", 2)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['line_content'], 'Line 2')
    
    def test_go_to_line_out_of_range(self):
        """Test line retrieval out of range"""
        self.editor.create_file("test.txt")
        self.editor.write_file("test.txt", "Line 1")
        result = self.editor.go_to_line("test.txt", 5)
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Line number out of range')
    
    def test_find_success(self):
        """Test successful text search"""
        self.editor.create_file("test.txt")
        self.editor.write_file("test.txt", "Hello World\nHello Universe\nGoodbye World")
        result = self.editor.find("test.txt", "Hello")
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['matches'], [1, 2])
    
    def test_find_and_replace_success(self):
        """Test successful find and replace"""
        self.editor.create_file("test.txt")
        self.editor.write_file("test.txt", "Hello World\nHello Universe")
        result = self.editor.find_and_replace("test.txt", "Hello", "Hi")
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], "Replaced all occurrences of 'Hello' with 'Hi'")
        self.assertEqual(self.editor.files['test.txt'], ['Hi World', 'Hi Universe'])
    
    def test_select_lines_success(self):
        """Test successful line selection"""
        self.editor.create_file("test.txt")
        self.editor.write_file("test.txt", "Line 1\nLine 2\nLine 3\nLine 4")
        result = self.editor.select_lines("test.txt", 2, 3)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['selected_lines'], ['Line 2', 'Line 3'])
    
    def test_select_lines_out_of_bounds(self):
        """Test line selection out of bounds"""
        self.editor.create_file("test.txt")
        self.editor.write_file("test.txt", "Line 1")
        result = self.editor.select_lines("test.txt", 1, 5)
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Line range out of bounds')
    
    def test_list_files(self):
        """Test file listing"""
        self.editor.create_file("file1.txt")
        self.editor.create_file("file2.txt")
        result = self.editor.list_files()
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('file1.txt', result['files'])
        self.assertIn('file2.txt', result['files'])
    
    @patch('builtins.open', new_callable=mock_open)
    def test_save_to_disk_success(self, mock_file):
        """Test successful disk save"""
        self.editor.create_file("test.txt")
        self.editor.write_file("test.txt", "Hello\nWorld")
        result = self.editor.save_to_disk("test.txt", "/path/to/file.txt")
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'File test.txt saved to disk at /path/to/file.txt')
        mock_file.assert_called_once_with('/path/to/file.txt', 'w')
        mock_file().write.assert_called_once_with('Hello\nWorld')
    
    def test_save_to_disk_file_not_exists(self):
        """Test saving non-existent file to disk"""
        result = self.editor.save_to_disk("nonexistent.txt", "/path/to/file.txt")
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'File nonexistent.txt does not exist in memory')
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="Hello\nWorld")
    def test_load_from_disk_success(self, mock_file, mock_exists):
        """Test successful disk load"""
        mock_exists.return_value = True
        result = self.editor.load_from_disk("test.txt", "/path/to/file.txt")
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'File /path/to/file.txt loaded into memory as test.txt')
        self.assertEqual(self.editor.files['test.txt'], ['Hello', 'World'])
    
    @patch('os.path.exists')
    def test_load_from_disk_file_not_exists(self, mock_exists):
        """Test loading non-existent disk file"""
        mock_exists.return_value = False
        result = self.editor.load_from_disk("test.txt", "/path/to/nonexistent.txt")
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'File /path/to/nonexistent.txt does not exist on disk')
    
    def test_initialize_change_templates(self):
        """Test template system initialization"""
        result = self.editor.initialize_change_templates()
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'Change templates system initialized')
        self.assertIn('.change_templates.json', self.editor.files)
        
        # Verify JSON content
        content = '\n'.join(self.editor.files['.change_templates.json'])
        templates = json.loads(content)
        self.assertEqual(templates, {})
    
    def test_save_change_template(self):
        """Test saving change template"""
        template = {"type": "replace", "content": "new content"}
        result = self.editor.save_change_template("test_template", template)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], "Change template 'test_template' saved")
        
        # Verify template was saved
        content = '\n'.join(self.editor.files['.change_templates.json'])
        templates = json.loads(content)
        self.assertEqual(templates['test_template'], template)
    
    def test_get_change_template_success(self):
        """Test retrieving change template"""
        template = {"type": "replace", "content": "new content"}
        self.editor.save_change_template("test_template", template)
        result = self.editor.get_change_template("test_template")
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['template'], template)
    
    def test_get_change_template_not_found(self):
        """Test retrieving non-existent template"""
        self.editor.initialize_change_templates()
        result = self.editor.get_change_template("nonexistent")
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], "Change template 'nonexistent' not found")
    
    def test_list_change_templates(self):
        """Test listing change templates"""
        self.editor.save_change_template("template1", {"type": "replace"})
        self.editor.save_change_template("template2", {"type": "insert"})
        result = self.editor.list_change_templates()
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('template1', result['templates'])
        self.assertIn('template2', result['templates'])
    
    def test_delete_change_template_success(self):
        """Test deleting change template"""
        self.editor.save_change_template("test_template", {"type": "replace"})
        result = self.editor.delete_change_template("test_template")
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], "Change template 'test_template' deleted")
        
        # Verify template was deleted
        content = '\n'.join(self.editor.files['.change_templates.json'])
        templates = json.loads(content)
        self.assertNotIn('test_template', templates)
    
    def test_delete_change_template_not_found(self):
        """Test deleting non-existent template"""
        self.editor.initialize_change_templates()
        result = self.editor.delete_change_template("nonexistent")
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], "Change template 'nonexistent' not found")
    
    def test_apply_llm_change_replace(self):
        """Test applying replace change"""
        self.editor.create_file("test.txt")
        self.editor.write_file("test.txt", "Line 1\nLine 2\nLine 3\nLine 4")
        
        change_template = {
            "type": "replace",
            "start_line": 2,
            "end_line": 3,
            "content": "New Line 2\nNew Line 3"
        }
        
        result = self.editor.apply_llm_change("test.txt", change_template)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'Replaced lines 2-3 with new content')
        expected_content = ['Line 1', 'New Line 2', 'New Line 3', 'Line 4']
        self.assertEqual(self.editor.files['test.txt'], expected_content)
    
    def test_apply_llm_change_insert(self):
        """Test applying insert change"""
        self.editor.create_file("test.txt")
        self.editor.write_file("test.txt", "Line 1\nLine 3")
        
        change_template = {
            "type": "insert",
            "start_line": 2,
            "content": "Line 2"
        }
        
        result = self.editor.apply_llm_change("test.txt", change_template)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'Inserted content before line 2')
        expected_content = ['Line 1', 'Line 2', 'Line 3']
        self.assertEqual(self.editor.files['test.txt'], expected_content)
    
    def test_apply_llm_change_delete(self):
        """Test applying delete change"""
        self.editor.create_file("test.txt")
        self.editor.write_file("test.txt", "Line 1\nLine 2\nLine 3\nLine 4")
        
        change_template = {
            "type": "delete",
            "start_line": 2,
            "end_line": 3
        }
        
        result = self.editor.apply_llm_change("test.txt", change_template)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'Deleted lines 2-3')
        expected_content = ['Line 1', 'Line 4']
        self.assertEqual(self.editor.files['test.txt'], expected_content)
    
    def test_apply_llm_change_unknown_type(self):
        """Test applying unknown change type"""
        self.editor.create_file("test.txt")
        change_template = {"type": "unknown"}
        
        result = self.editor.apply_llm_change("test.txt", change_template)
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Unknown change type: unknown')


if __name__ == '__main__':
    unittest.main()