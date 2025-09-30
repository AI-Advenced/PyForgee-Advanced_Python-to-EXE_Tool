# PyForgee - Advanced Python-to-EXE Tool

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-orange.svg)](#)

**PyForgee** is a hybrid tool that combines the advantages of PyInstaller, cx_Freeze, and Nuitka with advanced compression, protection, and optimization features to create optimal Python executables.

---

## ✨ Key Features

### 🔧 Smart Hybrid Compilation

* **Automatic selection** of the best compiler depending on the context
* Supports **PyInstaller**, **Nuitka**, and **cx_Freeze**
* **Static and dynamic dependency analysis**
* **Adaptive optimizations** depending on application type

### 🗜️ Advanced Compression

* **UPX** – 50-70% executable size reduction
* **LZMA/7z** – High-performance resource compression
* **Brotli** – Optimized for web-related data
* **Custom algorithms** – Adaptive compression depending on content

### 🔒 Multi-layer Protection

* **PyArmor** – Professional-grade anti-decompilation
* **Custom obfuscation** – Name and string masking
* **Bytecode encryption** – AES-encrypted `.pyc` files
* **Anti-debugging** – Debugger and VM detection

### 🎨 User Interfaces

* **Modern CLI** using Rich and Click
* **Intuitive GUI** with PySide6 (in development)
* **Flexible configuration** – YAML, JSON, INI
* **Extensible plugin system**

---

## 📦 Installation

### Prerequisites

* Python 3.9 or higher
* pip (Python package manager)

### Standard Installation

```bash
# Clone the repository
git clone https://github.com/PyForgee/PyForgee.git
cd PyForgee

# Install dependencies
pip install -r requirements.txt

# Install PyForgee
pip install -e .
```

### Full Installation with Optional Dependencies

```bash
# Install with dev/docs extras
pip install -e ".[dev,docs]"

# Recommended external tools
pip install pyinstaller>=5.0
pip install nuitka>=1.5.0
pip install pyarmor>=8.0.0
```

### Optional External Tools

* **UPX**: [Download UPX](https://upx.github.io/) for executable compression
* **PyArmor Pro**: License required for advanced protection

---

## 🚀 Quick Usage

### Simple Compilation

```bash
# Basic compilation
PyForgee compile script.py

# With optimizations
PyForgee compile script.py --optimize --compress upx

# With protection
PyForgee compile script.py --protect advanced --obfuscate-names
```

### Dependency Analysis

```bash
# Standard analysis
PyForgee analyze script.py

# Deep analysis with JSON export
PyForgee analyze script.py --deep --format json --output dependencies.json
```

### Executable Compression

```bash
# UPX compression
PyForgee compress app.exe --method upx --level 9

# Multiple files in parallel
PyForgee compress *.exe --parallel --max-workers 8
```

### Code Protection

```bash
# Intermediate protection
PyForgee protect src/ --level intermediate

# Maximum protection
PyForgee protect script.py --level maximum --obfuscate-strings --anti-debug
```

---

## 📋 Configuration

### Example config.yaml

```yaml
preferred_compiler: auto   # auto, pyinstaller, nuitka, cx_freeze
pyinstaller_path: null
nuitka_path: null

default_compression: auto  # auto, upx, lzma, brotli, custom
compression_level: 9
upx_path: null

default_protection_level: intermediate  # basic, intermediate, advanced, maximum
pyarmor_path: null

output_directory: "./dist"
temp_directory: null
cache_directory: null

backup_original: true
parallel_builds: true
max_workers: 4

default_excludes:
  - tkinter
  - unittest
  - doctest
  - pdb
  - sqlite3
```

### Config Management

```bash
PyForgee config show
PyForgee config set preferred_compiler nuitka
PyForgee config export my_config.yaml --format yaml
PyForgee config import my_config.yaml
```

---

## 🎯 Usage Examples

### 1. Simple GUI App

```bash
PyForgee compile gui_app.py \
  --compiler pyinstaller \
  --no-console \
  --icon app_icon.ico \
  --compress upx \
  --optimize
```

### 2. Protected Server App

```bash
PyForgee compile server.py \
  --compiler nuitka \
  --protect advanced \
  --obfuscate-names \
  --obfuscate-strings \
  --exclude tkinter unittest
```

### 3. Batch Compilation with Config

```bash
PyForgee batch *.py \
  --config batch_config.yaml \
  --parallel \
  --max-workers 6 \
  --output ./release
```

### 4. Dependency Analysis + Optimization

```bash
PyForgee analyze large_app.py --deep --include-stdlib

PyForgee compile large_app.py \
  --exclude $(PyForgee analyze large_app.py --suggest-excludes) \
  --compress auto \
  --optimize
```

---

## 🔌 Plugin System

### Built-in Plugins

* **UPX Compressor** – Executable compression
* **PyArmor Protector** – Professional code protection
* **Icon Manager** – Icon conversion and management

### Example Custom Plugin

```python
from PyForgee.plugins import BasePlugin, PluginMetadata, PluginType

class MyPlugin(BasePlugin):
    def get_metadata(self):
        return PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            description="My custom plugin",
            plugin_type=PluginType.TOOL
        )
    
    def initialize(self, config):
        return True
    
    def execute(self, context):
        return {"success": True}
```

---

## 📊 Performance Metrics

### Achieved Goals

* **Size reduction**: 40–70% vs PyInstaller alone
* **Build time**: < 2 minutes for medium projects
* **Compatibility**: Windows 10/11, Linux, macOS
* **Protection**: Resistant to standard decompilation tools

### Benchmark Examples

| Application Type | Original Size | After PyForgee | Reduction |
| ---------------- | ------------- | ------------- | --------- |
| Simple CLI       | 15 MB         | 6 MB          | 60%       |
| Tkinter GUI      | 45 MB         | 18 MB         | 60%       |
| Data Science App | 120 MB        | 50 MB         | 58%       |

---

## 🛠️ Technical Architecture

```
PyForgee/
├── core/                    
│   ├── compiler_engine.py
│   ├── dependency_analyzer.py
│   ├── compression_handler.py
│   └── protection_manager.py
├── gui/                     
├── cli/                     
├── utils/                   
├── plugins/                 
└── tests/                   
```

### Technologies

* **Python 3.9+**
* **Click** – Modern CLI framework
* **Rich** – Advanced terminal rendering
* **PySide6** – GUI framework
* **PyYAML** – Config parsing
* **asyncio** – Async operations

---

## 🧪 Testing & Quality

### Run Tests

```bash
pytest tests/
pytest tests/ --cov=src --cov-report=html
pytest tests/integration/

flake8 src/
black src/
mypy src/
```

### Test Structure

```
tests/
├── unit/
│   ├── test_compiler_engine.py
│   ├── test_dependency_analyzer.py
│   └── test_compression_handler.py
├── integration/
├── fixtures/
└── conftest.py
```

---

## 📖 Documentation

### User Docs

* [Detailed Installation Guide](docs/installation.md)
* [Step-by-step Tutorials](docs/tutorials/)
* [Complete CLI Reference](docs/cli_reference.md)
* [Advanced Config](docs/configuration.md)

### Developer Docs

* [Project Architecture](docs/architecture.md)
* [Contribution Guide](docs/contributing.md)
* [API Reference](docs/api/)
* [Plugin Development](docs/plugin_development.md)

---

## 🤝 Contribution

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Contributions Wanted

* 🐛 Bug fixes
* ✨ New features
* 📚 Documentation improvements
* 🧪 Extra tests
* 🔌 Community plugins

### Contribution Workflow

1. Fork the project
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

MIT License – see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

* **PyInstaller Team** – Compatibility foundation
* **Nuitka Project** – Performance optimizations
* **UPX Team** – Outstanding compression tool
* **PyArmor** – Professional protection solutions
* **Python Community** – Ecosystem and feedback

---

## 📞 Support & Contact

* **Issues**: [GitHub Issues](https://github.com/PyForgee/PyForgee/issues)
* **Discussions**: [GitHub Discussions](https://github.com/PyForgee/PyForgee/discussions)
* **Docs**: [docs.PyForgee.dev](https://docs.PyForgee.dev)
* **Email**: [contact@PyForgee.dev](mailto:contact@PyForgee.dev)

---

**PyForgee** – Forge your Python applications into optimized executables! 🚀

---
