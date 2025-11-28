#!/usr/bin/env python3
"""
Ejemplo de cómo se generan URLs con subdominios personalizados
"""
import os

def demo_subdomain_urls():
    """Muestra ejemplos de URLs con subdominios"""

    # Configuración de ejemplo
    custom_domain = os.getenv("GITHUB_PAGES_CUSTOM_DOMAIN", "landing-pages.miexperto.com")

    print("🚀 DEMO: URLs con Subdominios Personalizados")
    print("=" * 60)
    print(f"Dominio base: {custom_domain}")
    print()

    # Ejemplos de keywords que se convierten en subdominios
    examples = [
        ("tarot gratis", "tarot-gratis"),
        ("lectura tarot online", "lectura-tarot-online"),
        ("tarot amor verdadero", "tarot-amor-verdadero"),
        ("consulta tarot economico", "consulta-tarot-economico"),
        ("tarot futuro laboral", "tarot-futuro-laboral"),
        ("lectura baraja espanola", "lectura-baraja-espanola"),
        ("tarot si o no gratis", "tarot-si-o-no-gratis"),
        ("prediccion tarot semanal", "prediccion-tarot-semanal")
    ]

    print("📄 Keywords -> Subdominios:")
    print("-" * 40)

    for original, slug in examples:
        subdomain_url = f"https://{slug}.{custom_domain}/"
        print(f"   {original:25} -> {subdomain_url}")

    print()
    print("🎯 VENTAJAS:")
    print("   ✅ URLs cortas y memorables")
    print("   ✅ Mejor para SEO")
    print("   ✅ Apariencia profesional")
    print("   ✅ Cada landing page tiene su propio subdominio")
    print("   ✅ Fácil compartir en redes sociales")

    print()
    print("⚙️  CONFIGURACIÓN NECESARIA:")
    print(f"   Variable: GITHUB_PAGES_CUSTOM_DOMAIN={custom_domain}")
    print(f"   DNS: *.{custom_domain} -> saltbalente.github.io")
    print("   Script: python3 setup_custom_domain.py")

if __name__ == "__main__":
    demo_subdomain_urls()