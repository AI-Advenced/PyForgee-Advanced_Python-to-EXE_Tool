#!/usr/bin/env python3
"""
Analyseur de dépendances intelligent pour PyForgee
Analyse statique et dynamique des dépendances Python
"""

import ast
import os
import sys
import importlib
import importlib.util
import pkgutil
import subprocess
import logging
import re
from pathlib import Path
from typing import Set, Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from importlib.metadata import version, PackageNotFoundError, distributions


@dataclass
class DependencyInfo:
    """Informations sur une dépendance"""
    name: str
    version: Optional[str] = None
    location: Optional[str] = None
    is_builtin: bool = False
    is_local: bool = False
    is_third_party: bool = False
    size_estimate: int = 0
    required_by: Set[str] = field(default_factory=set)
    imports: Set[str] = field(default_factory=set)
    sub_dependencies: Set[str] = field(default_factory=set)


@dataclass 
class AnalysisResult:
    """Résultat de l'analyse de dépendances"""
    dependencies: Dict[str, DependencyInfo]
    builtin_modules: Set[str]
    third_party_modules: Set[str]
    local_modules: Set[str]
    missing_modules: Set[str]
    circular_dependencies: List[List[str]]
    total_size_estimate: int
    analysis_time: float
    warnings: List[str] = field(default_factory=list)


