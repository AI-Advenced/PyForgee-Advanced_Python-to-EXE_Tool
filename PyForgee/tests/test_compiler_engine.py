#!/usr/bin/env python3
"""
Tests pour le moteur de compilation PyForgee
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.core.compiler_engine import (
    CompilerEngine, CompilationOptions, CompilationResult,
    PyInstallerBackend, NuitkaBackend, CxFreezeBackend,
    CompilerType, create_default_options
)


class TestCompilationOptions:
    """Tests pour CompilationOptions"""
    
    def test_default_options(self):
        """Test des options par défaut"""
        options = CompilationOptions(
            source_path="test.py",
            output_path="./dist"
        )
        
        assert options.source_path == "test.py"
        assert options.output_path == "./dist"
        assert options.onefile == True
        assert options.console == False
        assert options.optimize == True
        assert options.exclude_modules == []
        assert options.hidden_imports == []
    
    def test_custom_options(self):
        """Test des options personnalisées"""
        options = CompilationOptions(
            source_path="app.py",
            output_path="./build",
            onefile=False,
            console=True,
            exclude_modules=["tkinter", "unittest"]
        )
        
        assert options.onefile == False
        assert options.console == True
        assert "tkinter" in options.exclude_modules
        assert "unittest" in options.exclude_modules


class TestCompilationResult:
    """Tests pour CompilationResult"""
    
    def test_successful_result(self):
        """Test d'un résultat de compilation réussi"""
        result = CompilationResult(
            success=True,
            output_path="/path/to/app.exe",
            compilation_time=45.5,
            file_size=1024000,
            compiler_used=CompilerType.PYINSTALLER
        )
        
        assert result.success == True
        assert result.output_path == "/path/to/app.exe"
        assert result.compilation_time == 45.5
        assert result.file_size == 1024000
        assert result.compiler_used == CompilerType.PYINSTALLER
        assert result.warnings == []
    
    def test_failed_result(self):
        """Test d'un résultat de compilation échoué"""
        result = CompilationResult(
            success=False,
            error_message="Compilation failed",
            compilation_time=10.0
        )
        
        assert result.success == False
        assert result.error_message == "Compilation failed"
        assert result.output_path == None
        assert result.file_size == 0


class TestPyInstallerBackend:
    """Tests pour PyInstallerBackend"""
    
    def setup_method(self):
        self.backend = PyInstallerBackend()
    
    @patch('subprocess.run')
    def test_is_available(self, mock_run):
        """Test de détection de PyInstaller"""
        mock_run.return_value.returncode = 0
        assert self.backend.is_available() == True
        
        mock_run.return_value.returncode = 1
        assert self.backend.is_available() == False
    
    @patch('subprocess.run')
    def test_get_version(self, mock_run):
        """Test de récupération de version"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "PyInstaller 5.0.1"
        
        version = self.backend.get_version()
        assert version == "PyInstaller 5.0.1"
    
    def test_get_score(self):
        """Test du calcul de score"""
        options = CompilationOptions("test.py", "./dist")
        score = self.backend.get_score(options)
        
        assert isinstance(score, int)
        assert 0 <= score <= 100
    
    @pytest.mark.asyncio
    async def test_compile_success(self):
        """Test de compilation réussie"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crée un fichier source de test
            source_file = os.path.join(temp_dir, "test.py")
            with open(source_file, 'w') as f:
                f.write("print('Hello World')")
            
            options = CompilationOptions(
                source_path=source_file,
                output_path=temp_dir
            )
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                # Mock process réussi
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b"Success", b"")
                mock_process.returncode = 0
                mock_subprocess.return_value = mock_process
                
                # Mock fichier de sortie
                output_file = os.path.join(temp_dir, "test.exe")
                with open(output_file, 'w') as f:
                    f.write("fake exe")
                
                with patch.object(self.backend, '_find_output_file', return_value=output_file):
                    result = await self.backend.compile(options)
                
                assert result.success == True
                assert result.compiler_used == CompilerType.PYINSTALLER


class TestNuitkaBackend:
    """Tests pour NuitkaBackend"""
    
    def setup_method(self):
        self.backend = NuitkaBackend()
    
    @patch('subprocess.run')
    def test_is_available(self, mock_run):
        """Test de détection de Nuitka"""
        mock_run.return_value.returncode = 0
        assert self.backend.is_available() == True
        
        mock_run.return_value.returncode = 1
        assert self.backend.is_available() == False
    
    def test_get_score(self):
        """Test du calcul de score Nuitka"""
        options = CompilationOptions("test.py", "./dist", optimize=True)
        score = self.backend.get_score(options)
        
        # Nuitka devrait avoir un bon score avec optimization
        assert score >= 80


