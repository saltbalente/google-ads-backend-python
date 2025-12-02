#!/usr/bin/env python3
"""Test del sistema de widgets ultra-robusto"""

from widgets_injector import inject_widgets, WidgetsInjector, WidgetConfig

def test_bad_html():
    """Test con HTML mal formado"""
    bad_html = '<html><div>Contenido</div>'
    config = {
        'whatsapp_number': '+573001234567',
        'show_sticky_bars': True,
        'show_vibrating_button': True,
    }
    
    result = inject_widgets(bad_html, config)
    print('Test 1: HTML mal formado')
    print(f'   Original: {len(bad_html)} bytes')
    print(f'   Resultado: {len(result)} bytes')
    print(f'   Contiene widgets: {"wa-sticky-bar" in result}')
    assert "wa-sticky-bar" in result
    print('   ✅ PASSED')
    print()

def test_good_html():
    """Test con HTML bien formado"""
    good_html = '<html><head><title>Test</title></head><body><div>Contenido</div></body></html>'
    config = {
        'whatsapp_number': '+573001234567',
        'show_sticky_bars': True,
        'show_vibrating_button': True,
    }
    
    result = inject_widgets(good_html, config)
    print('Test 2: HTML bien formado')
    print(f'   Original: {len(good_html)} bytes')
    print(f'   Resultado: {len(result)} bytes')
    print(f'   Contiene CSS: {"widgets-injected-css" in result}')
    print(f'   Contiene HTML: {"wa-sticky-bar" in result}')
    assert "widgets-injected-css" in result
    assert "wa-sticky-bar" in result
    print('   ✅ PASSED')
    print()

def test_all_widgets():
    """Test con todos los widgets activos"""
    html = '<html><head></head><body></body></html>'
    config = {
        'whatsapp_number': '+573001234567',
        'show_sticky_bars': True,
        'show_vibrating_button': True,
        'show_scroll_popup': True,
        'show_live_consultations': True,
        'show_live_questions': True,
        'show_hypnotic_texts': True,
        'show_typing_effect': True,
        'sticky_bars_style': 'mystical',
        'vibrating_button_style': 'heart',
    }
    
    result = inject_widgets(html, config)
    print('Test 3: Todos los widgets')
    print(f'   Resultado: {len(result)} bytes')
    
    widgets_found = []
    if 'wa-sticky-bar' in result:
        widgets_found.append('sticky_bars')
    if 'vibrating-wa-btn' in result:
        widgets_found.append('vibrating_button')
    if 'scroll-popup' in result:
        widgets_found.append('scroll_popup')
    if 'live-consults' in result:
        widgets_found.append('live_consultations')
    if 'live-question' in result:
        widgets_found.append('live_questions')
    if 'hypnotic' in result:
        widgets_found.append('hypnotic_texts')
    if 'typing-indicator' in result:
        widgets_found.append('typing_effect')
    
    print(f'   Widgets encontrados: {len(widgets_found)}/7')
    print(f'   {widgets_found}')
    assert len(widgets_found) == 7
    print('   ✅ PASSED')
    print()

def test_no_widgets():
    """Test sin widgets habilitados"""
    html = '<html><head></head><body></body></html>'
    config = {}
    
    result = inject_widgets(html, config)
    print('Test 4: Sin widgets')
    print(f'   Original === Resultado: {html == result}')
    assert html == result
    print('   ✅ PASSED')
    print()

def test_injector_methods():
    """Test de métodos de inyección"""
    injector = WidgetsInjector(WidgetConfig(
        show_sticky_bars=True,
        show_vibrating_button=True
    ))
    
    # Test method 1: Normal
    html1 = '<html><head></head><body></body></html>'
    result1 = injector.inject(html1)
    print(f'Test 5: Método de inyección')
    print(f'   Método usado: {injector.injection_method}')
    assert injector.injection_method == 'normal'
    print('   ✅ PASSED')
    print()

if __name__ == '__main__':
    print('=' * 50)
    print('🔌 WIDGET INJECTION TESTS')
    print('=' * 50)
    print()
    
    test_bad_html()
    test_good_html()
    test_all_widgets()
    test_no_widgets()
    test_injector_methods()
    
    print('=' * 50)
    print('✅ ALL TESTS PASSED')
    print('=' * 50)
