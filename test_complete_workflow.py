#!/usr/bin/env python3
"""
Test Completo del Sistema de Templates:
1. Crear template básico
2. Guardarlo en templates/landing/ y templates/previews/
3. Editarlo (simular edición con IA)
4. Re-guardarlo
5. Verificar archivos en GitHub
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from custom_template_manager import CustomTemplateManager

def test_complete_workflow():
    print("\n" + "="*70)
    print("🧪 TEST COMPLETO: Generar → Guardar → Editar → Re-Guardar")
    print("="*70 + "\n")
    
    manager = CustomTemplateManager()
    
    # ========== PASO 1: GENERAR TEMPLATE BÁSICO ==========
    print("📝 PASO 1: Generando template básico...")
    
    template_basico = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ business_type }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Arial', sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .hero { 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            text-align: center;
        }
        h1 { 
            font-size: 3.5rem; 
            margin-bottom: 1rem; 
            text-shadow: 2px 2px 8px rgba(0,0,0,0.3);
            animation: fadeIn 1s ease-in;
        }
        .subtitle { 
            font-size: 1.5rem; 
            margin-bottom: 2rem; 
            opacity: 0.9;
        }
        .cta-button { 
            background: #f6d365; 
            color: #333; 
            padding: 15px 40px; 
            border-radius: 50px; 
            text-decoration: none; 
            font-weight: bold; 
            display: inline-block;
            transition: transform 0.3s;
        }
        .cta-button:hover { transform: scale(1.05); }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <section class="hero">
        <div class="container">
            <h1>{{ business_type }}</h1>
            <p class="subtitle">Servicios profesionales de {{ keywords }}</p>
            <a href="#contacto" class="cta-button">{{ call_to_action }}</a>
        </div>
    </section>
    
    <footer style="text-align: center; padding: 40px 20px; background: rgba(0,0,0,0.3);">
        <p>&copy; {{ current_year }} - {{ business_type }}</p>
        <p>Email: {{ email }} | Teléfono: {{ phone }}</p>
    </footer>
</body>
</html>"""
    
    template_data = {
        "name": "Test Template Básico",
        "content": template_basico,
        "businessType": "Servicios de Tarot Profesional",
        "targetAudience": "Personas buscando orientación espiritual",
        "tone": "Místico y profesional",
        "callToAction": "Consulta Ahora",
        "colorScheme": "Púrpura y dorado",
        "sections": ["hero", "contact"],
        "keywords": ["tarot", "videncia", "lectura de cartas"]
    }
    
    # ========== PASO 2: GUARDAR TEMPLATE ==========
    print("\n💾 PASO 2: Guardando template en GitHub structure...")
    result = manager.save_template(template_data)
    
    if not result["success"]:
        print(f"❌ Error guardando: {result.get('message')}")
        return False
    
    print(f"✅ {result['message']}")
    print(f"   📁 Landing: {result['files']['landing']}")
    print(f"   📁 Preview: {result['files']['preview']}")
    
    template_filename = result["template"]["filename"].replace('.html', '')
    
    # ========== PASO 3: VERIFICAR ARCHIVOS ==========
    print("\n🔍 PASO 3: Verificando archivos creados...")
    
    landing_path = result['files']['landing']
    preview_path = result['files']['preview']
    
    if os.path.exists(landing_path):
        size = os.path.getsize(landing_path)
        print(f"✅ Landing existe: {size} bytes")
    else:
        print(f"❌ Landing NO existe: {landing_path}")
        return False
    
    if os.path.exists(preview_path):
        size = os.path.getsize(preview_path)
        print(f"✅ Preview existe: {size} bytes")
    else:
        print(f"❌ Preview NO existe: {preview_path}")
        return False
    
    # ========== PASO 4: SIMULAR EDICIÓN CON IA ==========
    print("\n✏️  PASO 4: Simulando edición con IA...")
    print("   Instrucción: 'Agregar sección de testimonios'")
    
    # Simular HTML editado por Grok
    template_editado = template_basico.replace(
        '</section>',
        '''</section>
    
    <section class="testimonios" style="padding: 80px 20px; background: rgba(0,0,0,0.2);">
        <div class="container">
            <h2 style="text-align: center; font-size: 2.5rem; margin-bottom: 3rem;">Lo que dicen nuestros clientes</h2>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px;">
                <div style="background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px);">
                    <div style="color: #f6d365; margin-bottom: 15px;">⭐⭐⭐⭐⭐</div>
                    <p style="font-style: italic; margin-bottom: 20px;">"Excelente lectura de tarot, muy precisa y profesional. Me ayudó a encontrar claridad en momentos difíciles."</p>
                    <p style="font-weight: bold;">- María González</p>
                </div>
                
                <div style="background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px);">
                    <div style="color: #f6d365; margin-bottom: 15px;">⭐⭐⭐⭐⭐</div>
                    <p style="font-style: italic; margin-bottom: 20px;">"Increíble experiencia, la lectura fue muy detallada y me dio las respuestas que buscaba. Totalmente recomendado."</p>
                    <p style="font-weight: bold;">- Carlos Ramírez</p>
                </div>
                
                <div style="background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px);">
                    <div style="color: #f6d365; margin-bottom: 15px;">⭐⭐⭐⭐⭐</div>
                    <p style="font-style: italic; margin-bottom: 20px;">"Profesionalismo y calidez humana. Las predicciones fueron acertadas y me dieron mucha paz interior."</p>
                    <p style="font-weight: bold;">- Ana Martínez</p>
                </div>
            </div>
        </div>
    </section>''',
        1  # Solo la primera ocurrencia
    )
    
    print(f"✅ Template editado: +{len(template_editado) - len(template_basico)} caracteres")
    print("   Agregada sección de testimonios con 3 reviews")
    
    # ========== PASO 5: RE-GUARDAR TEMPLATE EDITADO ==========
    print("\n💾 PASO 5: Re-guardando template editado...")
    
    update_result = manager.update_template(
        template_filename,
        {"content": template_editado}
    )
    
    if not update_result["success"]:
        print(f"❌ Error actualizando: {update_result.get('message')}")
        return False
    
    print(f"✅ {update_result['message']}")
    
    # ========== PASO 6: VERIFICAR ACTUALIZACIÓN ==========
    print("\n🔍 PASO 6: Verificando actualización...")
    
    updated_template = manager.get_template_by_id(template_filename)
    if updated_template:
        if "testimonios" in updated_template["content"]:
            print("✅ Template actualizado correctamente (contiene 'testimonios')")
            print(f"   Tamaño final: {len(updated_template['content'])} caracteres")
        else:
            print("❌ Template NO contiene la sección de testimonios")
            return False
    else:
        print("❌ No se pudo recuperar template actualizado")
        return False
    
    # ========== PASO 7: VERIFICAR PREVIEW ACTUALIZADO ==========
    print("\n🔍 PASO 7: Verificando preview actualizado...")
    
    if os.path.exists(preview_path):
        with open(preview_path, 'r', encoding='utf-8') as f:
            preview_content = f.read()
        
        if "testimonios" in preview_content and "María González" in preview_content:
            print("✅ Preview actualizado correctamente")
            print(f"   Tamaño preview: {len(preview_content)} caracteres")
        else:
            print("❌ Preview NO fue actualizado")
            return False
    
    # ========== PASO 8: PREPARAR PARA GIT ==========
    print("\n📦 PASO 8: Archivos listos para Git...")
    
    print("\n   Comando para commit:")
    print(f"   git add templates/landing/{template_filename}.html")
    print(f"   git add templates/previews/{template_filename}_preview.html")
    print(f"   git add custom_templates/templates_index.json")
    print(f'   git commit -m "✨ Test Template Básico con testimonios agregados"')
    print(f"   git push")
    
    # ========== RESUMEN FINAL ==========
    print("\n" + "="*70)
    print("✅ TEST COMPLETO FINALIZADO CON ÉXITO")
    print("="*70)
    
    print("\n📊 Resumen:")
    print(f"   ✅ Template generado: Test Template Básico")
    print(f"   ✅ Guardado en: templates/landing/")
    print(f"   ✅ Preview en: templates/previews/")
    print(f"   ✅ Editado: Sección de testimonios agregada")
    print(f"   ✅ Re-guardado: Archivos actualizados")
    print(f"   ✅ Listo para: Git commit y GitHub Pages")
    
    print("\n🌐 URLs después del push:")
    print(f"   Landing: https://raw.githubusercontent.com/saltbalente/google-ads-backend-python/main/templates/landing/{template_filename}.html")
    print(f"   Preview: https://saltbalente.github.io/google-ads-backend-python/templates/previews/{template_filename}_preview.html")
    
    # ========== PASO 9: LIMPIEZA (OPCIONAL) ==========
    print("\n🧹 ¿Eliminar template de prueba? (Presiona Enter para mantener, 'd' para eliminar)")
    # En test automático no preguntamos, lo dejamos
    print("   Template mantenido para inspección manual")
    
    return True

if __name__ == "__main__":
    try:
        success = test_complete_workflow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