class DependencyAnalyzer:
    """Analyseur de dépendances intelligent"""
    
    def __init__(self):
        self.logger = logging.getLogger("PyForgee.dependency_analyzer")
        self._builtin_modules = set(sys.builtin_module_names)
        self._stdlib_modules = self._get_stdlib_modules()
        self._analysis_cache = {}

        self.default_excludes = {
            'test', 'tests', 'unittest', 'doctest', 'pdb', 'pydoc',
            'tkinter', 'turtle', 'turtledemo',
            'ftplib', 'imaplib', 'poplib', 'smtplib', 'telnetlib',
            'socketserver', 'wsgiref', 'xmlrpc',
            'distutils', 'lib2to3', 'ensurepip',
            'sqlite3', 'dbm', 'shelve'
        }
    
    def _get_stdlib_modules(self) -> Set[str]:
        stdlib_modules = set()
        stdlib_modules.update(sys.builtin_module_names)
        try:
            stdlib_path = Path(sys.executable).parent.parent / "Lib"
            if stdlib_path.exists():
                for item in stdlib_path.iterdir():
                    if item.is_file() and item.suffix == '.py':
                        stdlib_modules.add(item.stem)
                    elif item.is_dir() and (item / '__init__.py').exists():
                        stdlib_modules.add(item.name)
        except Exception as e:
            self.logger.warning(f"Erreur lors de la détection de la stdlib: {e}")
        return stdlib_modules
    
    def analyze_dependencies(self, script_path: str, 
                           include_stdlib: bool = False,
                           deep_analysis: bool = True) -> AnalysisResult:
        """
        Analyse complète des dépendances d'un script
        
        Args:
            script_path: Chemin vers le script à analyser
            include_stdlib: Inclure les modules de la bibliothèque standard
            deep_analysis: Effectuer une analyse récursive profonde
        """
        import time
        start_time = time.time()
        
        self.logger.info(f"Analyse des dépendances de: {script_path}")
        
        # Validation
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script non trouvé: {script_path}")
        
        try:
            # Analyse statique
            static_deps = self._static_analysis(script_path, deep_analysis)
            
            # Analyse dynamique (optionnelle)
            dynamic_deps = self._dynamic_analysis(script_path)
            
            # Fusion des résultats
            all_deps = self._merge_dependencies(static_deps, dynamic_deps)
            
            # Classification des dépendances
            classified = self._classify_dependencies(all_deps, include_stdlib)
            
            # Détection des dépendances circulaires
            circular = self._detect_circular_dependencies(classified)
            
            # Estimation des tailles
            self._estimate_sizes(classified)
            
            # Calcul des statistiques
            total_size = sum(dep.size_estimate for dep in classified.values())
            
            analysis_time = time.time() - start_time
            
            result = AnalysisResult(
                dependencies=classified,
                builtin_modules={name for name, dep in classified.items() if dep.is_builtin},
                third_party_modules={name for name, dep in classified.items() if dep.is_third_party},
                local_modules={name for name, dep in classified.items() if dep.is_local},
                missing_modules=set(),  # À implémenter si nécessaire
                circular_dependencies=circular,
                total_size_estimate=total_size,
                analysis_time=analysis_time
            )
            
            self.logger.info(f"Analyse terminée en {analysis_time:.2f}s")
            self.logger.info(f"Dépendances trouvées: {len(classified)}")
            
            return result
            
        except Exception as e:
            self.logger.exception("Erreur lors de l'analyse des dépendances")
            raise
    
    def _static_analysis(self, script_path: str, deep: bool = True) -> Dict[str, Set[str]]:
        """Analyse statique du code source"""
        
        dependencies = defaultdict(set)
        analyzed_files = set()
        
        def analyze_file(file_path: str, parent: Optional[str] = None):
            if file_path in analyzed_files:
                return
            
            analyzed_files.add(file_path)
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Parse AST
                tree = ast.parse(content, filename=file_path)
                
                # Visite de l'AST
                visitor = ImportVisitor()
                visitor.visit(tree)
                
                current_module = parent or Path(file_path).stem
                
                for imp in visitor.imports:
                    dependencies[current_module].add(imp)
                
                # Analyse récursive des imports locaux
                if deep:
                    for imp in visitor.imports:
                        local_path = self._resolve_local_import(imp, file_path)
                        if local_path and local_path not in analyzed_files:
                            analyze_file(local_path, imp)
                            
            except Exception as e:
                self.logger.warning(f"Erreur analyse statique {file_path}: {e}")
        
        # Analyse du fichier principal
        analyze_file(script_path)
        
        return dict(dependencies)
    
    def _dynamic_analysis(self, script_path: str) -> Dict[str, Set[str]]:
        """Analyse dynamique par exécution contrôlée"""
        
        dependencies = defaultdict(set)
        
        try:
            # Code d'instrumentation
            instrumentation_code = '''
import sys
import importlib
import importlib.util

original_import = __import__
imported_modules = set()

def traced_import(name, globals=None, locals=None, fromlist=(), level=0):
    imported_modules.add(name.split('.')[0])
    return original_import(name, globals, locals, fromlist, level)

__builtins__['__import__'] = traced_import

# Exécution du script original
exec(compile(open(r"{script_path}").read(), r"{script_path}", 'exec'))

# Affichage des modules importés
for module in imported_modules:
    print(f"IMPORTED: {{module}}")
'''.format(script_path=script_path.replace('\\', '\\\\'))
            
            # Exécution dans un processus séparé
            result = subprocess.run(
                [sys.executable, '-c', instrumentation_code],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.dirname(script_path)
            )
            
            if result.returncode == 0:
                # Parse des résultats
                for line in result.stdout.split('\n'):
                    if line.startswith('IMPORTED: '):
                        module = line[10:].strip()
                        dependencies['__main__'].add(module)
            else:
                self.logger.warning("L'analyse dynamique a échoué")
                
        except Exception as e:
            self.logger.warning(f"Erreur analyse dynamique: {e}")
        
        return dict(dependencies)
    
    def _resolve_local_import(self, module_name: str, current_file: str) -> Optional[str]:
        """Résout un import local vers un chemin de fichier"""
        
        current_dir = Path(current_file).parent
        
        # Essaye différents formats
        possible_paths = [
            current_dir / f"{module_name}.py",
            current_dir / module_name / "__init__.py",
            current_dir.parent / f"{module_name}.py",
            current_dir.parent / module_name / "__init__.py",
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def _merge_dependencies(self, static: Dict[str, Set[str]], 
                           dynamic: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
        """Fusionne les résultats d'analyse statique et dynamique"""
        
        merged = defaultdict(set)
        
        # Ajoute les dépendances statiques
        for module, deps in static.items():
            merged[module].update(deps)
        
        # Ajoute les dépendances dynamiques
        for module, deps in dynamic.items():
            merged[module].update(deps)
        
        return dict(merged)
    
    def _classify_dependencies(self, dependencies: Dict[str, Set[str]], 
                             include_stdlib: bool) -> Dict[str, DependencyInfo]:
        """Classifie les dépendances par type"""
        
        classified = {}
        all_modules = set()
        
        # Collecte tous les modules
        for module_deps in dependencies.values():
            all_modules.update(module_deps)
        
        # Classifie chaque module
        for module in all_modules:
            info = self._get_module_info(module)
            
            # Filtre les modules stdlib si demandé
            if not include_stdlib and info.is_builtin:
                continue
                
            classified[module] = info
        
        # Ajoute les relations de dépendance
        for parent, deps in dependencies.items():
            for dep in deps:
                if dep in classified:
                    classified[dep].required_by.add(parent)
        
        return classified
    

    def _get_module_info(self, module_name: str) -> DependencyInfo:
        """Obtient les informations détaillées d'un module"""
        info = DependencyInfo(name=module_name)

        try:
            if module_name in self._builtin_modules or module_name in self._stdlib_modules:
                info.is_builtin = True
                return info

            spec = importlib.util.find_spec(module_name)
            if spec is None:
                return info

            info.location = spec.origin
            if spec.origin:
                path = Path(spec.origin)
                if 'site-packages' not in str(path):
                    info.is_local = True
                else:
                    info.is_third_party = True
                    try:
                        info.version = version(module_name)
                    except PackageNotFoundError:
                        info.version = None
        except Exception as e:
            self.logger.debug(f"Erreur info module {module_name}: {e}")
        
        return info
    
    def _detect_circular_dependencies(self, dependencies: Dict[str, DependencyInfo]) -> List[List[str]]:
        """Détecte les dépendances circulaires"""
        
        # Construit le graphe de dépendances
        graph = {}
        for name, info in dependencies.items():
            graph[name] = list(info.required_by)
        
        # Détecte les cycles avec DFS
        def find_cycles():
            visited = set()
            rec_stack = set()
            cycles = []
            
            def dfs(node, path):
                if node in rec_stack:
                    # Cycle trouvé
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:] + [node]
                    cycles.append(cycle)
                    return
                
                if node in visited:
                    return
                
                visited.add(node)
                rec_stack.add(node)
                
                for neighbor in graph.get(node, []):
                    dfs(neighbor, path + [neighbor])
                
                rec_stack.remove(node)
            
            for node in graph:
                if node not in visited:
                    dfs(node, [node])
            
            return cycles
        
        return find_cycles()
    
    def _estimate_sizes(self, dependencies: Dict[str, DependencyInfo]):
        """Estime la taille des dépendances"""
        
        for name, info in dependencies.items():
            try:
                if info.location and os.path.exists(info.location):
                    # Taille du fichier principal
                    size = os.path.getsize(info.location)
                    
                    # Si c'est un package, ajoute la taille du dossier
                    if info.location.endswith('__init__.py'):
                        package_dir = Path(info.location).parent
                        size += self._get_directory_size(package_dir)
                    
                    info.size_estimate = size
                else:
                    # Estimation par défaut basée sur le type
                    if info.is_builtin:
                        info.size_estimate = 1024  # Très petit
                    elif info.is_third_party:
                        info.size_estimate = 50 * 1024  # 50KB par défaut
                    else:
                        info.size_estimate = 5 * 1024   # 5KB par défaut
                        
            except Exception as e:
                self.logger.debug(f"Erreur estimation taille {name}: {e}")
                info.size_estimate = 1024
    
    def _get_directory_size(self, directory: Path, max_depth: int = 2) -> int:
        """Calcule la taille d'un répertoire (avec limite de profondeur)"""
        
        total_size = 0
        try:
            for root, dirs, files in os.walk(directory):
                # Limite la profondeur
                level = root.replace(str(directory), '').count(os.sep)
                if level >= max_depth:
                    dirs[:] = []  # Ne pas descendre plus profond
                
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                    except:
                        continue
        except:
            pass
            
        return total_size
    
    def get_optimization_suggestions(self, result: AnalysisResult) -> Dict[str, Any]:
        """Génère des suggestions d'optimisation"""
        
        suggestions = {
            'excludable_modules': [],
            'large_dependencies': [],
            'unused_stdlib': [],
            'optimization_potential': 0
        }
        
        # Modules potentiellement exclus
        for name, info in result.dependencies.items():
            if name in self.default_excludes:
                suggestions['excludable_modules'].append({
                    'name': name,
                    'size': info.size_estimate,
                    'reason': 'Module rarement nécessaire en production'
                })
        
        # Grosses dépendances
        large_deps = sorted(
            [(name, info) for name, info in result.dependencies.items()],
            key=lambda x: x[1].size_estimate,
            reverse=True
        )[:10]
        
        for name, info in large_deps:
            if info.size_estimate > 100 * 1024:  # > 100KB
                suggestions['large_dependencies'].append({
                    'name': name,
                    'size': info.size_estimate,
                    'type': 'third_party' if info.is_third_party else 'local'
                })
        
        # Calcul du potentiel d'optimisation
        excludable_size = sum(
            result.dependencies[name].size_estimate 
            for name in result.dependencies 
            if name in self.default_excludes
        )
        
        suggestions['optimization_potential'] = excludable_size
        
        return suggestions
    
    def export_requirements_txt(self, result: AnalysisResult, output_path: str):
        """Exporte les dépendances vers un fichier requirements.txt"""
        
        third_party_deps = []
        
        for name, info in result.dependencies.items():
            if info.is_third_party and info.version:
                third_party_deps.append(f"{name}=={info.version}")
            elif info.is_third_party:
                third_party_deps.append(name)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(third_party_deps)))
        
        self.logger.info(f"Requirements exportées vers: {output_path}")


class ImportVisitor(ast.NodeVisitor):
    """Visiteur AST pour extraire les imports"""
    def __init__(self):
        self.imports = set()
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name.split('.')[0])
        self.generic_visit(node)
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module.split('.')[0])
        self.generic_visit(node)
    def visit_Call(self, node):
        if (isinstance(node.func, ast.Name) and node.func.id == '__import__' and 
            node.args and isinstance(node.args[0], ast.Constant)):
            self.imports.add(str(node.args[0].value).split('.')[0])
        if (isinstance(node.func, ast.Attribute) and 
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'importlib' and
            node.func.attr == 'import_module' and
            node.args and isinstance(node.args[0], ast.Constant)):
            self.imports.add(str(node.args[0].value).split('.')[0])
        self.generic_visit(node)


def analyze_script_dependencies(script_path: str, **kwargs) -> AnalysisResult:
    """Fonction utilitaire pour analyser les dépendances d'un script"""
    analyzer = DependencyAnalyzer()
    return analyzer.analyze_dependencies(script_path, **kwargs)