import unittest
from unittest.mock import patch, Mock, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from os_araci.tools.archive_manager import ArchiveManagerTool


class TestArchiveManagerTool(unittest.TestCase):
    """Comprehensive unit tests for ArchiveManagerTool"""

    def setUp(self):
        """Set up test fixtures"""
        self.tool = ArchiveManagerTool()

    def test_init(self):
        """Test initialization of ArchiveManagerTool"""
        self.assertEqual(self.tool.name, "archive_manager")
        self.assertEqual(self.tool.description, "Dosya arşivleme ve sıkıştırma işlemleri")
        self.assertEqual(self.tool.version, "1.0.0")
        
        # Check that actions are registered
        actions = self.tool.get_all_actions()
        self.assertIn("compress", actions)
        self.assertIn("extract", actions)
        self.assertIn("list_archive_contents", actions)

    @patch('os_araci.tools.archive_manager.shutil.make_archive')
    def test_compress_success(self, mock_make_archive):
        """Test successful compression"""
        mock_make_archive.return_value = None
        
        result = self.tool.compress(source="/test/source", destination="test.zip")
        
        self.assertEqual(result, {'message': 'Compressed /test/source into test.zip'})
        mock_make_archive.assert_called_once_with("test", 'zip', "/test/source")

    def test_compress_no_source(self):
        """Test compression with no source provided"""
        result = self.tool.compress()
        
        self.assertEqual(result, ({'error': 'Source path is required'}, 400))

    def test_compress_empty_source(self):
        """Test compression with empty source"""
        result = self.tool.compress(source="")
        
        self.assertEqual(result, ({'error': 'Source path is required'}, 400))

    def test_compress_none_source(self):
        """Test compression with None source"""
        result = self.tool.compress(source=None)
        
        self.assertEqual(result, ({'error': 'Source path is required'}, 400))

    @patch('os_araci.tools.archive_manager.shutil.make_archive')
    def test_compress_exception(self, mock_make_archive):
        """Test compression with exception"""
        mock_make_archive.side_effect = Exception("Compression failed")
        
        result = self.tool.compress(source="/test/source", destination="test.zip")
        
        self.assertEqual(result, ({'error': 'Compression failed'}, 400))

    @patch('os_araci.tools.archive_manager.shutil.make_archive')
    def test_compress_default_destination(self, mock_make_archive):
        """Test compression with default destination"""
        mock_make_archive.return_value = None
        
        result = self.tool.compress(source="/test/source")
        
        self.assertEqual(result, {'message': 'Compressed /test/source into archive.zip'})
        mock_make_archive.assert_called_once_with("archive", 'zip', "/test/source")

    @patch('os_araci.tools.archive_manager.shutil.make_archive')
    def test_compress_with_kwargs(self, mock_make_archive):
        """Test compression with additional kwargs"""
        mock_make_archive.return_value = None
        
        result = self.tool.compress(source="/test/source", destination="test.zip", extra_param="value")
        
        self.assertEqual(result, {'message': 'Compressed /test/source into test.zip'})
        mock_make_archive.assert_called_once_with("test", 'zip', "/test/source")

    @patch('os_araci.tools.archive_manager.shutil.unpack_archive')
    def test_extract_success(self, mock_unpack_archive):
        """Test successful extraction"""
        mock_unpack_archive.return_value = None
        
        result = self.tool.extract(archive_path="/test/archive.zip", extract_to="/test/output")
        
        self.assertEqual(result, {'message': 'Extracted /test/archive.zip to /test/output'})
        mock_unpack_archive.assert_called_once_with("/test/archive.zip", "/test/output")

    @patch('os_araci.tools.archive_manager.shutil.unpack_archive')
    def test_extract_default_location(self, mock_unpack_archive):
        """Test extraction with default location"""
        mock_unpack_archive.return_value = None
        
        result = self.tool.extract(archive_path="/test/archive.zip")
        
        self.assertEqual(result, {'message': 'Extracted /test/archive.zip to .'})
        mock_unpack_archive.assert_called_once_with("/test/archive.zip", ".")

    def test_extract_no_archive_path(self):
        """Test extraction with no archive path"""
        result = self.tool.extract()
        
        self.assertEqual(result, ({'error': 'Archive path is required'}, 400))

    def test_extract_empty_archive_path(self):
        """Test extraction with empty archive path"""
        result = self.tool.extract(archive_path="")
        
        self.assertEqual(result, ({'error': 'Archive path is required'}, 400))

    def test_extract_none_archive_path(self):
        """Test extraction with None archive path"""
        result = self.tool.extract(archive_path=None)
        
        self.assertEqual(result, ({'error': 'Archive path is required'}, 400))

    @patch('os_araci.tools.archive_manager.shutil.unpack_archive')
    def test_extract_exception(self, mock_unpack_archive):
        """Test extraction with exception"""
        mock_unpack_archive.side_effect = Exception("Extraction failed")
        
        result = self.tool.extract(archive_path="/test/archive.zip", extract_to="/test/output")
        
        self.assertEqual(result, ({'error': 'Extraction failed'}, 400))

    @patch('os_araci.tools.archive_manager.shutil.unpack_archive')
    def test_extract_with_kwargs(self, mock_unpack_archive):
        """Test extraction with additional kwargs"""
        mock_unpack_archive.return_value = None
        
        result = self.tool.extract(archive_path="/test/archive.zip", extract_to="/test/output", extra_param="value")
        
        self.assertEqual(result, {'message': 'Extracted /test/archive.zip to /test/output'})
        mock_unpack_archive.assert_called_once_with("/test/archive.zip", "/test/output")

    @patch('os_araci.tools.archive_manager.shutil.ZipFile')
    def test_list_archive_contents_success(self, mock_zipfile):
        """Test successful archive contents listing"""
        mock_archive = MagicMock()
        mock_archive.namelist.return_value = ["file1.txt", "file2.txt", "folder/file3.txt"]
        mock_zipfile.return_value.__enter__.return_value = mock_archive
        
        result = self.tool.list_archive_contents(archive_path="/test/archive.zip")
        
        expected_files = ["file1.txt", "file2.txt", "folder/file3.txt"]
        self.assertEqual(result, {'files': expected_files})
        mock_zipfile.assert_called_once_with("/test/archive.zip", 'r')

    def test_list_archive_contents_no_path(self):
        """Test listing archive contents with no path"""
        result = self.tool.list_archive_contents()
        
        self.assertEqual(result, ({'error': 'Archive path is required'}, 400))

    def test_list_archive_contents_empty_path(self):
        """Test listing archive contents with empty path"""
        result = self.tool.list_archive_contents(archive_path="")
        
        self.assertEqual(result, ({'error': 'Archive path is required'}, 400))

    def test_list_archive_contents_none_path(self):
        """Test listing archive contents with None path"""
        result = self.tool.list_archive_contents(archive_path=None)
        
        self.assertEqual(result, ({'error': 'Archive path is required'}, 400))

    @patch('os_araci.tools.archive_manager.shutil.ZipFile')
    def test_list_archive_contents_exception(self, mock_zipfile):
        """Test listing archive contents with exception"""
        mock_zipfile.side_effect = Exception("Cannot read archive")
        
        result = self.tool.list_archive_contents(archive_path="/test/archive.zip")
        
        self.assertEqual(result, ({'error': 'Cannot read archive'}, 400))

    @patch('os_araci.tools.archive_manager.shutil.ZipFile')
    def test_list_archive_contents_empty_archive(self, mock_zipfile):
        """Test listing empty archive contents"""
        mock_archive = MagicMock()
        mock_archive.namelist.return_value = []
        mock_zipfile.return_value.__enter__.return_value = mock_archive
        
        result = self.tool.list_archive_contents(archive_path="/test/empty.zip")
        
        self.assertEqual(result, {'files': []})

    @patch('os_araci.tools.archive_manager.shutil.ZipFile')
    def test_list_archive_contents_with_kwargs(self, mock_zipfile):
        """Test listing archive contents with additional kwargs"""
        mock_archive = MagicMock()
        mock_archive.namelist.return_value = ["file1.txt"]
        mock_zipfile.return_value.__enter__.return_value = mock_archive
        
        result = self.tool.list_archive_contents(archive_path="/test/archive.zip", extra_param="value")
        
        self.assertEqual(result, {'files': ["file1.txt"]})
        mock_zipfile.assert_called_once_with("/test/archive.zip", 'r')

    def test_action_execution(self):
        """Test action execution through the tool interface"""
        with patch('os_araci.tools.archive_manager.shutil.make_archive') as mock_make_archive:
            mock_make_archive.return_value = None
            
            result = self.tool.execute_action("compress", source="/test/source", destination="test.zip")
            
            self.assertEqual(result, {'message': 'Compressed /test/source into test.zip'})

    def test_invalid_action_execution(self):
        """Test execution of non-existent action"""
        with self.assertRaises(ValueError) as context:
            self.tool.execute_action("invalid_action", param="value")
        
        self.assertIn("Aksiyon bulunamadı: invalid_action", str(context.exception))

    def tearDown(self):
        """Clean up after each test"""
        pass


if __name__ == '__main__':
    unittest.main()