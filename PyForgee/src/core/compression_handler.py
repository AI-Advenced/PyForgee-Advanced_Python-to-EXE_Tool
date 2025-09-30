#!/usr/bin/env python3
"""
Gestionnaire de compression avancé pour PyForgee
Support UPX, LZMA, Brotli et algorithmes personnalisés
"""

import os
import sys
import subprocess
import shutil
import tempfile
import logging
import lzma
import gzip
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import struct

# Import conditionnel pour Brotli
try:
    import brotli
    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False

from ..utils.system_utils import SystemUtils
from ..utils.file_utils import FileUtils


class CompressionMethod(Enum):
    """Méthodes de compression disponibles"""
    UPX = "upx"
    LZMA = "lzma"
    BROTLI = "brotli"
    GZIP = "gzip"
    CUSTOM = "custom"
    AUTO = "auto"


@dataclass
class CompressionOptions:
    """Options de compression"""
    method: CompressionMethod = CompressionMethod.AUTO
    level: int = 9
    preserve_resources: bool = True
    backup_original: bool = True
    
    # Options UPX
    upx_ultra_brute: bool = False
    upx_compress_icons: bool = True
    upx_strip_relocs: bool = False
    
    # Options LZMA
    lzma_preset: int = 9
    lzma_check: int = 1  # CRC32
    
    # Options Brotli
    brotli_quality: int = 11
    brotli_window_bits: int = 22
    
    # Options personnalisées
    custom_algorithm: Optional[str] = None
    exclude_patterns: List[str] = None
    
    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = []


@dataclass
class CompressionResult:
    """Résultat de compression"""
    success: bool
    original_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    compression_time: float = 0.0
    method_used: Optional[CompressionMethod] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        
        if self.original_size > 0 and self.compressed_size > 0:
            self.compression_ratio = (self.original_size - self.compressed_size) / self.original_size


