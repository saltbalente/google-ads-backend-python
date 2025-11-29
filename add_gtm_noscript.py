#!/usr/bin/env python3
"""
Script para agregar el noscript de GTM a templates que les falta.
"""

import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / 'templates' / 'landing'

GTM_BODY_NOSCRIPT = '''  <!-- Google Tag Manager (noscript) -->
  <noscript><iframe src="https://www.googletagmanager.com/ns.html?id={{ gtm_id }}"
  height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
  <!-- End Google Tag Manager (noscript) -->

'''

def add_noscript_to_template(template_path):
    """Add GTM noscript after <body> if not present."""
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already has noscript
    if 'googletagmanager.com/ns.html?id=' in content:
        print(f"  ⏭️  Noscript ya presente")
        return False
    
    # Skip AMP templates
    if '<html amp' in content or '<html ⚡' in content:
        print(f"  ⚙️  Template AMP - no requiere noscript")
        return False
    
    # Check if has GTM variable
    if '{{ gtm_id }}' not in content:
        print(f"  ⚠️  Template no tiene {{ gtm_id }} - ejecutar add_gtm_to_templates.py primero")
        return False
    
    # Add noscript after <body>
    body_pattern = r'(<body[^>]*>)'
    if re.search(body_pattern, content):
        content = re.sub(body_pattern, r'\1\n' + GTM_BODY_NOSCRIPT, content, count=1)
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ Noscript GTM agregado")
        return True
    else:
        print(f"  ⚠️  No se encontró etiqueta <body>")
        return False

def main():
    print("📊 Agregando noscript de GTM a templates")
    print("=" * 80)
    
    templates = list(TEMPLATES_DIR.glob('*.html'))
    
    print(f"📁 Procesando {len(templates)} templates\n")
    
    updated = 0
    skipped = 0
    
    for template in sorted(templates):
        print(f"📄 {template.name}")
        try:
            if add_noscript_to_template(template):
                updated += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
        print()
    
    print("=" * 80)
    print("📊 RESUMEN:")
    print(f"  ✅ Actualizados: {updated}")
    print(f"  ⏭️  Omitidos: {skipped}")
    print(f"  📝 Total: {len(templates)}")
    print()
    
    if updated > 0:
        print("🎉 ¡Noscript de GTM agregado exitosamente!")
        print("\n📋 Próximos pasos:")
        print("  1. Ejecutar: python3 validate_gtm_templates.py")
        print("  2. Verificar que todos los templates pasen la validación")

if __name__ == "__main__":
    main()
