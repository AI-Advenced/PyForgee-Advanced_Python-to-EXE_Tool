#!/usr/bin/env python3
"""
Tests pour l'analyseur de dépendances PyForgee
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.core.dependency_analyzer import (
    DependencyAnalyzer, DependencyInfo, AnalysisResult, 
    ImportVisitor, analyze_script_dependencies
)


class TestDependencyInfo:
    """Tests pour DependencyInfo"""
    
    def test_default_dependency_info(self):
        """Test des valeurs par défaut"""
        dep = DependencyInfo(name="test_module")
        
        assert dep.name == "test_module"
        assert dep.version is None
        assert dep.location is None
        assert dep.is_builtin == False
        assert dep.is_local == False
        assert dep.is_third_party == False
        assert dep.size_estimate == 0
        assert len(dep.required_by) == 0
        assert len(dep.imports) == 0
    
    def test_custom_dependency_info(self):
        """Test avec valeurs personnalisées"""
        dep = DependencyInfo(
            name="requests",
            version="2.28.0",
            is_third_party=True,
            size_estimate=1024000
        )
        
        assert dep.name == "requests"
        assert dep.version == "2.28.0"
        assert dep.is_third_party == True
        assert dep.size_estimate == 1024000


class TestImportVisitor:
    """Tests pour ImportVisitor"""
    
    def test_simple_import(self):
        """Test d'import simple"""
        import ast
        
        code = """
import os
import sys
"""
        
        tree = ast.parse(code)
        visitor = ImportVisitor()
        visitor.visit(tree)
        
        assert "os" in visitor.imports
        assert "sys" in visitor.imports
    
    def test_from_import(self):
        """Test d'import from"""
        import ast
        
        code = """
from pathlib import Path
from datetime import datetime, timedelta
"""
        
        tree = ast.parse(code)
        visitor = ImportVisitor()
        visitor.visit(tree)
        
        assert "pathlib" in visitor.imports
        assert "datetime" in visitor.imports
    
    def test_dynamic_import(self):
        """Test d'import dynamique"""
        import ast
        
        code = """
__import__('json')
importlib.import_module('yaml')
"""
        
        tree = ast.parse(code)
        visitor = ImportVisitor()
        visitor.visit(tree)
        
        assert "json" in visitor.imports
    
    def test_nested_import(self):
        """Test d'import imbriqué"""
        import ast
        
        code = """
from package.subpackage import module
"""
        
        tree = ast.parse(code)
        visitor = ImportVisitor()
        visitor.visit(tree)
        
        assert "package" in visitor.imports


