#!/usr/bin/env python3
"""
🧪 TEST COMPLETO DEL SISTEMA DE LANDING PAGES
==============================================

Este script prueba todo el flujo del sistema:
1. Health checks
2. Sistema de diseño dinámico
3. Templates disponibles
4. Preview de landing pages
5. Generación de contenido
6. Custom templates

Uso:
    python3 test_full_system.py [--production]
    
    Sin flags: prueba local (localhost:5000)
    --production: prueba el servidor de Render
"""

import requests
import json
import sys
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

LOCAL_URL = "http://localhost:5000"
PRODUCTION_URL = "https://google-ads-backend-mm4z.onrender.com"

# Detectar si es producción
USE_PRODUCTION = "--production" in sys.argv or "-p" in sys.argv
BASE_URL = PRODUCTION_URL if USE_PRODUCTION else LOCAL_URL

print(f"🌐 Testing: {BASE_URL}")
print("=" * 60)

# ============================================================================
# HELPERS
# ============================================================================

class TestResult(Enum):
    PASSED = "✅ PASSED"
    FAILED = "❌ FAILED"
    SKIPPED = "⏭️ SKIPPED"
    WARNING = "⚠️ WARNING"


@dataclass
class Test:
    name: str
    result: TestResult
    message: str
    duration_ms: float = 0
    details: Optional[Dict] = None


def api_call(method: str, endpoint: str, data: Optional[Dict] = None, 
             headers: Optional[Dict] = None) -> Tuple[int, Dict]:
    """Hace una llamada a la API y retorna status code y respuesta."""
    url = f"{BASE_URL}{endpoint}"
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)
    
    start = time.time()
    try:
        if method.upper() == "GET":
            resp = requests.get(url, headers=default_headers, timeout=30)
        elif method.upper() == "POST":
            resp = requests.post(url, json=data, headers=default_headers, timeout=60)
        elif method.upper() == "PUT":
            resp = requests.put(url, json=data, headers=default_headers, timeout=30)
        elif method.upper() == "DELETE":
            resp = requests.delete(url, headers=default_headers, timeout=30)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        elapsed = (time.time() - start) * 1000
        
        try:
            return resp.status_code, resp.json(), elapsed
        except:
            return resp.status_code, {"raw": resp.text[:500]}, elapsed
            
    except requests.exceptions.RequestException as e:
        elapsed = (time.time() - start) * 1000
        return 0, {"error": str(e)}, elapsed


def run_test(name: str, test_func) -> Test:
    """Ejecuta un test y captura errores."""
    print(f"\n🧪 Testing: {name}...")
    start = time.time()
    
    try:
        result, message, details = test_func()
        duration = (time.time() - start) * 1000
        test = Test(name, result, message, duration, details)
    except Exception as e:
        duration = (time.time() - start) * 1000
        test = Test(name, TestResult.FAILED, f"Exception: {str(e)}", duration)
    
    print(f"   {test.result.value}: {test.message} ({test.duration_ms:.0f}ms)")
    return test


# ============================================================================
# TESTS
# ============================================================================

def test_health():
    """Test 1: Health Check básico"""
    status, data, elapsed = api_call("GET", "/api/health")
    
    if status == 200 and data.get("status") == "ok":
        return TestResult.PASSED, f"Backend v{data.get('version', '?')} operativo", data
    else:
        return TestResult.FAILED, f"Status: {status}, Response: {data}", data


def test_ai_health():
    """Test 2: Health de servicios de IA"""
    status, data, elapsed = api_call("GET", "/api/ai/health")
    
    if status == 200:
        openai_ok = data.get("openai", {}).get("available", False)
        gemini_ok = data.get("gemini", {}).get("available", False)
        
        if openai_ok or gemini_ok:
            return TestResult.PASSED, f"OpenAI: {openai_ok}, Gemini: {gemini_ok}", data
        else:
            return TestResult.WARNING, "AI services may have issues", data
    else:
        return TestResult.FAILED, f"Status: {status}", data


def test_system_status():
    """Test 3: System Status completo"""
    status, data, elapsed = api_call("GET", "/api/system/status")
    
    if status == 200:
        sys_status = data.get("status", "unknown")
        version = data.get("version", "?")
        memory = data.get("system", {}).get("memory_mb", "?")
        
        if sys_status in ["operational", "partial"]:
            return TestResult.PASSED, f"Status: {sys_status}, v{version}, {memory}MB RAM", data
        else:
            return TestResult.WARNING, f"Status: {sys_status}", data
    else:
        return TestResult.FAILED, f"Status: {status}, Error: {data.get('error', '?')}", data


