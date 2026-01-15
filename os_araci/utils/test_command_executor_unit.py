import unittest
from unittest.mock import patch, MagicMock
import platform
from command_executor import execute_command


class TestCommandExecutor(unittest.TestCase):
    
    @patch('platform.system')
    @patch('subprocess.run')
    def test_execute_command_windows_success(self, mock_run, mock_system):
        """Test successful command execution on Windows"""
        mock_system.return_value = "Windows"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Command output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = execute_command("dir")
        
        self.assertEqual(result, "Command output")
        mock_run.assert_called_once_with("dir", shell=True, capture_output=True, text=True)
    
    @patch('platform.system')
    @patch('subprocess.run')
    def test_execute_command_linux_success(self, mock_run, mock_system):
        """Test successful command execution on Linux"""
        mock_system.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Command output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = execute_command("ls")
        
        self.assertEqual(result, "Command output")
        mock_run.assert_called_once_with("bash -c 'ls'", shell=True, capture_output=True, text=True)
    
    @patch('platform.system')
    @patch('subprocess.run')
    def test_execute_command_error(self, mock_run, mock_system):
        """Test command execution with error"""
        mock_system.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command not found"
        mock_run.return_value = mock_result
        
        result = execute_command("invalid_command")
        
        self.assertEqual(result, "Command not found")
    
    @patch('platform.system')
    @patch('subprocess.run')
    def test_execute_command_exception(self, mock_run, mock_system):
        """Test command execution with exception"""
        mock_system.return_value = "Linux"
        mock_run.side_effect = Exception("Subprocess error")
        
        result = execute_command("test_command")
        
        self.assertEqual(result, "Hata: Subprocess error")


if __name__ == '__main__':
    unittest.main()