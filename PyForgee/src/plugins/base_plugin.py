#!/usr/bin/env python3
"""
Système de plugins modulaire pour PyForgee
Classe de base pour tous les plugins
"""

import os
import sys
import json
import logging
import importlib
import importlib.util
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum


class PluginType(Enum):
    """Types de plugins supportés"""
    COMPILER = "compiler"
    COMPRESSOR = "compressor"
    PROTECTOR = "protector"
    ANALYZER = "analyzer"
    TOOL = "tool"
    EXTENSION = "extension"


class PluginPriority(Enum):
    """Priorités des plugins"""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class PluginMetadata:
    """Métadonnées d'un plugin"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    priority: PluginPriority = PluginPriority.NORMAL
    
    # Compatibilité
    min_PyForgee_version: Optional[str] = None
    max_PyForgee_version: Optional[str] = None
    python_versions: List[str] = field(default_factory=list)
    platforms: List[str] = field(default_factory=list)
    
    # Dépendances
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    
    # Configuration
    config_schema: Optional[Dict[str, Any]] = None
    default_config: Optional[Dict[str, Any]] = None
    
    # État
    enabled: bool = True
    loaded: bool = False
    
    def __post_init__(self):
        if not self.python_versions:
            self.python_versions = [f"{sys.version_info.major}.{sys.version_info.minor}"]
        if not self.platforms:
            self.platforms = [sys.platform]


@dataclass
class PluginContext:
    """Contexte d'exécution d'un plugin"""
    source_path: Optional[str] = None
    output_path: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    shared_data: Dict[str, Any] = field(default_factory=dict)
    
    # Callbacks
    progress_callback: Optional[Callable[[str, float], None]] = None
    log_callback: Optional[Callable[[str, str], None]] = None
    
    def update_progress(self, message: str, progress: float):
        """Met à jour la progression"""
        if self.progress_callback:
            self.progress_callback(message, progress)
    
    def log(self, level: str, message: str):
        """Log un message"""
        if self.log_callback:
            self.log_callback(level, message)


class BasePlugin(ABC):
    """Classe de base pour tous les plugins PyForgee"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"PyForgee.plugin.{self.get_metadata().name}")
        self._metadata = None
        self._config = {}
        self._hooks = {}
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Retourne les métadonnées du plugin"""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialise le plugin avec sa configuration"""
        pass
    
    @abstractmethod
    def execute(self, context: PluginContext) -> Dict[str, Any]:
        """Exécute le plugin avec le contexte donné"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Nettoie les ressources du plugin"""
        pass
    
    def is_compatible(self) -> bool:
        """Vérifie si le plugin est compatible avec l'environnement actuel"""
        metadata = self.get_metadata()
        
        # Vérification Python
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        if metadata.python_versions and python_version not in metadata.python_versions:
            return False
        
        # Vérification plateforme
        if metadata.platforms and sys.platform not in metadata.platforms:
            return False
        
        # Vérification des dépendances
        for dep in metadata.dependencies:
            try:
                importlib.import_module(dep)
            except ImportError:
                return False
        
        return True
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de configuration"""
        return self._config.get(key, default)
    
    def set_config_value(self, key: str, value: Any):
        """Définit une valeur de configuration"""
        self._config[key] = value
    
    def register_hook(self, event: str, callback: Callable):
        """Enregistre un hook pour un événement"""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
    
    def trigger_hook(self, event: str, *args, **kwargs):
        """Déclenche tous les hooks pour un événement"""
        if event in self._hooks:
            for callback in self._hooks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Erreur dans hook {event}: {e}")
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Valide la configuration selon le schéma"""
        errors = []
        metadata = self.get_metadata()
        
        if metadata.config_schema:
            # Validation basique (peut être étendue avec jsonschema)
            for key, schema in metadata.config_schema.items():
                if key in config:
                    value = config[key]
                    expected_type = schema.get('type')
                    
                    if expected_type == 'string' and not isinstance(value, str):
                        errors.append(f"'{key}' doit être une chaîne")
                    elif expected_type == 'integer' and not isinstance(value, int):
                        errors.append(f"'{key}' doit être un entier")
                    elif expected_type == 'boolean' and not isinstance(value, bool):
                        errors.append(f"'{key}' doit être un booléen")
                    elif expected_type == 'array' and not isinstance(value, list):
                        errors.append(f"'{key}' doit être une liste")
                    
                    # Validation des valeurs
                    if 'enum' in schema and value not in schema['enum']:
                        errors.append(f"'{key}' doit être l'une des valeurs: {schema['enum']}")
                    
                    if 'min' in schema and isinstance(value, (int, float)) and value < schema['min']:
                        errors.append(f"'{key}' doit être >= {schema['min']}")
                    
                    if 'max' in schema and isinstance(value, (int, float)) and value > schema['max']:
                        errors.append(f"'{key}' doit être <= {schema['max']}")
                
                elif schema.get('required', False):
                    errors.append(f"'{key}' est requis")
        
        return errors
    
    def get_default_config(self) -> Dict[str, Any]:
        """Retourne la configuration par défaut"""
        metadata = self.get_metadata()
        return metadata.default_config or {}


