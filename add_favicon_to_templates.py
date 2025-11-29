#!/usr/bin/env python3
"""
Script para agregar favicon a todos los templates de landing pages.
Busca la etiqueta <title> y agrega las líneas de favicon después.
"""

import os
import re
from pathlib import Path

# Favicon lines to insert
FAVICON_LINES = '''
  <!-- Favicon -->
  <link rel="icon" type="image/svg+xml" href="https://cdn.jsdelivr.net/gh/saltbalente/monorepo-landings@main/static/favicon.svg">
  <link rel="icon" type="image/png" sizes="32x32" href="https://cdn.jsdelivr.net/gh/saltbalente/monorepo-landings@main/static/favicon-32x32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="https://cdn.jsdelivr.net/gh/saltbalente/monorepo-landings@main/static/apple-touch-icon.png">
'''

# Templates directory
TEMPLATES_DIR = Path(__file__).parent / 'templates' / 'landing'

def add_favicon_to_template(template_path):
    """Add favicon lines after <title> tag if not already present."""
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if favicon already exists
    if 'favicon' in content.lower():
        print(f"  ⏭️  Favicon already present in {template_path.name}")
        return False
    
    # For AMP templates (jose-amp.html), skip as they have different structure
    if 'amp' in template_path.name.lower() or '<html amp' in content or '<html ⚡' in content:
        print(f"  ⚙️  AMP template detected, adding AMP-compatible favicon to {template_path.name}")
        # For AMP, add after <meta name="viewport"
        amp_favicon = '''
  <!-- Favicon (AMP Compatible) -->
  <link rel="icon" href="https://cdn.jsdelivr.net/gh/saltbalente/monorepo-landings@main/static/favicon.svg">
'''
        # Find viewport meta tag and insert after it
        pattern = r'(<meta name="viewport"[^>]*>)'
        if re.search(pattern, content):
            content = re.sub(pattern, r'\1' + amp_favicon, content, count=1)
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        else:
            print(f"  ⚠️  Could not find viewport meta tag in {template_path.name}")
            return False
    
    # For regular HTML templates, add after <title> tag
    # Match <title>...</title> with optional whitespace
    pattern = r'(<title>.*?</title>)'
    
    if re.search(pattern, content, re.DOTALL):
        # Insert favicon lines after title
        content = re.sub(pattern, r'\1' + FAVICON_LINES, content, count=1, flags=re.DOTALL)
        
        # Write back
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    else:
        print(f"  ⚠️  Could not find <title> tag in {template_path.name}")
        return False

def main():
    print("🎨 Agregando favicon a todos los templates...")
    print("=" * 80)
    
    # Get all HTML templates
    templates = list(TEMPLATES_DIR.glob('*.html'))
    
    print(f"📁 Encontrados {len(templates)} templates\n")
    
    updated = 0
    skipped = 0
    errors = 0
    
    for template in sorted(templates):
        print(f"📄 Procesando {template.name}...")
        try:
            if add_favicon_to_template(template):
                print(f"  ✅ Favicon agregado exitosamente")
                updated += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            errors += 1
        print()
    
    print("=" * 80)
    print("📊 RESUMEN:")
    print(f"  ✅ Actualizados: {updated}")
    print(f"  ⏭️  Omitidos: {skipped}")
    print(f"  ❌ Errores: {errors}")
    print(f"  📝 Total: {len(templates)}")
    print()
    
    if updated > 0:
        print("🎉 ¡Favicon agregado exitosamente a los templates!")
        print("\n📋 Próximos pasos:")
        print("  1. git add templates/landing/*.html static/favicon.svg")
        print("  2. git commit -m 'feat: Agregar favicon a todos los templates'")
        print("  3. git push origin main")
    else:
        print("ℹ️  No se realizaron cambios (favicon ya presente en todos los templates)")

if __name__ == "__main__":
    main()