class TestCompilerEngine:
    """Tests pour CompilerEngine"""
    
    def setup_method(self):
        self.engine = CompilerEngine()
    
    def test_initialization(self):
        """Test d'initialisation du moteur"""
        assert hasattr(self.engine, 'compilers')
        assert hasattr(self.engine, 'available_compilers')
        assert CompilerType.PYINSTALLER in self.engine.compilers
        assert CompilerType.NUITKA in self.engine.compilers
        assert CompilerType.CX_FREEZE in self.engine.compilers
    
    def test_select_best_compiler_with_preference(self):
        """Test de sélection avec préférence"""
        options = CompilationOptions(
            source_path="test.py",
            output_path="./dist",
            preferred_compiler=CompilerType.NUITKA
        )
        
        # Mock des compilateurs disponibles
        mock_nuitka = Mock()
        self.engine.available_compilers = {
            CompilerType.NUITKA: mock_nuitka
        }
        
        compiler_type, backend = self.engine.select_best_compiler(options)
        
        assert compiler_type == CompilerType.NUITKA
        assert backend == mock_nuitka
    
    def test_select_best_compiler_auto(self):
        """Test de sélection automatique"""
        options = CompilationOptions("test.py", "./dist")
        
        # Mock des compilateurs avec scores
        mock_pyinstaller = Mock()
        mock_pyinstaller.get_score.return_value = 70
        
        mock_nuitka = Mock()
        mock_nuitka.get_score.return_value = 85
        
        self.engine.available_compilers = {
            CompilerType.PYINSTALLER: mock_pyinstaller,
            CompilerType.NUITKA: mock_nuitka
        }
        
        compiler_type, backend = self.engine.select_best_compiler(options)
        
        # Nuitka devrait être sélectionné avec un score plus élevé
        assert compiler_type == CompilerType.NUITKA
        assert backend == mock_nuitka
    
    @pytest.mark.asyncio
    async def test_compile_success(self):
        """Test de compilation réussie"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crée un fichier source
            source_file = os.path.join(temp_dir, "test.py")
            with open(source_file, 'w') as f:
                f.write("print('Hello World')")
            
            options = CompilationOptions(
                source_path=source_file,
                output_path=temp_dir
            )
            
            # Mock du backend
            mock_backend = AsyncMock()
            mock_result = CompilationResult(
                success=True,
                output_path=os.path.join(temp_dir, "test.exe"),
                compilation_time=30.0,
                file_size=1024,
                compiler_used=CompilerType.PYINSTALLER
            )
            mock_backend.compile.return_value = mock_result
            
            with patch.object(self.engine, 'select_best_compiler') as mock_select:
                mock_select.return_value = (CompilerType.PYINSTALLER, mock_backend)
                
                result = await self.engine.compile(options)
            
            assert result.success == True
            assert result.compiler_used == CompilerType.PYINSTALLER
    
    @pytest.mark.asyncio
    async def test_compile_file_not_found(self):
        """Test de compilation avec fichier inexistant"""
        options = CompilationOptions(
            source_path="nonexistent.py",
            output_path="./dist"
        )
        
        result = await self.engine.compile(options)
        
        assert result.success == False
        assert "Fichier source introuvable" in result.error_message
    
    @pytest.mark.asyncio
    async def test_batch_compile(self):
        """Test de compilation en lot"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crée plusieurs fichiers source
            scripts = []
            for i in range(3):
                script_file = os.path.join(temp_dir, f"test{i}.py")
                with open(script_file, 'w') as f:
                    f.write(f"print('Script {i}')")
                scripts.append(script_file)
            
            base_options = CompilationOptions(
                source_path="",  # Sera remplacé pour chaque script
                output_path=temp_dir
            )
            
            # Mock compile pour retourner des succès
            with patch.object(self.engine, 'compile') as mock_compile:
                mock_compile.return_value = CompilationResult(success=True)
                
                results = await self.engine.batch_compile(scripts, base_options)
            
            assert len(results) == 3
            assert all(result.success for result in results)
    
    def test_get_compiler_info(self):
        """Test de récupération des informations compilateurs"""
        info = self.engine.get_compiler_info()
        
        assert isinstance(info, dict)
        assert 'pyinstaller' in info
        assert 'nuitka' in info
        assert 'cx_freeze' in info
        
        for compiler_info in info.values():
            assert 'available' in compiler_info
            assert 'version' in compiler_info
            assert 'description' in compiler_info


class TestUtilityFunctions:
    """Tests pour les fonctions utilitaires"""
    
    def test_create_default_options(self):
        """Test de création d'options par défaut"""
        options = create_default_options("script.py", "./output")
        
        assert options.source_path == "script.py"
        assert options.output_path == "./output"
        assert options.onefile == True
        assert options.optimize == True
        assert options.upx_compress == True
        assert len(options.exclude_modules) > 0  # Doit avoir des exclusions par défaut


if __name__ == '__main__':
    pytest.main([__file__])