#!/usr/bin/env python3
"""
Plugin UPX pour PyForgee
Compression avancée d'exécutables avec UPX
"""

import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .base_plugin import BasePlugin, PluginMetadata, PluginContext, PluginType, PluginPriority


class UPXPlugin(BasePlugin):
    """Plugin pour la compression UPX"""
    
    def __init__(self):
        super().__init__()
        self.upx_path = None
        self.upx_version = None
    
    def get_metadata(self) -> PluginMetadata:
        """Métadonnées du plugin UPX"""
        return PluginMetadata(
            name="upx_compressor",
            version="1.0.0",
            description="Compression d'exécutables avec UPX",
            author="PyForgee Team",
            plugin_type=PluginType.COMPRESSOR,
            priority=PluginPriority.HIGH,
            
            # Configuration
            config_schema={
                "upx_path": {
                    "type": "string",
                    "description": "Chemin vers l'exécutable UPX",
                    "required": False
                },
                "compression_level": {
                    "type": "integer",
                    "description": "Niveau de compression (1-9)",
                    "min": 1,
                    "max": 9,
                    "default": 9
                },
                "ultra_brute": {
                    "type": "boolean",
                    "description": "Utiliser le mode ultra-brute",
                    "default": False
                },
                "compress_icons": {
                    "type": "boolean",
                    "description": "Compresser les icônes",
                    "default": True
                },
                "strip_relocs": {
                    "type": "boolean", 
                    "description": "Supprimer les relocations",
                    "default": False
                },
                "backup_original": {
                    "type": "boolean",
                    "description": "Sauvegarder le fichier original",
                    "default": True
                }
            },
            
            default_config={
                "compression_level": 9,
                "ultra_brute": False,
                "compress_icons": True,
                "strip_relocs": False,
                "backup_original": True
            }
        )
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialise le plugin UPX"""
        self._config = config
        
        # Trouve UPX
        self.upx_path = self._find_upx_executable()
        if not self.upx_path:
            self.logger.error("UPX non trouvé dans le PATH")
            return False
        
        # Vérifie la version
        self.upx_version = self._get_upx_version()
        if not self.upx_version:
            self.logger.error("Impossible de déterminer la version UPX")
            return False
        
        self.logger.info(f"UPX initialisé: {self.upx_version} à {self.upx_path}")
        return True
    
    def execute(self, context: PluginContext) -> Dict[str, Any]:
        """Compresse un fichier avec UPX"""
        
        if not context.source_path or not os.path.exists(context.source_path):
            raise ValueError("Fichier source requis et doit exister")
        
        source_path = context.source_path
        
        context.update_progress("Préparation compression UPX...", 0.0)
        
        # Informations du fichier original
        original_size = os.path.getsize(source_path)
        
        # Sauvegarde si demandée
        backup_path = None
        if self.get_config_value("backup_original", True):
            backup_path = f"{source_path}.backup"
            try:
                shutil.copy2(source_path, backup_path)
                context.log("info", f"Sauvegarde créée: {backup_path}")
            except Exception as e:
                context.log("warning", f"Impossible de créer la sauvegarde: {e}")
        
        try:
            context.update_progress("Compression UPX en cours...", 0.2)
            
            # Construction de la commande
            cmd = self._build_upx_command(source_path)
            
            context.log("debug", f"Commande UPX: {' '.join(cmd)}")
            
            # Exécution
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max
            )
            
            context.update_progress("Compression terminée", 1.0)
            
            if result.returncode == 0:
                # Succès
                compressed_size = os.path.getsize(source_path)
                compression_ratio = (original_size - compressed_size) / original_size
                
                context.log("info", f"Compression réussie: {compression_ratio:.1%} de réduction")
                
                # Nettoie la sauvegarde si tout s'est bien passé
                if backup_path and os.path.exists(backup_path):
                    os.remove(backup_path)
                
                return {
                    "success": True,
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "compression_ratio": compression_ratio,
                    "upx_version": self.upx_version,
                    "output_path": source_path
                }
            else:
                # Échec - restaure la sauvegarde
                if backup_path and os.path.exists(backup_path):
                    shutil.move(backup_path, source_path)
                    context.log("info", "Fichier original restauré")
                
                error_msg = result.stderr or "Erreur UPX inconnue"
                context.log("error", f"Échec compression UPX: {error_msg}")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "original_size": original_size
                }
                
        except subprocess.TimeoutExpired:
            # Timeout - restaure la sauvegarde
            if backup_path and os.path.exists(backup_path):
                shutil.move(backup_path, source_path)
            
            error_msg = "Timeout lors de la compression UPX"
            context.log("error", error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "original_size": original_size
            }
        
        except Exception as e:
            # Erreur générale - restaure la sauvegarde
            if backup_path and os.path.exists(backup_path):
                shutil.move(backup_path, source_path)
            
            error_msg = f"Erreur lors de la compression: {e}"
            context.log("error", error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "original_size": original_size
            }
    
    def cleanup(self):
        """Nettoie les ressources du plugin"""
        # Rien à nettoyer pour UPX
        pass
    
    def _find_upx_executable(self) -> Optional[str]:
        """Trouve l'exécutable UPX"""
        
        # Chemin spécifié dans la config
        upx_path = self.get_config_value("upx_path")
        if upx_path and os.path.exists(upx_path):
            return upx_path
        
        # Recherche dans le PATH
        upx_executable = shutil.which("upx")
        if upx_executable:
            return upx_executable
        
        # Emplacements communs
        common_locations = [
            "/usr/bin/upx",
            "/usr/local/bin/upx",
            "C:\\Program Files\\UPX\\upx.exe",
            "C:\\Program Files (x86)\\UPX\\upx.exe",
            "C:\\Tools\\upx.exe"
        ]
        
        for location in common_locations:
            if os.path.exists(location):
                return location
        
        return None
    
    def _get_upx_version(self) -> Optional[str]:
        """Récupère la version d'UPX"""
        if not self.upx_path:
            return None
        
        try:
            result = subprocess.run(
                [self.upx_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'upx' in line.lower() and any(c.isdigit() for c in line):
                        return line.strip()
        except Exception:
            pass
        
        return None
    
    def _build_upx_command(self, file_path: str) -> list:
        """Construit la commande UPX"""
        
        cmd = [self.upx_path]
        
        # Niveau de compression
        level = self.get_config_value("compression_level", 9)
        
        if self.get_config_value("ultra_brute", False) or level >= 9:
            cmd.append("--ultra-brute")
        elif level >= 7:
            cmd.append("--best")
        else:
            cmd.append(f"-{level}")
        
        # Options avancées
        if not self.get_config_value("compress_icons", True):
            cmd.append("--compress-icons=0")
        
        if self.get_config_value("strip_relocs", False):
            cmd.append("--strip-relocs=1")
        
        # Options communes
        cmd.extend([
            "--force",  # Force la compression
            "-qq",      # Mode silencieux
        ])
        
        # Fichier cible
        cmd.append(file_path)
        
        return cmd
    
    def get_file_type_score(self, file_path: str) -> int:
        """Retourne un score de compatibilité pour un type de fichier"""
        
        if not os.path.exists(file_path):
            return 0
        
        # Détection du type de fichier
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
            
            # PE (Windows)
            if header.startswith(b'MZ'):
                return 100
            
            # ELF (Linux)
            elif header.startswith(b'\x7fELF'):
                return 90
            
            # Mach-O (macOS)
            elif header.startswith(b'\xca\xfe\xba\xbe'):
                return 85
            
            # Autres formats
            else:
                return 0
                
        except Exception:
            return 0
    
    def supports_file(self, file_path: str) -> bool:
        """Vérifie si UPX peut compresser ce fichier"""
        return self.get_file_type_score(file_path) > 0
    
    def get_estimated_compression_ratio(self, file_path: str) -> float:
        """Estime le ratio de compression pour un fichier"""
        
        if not self.supports_file(file_path):
            return 0.0
        
        file_size = os.path.getsize(file_path)
        
        # Estimations basées sur des observations
        if file_size < 100 * 1024:  # < 100KB
            return 0.3  # 30% de réduction
        elif file_size < 1024 * 1024:  # < 1MB
            return 0.5  # 50% de réduction
        elif file_size < 10 * 1024 * 1024:  # < 10MB
            return 0.6  # 60% de réduction
        else:
            return 0.7  # 70% de réduction
    
    def validate_environment(self) -> Dict[str, Any]:
        """Valide l'environnement pour UPX"""
        
        validation = {
            "upx_available": False,
            "upx_version": None,
            "upx_path": None,
            "permissions": False,
            "issues": []
        }
        
        # Vérifie UPX
        if self.upx_path:
            validation["upx_available"] = True
            validation["upx_path"] = self.upx_path
            validation["upx_version"] = self.upx_version
        else:
            validation["issues"].append("UPX non trouvé")
        
        # Vérifie les permissions
        if self.upx_path and os.access(self.upx_path, os.X_OK):
            validation["permissions"] = True
        else:
            validation["issues"].append("Permissions insuffisantes pour UPX")
        
        return validation