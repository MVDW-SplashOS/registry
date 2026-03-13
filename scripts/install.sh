#!/bin/bash
set -e

echo "Installing Registry..."

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

echo "Installing binary..."
cp -f cli/zig-out/bin/registry /usr/local/bin/

echo "Installing library..."
cp -f library/target/release/libregistry.so /usr/local/lib/
ldconfig

echo "Installing bash completion..."
mkdir -p /etc/bash_completion.d
cp -f cli/completions/bash /etc/bash_completion.d/registry

COMPLETION_LINE='[ -f /etc/bash_completion.d/registry ] && source /etc/bash_completion.d/registry'

echo "$COMPLETION_LINE" > ~/.bashrc.tmp
if [ -f ~/.bashrc ]; then
    grep -v "bash_completion.d/registry" ~/.bashrc >> ~/.bashrc.tmp
fi
mv -f ~/.bashrc.tmp ~/.bashrc
echo "" >> ~/.bashrc
echo "# Registry tab completion" >> ~/.bashrc
echo "$COMPLETION_LINE" >> ~/.bashrc
echo "Overwrote tab completion in ~/.bashrc"

echo ""
echo "Registry installed successfully!"
echo ""
echo "Tab completion has been enabled for bash."
echo "Run 'source ~/.bashrc' or open a new terminal to use it."
