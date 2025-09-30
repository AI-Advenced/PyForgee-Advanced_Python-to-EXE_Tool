#!/usr/bin/env python3
"""
Moteur de compilation hybride pour PyForgee
Combine PyInstaller, Nuitka et cx_Freeze avec sélection automatique optimale
"""

import os
import sys
import subprocess
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import psutil
import yaml
from packaging import version

from ..utils.system_utils import SystemUtils
from ..utils.file_utils import FileUtils


class CompilerType(Enum):
    """Types de compilateurs disponibles"""
    PYINSTALLER = "pyinstaller"
    NUITKA = "nuitka"
    CX_FREEZE = "cx_freeze"


@dataclass
class CompilationOptions:
    """Options de compilation"""
    source_path: str
    output_path: str
    output_name: Optional[str] = None
    icon_path: Optional[str] = None
    
    # Options générales
    onefile: bool = True
    console: bool = False
    optimize: bool = True
    debug: bool = False
    
    # Exclusions
    exclude_modules: List[str] = None
    hidden_imports: List[str] = None
    
    # Compression
    upx_compress: bool = False
    upx_level: int = 9
    
    # Protection
    obfuscate: bool = False
    encrypt_bytecode: bool = False
    
    # Compilateur spécifique
    preferred_compiler: Optional[CompilerType] = None
    nuitka_standalone: bool = True
    pyinstaller_collect_all: List[str] = None
    
    def __post_init__(self):
        if self.exclude_modules is None:
            self.exclude_modules = []
        if self.hidden_imports is None:
            self.hidden_imports = []
        if self.pyinstaller_collect_all is None:
            self.pyinstaller_collect_all = []


@dataclass 
class CompilationResult:
    """Résultat d'une compilation"""
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    compilation_time: float = 0.0
    file_size: int = 0
    compiler_used: Optional[CompilerType] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class CompilerBackend(ABC):
    """Classe abstraite pour les backends de compilation"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"PyForgee.{name}")
        
    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si le compilateur est disponible"""
        pass
    
    @abstractmethod
    def get_version(self) -> Optional[str]:
        """Retourne la version du compilateur"""
        pass
        
    @abstractmethod
    async def compile(self, options: CompilationOptions) -> CompilationResult:
        """Compile le script avec ce backend"""
        pass
    
    @abstractmethod
    def get_score(self, options: CompilationOptions) -> int:
        """Retourne un score pour ce compilateur selon les options (0-100)"""
        pass


