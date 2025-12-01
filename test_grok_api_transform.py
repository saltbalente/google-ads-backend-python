#!/usr/bin/env python3
"""
Test Real con API de Grok
=========================

Este script realiza una prueba REAL con la API de Grok (x-ai/grok-code-fast-1):
1. Carga un template HTML base
2. Envía instrucciones a la API de Grok
3. Recibe el código transformado de Grok
4. Incrusta automáticamente la respuesta en el template
5. Valida que los cambios solicitados se aplicaron correctamente

Requisitos:
- Variable de entorno OPEN_ROUTER_API_KEY o OPENROUTER_API_KEY configurada
- Conexión a internet
"""

import os
import sys
import re
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
if os.path.exists('.env'):
    load_dotenv()
    print("✅ Variables de entorno cargadas desde .env")

# ====================================================================
# CONFIGURACIÓN
# ====================================================================

# API Configuration
OPENROUTER_API_KEY = os.getenv('OPEN_ROUTER_API_KEY') or os.getenv('OPENROUTER_API_KEY') or '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'
OPENROUTER_ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'
GROK_MODEL = 'x-ai/grok-code-fast-1'
API_TIMEOUT = 60  # segundos

# Template base para pruebas
TEMPLATE_BASE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Consulta de Tarot Profesional</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; }
        .hero {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 100px 20px;
            text-align: center;
        }
        .hero h1 { font-size: 3rem; margin-bottom: 20px; }
        .hero p { font-size: 1.2rem; margin-bottom: 30px; }
        .content { padding: 60px 20px; max-width: 1200px; margin: 0 auto; }
        .services { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; margin: 40px 0; }
        .service-card {
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .service-card:hover { transform: translateY(-5px); }
        footer {
            background: #333;
            color: white;
            text-align: center;
            padding: 40px 20px;
        }
    </style>
</head>
<body>
    <section class="hero">
        <h1>Consulta de Tarot Profesional</h1>
        <p>Descubre lo que el futuro tiene preparado para ti</p>
    </section>

    <div class="content">
        <h2>Nuestros Servicios de Tarot</h2>
        <div class="services">
            <div class="service-card">
                <h3>Lectura de Tarot Básica</h3>
                <p>Consulta general sobre tu situación actual y perspectivas futuras.</p>
            </div>
            <div class="service-card">
                <h3>Tarot del Amor</h3>
                <p>Descubre las respuestas sobre tus relaciones sentimentales.</p>
            </div>
            <div class="service-card">
                <h3>Tarot Profesional</h3>
                <p>Orientación sobre tu carrera y oportunidades laborales.</p>
            </div>
        </div>
    </div>

    <footer>
        <p>&copy; 2025 Consulta de Tarot. Todos los derechos reservados.</p>
    </footer>
</body>
</html>"""


# ====================================================================
# FUNCIONES DE API
# ====================================================================

def call_grok_api(instructions, html_code, timeout=60):
    """
    Llama a la API de Grok para transformar el template HTML.
    
    Args:
        instructions (str): Instrucciones de lo que se quiere hacer
        html_code (str): Código HTML a transformar
        timeout (int): Timeout en segundos
    
    Returns:
        tuple: (codigo_transformado, error)
    """
    if not OPENROUTER_API_KEY:
        return None, '❌ ERROR: Variable OPEN_ROUTER_API_KEY o OPENROUTER_API_KEY no configurada'
    
    # Construir el prompt para Grok
    prompt = f"""Eres un experto desarrollador web especializado en editar código HTML/CSS.

INSTRUCCIONES DEL USUARIO:
{instructions}

CÓDIGO HTML ACTUAL:
{html_code}

REGLAS IMPORTANTES:
1. Devuelve SOLO el código HTML completo modificado
2. NO agregues explicaciones antes o después del código
3. NO uses markdown (```html o ```)
4. Mantén la estructura HTML válida
5. Preserva los estilos CSS existentes
6. Si agregas nuevas secciones, usa estilos inline o en <style>
7. Asegúrate que el código sea responsive

Retorna el código HTML completo y modificado según las instrucciones."""

    messages = [
        {
            "role": "system",
            "content": "Eres un asistente experto en desarrollo web que modifica código HTML/CSS de manera precisa y profesional. Siempre devuelves código limpio sin explicaciones adicionales."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    payload = {
        'model': GROK_MODEL,
        'messages': messages,
        'temperature': 0.2,
        'max_tokens': 16000
    }
    
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://google-ads-backend-mm4z.onrender.com',
        'X-Title': 'Google Ads Backend - Test'
    }
    
    print(f"\n🌐 Llamando a API de Grok ({GROK_MODEL})...")
    print(f"   Instrucciones: {instructions[:100]}...")
    print(f"   Tamaño HTML: {len(html_code)} bytes")
    print(f"   Timeout: {timeout}s")
    
    try:
        response = requests.post(
            OPENROUTER_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code != 200:
            error_text = response.text[:500]
            return None, f'❌ API Error {response.status_code}: {error_text}'
        
        data = response.json()
        
        # Extraer el contenido de la respuesta
        try:
            content = data['choices'][0]['message']['content']
            
            # Limpiar markdown si Grok lo agregó
            content = re.sub(r'^```html\s*', '', content, flags=re.MULTILINE)
            content = re.sub(r'^```\s*$', '', content, flags=re.MULTILINE)
            content = content.strip()
            
            print(f"✅ Respuesta recibida: {len(content)} bytes")
            
            # Validar que sea HTML válido
            if not content.startswith('<!DOCTYPE html>') and not content.startswith('<html'):
                return None, f'❌ La respuesta de Grok no es HTML válido (comienza con: {content[:100]}...)'
            
            return content, None
            
        except (KeyError, IndexError) as e:
            return None, f'❌ Estructura de respuesta inválida: {str(e)}'
            
    except requests.exceptions.Timeout:
        return None, f'❌ Timeout después de {timeout}s - intenta con un template más pequeño'
    except requests.exceptions.ConnectionError as e:
        return None, f'❌ Error de conexión: {str(e)}'
    except Exception as e:
        return None, f'❌ Error inesperado: {str(e)}'


def validate_transformation(original_html, transformed_html, instructions):
    """
    Valida que la transformación se haya realizado correctamente.
    
    Args:
        original_html (str): HTML original
        transformed_html (str): HTML transformado
        instructions (str): Instrucciones que se dieron
    
    Returns:
        dict: Resultados de validación
    """
    results = {
        'valid': True,
        'checks': [],
        'warnings': []
    }
    
    # Check 1: HTML válido y completo
    if transformed_html.startswith('<!DOCTYPE html>') or transformed_html.startswith('<html'):
        results['checks'].append('✅ HTML completo y válido')
    else:
        results['checks'].append('❌ HTML incompleto o inválido')
        results['valid'] = False
    
    # Check 2: Tamaño razonable
    size_increase = len(transformed_html) - len(original_html)
    size_increase_pct = (size_increase / len(original_html)) * 100
    
    if size_increase > 0:
        results['checks'].append(f'✅ Código aumentó {size_increase} bytes ({size_increase_pct:.1f}%)')
    elif size_increase < 0:
        results['checks'].append(f'⚠️  Código redujo {abs(size_increase)} bytes ({abs(size_increase_pct):.1f}%)')
        results['warnings'].append('El código es más pequeño que el original')
    else:
        results['checks'].append('⚠️  Código sin cambios de tamaño')
        results['warnings'].append('No se detectaron cambios significativos')
    
    # Check 3: Buscar palabras clave de las instrucciones
    keywords_found = []
    
    # Extraer palabras clave de las instrucciones
    if 'whatsapp' in instructions.lower():
        if 'wa.me' in transformed_html.lower() or 'whatsapp' in transformed_html.lower():
            keywords_found.append('WhatsApp')
    
    if 'cta' in instructions.lower():
        soup = BeautifulSoup(transformed_html, 'html.parser')
        cta_sections = soup.find_all(['section', 'div'], class_=re.compile(r'cta', re.I))
        if len(cta_sections) >= 2:
            keywords_found.append(f'{len(cta_sections)} secciones CTA')
    
    # Buscar keyword específica (ej: "Consulta de tarot")
    keyword_match = re.search(r'palabra clave[:\s]+["\']([^"\']+)["\']', instructions, re.I)
    if keyword_match:
        keyword = keyword_match.group(1)
        if keyword.lower() in transformed_html.lower():
            keywords_found.append(f'Keyword "{keyword}"')
    
    if keywords_found:
        results['checks'].append(f'✅ Elementos encontrados: {", ".join(keywords_found)}')
    else:
        results['checks'].append('⚠️  No se encontraron keywords específicas')
        results['warnings'].append('Verifica manualmente que los cambios sean los esperados')
    
    # Check 4: Estructura HTML válida con BeautifulSoup
    try:
        soup = BeautifulSoup(transformed_html, 'html.parser')
        if soup.find('html') and soup.find('body'):
            results['checks'].append('✅ Estructura HTML correcta')
        else:
            results['checks'].append('❌ Estructura HTML incompleta')
            results['valid'] = False
    except Exception as e:
        results['checks'].append(f'❌ Error parseando HTML: {str(e)}')
        results['valid'] = False
    
    return results


# ====================================================================
# TEST PRINCIPAL
# ====================================================================

def run_grok_api_test():
    """Ejecuta el test completo con la API de Grok"""
    
    print("=" * 70)
    print("🤖 TEST CON API REAL DE GROK (x-ai/grok-code-fast-1)")
    print("=" * 70)
    
    # Verificar API key
    if not OPENROUTER_API_KEY:
        print("\n❌ ERROR: No se encontró la variable de entorno OPEN_ROUTER_API_KEY")
        print("\nPara configurarla:")
        print("  export OPEN_ROUTER_API_KEY='tu-api-key-aqui'")
        print("\nO agrégala en el archivo .env")
        return False
    
    print(f"\n✅ API Key configurada: {OPENROUTER_API_KEY[:10]}...{OPENROUTER_API_KEY[-4:]}")
    
    # Instrucciones de prueba
    instructions = """Crea 2 CTAs para la palabra clave "Consulta de tarot" con botones de WhatsApp.

Cada CTA debe:
- Tener un diseño profesional y atractivo
- Incluir un botón de WhatsApp con enlace wa.me/5215512345678
- Usar la palabra clave "Consulta de tarot" en el texto
- Tener estilos responsive
- El primer CTA debe tener fondo con gradiente morado
- El segundo CTA debe tener fondo gris claro

Inserta los CTAs en lugares estratégicos del template (después del hero y antes del footer)."""
    
    print(f"\n📋 Instrucciones para Grok:")
    print(f"   {instructions[:150]}...")
    
    print(f"\n📄 Template base: {len(TEMPLATE_BASE)} bytes")
    
    # Llamar a la API de Grok
    start_time = datetime.now()
    transformed_html, error = call_grok_api(instructions, TEMPLATE_BASE, timeout=API_TIMEOUT)
    elapsed = (datetime.now() - start_time).total_seconds()
    
    if error:
        print(f"\n❌ ERROR en llamada a API:")
        print(f"   {error}")
        return False
    
    print(f"\n✅ Transformación completada en {elapsed:.1f}s")
    print(f"📄 HTML transformado: {len(transformed_html)} bytes")
    print(f"📊 Incremento: +{len(transformed_html) - len(TEMPLATE_BASE)} bytes")
    
    # Validar transformación
    print("\n" + "=" * 70)
    print("🔍 VALIDACIÓN DE TRANSFORMACIÓN")
    print("=" * 70)
    
    validation = validate_transformation(TEMPLATE_BASE, transformed_html, instructions)
    
    for check in validation['checks']:
        print(f"   {check}")
    
    if validation['warnings']:
        print(f"\n⚠️  Advertencias:")
        for warning in validation['warnings']:
            print(f"   - {warning}")
    
    # Guardar resultado
    output_file = 'test_grok_output.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(transformed_html)
    
    print(f"\n💾 Archivo guardado: {output_file}")
    
    # Análisis detallado con BeautifulSoup
    print("\n" + "=" * 70)
    print("🔬 ANÁLISIS DETALLADO")
    print("=" * 70)
    
    soup = BeautifulSoup(transformed_html, 'html.parser')
    
    # Buscar CTAs
    cta_sections = soup.find_all(['section', 'div'], class_=re.compile(r'cta', re.I))
    print(f"\n📍 Secciones CTA encontradas: {len(cta_sections)}")
    
    # Buscar enlaces de WhatsApp
    whatsapp_links = soup.find_all('a', href=re.compile(r'wa\.me', re.I))
    print(f"📱 Enlaces de WhatsApp: {len(whatsapp_links)}")
    
    if whatsapp_links:
        for i, link in enumerate(whatsapp_links, 1):
            print(f"   {i}. {link.get('href', 'N/A')}")
    
    # Buscar keyword
    keyword_count = transformed_html.lower().count('consulta de tarot')
    print(f"🔑 Menciones de 'Consulta de tarot': {keyword_count}")
    
    # Resultado final
    print("\n" + "=" * 70)
    if validation['valid'] and len(cta_sections) >= 2 and len(whatsapp_links) >= 2:
        print("✅ TEST EXITOSO - Transformación completada correctamente")
        print("=" * 70)
        print(f"\n🌐 Abre el archivo en tu navegador:")
        print(f"   open {output_file}")
        return True
    else:
        print("⚠️  TEST COMPLETADO CON ADVERTENCIAS")
        print("=" * 70)
        print(f"\nRevisa manualmente el archivo: {output_file}")
        return False


if __name__ == '__main__':
    success = run_grok_api_test()
    sys.exit(0 if success else 1)
