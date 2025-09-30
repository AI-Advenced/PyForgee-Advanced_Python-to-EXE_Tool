#!/usr/bin/env python3
"""
Gestionnaire de protection du code pour PyForgee
Obfuscation, chiffrement et protection anti-debugging
"""

import os
import sys
import ast
import subprocess
import tempfile
import shutil
import logging
import hashlib
import base64
import random
import string
import keyword
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple, Set
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import marshal
import py_compile
import importlib.util

# Imports conditionnels
try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    from Crypto.Protocol.KDF import PBKDF2
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class ProtectionLevel(Enum):
    """Niveaux de protection disponibles"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"  
    ADVANCED = "advanced"
    MAXIMUM = "maximum"


class ObfuscationMethod(Enum):
    """Méthodes d'obfuscation"""
    PYARMOR = "pyarmor"
    CUSTOM = "custom"
    BYTECODE = "bytecode"
    STRING_ENCODING = "string_encoding"
    CONTROL_FLOW = "control_flow"


@dataclass
class ProtectionOptions:
    """Options de protection"""
    level: ProtectionLevel = ProtectionLevel.INTERMEDIATE
    methods: List[ObfuscationMethod] = field(default_factory=list)
    
    # Options générales
    obfuscate_names: bool = True
    obfuscate_strings: bool = True
    encrypt_bytecode: bool = False
    add_anti_debug: bool = False
    
    # Options PyArmor
    use_pyarmor: bool = False
    pyarmor_license: Optional[str] = None
    pyarmor_exclude: List[str] = field(default_factory=list)
    
    # Options personnalisées
    custom_key: Optional[str] = None
    preserve_docstrings: bool = False
    obfuscation_depth: int = 3
    
    # Anti-debugging
    detect_debugger: bool = False
    detect_vm: bool = False
    integrity_check: bool = False
    
    def __post_init__(self):
        if not self.methods:
            # Méthodes par défaut selon le niveau
            if self.level == ProtectionLevel.BASIC:
                self.methods = [ObfuscationMethod.BYTECODE]
            elif self.level == ProtectionLevel.INTERMEDIATE:
                self.methods = [ObfuscationMethod.CUSTOM, ObfuscationMethod.STRING_ENCODING]
            elif self.level == ProtectionLevel.ADVANCED:
                self.methods = [
                    ObfuscationMethod.CUSTOM, 
                    ObfuscationMethod.STRING_ENCODING,
                    ObfuscationMethod.CONTROL_FLOW
                ]
            else:  # MAXIMUM
                self.methods = [
                    ObfuscationMethod.PYARMOR,
                    ObfuscationMethod.CUSTOM,
                    ObfuscationMethod.BYTECODE,
                    ObfuscationMethod.STRING_ENCODING,
                    ObfuscationMethod.CONTROL_FLOW
                ]


@dataclass
class ProtectionResult:
    """Résultat de la protection"""
    success: bool
    protected_files: Dict[str, str] = field(default_factory=dict)  # original -> protected
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    protection_time: float = 0.0
    methods_applied: List[ObfuscationMethod] = field(default_factory=list)
    entropy_increase: float = 0.0


class ProtectionBackend(ABC):
    """Classe abstraite pour les backends de protection"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"PyForgee.protection.{name}")
    
    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si ce backend est disponible"""
        pass
    
    @abstractmethod
    def get_version(self) -> Optional[str]:
        """Retourne la version du protecteur"""
        pass
    
    @abstractmethod
    async def protect(self, source_path: str, options: ProtectionOptions) -> ProtectionResult:
        """Protège un fichier/dossier source"""
        pass
    
    @abstractmethod
    def get_score(self, source_path: str, options: ProtectionOptions) -> int:
        """Retourne un score pour ce protecteur (0-100)"""
        pass


