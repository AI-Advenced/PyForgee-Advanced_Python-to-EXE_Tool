#!/usr/bin/env python3
"""
Script de démarrage rapide pour PyForgee
Permet de tester l'installation et les fonctionnalités de base
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header():
    """Affiche l'en-tête du script"""
    print("=" * 60)
    print("🚀 PyForgee - Script de Démarrage Rapide")
    print("=" * 60)
    print("Ce script teste l'installation et démontre l'utilisation de PyForgee")
    print()

def check_python_version():
    """Vérifie la version de Python"""
    print("🐍 Vérification de la version Python...")
    
    if sys.version_info < (3, 9):
        print(f"❌ Python {sys.version_info.major}.{sys.version_info.minor} détecté")
        print("⚠️ PyForgee nécessite Python 3.9 ou supérieur")
        return False
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} - OK")
        return True

def check_dependencies():
    """Vérifie les dépendances de base"""
    print("\n📦 Vérification des dépendances...")
    
    required_modules = [
        ('click', 'Interface CLI'),
        ('rich', 'Affichage terminal'),
        ('yaml', 'Configuration'),
        ('psutil', 'Informations système')
    ]
    
    optional_modules = [
        ('PySide6', 'Interface graphique'),
        ('PIL', 'Traitement d\'images'),
        ('pyarmor', 'Protection avancée'),
    ]
    
    missing_required = []
    missing_optional = []
    
    # Modules requis
    for module, description in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {module} - {description}")
        except ImportError:
            print(f"   ❌ {module} - {description} (REQUIS)")
            missing_required.append(module)
    
    # Modules optionnels
    for module, description in optional_modules:
        try:
            __import__(module)
            print(f"   ✅ {module} - {description}")
        except ImportError:
            print(f"   ⚠️ {module} - {description} (optionnel)")
            missing_optional.append(module)
    
    if missing_required:
        print(f"\n❌ Modules requis manquants: {', '.join(missing_required)}")
        print("💡 Installez avec: pip install -r requirements.txt")
        return False
    
    if missing_optional:
        print(f"\nℹ️ Modules optionnels manquants: {', '.join(missing_optional)}")
        print("💡 Fonctionnalités réduites sans ces modules")
    
    return True

