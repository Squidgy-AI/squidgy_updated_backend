# Squidgy Backend
Backend Code base for Squidgy - Deployed on Heroku

## Requirements
- **Python 3.12** (required - Python 3.13 has compatibility issues with some dependencies)

## Setup
```bash
# Create conda environment
conda create -n squidgy_backend python=3.12
conda activate squidgy_backend

# Install dependencies
pip install -r requirements.txt
```

## Notes
- Fixed payment scopes issue - reduced to chromium only
