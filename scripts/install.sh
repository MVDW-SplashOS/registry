#!/bin/bash
set -e

echo "Installing Registry..."

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

echo "Installing binary..."
cp registry-zig/zig-out/bin/registry /usr/local/bin/

echo "Installing library..."
cp libregistry-rs/target/release/libregistry.so /usr/local/lib/
ldconfig

echo "Registry installed successfully!"
echo "Run 'registry --help' to get started."
