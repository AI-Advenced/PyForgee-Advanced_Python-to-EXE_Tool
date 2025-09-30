"""Moteur principal de PyForgee"""

from .compiler_engine import CompilerEngine, PyInstallerBackend, NuitkaBackend, CxFreezeBackend
from .dependency_analyzer import DependencyAnalyzer
from .compression_handler import CompressionHandler, UPXCompressor, LZMACompressor, BrotliCompressor
from .protection_manager import ProtectionManager, PyArmorProtector, CustomObfuscator, BytecodeEncryptor

__all__ = [
    "CompilerEngine",
    "PyInstallerBackend",
    "NuitkaBackend",
    "CxFreezeBackend",
    "DependencyAnalyzer",
    "CompressionHandler",
    "UPXCompressor",
    "LZMACompressor",
    "BrotliCompressor",
    "ProtectionManager",
    "PyArmorProtector",
    "CustomObfuscator",
    "BytecodeEncryptor",
]