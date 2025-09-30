"""
PyForgee - Outil Python-to-EXE avancé
Version 1.0.0

Un outil hybride qui combine les avantages de PyInstaller, cx_Freeze, et Nuitka
avec des fonctionnalités avancées de compression, protection, et optimisation.
"""

__version__ = "1.0.0"
__author__ = "PyForgee Team"
__email__ = "contact@PyForgee.dev"
__description__ = "Outil Python-to-EXE avancé avec optimisations et protection"

# Export des classes principales
from .core.compiler_engine import CompilerEngine
from .core.dependency_analyzer import DependencyAnalyzer
from .core.compression_handler import CompressionHandler
from .core.protection_manager import ProtectionManager

__all__ = [
    "CompilerEngine",
    "DependencyAnalyzer", 
    "CompressionHandler",
    "ProtectionManager",
    "__version__",
]