class PyInstallerBackend(CompilerBackend):
    """Backend PyInstaller"""
    
    def __init__(self):
        super().__init__("pyinstaller")
        
    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["pyinstaller", "--version"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def get_version(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["pyinstaller", "--version"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return None
    
    async def compile(self, options: CompilationOptions) -> CompilationResult:
        """Compilation avec PyInstaller"""
        import time
        start_time = time.time()
        
        try:
            # Construction de la commande
            cmd = ["pyinstaller"]
            
            # Options de base
            if options.onefile:
                cmd.append("--onefile")
            if not options.console:
                cmd.append("--windowed")
            if options.debug:
                cmd.append("--debug=all")
            else:
                cmd.append("--log-level=WARN")
                
            # Icône
            if options.icon_path and os.path.exists(str(options.icon_path)):
                cmd.extend(["--icon", str(options.icon_path)])
                
            # Output
            name = options.output_name or Path(str(options.output_path)).stem
            cmd.extend(["--name", name])

            # Le dossier parent sert de distpath
            output_str = str(options.output_path)
            dist_dir = str(Path(output_str).parent if output_str.endswith(".exe") else Path(output_str))
            cmd.extend(["--distpath", dist_dir])
            
            # Exclusions
            for module in options.exclude_modules:
                cmd.extend(["--exclude-module", module])
                
            # Imports cachés
            for imp in options.hidden_imports:
                cmd.extend(["--hidden-import", imp])
                
            # Collect all
            for module in options.pyinstaller_collect_all:
                cmd.extend(["--collect-all", module])
                
            # UPX
            if options.upx_compress:
                cmd.append("--upx-compress")
                
            # Script source
            cmd.append(str(options.source_path))
            
            self.logger.info(f"Commande PyInstaller: {' '.join(cmd)}")
            
            # Exécution
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(str(options.source_path)) or "."
            )
            
            stdout, stderr = await process.communicate()
            
            compilation_time = time.time() - start_time
            
            if process.returncode == 0:
                # Recherche du fichier généré
                output_file = self._find_output_file(options)
                if output_file and os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    return CompilationResult(
                        success=True,
                        output_path=output_file,
                        compilation_time=compilation_time,
                        file_size=file_size,
                        compiler_used=CompilerType.PYINSTALLER
                    )
                else:
                    return CompilationResult(
                        success=False,
                        error_message="Fichier de sortie introuvable",
                        compilation_time=compilation_time,
                        compiler_used=CompilerType.PYINSTALLER
                    )
            else:
                return CompilationResult(
                    success=False,
                    error_message=stderr.decode('utf-8', errors='ignore'),
                    compilation_time=compilation_time,
                    compiler_used=CompilerType.PYINSTALLER
                )
                
        except Exception as e:
            return CompilationResult(
                success=False,
                error_message=str(e),
                compilation_time=time.time() - start_time,
                compiler_used=CompilerType.PYINSTALLER
            )

    def _find_output_file(self, options: CompilationOptions) -> Optional[str]:
        """Trouve le fichier de sortie généré par PyInstaller"""
        base_name = options.output_name or Path(options.source_path).stem
        
        # Essaye différents emplacements
        possible_paths = [
            os.path.join(options.output_path, f"{base_name}.exe"),
            os.path.join(options.output_path, base_name),
            os.path.join("dist", f"{base_name}.exe"),
            os.path.join("dist", base_name),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def get_score(self, options: CompilationOptions) -> int:
        """Score PyInstaller selon les options"""
        score = 70  # Score de base
        
        # Bonus pour compatibilité
        score += 15  # Très compatible
        
        # Malus pour performance
        if options.optimize:
            score -= 5
            
        # Bonus pour facilité
        score += 10
        
        return min(100, max(0, score))


class NuitkaBackend(CompilerBackend):
    """Backend Nuitka"""
    
    def __init__(self):
        super().__init__("nuitka")
        
    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["python", "-m", "nuitka", "--version"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def get_version(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["python", "-m", "nuitka", "--version"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return None
    
    async def compile(self, options: CompilationOptions) -> CompilationResult:
        """Compilation avec Nuitka"""
        import time
        start_time = time.time()
        
        try:
            # Construction de la commande
            cmd = ["python", "-m", "nuitka"]
            
            # Options de base
            if options.nuitka_standalone:
                cmd.append("--standalone")
            else:
                cmd.append("--onefile")
                
            if not options.console:
                cmd.append("--windows-disable-console")
                
            if options.optimize:
                cmd.append("--lto=yes")
                cmd.append("--optimize-for-size")
                
            # Icône
            if options.icon_path and os.path.exists(options.icon_path):
                cmd.append(f"--windows-icon-from-ico={options.icon_path}")
                
            # Output
            if options.output_name:
                cmd.append(f"--output-filename={options.output_name}")
            cmd.append(f"--output-dir={options.output_path}")
            
            # Exclusions et inclusions
            for module in options.exclude_modules:
                cmd.append(f"--nofollow-import-to={module}")
                
            for imp in options.hidden_imports:
                cmd.append(f"--include-module={imp}")
            
            # Optimisations Nuitka spécifiques
            cmd.extend([
                "--assume-yes-for-downloads",
                "--remove-output",
                "--no-progress-bar"
            ])
            
            # Script source
            cmd.append(options.source_path)
            
            self.logger.info(f"Commande Nuitka: {' '.join(cmd)}")
            
            # Exécution
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(options.source_path) or "."
            )
            
            stdout, stderr = await process.communicate()
            
            compilation_time = time.time() - start_time
            
            if process.returncode == 0:
                # Recherche du fichier généré
                output_file = self._find_output_file(options)
                if output_file and os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    return CompilationResult(
                        success=True,
                        output_path=output_file,
                        compilation_time=compilation_time,
                        file_size=file_size,
                        compiler_used=CompilerType.NUITKA
                    )
                else:
                    return CompilationResult(
                        success=False,
                        error_message="Fichier de sortie introuvable",
                        compilation_time=compilation_time,
                        compiler_used=CompilerType.NUITKA
                    )
            else:
                return CompilationResult(
                    success=False,
                    error_message=stderr.decode('utf-8', errors='ignore'),
                    compilation_time=compilation_time,
                    compiler_used=CompilerType.NUITKA
                )
                
        except Exception as e:
            return CompilationResult(
                success=False,
                error_message=str(e),
                compilation_time=time.time() - start_time,
                compiler_used=CompilerType.NUITKA
            )
    
        def _find_output_file(self, options: CompilationOptions) -> Optional[str]:
            """Trouve le fichier de sortie généré par PyInstaller"""
            base_name = options.output_name or Path(options.source_path).stem
            dist_dir = str(Path(options.output_path).parent if options.output_path.endswith(".exe") else Path(options.output_path))
        
            possible_paths = [
                os.path.join(dist_dir, f"{base_name}.exe"),                     # distpath/base.exe
                os.path.join(dist_dir, base_name, f"{base_name}.exe"),          # distpath/base/base.exe (cas fréquent)
                os.path.join(dist_dir, base_name),                              # distpath/base
                os.path.join("dist", f"{base_name}.exe"),                       # fallback
                os.path.join("dist", base_name, f"{base_name}.exe"),            # fallback
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    return path
            return None

    def get_score(self, options: CompilationOptions) -> int:
        """Score Nuitka selon les options"""
        score = 85  # Score de base élevé
        
        # Bonus pour optimisation
        if options.optimize:
            score += 10
            
        # Bonus pour protection
        if options.obfuscate or options.encrypt_bytecode:
            score += 5
            
        # Malus pour compatibilité
        score -= 5
        
        return min(100, max(0, score))


class CxFreezeBackend(CompilerBackend):
    """Backend cx_Freeze"""
    
    def __init__(self):
        super().__init__("cx_freeze")
        
    def is_available(self) -> bool:
        try:
            import cx_Freeze
            return True
        except ImportError:
            return False
    
    def get_version(self) -> Optional[str]:
        try:
            import cx_Freeze
            return cx_Freeze.__version__
        except ImportError:
            return None
    
    async def compile(self, options: CompilationOptions) -> CompilationResult:
        """Compilation avec cx_Freeze"""
        import time
        start_time = time.time()
        
        try:
            # cx_Freeze utilise un setup.py temporaire
            setup_content = self._generate_setup_script(options)
            setup_path = os.path.join(
                os.path.dirname(options.source_path), 
                "temp_setup.py"
            )
            
            # Écrire le setup temporaire
            with open(setup_path, 'w', encoding='utf-8') as f:
                f.write(setup_content)
            
            try:
                # Construction de la commande
                cmd = [
                    sys.executable, 
                    setup_path, 
                    "build_exe",
                    f"--build-exe={options.output_path}"
                ]
                
                self.logger.info(f"Commande cx_Freeze: {' '.join(cmd)}")
                
                # Exécution
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=os.path.dirname(options.source_path) or "."
                )
                
                stdout, stderr = await process.communicate()
                
                compilation_time = time.time() - start_time
                
                if process.returncode == 0:
                    # Recherche du fichier généré
                    output_file = self._find_output_file(options)
                    if output_file and os.path.exists(output_file):
                        file_size = os.path.getsize(output_file)
                        return CompilationResult(
                            success=True,
                            output_path=output_file,
                            compilation_time=compilation_time,
                            file_size=file_size,
                            compiler_used=CompilerType.CX_FREEZE
                        )
                    else:
                        return CompilationResult(
                            success=False,
                            error_message="Fichier de sortie introuvable",
                            compilation_time=compilation_time,
                            compiler_used=CompilerType.CX_FREEZE
                        )
                else:
                    return CompilationResult(
                        success=False,
                        error_message=stderr.decode('utf-8', errors='ignore'),
                        compilation_time=compilation_time,
                        compiler_used=CompilerType.CX_FREEZE
                    )
                    
            finally:
                # Nettoyer le setup temporaire
                if os.path.exists(setup_path):
                    os.remove(setup_path)
                    
        except Exception as e:
            return CompilationResult(
                success=False,
                error_message=str(e),
                compilation_time=time.time() - start_time,
                compiler_used=CompilerType.CX_FREEZE
            )
    
    def _generate_setup_script(self, options: CompilationOptions) -> str:
        """Génère un script setup.py pour cx_Freeze"""
        base_name = options.output_name or Path(options.source_path).stem
        
        setup_content = f'''
import sys
from cx_Freeze import setup, Executable

# Options de build
build_options = {{
    "packages": [],
    "excludes": {options.exclude_modules},
    "includes": {options.hidden_imports},
    "optimize": {1 if options.optimize else 0},
}}

# Options d'exécutable
exe_options = {{
    "target_name": "{base_name}.exe" if sys.platform == "win32" else "{base_name}",
}}

if "{options.icon_path}" and sys.platform == "win32":
    exe_options["icon"] = "{options.icon_path}"

executables = [
    Executable(
        "{options.source_path}",
        base="Win32GUI" if not {options.console} and sys.platform == "win32" else None,
        **exe_options
    )
]

setup(
    name="{base_name}",
    version="1.0",
    options={{"build_exe": build_options}},
    executables=executables,
)
'''
        return setup_content
    
    def _find_output_file(self, options: CompilationOptions) -> Optional[str]:
        """Trouve le fichier de sortie généré par cx_Freeze"""
        base_name = options.output_name or Path(options.source_path).stem
        
        possible_paths = [
            os.path.join(options.output_path, f"{base_name}.exe"),
            os.path.join(options.output_path, base_name),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def get_score(self, options: CompilationOptions) -> int:
        """Score cx_Freeze selon les options"""
        score = 60  # Score de base moyen
        
        # Bonus pour simplicité
        score += 5
        
        # Malus pour fonctionnalités limitées
        if options.obfuscate or options.encrypt_bytecode:
            score -= 10
            
        return min(100, max(0, score))


class CompilerEngine:
    """Moteur de compilation hybride principal"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("PyForgee.engine")
        
        # Initialisation des backends
        self.compilers = {
            CompilerType.PYINSTALLER: PyInstallerBackend(),
            CompilerType.NUITKA: NuitkaBackend(), 
            CompilerType.CX_FREEZE: CxFreezeBackend(),
        }
        
        self.available_compilers = self._detect_compilers()
        self.logger.info(f"Compilateurs disponibles: {list(self.available_compilers.keys())}")
    
    def _detect_compilers(self) -> Dict[CompilerType, CompilerBackend]:
        """Détecte les compilateurs disponibles"""
        available = {}
        
        for compiler_type, backend in self.compilers.items():
            if backend.is_available():
                version = backend.get_version()
                self.logger.info(f"{compiler_type.value} disponible: {version}")
                available[compiler_type] = backend
            else:
                self.logger.warning(f"{compiler_type.value} non disponible")
                
        return available
    
    def select_best_compiler(self, options: CompilationOptions) -> Tuple[CompilerType, CompilerBackend]:
        """Sélectionne le meilleur compilateur selon les options"""
        
        # Si un compilateur est spécifiquement demandé
        if (options.preferred_compiler and 
            options.preferred_compiler in self.available_compilers):
            return options.preferred_compiler, self.available_compilers[options.preferred_compiler]
        
        # Sinon, calcule les scores
        scores = {}
        for compiler_type, backend in self.available_compilers.items():
            score = backend.get_score(options)
            scores[compiler_type] = score
            self.logger.debug(f"Score {compiler_type.value}: {score}")
        
        if not scores:
            raise RuntimeError("Aucun compilateur disponible")
        
        # Sélectionne le meilleur score
        best_compiler = max(scores.keys(), key=lambda k: scores[k])
        best_backend = self.available_compilers[best_compiler]
        
        self.logger.info(f"Compilateur sélectionné: {best_compiler.value} (score: {scores[best_compiler]})")
        return best_compiler, best_backend
    
    async def compile(self, options: CompilationOptions) -> CompilationResult:
        """Compile un script Python en exécutable"""
        
        # Validation des entrées
        if not os.path.exists(options.source_path):
            return CompilationResult(
                success=False,
                error_message=f"Fichier source introuvable: {options.source_path}"
            )
        
        # Création du dossier de sortie
        os.makedirs(options.output_path, exist_ok=True)
        
        try:
            # Sélection du compilateur
            compiler_type, backend = self.select_best_compiler(options)
            
            # Compilation
            self.logger.info(f"Début de la compilation avec {compiler_type.value}")
            result = await backend.compile(options)
            
            if result.success:
                self.logger.info(f"Compilation réussie: {result.output_path}")
                self.logger.info(f"Taille du fichier: {result.file_size} bytes")
                self.logger.info(f"Temps de compilation: {result.compilation_time:.2f}s")
            else:
                self.logger.error(f"Échec de la compilation: {result.error_message}")
                
            return result
            
        except Exception as e:
            self.logger.exception("Erreur lors de la compilation")
            return CompilationResult(
                success=False,
                error_message=str(e)
            )
    
    async def batch_compile(self, scripts: List[str], base_options: CompilationOptions) -> List[CompilationResult]:
        """Compile plusieurs scripts en parallèle"""
        
        tasks = []
        for script in scripts:
            # Copie des options pour chaque script
            options = CompilationOptions(
                source_path=script,
                output_path=base_options.output_path,
                **{k: v for k, v in base_options.__dict__.items() 
                   if k not in ['source_path', 'output_path']}
            )
            tasks.append(self.compile(options))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traite les exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(CompilationResult(
                    success=False,
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
                
        return final_results
    
    def get_compiler_info(self) -> Dict[str, Any]:
        """Retourne des informations sur les compilateurs disponibles"""
        info = {}
        
        for compiler_type, backend in self.compilers.items():
            info[compiler_type.value] = {
                "available": backend.is_available(),
                "version": backend.get_version() if backend.is_available() else None,
                "description": f"Backend {compiler_type.value}"
            }
            
        return info


# Configuration par défaut
DEFAULT_OPTIMIZATION_CONFIG = {
    'exclude_modules': [
        'tkinter', 'unittest', 'doctest', 'pdb', 'pydoc',
        'sqlite3', 'ssl', 'email', 'xml', 'xmlrpc',
        'http', 'urllib', 'ftplib', 'imaplib', 'poplib',
        'smtplib', 'telnetlib', 'socketserver', 'wsgiref',
        'distutils', 'test', 'lib2to3', 'turtledemo'
    ],
    'compression': {
        'method': 'upx',
        'level': 9,
        'preserve_resources': True
    },
    'bundle_optimization': True,
    'size_optimization': True,
    'speed_optimization': False
}


def create_default_options(source_path: str, output_path: str = "./dist") -> CompilationOptions:
    """Crée des options de compilation par défaut optimisées"""
    
    return CompilationOptions(
        source_path=source_path,
        output_path=output_path,
        onefile=True,
        console=False,
        optimize=True,
        exclude_modules=DEFAULT_OPTIMIZATION_CONFIG['exclude_modules'].copy(),
        upx_compress=True,
        upx_level=9
    )