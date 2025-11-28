#!/usr/bin/env python3
"""
Script para configurar y verificar el dominio personalizado para landing pages
"""
import os
import sys

def setup_custom_domain():
    """Configura el dominio personalizado correcto"""

    print("🔧 Configuración de Dominio Personalizado")
    print("=" * 50)

    # Configuración correcta
    correct_domain = "consultadebrujosgratis.store"

    # Verificar variable actual
    current_domain = os.getenv("GITHUB_PAGES_CUSTOM_DOMAIN")

    print(f"Dominio actual: {current_domain or 'No configurado'}")
    print(f"Dominio correcto: {correct_domain}")
    print()

    if current_domain == correct_domain:
        print("✅ ¡Dominio ya configurado correctamente!")
    else:
        print("⚠️  Dominio no configurado o incorrecto")
        print("🔧 Configurando...")

        # Configurar variable
        os.environ["GITHUB_PAGES_CUSTOM_DOMAIN"] = correct_domain
        print(f"✅ Variable configurada: GITHUB_PAGES_CUSTOM_DOMAIN={correct_domain}")

    print()
    print("🎯 Formato de URLs:")
    print("   ✅ Sistema principal (rutas): https://consultadebrujosgratis.store/espiritista-gratis-831/")
    print("   ❌ Demo subdominios (solo ejemplo): espiritista-gratis-831.consultadebrujosgratis.store")
    print()

    # Verificar que el sistema funcione
    try:
        from landing_generator import LandingPageGenerator
        gen = LandingPageGenerator()

        if gen.custom_domain == correct_domain:
            print("✅ LandingPageGenerator configurado correctamente")
        else:
            print(f"⚠️  LandingPageGenerator tiene: {gen.custom_domain}")

    except Exception as e:
        print(f"❌ Error verificando configuración: {e}")

    print()
    print("📋 Para configuración permanente:")
    print("   Agrega esta línea a tu ~/.bashrc o ~/.zshrc:")
    print(f"   export GITHUB_PAGES_CUSTOM_DOMAIN={correct_domain}")
    print()
    print("   Luego ejecuta: source ~/.bashrc")

def test_url_generation():
    """Prueba la generación de URLs"""

    print("\n🧪 Prueba de Generación de URLs")
    print("=" * 30)

    # Simular configuración
    os.environ["GITHUB_PAGES_CUSTOM_DOMAIN"] = "consultadebrujosgratis.store"

    try:
        from landing_generator import LandingPageGenerator
        gen = LandingPageGenerator()

        # Simular una URL generada
        folder_name = "espiritista-gratis-831"

        if gen.custom_domain:
            url = f"https://{gen.custom_domain}/{folder_name}/"
            print(f"✅ URL generada: {url}")
        else:
            url = f"https://{gen.github_owner}.github.io/{gen.github_repo}/{folder_name}/"
            print(f"❌ URL por defecto: {url}")

    except Exception as e:
        print(f"❌ Error en prueba: {e}")

if __name__ == "__main__":
    setup_custom_domain()
    test_url_generation()

    print("\n🎉 ¡Configuración completada!")
    print("Ahora las landing pages usarán URLs del formato correcto.")