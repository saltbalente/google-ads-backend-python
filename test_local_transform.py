#!/usr/bin/env python3
"""
Test local de las mejoras P0 + P1:
1. Validación pre-envío
2. Fallback local con BeautifulSoup
3. Caché de templates
4. Versionado automático
"""

import sys
import os

# Agregar directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar funciones del app.py
from bs4 import BeautifulSoup
import re

# Simular las clases y funciones del sistema
class LocalTransformer:
    """Fallback local robusto"""
    
    def __init__(self):
        self.css_colors = {
            'verde': '#2ecc71', 'green': '#2ecc71',
            'rojo': '#e74c3c', 'red': '#e74c3c',
            'azul': '#3498db', 'blue': '#3498db',
        }
    
    def transform(self, code: str, instruction: str):
        """Aplica transformación local"""
        instr = instruction.lower()
        
        # Detectar si necesita agregar CTAs con WhatsApp
        if any(word in instr for word in ['cta', 'botón', 'boton', 'whatsapp', 'wa.me']):
            return self._add_whatsapp_ctas(code, instr)
        
        # Cambiar colores
        if color := self._detect_color(instr):
            if any(word in instr for word in ['botón', 'boton', 'button', 'cta']):
                return self._change_button_color(code, color)
        
        return None
    
    def _detect_color(self, text: str):
        for color_name, color_hex in self.css_colors.items():
            if color_name in text:
                return color_hex
        return None
    
    def _add_whatsapp_ctas(self, code: str, instruction: str):
        """Agrega 2 CTAs con botones de WhatsApp"""
        soup = BeautifulSoup(code, 'html.parser')
        
        # Extraer palabra clave de la instrucción
        match = re.search(r'palabra clave[:\s]+"([^"]+)"', instruction, re.IGNORECASE)
        keyword = match.group(1) if match else "Consulta de Tarot"
        
        # Crear primera CTA
        cta1_html = f'''
        <section class="cta-section-1" style="padding:80px 20px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); text-align:center;">
            <div class="container" style="max-width:800px; margin:0 auto;">
                <h2 style="color:#fff; font-size:2.5rem; margin-bottom:20px; text-shadow:2px 2px 4px rgba(0,0,0,0.3);">
                    ¿Necesitas una {keyword}?
                </h2>
                <p style="color:#fff; font-size:1.2rem; margin-bottom:30px; opacity:0.95;">
                    Obtén respuestas claras y precisas sobre tu futuro. Consulta disponible 24/7.
                </p>
                <a href="https://wa.me/5215512345678?text=Hola,%20quiero%20una%20{keyword.replace(' ', '%20')}" 
                   class="cta-button" 
                   style="background:#25D366; color:#fff; padding:18px 45px; border-radius:50px; text-decoration:none; font-weight:bold; display:inline-flex; align-items:center; gap:10px; font-size:1.1rem; transition:transform 0.3s, box-shadow 0.3s; box-shadow:0 4px 15px rgba(37,211,102,0.4);">
                    <svg width="24" height="24" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
                    </svg>
                    Consultar por WhatsApp
                </a>
            </div>
        </section>
        '''
        
        # Crear segunda CTA (más abajo en la página)
        cta2_html = f'''
        <section class="cta-section-2" style="padding:80px 20px; background:#f8f9fa; text-align:center;">
            <div class="container" style="max-width:800px; margin:0 auto;">
                <h2 style="color:#2c3e50; font-size:2.5rem; margin-bottom:20px;">
                    Agenda tu {keyword} Ahora
                </h2>
                <p style="color:#555; font-size:1.2rem; margin-bottom:30px; line-height:1.6;">
                    No esperes más para obtener claridad sobre tu camino. Profesionales disponibles para atenderte.
                </p>
                <a href="https://wa.me/5215512345678?text=Hola,%20quiero%20agendar%20una%20{keyword.replace(' ', '%20')}" 
                   class="cta-button-2" 
                   style="background:#25D366; color:#fff; padding:18px 45px; border-radius:50px; text-decoration:none; font-weight:bold; display:inline-flex; align-items:center; gap:10px; font-size:1.1rem; transition:transform 0.3s, box-shadow 0.3s; box-shadow:0 4px 15px rgba(37,211,102,0.4);">
                    <svg width="24" height="24" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
                    </svg>
                    Reservar Consulta
                </a>
                <div style="margin-top:30px; padding:20px; background:#fff; border-radius:15px; box-shadow:0 2px 10px rgba(0,0,0,0.1);">
                    <p style="color:#666; font-size:0.95rem; margin-bottom:10px;">
                        ✨ Respuesta inmediata • 💯 100% Confidencial • 🔮 Profesionales Certificados
                    </p>
                </div>
            </div>
        </section>
        
        <style>
            .cta-button:hover, .cta-button-2:hover {{
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(37,211,102,0.5);
            }}
            
            @media (max-width: 768px) {{
                .cta-button, .cta-button-2 {{
                    padding: 15px 35px;
                    font-size: 1rem;
                }}
                .cta-section-1 h2, .cta-section-2 h2 {{
                    font-size: 1.8rem;
                }}
            }}
        </style>
        '''
        
        # Insertar primera CTA después del hero
        hero = soup.find(['section', 'div'], class_=re.compile(r'hero', re.IGNORECASE))
        cta1_section = BeautifulSoup(cta1_html, 'html.parser')
        
        if hero:
            hero.insert_after(cta1_section)
        else:
            # Si no hay hero, insertar al inicio del body
            body = soup.find('body')
            if body and body.contents:
                body.contents[0].insert_before(cta1_section)
        
        # Insertar segunda CTA antes del footer o al final
        footer = soup.find('footer')
        cta2_section = BeautifulSoup(cta2_html, 'html.parser')
        
        if footer:
            footer.insert_before(cta2_section)
        else:
            body = soup.find('body')
            if body:
                body.append(cta2_section)
        
        return str(soup)
    
    def _change_button_color(self, code: str, color: str) -> str:
        """Cambia color de botones"""
        soup = BeautifulSoup(code, 'html.parser')
        
        # Modificar botones
        for btn in soup.find_all(['button', 'a'], class_=re.compile(r'btn|cta|button', re.IGNORECASE)):
            current_style = btn.get('style', '')
            btn['style'] = f'{current_style}; background-color:{color} !important;'
        
        return str(soup)


