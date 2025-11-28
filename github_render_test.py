#!/usr/bin/env python3
"""
Quick GitHub Token Test for Render.com

Run this in Render.com to verify if the GitHub token works
"""

import os
import requests

def test_github_token():
    """Test GitHub token in Render.com environment"""

    token = os.getenv('GITHUB_TOKEN')
    owner = os.getenv('GITHUB_REPO_OWNER')
    repo = os.getenv('GITHUB_REPO_NAME')

    print("🔍 GitHub Token Test for Render.com")
    print("=" * 40)

    if not token:
        print("❌ GITHUB_TOKEN not found in environment")
        return False

    if not owner:
        print("❌ GITHUB_REPO_OWNER not found in environment")
        return False

    if not repo:
        print("❌ GITHUB_REPO_NAME not found in environment")
        return False

    print(f"📋 Testing with:")
    print(f"   Owner: {owner}")
    print(f"   Repo: {repo}")
    print(f"   Token: ***{token[-4:]}")

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json'
    }

    try:
        url = f'https://api.github.com/repos/{owner}/{repo}'
        response = requests.get(url, headers=headers, timeout=10)

        print(f"🔗 API URL: {url}")
        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            permissions = data.get('permissions', {})

            print("✅ SUCCESS: Repository found!")
            print(f"📁 Full name: {data.get('full_name')}")
            print(f"🔒 Private: {data.get('private')}")
            print(f"📤 Push permissions: {permissions.get('push', False)}")

            if permissions.get('push', False):
                print("🎉 GitHub token is working correctly!")
                return True
            else:
                print("⚠️  Repository found but no push permissions")
                return False

        elif response.status_code == 401:
            print("❌ ERROR: Invalid token or authentication failed")
            return False

        elif response.status_code == 404:
            print("❌ ERROR: Repository not found")
            print("   Check GITHUB_REPO_OWNER and GITHUB_REPO_NAME")
            return False

        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_github_token()
    if success:
        print("\n✅ GitHub configuration is correct!")
    else:
        print("\n❌ GitHub configuration needs to be fixed.")