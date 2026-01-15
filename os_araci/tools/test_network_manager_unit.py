import unittest
from unittest.mock import patch, Mock, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from os_araci.tools.network_manager import NetworkManagerTool


class TestNetworkManagerTool(unittest.TestCase):
    """Comprehensive unit tests for NetworkManagerTool"""

    def setUp(self):
        """Set up test fixtures"""
        self.tool = NetworkManagerTool()

    def test_init(self):
        """Test initialization of NetworkManagerTool"""
        self.assertEqual(self.tool.name, "network_manager")
        self.assertEqual(self.tool.description, "Network yönetim işlemleri")
        self.assertEqual(self.tool.version, "1.0.0")
        
        # Check that actions are registered
        actions = self.tool.get_all_actions()
        self.assertIn("ping", actions)
        self.assertIn("get_connections", actions)
        self.assertIn("port_scan", actions)
        self.assertIn("get_ip", actions)
        self.assertIn("change_ip", actions)

    @patch('os_araci.tools.network_manager.execute_command')
    @patch('os_araci.tools.network_manager.os.name', 'posix')
    def test_ping_success_linux(self, mock_execute):
        """Test successful ping on Linux"""
        mock_execute.return_value = "PING google.com (142.250.191.14): 56 data bytes\n64 bytes from 142.250.191.14: icmp_seq=0 ttl=113 time=15.123 ms"
        
        result = self.tool.ping(host="google.com")
        
        self.assertEqual(result['output'], mock_execute.return_value)
        mock_execute.assert_called_once_with('ping -c 4 google.com')

    @patch('os_araci.tools.network_manager.execute_command')
    @patch('os_araci.tools.network_manager.os.name', 'nt')
    def test_ping_success_windows(self, mock_execute):
        """Test successful ping on Windows"""
        mock_execute.return_value = "Pinging google.com [142.250.191.14] with 32 bytes of data:\nReply from 142.250.191.14: bytes=32 time=15ms TTL=113"
        
        result = self.tool.ping(host="google.com")
        
        self.assertEqual(result['output'], mock_execute.return_value)
        mock_execute.assert_called_once_with('ping google.com')

    @patch('os_araci.tools.network_manager.execute_command')
    @patch('os_araci.tools.network_manager.os.name', 'posix')
    def test_ping_default_host(self, mock_execute):
        """Test ping with default host"""
        mock_execute.return_value = "ping output"
        
        result = self.tool.ping()
        
        self.assertEqual(result['output'], "ping output")
        mock_execute.assert_called_once_with('ping -c 4 google.com')

    @patch('os_araci.tools.network_manager.execute_command')
    def test_ping_exception(self, mock_execute):
        """Test ping with exception"""
        mock_execute.side_effect = Exception("Network unreachable")
        
        result = self.tool.ping(host="invalid.host")
        
        self.assertEqual(result, ({'error': 'Network unreachable'}, 400))

    @patch('os_araci.tools.network_manager.execute_command')
    def test_ping_with_kwargs(self, mock_execute):
        """Test ping with additional kwargs"""
        mock_execute.return_value = "ping output"
        
        result = self.tool.ping(host="example.com", extra_param="value")
        
        self.assertIn('output', result)
        self.assertEqual(result['output'], "ping output")

    @patch('os_araci.tools.network_manager.execute_command')
    @patch('os_araci.tools.network_manager.os.name', 'posix')
    def test_get_connections_success_linux(self, mock_execute):
        """Test successful get_connections on Linux"""
        mock_output = "Active Internet connections (only servers)\nProto Recv-Q Send-Q Local Address Foreign Address State\ntcp 0 0 0.0.0.0:22 0.0.0.0:* LISTEN"
        mock_execute.return_value = mock_output
        
        result = self.tool.get_connections()
        
        expected_connections = mock_output.splitlines()
        self.assertEqual(result['connections'], expected_connections)
        mock_execute.assert_called_once_with('netstat -tuln')

    @patch('os_araci.tools.network_manager.execute_command')
    @patch('os_araci.tools.network_manager.os.name', 'nt')
    def test_get_connections_success_windows(self, mock_execute):
        """Test successful get_connections on Windows"""
        mock_output = "Active Connections\nProto Local Address Foreign Address State\nTCP 0.0.0.0:135 0.0.0.0:0 LISTENING"
        mock_execute.return_value = mock_output
        
        result = self.tool.get_connections()
        
        expected_connections = mock_output.splitlines()
        self.assertEqual(result['connections'], expected_connections)
        mock_execute.assert_called_once_with('netstat -an')

    @patch('os_araci.tools.network_manager.execute_command')
    def test_get_connections_exception(self, mock_execute):
        """Test get_connections with exception"""
        mock_execute.side_effect = Exception("Command failed")
        
        result = self.tool.get_connections()
        
        self.assertEqual(result, ({'error': 'Command failed'}, 400))

    @patch('os_araci.tools.network_manager.execute_command')
    def test_get_connections_with_kwargs(self, mock_execute):
        """Test get_connections with additional kwargs"""
        mock_execute.return_value = "connection output"
        
        result = self.tool.get_connections(extra_param="value")
        
        self.assertIn('connections', result)
        self.assertEqual(result['connections'], ["connection output"])

    @patch('os_araci.tools.network_manager.execute_command')
    @patch('os_araci.tools.network_manager.os.name', 'posix')
    def test_port_scan_success_linux(self, mock_execute):
        """Test successful port scan on Linux"""
        mock_execute.side_effect = [
            "Connection to 192.168.1.1 port 22 [tcp/ssh] succeeded!",
            "nc: connect to 192.168.1.1 port 23 (tcp) failed: Connection refused",
            "Connection to 192.168.1.1 port 80 [tcp/http] succeeded!"
        ]
        
        result = self.tool.port_scan(ip="192.168.1.1", ports=[22, 23, 80])
        
        self.assertEqual(result['open_ports'], [22, 80])
        self.assertEqual(mock_execute.call_count, 3)

    @patch('os_araci.tools.network_manager.execute_command')
    @patch('os_araci.tools.network_manager.os.name', 'nt')
    def test_port_scan_success_windows(self, mock_execute):
        """Test successful port scan on Windows"""
        mock_execute.side_effect = [
            "Connecting To 192.168.1.1...Could not open connection to the host, on port 22: Connect failed",
            "Welcome to Microsoft Telnet Service",
            "Connecting To 192.168.1.1...Could not open connection to the host, on port 80: Connect failed"
        ]
        
        result = self.tool.port_scan(ip="192.168.1.1", ports=[22, 23, 80])
        
        self.assertEqual(result['open_ports'], [23])
        self.assertEqual(mock_execute.call_count, 3)

    def test_port_scan_no_ip(self):
        """Test port scan with no IP"""
        result = self.tool.port_scan(ports=[22, 80])
        
        self.assertEqual(result, ({'error': 'IP address and ports are required'}, 400))

    def test_port_scan_no_ports(self):
        """Test port scan with no ports"""
        result = self.tool.port_scan(ip="192.168.1.1")
        
        self.assertEqual(result, ({'error': 'IP address and ports are required'}, 400))

    def test_port_scan_empty_ip(self):
        """Test port scan with empty IP"""
        result = self.tool.port_scan(ip="", ports=[22, 80])
        
        self.assertEqual(result, ({'error': 'IP address and ports are required'}, 400))

    def test_port_scan_empty_ports(self):
        """Test port scan with empty ports list"""
        result = self.tool.port_scan(ip="192.168.1.1", ports=[])
        
        self.assertEqual(result['open_ports'], [])

    @patch('os_araci.tools.network_manager.execute_command')
    def test_port_scan_exception(self, mock_execute):
        """Test port scan with exception"""
        mock_execute.side_effect = Exception("Scan failed")
        
        result = self.tool.port_scan(ip="192.168.1.1", ports=[22, 80])
        
        self.assertEqual(result, ({'error': 'Scan failed'}, 400))

    @patch('os_araci.tools.network_manager.execute_command')
    @patch('os_araci.tools.network_manager.os.name', 'nt')
    def test_get_ip_success_windows(self, mock_execute):
        """Test successful get_ip on Windows"""
        mock_execute.return_value = "   192.168.1.100   "
        
        result = self.tool.get_ip()
        
        self.assertEqual(result['ip'], "192.168.1.100")
        mock_execute.assert_called_once_with('ipconfig')

    @patch('os_araci.tools.network_manager.execute_command')
    @patch('os_araci.tools.network_manager.os.name', 'posix')
    def test_get_ip_success_linux(self, mock_execute):
        """Test successful get_ip on Linux"""
        mock_execute.return_value = "192.168.1.100 "
        
        result = self.tool.get_ip()
        
        self.assertEqual(result['ip'], "192.168.1.100")
        mock_execute.assert_called_once_with('hostname -I')

    @patch('os_araci.tools.network_manager.execute_command')
    def test_get_ip_exception(self, mock_execute):
        """Test get_ip with exception"""
        mock_execute.side_effect = Exception("Command failed")
        
        result = self.tool.get_ip()
        
        self.assertEqual(result, ({'error': 'Command failed'}, 400))

    @patch('os_araci.tools.network_manager.execute_command')
    def test_get_ip_with_kwargs(self, mock_execute):
        """Test get_ip with additional kwargs"""
        mock_execute.return_value = "192.168.1.100"
        
        result = self.tool.get_ip(extra_param="value")
        
        self.assertEqual(result['ip'], "192.168.1.100")

    @patch('os_araci.tools.network_manager.execute_command')
    @patch('os_araci.tools.network_manager.os.name', 'nt')
    def test_change_ip_success_windows(self, mock_execute):
        """Test successful change_ip on Windows"""
        mock_execute.return_value = "Ok."
        
        result = self.tool.change_ip(interface="Ethernet", ip="192.168.1.100")
        
        expected_message = 'IP address of Ethernet changed to 192.168.1.100'
        self.assertEqual(result['message'], expected_message)
        self.assertEqual(result['details'], "Ok.")
        expected_command = 'netsh interface ip set address name="Ethernet" static 192.168.1.100 255.255.255.0'
        mock_execute.assert_called_once_with(expected_command)

    @patch('os_araci.tools.network_manager.execute_command')
    @patch('os_araci.tools.network_manager.os.name', 'posix')
    def test_change_ip_success_linux(self, mock_execute):
        """Test successful change_ip on Linux"""
        mock_execute.return_value = ""
        
        result = self.tool.change_ip(interface="eth0", ip="192.168.1.100")
        
        expected_message = 'IP address of eth0 changed to 192.168.1.100'
        self.assertEqual(result['message'], expected_message)
        self.assertEqual(result['details'], "")
        expected_command = 'sudo ip addr add 192.168.1.100/24 dev eth0'
        mock_execute.assert_called_once_with(expected_command)

    def test_change_ip_no_interface(self):
        """Test change_ip with no interface"""
        result = self.tool.change_ip(ip="192.168.1.100")
        
        self.assertEqual(result, ({'error': 'Interface and new IP address are required'}, 400))

    def test_change_ip_no_ip(self):
        """Test change_ip with no IP"""
        result = self.tool.change_ip(interface="eth0")
        
        self.assertEqual(result, ({'error': 'Interface and new IP address are required'}, 400))

    def test_change_ip_empty_interface(self):
        """Test change_ip with empty interface"""
        result = self.tool.change_ip(interface="", ip="192.168.1.100")
        
        self.assertEqual(result, ({'error': 'Interface and new IP address are required'}, 400))

    def test_change_ip_empty_ip(self):
        """Test change_ip with empty IP"""
        result = self.tool.change_ip(interface="eth0", ip="")
        
        self.assertEqual(result, ({'error': 'Interface and new IP address are required'}, 400))

    @patch('os_araci.tools.network_manager.execute_command')
    def test_change_ip_exception(self, mock_execute):
        """Test change_ip with exception"""
        mock_execute.side_effect = Exception("Change failed")
        
        result = self.tool.change_ip(interface="eth0", ip="192.168.1.100")
        
        self.assertEqual(result, ({'error': 'Change failed'}, 400))

    @patch('os_araci.tools.network_manager.execute_command')
    def test_change_ip_with_kwargs(self, mock_execute):
        """Test change_ip with additional kwargs"""
        mock_execute.return_value = "Success"
        
        result = self.tool.change_ip(interface="eth0", ip="192.168.1.100", extra_param="value")
        
        self.assertIn('message', result)
        self.assertIn('details', result)

    def test_action_execution(self):
        """Test action execution through the tool interface"""
        with patch('os_araci.tools.network_manager.execute_command') as mock_execute:
            mock_execute.return_value = "ping output"
            
            result = self.tool.execute_action("ping", host="example.com")
            
            self.assertEqual(result['output'], "ping output")

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