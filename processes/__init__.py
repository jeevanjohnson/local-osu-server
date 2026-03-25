from .interface.interface import interface_process
from .los.server import los_process
from .middleman.proxy import proxy_process
from .songs_folder import songs_folder_process

__all__ = ["interface_process", "los_process", "proxy_process", "songs_folder_process"]
