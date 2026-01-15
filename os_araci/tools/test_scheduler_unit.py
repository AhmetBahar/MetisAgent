import unittest
from unittest.mock import patch, Mock, MagicMock
import sys
import os
import subprocess

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from os_araci.tools.scheduler import SchedulerTool


class TestSchedulerTool(unittest.TestCase):
    """Comprehensive unit tests for SchedulerTool"""

    def setUp(self):
        """Set up test fixtures"""
        self.tool = SchedulerTool()

    def test_init(self):
        """Test initialization of SchedulerTool"""
        self.assertEqual(self.tool.name, "scheduler")
        self.assertEqual(self.tool.description, "Zamanlamalı yürütme işlemleri")
        self.assertEqual(self.tool.version, "1.0.0")
        
        # Check that actions are registered
        actions = self.tool.get_all_actions()
        self.assertIn("schedule_task", actions)
        self.assertIn("list_scheduled_tasks", actions)
        self.assertIn("cancel_task", actions)
        self.assertIn("schedule_recurring_task", actions)
        self.assertIn("task_status", actions)

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_schedule_task_success_windows(self, mock_platform, mock_subprocess):
        """Test successful task scheduling on Windows"""
        mock_platform.return_value = "Windows"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = self.tool.schedule_task(command="notepad.exe", time="14:30")
        
        self.assertEqual(result['message'], 'Task scheduled: notepad.exe at 14:30')
        expected_command = 'schtasks /create /tn "ScheduledTask" /tr "notepad.exe" /sc once /st 14:30'
        mock_subprocess.assert_called_once_with(expected_command, shell=True, capture_output=True, text=True)

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_schedule_task_success_linux(self, mock_platform, mock_subprocess):
        """Test successful task scheduling on Linux"""
        mock_platform.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = self.tool.schedule_task(command="ls /", time="14:30")
        
        self.assertEqual(result['message'], 'Task scheduled: ls / at 14:30')
        expected_command = '(echo "14:30 ls /") | at'
        mock_subprocess.assert_called_once_with(expected_command, shell=True, capture_output=True, text=True)

    def test_schedule_task_no_command(self):
        """Test task scheduling with no command"""
        result = self.tool.schedule_task(time="14:30")
        
        self.assertEqual(result, ({'error': 'Command and time are required'}, 400))

    def test_schedule_task_no_time(self):
        """Test task scheduling with no time"""
        result = self.tool.schedule_task(command="ls /")
        
        self.assertEqual(result, ({'error': 'Command and time are required'}, 400))

    def test_schedule_task_empty_command(self):
        """Test task scheduling with empty command"""
        result = self.tool.schedule_task(command="", time="14:30")
        
        self.assertEqual(result, ({'error': 'Command and time are required'}, 400))

    def test_schedule_task_empty_time(self):
        """Test task scheduling with empty time"""
        result = self.tool.schedule_task(command="ls /", time="")
        
        self.assertEqual(result, ({'error': 'Command and time are required'}, 400))

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_schedule_task_failure(self, mock_platform, mock_subprocess):
        """Test task scheduling failure"""
        mock_platform.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "at: command not found"
        mock_subprocess.return_value = mock_result
        
        result = self.tool.schedule_task(command="ls /", time="14:30")
        
        self.assertEqual(result, ({'error': 'at: command not found'}, 400))

    @patch('os_araci.tools.scheduler.subprocess.run')
    def test_schedule_task_exception(self, mock_subprocess):
        """Test task scheduling with exception"""
        mock_subprocess.side_effect = Exception("Subprocess failed")
        
        result = self.tool.schedule_task(command="ls /", time="14:30")
        
        self.assertEqual(result, ({'error': 'Subprocess failed'}, 400))

    @patch('os_araci.tools.scheduler.subprocess.run')
    def test_schedule_task_with_kwargs(self, mock_subprocess):
        """Test task scheduling with additional kwargs"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = self.tool.schedule_task(command="ls /", time="14:30", extra_param="value")
        
        self.assertIn('message', result)

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_list_scheduled_tasks_success_windows(self, mock_platform, mock_subprocess):
        """Test successful task listing on Windows"""
        mock_platform.return_value = "Windows"
        mock_result = MagicMock()
        mock_result.stdout = "TaskName                                 Next Run Time          Status\n============================================== ====================== ===============\nScheduledTask                            12/13/2025 2:30:00 PM    Ready"
        mock_subprocess.return_value = mock_result
        
        result = self.tool.list_scheduled_tasks()
        
        expected_tasks = mock_result.stdout.strip().split('\n')
        self.assertEqual(result['tasks'], expected_tasks)
        mock_subprocess.assert_called_once_with("schtasks", shell=True, capture_output=True, text=True)

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_list_scheduled_tasks_success_linux(self, mock_platform, mock_subprocess):
        """Test successful task listing on Linux"""
        mock_platform.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.stdout = "1\tFri Dec 13 14:30:00 2025 a user\n2\tSat Dec 14 10:00:00 2025 a user"
        mock_subprocess.return_value = mock_result
        
        result = self.tool.list_scheduled_tasks()
        
        expected_tasks = mock_result.stdout.strip().split('\n')
        self.assertEqual(result['tasks'], expected_tasks)
        mock_subprocess.assert_called_once_with("atq", shell=True, capture_output=True, text=True)

    @patch('os_araci.tools.scheduler.subprocess.run')
    def test_list_scheduled_tasks_exception(self, mock_subprocess):
        """Test task listing with exception"""
        mock_subprocess.side_effect = Exception("List failed")
        
        result = self.tool.list_scheduled_tasks()
        
        self.assertEqual(result, ({'error': 'List failed'}, 400))

    @patch('os_araci.tools.scheduler.subprocess.run')
    def test_list_scheduled_tasks_empty(self, mock_subprocess):
        """Test task listing with empty result"""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result
        
        result = self.tool.list_scheduled_tasks()
        
        self.assertEqual(result['tasks'], [""])

    @patch('os_araci.tools.scheduler.subprocess.run')
    def test_list_scheduled_tasks_with_kwargs(self, mock_subprocess):
        """Test task listing with additional kwargs"""
        mock_result = MagicMock()
        mock_result.stdout = "task1\ntask2"
        mock_subprocess.return_value = mock_result
        
        result = self.tool.list_scheduled_tasks(extra_param="value")
        
        self.assertIn('tasks', result)

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_cancel_task_success_windows(self, mock_platform, mock_subprocess):
        """Test successful task cancellation on Windows"""
        mock_platform.return_value = "Windows"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = self.tool.cancel_task(task_id="ScheduledTask")
        
        self.assertEqual(result['message'], 'Task ScheduledTask cancelled successfully')
        expected_command = 'schtasks /delete /tn "ScheduledTask" /f'
        mock_subprocess.assert_called_once_with(expected_command, shell=True, capture_output=True, text=True)

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_cancel_task_success_linux(self, mock_platform, mock_subprocess):
        """Test successful task cancellation on Linux"""
        mock_platform.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = self.tool.cancel_task(task_id="1")
        
        self.assertEqual(result['message'], 'Task 1 cancelled successfully')
        expected_command = 'at -d 1'
        mock_subprocess.assert_called_once_with(expected_command, shell=True, capture_output=True, text=True)

    def test_cancel_task_no_id(self):
        """Test task cancellation with no task ID"""
        result = self.tool.cancel_task()
        
        self.assertEqual(result, ({'error': 'Task ID is required'}, 400))

    def test_cancel_task_empty_id(self):
        """Test task cancellation with empty task ID"""
        result = self.tool.cancel_task(task_id="")
        
        self.assertEqual(result, ({'error': 'Task ID is required'}, 400))

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_cancel_task_failure(self, mock_platform, mock_subprocess):
        """Test task cancellation failure"""
        mock_platform.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "at: invalid job number"
        mock_subprocess.return_value = mock_result
        
        result = self.tool.cancel_task(task_id="999")
        
        self.assertEqual(result, ({'error': 'at: invalid job number'}, 400))

    @patch('os_araci.tools.scheduler.subprocess.run')
    def test_cancel_task_exception(self, mock_subprocess):
        """Test task cancellation with exception"""
        mock_subprocess.side_effect = Exception("Cancel failed")
        
        result = self.tool.cancel_task(task_id="1")
        
        self.assertEqual(result, ({'error': 'Cancel failed'}, 400))

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_schedule_recurring_task_success_windows(self, mock_platform, mock_subprocess):
        """Test successful recurring task scheduling on Windows"""
        mock_platform.return_value = "Windows"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = self.tool.schedule_recurring_task(command="backup.bat", schedule_type="daily", time="02:00")
        
        self.assertEqual(result['message'], 'Recurring task scheduled: backup.bat as daily at 02:00')
        expected_command = 'schtasks /create /tn "RecurringTask" /tr "backup.bat" /sc daily /st 02:00'
        mock_subprocess.assert_called_once_with(expected_command, shell=True, capture_output=True, text=True)

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_schedule_recurring_task_daily_linux(self, mock_platform, mock_subprocess):
        """Test successful daily recurring task scheduling on Linux"""
        mock_platform.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = self.tool.schedule_recurring_task(command="backup.sh", schedule_type="daily", time="02:30")
        
        self.assertEqual(result['message'], 'Recurring task scheduled: backup.sh as daily at 02:30')
        expected_command = '(echo "30 2 * * * backup.sh") | crontab -'
        mock_subprocess.assert_called_once_with(expected_command, shell=True, capture_output=True, text=True)

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_schedule_recurring_task_weekly_linux(self, mock_platform, mock_subprocess):
        """Test successful weekly recurring task scheduling on Linux"""
        mock_platform.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = self.tool.schedule_recurring_task(command="weekly_backup.sh", schedule_type="weekly", time="03:15")
        
        self.assertEqual(result['message'], 'Recurring task scheduled: weekly_backup.sh as weekly at 03:15')
        expected_command = '(echo "15 3 * * 1 weekly_backup.sh") | crontab -'
        mock_subprocess.assert_called_once_with(expected_command, shell=True, capture_output=True, text=True)

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_schedule_recurring_task_monthly_linux(self, mock_platform, mock_subprocess):
        """Test successful monthly recurring task scheduling on Linux"""
        mock_platform.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = self.tool.schedule_recurring_task(command="monthly_backup.sh", schedule_type="monthly", time="04:00")
        
        self.assertEqual(result['message'], 'Recurring task scheduled: monthly_backup.sh as monthly at 04:00')
        expected_command = '(echo "0 4 1 * * monthly_backup.sh") | crontab -'
        mock_subprocess.assert_called_once_with(expected_command, shell=True, capture_output=True, text=True)

    @patch('os_araci.tools.scheduler.platform.system')
    def test_schedule_recurring_task_invalid_type_linux(self, mock_platform):
        """Test recurring task scheduling with invalid schedule type on Linux"""
        mock_platform.return_value = "Linux"
        
        result = self.tool.schedule_recurring_task(command="test.sh", schedule_type="invalid", time="10:00")
        
        self.assertEqual(result, ({'error': 'Invalid schedule_type'}, 400))

    def test_schedule_recurring_task_no_command(self):
        """Test recurring task scheduling with no command"""
        result = self.tool.schedule_recurring_task(schedule_type="daily", time="02:00")
        
        self.assertEqual(result, ({'error': 'Command, schedule_type, and time are required'}, 400))

    def test_schedule_recurring_task_no_schedule_type(self):
        """Test recurring task scheduling with no schedule type"""
        result = self.tool.schedule_recurring_task(command="test.sh", time="02:00")
        
        self.assertEqual(result, ({'error': 'Command, schedule_type, and time are required'}, 400))

    def test_schedule_recurring_task_no_time(self):
        """Test recurring task scheduling with no time"""
        result = self.tool.schedule_recurring_task(command="test.sh", schedule_type="daily")
        
        self.assertEqual(result, ({'error': 'Command, schedule_type, and time are required'}, 400))

    @patch('os_araci.tools.scheduler.subprocess.run')
    def test_schedule_recurring_task_exception(self, mock_subprocess):
        """Test recurring task scheduling with exception"""
        mock_subprocess.side_effect = Exception("Recurring schedule failed")
        
        result = self.tool.schedule_recurring_task(command="test.sh", schedule_type="daily", time="02:00")
        
        self.assertEqual(result, ({'error': 'Recurring schedule failed'}, 400))

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_task_status_success_windows(self, mock_platform, mock_subprocess):
        """Test successful task status check on Windows"""
        mock_platform.return_value = "Windows"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "HostName: DESKTOP-123\nTaskName: \\ScheduledTask\nNext Run Time: 12/13/2025 2:30:00 PM\nStatus: Ready"
        mock_subprocess.return_value = mock_result
        
        result = self.tool.task_status(task_name="ScheduledTask")
        
        self.assertEqual(result['status'], mock_result.stdout.strip())
        expected_command = 'schtasks /query /tn "ScheduledTask" /v /fo LIST'
        mock_subprocess.assert_called_once_with(expected_command, shell=True, capture_output=True, text=True)

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_task_status_success_linux(self, mock_platform, mock_subprocess):
        """Test successful task status check on Linux"""
        mock_platform.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "30 2 * * * /usr/bin/backup.sh"
        mock_subprocess.return_value = mock_result
        
        result = self.tool.task_status(task_name="backup.sh")
        
        self.assertEqual(result['status'], mock_result.stdout.strip())
        expected_command = 'crontab -l | grep "backup.sh"'
        mock_subprocess.assert_called_once_with(expected_command, shell=True, capture_output=True, text=True)

    def test_task_status_no_name(self):
        """Test task status check with no task name"""
        result = self.tool.task_status()
        
        self.assertEqual(result, ({'error': 'Task name is required'}, 400))

    def test_task_status_empty_name(self):
        """Test task status check with empty task name"""
        result = self.tool.task_status(task_name="")
        
        self.assertEqual(result, ({'error': 'Task name is required'}, 400))

    @patch('os_araci.tools.scheduler.subprocess.run')
    @patch('os_araci.tools.scheduler.platform.system')
    def test_task_status_failure(self, mock_platform, mock_subprocess):
        """Test task status check failure"""
        mock_platform.return_value = "Windows"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "ERROR: The system cannot find the specified task."
        mock_subprocess.return_value = mock_result
        
        result = self.tool.task_status(task_name="NonExistentTask")
        
        self.assertEqual(result, ({'error': 'ERROR: The system cannot find the specified task.'}, 400))

    @patch('os_araci.tools.scheduler.subprocess.run')
    def test_task_status_exception(self, mock_subprocess):
        """Test task status check with exception"""
        mock_subprocess.side_effect = Exception("Status check failed")
        
        result = self.tool.task_status(task_name="test_task")
        
        self.assertEqual(result, ({'error': 'Status check failed'}, 400))

    def test_action_execution(self):
        """Test action execution through the tool interface"""
        with patch('os_araci.tools.scheduler.subprocess.run') as mock_subprocess:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_subprocess.return_value = mock_result
            
            result = self.tool.execute_action("schedule_task", command="test.sh", time="14:30")
            
            self.assertIn('message', result)

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