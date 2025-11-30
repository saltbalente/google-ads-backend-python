#!/usr/bin/env python3
"""
Script para probar el solucionador de accesibilidad
"""

from web_cloner import ContentProcessor
import os

def test_accessibility_solver():
    # Leer el archivo HTML de prueba
    with open('test_accessibility/index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    print('=== HTML ORIGINAL ===')
    print('Problemas de accesibilidad en el HTML original:')
    print('- Texto blanco sobre fondo blanco')
    print('- Texto negro sobre fondo negro')
    print('- Texto con opacidad baja')
    print('- Texto transparente sobre fondo transparente')
    print()

    # Procesar con el solucionador de accesibilidad
    processor = ContentProcessor()
    processed_html, resources = processor.process_html(html_content, 'file://test_accessibility/index.html')

    print('=== HTML PROCESADO ===')
    print('Verificando correcciones aplicadas...')

    # Verificar que se aplicaron las correcciones
    important_marker = '!important'
    if 'color: #333 ' + important_marker in processed_html:
        print('✅ Corrección aplicada: Color de texto forzado a #333')
    else:
        print('❌ No se aplicó corrección de color de texto')

    if 'background-color: #fff ' + important_marker in processed_html:
        print('✅ Corrección aplicada: Color de fondo forzado a #fff')
    else:
        print('❌ No se aplicó corrección de color de fondo')

    if 'opacity: 1 ' + important_marker in processed_html:
        print('✅ Corrección aplicada: Opacidad forzada a 1')
    else:
        print('❌ No se aplicó corrección de opacidad')

    # Contar elementos corregidos
    contrast_fixes = processed_html.count('color: #333 ' + important_marker)
    print(f'✅ Total de elementos con corrección de contraste: {contrast_fixes}')

    # Guardar el HTML procesado para inspección
    with open('test_accessibility/processed.html', 'w', encoding='utf-8') as f:
        f.write(processed_html)

    print()
    print('=== RESULTADO ===')
    print('El solucionador de accesibilidad ha procesado el HTML.')
    print('Archivo procesado guardado en: test_accessibility/processed.html')

if __name__ == '__main__':
    test_accessibility_solver()