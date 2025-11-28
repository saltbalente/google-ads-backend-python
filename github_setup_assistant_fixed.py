#!/usr/bin/env python3
"""
Interactive GitHub Setup Assistant

This script helps you set up GitHub configuration step by step.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(cmd):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def check_github_access(owner, repo, token):
    """Test GitHub access with provided credentials."""
    import requests

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    try:
        # Test repository access
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(repo_url, headers=headers, timeout=10)

        if response.status_code == 200:
            repo_data = response.json()
            permissions = repo_data.get("permissions", {})

            return {
                "success": True,
                "repo_name": repo_data.get("full_name"),
                "private": repo_data.get("private"),
                "can_push": permissions.get("push", False)
            }
        elif response.status_code == 404:
            return {"success": False, "error": "Repository not found"}
        elif response.status_code == 401:
            return {"success": False, "error": "Invalid token"}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    print("🚀 GitHub Setup Assistant for Landing Page Generator")
    print("=" * 55)
    print()

    # Check current environment
    current_vars = {
        "GITHUB_REPO_OWNER": os.getenv("GITHUB_REPO_OWNER"),
        "GITHUB_REPO_NAME": os.getenv("GITHUB_REPO_NAME"),
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN")
    }

    print("📋 Current Environment Variables:")
    for var, value in current_vars.items():
        if value:
            if "TOKEN" in var:
                display_value = f"***{value[-4:]}"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: NOT SET")
    print()

    # Interactive setup
    print("🔧 Let's configure GitHub step by step:")
    print()

    # Step 1: GitHub Owner
    while True:
        owner = input("1. Enter your GitHub username or organization name: ").strip()
        if owner:
            break
        print("❌ GitHub owner cannot be empty. Please try again.")

    # Step 2: Repository Name
    while True:
        repo = input("2. Enter the repository name (e.g., 'landing-pages'): ").strip()
        if repo:
            break
        print("❌ Repository name cannot be empty. Please try again.")

    # Step 3: Personal Access Token
    while True:
        token = input("3. Enter your GitHub Personal Access Token: ").strip()
        if token and len(token) > 20:  # Basic validation
            break
        print("❌ Token seems invalid. Please check and try again.")

    print()
    print("🔍 Testing GitHub access...")

    # Test the configuration
    test_result = check_github_access(owner, repo, token)

    if test_result["success"]:
        print("✅ GitHub access successful!")
        print(f"📁 Repository: {test_result['repo_name']}")
        print(f"🔒 Private: {test_result['private']}")
        print(f"📤 Push access: {test_result['can_push']}")

        if not test_result["can_push"]:
            print("⚠️  WARNING: No push permissions detected!")
            print("   Make sure your token has 'repo' scope for private repos or 'public_repo' for public repos.")
            print()

        # Generate setup commands
        print("📝 Setup Commands:")
        print("=" * 20)
        print("# Add these to your environment variables:")
        print(f"export GITHUB_REPO_OWNER=\"{owner}\"")
        print(f"export GITHUB_REPO_NAME=\"{repo}\"")
        print(f"export GITHUB_TOKEN=\"{token}\"")
        print()

        # For Render.com
        print("# For Render.com deployment, add these environment variables:")
        print(f"GITHUB_REPO_OWNER = {owner}")
        print(f"GITHUB_REPO_NAME = {repo}")
        print(f"GITHUB_TOKEN = {token}")
        print()

        # Test with diagnostics
        print("🧪 Testing with diagnostic script...")
        test_env = os.environ.copy()
        test_env.update({
            "GITHUB_REPO_OWNER": owner,
            "GITHUB_REPO_NAME": repo,
            "GITHUB_TOKEN": token
        })

        success, stdout, stderr = run_command("python3 github_diagnostics.py")
        if success:
            print("✅ Diagnostic test passed!")
        else:
            print("❌ Diagnostic test failed:")
            print(stdout)
            print(stderr)

    else:
        print("❌ GitHub access failed!")
        print(f"Error: {test_result['error']}")
        print()
        print("💡 Troubleshooting:")
        print("- Check that the repository exists and is accessible")
        print("- Verify your token has the correct permissions")
        print("- Make sure the repository name and owner are spelled correctly")
        print("- For organization repos, ensure you're a member with write access")

    print()
    print("📖 For detailed setup instructions, see: GITHUB_SETUP_GUIDE.md")
    print("🔍 Run diagnostics anytime with: python3 github_diagnostics.py")

if __name__ == "__main__":
    main()
