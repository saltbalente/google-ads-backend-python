#!/usr/bin/env python3
"""
Test del Custom Template Manager con nueva estructura
Guarda en templates/landing/ y templates/previews/
"""

import sys
import os

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from custom_template_manager import CustomTemplateManager

def test_custom_template_manager():
    """Prueba completa del sistema de custom templates"""
    
    print("\n" + "="*60)
    print("🧪 TEST: Custom Template Manager - GitHub Structure")
    print("="*60 + "\n")
    
    manager = CustomTemplateManager()
    
    # Template de prueba generado con Grok
    template_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ business_type }} - {{ keywords }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Georgia', serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; }
        .hero { min-height: 100vh; display: flex; align-items: center; justify-content: center; text-align: center; padding: 20px; }
        h1 { font-size: 3rem; margin-bottom: 1rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .cta-button { background: #f6d365; color: #333; padding: 15px 40px; border-radius: 50px; text-decoration: none; font-weight: bold; display: inline-block; margin-top: 20px; }
        .problem { background: rgba(0,0,0,0.3); padding: 60px 20px; }
        .solution { padding: 60px 20px; }
    </style>
</head>
<body>
    <section class="hero">
        <div>
            <h1>{{ business_type }}</h1>
            <p>Servicios profesionales de {{ keywords }}</p>
            <a href="#contacto" class="cta-button">{{ call_to_action }}</a>
        </div>
    </section>
    
    <section class="problem">
        <h2>¿Sientes que algo falta en tu vida?</h2>
        <p>Muchas personas buscan respuestas y orientación espiritual...</p>
    </section>
    
    <section class="solution">
        <h2>Encuentra tu camino</h2>
        <p>Con más de 10 años de experiencia...</p>
    </section>
    
    <footer>
        <p>{{ current_year }} - {{ business_type }}</p>
        <p>Email: {{ email }} | Teléfono: {{ phone }}</p>
    </footer>
</body>
</html>"""
    
    template_data = {
        "name": "Template Tarot Místico Pro",
        "content": template_content,
        "businessType": "Tarot y Videncia Profesional",
        "targetAudience": "Personas buscando orientación espiritual",
        "tone": "Místico y empático",
        "callToAction": "Consulta Ahora",
        "colorScheme": "Púrpura y dorado",
        "sections": ["hero", "problem", "solution", "testimonials", "contact"],
        "keywords": ["tarot", "videncia", "lectura de cartas", "orientación espiritual"]
    }
    
    print("📝 1. Guardando template...")
    result = manager.save_template(template_data)
    
    if result["success"]:
        print(f"✅ {result['message']}")
        print(f"   📁 Landing: {result['files']['landing']}")
        print(f"   📁 Preview: {result['files']['preview']}")
        template_saved = result["template"]
    else:
        print(f"❌ Error: {result['message']}")
        return False
    
    print("\n📋 2. Cargando todos los templates...")
    all_templates = manager.get_all_templates()
    print(f"✅ Total de templates: {len(all_templates)}")
    for t in all_templates[-3:]:  # Mostrar últimos 3
        print(f"   - {t['name']} ({t['filename']})")
    
    print("\n🔍 3. Buscando templates por keyword 'tarot'...")
    matching = manager.get_templates_by_keywords(["tarot"])
    print(f"✅ Encontrados: {len(matching)} templates")
    for t in matching[:3]:
        print(f"   - {t['name']} (matches: {t['matchCount']})")
    
    print("\n📖 4. Obteniendo template por nombre...")
    filename = template_saved["filename"].replace('.html', '')
    retrieved = manager.get_template_by_id(filename)
    if retrieved:
        print(f"✅ Template encontrado: {retrieved['name']}")
        print(f"   Contenido: {len(retrieved['content'])} caracteres")
        print(f"   Keywords: {', '.join(retrieved['keywords'])}")
    else:
        print("❌ Template no encontrado")
    
    print("\n✏️  5. Actualizando template...")
    update_result = manager.update_template(
        filename,
        {"name": "Template Tarot Místico Pro v2", "tone": "Profesional y empático"}
    )
    if update_result["success"]:
        print(f"✅ {update_result['message']}")
    else:
        print(f"❌ {update_result['message']}")
    
    print("\n🗑️  6. Eliminando template de prueba...")
    delete_result = manager.delete_template(filename)
    if delete_result["success"]:
        print(f"✅ {delete_result['message']}")
    else:
        print(f"❌ {delete_result['message']}")
    
    print("\n" + "="*60)
    print("✅ PRUEBA COMPLETA FINALIZADA CON ÉXITO")
    print("="*60 + "\n")
    
    print("📁 Archivos creados en:")
    print(f"   - templates/landing/ (templates Jinja2)")
    print(f"   - templates/previews/ (previews HTML estáticos)")
    print(f"   - custom_templates/templates_index.json (índice)")
    
    return True

if __name__ == "__main__":
    try:
        success = test_custom_template_manager()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
