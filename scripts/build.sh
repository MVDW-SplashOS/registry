#!/bin/bash
set -e

echo "Building Registry..."

echo "Building library..."
cd library
cargo build --release
cd ..

echo "Copying library to CLI..."
mkdir -p cli/lib
cp library/target/release/libregistry.so cli/lib/

echo "Building CLI..."
cd cli
zig build
cd ..

echo "Build complete! Binary at: cli/zig-out/bin/registry"
