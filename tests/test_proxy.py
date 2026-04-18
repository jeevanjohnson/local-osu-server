"""Tests for proxy.main module."""

import pytest
from unittest.mock import patch, MagicMock, call
from proxy import main


class TestSetInternetSetting:
    """Test suite for set_internet_setting function."""

    @patch("proxy.main.QueryValueEx")
    @patch("proxy.main.SetValueEx")
    def test_happy_path_set_string_value(self, mock_set, mock_query):
        """Set a string internet setting."""
        mock_query.return_value = ("http://proxy:8080", 1)  # REG_SZ type
        
        main.set_internet_setting("ProxyServer", "http://localhost:8080")
        
        mock_query.assert_called_once()
        mock_set.assert_called_once()
        # Verify SetValueEx was called with correct arguments
        # SetValueEx(key, value_name, reserved, type, value)
        args = mock_set.call_args[0]
        assert args[1] == "ProxyServer"  # value_name
        assert args[4] == "http://localhost:8080"  # value
        assert args[3] == 1  # type (preserved from registry)

    @patch("proxy.main.QueryValueEx")
    @patch("proxy.main.SetValueEx")
    def test_happy_path_set_numeric_value(self, mock_set, mock_query):
        """Set a numeric internet setting."""
        mock_query.return_value = (0, 4)  # REG_DWORD type
        
        main.set_internet_setting("ProxyEnable", 1)
        
        mock_set.assert_called_once()
        args = mock_set.call_args[0]
        assert args[4] == 1

    @patch("proxy.main.QueryValueEx")
    @patch("proxy.main.SetValueEx")
    def test_edge_case_empty_string_value(self, mock_set, mock_query):
        """Set internet setting to empty string."""
        mock_query.return_value = ("", 1)
        
        main.set_internet_setting("ProxyServer", "")
        
        mock_set.assert_called_once()
        args = mock_set.call_args[0]
        assert args[4] == ""

    @patch("proxy.main.QueryValueEx", side_effect=Exception("Registry error"))
    def test_error_case_registry_query_fails(self, mock_query):
        """Setting fails if query throws exception."""
        with pytest.raises(Exception, match="Registry error"):
            main.set_internet_setting("ProxyEnable", 1)


class TestNotifyInternetSettingsChanged:
    """Test suite for notify_internet_settings_changed function."""

    @patch("proxy.main.ctypes")
    def test_happy_path_notify_success(self, mock_ctypes):
        """Successfully notify Windows of internet settings change."""
        mock_internet_set_option = MagicMock()
        mock_ctypes.windll.Wininet.InternetSetOptionW = mock_internet_set_option
        
        main.notify_internet_settings_changed()
        
        # Should be called twice: INTERNET_OPTION_REFRESH and INTERNET_OPTION_SETTINGS_CHANGED
        assert mock_internet_set_option.call_count == 2
        mock_internet_set_option.assert_any_call(0, 37, 0, 0)
        mock_internet_set_option.assert_any_call(0, 39, 0, 0)

    @patch("proxy.main.ctypes")
    @patch("builtins.print")
    def test_error_case_windll_access_fails(self, mock_print, mock_ctypes):
        """InternetSetOptionW call fails gracefully."""
        mock_ctypes.windll.Wininet.InternetSetOptionW.side_effect = Exception("WinAPI error")
        
        # Should not raise, but should print warning
        main.notify_internet_settings_changed()
        
        # Verify warning was printed
        mock_print.assert_called()
        call_args = mock_print.call_args[0][0]
        assert "Could not notify system" in call_args


class TestEnableWindowsProxy:
    """Test suite for enable_windows_proxy function."""

    @patch("proxy.main.notify_internet_settings_changed")
    @patch("proxy.main.set_internet_setting")
    @patch("builtins.print")
    def test_happy_path_enable_proxy(self, mock_print, mock_set, mock_notify):
        """Successfully enable Windows proxy."""
        main.enable_windows_proxy()
        
        # Verify all settings were set
        assert mock_set.call_count == 3
        mock_set.assert_any_call("ProxyEnable", 1)
        mock_set.assert_any_call("ProxyServer", "http://localhost:8080")
        mock_set.assert_any_call("ProxyOverride", "*.ppy.sh*")
        
        # Verify notification was sent
        mock_notify.assert_called_once()
        
        # Verify success message was printed
        mock_print.assert_called()
        assert "✓" in str(mock_print.call_args[0][0])

    @patch("proxy.main.notify_internet_settings_changed")
    @patch("proxy.main.set_internet_setting", side_effect=Exception("Registry error"))
    @patch("builtins.print")
    def test_error_case_enable_fails(self, mock_print, mock_set, mock_notify):
        """Enable proxy fails gracefully."""
        main.enable_windows_proxy()
        
        # Should print error message
        mock_print.assert_called()
        call_args = mock_print.call_args[0][0]
        assert "✗" in call_args
        assert "Failed" in call_args


