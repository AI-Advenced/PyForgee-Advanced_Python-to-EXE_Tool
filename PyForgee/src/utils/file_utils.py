#!/usr/bin/env python3
"""
Utilitaires de gestion des fichiers pour PyForgee
"""

import os
import sys
import shutil
import tempfile
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Any, Generator
import mimetypes
import stat


class FileUtils:
    """Utilitaires pour la gestion des fichiers"""
    
    def __init__(self):
        self.logger = logging.getLogger("PyForgee.file_utils")
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> str:
        """S'assure qu'un dossier existe, le crée sinon"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    @staticmethod
    def get_file_hash(file_path: str, algorithm: str = 'sha256') -> str:
        """Calcule le hash d'un fichier"""
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Retourne la taille d'un fichier en bytes"""
        return os.path.getsize(file_path)
    
    @staticmethod
    def get_directory_size(directory: str, follow_symlinks: bool = False) -> int:
        """Calcule la taille totale d'un dossier"""
        total_size = 0
        
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                
                if follow_symlinks or not os.path.islink(file_path):
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, FileNotFoundError):
                        continue
        
        return total_size
    
    @staticmethod
    def find_files(directory: str, pattern: str = "*.py", 
                  recursive: bool = True) -> List[str]:
        """Trouve des fichiers selon un pattern"""
        import glob
        
        if recursive:
            pattern = os.path.join(directory, "**", pattern)
            return glob.glob(pattern, recursive=True)
        else:
            pattern = os.path.join(directory, pattern)
            return glob.glob(pattern)
    
    @staticmethod
    def backup_file(file_path: str, backup_suffix: str = ".backup") -> str:
        """Crée une sauvegarde d'un fichier"""
        backup_path = f"{file_path}{backup_suffix}"
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    @staticmethod
    def restore_backup(backup_path: str, original_path: Optional[str] = None) -> bool:
        """Restaure un fichier depuis sa sauvegarde"""
        try:
            if original_path is None:
                original_path = backup_path.replace(".backup", "")
            
            shutil.move(backup_path, original_path)
            return True
        except Exception:
            return False
    
    @staticmethod
    def safe_copy(src: str, dst: str, preserve_metadata: bool = True) -> bool:
        """Copie sécurisée d'un fichier"""
        try:
            # S'assure que le dossier de destination existe
            FileUtils.ensure_directory(os.path.dirname(dst))
            
            if preserve_metadata:
                shutil.copy2(src, dst)
            else:
                shutil.copy(src, dst)
            
            return True
        except Exception as e:
            logging.getLogger("PyForgee.file_utils").error(f"Erreur copie {src} -> {dst}: {e}")
            return False
    
    @staticmethod
    def safe_move(src: str, dst: str) -> bool:
        """Déplacement sécurisé d'un fichier"""
        try:
            FileUtils.ensure_directory(os.path.dirname(dst))
            shutil.move(src, dst)
            return True
        except Exception as e:
            logging.getLogger("PyForgee.file_utils").error(f"Erreur déplacement {src} -> {dst}: {e}")
            return False
    
    @staticmethod
    def clean_directory(directory: str, keep_patterns: List[str] = None) -> int:
        """Nettoie un dossier en gardant certains fichiers"""
        import fnmatch
        
        keep_patterns = keep_patterns or []
        removed_count = 0
        
        for root, dirs, files in os.walk(directory, topdown=False):
            # Supprime les fichiers
            for file in files:
                file_path = os.path.join(root, file)
                
                # Vérifie si le fichier doit être gardé
                should_keep = any(
                    fnmatch.fnmatch(file, pattern) for pattern in keep_patterns
                )
                
                if not should_keep:
                    try:
                        os.remove(file_path)
                        removed_count += 1
                    except Exception:
                        pass
            
            # Supprime les dossiers vides
            try:
                if root != directory and not os.listdir(root):
                    os.rmdir(root)
            except Exception:
                pass
        
        return removed_count
    
    @staticmethod
    def get_temp_directory() -> str:
        """Crée un dossier temporaire"""
        return tempfile.mkdtemp(prefix="PyForgee_")
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """Retourne des informations détaillées sur un fichier"""
        try:
            stat_result = os.stat(file_path)
            
            return {
                'path': file_path,
                'name': os.path.basename(file_path),
                'size': stat_result.st_size,
                'modified_time': stat_result.st_mtime,
                'created_time': stat_result.st_ctime,
                'is_file': os.path.isfile(file_path),
                'is_directory': os.path.isdir(file_path),
                'is_executable': bool(stat_result.st_mode & stat.S_IEXEC),
                'permissions': oct(stat_result.st_mode)[-3:],
                'mime_type': mimetypes.guess_type(file_path)[0],
                'extension': Path(file_path).suffix.lower(),
                'hash_md5': FileUtils.get_file_hash(file_path, 'md5') if os.path.isfile(file_path) else None
            }
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def is_python_file(file_path: str) -> bool:
        """Vérifie si un fichier est un script Python"""
        if not os.path.isfile(file_path):
            return False
        
        # Vérification par extension
        if file_path.lower().endswith(('.py', '.pyw', '.pyi')):
            return True
        
        # Vérification par shebang
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline().strip()
                if first_line.startswith('#!') and 'python' in first_line:
                    return True
        except Exception:
            pass
        
        return False
    
    @staticmethod
    def scan_python_files(directory: str) -> List[str]:
        """Scanne un dossier pour trouver tous les fichiers Python"""
        python_files = []
        
        for root, dirs, files in os.walk(directory):
            # Exclut certains dossiers
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache', 'node_modules'}]
            
            for file in files:
                file_path = os.path.join(root, file)
                if FileUtils.is_python_file(file_path):
                    python_files.append(file_path)
        
        return python_files
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalise un chemin de fichier"""
        return os.path.normpath(os.path.abspath(path))
    
    @staticmethod
    def make_executable(file_path: str) -> bool:
        """Rend un fichier exécutable"""
        try:
            current_mode = os.stat(file_path).st_mode
            os.chmod(file_path, current_mode | stat.S_IEXEC)
            return True
        except Exception:
            return False
    
    @classmethod
    def batch_process_files(cls, file_paths: List[str], 
                           processor_func, *args, **kwargs) -> Dict[str, Any]:
        """Traite plusieurs fichiers en lot"""
        results = {}
        
        for file_path in file_paths:
            try:
                result = processor_func(file_path, *args, **kwargs)
                results[file_path] = {'success': True, 'result': result}
            except Exception as e:
                results[file_path] = {'success': False, 'error': str(e)}
        
        return results
    
    @staticmethod
    def validate_path(path: str, must_exist: bool = False, 
                     must_be_file: bool = False, 
                     must_be_directory: bool = False) -> bool:
        """Valide un chemin selon des critères"""
        if not path:
            return False
        
        if must_exist and not os.path.exists(path):
            return False
        
        if must_be_file and not os.path.isfile(path):
            return False
        
        if must_be_directory and not os.path.isdir(path):
            return False
        
        return True