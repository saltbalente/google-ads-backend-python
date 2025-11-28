#!/usr/bin/env python3
"""
Configuración específica para consultadebrujosgratis.store
"""
import os
import sys

def configure_consultadebrujos_domain():
    """Configura el dominio consultadebrujosgratis.store"""

    print("🔮 CONFIGURACIÓN PARA CONSULTADEBRUJOSGRATIS.STORE")
    print("=" * 60)

    # Configurar variable de entorno
    domain = "consultadebrujosgratis.store"
    os.environ["GITHUB_PAGES_CUSTOM_DOMAIN"] = domain

    print(f"✅ Dominio configurado: {domain}")
    print()

    # Mostrar ejemplos de URLs que se generarán
    examples = [
        ("lectura tarot gratis", "lectura-tarot-gratis"),
        ("consulta brujos online", "consulta-brujos-online"),
        ("tarot amor gratis", "tarot-amor-gratis"),
        ("prediccion futuro", "prediccion-futuro"),
        ("ritual amor poderoso", "ritual-amor-poderoso")
    ]

    print("🌐 URLs que se generarán automáticamente:")
    print("-" * 50)

    for original, slug in examples:
        subdomain_url = f"https://{slug}.{domain}/"
        print(f"   {original:25} -> {subdomain_url}")

    print()
    print("⚙️  PASOS PARA CONFIGURAR:")
    print("   1. Ve a tu proveedor de dominio (donde compraste .store)")
    print("   2. Configura DNS:")
    print("      Tipo: CNAME")
    print("      Nombre: * (wildcard)")
    print("      Valor: saltbalente.github.io")
    print("      TTL: 3600 (1 hora)")
    print()
    print("   3. En Render.com, agrega variable:")
    print(f"      GITHUB_PAGES_CUSTOM_DOMAIN={domain}")
    print()
    print("   4. Ejecuta configuración:")
    print("      python3 setup_custom_domain.py")
    print()
    print("⏱️  TIEMPOS:")
    print("   • Configuración inicial: 24-48 horas")
    print("   • Nuevos subdominios: ¡INSTANTÁNEOS!")
    print("   • Sin configuración adicional por landing page")

    print()
    print("🎉 ¡VENTAJAS DE TU DOMINIO!")
    print("   ✅ Profesional: consultadebrujosgratis.store")
    print("   ✅ Memorables: tarot-gratis.consultadebrujosgratis.store")
    print("   ✅ SEO: Autoridad de dominio propio")
    print("   ✅ Confianza: Apariencia profesional")

if __name__ == "__main__":
    configure_consultadebrujos_domain()