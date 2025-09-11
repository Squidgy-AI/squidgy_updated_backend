#!/bin/bash
# Install only Chromium browser for Playwright

echo "Installing Playwright Chromium browser..."

# Set environment to install only Chromium
export PLAYWRIGHT_BROWSERS_PATH=/app/browsers

# Install only Chromium
python -m playwright install chromium

echo "Chromium installation complete!"