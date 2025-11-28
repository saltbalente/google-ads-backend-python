#!/usr/bin/env python3
"""
GitHub Diagnostics Script for Landing Page Generator

This script helps diagnose GitHub-related issues that might be causing
the landing page generation to fail.

Usage:
    python3 github_diagnostics.py

Make sure to set the required environment variables:
- GITHUB_REPO_OWNER
- GITHUB_REPO_NAME
- GITHUB_TOKEN
"""

import os
import sys
import json
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("🔍 GitHub Diagnostics for Landing Page Generator")
    print("=" * 50)

    # Check if we can import the generator
    try:
        from landing_generator import LandingPageGenerator
        print("✅ Successfully imported LandingPageGenerator")
    except Exception as e:
        print(f"❌ Failed to import LandingPageGenerator: {e}")
        return

    # Check environment variables
    required_vars = ["GITHUB_REPO_OWNER", "GITHUB_REPO_NAME", "GITHUB_TOKEN"]
    missing_vars = []

    print("\n📋 Environment Variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if "TOKEN" in var:
                print(f"✅ {var}: ***{value[-4:]}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
            missing_vars.append(var)

    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables and try again.")
        return

    # Try to create generator and run diagnostics
    try:
        print("\n🏗️ Creating LandingPageGenerator...")
        generator = LandingPageGenerator()
        print("✅ Generator created successfully")

        print("\n🔍 Running GitHub diagnostics...")
        diagnostics = generator.diagnose_github_issues()

        print(f"\n📊 Diagnostics Results: {diagnostics['overall_status']}")
        print("-" * 30)

        print("Environment:")
        for key, value in diagnostics.get("environment", {}).items():
            print(f"  {key}: {value}")

        print("\nChecks:")
        for check, status in diagnostics.get("checks", {}).items():
            print(f"  {check}: {status}")

        if "token_user" in diagnostics:
            print(f"\nToken User: {diagnostics['token_user']}")

        print("\n💡 Recommendations:")
        for rec in diagnostics.get("recommendations", []):
            print(f"  • {rec}")

        if diagnostics["overall_status"] == "❌ ISSUES FOUND":
            print("\n❌ Issues found that need to be resolved before the landing page generator can work.")
        else:
            print("\n✅ All GitHub checks passed! The landing page generator should work correctly.")

    except Exception as e:
        print(f"\n❌ Error during diagnostics: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()