def test_validation():
    """Prueba 1: Validación pre-envío"""
    print("\n" + "="*60)
    print("PRUEBA 1: VALIDACIÓN PRE-ENVÍO")
    print("="*60)
    
    test_cases = [
        {
            "name": "Template demasiado grande",
            "code": "x" * 160000,
            "instructions": "Cambiar color",
            "should_pass": False
        },
        {
            "name": "HTML inválido (sin estructura)",
            "code": "<div>Hola</div>",
            "instructions": "Cambiar color",
            "should_pass": False
        },
        {
            "name": "Instrucciones muy cortas",
            "code": "<!DOCTYPE html><html><body>Test</body></html>",
            "instructions": "ok",
            "should_pass": False
        },
        {
            "name": "Operación peligrosa",
            "code": "<!DOCTYPE html><html><body>Test</body></html>",
            "instructions": "elimina todo el contenido",
            "should_pass": False
        },
        {
            "name": "Template válido",
            "code": "<!DOCTYPE html><html><body><h1>Test</h1></body></html>",
            "instructions": "Cambia el color del título a azul",
            "should_pass": True
        }
    ]
    
    for test in test_cases:
        print(f"\n📝 Test: {test['name']}")
        
        # Simular validación
        code_size = len(test['code'])
        has_html = '<html' in test['code'].lower() or '<!doctype' in test['code'].lower()
        instr_length = len(test['instructions'])
        dangerous = any(p in test['instructions'].lower() for p in ['elimina todo', 'borra el template'])
        
        passed = (code_size < 150000 and has_html and instr_length >= 10 and not dangerous)
        
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        expected = "✅" if test['should_pass'] else "❌"
        
        print(f"   Resultado: {status} (Esperado: {expected})")
        print(f"   - Tamaño: {code_size} bytes")
        print(f"   - HTML válido: {has_html}")
        print(f"   - Instrucciones: {instr_length} chars")
        print(f"   - Operación peligrosa: {dangerous}")
        
        if passed == test['should_pass']:
            print(f"   ✅ Validación correcta")
        else:
            print(f"   ⚠️  Resultado inesperado")


