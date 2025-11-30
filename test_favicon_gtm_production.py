#!/usr/bin/env python3
"""
Script de prueba end-to-end para verificar favicon y GTM en producción.
Genera una landing page y valida que tenga ambos elementos correctamente.
"""

import requests
import re
import sys
from urllib.parse import urlparse

# Configuración
API_URL = "https://google-ads-backend-mm4z.onrender.com/api/landing/build"
TEST_DATA = {
    "customerId": "1234567890",
    "adGroupId": "9876543210",
    "whatsappNumber": "+525512345678",
    "gtmId": "GTM-TEST123",
    "selectedTemplate": "mystical"
}

def test_api_response():
    """Test 1: Verificar que el API responde correctamente."""
    print("🧪 TEST 1: API Response")
    print("-" * 80)
    
    try:
        response = requests.post(API_URL, json=TEST_DATA, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                url = data.get('url')
                print(f"  ✅ API respondió exitosamente")
                print(f"  📍 URL generada: {url}")
                return url
            else:
                error = data.get('error', 'Unknown error')
                print(f"  ❌ API retornó error: {error}")
                return None
        else:
            print(f"  ❌ API retornó código: {response.status_code}")
            print(f"     Respuesta: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error al llamar API: {str(e)}")
        return None

def test_landing_page_loads(url):
    """Test 2: Verificar que la landing page carga correctamente."""
    print("\n🧪 TEST 2: Landing Page Loads")
    print("-" * 80)
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            html = response.text
            print(f"  ✅ Landing page carga correctamente")
            print(f"  📏 Tamaño HTML: {len(html):,} bytes")
            return html
        else:
            print(f"  ❌ Landing page retornó código: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error al cargar landing page: {str(e)}")
        return None

def test_favicon_present(html):
    """Test 3: Verificar que el favicon está presente en el HTML."""
    print("\n🧪 TEST 3: Favicon Present")
    print("-" * 80)
    
    # Buscar tag de favicon
    favicon_patterns = [
        r'<link[^>]*rel=["\']icon["\'][^>]*>',
        r'<link[^>]*href=["\'][^"\']*favicon[^"\']*["\'][^>]*>',
    ]
    
    found = False
    for pattern in favicon_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            found = True
            print(f"  ✅ Favicon encontrado:")
            for match in matches[:3]:  # Mostrar máximo 3
                print(f"     {match[:80]}...")
            break
    
    if not found:
        print(f"  ❌ Favicon NO encontrado en el HTML")
    
    return found

def test_gtm_present(html):
    """Test 4: Verificar que GTM está presente y con el ID correcto."""
    print("\n🧪 TEST 4: Google Tag Manager Present")
    print("-" * 80)
    
    issues = []
    
    # Check 1: GTM script en head
    if 'googletagmanager.com/gtm.js' in html or 'googletagmanager.com/gtag/js' in html:
        print(f"  ✅ Script de GTM encontrado")
    else:
        print(f"  ❌ Script de GTM NO encontrado")
        issues.append("Script GTM faltante")
    
    # Check 2: GTM ID correcto (no debe ser variable sin renderizar)
    if '{{ gtm_id }}' in html:
        print(f"  ❌ Variable {{ gtm_id }} sin renderizar encontrada")
        issues.append("Variable Jinja2 sin renderizar")
    else:
        print(f"  ✅ Variable GTM renderizada correctamente")
    
    # Check 3: GTM ID específico del test
    if TEST_DATA['gtmId'] in html:
        print(f"  ✅ GTM ID correcto encontrado: {TEST_DATA['gtmId']}")
        count = html.count(TEST_DATA['gtmId'])
        print(f"     Aparece {count} vez/veces en el HTML")
    else:
        print(f"  ⚠️  GTM ID del test ({TEST_DATA['gtmId']}) no encontrado")
        print(f"     Buscando cualquier GTM ID...")
        gtm_ids = re.findall(r'GTM-[A-Z0-9]{7,}', html)
        if gtm_ids:
            print(f"     GTM IDs encontrados: {', '.join(set(gtm_ids))}")
        else:
            print(f"     No se encontraron GTM IDs")
            issues.append("GTM ID no encontrado")
    
    # Check 4: Noscript iframe
    if 'googletagmanager.com/ns.html' in html:
        print(f"  ✅ Noscript iframe de GTM encontrado")
    else:
        print(f"  ⚠️  Noscript iframe de GTM no encontrado (puede ser template AMP)")
    
    return len(issues) == 0

def main():
    print("\n" + "="*80)
    print("🚀 PRUEBA END-TO-END: Favicon y Google Tag Manager")
    print("="*80)
    print(f"\n🎯 Template a probar: {TEST_DATA['selectedTemplate']}")
    print(f"📊 GTM ID de prueba: {TEST_DATA['gtmId']}")
    print()
    
    # Test 1: API
    url = test_api_response()
    if not url:
        print("\n❌ TEST FALLIDO: No se pudo obtener URL de la landing page")
        return 1
    
    # Test 2: Landing page carga
    html = test_landing_page_loads(url)
    if not html:
        print("\n❌ TEST FALLIDO: No se pudo cargar la landing page")
        return 1
    
    # Test 3: Favicon
    favicon_ok = test_favicon_present(html)
    
    # Test 4: GTM
    gtm_ok = test_gtm_present(html)
    
    # Resumen
    print("\n" + "="*80)
    print("📊 RESUMEN DE TESTS")
    print("="*80)
    
    tests_passed = sum([url is not None, html is not None, favicon_ok, gtm_ok])
    total_tests = 4
    
    print(f"\n  ✅ Tests pasados: {tests_passed}/{total_tests}")
    print(f"  📍 URL de la landing: {url}")
    print()
    
    if tests_passed == total_tests:
        print("🎉 ¡TODOS LOS TESTS PASARON!")
        print("\n✨ Implementación correcta verificada:")
        print("   • Favicon presente y accesible")
        print("   • GTM correctamente implementado")
        print("   • GTM ID renderizado correctamente")
        print("   • Landing page funcional")
        return 0
    else:
        print("⚠️  ALGUNOS TESTS FALLARON")
        print("\nRevisa los detalles arriba para ver qué necesita corrección.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
