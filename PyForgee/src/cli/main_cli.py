#!/usr/bin/env python3
"""
Interface ligne de commande principale pour PyForgee
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

# Import des modules PyForgee
from ..core.compiler_engine import CompilerEngine, CompilationOptions, CompilerType
from ..core.dependency_analyzer import DependencyAnalyzer
from ..core.compression_handler import CompressionHandler, CompressionMethod
from ..core.protection_manager import ProtectionManager, ProtectionLevel
from ..utils.config_manager import get_config_manager
from ..utils.file_utils import FileUtils
from ..utils.system_utils import SystemUtils


console = Console()


def setup_logging(verbose: bool = False, log_file: Optional[str] = None):
    """Configure le logging"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configuration du logger racine
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=log_file
    )
    
    # Logger spécifique pour PyForgee
    logger = logging.getLogger('PyForgee')
    logger.setLevel(level)
    
    return logger


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Affiche la version')
@click.option('--verbose', '-v', is_flag=True, help='Mode verbose')
@click.option('--config', '-c', type=click.Path(), help='Fichier de configuration')
@click.pass_context
def cli(ctx, version, verbose, config):
    """
    PyForgee - Outil Python-to-EXE avancé
    
    Un outil hybride qui combine les avantages de PyInstaller, cx_Freeze, et Nuitka
    avec des fonctionnalités avancées de compression, protection, et optimisation.
    """
    
    if version:
        from .. import __version__
        rprint(f"[bold green]PyForgee version {__version__}[/bold green]")
        return
    
    # Configuration du contexte
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config_file'] = config
    
    # Setup logging
    logger = setup_logging(verbose)
    
    # Chargement de la configuration
    if config:
        config_manager = get_config_manager()
        if not config_manager.import_config(config):
            logger.error(f"Impossible de charger la configuration: {config}")
    
    if ctx.invoked_subcommand is None:
        rprint(Panel.fit(
            "[bold blue]PyForgee[/bold blue] - Outil Python-to-EXE avancé\n\n"
            "Utilisez [bold]PyForgee --help[/bold] pour voir les commandes disponibles.",
            title="Bienvenue"
        ))


