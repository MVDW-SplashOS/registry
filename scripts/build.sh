#!/bin/bash
set -e

echo "Building Registry..."

echo "Building Rust library..."
cd libregistry-rs
cargo build --release
cd ..

echo "Copying library to CLI..."
mkdir -p registry-zig/lib
cp libregistry-rs/target/release/libregistry.so registry-zig/lib/

echo "Building Zig CLI..."
cd registry-zig
zig build
cd ..

echo "Build complete! Binary at: registry-zig/zig-out/bin/registry"
