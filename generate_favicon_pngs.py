#!/usr/bin/env python3
"""
Script para generar versiones PNG del favicon SVG.
Usa PIL/Pillow para convertir SVG a PNG en diferentes tamaños.
"""

try:
    from PIL import Image
    from cairosvg import svg2png
    import os
    
    SVG_PATH = 'static/favicon.svg'
    
    # Leer SVG
    with open(SVG_PATH, 'rb') as f:
        svg_data = f.read()
    
    # Generar PNG de 32x32
    png_32 = svg2png(bytestring=svg_data, output_width=32, output_height=32)
    with open('static/favicon-32x32.png', 'wb') as f:
        f.write(png_32)
    print("✅ Generado favicon-32x32.png")
    
    # Generar PNG de 180x180 (Apple Touch Icon)
    png_180 = svg2png(bytestring=svg_data, output_width=180, output_height=180)
    with open('static/apple-touch-icon.png', 'wb') as f:
        f.write(png_180)
    print("✅ Generado apple-touch-icon.png")
    
    print("\n🎉 Favicons PNG generados exitosamente!")
    
except ImportError:
    print("⚠️  CairoSVG no está instalado.")
    print("Para generar PNGs automáticamente, instala: pip install cairosvg")
    print("\nPor ahora, el favicon SVG funcionará en todos los navegadores modernos.")
    print("Los archivos PNG son opcionales para compatibilidad con navegadores antiguos.")

if __name__ == "__main__":
    pass
