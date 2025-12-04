#!/bin/bash
# Build script for Render - installs Playwright browsers

echo "Installing Playwright browsers..."

# Install playwright browsers
python -m playwright install chromium

# Install system dependencies for Chromium on Linux
python -m playwright install-deps chromium || true

echo "Playwright installation complete!"
