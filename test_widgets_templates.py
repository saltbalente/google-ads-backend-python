#!/usr/bin/env python3
"""
🧪 TEST COMPLETO DE WIDGETS CON TEMPLATES REALES
==================================================
Prueba el sistema de inyección de widgets con:
1. Templates predefinidas (mystical, prosperity, romantic, etc.)
2. Templates customizadas del usuario
3. Dynamic AI template
4. Todos los widgets habilitados
5. Premium popups
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from widgets_injector import inject_widgets, WidgetConfig
from premium_popups_injector import inject_premium_popups


def load_template(template_name):
    """Carga una template desde el directorio templates/landing"""
    template_path = Path(__file__).parent / 'templates' / 'landing' / template_name
    if not template_path.exists():
        print(f"❌ Template no encontrada: {template_path}")
        return None
    
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def test_template_with_widgets(template_name, test_name):
    """Prueba una template con widgets y premium popups"""
    print(f"\n{'='*70}")
    print(f"🧪 TEST: {test_name}")
    print(f"   Template: {template_name}")
    print(f"{'='*70}")
    
    # Load template
    html = load_template(template_name)
    if not html:
        print(f"⚠️  Template {template_name} no encontrada, saltando...")
        return False
    
    print(f"✅ Template cargada: {len(html):,} bytes")
    
    # Widget configuration - ALL WIDGETS ENABLED
    widget_config = {
        'whatsapp_number': '+573001234567',
        'phone_number': '+573001234567',
        'primary_color': '#8B5CF6',
        'secondary_color': '#6B46C1',
        
        # Enable ALL widgets
        'show_sticky_bars': True,
        'show_vibrating_button': True,
        'show_scroll_popup': True,
        'show_live_consultations': True,
        'show_live_questions': True,
        'show_hypnotic_texts': True,
        'show_typing_effect': True,
        
        # Styles
        'sticky_bars_style': 'whatsapp',
        'vibrating_button_style': 'circular',
        'scroll_popup_style': 'centered',
        'live_consultations_style': 'floating',
        'live_questions_style': 'accordion',
        'hypnotic_texts_style': 'cards',
        'typing_effect_style': 'bubble',
    }
    
    # Inject widgets
    print("\n🔌 Inyectando widgets...")
    html_with_widgets = inject_widgets(html, widget_config)
    
    # Check widgets
    widget_checks = {
        'wa-sticky-bar': 'Sticky Bar',
        'vibrating-wa-btn': 'Vibrating Button',
        'scroll-popup': 'Scroll Popup',
        'live-notification': 'Live Consultations',
        'live-questions-section': 'Live Questions',
        'hypnotic-section': 'Hypnotic Texts',
        'typing-indicator': 'Typing Effect',
        'widgets-injected-css': 'CSS Styles',
        'widgets-injected-js': 'JavaScript',
    }
    
    injected_count = 0
    for widget_id, widget_name in widget_checks.items():
        if widget_id in html_with_widgets:
            print(f"   ✅ {widget_name}: INYECTADO")
            injected_count += 1
        else:
            print(f"   ❌ {widget_name}: FALTA")
    
    print(f"\n📊 Widgets inyectados: {injected_count}/{len(widget_checks)}")
    
    # Inject premium popups
    print("\n🎯 Inyectando premium popups...")
    popup_ids = ['urgency_timer', 'social_proof', 'floating_cta']
    popup_config = {
        'whatsapp_number': '+573001234567',
        'primary_color': '#8B5CF6',
        'secondary_color': '#6B46C1',
    }
    
    html_final = inject_premium_popups(html_with_widgets, popup_ids, popup_config)
    
    # Check popups
    popup_checks = {
        'premium-popup-urgency-timer': 'Urgency Timer',
        'premium-popup-social-proof': 'Social Proof',
        'premium-popup-floating-cta': 'Floating CTA',
        'premium-popups-css': 'Popup CSS',
        'premium-popups-js': 'Popup JS',
    }
    
    popup_count = 0
    for popup_id, popup_name in popup_checks.items():
        if popup_id in html_final:
            print(f"   ✅ {popup_name}: INYECTADO")
            popup_count += 1
        else:
            print(f"   ❌ {popup_name}: FALTA")
    
    print(f"\n📊 Popups inyectados: {popup_count}/{len(popup_checks)}")
    
    # Size comparison
    print(f"\n📏 Tamaños:")
    print(f"   Original:       {len(html):,} bytes")
    print(f"   Con widgets:    {len(html_with_widgets):,} bytes (+{len(html_with_widgets)-len(html):,})")
    print(f"   Con popups:     {len(html_final):,} bytes (+{len(html_final)-len(html):,})")
    
    # Save output for inspection
    output_dir = Path(__file__).parent / 'test_output_templates'
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"test_{template_name.replace('.html', '')}_with_widgets.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_final)
    
    print(f"\n💾 Guardado en: {output_file}")
    
    # Overall result
    success = injected_count >= 7 and popup_count >= 3
    if success:
        print(f"\n✅ TEST PASSED: {test_name}")
    else:
        print(f"\n❌ TEST FAILED: {test_name}")
    
    return success


def test_custom_template():
    """Test con template customizada (HTML básico)"""
    print(f"\n{'='*70}")
    print(f"🧪 TEST: Template Customizada")
    print(f"{'='*70}")
    
    custom_html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mi Landing Personalizada</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        .hero {
            text-align: center;
            padding: 60px 20px;
        }
        h1 {
            font-size: 48px;
            margin-bottom: 20px;
        }
        .cta-button {
            display: inline-block;
            padding: 15px 40px;
            background: white;
            color: #667eea;
            border-radius: 50px;
            text-decoration: none;
            font-weight: bold;
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <h1>🔮 Transforma Tu Vida Hoy</h1>
            <p>Consulta con nuestros expertos y descubre tu destino</p>
            <a href="https://wa.me/573001234567" class="cta-button">Consultar Ahora</a>
        </div>
        
        <div class="features">
            <h2>¿Por qué elegirnos?</h2>
            <ul>
                <li>✨ Expertos con más de 10 años de experiencia</li>
                <li>🔒 100% Confidencial</li>
                <li>⚡ Respuesta inmediata</li>
                <li>💰 Primera consulta GRATIS</li>
            </ul>
        </div>
        
        <div class="testimonials">
            <h2>Lo que dicen nuestros clientes</h2>
            <blockquote>
                "Increíble experiencia, cambió mi vida completamente"
                <footer>- María G.</footer>
            </blockquote>
        </div>
    </div>
</body>
</html>"""
    
    print(f"✅ Template customizada creada: {len(custom_html):,} bytes")
    
    # Inject widgets
    widget_config = {
        'whatsapp_number': '+573001234567',
        'show_sticky_bars': True,
        'show_vibrating_button': True,
        'show_scroll_popup': True,
        'show_live_consultations': True,
        'show_live_questions': True,
        'show_hypnotic_texts': True,
        'show_typing_effect': True,
    }
    
    print("\n🔌 Inyectando widgets en template customizada...")
    html_with_widgets = inject_widgets(custom_html, widget_config)
    
    # Check
    checks = ['wa-sticky-bar', 'vibrating-wa-btn', 'scroll-popup', 'widgets-injected-css']
    success = all(check in html_with_widgets for check in checks)
    
    for check in checks:
        status = "✅" if check in html_with_widgets else "❌"
        print(f"   {status} {check}")
    
    # Inject popups
    print("\n🎯 Inyectando premium popups...")
    html_final = inject_premium_popups(
        html_with_widgets, 
        ['exit_intent', 'wheel_fortune'], 
        {'whatsapp_number': '+573001234567'}
    )
    
    popup_checks = ['premium-popup-exit-intent', 'premium-popup-wheel-fortune']
    for check in popup_checks:
        status = "✅" if check in html_final else "❌"
        print(f"   {status} {check}")
    
    # Save
    output_dir = Path(__file__).parent / 'test_output_templates'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "test_custom_template_with_widgets.html"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_final)
    
    print(f"\n💾 Guardado en: {output_file}")
    print(f"\n📏 Tamaño final: {len(html_final):,} bytes")
    
    if success:
        print(f"\n✅ TEST PASSED: Template Customizada")
    else:
        print(f"\n❌ TEST FAILED: Template Customizada")
    
    return success


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 TESTING WIDGETS & POPUPS WITH REAL TEMPLATES")
    print("="*70)
    
    templates_to_test = [
        ('dynamic_ai.html', 'Dynamic AI Template'),
        ('mystical.html', 'Mystical Template'),
        ('prosperity.html', 'Prosperity Template'),
        ('romantic.html', 'Romantic Template'),
        ('base.html', 'Base Template'),
    ]
    
    results = []
    
    # Test predefined templates
    for template_file, test_name in templates_to_test:
        try:
            result = test_template_with_widgets(template_file, test_name)
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ ERROR en {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Test custom template
    try:
        result = test_custom_template()
        results.append(('Custom Template', result))
    except Exception as e:
        print(f"\n❌ ERROR en Custom Template: {e}")
        import traceback
        traceback.print_exc()
        results.append(('Custom Template', False))
    
    # Summary
    print("\n" + "="*70)
    print("📊 RESUMEN DE TESTS")
    print("="*70)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n📈 Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 TODOS LOS TESTS PASARON!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests fallaron")
        return 1


if __name__ == '__main__':
    sys.exit(main())
