#!/usr/bin/env python3
"""
Render.com Environment Variables Checker

This script helps verify and update environment variables in Render.com
"""

import os
import json
from dotenv import load_dotenv

def check_render_variables():
    """Check current environment variables against Render.com setup."""
    load_dotenv()

    print("🔍 Render.com Environment Variables Checker")
    print("=" * 50)

    # Variables that should be in Render.com
    render_vars = {
        "GITHUB_REPO_OWNER": os.getenv("GITHUB_REPO_OWNER"),
        "GITHUB_REPO_NAME": os.getenv("GITHUB_REPO_NAME"),
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "OPENAI_MODEL": os.getenv("OPENAI_MODEL"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
        "DEEPSEEK_MODEL": os.getenv("DEEPSEEK_MODEL"),
        "GOOGLE_ADS_DEVELOPER_TOKEN": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "GOOGLE_ADS_CLIENT_ID": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "GOOGLE_ADS_CLIENT_SECRET": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "GOOGLE_ADS_REFRESH_TOKEN": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "VERCEL_TOKEN": os.getenv("VERCEL_TOKEN"),
        "VERCEL_PROJECT_ID": os.getenv("VERCEL_PROJECT_ID"),
        "LANDINGS_BASE_DOMAIN": os.getenv("LANDINGS_BASE_DOMAIN")
    }

    print("📋 Current .env variables:")
    for var, value in render_vars.items():
        if value:
            if "TOKEN" in var or "SECRET" in var or "KEY" in var:
                display_value = f"***{value[-4:]}" if len(value) > 4 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: NOT SET")

    print("\n🚀 Render.com Update Commands:")
    print("=" * 30)
    print("# Copy and run these commands in Render.com dashboard:")
    print("# Go to: https://dashboard.render.com/ → Your Service → Environment")
    print()

    for var, value in render_vars.items():
        if value:
            if "TOKEN" in var or "SECRET" in var or "KEY" in var:
                print(f"# {var} = ***{value[-4:]}")
            else:
                print(f"# {var} = {value}")
            print(f'echo "Update {var} in Render.com dashboard"')
            print()

    print("⚠️  IMPORTANT: Update GITHUB_TOKEN in Render.com to:")
    print(f"GITHUB_TOKEN = YOUR_GITHUB_TOKEN")
    print()
    print("💡 After updating, redeploy your Render.com service!")

if __name__ == "__main__":
    check_render_variables()