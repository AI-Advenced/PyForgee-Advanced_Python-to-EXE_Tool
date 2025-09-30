#!/usr/bin/env python3
"""
Configuration pytest pour les tests PyForgee
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Ajoute le répertoire src au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def temp_directory():
    """Fixture pour un répertoire temporaire"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_python_script():
    """Fixture pour un script Python de test"""
    script_content = '''#!/usr/bin/env python3
"""Script de test pour PyForgee"""

import os
import sys

def main():
    print("Hello from PyForgee test script!")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    
    # Test des imports
    import json
    import datetime
    
    data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "message": "PyForgee test successful"
    }
    
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
'''
    return script_content


@pytest.fixture
def sample_gui_script():
    """Fixture pour un script GUI de test"""
    gui_script = '''#!/usr/bin/env python3
"""Script GUI de test pour PyForgee"""

import tkinter as tk
from tkinter import messagebox

def main():
    root = tk.Tk()
    root.title("PyForgee Test GUI")
    root.geometry("300x200")
    
    def show_message():
        messagebox.showinfo("Info", "PyForgee GUI test successful!")
    
    button = tk.Button(root, text="Test PyForgee", command=show_message)
    button.pack(expand=True)
    
    # Ne démarre la mainloop qu'en mode interactif
    if not os.environ.get('PYTEST_RUNNING'):
        root.mainloop()
    else:
        root.quit()

if __name__ == "__main__":
    import os
    os.environ['PYTEST_RUNNING'] = '1'
    main()
'''
    return gui_script


@pytest.fixture
def create_test_script(temp_directory):
    """Fonction helper pour créer des scripts de test"""
    def _create_script(filename, content, executable=False):
        script_path = temp_directory / filename
        script_path.write_text(content, encoding='utf-8')
        
        if executable and hasattr(os, 'chmod'):
            os.chmod(script_path, 0o755)
        
        return script_path
    
    return _create_script


@pytest.fixture
def mock_compiler_backend():
    """Fixture pour un backend de compilation mocké"""
    backend = Mock()
    backend.is_available.return_value = True
    backend.get_version.return_value = "MockCompiler 1.0.0"
    backend.get_score.return_value = 75
    
    return backend


@pytest.fixture
def mock_successful_compilation():
    """Fixture pour une compilation réussie mockée"""
    from src.core.compiler_engine import CompilationResult, CompilerType
    
    return CompilationResult(
        success=True,
        output_path="/fake/path/app.exe",
        compilation_time=30.0,
        file_size=1024000,
        compiler_used=CompilerType.PYINSTALLER
    )


@pytest.fixture
def mock_failed_compilation():
    """Fixture pour une compilation échouée mockée"""
    from src.core.compiler_engine import CompilationResult
    
    return CompilationResult(
        success=False,
        error_message="Mock compilation error",
        compilation_time=5.0
    )


@pytest.fixture
def sample_dependencies():
    """Fixture avec des dépendances de test"""
    return {
        'builtin_modules': {'os', 'sys', 'json', 'datetime'},
        'third_party_modules': {'requests', 'numpy', 'pandas'},
        'local_modules': {'my_module', 'utils'},
        'missing_modules': {'nonexistent_module'}
    }


@pytest.fixture
def mock_system_info():
    """Fixture pour les informations système mockées"""
    return {
        'platform': 'Windows-10-10.0.19041-SP0',
        'system': 'Windows',
        'release': '10',
        'version': '10.0.19041',
        'machine': 'AMD64',
        'processor': 'Intel64 Family 6 Model 142 Stepping 10, GenuineIntel',
        'python_version': '3.9.7 (default, Sep 16 2021, 16:59:28) [MSC v.1929 64 bit (AMD64)]',
        'python_executable': 'C:\\Python39\\python.exe',
        'cpu_count': 8,
        'memory_total': 17179869184
    }


@pytest.fixture(autouse=True)
def setup_logging():
    """Configure le logging pour les tests"""
    import logging
    
    # Configuration silencieuse pour les tests
    logging.getLogger('PyForgee').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)