class TestDisableWindowsProxy:
    """Test suite for disable_windows_proxy function."""

    @patch("proxy.main.notify_internet_settings_changed")
    @patch("proxy.main.set_internet_setting")
    @patch("builtins.print")
    def test_happy_path_disable_proxy(self, mock_print, mock_set, mock_notify):
        """Successfully disable Windows proxy."""
        main.disable_windows_proxy()
        
        # Verify all settings were reset
        assert mock_set.call_count == 3
        mock_set.assert_any_call("ProxyEnable", 0)
        mock_set.assert_any_call("ProxyServer", "-")
        mock_set.assert_any_call("ProxyOverride", "-")
        
        # Verify notification was sent
        mock_notify.assert_called_once()
        
        # Verify success message
        mock_print.assert_called()
        assert "✓" in str(mock_print.call_args[0][0])

    @patch("proxy.main.notify_internet_settings_changed")
    @patch("proxy.main.set_internet_setting", side_effect=Exception("Registry error"))
    @patch("builtins.print")
    def test_error_case_disable_fails(self, mock_print, mock_set, mock_notify):
        """Disable proxy fails gracefully."""
        main.disable_windows_proxy()
        
        # Should print error message
        mock_print.assert_called()
        call_args = mock_print.call_args[0][0]
        assert "✗" in call_args
        assert "Failed" in call_args


class TestStart:
    """Test suite for start function."""

    @patch("proxy.main.subprocess.Popen")
    @patch("proxy.main.enable_windows_proxy")
    def test_happy_path_start_proxy(self, mock_enable, mock_popen):
        """Successfully start proxy service."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        main.start()
        
        # Verify proxy was enabled
        mock_enable.assert_called_once()
        
        # Verify mitmdump was started
        mock_popen.assert_called_once_with(["mitmdump", "-s", "./proxy/mitm.py"])
        
        # Verify process.wait() was called
        mock_process.wait.assert_called_once()

    @patch("proxy.main.subprocess.Popen", side_effect=FileNotFoundError("mitmdump not found"))
    @patch("proxy.main.enable_windows_proxy")
    def test_error_case_mitmdump_not_found(self, mock_enable, mock_popen):
        """Start fails if mitmdump is not found."""
        with pytest.raises(FileNotFoundError):
            main.start()
        
        # Proxy should still have been enabled
        mock_enable.assert_called_once()

    @patch("proxy.main.subprocess.Popen")
    @patch("proxy.main.enable_windows_proxy", side_effect=Exception("Proxy enable failed"))
    def test_error_case_enable_proxy_fails(self, mock_enable, mock_popen):
        """Start fails if enabling proxy fails."""
        with pytest.raises(Exception, match="Proxy enable failed"):
            main.start()
        
        # mitmdump should not be started
        mock_popen.assert_not_called()


class TestStop:
    """Test suite for stop function."""

    @patch("proxy.main.disable_windows_proxy")
    @patch("os.system")
    def test_happy_path_stop_proxy(self, mock_system, mock_disable):
        """Successfully stop proxy service."""
        main.stop()
        
        # Verify mitmdump was killed
        mock_system.assert_called_once_with("taskkill /F /IM mitmdump.exe")
        
        # Verify proxy was disabled
        mock_disable.assert_called_once()

    @patch("proxy.main.disable_windows_proxy")
    @patch("os.system", side_effect=Exception("taskkill failed"))
    def test_error_case_taskkill_fails(self, mock_system, mock_disable):
        """Stop succeeds even if taskkill fails."""
        main.stop()
        
        # Disable proxy should still be called
        mock_disable.assert_called_once()

    @patch("proxy.main.disable_windows_proxy", side_effect=Exception("Disable failed"))
    @patch("os.system")
    def test_error_case_disable_fails(self, mock_system, mock_disable):
        """Stop fails if disable proxy fails."""
        with pytest.raises(Exception, match="Disable failed"):
            main.stop()

    @patch("proxy.main.disable_windows_proxy")
    @patch("os.system")
    @patch("builtins.print")
    def test_error_case_exception_caught_gracefully(self, mock_print, mock_system, mock_disable):
        """Stop handles exceptions gracefully and prints error."""
        mock_system.side_effect = Exception("Test error")
        
        # Should not raise, error should be caught
        main.stop()
        
        # Error message should be printed
        mock_print.assert_called()
        assert "error" in str(mock_print.call_args[0][0]).lower()


class TestServiceLifecycle:
    """Integration tests for service start/stop lifecycle."""

    @patch("proxy.main.subprocess.Popen")
    @patch("proxy.main.disable_windows_proxy")
    @patch("proxy.main.enable_windows_proxy")
    @patch("os.system")
    def test_full_lifecycle_start_and_stop(self, mock_system, mock_enable, mock_disable, mock_popen):
        """Complete start and stop cycle."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        # Start service
        main.start()
        mock_enable.assert_called_once()
        
        # Stop service
        main.stop()
        mock_system.assert_called_once()
        mock_disable.assert_called_once()

    @patch("proxy.main.subprocess.Popen")
    @patch("proxy.main.disable_windows_proxy")
    @patch("proxy.main.enable_windows_proxy")
    @patch("os.system")
    def test_multiple_starts(self, mock_system, mock_enable, mock_disable, mock_popen):
        """Multiple service starts (should handle gracefully)."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        main.start()
        main.start()
        
        # Should start multiple processes
        assert mock_popen.call_count == 2
