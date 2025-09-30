#!/usr/bin/env python3
"""
Utilitaires système pour PyForgee
"""

import os
import sys
import platform
import subprocess
import shutil
import logging
import psutil
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path
import tempfile


class SystemUtils:
    """Utilitaires système"""
    
    def __init__(self):
        self.logger = logging.getLogger("PyForgee.system_utils")
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Retourne des informations sur le système"""
        return {
            'platform': platform.platform(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': sys.version,
            'python_executable': sys.executable,
            'cpu_count': os.cpu_count(),
            'memory_total': psutil.virtual_memory().total if hasattr(psutil, 'virtual_memory') else None,
            'disk_usage': shutil.disk_usage('.') if hasattr(shutil, 'disk_usage') else None
        }
    
    @staticmethod
    def is_windows() -> bool:
        """Vérifie si on est sur Windows"""
        return platform.system() == 'Windows'
    
    @staticmethod
    def is_linux() -> bool:
        """Vérifie si on est sur Linux"""
        return platform.system() == 'Linux'
    
    @staticmethod
    def is_macos() -> bool:
        """Vérifie si on est sur macOS"""
        return platform.system() == 'Darwin'
    
    @staticmethod
    def find_executable(name: str) -> Optional[str]:
        """Trouve un exécutable dans le PATH"""
        return shutil.which(name)
    
    @staticmethod
    def run_command(cmd: Union[str, List[str]], 
                   cwd: Optional[str] = None,
                   timeout: Optional[float] = None,
                   capture_output: bool = True) -> Tuple[int, str, str]:
        """Exécute une commande système"""
        try:
            if isinstance(cmd, str):
                cmd = cmd.split()
            
            result = subprocess.run(
                cmd,
                cwd=cwd,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                check=False
            )
            
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout"
        except Exception as e:
            return -1, "", str(e)
    
    @staticmethod
    def get_available_memory() -> int:
        """Retourne la mémoire disponible en bytes"""
        try:
            return psutil.virtual_memory().available
        except:
            return 0
    
    @staticmethod
    def get_cpu_usage() -> float:
        """Retourne l'usage CPU en pourcentage"""
        try:
            return psutil.cpu_percent(interval=1)
        except:
            return 0.0
    
    @staticmethod
    def kill_process_by_name(name: str) -> int:
        """Tue tous les processus avec le nom donné"""
        killed_count = 0
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and name.lower() in proc.info['name'].lower():
                    try:
                        proc.terminate()
                        proc.wait(timeout=3)
                        killed_count += 1
                    except:
                        try:
                            proc.kill()
                            killed_count += 1
                        except:
                            pass
        except:
            pass
        
        return killed_count
    
    @staticmethod
    def is_process_running(name: str) -> bool:
        """Vérifie si un processus est en cours d'exécution"""
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and name.lower() in proc.info['name'].lower():
                    return True
        except:
            pass
        
        return False
    
    @staticmethod
    def get_free_port(start_port: int = 8000, max_attempts: int = 1000) -> Optional[int]:
        """Trouve un port libre"""
        import socket
        
        for port in range(start_port, start_port + max_attempts):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('localhost', port))
                sock.close()
                return port
            except OSError:
                continue
        
        return None
    
    @staticmethod
    def get_environment_variables() -> Dict[str, str]:
        """Retourne les variables d'environnement"""
        return dict(os.environ)
    
    @staticmethod
    def set_environment_variable(name: str, value: str) -> bool:
        """Définit une variable d'environnement"""
        try:
            os.environ[name] = value
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_temp_dir() -> str:
        """Retourne le dossier temporaire système"""
        return tempfile.gettempdir()
    
    @staticmethod
    def create_temp_file(suffix: str = "", prefix: str = "PyForgee_") -> str:
        """Crée un fichier temporaire"""
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        os.close(fd)
        return path
    
    @staticmethod
    def get_python_installations() -> List[Dict[str, str]]:
        """Trouve toutes les installations Python"""
        installations = []
        
        # Python actuel
        installations.append({
            'path': sys.executable,
            'version': sys.version,
            'current': True
        })
        
        # Recherche d'autres installations
        search_paths = [
            '/usr/bin',
            '/usr/local/bin',
            'C:\\Python*',
            'C:\\Program Files\\Python*',
            os.path.expanduser('~/AppData/Local/Programs/Python')
        ]
        
        for search_path in search_paths:
            try:
                if '*' in search_path:
                    import glob
                    for path in glob.glob(search_path):
                        python_exe = os.path.join(path, 'python.exe' if SystemUtils.is_windows() else 'python')
                        if os.path.exists(python_exe):
                            try:
                                result = subprocess.run([python_exe, '--version'], capture_output=True, text=True, timeout=5)
                                if result.returncode == 0:
                                    installations.append({
                                        'path': python_exe,
                                        'version': result.stdout.strip(),
                                        'current': False
                                    })
                            except:
                                pass
                else:
                    if os.path.isdir(search_path):
                        for item in os.listdir(search_path):
                            if item.startswith('python'):
                                python_exe = os.path.join(search_path, item)
                                if os.path.isfile(python_exe) and os.access(python_exe, os.X_OK):
                                    try:
                                        result = subprocess.run([python_exe, '--version'], capture_output=True, text=True, timeout=5)
                                        if result.returncode == 0:
                                            installations.append({
                                                'path': python_exe,
                                                'version': result.stdout.strip(),
                                                'current': False
                                            })
                                    except:
                                        pass
            except:
                pass
        
        # Déduplique
        unique_installations = []
        seen_paths = set()
        
        for install in installations:
            path = os.path.normpath(install['path'])
            if path not in seen_paths:
                seen_paths.add(path)
                unique_installations.append(install)
        
        return unique_installations
    
    @staticmethod
    def check_dependencies() -> Dict[str, Dict[str, Any]]:
        """Vérifie la disponibilité des dépendances"""
        dependencies = {
            'pyinstaller': {'command': 'pyinstaller --version'},
            'nuitka': {'command': 'python -m nuitka --version'},
            'upx': {'command': 'upx --version'},
            'pyarmor': {'command': 'pyarmor --version'},
        }
        
        results = {}
        
        for name, info in dependencies.items():
            try:
                result = subprocess.run(
                    info['command'].split(),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                results[name] = {
                    'available': result.returncode == 0,
                    'version': result.stdout.strip() if result.returncode == 0 else None,
                    'error': result.stderr.strip() if result.returncode != 0 else None
                }
            except Exception as e:
                results[name] = {
                    'available': False,
                    'version': None,
                    'error': str(e)
                }
        
        return results
    
    @staticmethod
    def install_package(package_name: str, pip_args: List[str] = None) -> bool:
        """Installe un package Python"""
        pip_args = pip_args or []
        
        try:
            cmd = [sys.executable, '-m', 'pip', 'install'] + pip_args + [package_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def get_installed_packages() -> Dict[str, str]:
        """Retourne la liste des packages installés"""
        packages = {}
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                package_list = json.loads(result.stdout)
                for package in package_list:
                    packages[package['name']] = package['version']
        except Exception:
            pass
        
        return packages
    
    @staticmethod
    def cleanup_temp_files(pattern: str = "PyForgee_*") -> int:
        """Nettoie les fichiers temporaires PyForgee"""
        import glob
        
        temp_dir = SystemUtils.get_temp_dir()
        pattern_path = os.path.join(temp_dir, pattern)
        
        cleaned_count = 0
        
        for item in glob.glob(pattern_path):
            try:
                if os.path.isfile(item):
                    os.remove(item)
                    cleaned_count += 1
                elif os.path.isdir(item):
                    shutil.rmtree(item)
                    cleaned_count += 1
            except Exception:
                pass
        
        return cleaned_count