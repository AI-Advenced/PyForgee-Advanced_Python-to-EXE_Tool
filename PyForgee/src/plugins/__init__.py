"""Système de plugins de PyForgee"""

from .base_plugin import BasePlugin
from .upx_plugin import UPXPlugin
from .pyarmor_plugin import PyArmorPlugin
from .icon_manager import IconManager

__all__ = [
    "BasePlugin",
    "UPXPlugin",
    "PyArmorPlugin",
    "IconManager",
]