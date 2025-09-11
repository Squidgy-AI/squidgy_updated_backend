#!/bin/bash
# Optimized Heroku deployment script

echo "Starting optimized Heroku deployment..."

# Use optimized requirements for deployment
cp requirements_heroku_optimized.txt requirements.txt

# Set Heroku config vars for optimization
heroku config:set PLAYWRIGHT_BUILDPACK_BROWSERS=chromium
heroku config:set PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Deploy to Heroku
git add .
git commit -m "Deploy optimized build for Heroku - reduced slug size"
git push heroku main

echo "Deployment complete!"