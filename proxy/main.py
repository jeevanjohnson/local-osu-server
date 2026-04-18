# Reference: https://gist.github.com/lopes/9bf99ff7cf3d6e8d4c98972bb3262985

import ctypes
import os
import subprocess
from typing import Any, Callable
from winreg import HKEY_CURRENT_USER, KEY_ALL_ACCESS, OpenKey, QueryValueEx, SetValueEx

INTERNET_SETTINGS = OpenKey(
    key=HKEY_CURRENT_USER,
    sub_key=r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
    reserved=0,
    access=KEY_ALL_ACCESS,
)


def set_internet_setting(key: str, value: Any) -> None:
    # try:
    # except FileNotFoundError:
    #     # Key doesn't exist, default to REG_SZ for strings
    #     value_type = 1  # REG_SZ
    current_value, value_type = QueryValueEx(INTERNET_SETTINGS, key)
    SetValueEx(INTERNET_SETTINGS, key, 0, value_type, value)


def notify_internet_settings_changed() -> None:
    """Notify Windows that Internet settings have changed."""
    try:
        internet_set_option: Callable = ctypes.windll.Wininet.InternetSetOptionW
        internet_set_option(0, 37, 0, 0)  # INTERNET_OPTION_REFRESH
        internet_set_option(0, 39, 0, 0)  # INTERNET_OPTION_SETTINGS_CHANGED
    except Exception as e:
        print(f"Warning: Could not notify system of proxy change: {e}")


def enable_windows_proxy() -> None:
    """Enable Windows proxy via Registry."""
    try:
        set_internet_setting("ProxyEnable", 1)
        set_internet_setting("ProxyServer", "http://localhost:8080")
        set_internet_setting("ProxyOverride", "*.ppy.sh*")
        notify_internet_settings_changed()
        print("✓ Windows proxy enabled: http://localhost:8080")
    except Exception as e:
        print(f"✗ Failed to enable proxy: {e}")


def disable_windows_proxy() -> None:
    """Disable Windows proxy via Registry."""
    try:
        set_internet_setting("ProxyEnable", 0)
        set_internet_setting("ProxyServer", "-")
        set_internet_setting("ProxyOverride", "-")
        notify_internet_settings_changed()
        print("✓ Windows proxy disabled")
    except Exception as e:
        print(f"✗ Failed to disable proxy: {e}")

# Service functions that will be called by the launcher

def stop():
    try:
        os.system("taskkill /F /IM mitmdump.exe")
    except Exception as e:
        print(f"error killing mitmdump: {e}")
    disable_windows_proxy()

def start():
    enable_windows_proxy()
    process = subprocess.Popen(["mitmdump", "-s", "./proxy/mitm.py"])
    process.wait()