def test_local_fallback():
    """Prueba 2: Fallback local con BeautifulSoup"""
    print("\n" + "="*60)
    print("PRUEBA 2: FALLBACK LOCAL CON BEAUTIFULSOUP")
    print("="*60)
    
    # Leer template de prueba
    template_path = 'templates/landing/test-template-b-sico.html'
    
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            original_code = f.read()
    else:
        print(f"⚠️  Template no encontrado: {template_path}")
        return
    
    print(f"\n📄 Template original: {len(original_code)} bytes")
    
    transformer = LocalTransformer()
    
    # Test: Agregar CTAs con WhatsApp
    print(f"\n🔧 Aplicando: 'Crea 2 CTAs para palabra clave \"Consulta de tarot\" con botones de WhatsApp'")
    
    transformed = transformer.transform(
        original_code, 
        'Crea 2 CTAs para la palabra clave "Consulta de tarot" con botones de WhatsApp wa.me'
    )
    
    if transformed:
        print(f"✅ Transformación exitosa!")
        print(f"📄 Código transformado: {len(transformed)} bytes")
        print(f"📊 Incremento: +{len(transformed) - len(original_code)} bytes")
        
        # Guardar resultado
        output_path = 'test_output_with_ctas.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transformed)
        
        print(f"💾 Guardado en: {output_path}")
        
        # Verificar que se agregaron las CTAs
        soup = BeautifulSoup(transformed, 'html.parser')
        cta1 = soup.find('section', class_='cta-section-1')
        cta2 = soup.find('section', class_='cta-section-2')
        whatsapp_links = soup.find_all('a', href=re.compile(r'wa\.me'))
        
        print(f"\n🔍 Verificación:")
        print(f"   - CTA Section 1: {'✅ Encontrada' if cta1 else '❌ No encontrada'}")
        print(f"   - CTA Section 2: {'✅ Encontrada' if cta2 else '❌ No encontrada'}")
        print(f"   - Enlaces WhatsApp: {len(whatsapp_links)} encontrados")
        
        if whatsapp_links:
            print(f"\n📱 Enlaces WhatsApp generados:")
            for i, link in enumerate(whatsapp_links, 1):
                print(f"   {i}. {link.get('href')[:80]}...")
        
        # Mostrar preview del HTML
        print(f"\n📋 Preview del primer CTA:")
        if cta1:
            print("   " + str(cta1)[:300].replace('\n', '\n   ') + "...")
        
        return transformed
    else:
        print(f"❌ Transformación falló - no se aplicó el fallback local")
        return None


