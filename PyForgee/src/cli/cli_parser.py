#!/usr/bin/env python3
"""
Parser avancé pour l'interface CLI de PyForgee
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from ..core.compiler_engine import CompilerType
from ..core.compression_handler import CompressionMethod
from ..core.protection_manager import ProtectionLevel


@dataclass
class CLIArguments:
    """Structure pour les arguments CLI parsés"""
    command: str
    source_path: Optional[str] = None
    output_path: Optional[str] = None
    output_name: Optional[str] = None
    
    # Compilation
    compiler: Optional[CompilerType] = None
    onefile: bool = True
    console: bool = False
    optimize: bool = False
    icon_path: Optional[str] = None
    exclude_modules: List[str] = None
    hidden_imports: List[str] = None
    
    # Compression
    compression_method: CompressionMethod = CompressionMethod.AUTO
    compression_level: int = 9
    backup_original: bool = True
    
    # Protection
    protection_level: ProtectionLevel = ProtectionLevel.INTERMEDIATE
    obfuscate_names: bool = False
    obfuscate_strings: bool = False
    encrypt_bytecode: bool = False
    add_anti_debug: bool = False
    
    # Options générales
    verbose: bool = False
    quiet: bool = False
    config_file: Optional[str] = None
    log_file: Optional[str] = None
    parallel: bool = True
    max_workers: int = 4
    
    # Analyse
    deep_analysis: bool = False
    include_stdlib: bool = False
    export_format: str = "text"
    
    # Batch
    batch_files: List[str] = None
    batch_config: Optional[str] = None
    
    def __post_init__(self):
        if self.exclude_modules is None:
            self.exclude_modules = []
        if self.hidden_imports is None:
            self.hidden_imports = []
        if self.batch_files is None:
            self.batch_files = []


class CLIParser:
    """Parser avancé pour les arguments CLI"""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Crée le parser principal avec toutes les commandes"""
        
        parser = argparse.ArgumentParser(
            prog='PyForgee',
            description='PyForgee - Outil Python-to-EXE avancé',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_examples()
        )
        
        # Options globales
        parser.add_argument(
            '--version', action='version', 
            version='%(prog)s 1.0.0'
        )
        
        parser.add_argument(
            '-v', '--verbose', action='store_true',
            help='Mode verbose'
        )
        
        parser.add_argument(
            '-q', '--quiet', action='store_true',
            help='Mode silencieux'
        )
        
        parser.add_argument(
            '-c', '--config', type=str, metavar='FILE',
            help='Fichier de configuration'
        )
        
        parser.add_argument(
            '--log-file', type=str, metavar='FILE',
            help='Fichier de log'
        )
        
        # Sous-commandes
        subparsers = parser.add_subparsers(
            dest='command', 
            help='Commandes disponibles'
        )
        
        # Commande compile
        self._add_compile_parser(subparsers)
        
        # Commande analyze
        self._add_analyze_parser(subparsers)
        
        # Commande compress
        self._add_compress_parser(subparsers)
        
        # Commande protect
        self._add_protect_parser(subparsers)
        
        # Commande batch
        self._add_batch_parser(subparsers)
        
        # Commande info
        self._add_info_parser(subparsers)
        
        # Commande config
        self._add_config_parser(subparsers)
        
        return parser
    
    def _add_compile_parser(self, subparsers):
        """Ajoute le parser pour la commande compile"""
        
        compile_parser = subparsers.add_parser(
            'compile', 
            help='Compile un script Python en exécutable',
            description='Compile un script Python en exécutable avec options avancées'
        )
        
        # Fichier source (requis)
        compile_parser.add_argument(
            'source', type=str,
            help='Fichier Python source à compiler'
        )
        
        # Options de base
        compile_parser.add_argument(
            '-o', '--output', type=str, metavar='DIR',
            help='Dossier de sortie (défaut: ./dist)'
        )
        
        compile_parser.add_argument(
            '-n', '--name', type=str,
            help='Nom de l\'exécutable'
        )
        
        compile_parser.add_argument(
            '--compiler', type=str, 
            choices=['auto', 'pyinstaller', 'nuitka', 'cx_freeze'],
            default='auto',
            help='Compilateur à utiliser (défaut: auto)'
        )
        
        # Options d'exécutable
        compile_parser.add_argument(
            '--onefile', action='store_true', default=True,
            help='Créer un fichier unique (défaut)'
        )
        
        compile_parser.add_argument(
            '--no-onefile', dest='onefile', action='store_false',
            help='Créer un dossier avec dépendances'
        )
        
        compile_parser.add_argument(
            '--console', action='store_true',
            help='Mode console (avec fenêtre terminal)'
        )
        
        compile_parser.add_argument(
            '--windowed', dest='console', action='store_false',
            help='Mode fenêtré (sans terminal)'
        )
        
        compile_parser.add_argument(
            '--optimize', action='store_true',
            help='Active les optimisations avancées'
        )
        
        compile_parser.add_argument(
            '--icon', type=str, metavar='FILE',
            help='Fichier icône (.ico sur Windows)'
        )
        
        # Dépendances
        compile_parser.add_argument(
            '--exclude', action='append', metavar='MODULE',
            help='Module à exclure (peut être répété)'
        )
        
        compile_parser.add_argument(
            '--hidden-import', action='append', metavar='MODULE',
            help='Import caché à inclure (peut être répété)'
        )
        
        # Compression
        compile_parser.add_argument(
            '--compress', type=str,
            choices=['none', 'auto', 'upx', 'lzma', 'brotli', 'custom'],
            default='auto',
            help='Méthode de compression (défaut: auto)'
        )
        
        compile_parser.add_argument(
            '--compression-level', type=int, choices=range(1, 10),
            default=9, metavar='LEVEL',
            help='Niveau de compression 1-9 (défaut: 9)'
        )
        
        # Protection
        compile_parser.add_argument(
            '--protect', type=str,
            choices=['none', 'basic', 'intermediate', 'advanced', 'maximum'],
            default='none',
            help='Niveau de protection (défaut: none)'
        )
        
        compile_parser.add_argument(
            '--obfuscate-names', action='store_true',
            help='Obfusque les noms de variables/fonctions'
        )
        
        compile_parser.add_argument(
            '--obfuscate-strings', action='store_true',
            help='Obfusque les chaînes de caractères'
        )
        
        compile_parser.add_argument(
            '--encrypt-bytecode', action='store_true',
            help='Chiffre le bytecode'
        )
        
        compile_parser.add_argument(
            '--anti-debug', action='store_true',
            help='Ajoute des protections anti-debugging'
        )
        
        # Options avancées
        compile_parser.add_argument(
            '--no-backup', dest='backup_original', action='store_false',
            help='Ne pas sauvegarder les fichiers originaux'
        )
    
    def _add_analyze_parser(self, subparsers):
        """Ajoute le parser pour la commande analyze"""
        
        analyze_parser = subparsers.add_parser(
            'analyze',
            help='Analyse les dépendances d\'un script',
            description='Analyse statique et dynamique des dépendances'
        )
        
        analyze_parser.add_argument(
            'source', type=str,
            help='Fichier Python à analyser'
        )
        
        analyze_parser.add_argument(
            '-o', '--output', type=str, metavar='FILE',
            help='Fichier de sortie pour le rapport'
        )
        
        analyze_parser.add_argument(
            '--format', type=str,
            choices=['text', 'json', 'yaml', 'csv'],
            default='text',
            help='Format de sortie (défaut: text)'
        )
        
        analyze_parser.add_argument(
            '--deep', action='store_true',
            help='Analyse récursive approfondie'
        )
        
        analyze_parser.add_argument(
            '--include-stdlib', action='store_true',
            help='Inclure les modules de la bibliothèque standard'
        )
        
        analyze_parser.add_argument(
            '--suggest-optimizations', action='store_true',
            help='Suggère des optimisations'
        )
    
    def _add_compress_parser(self, subparsers):
        """Ajoute le parser pour la commande compress"""
        
        compress_parser = subparsers.add_parser(
            'compress',
            help='Compresse des fichiers exécutables',
            description='Compression avancée d\'exécutables'
        )
        
        compress_parser.add_argument(
            'files', nargs='+', type=str,
            help='Fichiers à compresser'
        )
        
        compress_parser.add_argument(
            '--method', type=str,
            choices=['auto', 'upx', 'lzma', 'brotli', 'custom'],
            default='auto',
            help='Méthode de compression (défaut: auto)'
        )
        
        compress_parser.add_argument(
            '--level', type=int, choices=range(1, 10),
            default=9, metavar='LEVEL',
            help='Niveau de compression 1-9 (défaut: 9)'
        )
        
        compress_parser.add_argument(
            '--no-backup', dest='backup_original', action='store_false',
            help='Ne pas sauvegarder les originaux'
        )
        
        compress_parser.add_argument(
            '--parallel', action='store_true', default=True,
            help='Compression parallèle (défaut)'
        )
        
        compress_parser.add_argument(
            '--no-parallel', dest='parallel', action='store_false',
            help='Compression séquentielle'
        )
    
    def _add_protect_parser(self, subparsers):
        """Ajoute le parser pour la commande protect"""
        
        protect_parser = subparsers.add_parser(
            'protect',
            help='Protège du code Python',
            description='Protection avancée contre la décompilation'
        )
        
        protect_parser.add_argument(
            'source', type=str,
            help='Fichier ou dossier Python à protéger'
        )
        
        protect_parser.add_argument(
            '-o', '--output', type=str, metavar='DIR',
            help='Dossier de sortie'
        )
        
        protect_parser.add_argument(
            '--level', type=str,
            choices=['basic', 'intermediate', 'advanced', 'maximum'],
            default='intermediate',
            help='Niveau de protection (défaut: intermediate)'
        )
        
        protect_parser.add_argument(
            '--methods', type=str, nargs='+',
            choices=['pyarmor', 'custom', 'bytecode', 'string_encoding', 'control_flow'],
            help='Méthodes de protection à utiliser'
        )
        
        protect_parser.add_argument(
            '--obfuscate-names', action='store_true',
            help='Obfusque les noms'
        )
        
        protect_parser.add_argument(
            '--obfuscate-strings', action='store_true',
            help='Obfusque les chaînes'
        )
        
        protect_parser.add_argument(
            '--encrypt-bytecode', action='store_true',
            help='Chiffre le bytecode'
        )
        
        protect_parser.add_argument(
            '--anti-debug', action='store_true',
            help='Protection anti-debugging'
        )
        
        protect_parser.add_argument(
            '--custom-key', type=str,
            help='Clé personnalisée pour le chiffrement'
        )
    
    def _add_batch_parser(self, subparsers):
        """Ajoute le parser pour la commande batch"""
        
        batch_parser = subparsers.add_parser(
            'batch',
            help='Compile plusieurs fichiers en lot',
            description='Compilation en lot avec configuration'
        )
        
        batch_parser.add_argument(
            'files', nargs='*', type=str,
            help='Fichiers Python à compiler'
        )
        
        batch_parser.add_argument(
            '--files-from', type=str, metavar='FILE',
            help='Lire la liste des fichiers depuis un fichier'
        )
        
        batch_parser.add_argument(
            '--pattern', type=str,
            help='Pattern pour trouver les fichiers (ex: "*.py")'
        )
        
        batch_parser.add_argument(
            '--directory', type=str,
            help='Dossier à scanner pour les fichiers Python'
        )
        
        batch_parser.add_argument(
            '-o', '--output', type=str, metavar='DIR',
            help='Dossier de sortie (défaut: ./dist)'
        )
        
        batch_parser.add_argument(
            '--config', type=str, metavar='FILE',
            help='Fichier de configuration batch'
        )
        
        batch_parser.add_argument(
            '--parallel', action='store_true', default=True,
            help='Compilation parallèle (défaut)'
        )
        
        batch_parser.add_argument(
            '--max-workers', type=int, default=4,
            help='Nombre maximum de workers parallèles'
        )
        
        batch_parser.add_argument(
            '--stop-on-error', action='store_true',
            help='Arrêter lors de la première erreur'
        )
    
    def _add_info_parser(self, subparsers):
        """Ajoute le parser pour la commande info"""
        
        info_parser = subparsers.add_parser(
            'info',
            help='Affiche les informations système',
            description='Informations sur le système et les dépendances'
        )
        
        info_parser.add_argument(
            '--system', action='store_true',
            help='Informations système seulement'
        )
        
        info_parser.add_argument(
            '--dependencies', action='store_true',
            help='Dépendances seulement'
        )
        
        info_parser.add_argument(
            '--format', type=str,
            choices=['text', 'json', 'yaml'],
            default='text',
            help='Format de sortie'
        )
        
        info_parser.add_argument(
            '--output', type=str, metavar='FILE',
            help='Fichier de sortie'
        )
    
    def _add_config_parser(self, subparsers):
        """Ajoute le parser pour la commande config"""
        
        config_parser = subparsers.add_parser(
            'config',
            help='Gère la configuration PyForgee',
            description='Configuration et paramètres'
        )
        
        config_subparsers = config_parser.add_subparsers(
            dest='config_action',
            help='Actions de configuration'
        )
        
        # Show config
        show_parser = config_subparsers.add_parser(
            'show', help='Affiche la configuration actuelle'
        )
        show_parser.add_argument(
            '--format', choices=['text', 'yaml', 'json'],
            default='text', help='Format d\'affichage'
        )
        
        # Set config
        set_parser = config_subparsers.add_parser(
            'set', help='Définit une valeur de configuration'
        )
        set_parser.add_argument('key', help='Clé de configuration')
        set_parser.add_argument('value', help='Valeur à définir')
        
        # Get config
        get_parser = config_subparsers.add_parser(
            'get', help='Récupère une valeur de configuration'
        )
        get_parser.add_argument('key', help='Clé de configuration')
        
        # Reset config
        reset_parser = config_subparsers.add_parser(
            'reset', help='Remet la configuration aux valeurs par défaut'
        )
        reset_parser.add_argument(
            '--confirm', action='store_true',
            help='Confirme la remise à zéro'
        )
        
        # Export/Import
        export_parser = config_subparsers.add_parser(
            'export', help='Exporte la configuration'
        )
        export_parser.add_argument('output', help='Fichier de sortie')
        export_parser.add_argument(
            '--format', choices=['yaml', 'json', 'ini'],
            default='yaml', help='Format d\'export'
        )
        
        import_parser = config_subparsers.add_parser(
            'import', help='Importe une configuration'
        )
        import_parser.add_argument('input', help='Fichier de configuration')
    
    def parse_args(self, args: Optional[List[str]] = None) -> CLIArguments:
        """Parse les arguments et retourne une structure CLIArguments"""
        
        parsed = self.parser.parse_args(args)
        
        # Conversion en CLIArguments
        cli_args = CLIArguments(command=parsed.command or '')
        
        # Options globales
        if hasattr(parsed, 'verbose'):
            cli_args.verbose = parsed.verbose
        if hasattr(parsed, 'quiet'):
            cli_args.quiet = parsed.quiet
        if hasattr(parsed, 'config'):
            cli_args.config_file = parsed.config
        if hasattr(parsed, 'log_file'):
            cli_args.log_file = parsed.log_file
        
        # Options spécifiques à la commande
        if parsed.command == 'compile':
            self._parse_compile_args(parsed, cli_args)
        elif parsed.command == 'analyze':
            self._parse_analyze_args(parsed, cli_args)
        elif parsed.command == 'compress':
            self._parse_compress_args(parsed, cli_args)
        elif parsed.command == 'protect':
            self._parse_protect_args(parsed, cli_args)
        elif parsed.command == 'batch':
            self._parse_batch_args(parsed, cli_args)
        
        return cli_args
    
    def _parse_compile_args(self, parsed, cli_args: CLIArguments):
        """Parse les arguments de compilation"""
        cli_args.source_path = parsed.source
        cli_args.output_path = parsed.output or './dist'
        cli_args.output_name = parsed.name
        
        # Compilateur
        if parsed.compiler != 'auto':
            cli_args.compiler = CompilerType(parsed.compiler)
        
        # Options d'exécutable
        cli_args.onefile = parsed.onefile
        cli_args.console = parsed.console
        cli_args.optimize = parsed.optimize
        cli_args.icon_path = parsed.icon
        
        # Dépendances
        cli_args.exclude_modules = parsed.exclude or []
        cli_args.hidden_imports = parsed.hidden_import or []
        
        # Compression
        if parsed.compress != 'none':
            cli_args.compression_method = CompressionMethod(parsed.compress)
        cli_args.compression_level = parsed.compression_level
        cli_args.backup_original = getattr(parsed, 'backup_original', True)
        
        # Protection
        if parsed.protect != 'none':
            cli_args.protection_level = ProtectionLevel(parsed.protect)
        cli_args.obfuscate_names = parsed.obfuscate_names
        cli_args.obfuscate_strings = parsed.obfuscate_strings
        cli_args.encrypt_bytecode = parsed.encrypt_bytecode
        cli_args.add_anti_debug = parsed.anti_debug
    
    def _parse_analyze_args(self, parsed, cli_args: CLIArguments):
        """Parse les arguments d'analyse"""
        cli_args.source_path = parsed.source
        cli_args.output_path = parsed.output
        cli_args.export_format = parsed.format
        cli_args.deep_analysis = parsed.deep
        cli_args.include_stdlib = parsed.include_stdlib
    
    def _parse_compress_args(self, parsed, cli_args: CLIArguments):
        """Parse les arguments de compression"""
        cli_args.batch_files = parsed.files
        cli_args.compression_method = CompressionMethod(parsed.method)
        cli_args.compression_level = parsed.level
        cli_args.backup_original = getattr(parsed, 'backup_original', True)
        cli_args.parallel = parsed.parallel
    
    def _parse_protect_args(self, parsed, cli_args: CLIArguments):
        """Parse les arguments de protection"""
        cli_args.source_path = parsed.source
        cli_args.output_path = parsed.output
        cli_args.protection_level = ProtectionLevel(parsed.level)
        cli_args.obfuscate_names = parsed.obfuscate_names
        cli_args.obfuscate_strings = parsed.obfuscate_strings
        cli_args.encrypt_bytecode = parsed.encrypt_bytecode
        cli_args.add_anti_debug = parsed.anti_debug
    
    def _parse_batch_args(self, parsed, cli_args: CLIArguments):
        """Parse les arguments de batch"""
        cli_args.batch_files = parsed.files or []
        cli_args.output_path = parsed.output or './dist'
        cli_args.batch_config = parsed.config
        cli_args.parallel = parsed.parallel
        cli_args.max_workers = parsed.max_workers
        
        # Traitement des patterns et dossiers
        if hasattr(parsed, 'files_from') and parsed.files_from:
            with open(parsed.files_from, 'r') as f:
                cli_args.batch_files.extend(line.strip() for line in f if line.strip())
        
        if hasattr(parsed, 'pattern') and parsed.pattern:
            import glob
            cli_args.batch_files.extend(glob.glob(parsed.pattern))
        
        if hasattr(parsed, 'directory') and parsed.directory:
            from ..utils.file_utils import FileUtils
            cli_args.batch_files.extend(FileUtils.scan_python_files(parsed.directory))
    
    def _get_examples(self) -> str:
        """Retourne des exemples d'utilisation"""
        return """
Exemples d'utilisation:

  # Compilation simple
  PyForgee compile script.py

  # Compilation avec options
  PyForgee compile script.py --compiler nuitka --optimize --compress upx

  # Compilation avec protection
  PyForgee compile script.py --protect advanced --obfuscate-names

  # Analyse des dépendances
  PyForgee analyze script.py --deep --format json

  # Compression d'exécutables
  PyForgee compress app.exe --method upx --level 9

  # Protection de code
  PyForgee protect src/ --level maximum --output protected/

  # Compilation en lot
  PyForgee batch *.py --parallel --max-workers 8

  # Informations système
  PyForgee info --dependencies

  # Configuration
  PyForgee config show
  PyForgee config set preferred_compiler nuitka
        """


def create_cli_parser() -> CLIParser:
    """Crée une instance du parser CLI"""
    return CLIParser()