class PyArmorProtector(ProtectionBackend):
    """Protecteur PyArmor professionnel"""
    
    def __init__(self):
        super().__init__("pyarmor")
        self._pyarmor_path = self._find_pyarmor()
    
    def _find_pyarmor(self) -> Optional[str]:
        """Trouve l'exécutable PyArmor"""
        try:
            result = subprocess.run(
                ["pyarmor", "--version"],
                capture_output=True,
                timeout=10
            )
            return "pyarmor" if result.returncode == 0 else None
        except:
            return None
    
    def is_available(self) -> bool:
        """Vérifie si PyArmor est disponible"""
        return self._pyarmor_path is not None
    
    def get_version(self) -> Optional[str]:
        """Version PyArmor"""
        if not self._pyarmor_path:
            return None
        
        try:
            result = subprocess.run(
                [self._pyarmor_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None
    
    async def protect(self, source_path: str, options: ProtectionOptions) -> ProtectionResult:
        """Protection avec PyArmor"""
        import time
        import asyncio
        
        start_time = time.time()
        
        if not self._pyarmor_path:
            return ProtectionResult(
                success=False,
                error_message="PyArmor non disponible"
            )
        
        try:
            # Création d'un dossier temporaire pour PyArmor
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = os.path.join(temp_dir, "protected")
                
                # Construction de la commande PyArmor
                cmd = [
                    self._pyarmor_path, 
                    "obfuscate",
                    "--output-dir", output_dir
                ]
                
                # Options selon le niveau de protection
                if options.level in [ProtectionLevel.ADVANCED, ProtectionLevel.MAXIMUM]:
                    cmd.extend(["--advanced", "1"])
                    
                if options.add_anti_debug:
                    cmd.extend(["--restrict", "1"])
                
                # Exclusions
                for exclude in options.pyarmor_exclude:
                    cmd.extend(["--exclude", exclude])
                
                # Fichier/dossier source
                cmd.append(source_path)
                
                self.logger.info(f"Commande PyArmor: {' '.join(cmd)}")
                
                # Exécution
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=os.path.dirname(source_path) or "."
                )
                
                stdout, stderr = await process.communicate()
                
                protection_time = time.time() - start_time
                
                if process.returncode == 0:
                    # Copie des fichiers protégés
                    protected_files = {}
                    
                    if os.path.isfile(source_path):
                        # Fichier unique
                        basename = os.path.basename(source_path)
                        protected_path = os.path.join(output_dir, basename)
                        
                        if os.path.exists(protected_path):
                            final_path = f"{source_path}.protected"
                            shutil.copy2(protected_path, final_path)
                            protected_files[source_path] = final_path
                    else:
                        # Dossier complet
                        for root, dirs, files in os.walk(output_dir):
                            for file in files:
                                if file.endswith('.py'):
                                    src = os.path.join(root, file)
                                    rel_path = os.path.relpath(src, output_dir)
                                    dst = os.path.join(os.path.dirname(source_path), f"{rel_path}.protected")
                                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                                    shutil.copy2(src, dst)
                                    protected_files[os.path.join(source_path, rel_path)] = dst
                    
                    return ProtectionResult(
                        success=True,
                        protected_files=protected_files,
                        protection_time=protection_time,
                        methods_applied=[ObfuscationMethod.PYARMOR]
                    )
                else:
                    return ProtectionResult(
                        success=False,
                        error_message=stderr.decode('utf-8', errors='ignore'),
                        protection_time=protection_time
                    )
                    
        except Exception as e:
            return ProtectionResult(
                success=False,
                error_message=str(e),
                protection_time=time.time() - start_time
            )
    
    def get_score(self, source_path: str, options: ProtectionOptions) -> int:
        """Score PyArmor"""
        score = 90  # Très bon score
        
        # Bonus pour niveaux élevés
        if options.level in [ProtectionLevel.ADVANCED, ProtectionLevel.MAXIMUM]:
            score += 10
        
        return min(100, score)


class CustomObfuscator(ProtectionBackend):
    """Obfuscateur personnalisé PyForgee"""
    
    def __init__(self):
        super().__init__("custom")
        self._name_mappings = {}
        self._string_mappings = {}
    
    def is_available(self) -> bool:
        """Toujours disponible"""
        return True
    
    def get_version(self) -> Optional[str]:
        """Version personnalisée"""
        return "PyForgee Custom Obfuscator 1.0"
    
    async def protect(self, source_path: str, options: ProtectionOptions) -> ProtectionResult:
        """Obfuscation personnalisée"""
        import time
        
        start_time = time.time()
        
        try:
            protected_files = {}
            
            if os.path.isfile(source_path):
                # Fichier unique
                result_path = await self._obfuscate_file(source_path, options)
                protected_files[source_path] = result_path
            else:
                # Dossier complet
                for root, dirs, files in os.walk(source_path):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            result_path = await self._obfuscate_file(file_path, options)
                            protected_files[file_path] = result_path
            
            protection_time = time.time() - start_time
            
            return ProtectionResult(
                success=True,
                protected_files=protected_files,
                protection_time=protection_time,
                methods_applied=[ObfuscationMethod.CUSTOM]
            )
            
        except Exception as e:
            return ProtectionResult(
                success=False,
                error_message=str(e),
                protection_time=time.time() - start_time
            )
    
    async def _obfuscate_file(self, file_path: str, options: ProtectionOptions) -> str:
        """Obfuscation d'un fichier Python"""
        
        # Lecture du code source
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()
        
        # Parse AST
        tree = ast.parse(source_code)
        
        # Transformations d'obfuscation
        if options.obfuscate_names:
            tree = self._obfuscate_names(tree)
        
        if options.obfuscate_strings:
            tree = self._obfuscate_strings(tree)
        
        if ObfuscationMethod.CONTROL_FLOW in options.methods:
            tree = self._obfuscate_control_flow(tree)
        
        # Ajout d'anti-debugging si demandé
        if options.add_anti_debug:
            tree = self._add_anti_debug_code(tree)
        
        # Génération du code obfusqué
        import astor
        try:
            obfuscated_code = astor.to_source(tree)
        except ImportError:
            # Fallback sans astor
            import ast
            obfuscated_code = ast.unparse(tree)
        
        # Écriture du fichier protégé
        output_path = f"{file_path}.obfuscated"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(obfuscated_code)
        
        return output_path
    
    def _obfuscate_names(self, tree: ast.AST) -> ast.AST:
        """Obfuscation des noms de variables et fonctions"""
        
        class NameObfuscator(ast.NodeTransformer):
            def __init__(self):
                self.name_map = {}
                self.builtin_names = set(dir(__builtins__)) | set(keyword.kwlist)
            
            def _generate_name(self, original: str) -> str:
                if original in self.name_map:
                    return self.name_map[original]
                
                # Génération d'un nom obfusqué
                while True:
                    new_name = '_' + ''.join(
                        random.choices(string.ascii_letters + string.digits, k=8)
                    )
                    if new_name not in self.builtin_names:
                        self.name_map[original] = new_name
                        return new_name
            
            def visit_FunctionDef(self, node):
                # Obfuscation des noms de fonction (sauf __main__, etc.)
                if not node.name.startswith('__') or not node.name.endswith('__'):
                    node.name = self._generate_name(node.name)
                return self.generic_visit(node)
            
            def visit_ClassDef(self, node):
                # Obfuscation des noms de classe
                if not node.name.startswith('_'):
                    node.name = self._generate_name(node.name)
                return self.generic_visit(node)
            
            def visit_Name(self, node):
                # Obfuscation des variables
                if (isinstance(node.ctx, ast.Store) and 
                    node.id not in self.builtin_names and
                    not node.id.startswith('__')):
                    node.id = self._generate_name(node.id)
                return node
        
        obfuscator = NameObfuscator()
        return obfuscator.visit(tree)
    
    def _obfuscate_strings(self, tree: ast.AST) -> ast.AST:
        """Obfuscation des chaînes de caractères"""
        
        class StringObfuscator(ast.NodeTransformer):
            def visit_Constant(self, node):
                if isinstance(node.value, str) and len(node.value) > 3:
                    # Encodage Base64 simple
                    encoded = base64.b64encode(node.value.encode()).decode()
                    
                    # Création d'un appel de décodage
                    decode_call = ast.Call(
                        func=ast.Attribute(
                            value=ast.Attribute(
                                value=ast.Name(id='base64', ctx=ast.Load()),
                                attr='b64decode',
                                ctx=ast.Load()
                            ),
                            attr='decode',
                            ctx=ast.Load()
                        ),
                        args=[ast.Constant(value=encoded)],
                        keywords=[]
                    )
                    
                    return decode_call
                return node
        
        obfuscator = StringObfuscator()
        return obfuscator.visit(tree)
    
    def _obfuscate_control_flow(self, tree: ast.AST) -> ast.AST:
        """Obfuscation du flux de contrôle"""
        
        class ControlFlowObfuscator(ast.NodeTransformer):
            def visit_If(self, node):
                # Ajoute des conditions factices
                if random.random() < 0.3:  # 30% de chance
                    dummy_condition = ast.Compare(
                        left=ast.Constant(value=1),
                        ops=[ast.Eq()],
                        comparators=[ast.Constant(value=1)]
                    )
                    
                    # Combine avec la condition originale
                    new_condition = ast.BoolOp(
                        op=ast.And(),
                        values=[dummy_condition, node.test]
                    )
                    node.test = new_condition
                
                return self.generic_visit(node)
            
            def visit_For(self, node):
                # Ajoute des boucles factices imbriquées parfois
                if random.random() < 0.2:  # 20% de chance
                    dummy_loop = ast.For(
                        target=ast.Name(id='_dummy_i', ctx=ast.Store()),
                        iter=ast.Call(
                            func=ast.Name(id='range', ctx=ast.Load()),
                            args=[ast.Constant(value=1)],
                            keywords=[]
                        ),
                        body=[node],
                        orelse=[]
                    )
                    return dummy_loop
                
                return self.generic_visit(node)
        
        obfuscator = ControlFlowObfuscator()
        return obfuscator.visit(tree)
    
    def _add_anti_debug_code(self, tree: ast.AST) -> ast.AST:
        """Ajoute du code anti-debugging"""
        
        # Code de détection de débogueur
        anti_debug_code = '''
import sys
import os
import time
import threading

def _check_debugger():
    if hasattr(sys, 'gettrace') and sys.gettrace() is not None:
        os._exit(1)
    
    import ctypes
    if ctypes.windll.kernel32.IsDebuggerPresent():
        os._exit(1)

def _check_vm():
    import subprocess
    try:
        output = subprocess.check_output(['systeminfo'], shell=True)
        if b'VMware' in output or b'VirtualBox' in output:
            os._exit(1)
    except:
        pass

# Exécution des vérifications
_check_debugger()
_check_vm()

# Vérification périodique
def _periodic_check():
    while True:
        time.sleep(5)
        _check_debugger()

threading.Thread(target=_periodic_check, daemon=True).start()
'''
        
        # Parse et insertion du code anti-debug
        anti_debug_tree = ast.parse(anti_debug_code)
        
        # Insertion au début du module
        if isinstance(tree, ast.Module):
            tree.body = anti_debug_tree.body + tree.body
        
        return tree
    
    def get_score(self, source_path: str, options: ProtectionOptions) -> int:
        """Score obfuscateur personnalisé"""
        score = 75  # Bon score de base
        
        # Bonus selon les options
        if options.obfuscate_names:
            score += 5
        if options.obfuscate_strings:
            score += 5
        if options.add_anti_debug:
            score += 10
        
        return min(100, score)


class BytecodeEncryptor(ProtectionBackend):
    """Chiffreur de bytecode Python"""
    
    def __init__(self):
        super().__init__("bytecode")
    
    def is_available(self) -> bool:
        """Disponible si la crypto l'est aussi"""
        return CRYPTO_AVAILABLE
    
    def get_version(self) -> Optional[str]:
        """Version du chiffreur"""
        return "PyForgee Bytecode Encryptor 1.0" if CRYPTO_AVAILABLE else None
    
    async def protect(self, source_path: str, options: ProtectionOptions) -> ProtectionResult:
        """Chiffrement du bytecode"""
        import time
        
        if not CRYPTO_AVAILABLE:
            return ProtectionResult(
                success=False,
                error_message="Module cryptographique non disponible"
            )
        
        start_time = time.time()
        
        try:
            protected_files = {}
            
            if os.path.isfile(source_path):
                result_path = await self._encrypt_file(source_path, options)
                protected_files[source_path] = result_path
            else:
                for root, dirs, files in os.walk(source_path):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            result_path = await self._encrypt_file(file_path, options)
                            protected_files[file_path] = result_path
            
            protection_time = time.time() - start_time
            
            return ProtectionResult(
                success=True,
                protected_files=protected_files,
                protection_time=protection_time,
                methods_applied=[ObfuscationMethod.BYTECODE]
            )
            
        except Exception as e:
            return ProtectionResult(
                success=False,
                error_message=str(e),
                protection_time=time.time() - start_time
            )
    
    async def _encrypt_file(self, file_path: str, options: ProtectionOptions) -> str:
        """Chiffre le bytecode d'un fichier"""
        
        # Compilation en bytecode
        compiled_file = f"{file_path}c"
        py_compile.compile(file_path, compiled_file, doraise=True)
        
        # Lecture du bytecode
        with open(compiled_file, 'rb') as f:
            bytecode = f.read()
        
        # Génération de clé
        key_source = options.custom_key or "PyForgee_default_key_2024"
        salt = get_random_bytes(16)
        key = PBKDF2(key_source, salt, 32, count=10000)
        
        # Chiffrement AES
        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(bytecode)
        
        # Génération du loader
        loader_code = self._generate_loader(salt, cipher.nonce, tag, ciphertext, key_source)
        
        # Écriture du fichier chiffré
        output_path = f"{file_path}.encrypted"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(loader_code)
        
        # Nettoyage
        if os.path.exists(compiled_file):
            os.remove(compiled_file)
        
        return output_path
    
    def _generate_loader(self, salt: bytes, nonce: bytes, tag: bytes, 
                        ciphertext: bytes, key_source: str) -> str:
        """Génère le code de déchiffrement"""
        
        # Encodage des données en base64
        salt_b64 = base64.b64encode(salt).decode()
        nonce_b64 = base64.b64encode(nonce).decode()
        tag_b64 = base64.b64encode(tag).decode()
        ciphertext_b64 = base64.b64encode(ciphertext).decode()
        
        loader_template = f'''
import base64
import marshal
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

# Données chiffrées
_salt = base64.b64decode('{salt_b64}')
_nonce = base64.b64decode('{nonce_b64}')
_tag = base64.b64decode('{tag_b64}')
_ciphertext = base64.b64decode('{ciphertext_b64}')

# Déchiffrement
_key = PBKDF2('{key_source}', _salt, 32, count=10000)
_cipher = AES.new(_key, AES.MODE_GCM, nonce=_nonce)
_bytecode = _cipher.decrypt_and_verify(_ciphertext, _tag)

# Exécution
exec(marshal.loads(_bytecode[16:]))  # Skip header
'''
        
        return loader_template
    
    def get_score(self, source_path: str, options: ProtectionOptions) -> int:
        """Score chiffreur bytecode"""
        if not CRYPTO_AVAILABLE:
            return 0
        
        score = 80  # Très bon pour la protection
        
        if options.encrypt_bytecode:
            score += 15
        
        return min(100, score)


class ProtectionManager:
    """Gestionnaire principal de protection"""
    
    def __init__(self):
        self.logger = logging.getLogger("PyForgee.protection")
        
        # Initialisation des protecteurs
        self.protectors = {
            ObfuscationMethod.PYARMOR: PyArmorProtector(),
            ObfuscationMethod.CUSTOM: CustomObfuscator(),
            ObfuscationMethod.BYTECODE: BytecodeEncryptor(),
        }
        
        self.available_protectors = self._detect_protectors()
        self.logger.info(f"Protecteurs disponibles: {list(self.available_protectors.keys())}")
    
    def _detect_protectors(self) -> Dict[ObfuscationMethod, ProtectionBackend]:
        """Détecte les protecteurs disponibles"""
        available = {}
        
        for method, protector in self.protectors.items():
            if protector.is_available():
                version = protector.get_version()
                self.logger.info(f"{method.value} disponible: {version}")
                available[method] = protector
            else:
                self.logger.warning(f"{method.value} non disponible")
        
        return available
    
    def select_best_protector(self, source_path: str, 
                            options: ProtectionOptions) -> Tuple[ObfuscationMethod, ProtectionBackend]:
        """Sélectionne le meilleur protecteur"""
        
        # Filtre selon les méthodes demandées
        available_methods = {
            method: protector for method, protector in self.available_protectors.items()
            if method in options.methods
        }
        
        if not available_methods:
            # Fallback sur custom si disponible
            if ObfuscationMethod.CUSTOM in self.available_protectors:
                return ObfuscationMethod.CUSTOM, self.available_protectors[ObfuscationMethod.CUSTOM]
            else:
                raise RuntimeError("Aucun protecteur disponible")
        
        # Calcul des scores
        scores = {}
        for method, protector in available_methods.items():
            score = protector.get_score(source_path, options)
            scores[method] = score
            self.logger.debug(f"Score {method.value}: {score}")
        
        # Sélection du meilleur
        best_method = max(scores.keys(), key=lambda k: scores[k])
        best_protector = available_methods[best_method]
        
        self.logger.info(f"Protecteur sélectionné: {best_method.value} (score: {scores[best_method]})")
        return best_method, best_protector
    
    async def protect_code(self, source_path: str, 
                          level: Union[ProtectionLevel, str] = ProtectionLevel.INTERMEDIATE,
                          **kwargs) -> ProtectionResult:
        """Protège du code source avec le niveau spécifié"""
        
        # Validation
        if not os.path.exists(source_path):
            return ProtectionResult(
                success=False,
                error_message=f"Fichier/dossier non trouvé: {source_path}"
            )
        
        # Création des options
        if isinstance(level, str):
            level = ProtectionLevel(level)
        
        options = ProtectionOptions(level=level, **kwargs)
        
        try:
            # Application séquentielle des protections
            current_path = source_path
            all_protected_files = {}
            all_methods = []
            total_time = 0.0
            
            for method in options.methods:
                if method in self.available_protectors:
                    protector = self.available_protectors[method]
                    
                    self.logger.info(f"Application de {method.value}")
                    result = await protector.protect(current_path, options)
                    
                    if result.success:
                        all_protected_files.update(result.protected_files)
                        all_methods.extend(result.methods_applied)
                        total_time += result.protection_time
                        
                        # Le prochain protecteur utilise les fichiers protégés
                        if result.protected_files:
                            current_path = next(iter(result.protected_files.values()))
                    else:
                        return result  # Erreur, on s'arrête
            
            return ProtectionResult(
                success=True,
                protected_files=all_protected_files,
                protection_time=total_time,
                methods_applied=all_methods
            )
            
        except Exception as e:
            self.logger.exception("Erreur lors de la protection")
            return ProtectionResult(
                success=False,
                error_message=str(e)
            )
    
    def get_protection_info(self) -> Dict[str, Any]:
        """Informations sur les protecteurs disponibles"""
        info = {}
        
        for method, protector in self.protectors.items():
            info[method.value] = {
                "available": protector.is_available(),
                "version": protector.get_version() if protector.is_available() else None,
                "description": f"Protecteur {method.value}"
            }
        
        return info


def create_protection_options(level: str = "intermediate", **kwargs) -> ProtectionOptions:
    """Crée des options de protection par défaut"""
    return ProtectionOptions(level=ProtectionLevel(level), **kwargs)