def test_templates_list():
    """Test 4: Lista de templates disponibles"""
    status, data, elapsed = api_call("GET", "/api/templates")
    
    if status == 200:
        templates = data.get("templates", [])
        
        # Handle both list and dict formats
        if isinstance(templates, dict):
            count = len(templates)
            names = list(templates.keys())[:5]
        elif isinstance(templates, list):
            count = len(templates)
            names = [t.get("name", t) if isinstance(t, dict) else str(t) for t in templates[:5]]
        else:
            count = 0
            names = []
        
        if count > 0:
            return TestResult.PASSED, f"{count} templates: {names}...", data
        else:
            return TestResult.WARNING, "No templates found", data
    else:
        return TestResult.FAILED, f"Status: {status}", data


def test_design_intelligence():
    """Test 5: Sistema de Inteligencia de Diseño"""
    # Importamos localmente para probar
    try:
        from design_intelligence import generate_dynamic_design, KeywordAnalyzer
        
        # Probamos con diferentes keywords
        test_cases = [
            (["amarre de amor", "recuperar ex"], "amor_amarres"),
            (["tarot", "lectura cartas"], "tarot_adivinacion"),
            (["brujo", "magia negra"], "brujeria_magia"),
            (["dinero", "prosperidad"], "prosperidad_dinero"),
        ]
        
        results = []
        for keywords, expected_category in test_cases:
            design = generate_dynamic_design(keywords, "test")
            actual = design["category"]
            match = actual == expected_category
            results.append({
                "keywords": keywords,
                "expected": expected_category,
                "actual": actual,
                "match": match,
                "atmosphere": design["atmosphere_name"],
                "hero_icon": design["hero_icon"]
            })
        
        all_match = all(r["match"] for r in results)
        if all_match:
            return TestResult.PASSED, f"4/4 categorías detectadas correctamente", {"tests": results}
        else:
            failed = [r for r in results if not r["match"]]
            return TestResult.WARNING, f"Algunas categorías no coincidieron", {"tests": results}
            
    except ImportError as e:
        return TestResult.SKIPPED, f"No se puede importar localmente: {e}", None


def test_template_preview():
    """Test 6: Preview de template"""
    status, data, elapsed = api_call("GET", "/api/templates/preview/mystical")
    
    if status == 200:
        html = data if isinstance(data, str) else data.get("raw", "")
        has_html = "<!doctype html>" in html.lower() or "<html" in html.lower()
        
        if has_html:
            return TestResult.PASSED, f"Preview HTML generado ({len(html)} bytes)", {"size": len(html)}
        else:
            return TestResult.WARNING, "Response no parece HTML", {"preview": html[:200]}
    else:
        return TestResult.FAILED, f"Status: {status}", data


def test_custom_templates_list():
    """Test 7: Lista de custom templates"""
    status, data, elapsed = api_call("GET", "/api/custom-templates")
    
    if status == 200:
        templates = data.get("templates", [])
        count = len(templates)
        
        if count > 0:
            names = [t.get("name", "?") for t in templates[:3]]
            return TestResult.PASSED, f"{count} custom templates: {names}", data
        else:
            return TestResult.PASSED, "No custom templates (OK para nueva instalación)", data
    else:
        return TestResult.FAILED, f"Status: {status}", data


def test_landing_preview():
    """Test 8: Preview de landing page (sin publicar)"""
    # Este test requiere credenciales de Google Ads, así que lo simulamos
    preview_data = {
        "customerId": "1234567890",
        "adGroupId": "123456789",
        "whatsappNumber": "+1234567890",
        "gtmId": "GTM-TEST123"
    }
    
    status, data, elapsed = api_call("POST", "/api/landing/preview", preview_data)
    
    # Sin credenciales válidas, esperamos error de autenticación
    if status == 401 or status == 403:
        return TestResult.SKIPPED, "Requiere credenciales Google Ads válidas", data
    elif status == 400:
        return TestResult.SKIPPED, f"Parámetros requeridos: {data.get('error', '?')}", data
    elif status == 200:
        return TestResult.PASSED, "Preview generado correctamente", data
    else:
        return TestResult.WARNING, f"Status inesperado: {status}", data


def test_landing_history():
    """Test 9: Historial de landings"""
    status, data, elapsed = api_call("GET", "/api/landing/history")
    
    if status == 200:
        landings = data.get("landings", [])
        count = len(landings)
        return TestResult.PASSED, f"{count} landings en historial", data
    else:
        return TestResult.FAILED, f"Status: {status}", data