def check_external_tools():
    """Vérifie les outils externes"""
    print("\n🔧 Vérification des outils externes...")
    
    tools = {
        'pyinstaller': 'Compilateur PyInstaller',
        'nuitka': 'Compilateur Nuitka', 
        'upx': 'Compresseur UPX',
        'pyarmor': 'Protecteur PyArmor'
    }
    
    available_tools = []
    
    for tool, description in tools.items():
        try:
            result = subprocess.run(
                [tool, '--version'] if tool != 'nuitka' else ['python', '-m', 'nuitka', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                print(f"   ✅ {tool} - {description} ({version})")
                available_tools.append(tool)
            else:
                print(f"   ❌ {tool} - {description} (non fonctionnel)")
                
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            print(f"   ❌ {tool} - {description} (non trouvé)")
    
    if not available_tools:
        print("\n⚠️ Aucun outil de compilation trouvé!")
        print("💡 Installez au moins PyInstaller: pip install pyinstaller")
        return False
    else:
        print(f"\n✅ {len(available_tools)} outil(s) de compilation disponible(s)")
        return True

def test_PyForgee_import():
    """Teste l'import de PyForgee"""
    print("\n📋 Test d'import de PyForgee...")
    
    try:
        # Ajoute le répertoire src au path si nécessaire
        current_dir = Path(__file__).parent
        src_dir = current_dir / 'src'
        if src_dir.exists() and str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        
        # Test des imports principaux
        from src.core.compiler_engine import CompilerEngine
        print("   ✅ CompilerEngine importé")
        
        from src.core.dependency_analyzer import DependencyAnalyzer  
        print("   ✅ DependencyAnalyzer importé")
        
        from src.core.compression_handler import CompressionHandler
        print("   ✅ CompressionHandler importé")
        
        from src.core.protection_manager import ProtectionManager
        print("   ✅ ProtectionManager importé")
        
        print("✅ Tous les modules PyForgee importés avec succès!")
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import PyForgee: {e}")
        print("💡 Vérifiez l'installation avec: pip install -e .")
        return False

def test_basic_functionality():
    """Teste les fonctionnalités de base"""
    print("\n🧪 Test des fonctionnalités de base...")
    
    try:
        # Test du moteur de compilation
        from src.core.compiler_engine import CompilerEngine, CompilationOptions
        
        engine = CompilerEngine()
        print("   ✅ Moteur de compilation initialisé")
        
        # Info sur les compilateurs
        info = engine.get_compiler_info()
        available_compilers = [name for name, details in info.items() if details['available']]
        print(f"   ✅ Compilateurs disponibles: {', '.join(available_compilers)}")
        
        # Test de l'analyseur de dépendances
        from src.core.dependency_analyzer import DependencyAnalyzer
        
        analyzer = DependencyAnalyzer()
        print("   ✅ Analyseur de dépendances initialisé")
        
        # Test du gestionnaire de compression
        from src.core.compression_handler import CompressionHandler
        
        compressor = CompressionHandler()
        comp_info = compressor.get_compressor_info()
        available_compressors = [name for name, details in comp_info.items() if details['available']]
        print(f"   ✅ Compresseurs disponibles: {', '.join(available_compressors)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def run_example_analysis():
    """Analyse l'exemple fourni"""
    print("\n🔍 Analyse de l'exemple fourni...")
    
    try:
        example_file = Path(__file__).parent / 'examples' / 'simple_app.py'
        
        if not example_file.exists():
            print("❌ Fichier d'exemple non trouvé")
            return False
        
        from src.core.dependency_analyzer import DependencyAnalyzer
        
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze_dependencies(str(example_file))
        
        print(f"   ✅ Analyse terminée en {result.analysis_time:.2f}s")
        print(f"   📦 {len(result.dependencies)} dépendances trouvées")
        print(f"   📊 Taille estimée: {result.total_size_estimate:,} bytes")
        
        # Suggestions d'optimisation
        suggestions = analyzer.get_optimization_suggestions(result)
        if suggestions['excludable_modules']:
            excludable_count = len(suggestions['excludable_modules'])
            print(f"   💡 {excludable_count} modules peuvent être exclus pour réduire la taille")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
        return False

def show_next_steps():
    """Affiche les étapes suivantes"""
    print("\n" + "=" * 60)
    print("🎯 Étapes suivantes recommandées")
    print("=" * 60)
    
    print("\n📖 1. Lire la documentation:")
    print("   - README.md pour une vue d'ensemble")
    print("   - examples/README.md pour les exemples d'utilisation")
    
    print("\n🧪 2. Tester avec l'exemple:")
    print("   cd examples")
    print("   python simple_app.py")
    
    print("\n⚙️ 3. Première compilation:")
    print("   PyForgee compile examples/simple_app.py")
    
    print("\n🔍 4. Analyser les dépendances:")
    print("   PyForgee analyze examples/simple_app.py --deep")
    
    print("\n📋 5. Voir toutes les options:")
    print("   PyForgee --help")
    print("   PyForgee compile --help")
    
    print("\n🔧 6. Configurer PyForgee:")
    print("   PyForgee config show")
    print("   cp PyForgee.yaml ~/.config/PyForgee/config.yaml  # Personnaliser")
    
    print("\n📚 7. Explorer les fonctionnalités avancées:")
    print("   - Compression: PyForgee compress --help")
    print("   - Protection: PyForgee protect --help")
    print("   - Batch: PyForgee batch --help")

def main():
    """Fonction principale"""
    print_header()
    
    # Tests séquentiels
    tests = [
        ("Version Python", check_python_version),
        ("Dépendances", check_dependencies),
        ("Outils externes", check_external_tools),
        ("Import PyForgee", test_PyForgee_import),
        ("Fonctionnalités de base", test_basic_functionality),
        ("Analyse d'exemple", run_example_analysis),
    ]
    
    success_count = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                success_count += 1
            else:
                print(f"⚠️ Test '{test_name}' échoué")
        except Exception as e:
            print(f"❌ Erreur dans le test '{test_name}': {e}")
    
    # Résumé
    print("\n" + "=" * 60)
    print(f"📊 Résumé: {success_count}/{total_tests} tests réussis")
    
    if success_count == total_tests:
        print("🎉 PyForgee est correctement installé et fonctionnel!")
        show_next_steps()
    elif success_count >= total_tests - 1:
        print("✅ PyForgee est fonctionnel avec quelques limitations")
        show_next_steps()
    else:
        print("❌ PyForgee nécessite une configuration supplémentaire")
        print("\n💡 Problèmes courants:")
        print("   - Installer les dépendances: pip install -r requirements.txt")
        print("   - Installer PyForgee: pip install -e .")
        print("   - Installer des outils: pip install pyinstaller nuitka")
    
    print("\n🚀 Merci d'utiliser PyForgee!")

if __name__ == "__main__":
    main()