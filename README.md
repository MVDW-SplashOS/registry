# 🗂️ Registry

A centralized system for managing configuration files across a Linux system, similar to a registry.

> [!WARNING]
> **Early Development:** The registry and its definitions are still in active development.
> Breaking changes (including definition format changes) may occur without notice.

## 🚀 Development Setup

Follow these steps to set up your local development environment:

### Prerequisites

- **Rust** (for the library): https://rustup.rs/
- **Zig** 0.15+ (for the CLI): https://ziglang.org/download/

### Build

```bash
./scripts/build.sh
```

### Run

```bash
./registry-zig/zig-out/bin/registry --help
```

### Running Tests

```bash
cd libregistry-rs && cargo test --release
```

## 📦 Installation

```bash
sudo ./scripts/install.sh
```

This installs:
- Binary to `/usr/local/bin/registry`
- Library to `/usr/local/lib/libregistry.so`

## Usage

```bash
registry --help
```
