# 🗂️ Registry

A centralized system for managing configuration files across a Linux system, similar to a registry.

> [!WARNING]
> **Early Development:** The registry and its definitions are still in active development.
> Breaking changes (including definition format changes) may occur without notice.

## 🚀 Development Setup

Follow these steps to set up your local development environment:

1. Clone the repository:
```bash
git clone https://github.com/MVDW-SplashOS/registry.git && cd registry
```

2. Install development dependencies:
```bash
pip install -e lib/ && pip install -e cli/
```
3. Install definitions
```bash
python ./scripts/install_definitions.py
```
