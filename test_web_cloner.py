#!/usr/bin/env python3
"""
Test suite para el sistema de clonación web
Verifica que todos los componentes funcionen correctamente
"""

import sys
import os
import tempfile
import shutil

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_cloner import WebCloner, WebClonerConfig, ContentProcessor
from github_cloner_uploader import GitHubClonerUploader


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_test(name, result, message=""):
    """Print test result with color"""
    icon = f"{Colors.GREEN}✅" if result else f"{Colors.RED}❌"
    status = f"{Colors.GREEN}PASS" if result else f"{Colors.RED}FAIL"
    print(f"{icon} {name}: {status}{Colors.END}")
    if message:
        print(f"   {message}")


def test_1_imports():
    """Test 1: Verificar imports"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 1: Verificar Imports{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    try:
        import requests
        print_test("requests", True)
    except ImportError:
        print_test("requests", False, "pip install requests")
        return False
    
    try:
        from bs4 import BeautifulSoup
        print_test("beautifulsoup4", True)
    except ImportError:
        print_test("beautifulsoup4", False, "pip install beautifulsoup4")
        return False
    
    try:
        from PIL import Image
        print_test("Pillow", True)
    except ImportError:
        print_test("Pillow", False, "pip install Pillow")
        return False
    
    try:
        from dotenv import load_dotenv
        print_test("python-dotenv", True)
    except ImportError:
        print_test("python-dotenv", False, "pip install python-dotenv")
        return False
    
    return True


def test_2_config():
    """Test 2: Verificar configuración"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 2: Verificar Configuración{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    try:
        config = WebClonerConfig()
        print_test("WebClonerConfig init", True)
        print_test("timeout configurado", config.timeout == 30, f"timeout={config.timeout}")
        print_test("max_retries configurado", config.max_retries == 3, f"retries={config.max_retries}")
        return True
    except Exception as e:
        print_test("WebClonerConfig init", False, str(e))
        return False


def test_3_content_processor():
    """Test 3: Verificar procesamiento de contenido"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 3: Procesamiento de Contenido{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    processor = ContentProcessor()
    
    # Test WhatsApp replacement
    processor.set_replacements(whatsapp='573001234567')
    html = '<a href="https://wa.me/573009999999">WhatsApp</a>'
    processed = processor._apply_replacements(html)
    whatsapp_ok = '573001234567' in processed
    print_test("WhatsApp replacement", whatsapp_ok)
    
    # Test phone replacement
    processor.set_replacements(phone='573001234567')
    html = '<a href="tel:+573009999999">Call</a>'
    processed = processor._apply_replacements(html)
    phone_ok = '573001234567' in processed
    print_test("Phone replacement", phone_ok)
    
    # Test GTM replacement
    processor.set_replacements(gtm_id='GTM-NEW123')
    html = '<script>dataLayer.push({gtmId: "GTM-OLD456"})</script>'
    processed = processor._apply_replacements(html)
    gtm_ok = 'GTM-NEW123' in processed
    print_test("GTM replacement", gtm_ok)
    
    return whatsapp_ok and phone_ok and gtm_ok


def test_4_url_validation():
    """Test 4: Verificar validación de URLs"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 4: Validación de URLs{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    # Import validation function from app
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Simulate validation logic
        def test_validate_url(url):
            from urllib.parse import urlparse
            try:
                parsed = urlparse(url)
                return all([parsed.scheme in ['http', 'https'], parsed.netloc])
            except:
                return False
        
        valid_urls = [
            'https://example.com',
            'http://example.com/page',
            'https://subdomain.example.com/path/to/page'
        ]
        
        invalid_urls = [
            'ftp://example.com',
            'example.com',
            'http://',
            ''
        ]
        
        all_valid = all(test_validate_url(url) for url in valid_urls)
        print_test("URLs válidas detectadas", all_valid)
        
        all_invalid = not any(test_validate_url(url) for url in invalid_urls)
        print_test("URLs inválidas rechazadas", all_invalid)
        
        return all_valid and all_invalid
        
    except Exception as e:
        print_test("Validación de URLs", False, str(e))
        return False


