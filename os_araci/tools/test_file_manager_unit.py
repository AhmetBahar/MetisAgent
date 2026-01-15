import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import shutil
from file_manager import FileManager


class TestFileManager(unittest.TestCase):
    
    def setUp(self):
        self.file_manager = FileManager()
    
    @patch('os.listdir')
    @patch('os.path.isfile')
    def test_list_files_success(self, mock_isfile, mock_listdir):
        """Test successful file listing"""
        mock_listdir.return_value = ['file1.txt', 'file2.txt', 'folder1']
        mock_isfile.side_effect = lambda path: path.endswith('.txt')
        
        result = self.file_manager.list_files('/test/path')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['items'], ['file1.txt', 'file2.txt'])
    
    @patch('os.listdir')
    def test_list_files_error(self, mock_listdir):
        """Test file listing with error"""
        mock_listdir.side_effect = OSError("Permission denied")
        
        result = self.file_manager.list_files('/invalid/path')
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Permission denied')
    
    @patch('builtins.open', new_callable=mock_open)
    def test_create_file_success(self, mock_file):
        """Test successful file creation"""
        result = self.file_manager.create_file('/test/file.txt', 'test content')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'File created at /test/file.txt')
        mock_file.assert_called_once_with('/test/file.txt', 'w')
        mock_file().write.assert_called_once_with('test content')
    
    @patch('builtins.open', new_callable=mock_open)
    def test_create_file_error(self, mock_file):
        """Test file creation with error"""
        mock_file.side_effect = OSError("Permission denied")
        
        result = self.file_manager.create_file('/invalid/file.txt', 'content')
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Permission denied')
    
    @patch('os.remove')
    def test_delete_file_success(self, mock_remove):
        """Test successful file deletion"""
        result = self.file_manager.delete_file('/test/file.txt')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'File /test/file.txt deleted successfully')
        mock_remove.assert_called_once_with('/test/file.txt')
    
    @patch('os.remove')
    def test_delete_file_error(self, mock_remove):
        """Test file deletion with error"""
        mock_remove.side_effect = OSError("File not found")
        
        result = self.file_manager.delete_file('/invalid/file.txt')
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'File not found')
    
    @patch('os.listdir')
    @patch('os.path.isdir')
    def test_list_folders_success(self, mock_isdir, mock_listdir):
        """Test successful folder listing"""
        mock_listdir.return_value = ['file1.txt', 'folder1', 'folder2']
        mock_isdir.side_effect = lambda path: not path.endswith('.txt')
        
        result = self.file_manager.list_folders('/test/path')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['folders'], ['folder1', 'folder2'])
    
    @patch('os.makedirs')
    def test_create_folder_success(self, mock_makedirs):
        """Test successful folder creation"""
        result = self.file_manager.create_folder('/test/folder')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'Folder created at /test/folder')
        mock_makedirs.assert_called_once_with('/test/folder', exist_ok=True)
    
    @patch('shutil.rmtree')
    def test_delete_folder_success(self, mock_rmtree):
        """Test successful folder deletion"""
        result = self.file_manager.delete_folder('/test/folder')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'Folder /test/folder deleted successfully')
        mock_rmtree.assert_called_once_with('/test/folder')
    
    @patch('os.rename')
    def test_rename_folder_success(self, mock_rename):
        """Test successful folder renaming"""
        result = self.file_manager.rename_folder('/old/path', '/new/path')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'Folder renamed from /old/path to /new/path')
        mock_rename.assert_called_once_with('/old/path', '/new/path')
    
    @patch('os.chdir')
    @patch('os.getcwd')
    def test_change_directory_success(self, mock_getcwd, mock_chdir):
        """Test successful directory change"""
        mock_getcwd.return_value = '/new/directory'
        
        result = self.file_manager.change_directory('/new/directory')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['message'], 'Current directory changed to /new/directory')
        mock_chdir.assert_called_once_with('/new/directory')
    
    @patch('os.chdir')
    def test_change_directory_error(self, mock_chdir):
        """Test directory change with error"""
        mock_chdir.side_effect = OSError("Directory not found")
        
        result = self.file_manager.change_directory('/invalid/directory')
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Directory not found')


if __name__ == '__main__':
    unittest.main()