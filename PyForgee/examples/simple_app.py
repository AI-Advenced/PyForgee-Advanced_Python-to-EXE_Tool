#!/usr/bin/env python3
"""
Exemple d'application simple pour tester PyForgee
Ce script démontre les fonctionnalités de base qu'un utilisateur pourrait vouloir compiler
"""

import os
import sys
import json
import datetime
from pathlib import Path


def get_system_info():
    """Récupère des informations système basiques"""
    return {
        "platform": sys.platform,
        "python_version": sys.version,
        "current_directory": os.getcwd(),
        "timestamp": datetime.datetime.now().isoformat(),
        "executable": sys.executable,
        "path_separator": os.sep
    }


def process_file_operations():
    """Démontre les opérations de fichiers"""
    current_dir = Path.cwd()
    
    print(f"📁 Répertoire actuel: {current_dir}")
    print(f"📄 Fichiers Python trouvés:")
    
    py_files = list(current_dir.glob("*.py"))
    for i, py_file in enumerate(py_files[:5], 1):  # Limite à 5 fichiers
        size = py_file.stat().st_size
        print(f"   {i}. {py_file.name} ({size} bytes)")
    
    if len(py_files) > 5:
        print(f"   ... et {len(py_files) - 5} autres fichiers")


def demonstrate_json_processing():
    """Démontre le traitement JSON"""
    sample_data = {
        "application": "PyForgee Example",
        "version": "1.0.0",
        "features": [
            "Compilation Python-to-EXE",
            "Compression avancée",
            "Protection du code",
            "Analyse de dépendances"
        ],
        "metadata": {
            "created_by": "PyForgee",
            "build_date": datetime.datetime.now().isoformat(),
            "target_platforms": ["Windows", "Linux", "macOS"]
        }
    }
    
    print("📊 Données JSON générées:")
    print(json.dumps(sample_data, indent=2, ensure_ascii=False))
    
    return sample_data


def calculate_fibonacci(n):
    """Calcule la séquence de Fibonacci (démontre les calculs)"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib_sequence = [0, 1]
    for i in range(2, n):
        fib_sequence.append(fib_sequence[i-1] + fib_sequence[i-2])
    
    return fib_sequence


def interactive_menu():
    """Menu interactif simple"""
    while True:
        print("\n" + "="*50)
        print("🚀 PyForgee - Application d'Exemple")
        print("="*50)
        print("1. 🖥️  Afficher les informations système")
        print("2. 📁 Analyser les fichiers du répertoire")
        print("3. 📊 Traitement de données JSON")
        print("4. 🔢 Calculer Fibonacci")
        print("5. 🧪 Test des imports")
        print("0. ❌ Quitter")
        print("-"*50)
        
        try:
            choice = input("Votre choix (0-5): ").strip()
            
            if choice == "0":
                print("👋 Au revoir!")
                break
            elif choice == "1":
                print("\n🖥️ Informations Système:")
                info = get_system_info()
                for key, value in info.items():
                    print(f"   {key}: {value}")
            
            elif choice == "2":
                print("\n📁 Analyse des Fichiers:")
                process_file_operations()
            
            elif choice == "3":
                print("\n📊 Traitement JSON:")
                data = demonstrate_json_processing()
                print(f"\n✅ {len(data)} entrées traitées avec succès!")
            
            elif choice == "4":
                try:
                    n = int(input("\nNombre d'éléments Fibonacci à calculer: "))
                    if n > 50:
                        print("⚠️ Limité à 50 éléments maximum")
                        n = 50
                    
                    fib_result = calculate_fibonacci(n)
                    print(f"\n🔢 Séquence Fibonacci ({n} éléments):")
                    print(f"   {fib_result}")
                    
                except ValueError:
                    print("❌ Veuillez entrer un nombre valide")
            
            elif choice == "5":
                print("\n🧪 Test des Imports:")
                test_imports()
            
            else:
                print("❌ Choix invalide. Veuillez choisir entre 0-5.")
        
        except KeyboardInterrupt:
            print("\n\n👋 Interruption détectée. Au revoir!")
            break
        except EOFError:
            print("\n\n👋 Fin d'entrée détectée. Au revoir!")
            break


def test_imports():
    """Teste différents types d'imports pour l'analyse de dépendances"""
    
    print("   📦 Test des imports standards...")
    
    # Imports standard library
    try:
        import urllib.request
        print("   ✅ urllib.request - OK")
    except ImportError as e:
        print(f"   ❌ urllib.request - {e}")
    
    try:
        import hashlib
        data = "PyForgee Test".encode()
        hash_result = hashlib.md5(data).hexdigest()
        print(f"   ✅ hashlib - OK (MD5: {hash_result[:8]}...)")
    except ImportError as e:
        print(f"   ❌ hashlib - {e}")
    
    try:
        import collections
        counter = collections.Counter("PyForgee")
        print(f"   ✅ collections - OK (Counter: {dict(counter)})")
    except ImportError as e:
        print(f"   ❌ collections - {e}")
    
    # Test d'imports optionnels (third-party)
    optional_modules = {
        'requests': 'Bibliothèque HTTP populaire',
        'numpy': 'Calcul scientifique',
        'pandas': 'Manipulation de données',
        'PIL': 'Traitement d\'images (Pillow)',
    }
    
    print("\n   📦 Test des imports optionnels...")
    
    for module, description in optional_modules.items():
        try:
            __import__(module)
            print(f"   ✅ {module} - OK ({description})")
        except ImportError:
            print(f"   ⚠️ {module} - Non disponible ({description})")


def main():
    """Fonction principale"""
    print("🚀 Démarrage de l'application d'exemple PyForgee...")
    print("📝 Cette application démontre diverses fonctionnalités Python")
    print("🔧 Compilée avec PyForgee pour créer un exécutable optimisé")
    
    # Vérifie si on est en mode interactif ou non
    if len(sys.argv) > 1:
        if sys.argv[1] == "--version":
            print("PyForgee Example App v1.0.0")
            return
        elif sys.argv[1] == "--info":
            print("\nℹ️ Informations de l'application:")
            info = get_system_info()
            for key, value in info.items():
                print(f"  {key}: {value}")
            return
        elif sys.argv[1] == "--test":
            print("\n🧪 Mode test rapide:")
            test_imports()
            print("\n✅ Tests terminés!")
            return
        elif sys.argv[1] == "--help":
            print("\n📖 Utilisation:")
            print("  python simple_app.py           - Mode interactif")
            print("  python simple_app.py --version - Affiche la version")
            print("  python simple_app.py --info    - Infos système")
            print("  python simple_app.py --test    - Tests rapides")
            print("  python simple_app.py --help    - Cette aide")
            return
    
    # Mode interactif par défaut
    try:
        interactive_menu()
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        print("🔍 Vérifiez la configuration de votre environnement")
        sys.exit(1)


if __name__ == "__main__":
    main()