@cli.command()
@click.argument('source', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Dossier de sortie')
@click.option('--name', '-n', help='Nom de l\'exécutable')
@click.option('--compiler', type=click.Choice(['auto', 'pyinstaller', 'nuitka', 'cx_freeze']), 
              default='auto', help='Compilateur à utiliser')
@click.option('--onefile/--no-onefile', default=True, help='Créer un fichier unique')
@click.option('--console/--no-console', default=False, help='Mode console')
@click.option('--optimize', is_flag=True, help='Optimisations avancées')
@click.option('--icon', type=click.Path(exists=True), help='Fichier icône')
@click.option('--exclude', multiple=True, help='Modules à exclure')
@click.option('--hidden-import', multiple=True, help='Imports cachés')
@click.option('--compress', type=click.Choice(['none', 'auto', 'upx', 'lzma', 'brotli']), 
              default='auto', help='Méthode de compression')
@click.option('--protect', type=click.Choice(['none', 'basic', 'intermediate', 'advanced', 'maximum']), 
              default='none', help='Niveau de protection')
@click.pass_context
def compile(ctx, source, output, name, compiler, onefile, console, optimize,
           icon, exclude, hidden_import, compress, protect):
    """Compile un script Python en exécutable"""

    async def _compile_async():
        logger = logging.getLogger('PyForgee.cli')

        source_path = Path(source).resolve()
        if not source_path.exists():
            rprint(f"[red]Erreur: Fichier source non trouvé: {source}[/red]")
            sys.exit(1)

        output_path = Path(output).resolve() if output else Path('./dist').resolve()
        if not name:
            nonlocal_name = source_path.stem
        else:
            nonlocal_name = name

        rprint(Panel.fit(
            f"[bold]Source:[/bold] {source_path}\n"
            f"[bold]Sortie:[/bold] {output_path}\n"
            f"[bold]Nom:[/bold] {nonlocal_name}\n"
            f"[bold]Compilateur:[/bold] {compiler}",
            title="Configuration de compilation"
        ))

        try:
            compiler_type = CompilerType(compiler) if compiler != 'auto' else None
            options = CompilationOptions(
                output_path=Path(output),
                source_path=str(source_path),
                output_name=nonlocal_name,
                onefile=onefile,
                console=console,
                optimize=optimize,
                icon_path=icon,
                exclude_modules=list(exclude),
                hidden_imports=list(hidden_import),
                preferred_compiler=compiler_type
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Compilation en cours...", total=100)
                result = await _compile_with_progress(options, progress, task)

            if result.success:
                rprint(f"[green]✓ Compilation réussie![/green]")
                rprint(f"[bold]Fichier généré:[/bold] {result.output_path}")
                rprint(f"[bold]Taille:[/bold] {result.file_size:,} bytes")
                rprint(f"[bold]Temps:[/bold] {result.compilation_time:.2f}s")

                if compress != 'none':
                    await _apply_compression(result.output_path, compress, progress)

                if protect != 'none':
                    await _apply_protection(str(source_path), protect, progress)
            else:
                rprint(f"[red]✗ Échec de la compilation:[/red] {result.error_message}")
                sys.exit(1)

        except Exception as e:
            logger.exception("Erreur lors de la compilation")
            rprint(f"[red]Erreur: {e}[/red]")
            sys.exit(1)

    asyncio.run(_compile_async())


@cli.command()
@click.argument('source', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Fichier de sortie')
@click.option('--format', type=click.Choice(['text', 'json', 'yaml']), 
              default='text', help='Format de sortie')
@click.option('--deep', is_flag=True, help='Analyse approfondie')
@click.option('--include-stdlib', is_flag=True, help='Inclure la bibliothèque standard')
def analyze(source, output, format, deep, include_stdlib):
    """Analyse les dépendances d'un script Python"""
    
    source_path = Path(source).resolve()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Analyse des dépendances...", total=None)
        
        # Analyse
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_dependencies(
            str(source_path),
            include_stdlib=include_stdlib,
            deep_analysis=deep
        )
        
        progress.remove_task(task)
    
    # Affichage des résultats
    if format == 'text':
        _display_dependency_analysis(result)
    elif format == 'json':
        import json
        data = {
            'dependencies': {name: {
                'version': dep.version,
                'is_builtin': dep.is_builtin,
                'is_third_party': dep.is_third_party,
                'size_estimate': dep.size_estimate
            } for name, dep in result.dependencies.items()},
            'total_size': result.total_size_estimate,
            'analysis_time': result.analysis_time
        }
        
        if output:
            with open(output, 'w') as f:
                json.dump(data, f, indent=2)
        else:
            print(json.dumps(data, indent=2))


@cli.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True), required=True)
@click.option('--method', type=click.Choice(['auto', 'upx', 'lzma', 'brotli', 'custom']), 
              default='auto', help='Méthode de compression')
@click.option('--level', type=int, default=9, help='Niveau de compression (1-9)')
@click.option('--backup/--no-backup', default=True, help='Sauvegarder les originaux')
def compress(files, method, level, backup):
    """Compresse des fichiers exécutables"""
    
    compression_method = CompressionMethod(method)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Compression...", total=len(files))
        
        for file_path in files:
            progress.update(task, description=f"Compression de {Path(file_path).name}")
            
            # Compression
            handler = CompressionHandler()
            result = asyncio.run(handler.compress_executable(
                file_path, 
                method=compression_method,
                level=level,
                backup_original=backup
            ))
            
            if result.success:
                ratio = result.compression_ratio * 100
                rprint(f"[green]✓[/green] {file_path}: {ratio:.1f}% de réduction")
            else:
                rprint(f"[red]✗[/red] {file_path}: {result.error_message}")
            
            progress.advance(task)


@cli.command()
@click.argument('source', type=click.Path(exists=True))
@click.option('--level', type=click.Choice(['basic', 'intermediate', 'advanced', 'maximum']), 
              default='intermediate', help='Niveau de protection')
@click.option('--output', '-o', type=click.Path(), help='Dossier de sortie')
def protect(source, level, output):
    """Protège du code Python contre la décompilation"""
    
    protection_level = ProtectionLevel(level)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Protection du code...", total=None)
        
        # Protection
        manager = ProtectionManager()
        result = asyncio.run(manager.protect_code(source, protection_level))
        
        progress.remove_task(task)
    
    if result.success:
        rprint(f"[green]✓ Protection appliquée![/green]")
        rprint(f"[bold]Fichiers protégés:[/bold] {len(result.protected_files)}")
        rprint(f"[bold]Méthodes utilisées:[/bold] {', '.join(m.value for m in result.methods_applied)}")
        rprint(f"[bold]Temps:[/bold] {result.protection_time:.2f}s")
    else:
        rprint(f"[red]✗ Échec de la protection:[/red] {result.error_message}")
        sys.exit(1)


@cli.command()
def info():
    """Affiche les informations système et dépendances"""
    
    # Informations système
    sys_info = SystemUtils.get_system_info()
    
    table = Table(title="Informations Système")
    table.add_column("Propriété", style="bold")
    table.add_column("Valeur")
    
    table.add_row("Plateforme", sys_info['platform'])
    table.add_row("Système", sys_info['system'])
    table.add_row("Version Python", sys_info['python_version'].split()[0])
    table.add_row("Exécutable Python", sys_info['python_executable'])
    table.add_row("CPU", f"{sys_info['cpu_count']} cœurs")
    
    if sys_info['memory_total']:
        memory_gb = sys_info['memory_total'] / (1024**3)
        table.add_row("Mémoire", f"{memory_gb:.1f} GB")
    
    console.print(table)
    
    # Dépendances
    deps = SystemUtils.check_dependencies()
    
    dep_table = Table(title="Dépendances")
    dep_table.add_column("Outil", style="bold")
    dep_table.add_column("Disponible")
    dep_table.add_column("Version")
    
    for name, info in deps.items():
        status = "[green]✓[/green]" if info['available'] else "[red]✗[/red]"
        version = info['version'] or "N/A"
        dep_table.add_row(name.title(), status, version)
    
    console.print(dep_table)


@cli.command()
@click.option('--format', type=click.Choice(['yaml', 'json', 'ini']), 
              default='yaml', help='Format d\'export')
@click.option('--output', '-o', type=click.Path(), help='Fichier de sortie')
def config(format, output):
    """Gère la configuration PyForgee"""
    
    config_manager = get_config_manager()
    
    if output:
        # Export de la configuration
        if config_manager.export_config(output, format):
            rprint(f"[green]Configuration exportée vers {output}[/green]")
        else:
            rprint("[red]Erreur lors de l'export[/red]")
    else:
        # Affichage de la configuration actuelle
        config_dict = config_manager.get_template_config()
        
        table = Table(title="Configuration PyForgee")
        table.add_column("Paramètre", style="bold")
        table.add_column("Valeur")
        table.add_column("Description")
        
        for key, info in config_dict.items():
            if key.startswith('#') or info is None:
                continue
                
            current_value = getattr(config_manager.config, key, "N/A")
            description = info.get('description', '')
            
            table.add_row(key, str(current_value), description)
        
        console.print(table)


@cli.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True), required=True)
@click.option('--output', '-o', type=click.Path(), help='Dossier de sortie')
@click.option('--config-file', '-c', type=click.Path(exists=True), help='Fichier de configuration')
def batch(files, output, config_file):
    """Compile plusieurs fichiers en lot"""
    
    # Chargement de la configuration
    if config_file:
        config_manager = get_config_manager()
        config_manager.import_config(config_file)
    
    output_path = Path(output) if output else Path('./dist')
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Compilation en lot...", total=len(files))
        
        for file_path in files:
            file_path = Path(file_path)
            progress.update(task, description=f"Compilation de {file_path.name}")
            
            # Options par défaut
            options = CompilationOptions(
                source_path=str(file_path),
                output_path=str(output_path),
                output_name=file_path.stem
            )
            
            # Compilation
            engine = CompilerEngine()
            result = asyncio.run(engine.compile(options))
            
            if result.success:
                rprint(f"[green]✓[/green] {file_path.name}: {result.output_path}")
            else:
                rprint(f"[red]✗[/red] {file_path.name}: {result.error_message}")
            
            progress.advance(task)