class PluginManager:
    """Gestionnaire de plugins pour PyForgee"""
    
    def __init__(self, plugin_directories: List[str] = None):
        self.logger = logging.getLogger("PyForgee.plugin_manager")
        
        # Dossiers de plugins
        self.plugin_directories = plugin_directories or self._get_default_plugin_dirs()
        
        # Plugins chargés
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
        
        # Configuration
        self.config: Dict[str, Dict[str, Any]] = {}
        
        # Hooks globaux
        self.global_hooks: Dict[str, List[Callable]] = {}
    
    def _get_default_plugin_dirs(self) -> List[str]:
        """Retourne les dossiers de plugins par défaut"""
        dirs = [
            os.path.join(os.path.dirname(__file__)),  # Dossier plugins de PyForgee
            os.path.expanduser("~/.PyForgee/plugins"),  # Plugins utilisateur
            "/usr/local/share/PyForgee/plugins",  # Plugins système (Linux)
            "C:\\ProgramData\\PyForgee\\plugins"  # Plugins système (Windows)
        ]
        
        # Filtre les dossiers existants
        return [d for d in dirs if os.path.isdir(d)]
    
    def discover_plugins(self) -> List[str]:
        """Découvre tous les plugins disponibles"""
        discovered = []
        
        for plugin_dir in self.plugin_directories:
            try:
                for item in os.listdir(plugin_dir):
                    item_path = os.path.join(plugin_dir, item)
                    
                    # Dossier de plugin
                    if os.path.isdir(item_path):
                        plugin_file = os.path.join(item_path, "__init__.py")
                        if os.path.exists(plugin_file):
                            discovered.append(item_path)
                    
                    # Fichier de plugin
                    elif item.endswith(".py") and not item.startswith("_"):
                        discovered.append(item_path)
                        
            except Exception as e:
                self.logger.warning(f"Erreur scan dossier {plugin_dir}: {e}")
        
        return discovered
    
    def load_plugin(self, plugin_path: str) -> bool:
        """Charge un plugin depuis un chemin"""
        try:
            # Détermine le nom du module
            if os.path.isdir(plugin_path):
                module_name = os.path.basename(plugin_path)
                plugin_file = os.path.join(plugin_path, "__init__.py")
            else:
                module_name = os.path.splitext(os.path.basename(plugin_path))[0]
                plugin_file = plugin_path
            
            # Charge le module
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                self.logger.error(f"Impossible de charger {plugin_path}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Trouve la classe de plugin
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BasePlugin) and 
                    attr != BasePlugin):
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                self.logger.error(f"Aucune classe de plugin trouvée dans {plugin_path}")
                return False
            
            # Instancie le plugin
            plugin = plugin_class()
            
            # Vérifie la compatibilité
            if not plugin.is_compatible():
                self.logger.warning(f"Plugin {module_name} incompatible avec cet environnement")
                return False
            
            # Récupère les métadonnées
            metadata = plugin.get_metadata()
            
            # Configuration
            config = self.config.get(metadata.name, plugin.get_default_config())
            
            # Valide la configuration
            config_errors = plugin.validate_config(config)
            if config_errors:
                self.logger.error(f"Erreurs de configuration pour {metadata.name}: {config_errors}")
                return False
            
            # Initialise le plugin
            if not plugin.initialize(config):
                self.logger.error(f"Échec initialisation du plugin {metadata.name}")
                return False
            
            # Enregistre le plugin
            self.plugins[metadata.name] = plugin
            self.plugin_metadata[metadata.name] = metadata
            metadata.loaded = True
            
            self.logger.info(f"Plugin chargé: {metadata.name} v{metadata.version}")
            return True
            
        except Exception as e:
            self.logger.exception(f"Erreur chargement plugin {plugin_path}: {e}")
            return False
    
    def load_all_plugins(self) -> Dict[str, bool]:
        """Charge tous les plugins découverts"""
        results = {}
        
        discovered = self.discover_plugins()
        for plugin_path in discovered:
            plugin_name = os.path.basename(plugin_path)
            results[plugin_name] = self.load_plugin(plugin_path)
        
        return results
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Décharge un plugin"""
        if plugin_name in self.plugins:
            try:
                self.plugins[plugin_name].cleanup()
                del self.plugins[plugin_name]
                
                if plugin_name in self.plugin_metadata:
                    self.plugin_metadata[plugin_name].loaded = False
                    del self.plugin_metadata[plugin_name]
                
                self.logger.info(f"Plugin déchargé: {plugin_name}")
                return True
                
            except Exception as e:
                self.logger.error(f"Erreur déchargement plugin {plugin_name}: {e}")
                return False
        
        return False
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[BasePlugin]:
        """Retourne les plugins d'un type donné"""
        return [
            plugin for name, plugin in self.plugins.items()
            if self.plugin_metadata[name].plugin_type == plugin_type
            and self.plugin_metadata[name].enabled
        ]
    
    def execute_plugin(self, plugin_name: str, context: PluginContext) -> Dict[str, Any]:
        """Exécute un plugin avec le contexte donné"""
        if plugin_name not in self.plugins:
            raise ValueError(f"Plugin non trouvé: {plugin_name}")
        
        plugin = self.plugins[plugin_name]
        
        try:
            result = plugin.execute(context)
            self.logger.debug(f"Plugin {plugin_name} exécuté avec succès")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur exécution plugin {plugin_name}: {e}")
            raise
    
    def execute_plugins_by_type(self, plugin_type: PluginType, 
                               context: PluginContext) -> Dict[str, Dict[str, Any]]:
        """Exécute tous les plugins d'un type donné"""
        results = {}
        
        plugins = self.get_plugins_by_type(plugin_type)
        
        # Trie par priorité (plus élevée en premier)
        plugins.sort(
            key=lambda p: self.plugin_metadata[p.get_metadata().name].priority.value,
            reverse=True
        )
        
        for plugin in plugins:
            name = plugin.get_metadata().name
            try:
                results[name] = self.execute_plugin(name, context)
            except Exception as e:
                results[name] = {'error': str(e)}
        
        return results
    
    def register_global_hook(self, event: str, callback: Callable):
        """Enregistre un hook global"""
        if event not in self.global_hooks:
            self.global_hooks[event] = []
        self.global_hooks[event].append(callback)
    
    def trigger_global_hook(self, event: str, *args, **kwargs):
        """Déclenche tous les hooks globaux pour un événement"""
        if event in self.global_hooks:
            for callback in self.global_hooks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Erreur dans hook global {event}: {e}")
    
    def get_plugin_info(self) -> Dict[str, Dict[str, Any]]:
        """Retourne des informations sur tous les plugins"""
        info = {}
        
        for name, metadata in self.plugin_metadata.items():
            info[name] = {
                'version': metadata.version,
                'description': metadata.description,
                'author': metadata.author,
                'type': metadata.plugin_type.value,
                'priority': metadata.priority.value,
                'enabled': metadata.enabled,
                'loaded': metadata.loaded,
                'compatible': name in self.plugins
            }
        
        return info
    
    def enable_plugin(self, plugin_name: str):
        """Active un plugin"""
        if plugin_name in self.plugin_metadata:
            self.plugin_metadata[plugin_name].enabled = True
    
    def disable_plugin(self, plugin_name: str):
        """Désactive un plugin"""
        if plugin_name in self.plugin_metadata:
            self.plugin_metadata[plugin_name].enabled = False
    
    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]):
        """Définit la configuration d'un plugin"""
        self.config[plugin_name] = config
        
        # Met à jour le plugin si chargé
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            plugin._config = config
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Récupère la configuration d'un plugin"""
        return self.config.get(plugin_name, {})


# Gestionnaire global
_plugin_manager: Optional[PluginManager] = None

def get_plugin_manager() -> PluginManager:
    """Retourne l'instance globale du gestionnaire de plugins"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager