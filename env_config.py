"""
Environment configuration module
Dynamically loads Supabase credentials based on environment
"""
import os
from typing import Dict


def get_environment() -> str:
    """
    Detect environment based on RENDER_EXTERNAL_URL or ENVIRONMENT variable

    Returns:
        str: 'production', 'staging', or 'dev'
    """
    # Check explicit environment variable first
    env = os.getenv('ENVIRONMENT', '').lower()
    if env in ['production', 'prod', 'main']:
        return 'production'
    elif env in ['staging', 'stage']:
        return 'staging'
    elif env in ['dev', 'development']:
        return 'dev'

    # Fallback to URL detection (for Render deployments)
    render_url = os.getenv('RENDER_EXTERNAL_URL', '')

    if 'app.squidgy.ai' in render_url:
        return 'production'
    elif 'staging.squidgy.ai' in render_url:
        return 'staging'
    elif 'dev.squidgy.ai' in render_url:
        return 'dev'

    # Default to dev for local development
    return 'dev'


def get_supabase_config() -> Dict[str, str]:
    """
    Get Supabase configuration based on current environment

    Returns:
        Dict with keys: url, service_key, anon_key, schema
    """
    env = get_environment()

    if env == 'production':
        return {
            'url': os.getenv('SUPABASE_URL'),
            'service_key': os.getenv('SUPABASE_SERVICE_KEY'),
            'anon_key': os.getenv('SUPABASE_KEY'),
            'schema': os.getenv('SUPABASE_SCHEMA', 'public')
        }
    elif env == 'staging':
        return {
            'url': os.getenv('SUPABASE_STAGING_URL'),
            'service_key': os.getenv('SUPABASE_STAGING_SERVICE_KEY'),
            'anon_key': os.getenv('SUPABASE_STAGING_ANON_KEY'),
            'schema': os.getenv('SUPABASE_SCHEMA', 'public')
        }
    else:  # dev
        return {
            'url': os.getenv('SUPABASE_DEV_URL'),
            'service_key': os.getenv('SUPABASE_DEV_SERVICE_KEY'),
            'anon_key': os.getenv('SUPABASE_DEV_ANON_KEY'),
            'schema': os.getenv('SUPABASE_SCHEMA', 'public')
        }


def get_automation_service_url() -> str:
    """
    Get automation service URL based on current environment

    Returns:
        str: Automation service URL
    """
    env = get_environment()

    if env == 'production':
        return os.getenv('AUTOMATION_PROD_SERVICE_URL', 'https://prod-squidgy-browser-automation.onrender.com')
    elif env == 'staging':
        return os.getenv('AUTOMATION_STAGING_SERVICE_URL', 'https://staging-squidgy-browser-automation.onrender.com')
    else:  # dev
        return os.getenv('AUTOMATION_DEV_SERVICE_URL', 'https://backgroundautomationuser1-1644057ede7b.herokuapp.com')


# Helper function to print current environment
def print_environment_info():
    """Print current environment configuration"""
    env = get_environment()
    config = get_supabase_config()
    automation_url = get_automation_service_url()

    print(f"🌍 Environment: {env.upper()}")
    print(f"📦 Supabase URL: {config['url']}")
    print(f"🤖 Automation Service: {automation_url}")
    print(f"🔑 Using {'STAGING' if env == 'staging' else 'DEV' if env == 'dev' else 'PROD'} credentials")