async def _compile_with_progress(options, progress, task):
    """Compile avec mise à jour de la progression"""
    
    # Simulation de progression
    progress.update(task, completed=10)
    
    engine = CompilerEngine()
    result = await engine.compile(options)
    
    progress.update(task, completed=100)
    
    return result


async def _apply_compression(file_path, method, progress):
    """Applique la compression"""
    
    task = progress.add_task("Compression...", total=100)
    
    handler = CompressionHandler()
    result = await handler.compress_executable(file_path, method=method)
    
    progress.update(task, completed=100)
    
    if result.success:
        ratio = result.compression_ratio * 100
        rprint(f"[green]✓ Compression: {ratio:.1f}% de réduction[/green]")
    else:
        rprint(f"[red]✗ Compression échouée: {result.error_message}[/red]")
    
    progress.remove_task(task)


async def _apply_protection(source_path, level, progress):
    """Applique la protection"""
    
    task = progress.add_task("Protection...", total=100)
    
    manager = ProtectionManager()
    result = await manager.protect_code(source_path, level)
    
    progress.update(task, completed=100)
    
    if result.success:
        rprint(f"[green]✓ Protection appliquée[/green]")
    else:
        rprint(f"[red]✗ Protection échouée: {result.error_message}[/red]")
    
    progress.remove_task(task)


def _display_dependency_analysis(result):
    """Affiche les résultats d'analyse des dépendances"""
    
    # Tableau principal
    table = Table(title="Analyse des Dépendances")
    table.add_column("Module", style="bold")
    table.add_column("Type")
    table.add_column("Version")
    table.add_column("Taille", justify="right")
    
    for name, dep in sorted(result.dependencies.items()):
        if dep.is_builtin:
            dep_type = "[blue]Builtin[/blue]"
        elif dep.is_third_party:
            dep_type = "[yellow]Third-party[/yellow]"
        else:
            dep_type = "[green]Local[/green]"
        
        version = dep.version or "N/A"
        size = f"{dep.size_estimate:,} B" if dep.size_estimate else "N/A"
        
        table.add_row(name, dep_type, version, size)
    
    console.print(table)
    
    # Statistiques
    total_deps = len(result.dependencies)
    total_size = result.total_size_estimate
    
    stats_text = (
        f"[bold]Total:[/bold] {total_deps} dépendances\n"
        f"[bold]Taille estimée:[/bold] {total_size:,} bytes ({total_size/1024/1024:.1f} MB)\n"
        f"[bold]Temps d'analyse:[/bold] {result.analysis_time:.2f}s"
    )
    
    console.print(Panel(stats_text, title="Statistiques"))


def main():
    """Point d'entrée principal"""
    try:
        cli()
    except KeyboardInterrupt:
        rprint("\n[yellow]Interruption par l'utilisateur[/yellow]")
        sys.exit(1)
    except Exception as e:
        rprint(f"[red]Erreur inattendue: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()