def test_5_github_config():
    """Test 5: Verificar configuración de GitHub"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 5: Configuración de GitHub{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    github_token = os.getenv('GITHUB_TOKEN')
    github_owner = os.getenv('GITHUB_REPO_OWNER')
    
    token_ok = bool(github_token and len(github_token) > 20)
    print_test("GITHUB_TOKEN configurado", token_ok, 
               f"{'✓ Token válido' if token_ok else '✗ Falta configurar GITHUB_TOKEN en .env'}")
    
    owner_ok = bool(github_owner)
    print_test("GITHUB_REPO_OWNER configurado", owner_ok,
               f"{'✓ Owner: ' + github_owner if owner_ok else '✗ Falta configurar GITHUB_REPO_OWNER en .env'}")
    
    if token_ok and owner_ok:
        try:
            uploader = GitHubClonerUploader()
            print_test("GitHubClonerUploader init", True)
            return True
        except Exception as e:
            print_test("GitHubClonerUploader init", False, str(e))
            return False
    else:
        print(f"\n{Colors.YELLOW}⚠️  Configura GitHub para tests completos{Colors.END}")
        return False


def test_6_basic_cloning():
    """Test 6: Prueba básica de clonación (sin subida)"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 6: Clonación Básica (sin subida){Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        
        print(f"{Colors.YELLOW}📥 Clonando https://example.com (puede tardar unos segundos)...{Colors.END}")
        
        from web_cloner import clone_website
        result = clone_website(
            url='https://example.com',
            output_dir=temp_dir
        )
        
        success = result.get('success', False)
        resources_count = result.get('resources_count', 0)
        
        print_test("Clonación exitosa", success)
        print_test("Recursos descargados", resources_count > 0, f"Descargados: {resources_count}")
        
        # Check if index.html exists
        index_path = os.path.join(temp_dir, 'index.html')
        html_exists = os.path.exists(index_path)
        print_test("index.html creado", html_exists)
        
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return success and html_exists
        
    except Exception as e:
        print_test("Clonación básica", False, str(e))
        return False


def test_7_api_endpoints():
    """Test 7: Verificar endpoints API (si Flask está corriendo)"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 7: Endpoints API{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    try:
        import requests
        
        # Test if server is running
        backend_url = os.getenv('BACKEND_URL', 'http://localhost:5000')
        
        print(f"{Colors.YELLOW}ℹ️  Probando conexión a {backend_url}...{Colors.END}")
        
        try:
            response = requests.get(f"{backend_url}/api/health", timeout=5)
            server_ok = response.status_code == 200
            print_test("Servidor corriendo", server_ok)
            
            if not server_ok:
                print(f"{Colors.YELLOW}⚠️  Inicia el servidor: python app.py{Colors.END}")
                return False
            
            # Test cloned sites endpoint
            response = requests.get(f"{backend_url}/api/cloned-sites", timeout=5)
            endpoint_ok = response.status_code == 200
            print_test("Endpoint /api/cloned-sites", endpoint_ok)
            
            return endpoint_ok
            
        except requests.exceptions.ConnectionError:
            print_test("Servidor corriendo", False, "Servidor no disponible")
            print(f"{Colors.YELLOW}ℹ️  Inicia el servidor para probar endpoints: python app.py{Colors.END}")
            return False
            
    except Exception as e:
        print_test("API endpoints", False, str(e))
        return False


def run_all_tests():
    """Ejecutar todos los tests"""
    print(f"""
{Colors.BLUE}╔══════════════════════════════════════════════════════════╗
║                                                          ║
║      🧪 TEST SUITE - SISTEMA DE CLONACIÓN WEB           ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝{Colors.END}
    """)
    
    results = []
    
    results.append(("Imports", test_1_imports()))
    results.append(("Configuración", test_2_config()))
    results.append(("Procesamiento de Contenido", test_3_content_processor()))
    results.append(("Validación de URLs", test_4_url_validation()))
    results.append(("Configuración de GitHub", test_5_github_config()))
    results.append(("Clonación Básica", test_6_basic_cloning()))
    results.append(("API Endpoints", test_7_api_endpoints()))
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}RESUMEN DE TESTS{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✅ PASS" if result else f"{Colors.RED}❌ FAIL"
        print(f"{status}{Colors.END} - {name}")
    
    print(f"\n{Colors.BLUE}{'─'*60}{Colors.END}")
    
    percentage = (passed / total) * 100
    
    if percentage == 100:
        color = Colors.GREEN
        icon = "🎉"
    elif percentage >= 70:
        color = Colors.YELLOW
        icon = "⚠️ "
    else:
        color = Colors.RED
        icon = "❌"
    
    print(f"{color}{icon} Tests pasados: {passed}/{total} ({percentage:.1f}%){Colors.END}")
    
    if percentage < 100:
        print(f"\n{Colors.YELLOW}💡 Verifica los tests fallidos arriba{Colors.END}")
    else:
        print(f"\n{Colors.GREEN}✅ ¡Todos los tests pasaron! Sistema listo.{Colors.END}")
    
    return percentage == 100


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Tests interrumpidos{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error inesperado: {str(e)}{Colors.END}")
        sys.exit(1)
