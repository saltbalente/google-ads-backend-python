#!/usr/bin/env python3
"""
Test script for Repository Importer
Run this to verify the system works before using in production
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(__file__))

from repository_importer import RepositoryImporter


def test_url_parsing():
    """Test GitHub URL parsing"""
    print("🧪 Testing URL parsing...")
    
    importer = RepositoryImporter()
    
    test_cases = [
        ("https://github.com/user/repo", ("user", "repo")),
        ("https://github.com/user/repo.git", ("user", "repo")),
        ("git@github.com:user/repo.git", ("user", "repo")),
        ("https://github.com/saltbalente/test-landing", ("saltbalente", "test-landing")),
    ]
    
    passed = 0
    failed = 0
    
    for url, expected in test_cases:
        try:
            owner, repo = importer._parse_github_url(url)
            if (owner, repo) == expected:
                print(f"  ✅ {url} → {owner}/{repo}")
                passed += 1
            else:
                print(f"  ❌ {url} → Expected {expected}, got ({owner}, {repo})")
                failed += 1
        except Exception as e:
            print(f"  ❌ {url} → Error: {str(e)}")
            failed += 1
    
    print(f"\n📊 URL Parsing: {passed} passed, {failed} failed\n")
    return failed == 0


def test_whatsapp_replacement():
    """Test WhatsApp number replacement"""
    print("🧪 Testing WhatsApp replacement...")
    
    importer = RepositoryImporter()
    
    test_html = """
    <a href="https://wa.me/1234567890">WhatsApp</a>
    <a href="https://api.whatsapp.com/send?phone=9876543210">Chat</a>
    <div>WhatsApp: +52 55 1234 5678</div>
    """
    
    result = importer._replace_whatsapp(test_html, "+521234567890")
    
    checks = [
        ("wa.me/521234567890" in result, "wa.me link updated"),
        (result.count("wa.me/521234567890") >= 2, "Multiple wa.me links updated"),
        ("api.whatsapp.com" not in result, "api.whatsapp.com converted to wa.me"),
    ]
    
    passed = sum(1 for check, _ in checks if check)
    failed = len(checks) - passed
    
    for check, description in checks:
        status = "✅" if check else "❌"
        print(f"  {status} {description}")
    
    print(f"\n📊 WhatsApp Replacement: {passed} passed, {failed} failed\n")
    return failed == 0


def test_gtm_replacement():
    """Test GTM ID replacement"""
    print("🧪 Testing GTM replacement...")
    
    importer = RepositoryImporter()
    
    test_html = """
    <script>(function(w,d,s,l,i){...})(window,document,'script','dataLayer','GTM-OLD1234');</script>
    <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-OLD1234"></iframe></noscript>
    <div data-gtm="GTM-OLD1234"></div>
    """
    
    result = importer._replace_gtm(test_html, "GTM-NEW9876")
    
    checks = [
        (result.count("GTM-NEW9876") == 3, "All 3 GTM IDs replaced"),
        ("GTM-OLD1234" not in result, "Old GTM ID removed"),
    ]
    
    passed = sum(1 for check, _ in checks if check)
    failed = len(checks) - passed
    
    for check, description in checks:
        status = "✅" if check else "❌"
        print(f"  {status} {description}")
    
    print(f"\n📊 GTM Replacement: {passed} passed, {failed} failed\n")
    return failed == 0


def test_phone_replacement():
    """Test phone number replacement"""
    print("🧪 Testing phone replacement...")
    
    importer = RepositoryImporter()
    
    test_html = """
    <a href="tel:+1234567890">Llamar</a>
    <p>Teléfono: +1234567890</p>
    <p>Tel: +1234567890</p>
    """
    
    result = importer._replace_phone(test_html, "+9876543210")
    
    checks = [
        ("tel:+9876543210" in result, "tel: link updated"),
        ("+9876543210" in result, "Phone display updated"),
    ]
    
    passed = sum(1 for check, _ in checks if check)
    failed = len(checks) - passed
    
    for check, description in checks:
        status = "✅" if check else "❌"
        print(f"  {status} {description}")
    
    print(f"\n📊 Phone Replacement: {passed} passed, {failed} failed\n")
    return failed == 0


def test_github_token():
    """Test GitHub token availability"""
    print("🧪 Testing GitHub token...")
    
    token = os.getenv('GITHUB_TOKEN')
    
    if token:
        print(f"  ✅ GitHub token found (length: {len(token)})")
        if token.startswith('ghp_'):
            print("  ✅ Token format looks correct (starts with ghp_)")
            return True
        else:
            print("  ⚠️  Token doesn't start with ghp_ (might be old format)")
            return True
    else:
        print("  ❌ GitHub token NOT found")
        print("  ℹ️  Set GITHUB_TOKEN environment variable:")
        print("     export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        return False


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Repository Importer Test Suite")
    print("=" * 60)
    print()
    
    results = {
        "URL Parsing": test_url_parsing(),
        "WhatsApp Replacement": test_whatsapp_replacement(),
        "GTM Replacement": test_gtm_replacement(),
        "Phone Replacement": test_phone_replacement(),
        "GitHub Token": test_github_token(),
    }
    
    print("=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total_passed = sum(1 for p in results.values() if p)
    total_tests = len(results)
    
    print()
    print(f"Total: {total_passed}/{total_tests} tests passed")
    
    if all(results.values()):
        print("\n🎉 All tests passed! System ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Fix issues before using in production.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
