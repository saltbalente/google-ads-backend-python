#!/usr/bin/env python3
"""
Script para agregar Google Tag Manager a templates que no lo tienen.
Agrega tanto el script en <head> como el noscript en <body>.
"""

import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / 'templates' / 'landing'

# GTM implementation to add
GTM_HEAD_SCRIPT = '''
  <!-- Google Tag Manager -->
  <script>
    (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
    new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
    j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
    'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
    })(window,document,'script','dataLayer','{{ gtm_id }}');
  </script>
  <!-- End Google Tag Manager -->
'''

GTM_BODY_NOSCRIPT = '''  <!-- Google Tag Manager (noscript) -->
  <noscript><iframe src="https://www.googletagmanager.com/ns.html?id={{ gtm_id }}"
  height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
  <!-- End Google Tag Manager (noscript) -->

'''

def has_gtm(content):
    """Check if template already has GTM."""
    return '{{ gtm_id }}' in content and 'googletagmanager.com' in content

def add_gtm_to_template(template_path):
    """Add GTM to template if not present."""
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already has GTM
    if has_gtm(content):
        print(f"  ⏭️  GTM ya presente")
        return False
    
    # Skip AMP templates (they have different implementation)
    if '<html amp' in content or '<html ⚡' in content:
        print(f"  ⚙️  Template AMP - requiere implementación especial")
        return False
    
    modified = False
    
    # Add GTM script before </head>
    if '</head>' in content:
        content = content.replace('</head>', GTM_HEAD_SCRIPT + '</head>')
        modified = True
        print(f"  ✅ Script GTM agregado en <head>")
    else:
        print(f"  ⚠️  No se encontró etiqueta </head>")
    
    # Add noscript after <body>
    # Find opening body tag (could be <body> or <body class="...">)
    body_pattern = r'(<body[^>]*>)'
    if re.search(body_pattern, content):
        content = re.sub(body_pattern, r'\1\n' + GTM_BODY_NOSCRIPT, content, count=1)
        modified = True
        print(f"  ✅ Noscript GTM agregado después de <body>")
    else:
        print(f"  ⚠️  No se encontró etiqueta <body>")
    
    if modified:
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return modified

def main():
    print("📊 Agregando Google Tag Manager a templates")
    print("=" * 80)
    
    templates = list(TEMPLATES_DIR.glob('*.html'))
    
    print(f"📁 Procesando {len(templates)} templates\n")
    
    updated = 0
    skipped = 0
    
    for template in sorted(templates):
        print(f"📄 {template.name}")
        try:
            if add_gtm_to_template(template):
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
        print("🎉 ¡GTM agregado exitosamente!")
        print("\n📋 Próximos pasos:")
        print("  1. Ejecutar: python3 validate_gtm_templates.py")
        print("  2. Verificar que todos los templates pasen la validación")
        print("  3. git add templates/landing/*.html")
        print("  4. git commit -m 'feat: Agregar GTM a templates faltantes'")
        print("  5. git push origin main")
    else:
        print("ℹ️  Todos los templates ya tienen GTM implementado")

if __name__ == "__main__":
    main()