@pytest.fixture
def mock_file_operations():
    """Mock pour les opérations de fichiers"""
    with patch('os.path.exists') as mock_exists, \
         patch('os.path.getsize') as mock_getsize, \
         patch('shutil.copy2') as mock_copy, \
         patch('os.makedirs') as mock_makedirs:
        
        mock_exists.return_value = True
        mock_getsize.return_value = 1024
        
        yield {
            'exists': mock_exists,
            'getsize': mock_getsize,
            'copy': mock_copy,
            'makedirs': mock_makedirs
        }


@pytest.fixture
def sample_config():
    """Configuration de test pour PyForgee"""
    return {
        'preferred_compiler': 'auto',
        'default_compression': 'auto',
        'default_protection_level': 'intermediate',
        'output_directory': './dist',
        'backup_original': True,
        'parallel_builds': True,
        'max_workers': 2,  # Réduit pour les tests
        'default_excludes': ['tkinter', 'unittest', 'test'],
        'compression_level': 6,  # Réduit pour les tests
        'log_level': 'WARNING'
    }


@pytest.fixture
def plugin_test_directory(temp_directory):
    """Répertoire de plugins de test"""
    plugin_dir = temp_directory / "plugins"
    plugin_dir.mkdir()
    
    # Crée un plugin de test simple
    test_plugin = plugin_dir / "test_plugin.py"
    test_plugin.write_text('''
from src.plugins.base_plugin import BasePlugin, PluginMetadata, PluginType

class TestPlugin(BasePlugin):
    def get_metadata(self):
        return PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Plugin de test",
            author="Test",
            plugin_type=PluginType.TOOL
        )
    
    def initialize(self, config):
        return True
    
    def execute(self, context):
        return {"success": True, "message": "Test plugin executed"}
    
    def cleanup(self):
        pass
''')
    
    return plugin_dir


@pytest.fixture
def disable_external_tools():
    """Désactive les outils externes pour les tests"""
    with patch('shutil.which') as mock_which:
        mock_which.return_value = None  # Aucun outil externe trouvé
        yield


@pytest.fixture
def enable_external_tools():
    """Active les outils externes pour les tests d'intégration"""
    with patch('shutil.which') as mock_which:
        # Simule la présence d'outils externes
        def mock_tool_finder(tool):
            tool_paths = {
                'pyinstaller': '/usr/bin/pyinstaller',
                'nuitka': '/usr/bin/nuitka', 
                'upx': '/usr/bin/upx',
                'pyarmor': '/usr/bin/pyarmor'
            }
            return tool_paths.get(tool)
        
        mock_which.side_effect = mock_tool_finder
        yield


class AsyncContextManager:
    """Helper pour les tests async"""
    
    def __init__(self, result):
        self.result = result
    
    async def __aenter__(self):
        return self.result
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def async_mock_result():
    """Factory pour créer des résultats async mockés"""
    def _create_async_mock(result):
        return AsyncContextManager(result)
    
    return _create_async_mock


# Marques pytest personnalisées
def pytest_configure(config):
    """Configuration des marques pytest"""
    config.addinivalue_line(
        "markers", "integration: marque les tests d'intégration"
    )
    config.addinivalue_line(
        "markers", "slow: marque les tests lents"
    )
    config.addinivalue_line(
        "markers", "external_tools: nécessite des outils externes"
    )
    config.addinivalue_line(
        "markers", "windows: tests spécifiques à Windows"
    )
    config.addinivalue_line(
        "markers", "linux: tests spécifiques à Linux"
    )


def pytest_collection_modifyitems(config, items):
    """Modification automatique des éléments de collection"""
    for item in items:
        # Marque automatiquement les tests lents
        if "slow" in item.nodeid or "integration" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        
        # Marque les tests nécessitant des outils externes
        if any(tool in item.nodeid.lower() for tool in ['pyinstaller', 'nuitka', 'upx', 'pyarmor']):
            item.add_marker(pytest.mark.external_tools)