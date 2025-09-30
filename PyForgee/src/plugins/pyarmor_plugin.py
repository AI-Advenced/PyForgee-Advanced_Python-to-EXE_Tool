#!/usr/bin/env python3
"""
Plugin PyArmor pour PyForgee
Protection professionnelle du code Python
"""

import os
import subprocess
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from .base_plugin import BasePlugin, PluginMetadata, PluginContext, PluginType, PluginPriority


class PyArmorPlugin(BasePlugin):
    """Plugin pour la protection PyArmor"""
    
    def __init__(self):
        super().__init__()
        self.pyarmor_path = None
        self.pyarmor_version = None
    
    def get_metadata(self) -> PluginMetadata:
        """Métadonnées du plugin PyArmor"""
        return PluginMetadata(
            name="pyarmor_protector",
            version="1.0.0",
            description="Protection professionnelle du code Python avec PyArmor",
            author="PyForgee Team",
            plugin_type=PluginType.PROTECTOR,
            priority=PluginPriority.HIGH,
            
            # Dépendances
            dependencies=["pyarmor"],
            
            # Configuration
            config_schema={
                "pyarmor_path": {
                    "type": "string",
                    "description": "Chemin vers PyArmor",
                    "required": False
                },
                "protection_level": {
                    "type": "string",
                    "description": "Niveau de protection",
                    "enum": ["basic", "intermediate", "advanced", "maximum"],
                    "default": "intermediate"
                },
                "obfuscate_mode": {
                    "type": "integer",
                    "description": "Mode d'obfuscation (0-4)",
                    "min": 0,
                    "max": 4,
                    "default": 1
                },
                "advanced_mode": {
                    "type": "boolean",
                    "description": "Mode avancé",
                    "default": False
                },
                "restrict_mode": {
                    "type": "boolean",
                    "description": "Mode restriction",
                    "default": False
                },
                "exclude_modules": {
                    "type": "array",
                    "description": "Modules à exclure",
                    "default": []
                },
                "license_file": {
                    "type": "string",
                    "description": "Fichier de license PyArmor",
                    "required": False
                },
                "bind_device": {
                    "type": "boolean",
                    "description": "Lier au dispositif",
                    "default": False
                },
                "bind_mac": {
                    "type": "boolean",
                    "description": "Lier à l'adresse MAC",
                    "default": False
                },
                "expire_date": {
                    "type": "string",
                    "description": "Date d'expiration (YYYY-MM-DD)",
                    "required": False
                }
            },
            
            default_config={
                "protection_level": "intermediate",
                "obfuscate_mode": 1,
                "advanced_mode": False,
                "restrict_mode": False,
                "exclude_modules": [],
                "bind_device": False,
                "bind_mac": False
            }
        )
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialise le plugin PyArmor"""
        self._config = config
        
        # Trouve PyArmor
        self.pyarmor_path = self._find_pyarmor_executable()
        if not self.pyarmor_path:
            self.logger.error("PyArmor non trouvé")
            return False
        
        # Vérifie la version
        self.pyarmor_version = self._get_pyarmor_version()
        if not self.pyarmor_version:
            self.logger.error("Impossible de déterminer la version PyArmor")
            return False
        
        # Vérifie la license
        if not self._check_license():
            self.logger.warning("Aucune license PyArmor détectée - fonctionnalités limitées")
        
        self.logger.info(f"PyArmor initialisé: {self.pyarmor_version}")
        return True
    
    def execute(self, context: PluginContext) -> Dict[str, Any]:
        """Protège du code Python avec PyArmor"""
        
        if not context.source_path or not os.path.exists(context.source_path):
            raise ValueError("Fichier/dossier source requis et doit exister")
        
        source_path = Path(context.source_path)
        
        context.update_progress("Préparation protection PyArmor...", 0.0)
        
        # Détermine le dossier de sortie
        if context.output_path:
            output_path = Path(context.output_path)
        else:
            output_path = source_path.parent / "protected"
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            context.update_progress("Protection en cours...", 0.2)
            
            # Construction de la commande
            cmd = self._build_pyarmor_command(source_path, output_path)
            
            context.log("debug", f"Commande PyArmor: {' '.join(cmd)}")
            
            # Exécution dans un dossier temporaire
            with tempfile.TemporaryDirectory() as temp_dir:
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=temp_dir,
                    timeout=600  # 10 minutes max
                )
                
                context.update_progress("Protection terminée", 0.8)
                
                if result.returncode == 0:
                    # Succès - copie les fichiers protégés
                    protected_files = self._collect_protected_files(temp_dir, output_path)
                    
                    context.update_progress("Finalisation...", 1.0)
                    
                    context.log("info", f"Protection réussie: {len(protected_files)} fichiers")
                    
                    return {
                        "success": True,
                        "protected_files": protected_files,
                        "output_path": str(output_path),
                        "pyarmor_version": self.pyarmor_version,
                        "protection_level": self.get_config_value("protection_level")
                    }
                else:
                    error_msg = result.stderr or result.stdout or "Erreur PyArmor inconnue"
                    context.log("error", f"Échec protection PyArmor: {error_msg}")
                    
                    return {
                        "success": False,
                        "error": error_msg
                    }
                    
        except subprocess.TimeoutExpired:
            error_msg = "Timeout lors de la protection PyArmor"
            context.log("error", error_msg)
            
            return {
                "success": False,
                "error": error_msg
            }
        
        except Exception as e:
            error_msg = f"Erreur lors de la protection: {e}"
            context.log("error", error_msg)
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def cleanup(self):
        """Nettoie les ressources du plugin"""
        # Nettoie les fichiers temporaires PyArmor si nécessaire
        pass
    
    def _find_pyarmor_executable(self) -> Optional[str]:
        """Trouve l'exécutable PyArmor"""
        
        # Chemin spécifié dans la config
        pyarmor_path = self.get_config_value("pyarmor_path")
        if pyarmor_path and shutil.which(pyarmor_path):
            return pyarmor_path
        
        # Recherche dans le PATH
        return shutil.which("pyarmor")
    
    def _get_pyarmor_version(self) -> Optional[str]:
        """Récupère la version de PyArmor"""
        if not self.pyarmor_path:
            return None
        
        try:
            result = subprocess.run(
                [self.pyarmor_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        
        return None
    
    def _check_license(self) -> bool:
        """Vérifie la license PyArmor"""
        if not self.pyarmor_path:
            return False
        
        try:
            result = subprocess.run(
                [self.pyarmor_path, "hdinfo"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Si la commande réussit, une license est présente
            return result.returncode == 0
        except Exception:
            return False
    
    def _build_pyarmor_command(self, source_path: Path, output_path: Path) -> List[str]:
        """Construit la commande PyArmor"""
        
        cmd = [self.pyarmor_path, "obfuscate"]
        
        # Niveau de protection
        protection_level = self.get_config_value("protection_level", "intermediate")
        
        if protection_level in ["advanced", "maximum"]:
            cmd.extend(["--advanced", str(self.get_config_value("obfuscate_mode", 1))])
        
        if protection_level == "maximum":
            cmd.extend(["--restrict", "1"])
        elif self.get_config_value("restrict_mode", False):
            cmd.extend(["--restrict", "1"])
        
        # Mode avancé
        if self.get_config_value("advanced_mode", False):
            cmd.extend(["--advanced", str(self.get_config_value("obfuscate_mode", 1))])
        
        # Dossier de sortie
        cmd.extend(["--output-dir", str(output_path)])
        
        # Exclusions
        exclude_modules = self.get_config_value("exclude_modules", [])
        for module in exclude_modules:
            cmd.extend(["--exclude", module])
        
        # License
        license_file = self.get_config_value("license_file")
        if license_file and os.path.exists(license_file):
            cmd.extend(["--license", license_file])
        
        # Liaisons
        if self.get_config_value("bind_device", False):
            cmd.extend(["--bind-device"])
        
        if self.get_config_value("bind_mac", False):
            cmd.extend(["--bind-mac"])
        
        # Date d'expiration
        expire_date = self.get_config_value("expire_date")
        if expire_date:
            cmd.extend(["--expire-date", expire_date])
        
        # Source
        cmd.append(str(source_path))
        
        return cmd
    
    def _collect_protected_files(self, temp_dir: str, output_path: Path) -> List[str]:
        """Collecte les fichiers protégés depuis le dossier temporaire"""
        
        protected_files = []
        
        # PyArmor génère généralement dans un sous-dossier
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.py', '.pyd', '.so')):
                    src_file = os.path.join(root, file)
                    
                    # Calcule le chemin relatif
                    rel_path = os.path.relpath(src_file, temp_dir)
                    dst_file = output_path / rel_path
                    
                    # S'assure que le dossier de destination existe
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copie le fichier
                    shutil.copy2(src_file, dst_file)
                    protected_files.append(str(dst_file))
        
        return protected_files
    
    def supports_source(self, source_path: str) -> bool:
        """Vérifie si PyArmor peut protéger cette source"""
        
        source = Path(source_path)
        
        if source.is_file():
            return source.suffix == '.py'
        elif source.is_dir():
            # Vérifie s'il y a des fichiers Python dans le dossier
            for file in source.rglob("*.py"):
                return True
        
        return False
    
    def get_protection_strength(self, level: str) -> int:
        """Retourne la force de protection (0-100)"""
        
        strength_map = {
            "basic": 40,
            "intermediate": 70,
            "advanced": 85,
            "maximum": 95
        }
        
        return strength_map.get(level, 50)
    
    def estimate_protection_time(self, source_path: str) -> float:
        """Estime le temps de protection en secondes"""
        
        if not os.path.exists(source_path):
            return 0.0
        
        source = Path(source_path)
        
        if source.is_file():
            file_count = 1
        else:
            file_count = len(list(source.rglob("*.py")))
        
        # Estimation: ~2 secondes par fichier + overhead
        base_time = file_count * 2.0
        overhead = 5.0  # Setup PyArmor
        
        protection_level = self.get_config_value("protection_level", "intermediate")
        if protection_level in ["advanced", "maximum"]:
            base_time *= 1.5
        
        return base_time + overhead
    
    def validate_environment(self) -> Dict[str, Any]:
        """Valide l'environnement pour PyArmor"""
        
        validation = {
            "pyarmor_available": False,
            "pyarmor_version": None,
            "license_valid": False,
            "python_compatible": False,
            "issues": []
        }
        
        # Vérifie PyArmor
        if self.pyarmor_path:
            validation["pyarmor_available"] = True
            validation["pyarmor_version"] = self.pyarmor_version
        else:
            validation["issues"].append("PyArmor non trouvé")
        
        # Vérifie la license
        if self._check_license():
            validation["license_valid"] = True
        else:
            validation["issues"].append("License PyArmor invalide ou manquante")
        
        # Vérifie la compatibilité Python
        import sys
        if sys.version_info >= (3, 6):
            validation["python_compatible"] = True
        else:
            validation["issues"].append("Python 3.6+ requis pour PyArmor")
        
        return validation
    
    def create_license_config(self, **kwargs) -> Dict[str, Any]:
        """Crée une configuration de license"""
        
        config = {
            "expired": kwargs.get("expire_date"),
            "bind_device": kwargs.get("bind_device", False),
            "bind_mac": kwargs.get("bind_mac", False),
            "bind_ip": kwargs.get("bind_ip"),
            "bind_domain": kwargs.get("bind_domain"),
        }
        
        # Filtre les valeurs None
        return {k: v for k, v in config.items() if v is not None}
    
    def generate_bootstrap(self, protected_path: str) -> str:
        """Génère un script de bootstrap pour les fichiers protégés"""
        
        bootstrap_code = f'''#!/usr/bin/env python3
"""
Bootstrap script for PyArmor protected files
Generated by PyForgee
"""

import sys
import os

# Add protected path to Python path
protected_path = r"{protected_path}"
if protected_path not in sys.path:
    sys.path.insert(0, protected_path)

# Import and run main module
try:
    from pytransform import pyarmor_runtime
    pyarmor_runtime()
    
    # Import your main module here
    import main  # Replace with actual main module name
    
    if hasattr(main, 'main'):
        main.main()
    
except ImportError as e:
    print(f"Error importing protected modules: {{e}}")
    sys.exit(1)
except Exception as e:
    print(f"Error running protected application: {{e}}")
    sys.exit(1)
'''
        
        return bootstrap_code