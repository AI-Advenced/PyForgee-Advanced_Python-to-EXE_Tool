#!/usr/bin/env python3
"""
Gestionnaire de configuration pour PyForgee
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
import configparser


@dataclass
class PyForgeeConfig:
    """Configuration principale de PyForgee"""
    # Compilateurs
    preferred_compiler: str = "auto"
    pyinstaller_path: Optional[str] = None
    nuitka_path: Optional[str] = None
    
    # Compression
    default_compression: str = "auto"
    upx_path: Optional[str] = None
    compression_level: int = 9
    
    # Protection
    default_protection_level: str = "intermediate"
    pyarmor_path: Optional[str] = None
    
    # Dossiers
    output_directory: str = "./dist"
    temp_directory: Optional[str] = None
    cache_directory: Optional[str] = None
    
    # Options générales
    backup_original: bool = True
    cleanup_temp: bool = True
    parallel_builds: bool = True
    max_workers: int = 4
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Interface
    remember_settings: bool = True
    theme: str = "default"
    
    # Exclusions par défaut
    default_excludes: List[str] = None
    
    def __post_init__(self):
        if self.default_excludes is None:
            self.default_excludes = [
                'tkinter', 'unittest', 'doctest', 'pdb',
                'sqlite3', 'email', 'xml', 'http'
            ]


class ConfigManager:
    """Gestionnaire de configuration PyForgee"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger("PyForgee.config")
        
        # Détermine le fichier de configuration
        if config_file:
            self.config_file = Path(config_file)
        else:
            self.config_file = self._get_default_config_path()
        
        # Charge la configuration
        self.config = self._load_config()
        
        # Assure les dossiers nécessaires
        self._ensure_directories()
    
    def _get_default_config_path(self) -> Path:
        """Détermine le chemin par défaut du fichier de config"""
        
        # Windows
        if sys.platform == "win32":
            config_dir = Path.home() / "AppData" / "Local" / "PyForgee"
        # macOS
        elif sys.platform == "darwin":
            config_dir = Path.home() / "Library" / "Application Support" / "PyForgee"
        # Linux et autres
        else:
            config_dir = Path.home() / ".config" / "PyForgee"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.yaml"
    
    def _load_config(self) -> PyForgeeConfig:
        """Charge la configuration depuis le fichier"""
        
        # Configuration par défaut
        config = PyForgeeConfig()
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    if self.config_file.suffix.lower() == '.yaml':
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)
                
                # Met à jour la config avec les valeurs du fichier
                if data:
                    for key, value in data.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
                
                self.logger.info(f"Configuration chargée depuis: {self.config_file}")
                
            except Exception as e:
                self.logger.warning(f"Erreur chargement config: {e}")
        
        return config
    
    def save_config(self) -> bool:
        """Sauvegarde la configuration"""
        try:
            # S'assure que le dossier existe
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convertit en dictionnaire
            config_dict = asdict(self.config)
            
            # Sauvegarde selon l'extension
            with open(self.config_file, 'w', encoding='utf-8') as f:
                if self.config_file.suffix.lower() == '.yaml':
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration sauvegardée vers: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde config: {e}")
            return False
    
    def _ensure_directories(self):
        """S'assure que les dossiers nécessaires existent"""
        
        directories = [
            self.config.output_directory,
            self.config.temp_directory,
            self.config.cache_directory
        ]
        
        for directory in directories:
            if directory:
                try:
                    Path(directory).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.logger.warning(f"Impossible de créer {directory}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de configuration"""
        return getattr(self.config, key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """Définit une valeur de configuration"""
        try:
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                return True
            else:
                self.logger.warning(f"Clé de configuration inconnue: {key}")
                return False
        except Exception as e:
            self.logger.error(f"Erreur définition config {key}: {e}")
            return False
    
    def update(self, **kwargs) -> bool:
        """Met à jour plusieurs valeurs de configuration"""
        success = True
        
        for key, value in kwargs.items():
            if not self.set(key, value):
                success = False
        
        return success
    
    def reset_to_defaults(self) -> bool:
        """Remet la configuration aux valeurs par défaut"""
        try:
            self.config = PyForgeeConfig()
            self.logger.info("Configuration remise aux valeurs par défaut")
            return True
        except Exception as e:
            self.logger.error(f"Erreur reset config: {e}")
            return False
    
    def export_config(self, output_path: str, format: str = "yaml") -> bool:
        """Exporte la configuration vers un fichier"""
        try:
            config_dict = asdict(self.config)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                if format.lower() == 'yaml':
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                elif format.lower() == 'json':
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)
                elif format.lower() == 'ini':
                    config = configparser.ConfigParser()
                    
                    # Convertit en sections INI
                    for section_name, section_data in self._group_config_by_section(config_dict).items():
                        config[section_name] = {}
                        for key, value in section_data.items():
                            config[section_name][key] = str(value)
                    
                    config.write(f)
                else:
                    raise ValueError(f"Format non supporté: {format}")
            
            self.logger.info(f"Configuration exportée vers: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur export config: {e}")
            return False
    
    def import_config(self, input_path: str) -> bool:
        """Importe une configuration depuis un fichier"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                file_ext = Path(input_path).suffix.lower()
                
                if file_ext in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif file_ext == '.json':
                    data = json.load(f)
                elif file_ext == '.ini':
                    config_parser = configparser.ConfigParser()
                    config_parser.read(input_path, encoding='utf-8')
                    data = self._flatten_ini_config(config_parser)
                else:
                    raise ValueError(f"Format non supporté: {file_ext}")
            
            # Met à jour la configuration
            if data:
                for key, value in data.items():
                    self.set(key, value)
            
            self.logger.info(f"Configuration importée depuis: {input_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur import config: {e}")
            return False
    
    def _group_config_by_section(self, config_dict: Dict) -> Dict[str, Dict]:
        """Groupe la configuration par sections pour le format INI"""
        sections = {
            'Compilers': {},
            'Compression': {},
            'Protection': {},
            'Directories': {},
            'General': {},
            'Logging': {},
            'Interface': {},
            'Exclusions': {}
        }
        
        section_mapping = {
            'preferred_compiler': 'Compilers',
            'pyinstaller_path': 'Compilers',
            'nuitka_path': 'Compilers',
            'default_compression': 'Compression',
            'upx_path': 'Compression',
            'compression_level': 'Compression',
            'default_protection_level': 'Protection',
            'pyarmor_path': 'Protection',
            'output_directory': 'Directories',
            'temp_directory': 'Directories',
            'cache_directory': 'Directories',
            'backup_original': 'General',
            'cleanup_temp': 'General',
            'parallel_builds': 'General',
            'max_workers': 'General',
            'log_level': 'Logging',
            'log_file': 'Logging',
            'remember_settings': 'Interface',
            'theme': 'Interface',
            'default_excludes': 'Exclusions'
        }
        
        for key, value in config_dict.items():
            section = section_mapping.get(key, 'General')
            
            if key == 'default_excludes' and isinstance(value, list):
                sections[section][key] = ','.join(value)
            else:
                sections[section][key] = value
        
        return sections
    
    def _flatten_ini_config(self, config_parser: configparser.ConfigParser) -> Dict:
        """Convertit une config INI en dictionnaire plat"""
        data = {}
        
        for section_name in config_parser.sections():
            for key, value in config_parser[section_name].items():
                if key == 'default_excludes':
                    data[key] = [item.strip() for item in value.split(',')]
                elif value.lower() in ['true', 'false']:
                    data[key] = value.lower() == 'true'
                elif value.isdigit():
                    data[key] = int(value)
                else:
                    data[key] = value
        
        return data
    
    def validate_config(self) -> List[str]:
        """Valide la configuration et retourne les erreurs"""
        errors = []
        
        # Vérifie les chemins
        paths_to_check = [
            ('pyinstaller_path', 'PyInstaller'),
            ('nuitka_path', 'Nuitka'),
            ('upx_path', 'UPX'),
            ('pyarmor_path', 'PyArmor'),
        ]
        
        for path_attr, tool_name in paths_to_check:
            path = getattr(self.config, path_attr)
            if path and not Path(path).exists():
                errors.append(f"Chemin {tool_name} invalide: {path}")
        
        # Vérifie les dossiers
        directories_to_check = [
            ('output_directory', 'Sortie'),
            ('temp_directory', 'Temporaire'),
            ('cache_directory', 'Cache'),
        ]
        
        for dir_attr, dir_name in directories_to_check:
            directory = getattr(self.config, dir_attr)
            if directory:
                try:
                    Path(directory).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"Impossible de créer le dossier {dir_name}: {e}")
        
        # Vérifie les valeurs
        if self.config.max_workers < 1:
            errors.append("Le nombre de workers doit être >= 1")
        
        if self.config.compression_level not in range(1, 10):
            errors.append("Le niveau de compression doit être entre 1 et 9")
        
        return errors
    
    def get_template_config(self) -> Dict[str, Any]:
        """Retourne un template de configuration avec descriptions"""
        return {
            "# Compilateurs": None,
            "preferred_compiler": {
                "value": "auto",
                "description": "Compilateur préféré (auto, pyinstaller, nuitka, cx_freeze)",
                "options": ["auto", "pyinstaller", "nuitka", "cx_freeze"]
            },
            
            "# Compression": None,
            "default_compression": {
                "value": "auto",
                "description": "Méthode de compression par défaut",
                "options": ["auto", "upx", "lzma", "brotli", "custom"]
            },
            "compression_level": {
                "value": 9,
                "description": "Niveau de compression (1-9)",
                "range": [1, 9]
            },
            
            "# Protection": None,
            "default_protection_level": {
                "value": "intermediate",
                "description": "Niveau de protection par défaut",
                "options": ["basic", "intermediate", "advanced", "maximum"]
            },
            
            "# Dossiers": None,
            "output_directory": {
                "value": "./dist",
                "description": "Dossier de sortie par défaut"
            },
            
            "# Options générales": None,
            "backup_original": {
                "value": True,
                "description": "Sauvegarder les fichiers originaux"
            },
            "parallel_builds": {
                "value": True,
                "description": "Builds parallèles"
            },
            "max_workers": {
                "value": 4,
                "description": "Nombre maximum de workers parallèles"
            },
            
            "# Exclusions par défaut": None,
            "default_excludes": {
                "value": ["tkinter", "unittest", "doctest", "pdb"],
                "description": "Modules exclus par défaut"
            }
        }


# Gestionnaire global
_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """Retourne l'instance globale du gestionnaire de config"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_config() -> PyForgeeConfig:
    """Retourne la configuration actuelle"""
    return get_config_manager().config