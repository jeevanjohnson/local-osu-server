# Reference: https://gist.github.com/lopes/9bf99ff7cf3d6e8d4c98972bb3262985

from jays_tools.architecture import Adapter
from typing import Any, Callable
import ctypes
from winreg import (
    HKEY_CURRENT_USER, KEY_ALL_ACCESS, 
    OpenKey, QueryValueEx, SetValueEx,
    HKEYType
)
import os
import subprocess

class WindowsProxyAdapter(Adapter):
    
    def get_internet_settings(self) -> HKEYType:
        return OpenKey(
            key=HKEY_CURRENT_USER,
            sub_key=r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            reserved=0,
            access=KEY_ALL_ACCESS,
        )

    def set_internet_setting(self, key: str, value: Any) -> None:
        INTERNET_SETTINGS = self.get_internet_settings()
        current_value, value_type = QueryValueEx(INTERNET_SETTINGS, key)
        SetValueEx(INTERNET_SETTINGS, key, 0, value_type, value)
    
    def notify_internet_settings_changed(self) -> None:
        """Notify Windows that Internet settings have changed."""
        try:
            internet_set_option: Callable = ctypes.windll.Wininet.InternetSetOptionW
            internet_set_option(0, 37, 0, 0)  # INTERNET_OPTION_REFRESH
            internet_set_option(0, 39, 0, 0)  # INTERNET_OPTION_SETTINGS_CHANGED
        except Exception as e:
            print(f"Warning: Could not notify system of proxy change: {e}")

    def enable_windows_proxy(
        self, 
        proxy_ip_address: str, 
        exclusions: str | None = None
    ) -> None:
        """Enable Windows proxy via Registry."""
        self.set_internet_setting("ProxyEnable", 1)
        self.set_internet_setting("ProxyServer", proxy_ip_address)

        if exclusions is not None:
            self.set_internet_setting("ProxyOverride", exclusions)
        else:
            self.set_internet_setting("ProxyOverride", "-")
        
        self.notify_internet_settings_changed()

    def disable_windows_proxy(self) -> None:
        """Disable Windows proxy via Registry."""
        self.set_internet_setting("ProxyEnable", 0)
        self.set_internet_setting("ProxyServer", "-")
        self.set_internet_setting("ProxyOverride", "-")
        self.notify_internet_settings_changed()

class MitmProxyAdapter(Adapter):

    def start_middleman_proxy(self, middle_man_script: str) -> None:
        subprocess.Popen(
            ["mitmdump", "-s", middle_man_script, "-q"]
        )
    
    def stop_middle_man_proxy(self) -> None:
        try:
            os.system("taskkill /F /IM mitmdump.exe")
        except Exception as error:
            error_str = str(error)

            if not '"mitmdump.exe" not found' in error_str:
                raise error