#!/usr/bin/env python3
"""
GitHub Access Test - Verifica que la configuración de GitHub funciona
"""

import os
import requests
from dotenv import load_dotenv

def test_github_access():
    """Test GitHub repository access with current configuration."""
    load_dotenv()  # Load environment variables from .env file

    owner = os.getenv("GITHUB_REPO_OWNER")
    repo = os.getenv("GITHUB_REPO_NAME")
    token = os.getenv("GITHUB_TOKEN")

    print("🔍 GitHub Access Test")
    print("=" * 30)

    # Check environment variables
    print("📋 Environment Variables:")
    if owner:
        print(f"✅ GITHUB_REPO_OWNER: {owner}")
    else:
        print("❌ GITHUB_REPO_OWNER: NOT SET")
        return False

    if repo:
        print(f"✅ GITHUB_REPO_NAME: {repo}")
    else:
        print("❌ GITHUB_REPO_NAME: NOT SET")
        return False

    if token:
        print(f"✅ GITHUB_TOKEN: ***{token[-4:]}")
    else:
        print("❌ GITHUB_TOKEN: NOT SET")
        return False

    print()
    print("🔍 Testing GitHub API access...")

    # Test repository access
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    try:
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(repo_url, headers=headers, timeout=10)

        if response.status_code == 200:
            repo_data = response.json()
            permissions = repo_data.get("permissions", {})

            print("✅ Repository access successful!")
            print(f"📁 Repository: {repo_data.get('full_name')}")
            print(f"🔒 Private: {repo_data.get('private')}")
            print(f"📤 Push permissions: {permissions.get('push', False)}")

            if not permissions.get('push', False):
                print("⚠️  WARNING: No push permissions detected!")
                print("   Make sure your token has 'repo' scope for private repos or 'public_repo' for public repos.")
            else:
                print("🎉 GitHub configuration is ready!")

            return True

        elif response.status_code == 404:
            print("❌ Repository not found!")
            print("   Check that the repository exists and the names are spelled correctly.")
            return False
        elif response.status_code == 401:
            print("❌ Authentication failed!")
            print("   Check that your token is valid and has the correct permissions.")
            return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_github_access()
    if success:
        print("\n✅ GitHub is properly configured! The landing page generator should work now.")
    else:
        print("\n❌ GitHub configuration needs to be fixed. Check the errors above.")
        print("💡 Run 'python3 github_setup_assistant.py' for guided setup.")