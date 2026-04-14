#!/bin/bash
# Build the Python FastAPI backend as a standalone sidecar binary using PyInstaller.
# Output is placed in src-tauri/binaries/ with the Tauri-expected triple suffix.
set -euo pipefail

cd "$(dirname "$0")/.."

ARCH=$(uname -m)
OS=$(uname -s)

# Determine Rust-style target triple
case "$OS" in
  Darwin)
    case "$ARCH" in
      arm64)  TARGET="aarch64-apple-darwin" ;;
      x86_64) TARGET="x86_64-apple-darwin" ;;
      *)      echo "Unsupported macOS arch: $ARCH"; exit 1 ;;
    esac
    ;;
  Linux)
    case "$ARCH" in
      x86_64)  TARGET="x86_64-unknown-linux-gnu" ;;
      aarch64) TARGET="aarch64-unknown-linux-gnu" ;;
      *)       echo "Unsupported Linux arch: $ARCH"; exit 1 ;;
    esac
    ;;
  MINGW*|MSYS*|CYGWIN*)
    TARGET="x86_64-pc-windows-msvc"
    EXE_SUFFIX=".exe"
    ;;
  *)
    echo "Unsupported OS: $OS"; exit 1
    ;;
esac

BINARY_NAME="scriptforge-server-${TARGET}${EXE_SUFFIX:-}"

echo "==> Building sidecar for target: ${TARGET}"
echo "==> Output: src-tauri/binaries/${BINARY_NAME}"

# Run PyInstaller
pyinstaller \
  --onefile \
  --name "${BINARY_NAME}" \
  --distpath dist/ \
  --clean \
  backend/sidecar_entry.py

# Copy to Tauri binaries directory
mkdir -p src-tauri/binaries
cp "dist/${BINARY_NAME}" "src-tauri/binaries/"

echo "==> Done! Sidecar binary: src-tauri/binaries/${BINARY_NAME}"