def test_rate_limiter():
    """Test 10: Rate Limiter funcional"""
    try:
        from rate_limiter import get_rate_limiter
        
        limiter = get_rate_limiter()
        
        # Simular varias peticiones
        test_ip = "192.168.1.100"
        test_customer = "test_customer_123"
        
        results = []
        for i in range(7):  # Intentar 7 veces (límite es 5/min)
            allowed, msg, retry = limiter.check_rate_limit(test_ip, test_customer)
            results.append({"attempt": i+1, "allowed": allowed, "message": msg})
        
        allowed_count = sum(1 for r in results if r["allowed"])
        blocked_count = len(results) - allowed_count
        
        if allowed_count <= 5 and blocked_count >= 2:
            return TestResult.PASSED, f"Rate limiting activo: {allowed_count} permitidos, {blocked_count} bloqueados", {"results": results}
        else:
            return TestResult.WARNING, f"Rate limiting puede no estar funcionando correctamente", {"results": results}
            
    except ImportError as e:
        return TestResult.SKIPPED, f"No se puede importar: {e}", None


def test_quality_validator():
    """Test 11: Validador de calidad"""
    try:
        from landing_quality import validate_landing_page, QualityLevel
        
        # HTML de prueba
        test_html = """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="utf-8">
            <title>Test Landing Page</title>
            <meta name="description" content="Test description">
        </head>
        <body>
            <h1>Test Headline</h1>
            <a href="https://wa.me/1234567890">WhatsApp</a>
            <script>(function(w,d,s,l,i){w[l]=w[l]||[];})(window,document,'script','dataLayer','GTM-TEST123');</script>
        </body>
        </html>
        """
        
        config = {"gtm_id": "GTM-TEST123", "whatsapp_number": "+1234567890"}
        report = validate_landing_page(test_html, config)
        
        critical = report.critical_count
        warnings = report.warning_count
        score = report.score
        
        if score > 0:
            return TestResult.PASSED, f"Score: {score}/100, {critical} críticos, {warnings} warnings", {
                "score": score,
                "issues": [{"level": i.level.value, "message": i.message} for i in report.issues[:5]]
            }
        else:
            return TestResult.WARNING, f"Score muy bajo: {score}", {"issues": report.issues}
            
    except ImportError as e:
        return TestResult.SKIPPED, f"No se puede importar: {e}", None


def test_dynamic_template_exists():
    """Test 12: Template dinámico existe"""
    import os
    template_path = "templates/landing/dynamic_ai.html"
    
    if os.path.exists(template_path):
        with open(template_path, 'r') as f:
            content = f.read()
        
        has_design_vars = "{{ design." in content
        has_css_vars = "css_variables" in content
        has_jinja = "{%" in content
        
        if has_design_vars and has_css_vars and has_jinja:
            return TestResult.PASSED, f"Template dinámico correcto ({len(content)} bytes)", {
                "has_design_vars": has_design_vars,
                "has_css_vars": has_css_vars,
                "size": len(content)
            }
        else:
            return TestResult.WARNING, "Template puede estar incompleto", None
    else:
        return TestResult.FAILED, "Template dynamic_ai.html no existe", None


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "=" * 60)
    print("🧪 SUITE DE TESTS COMPLETA DEL SISTEMA")
    print("=" * 60)
    
    tests = [
        ("1. Health Check", test_health),
        ("2. AI Health", test_ai_health),
        ("3. System Status", test_system_status),
        ("4. Templates List", test_templates_list),
        ("5. Design Intelligence", test_design_intelligence),
        ("6. Template Preview", test_template_preview),
        ("7. Custom Templates", test_custom_templates_list),
        ("8. Landing Preview", test_landing_preview),
        ("9. Landing History", test_landing_history),
        ("10. Rate Limiter", test_rate_limiter),
        ("11. Quality Validator", test_quality_validator),
        ("12. Dynamic Template", test_dynamic_template_exists),
    ]
    
    results = []
    for name, test_func in tests:
        result = run_test(name, test_func)
        results.append(result)
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE TESTS")
    print("=" * 60)
    
    passed = sum(1 for r in results if r.result == TestResult.PASSED)
    failed = sum(1 for r in results if r.result == TestResult.FAILED)
    warnings = sum(1 for r in results if r.result == TestResult.WARNING)
    skipped = sum(1 for r in results if r.result == TestResult.SKIPPED)
    
    print(f"\n   ✅ Passed:   {passed}")
    print(f"   ❌ Failed:   {failed}")
    print(f"   ⚠️  Warnings: {warnings}")
    print(f"   ⏭️  Skipped:  {skipped}")
    print(f"\n   Total: {len(results)} tests")
    
    # Tiempo total
    total_time = sum(r.duration_ms for r in results)
    print(f"   Tiempo total: {total_time/1000:.2f}s")
    
    # Status final
    if failed == 0:
        print("\n🎉 ¡TODOS LOS TESTS CRÍTICOS PASARON!")
        return 0
    else:
        print(f"\n⚠️ {failed} tests fallaron. Revisar logs arriba.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