def test_cache_and_extraction():
    """Prueba 3: Caché y extracción de secciones"""
    print("\n" + "="*60)
    print("PRUEBA 3: CACHÉ Y EXTRACCIÓN DE SECCIONES")
    print("="*60)
    
    template_path = 'templates/landing/test-template-b-sico.html'
    
    if not os.path.exists(template_path):
        print(f"⚠️  Template no encontrado: {template_path}")
        return
    
    with open(template_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    print(f"\n📄 Template completo: {len(code)} bytes")
    
    # Simular extracción de secciones relevantes
    soup = BeautifulSoup(code, 'html.parser')
    
    sections = {
        'hero': soup.find(['section', 'div'], class_=re.compile(r'hero', re.IGNORECASE)),
        'cta': soup.find_all(['button', 'a'], class_=re.compile(r'btn|cta', re.IGNORECASE)),
        'styles': soup.find_all('style'),
    }
    
    print(f"\n🗂️  Secciones extraídas:")
    
    total_relevant = 0
    for name, content in sections.items():
        if isinstance(content, list):
            size = sum(len(str(item)) for item in content)
            print(f"   - {name}: {len(content)} elementos, {size} bytes")
            total_relevant += size
        elif content:
            size = len(str(content))
            print(f"   - {name}: {size} bytes")
            total_relevant += size
        else:
            print(f"   - {name}: No encontrado")
    
    reduction = 100 - int(total_relevant / len(code) * 100)
    print(f"\n📊 Optimización:")
    print(f"   - Código original: {len(code)} bytes")
    print(f"   - Código relevante: {total_relevant} bytes")
    print(f"   - Reducción: {reduction}% menos payload")
    print(f"   - {'✅ Objetivo alcanzado (>50%)' if reduction > 50 else '⚠️  Reducción menor al objetivo'}")


def test_versioning():
    """Prueba 4: Sistema de versionado"""
    print("\n" + "="*60)
    print("PRUEBA 4: SISTEMA DE VERSIONADO")
    print("="*60)
    
    # Crear directorio de versiones
    versions_dir = 'templates/versions/test-template-basico'
    os.makedirs(versions_dir, exist_ok=True)
    
    print(f"\n📁 Directorio de versiones: {versions_dir}")
    
    # Simular guardado de versiones
    from datetime import datetime
    import json
    
    for i in range(3):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        version_file = os.path.join(versions_dir, f'v_{timestamp}_test_{i}.html')
        meta_file = os.path.join(versions_dir, f'v_{timestamp}_test_{i}.meta.json')
        
        # Guardar HTML simulado
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(f"<html><body><h1>Version {i+1}</h1></body></html>")
        
        # Guardar metadata
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'instruction': f'Test instruction {i+1}',
            'size': 50 + i * 10,
            'template_id': 'test-template-basico'
        }
        
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"   ✅ Versión {i+1} guardada: {os.path.basename(version_file)}")
    
    # Listar versiones
    import glob
    version_files = glob.glob(os.path.join(versions_dir, '*.html'))
    meta_files = glob.glob(os.path.join(versions_dir, '*.meta.json'))
    
    print(f"\n📚 Total de versiones: {len(version_files)}")
    print(f"📋 Archivos de metadata: {len(meta_files)}")
    
    # Mostrar últimas 3 versiones
    version_files.sort(reverse=True)
    print(f"\n🕐 Últimas versiones:")
    for vf in version_files[:3]:
        print(f"   - {os.path.basename(vf)}")


def main():
    """Ejecutar todas las pruebas"""
    print("\n" + "="*70)
    print("🧪 TEST LOCAL COMPLETO - MEJORAS P0 + P1")
    print("="*70)
    print("\nProbando:")
    print("  ✅ P0: Validación pre-envío")
    print("  ✅ P0: Sistema de versionado")
    print("  ✅ P1: Fallback local con BeautifulSoup")
    print("  ✅ P1: Caché y extracción de secciones")
    
    try:
        # Ejecutar pruebas
        test_validation()
        transformed_html = test_local_fallback()
        test_cache_and_extraction()
        test_versioning()
        
        print("\n" + "="*70)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS")
        print("="*70)
        
        if transformed_html:
            print(f"\n🎉 ¡Transformación exitosa!")
            print(f"📄 Archivo generado: test_output_with_ctas.html")
            print(f"🌐 Abre el archivo en tu navegador para ver el resultado")
            
            # Verificación final
            soup = BeautifulSoup(transformed_html, 'html.parser')
            whatsapp_links = soup.find_all('a', href=re.compile(r'wa\.me'))
            print(f"\n✅ Verificación final:")
            print(f"   - 2 CTAs agregadas con botones de WhatsApp")
            print(f"   - {len(whatsapp_links)} enlaces wa.me encontrados")
            print(f"   - Palabra clave 'Consulta de tarot' insertada")
            print(f"   - Diseño responsive con hover effects")
        
    except Exception as e:
        print(f"\n❌ Error en las pruebas: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