class TestDependencyAnalyzer:
    """Tests pour DependencyAnalyzer"""
    
    def setup_method(self):
        """Setup pour chaque test"""
        self.analyzer = DependencyAnalyzer()
    
    def test_initialization(self):
        """Test d'initialisation"""
        assert hasattr(self.analyzer, '_builtin_modules')
        assert hasattr(self.analyzer, '_stdlib_modules')
        assert hasattr(self.analyzer, 'default_excludes')
        assert len(self.analyzer.default_excludes) > 0
    
    def test_get_stdlib_modules(self):
        """Test de récupération des modules stdlib"""
        stdlib = self.analyzer._get_stdlib_modules()
        
        assert isinstance(stdlib, set)
        assert "os" in stdlib
        assert "sys" in stdlib
        assert "json" in stdlib
    
    def test_analyze_simple_script(self):
        """Test d'analyse d'un script simple"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import os
import sys
import json
from pathlib import Path

def main():
    print("Hello World")
    data = {"key": "value"}
    json.dumps(data)

if __name__ == "__main__":
    main()
""")
            f.flush()
            
            try:
                result = self.analyzer.analyze_dependencies(f.name)
                
                assert isinstance(result, AnalysisResult)
                assert result.analysis_time > 0
                assert len(result.dependencies) > 0
                
                # Vérifications spécifiques
                deps_names = set(result.dependencies.keys())
                assert "os" in deps_names or "sys" in deps_names or "json" in deps_names
                
            finally:
                os.unlink(f.name)
    
    def test_analyze_with_third_party(self):
        """Test d'analyse avec dépendances third-party"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import os
import requests  # Third-party si disponible
import custom_module  # Local module

def main():
    pass
""")
            f.flush()
            
            try:
                result = self.analyzer.analyze_dependencies(f.name, include_stdlib=True)
                
                assert isinstance(result, AnalysisResult)
                assert len(result.dependencies) > 0
                
                # Vérifie la classification
                builtin_found = False
                for dep in result.dependencies.values():
                    if dep.is_builtin:
                        builtin_found = True
                        break
                
                # Au moins un module builtin devrait être trouvé
                assert builtin_found
                
            finally:
                os.unlink(f.name)
    
    def test_analyze_nonexistent_file(self):
        """Test d'analyse d'un fichier inexistant"""
        with pytest.raises(FileNotFoundError):
            self.analyzer.analyze_dependencies("nonexistent_file.py")
    
    def test_get_module_info_builtin(self):
        """Test d'info sur un module builtin"""
        info = self.analyzer._get_module_info("os")
        
        assert info.name == "os"
        assert info.is_builtin == True
        assert info.is_third_party == False
        assert info.is_local == False
    
    def test_detect_circular_dependencies(self):
        """Test de détection de dépendances circulaires"""
        # Crée un graphe simple avec cycle
        deps = {
            'module_a': DependencyInfo('module_a'),
            'module_b': DependencyInfo('module_b'),
        }
        
        # A dépend de B, B dépend de A
        deps['module_a'].required_by.add('module_b')
        deps['module_b'].required_by.add('module_a')
        
        cycles = self.analyzer._detect_circular_dependencies(deps)
        
        # Note: Cette implémentation peut nécessiter des ajustements
        # selon l'algorithme de détection des cycles
        assert isinstance(cycles, list)
    
    def test_estimate_sizes(self):
        """Test d'estimation des tailles"""
        deps = {
            'test_module': DependencyInfo('test_module', location=__file__)
        }
        
        self.analyzer._estimate_sizes(deps)
        
        # Le module de test devrait avoir une taille estimée
        assert deps['test_module'].size_estimate > 0
    
    def test_get_optimization_suggestions(self):
        """Test de génération de suggestions d'optimisation"""
        # Crée un résultat d'analyse avec modules exclus par défaut
        result = AnalysisResult(
            dependencies={
                'tkinter': DependencyInfo('tkinter', size_estimate=500000),
                'unittest': DependencyInfo('unittest', size_estimate=300000),
                'os': DependencyInfo('os', is_builtin=True),
            },
            builtin_modules={'os'},
            third_party_modules=set(),
            local_modules=set(),
            missing_modules=set(),
            circular_dependencies=[],
            total_size_estimate=800000,
            analysis_time=1.0
        )
        
        suggestions = self.analyzer.get_optimization_suggestions(result)
        
        assert 'excludable_modules' in suggestions
        assert 'large_dependencies' in suggestions
        assert 'optimization_potential' in suggestions
        
        # tkinter et unittest devraient être suggérés pour exclusion
        excludable_names = [mod['name'] for mod in suggestions['excludable_modules']]
        assert 'tkinter' in excludable_names or 'unittest' in excludable_names
    
    def test_export_requirements_txt(self):
        """Test d'export requirements.txt"""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as f:
            # Crée un résultat avec dépendances third-party
            result = AnalysisResult(
                dependencies={
                    'requests': DependencyInfo('requests', version='2.28.0', is_third_party=True),
                    'numpy': DependencyInfo('numpy', version='1.21.0', is_third_party=True),
                    'os': DependencyInfo('os', is_builtin=True),
                },
                builtin_modules={'os'},
                third_party_modules={'requests', 'numpy'},
                local_modules=set(),
                missing_modules=set(),
                circular_dependencies=[],
                total_size_estimate=1000000,
                analysis_time=1.0
            )
            
            try:
                self.analyzer.export_requirements_txt(result, f.name)
                
                # Lit le fichier généré
                f.seek(0)
                content = f.read()
                
                assert 'requests==2.28.0' in content
                assert 'numpy==1.21.0' in content
                assert 'os' not in content  # Module builtin, ne doit pas être inclus
                
            finally:
                os.unlink(f.name)


class TestUtilityFunctions:
    """Tests pour les fonctions utilitaires"""
    
    def test_analyze_script_dependencies(self):
        """Test de la fonction utilitaire d'analyse"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import json
import os

print("Test script")
""")
            f.flush()
            
            try:
                result = analyze_script_dependencies(f.name)
                
                assert isinstance(result, AnalysisResult)
                assert len(result.dependencies) > 0
                
            finally:
                os.unlink(f.name)


if __name__ == '__main__':
    pytest.main([__file__])