#!/usr/bin/env python3
"""
Plugin Icon Manager pour PyForgee
Gestion et conversion d'icônes pour exécutables
"""

import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from .base_plugin import BasePlugin, PluginMetadata, PluginContext, PluginType, PluginPriority

# Imports conditionnels pour la manipulation d'images
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class IconManager(BasePlugin):
    """Plugin pour la gestion des icônes"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.ico', '.png', '.jpg', '.jpeg', '.bmp', '.gif']
        self.icon_sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
    
    def get_metadata(self) -> PluginMetadata:
        """Métadonnées du plugin Icon Manager"""
        return PluginMetadata(
            name="icon_manager",
            version="1.0.0",
            description="Gestion et conversion d'icônes pour exécutables",
            author="PyForgee Team",
            plugin_type=PluginType.TOOL,
            priority=PluginPriority.NORMAL,
            
            # Dépendances optionnelles
            optional_dependencies=["Pillow"],
            
            # Configuration
            config_schema={
                "default_icon_size": {
                    "type": "integer",
                    "description": "Taille d'icône par défaut",
                    "enum": [16, 20, 24, 32, 40, 48, 64, 96, 128, 256],
                    "default": 32
                },
                "generate_multiple_sizes": {
                    "type": "boolean",
                    "description": "Générer plusieurs tailles d'icône",
                    "default": True
                },
                "output_format": {
                    "type": "string",
                    "description": "Format de sortie",
                    "enum": ["ico", "png", "auto"],
                    "default": "auto"
                },
                "compression_quality": {
                    "type": "integer",
                    "description": "Qualité de compression (1-100)",
                    "min": 1,
                    "max": 100,
                    "default": 95
                },
                "preserve_aspect_ratio": {
                    "type": "boolean",
                    "description": "Préserver le ratio d'aspect",
                    "default": True
                },
                "add_padding": {
                    "type": "boolean",
                    "description": "Ajouter du padding si nécessaire",
                    "default": True
                },
                "background_color": {
                    "type": "string",
                    "description": "Couleur de fond (transparent, white, black, ou #RRGGBB)",
                    "default": "transparent"
                }
            },
            
            default_config={
                "default_icon_size": 32,
                "generate_multiple_sizes": True,
                "output_format": "auto",
                "compression_quality": 95,
                "preserve_aspect_ratio": True,
                "add_padding": True,
                "background_color": "transparent"
            }
        )
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialise le plugin Icon Manager"""
        self._config = config
        
        if not PIL_AVAILABLE:
            self.logger.warning("Pillow non disponible - fonctionnalités limitées")
        
        self.logger.info("Icon Manager initialisé")
        return True
    
    def execute(self, context: PluginContext) -> Dict[str, Any]:
        """Traite une icône selon le contexte"""
        
        if not context.source_path or not os.path.exists(context.source_path):
            raise ValueError("Fichier d'icône source requis et doit exister")
        
        source_path = Path(context.source_path)
        
        # Détermine l'action à effectuer
        action = context.config.get('action', 'convert')
        
        if action == 'convert':
            return self._convert_icon(source_path, context)
        elif action == 'validate':
            return self._validate_icon(source_path, context)
        elif action == 'extract':
            return self._extract_icon(context.config.get('executable_path'), context)
        elif action == 'generate_sizes':
            return self._generate_multiple_sizes(source_path, context)
        else:
            raise ValueError(f"Action non supportée: {action}")
    
    def cleanup(self):
        """Nettoie les ressources du plugin"""
        # Rien à nettoyer pour l'Icon Manager
        pass
    
    def _convert_icon(self, source_path: Path, context: PluginContext) -> Dict[str, Any]:
        """Convertit une icône vers le format désiré"""
        
        if not PIL_AVAILABLE:
            return {
                "success": False,
                "error": "Pillow requis pour la conversion d'icônes"
            }
        
        context.update_progress("Conversion d'icône en cours...", 0.0)
        
        try:
            # Charge l'image source
            with Image.open(source_path) as img:
                
                context.update_progress("Traitement de l'image...", 0.2)
                
                # Détermine le format de sortie
                output_format = self._determine_output_format(source_path)
                
                # Détermine le dossier de sortie
                if context.output_path:
                    output_dir = Path(context.output_path)
                else:
                    output_dir = source_path.parent
                
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Génère les icônes
                generated_files = []
                
                if self.get_config_value("generate_multiple_sizes", True) and output_format == 'ico':
                    # Génère un fichier ICO avec plusieurs tailles
                    ico_path = output_dir / f"{source_path.stem}.ico"
                    
                    context.update_progress("Génération des tailles multiples...", 0.4)
                    
                    sizes = self._get_icon_sizes_for_ico()
                    images = []
                    
                    for size in sizes:
                        resized_img = self._resize_image(img, size)
                        images.append(resized_img)
                    
                    context.update_progress("Sauvegarde du fichier ICO...", 0.8)
                    
                    # Sauvegarde en ICO
                    images[0].save(
                        ico_path,
                        format='ICO',
                        sizes=[(img.width, img.height) for img in images]
                    )
                    
                    generated_files.append(str(ico_path))
                    
                else:
                    # Génère une seule taille
                    size = self.get_config_value("default_icon_size", 32)
                    
                    context.update_progress(f"Redimensionnement vers {size}x{size}...", 0.4)
                    
                    resized_img = self._resize_image(img, size)
                    
                    # Détermine l'extension
                    if output_format == 'auto':
                        ext = '.ico' if self._is_windows_context(context) else '.png'
                    else:
                        ext = f'.{output_format}'
                    
                    output_path = output_dir / f"{source_path.stem}{ext}"
                    
                    context.update_progress("Sauvegarde...", 0.8)
                    
                    # Sauvegarde
                    save_kwargs = {}
                    if ext.lower() in ['.jpg', '.jpeg']:
                        save_kwargs['quality'] = self.get_config_value("compression_quality", 95)
                        save_kwargs['optimize'] = True
                    
                    resized_img.save(output_path, **save_kwargs)
                    generated_files.append(str(output_path))
                
                context.update_progress("Conversion terminée", 1.0)
                
                context.log("info", f"Icône convertie: {len(generated_files)} fichier(s) générés")
                
                return {
                    "success": True,
                    "generated_files": generated_files,
                    "output_format": output_format,
                    "original_size": (img.width, img.height)
                }
                
        except Exception as e:
            error_msg = f"Erreur lors de la conversion: {e}"
            context.log("error", error_msg)
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def _validate_icon(self, source_path: Path, context: PluginContext) -> Dict[str, Any]:
        """Valide un fichier d'icône"""
        
        context.update_progress("Validation de l'icône...", 0.0)
        
        validation = {
            "success": True,
            "valid": True,
            "issues": [],
            "info": {}
        }
        
        try:
            # Vérifications de base
            if not source_path.exists():
                validation["valid"] = False
                validation["issues"].append("Fichier inexistant")
                return validation
            
            if source_path.suffix.lower() not in self.supported_formats:
                validation["issues"].append(f"Format non supporté: {source_path.suffix}")
            
            # Vérifications avec PIL si disponible
            if PIL_AVAILABLE:
                try:
                    with Image.open(source_path) as img:
                        validation["info"] = {
                            "format": img.format,
                            "mode": img.mode,
                            "size": img.size,
                            "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                        }
                        
                        # Vérifications spécifiques
                        width, height = img.size
                        
                        if width != height:
                            validation["issues"].append("L'icône n'est pas carrée")
                        
                        if width > 256 or height > 256:
                            validation["issues"].append("Taille très grande (>256px)")
                        
                        if width < 16 or height < 16:
                            validation["issues"].append("Taille très petite (<16px)")
                        
                        if img.mode not in ('RGB', 'RGBA', 'P'):
                            validation["issues"].append(f"Mode couleur non optimal: {img.mode}")
                        
                except Exception as e:
                    validation["valid"] = False
                    validation["issues"].append(f"Erreur lecture image: {e}")
            else:
                validation["info"]["pil_available"] = False
                validation["issues"].append("Pillow non disponible - validation limitée")
            
            # Taille de fichier
            file_size = source_path.stat().st_size
            validation["info"]["file_size"] = file_size
            
            if file_size > 1024 * 1024:  # > 1MB
                validation["issues"].append("Taille de fichier importante (>1MB)")
            
            context.update_progress("Validation terminée", 1.0)
            
            if validation["issues"]:
                validation["valid"] = False
            
            return validation
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_icon(self, executable_path: str, context: PluginContext) -> Dict[str, Any]:
        """Extrait l'icône d'un exécutable"""
        
        if not executable_path or not os.path.exists(executable_path):
            return {
                "success": False,
                "error": "Chemin d'exécutable requis et doit exister"
            }
        
        context.update_progress("Extraction d'icône...", 0.0)
        
        # Cette fonctionnalité nécessiterait des bibliothèques spécialisées
        # comme win32api sur Windows ou des outils système
        
        return {
            "success": False,
            "error": "Extraction d'icône non implémentée - nécessite des dépendances supplémentaires"
        }
    
    def _generate_multiple_sizes(self, source_path: Path, context: PluginContext) -> Dict[str, Any]:
        """Génère plusieurs tailles d'une icône"""
        
        if not PIL_AVAILABLE:
            return {
                "success": False,
                "error": "Pillow requis pour générer plusieurs tailles"
            }
        
        context.update_progress("Génération de tailles multiples...", 0.0)
        
        try:
            with Image.open(source_path) as img:
                
                # Détermine le dossier de sortie
                if context.output_path:
                    output_dir = Path(context.output_path)
                else:
                    output_dir = source_path.parent / f"{source_path.stem}_sizes"
                
                output_dir.mkdir(parents=True, exist_ok=True)
                
                generated_files = []
                sizes = self.get_config_value("icon_sizes", self.icon_sizes)
                
                for i, size in enumerate(sizes):
                    context.update_progress(f"Génération {size}x{size}...", i / len(sizes))
                    
                    resized_img = self._resize_image(img, size)
                    output_file = output_dir / f"{source_path.stem}_{size}x{size}.png"
                    
                    resized_img.save(output_file, optimize=True)
                    generated_files.append(str(output_file))
                
                context.update_progress("Génération terminée", 1.0)
                
                return {
                    "success": True,
                    "generated_files": generated_files,
                    "sizes_generated": sizes
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _resize_image(self, img: 'Image.Image', size: int) -> 'Image.Image':
        """Redimensionne une image avec les options configurées"""
        
        target_size = (size, size)
        
        # Préserve le ratio d'aspect si demandé
        if self.get_config_value("preserve_aspect_ratio", True):
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # Ajoute du padding si nécessaire
            if self.get_config_value("add_padding", True) and img.size != target_size:
                
                # Détermine la couleur de fond
                bg_color = self._get_background_color()
                
                # Crée une nouvelle image avec padding
                new_img = Image.new('RGBA', target_size, bg_color)
                
                # Centre l'image redimensionnée
                x = (target_size[0] - img.width) // 2
                y = (target_size[1] - img.height) // 2
                
                if img.mode == 'RGBA' or 'transparency' in img.info:
                    new_img.paste(img, (x, y), img)
                else:
                    new_img.paste(img, (x, y))
                
                return new_img
            
            return img
        else:
            # Redimensionne directement
            return img.resize(target_size, Image.Resampling.LANCZOS)
    
    def _get_background_color(self) -> Tuple[int, int, int, int]:
        """Retourne la couleur de fond configurée"""
        
        bg_color = self.get_config_value("background_color", "transparent")
        
        if bg_color == "transparent":
            return (0, 0, 0, 0)
        elif bg_color == "white":
            return (255, 255, 255, 255)
        elif bg_color == "black":
            return (0, 0, 0, 255)
        elif bg_color.startswith("#") and len(bg_color) == 7:
            # Format hexadécimal #RRGGBB
            try:
                r = int(bg_color[1:3], 16)
                g = int(bg_color[3:5], 16)
                b = int(bg_color[5:7], 16)
                return (r, g, b, 255)
            except ValueError:
                pass
        
        # Défaut: transparent
        return (0, 0, 0, 0)
    
    def _determine_output_format(self, source_path: Path) -> str:
        """Détermine le format de sortie optimal"""
        
        output_format = self.get_config_value("output_format", "auto")
        
        if output_format == "auto":
            # Logique automatique
            if source_path.suffix.lower() == '.ico':
                return 'ico'
            else:
                return 'png'  # PNG par défaut pour la qualité
        
        return output_format
    
    def _get_icon_sizes_for_ico(self) -> List[int]:
        """Retourne les tailles optimales pour un fichier ICO"""
        # Tailles courantes pour Windows
        return [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
    
    def _is_windows_context(self, context: PluginContext) -> bool:
        """Détermine si on est dans un contexte Windows"""
        
        # Vérifie le contexte ou l'OS
        target_platform = context.config.get('target_platform', 'auto')
        
        if target_platform == 'windows':
            return True
        elif target_platform in ['linux', 'macos']:
            return False
        else:
            # Auto-détection
            import sys
            return sys.platform == 'win32'
    
    def get_supported_formats(self) -> List[str]:
        """Retourne les formats supportés"""
        return self.supported_formats.copy()
    
    def is_valid_icon_size(self, size: int) -> bool:
        """Vérifie si une taille d'icône est valide"""
        return size in self.icon_sizes or (16 <= size <= 512)
    
    def suggest_icon_size(self, use_case: str) -> int:
        """Suggère une taille d'icône selon le cas d'usage"""
        
        suggestions = {
            'desktop': 48,
            'taskbar': 32,
            'system_tray': 16,
            'large_icons': 96,
            'retina': 128,
            'high_dpi': 256
        }
        
        return suggestions.get(use_case, 32)