#!/usr/bin/env python3
"""
Script de validación de Google Tag Manager en los templates.
Verifica que todos los templates tengan GTM correctamente implementado.
"""

import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / 'templates' / 'landing'

def validate_gtm_in_template(template_path):
    """Validate GTM implementation in a template."""
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    warnings = []
    
    # Check 1: GTM variable present
    if '{{ gtm_id }}' not in content:
        issues.append("❌ Variable {{ gtm_id }} no encontrada")
    
    # Check 2: GTM script in head (standard implementation)
    gtm_script_patterns = [
        r'googletagmanager\.com/gtm\.js\?id=',
        r'googletagmanager\.com/gtag/js\?id=',
        r'googletagmanager\.com/amp\.json\?id=',  # AMP
    ]
    
    has_gtm_script = any(re.search(pattern, content) for pattern in gtm_script_patterns)
    
    if not has_gtm_script:
        issues.append("❌ Script de GTM no encontrado en <head>")
    
    # Check 3: Noscript iframe (for standard GTM)
    if '<html amp' not in content and '<html ⚡' not in content:  # Not AMP
        if 'googletagmanager.com/ns.html?id=' not in content:
            warnings.append("⚠️  Noscript iframe de GTM no encontrado")
    
    # Check 4: GTM variable not hardcoded
    hardcoded_gtm = re.findall(r"GTM-[A-Z0-9]{7,}", content)
    if hardcoded_gtm:
        # Filter out template examples and placeholders
        real_hardcoded = [gtm for gtm in hardcoded_gtm if gtm not in ['GTM-XXXXXXX', 'GTM-TEST123']]
        if real_hardcoded:
            warnings.append(f"⚠️  GTM ID hardcodeado encontrado: {', '.join(set(real_hardcoded))}")
    
    return issues, warnings

def main():
    print("🔍 Validación de Google Tag Manager en Templates")
    print("=" * 80)
    
    templates = list(TEMPLATES_DIR.glob('*.html'))
    
    print(f"📁 Analizando {len(templates)} templates\n")
    
    total_issues = 0
    total_warnings = 0
    templates_ok = 0
    
    for template in sorted(templates):
        issues, warnings = validate_gtm_in_template(template)
        
        if not issues and not warnings:
            print(f"✅ {template.name}")
            templates_ok += 1
        else:
            print(f"📄 {template.name}")
            for issue in issues:
                print(f"  {issue}")
                total_issues += 1
            for warning in warnings:
                print(f"  {warning}")
                total_warnings += 1
            print()
    
    print("=" * 80)
    print("📊 RESUMEN:")
    print(f"  ✅ Templates correctos: {templates_ok}/{len(templates)}")
    print(f"  ❌ Issues críticos: {total_issues}")
    print(f"  ⚠️  Advertencias: {total_warnings}")
    print()
    
    if total_issues == 0 and total_warnings == 0:
        print("🎉 ¡Todos los templates tienen GTM correctamente implementado!")
    elif total_issues == 0:
        print("✅ No hay issues críticos, solo advertencias menores.")
    else:
        print("⚠️  Se encontraron issues que requieren atención.")
    
    print("\n📋 Verificaciones realizadas:")
    print("  1. Variable {{ gtm_id }} presente")
    print("  2. Script de GTM en <head>")
    print("  3. Noscript iframe para no-JS (templates estándar)")
    print("  4. No hay GTM IDs hardcodeados")

if __name__ == "__main__":
    main()