class CompressionBackend(ABC):
    """Classe abstraite pour les backends de compression"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"PyForgee.compression.{name}")
    
    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si ce backend est disponible"""
        pass
    
    @abstractmethod
    def get_version(self) -> Optional[str]:
        """Retourne la version du compresseur"""
        pass
    
    @abstractmethod
    async def compress(self, file_path: str, options: CompressionOptions) -> CompressionResult:
        """Compresse un fichier"""
        pass
    
    @abstractmethod
    def get_score(self, file_path: str, options: CompressionOptions) -> int:
        """Retourne un score pour ce compresseur (0-100)"""
        pass
    
    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Obtient les informations d'un fichier"""
        try:
            stat = os.stat(file_path)
            return {
                'size': stat.st_size,
                'is_executable': os.access(file_path, os.X_OK),
                'extension': Path(file_path).suffix.lower(),
                'type': self._detect_file_type(file_path)
            }
        except Exception as e:
            self.logger.error(f"Erreur lecture fichier {file_path}: {e}")
            return {}
    
    def _detect_file_type(self, file_path: str) -> str:
        """Détecte le type de fichier"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
            
            # Détection par signature
            if header.startswith(b'MZ'):
                return 'pe_executable'
            elif header.startswith(b'\x7fELF'):
                return 'elf_executable'
            elif header.startswith(b'\xca\xfe\xba\xbe'):
                return 'mach_executable'
            else:
                return 'unknown'
        except:
            return 'unknown'


class UPXCompressor(CompressionBackend):
    """Compresseur UPX pour exécutables"""
    
    def __init__(self):
        super().__init__("upx")
        self._upx_path = self._find_upx_executable()
    
    def _find_upx_executable(self) -> Optional[str]:
        """Trouve l'exécutable UPX"""
        # Essaye différents emplacements
        possible_paths = [
            "upx",
            "upx.exe", 
            "/usr/bin/upx",
            "/usr/local/bin/upx",
            "C:\\Program Files\\UPX\\upx.exe",
            "C:\\Program Files (x86)\\UPX\\upx.exe"
        ]
        
        for path in possible_paths:
            if shutil.which(path):
                return path
        
        return None
    
    def is_available(self) -> bool:
        """Vérifie si UPX est disponible"""
        if not self._upx_path:
            return False
        
        try:
            result = subprocess.run(
                [self._upx_path, "--version"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    def get_version(self) -> Optional[str]:
        """Retourne la version d'UPX"""
        if not self._upx_path:
            return None
        
        try:
            result = subprocess.run(
                [self._upx_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'upx' in line.lower() and any(c.isdigit() for c in line):
                        return line.strip()
        except:
            pass
        
        return None
    
    async def compress(self, file_path: str, options: CompressionOptions) -> CompressionResult:
        """Compresse avec UPX"""
        import time
        import asyncio
        
        start_time = time.time()
        
        if not self._upx_path:
            return CompressionResult(
                success=False,
                error_message="UPX non disponible"
            )
        
        # Informations du fichier original
        try:
            original_size = os.path.getsize(file_path)
        except Exception as e:
            return CompressionResult(
                success=False,
                error_message=f"Erreur lecture fichier: {e}"
            )
        
        # Sauvegarde si demandée
        backup_path = None
        if options.backup_original:
            backup_path = f"{file_path}.backup"
            try:
                shutil.copy2(file_path, backup_path)
            except Exception as e:
                self.logger.warning(f"Impossible de sauvegarder: {e}")
        
        try:
            # Construction de la commande UPX
            cmd = [self._upx_path]
            
            # Niveau de compression
            if options.level >= 9 or options.upx_ultra_brute:
                cmd.append("--ultra-brute")
            elif options.level >= 7:
                cmd.append("--best")
            elif options.level >= 4:
                cmd.extend(["-9"])
            else:
                cmd.extend([f"-{options.level}"])
            
            # Options avancées
            if not options.upx_compress_icons:
                cmd.append("--compress-icons=0")
            
            if options.upx_strip_relocs:
                cmd.append("--strip-relocs=1")
                
            if not options.preserve_resources:
                cmd.append("--compress-resources=1")
            
            # Options communes
            cmd.extend([
                "--force",  # Force la compression
                "-qq",      # Mode silencieux
            ])
            
            # Fichier cible
            cmd.append(file_path)
            
            self.logger.info(f"Commande UPX: {' '.join(cmd)}")
            
            # Exécution asynchrone
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            compression_time = time.time() - start_time
            
            if process.returncode == 0:
                # Succès
                try:
                    compressed_size = os.path.getsize(file_path)
                    
                    return CompressionResult(
                        success=True,
                        original_size=original_size,
                        compressed_size=compressed_size,
                        compression_time=compression_time,
                        method_used=CompressionMethod.UPX,
                        output_path=file_path
                    )
                except Exception as e:
                    return CompressionResult(
                        success=False,
                        error_message=f"Erreur post-compression: {e}",
                        compression_time=compression_time
                    )
            else:
                # Restaure la sauvegarde en cas d'erreur
                if backup_path and os.path.exists(backup_path):
                    try:
                        shutil.move(backup_path, file_path)
                    except:
                        pass
                
                error_msg = stderr.decode('utf-8', errors='ignore') if stderr else "Erreur UPX inconnue"
                return CompressionResult(
                    success=False,
                    error_message=error_msg,
                    compression_time=compression_time,
                    original_size=original_size
                )
                
        except Exception as e:
            # Restaure la sauvegarde en cas d'exception
            if backup_path and os.path.exists(backup_path):
                try:
                    shutil.move(backup_path, file_path)
                except:
                    pass
            
            return CompressionResult(
                success=False,
                error_message=str(e),
                compression_time=time.time() - start_time,
                original_size=original_size
            )
        
        finally:
            # Nettoie la sauvegarde si tout s'est bien passé
            if backup_path and os.path.exists(backup_path) and os.path.exists(file_path):
                try:
                    os.remove(backup_path)
                except:
                    pass
    
    def get_score(self, file_path: str, options: CompressionOptions) -> int:
        """Score UPX selon le fichier et les options"""
        file_info = self._get_file_info(file_path)
        
        score = 50  # Score de base
        
        # Bonus pour les exécutables
        if file_info.get('type') == 'pe_executable':
            score += 40
        elif file_info.get('is_executable'):
            score += 30
        
        # Bonus pour les gros fichiers
        size = file_info.get('size', 0)
        if size > 10 * 1024 * 1024:  # > 10MB
            score += 10
        elif size > 1 * 1024 * 1024:  # > 1MB
            score += 5
        
        # Malus pour les petits fichiers
        if size < 100 * 1024:  # < 100KB
            score -= 20
        
        return min(100, max(0, score))


class LZMACompressor(CompressionBackend):
    """Compresseur LZMA pour données générales"""
    
    def __init__(self):
        super().__init__("lzma")
    
    def is_available(self) -> bool:
        """LZMA est toujours disponible en Python 3.3+"""
        return True
    
    def get_version(self) -> Optional[str]:
        """Version LZMA intégrée"""
        try:
            import lzma
            return f"Python LZMA (liblzma)"
        except ImportError:
            return None
    
    async def compress(self, file_path: str, options: CompressionOptions) -> CompressionResult:
        """Compresse avec LZMA"""
        import time
        
        start_time = time.time()
        
        try:
            # Lecture du fichier original
            with open(file_path, 'rb') as f:
                original_data = f.read()
            
            original_size = len(original_data)
            
            # Compression LZMA
            compressed_data = lzma.compress(
                original_data,
                format=lzma.FORMAT_XZ,
                check=options.lzma_check,
                preset=options.lzma_preset
            )
            
            compressed_size = len(compressed_data)
            
            # Écriture du fichier compressé
            compressed_path = f"{file_path}.lzma"
            with open(compressed_path, 'wb') as f:
                f.write(compressed_data)
            
            compression_time = time.time() - start_time
            
            return CompressionResult(
                success=True,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_time=compression_time,
                method_used=CompressionMethod.LZMA,
                output_path=compressed_path
            )
            
        except Exception as e:
            return CompressionResult(
                success=False,
                error_message=str(e),
                compression_time=time.time() - start_time
            )
    
    def get_score(self, file_path: str, options: CompressionOptions) -> int:
        """Score LZMA selon le fichier"""
        file_info = self._get_file_info(file_path)
        
        score = 60  # Score de base correct
        
        # Bonus pour les gros fichiers
        size = file_info.get('size', 0)
        if size > 1 * 1024 * 1024:  # > 1MB
            score += 20
        
        # Malus pour les exécutables (UPX est mieux)
        if file_info.get('type') == 'pe_executable':
            score -= 30
        
        return min(100, max(0, score))


class BrotliCompressor(CompressionBackend):
    """Compresseur Brotli pour données web"""
    
    def __init__(self):
        super().__init__("brotli")
    
    def is_available(self) -> bool:
        """Vérifie si Brotli est disponible"""
        return BROTLI_AVAILABLE
    
    def get_version(self) -> Optional[str]:
        """Version Brotli"""
        if not BROTLI_AVAILABLE:
            return None
        try:
            return f"Brotli {brotli.__version__}"
        except:
            return "Brotli (version inconnue)"
    
    async def compress(self, file_path: str, options: CompressionOptions) -> CompressionResult:
        """Compresse avec Brotli"""
        import time
        
        if not BROTLI_AVAILABLE:
            return CompressionResult(
                success=False,
                error_message="Brotli non disponible"
            )
        
        start_time = time.time()
        
        try:
            # Lecture du fichier original
            with open(file_path, 'rb') as f:
                original_data = f.read()
            
            original_size = len(original_data)
            
            # Compression Brotli
            compressed_data = brotli.compress(
                original_data,
                quality=options.brotli_quality,
                lgwin=options.brotli_window_bits
            )
            
            compressed_size = len(compressed_data)
            
            # Écriture du fichier compressé
            compressed_path = f"{file_path}.br"
            with open(compressed_path, 'wb') as f:
                f.write(compressed_data)
            
            compression_time = time.time() - start_time
            
            return CompressionResult(
                success=True,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_time=compression_time,
                method_used=CompressionMethod.BROTLI,
                output_path=compressed_path
            )
            
        except Exception as e:
            return CompressionResult(
                success=False,
                error_message=str(e),
                compression_time=time.time() - start_time
            )
    
    def get_score(self, file_path: str, options: CompressionOptions) -> int:
        """Score Brotli selon le fichier"""
        file_info = self._get_file_info(file_path)
        
        score = 65  # Score de base bon
        
        # Bonus pour les fichiers texte/web
        ext = file_info.get('extension', '')
        if ext in ['.txt', '.js', '.css', '.html', '.json', '.xml']:
            score += 25
        
        # Malus pour les exécutables
        if file_info.get('type') == 'pe_executable':
            score -= 40
        
        return min(100, max(0, score))


class CustomCompressor(CompressionBackend):
    """Compresseur personnalisé avec algorithmes optimisés"""
    
    def __init__(self):
        super().__init__("custom")
    
    def is_available(self) -> bool:
        """Toujours disponible"""
        return True
    
    def get_version(self) -> Optional[str]:
        """Version personnalisée"""
        return "PyForgee Custom Compressor 1.0"
    
    async def compress(self, file_path: str, options: CompressionOptions) -> CompressionResult:
        """Compression personnalisée optimisée"""
        import time
        
        start_time = time.time()
        
        try:
            # Lecture et analyse du fichier
            with open(file_path, 'rb') as f:
                original_data = f.read()
            
            original_size = len(original_data)
            
            # Sélection de l'algorithme optimal selon le contenu
            compressed_data = self._optimal_compress(original_data, options)
            
            compressed_size = len(compressed_data)
            
            # Écriture avec en-tête personnalisé
            compressed_path = f"{file_path}.pfc"  # PyForgee Compressed
            with open(compressed_path, 'wb') as f:
                # En-tête: magic + method + original_size
                f.write(b'PFC\x01')  # Magic + version
                f.write(struct.pack('<I', original_size))
                f.write(compressed_data)
            
            compression_time = time.time() - start_time
            
            return CompressionResult(
                success=True,
                original_size=original_size,
                compressed_size=compressed_size + 8,  # +8 pour l'en-tête
                compression_time=compression_time,
                method_used=CompressionMethod.CUSTOM,
                output_path=compressed_path
            )
            
        except Exception as e:
            return CompressionResult(
                success=False,
                error_message=str(e),
                compression_time=time.time() - start_time
            )
    
    def _optimal_compress(self, data: bytes, options: CompressionOptions) -> bytes:
        """Sélectionne et applique la compression optimale"""
        
        # Analyse du contenu
        entropy = self._calculate_entropy(data)
        repetition_ratio = self._calculate_repetition_ratio(data)
        
        # Sélection de l'algorithme
        if entropy < 6.0 and repetition_ratio > 0.3:
            # Données très répétitives -> LZMA
            return lzma.compress(data, preset=options.lzma_preset or 9)
        elif BROTLI_AVAILABLE and len(data) < 1024 * 1024:
            # Petits fichiers -> Brotli
            return brotli.compress(data, quality=options.brotli_quality or 11)
        else:
            # Défaut -> LZMA
            return lzma.compress(data, preset=options.lzma_preset or 6)
    
    def _calculate_entropy(self, data: bytes) -> float:
        """Calcule l'entropie des données"""
        if not data:
            return 0.0
        
        # Comptage des fréquences
        freq = {}
        for byte in data:
            freq[byte] = freq.get(byte, 0) + 1
        
        # Calcul de l'entropie de Shannon
        import math
        entropy = 0.0
        data_len = len(data)
        
        for count in freq.values():
            if count > 0:
                prob = count / data_len
                entropy -= prob * math.log2(prob)
        
        return entropy
    
    def _calculate_repetition_ratio(self, data: bytes) -> float:
        """Calcule le ratio de répétition dans les données"""
        if len(data) < 100:
            return 0.0
        
        # Recherche de patterns répétés
        sample_size = min(1000, len(data))
        sample = data[:sample_size]
        
        repeated_bytes = 0
        for i in range(1, len(sample)):
            if sample[i] == sample[i-1]:
                repeated_bytes += 1
        
        return repeated_bytes / (sample_size - 1)
    
    def get_score(self, file_path: str, options: CompressionOptions) -> int:
        """Score personnalisé adaptatif"""
        file_info = self._get_file_info(file_path)
        
        score = 70  # Score de base élevé
        
        # Bonus pour la flexibilité
        score += 15
        
        # Bonus selon la taille
        size = file_info.get('size', 0)
        if size > 500 * 1024:  # > 500KB
            score += 10
        
        return min(100, max(0, score))


class CompressionHandler:
    """Gestionnaire principal de compression"""
    
    def __init__(self):
        self.logger = logging.getLogger("PyForgee.compression")
        
        # Initialisation des compresseurs
        self.compressors = {
            CompressionMethod.UPX: UPXCompressor(),
            CompressionMethod.LZMA: LZMACompressor(),
            CompressionMethod.BROTLI: BrotliCompressor(),
            CompressionMethod.CUSTOM: CustomCompressor(),
        }
        
        self.available_compressors = self._detect_compressors()
        self.logger.info(f"Compresseurs disponibles: {list(self.available_compressors.keys())}")
    
    def _detect_compressors(self) -> Dict[CompressionMethod, CompressionBackend]:
        """Détecte les compresseurs disponibles"""
        available = {}
        
        for method, compressor in self.compressors.items():
            if compressor.is_available():
                version = compressor.get_version()
                self.logger.info(f"{method.value} disponible: {version}")
                available[method] = compressor
            else:
                self.logger.warning(f"{method.value} non disponible")
        
        return available
    
    def select_best_compressor(self, file_path: str, 
                              options: CompressionOptions) -> Tuple[CompressionMethod, CompressionBackend]:
        """Sélectionne le meilleur compresseur"""
        
        # Si une méthode spécifique est demandée
        if (options.method != CompressionMethod.AUTO and 
            options.method in self.available_compressors):
            return options.method, self.available_compressors[options.method]
        
        # Calcul des scores
        scores = {}
        for method, compressor in self.available_compressors.items():
            score = compressor.get_score(file_path, options)
            scores[method] = score
            self.logger.debug(f"Score {method.value}: {score}")
        
        if not scores:
            raise RuntimeError("Aucun compresseur disponible")
        
        # Sélection du meilleur
        best_method = max(scores.keys(), key=lambda k: scores[k])
        best_compressor = self.available_compressors[best_method]
        
        self.logger.info(f"Compresseur sélectionné: {best_method.value} (score: {scores[best_method]})")
        return best_method, best_compressor
    
    async def compress_executable(self, exe_path: str, 
                                 method: Union[CompressionMethod, str] = CompressionMethod.AUTO,
                                 **kwargs) -> CompressionResult:
        """Compresse un exécutable avec la méthode optimale"""
        
        # Validation
        if not os.path.exists(exe_path):
            return CompressionResult(
                success=False,
                error_message=f"Fichier non trouvé: {exe_path}"
            )
        
        # Création des options
        if isinstance(method, str):
            method = CompressionMethod(method)
        
        options = CompressionOptions(method=method, **kwargs)
        
        try:
            # Sélection du compresseur
            compression_method, compressor = self.select_best_compressor(exe_path, options)
            
            # Compression
            self.logger.info(f"Compression de {exe_path} avec {compression_method.value}")
            result = await compressor.compress(exe_path, options)
            
            if result.success:
                ratio = result.compression_ratio * 100
                self.logger.info(f"Compression réussie: {ratio:.1f}% de réduction")
                self.logger.info(f"Taille originale: {result.original_size} bytes")
                self.logger.info(f"Taille compressée: {result.compressed_size} bytes")
                self.logger.info(f"Temps: {result.compression_time:.2f}s")
            else:
                self.logger.error(f"Échec de la compression: {result.error_message}")
            
            return result
            
        except Exception as e:
            self.logger.exception("Erreur lors de la compression")
            return CompressionResult(
                success=False,
                error_message=str(e)
            )
    
    async def batch_compress(self, files: List[str], 
                           base_options: CompressionOptions) -> List[CompressionResult]:
        """Compresse plusieurs fichiers en parallèle"""
        import asyncio
        
        tasks = []
        for file_path in files:
            task = self.compress_executable(file_path, base_options.method, **base_options.__dict__)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traite les exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(CompressionResult(
                    success=False,
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def get_compressor_info(self) -> Dict[str, Any]:
        """Informations sur les compresseurs disponibles"""
        info = {}
        
        for method, compressor in self.compressors.items():
            info[method.value] = {
                "available": compressor.is_available(),
                "version": compressor.get_version() if compressor.is_available() else None,
                "description": f"Compresseur {method.value}"
            }
        
        return info


def create_compression_options(**kwargs) -> CompressionOptions:
    """Crée des options de compression par défaut"""
    return CompressionOptions(**kwargs)