#!/usr/bin/env python3
"""
Script de prueba para demostrar GitHub Pages automático
"""
import os
import sys
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables de entorno cargadas desde .env")
except ImportError:
    print("⚠️  dotenv no disponible, usando variables del sistema")

# Configurar variables necesarias para la prueba
os.environ.setdefault("GITHUB_REPO_NAME", "monorepo-landings")
os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")

from landing_generator import LandingPageGenerator

def test_github_pages_integration():
    """Prueba la integración completa con GitHub Pages"""

    print("\n🚀 PRUEBA DE INTEGRACIÓN CON GITHUB PAGES")
    print("=" * 60)

    # Datos de prueba
    test_data = {
        "customer_id": "5852810891",
        "ad_group_id": "175024723431",
        "whatsapp_number": "+52551234567",
        "gtm_id": "GTM-XXXXXXX",
        "phone_number": "+52551234567"
    }

    print(f"📊 Datos de prueba:")
    for key, value in test_data.items():
        print(f"   {key}: {value}")
    print()

    try:
        # Crear el generador
        print("🏗️  Creando generador...")
        generator = LandingPageGenerator()
        print("✅ Generador creado exitosamente")

        # Simular la extracción de contexto (esto normalmente vendría de Google Ads)
        print("\n📋 Paso 1: Simulando extracción de contexto...")

        # Crear contexto simulado
        from landing_generator import AdGroupContext, GeneratedContent

        context = AdGroupContext(
            keywords=["tarot gratis", "lectura tarot", "tarot online", "tarot amor"],
            headlines=["Lectura Tarot Gratis", "Tarot Online Preciso", "Descubre tu Futuro"],
            descriptions=["Consulta con tarotistas profesionales", "Lecturas personalizadas"],
            locations=["México", "Ciudad de México", "Guadalajara"],
            primary_keyword="tarot gratis"
        )

        print(f"   ✅ Contexto extraído: {len(context.keywords)} keywords, {len(context.headlines)} headlines")

        # Paso 2: Generar contenido con IA
        print("\n🤖 Paso 2: Generando contenido con IA...")
        content = GeneratedContent(
            headline_h1="Descubre tu Futuro con Tarot Gratis",
            subheadline="Lecturas precisas y personalizadas por expertos tarotistas",
            cta_text="Obtener Lectura Gratis",
            social_proof=[
                "⭐⭐⭐⭐⭐ Más de 10,000 lecturas realizadas",
                "✅ 98% de satisfacción de clientes",
                "🏆 Tarotistas certificados"
            ],
            benefits=[
                "Lectura completamente gratis",
                "Sin registro requerido",
                "Resultados inmediatos",
                "Expertos en tarot desde 1995"
            ],
            seo_title="Tarot Gratis Online - Lectura Precisa y Personalizada",
            seo_description="Obtén una lectura de tarot completamente gratis. Consultas personalizadas con tarotistas profesionales. Descubre tu futuro hoy mismo."
        )

        print("   ✅ Contenido generado exitosamente")

        # Paso 3: Renderizar HTML
        print("\n🎨 Paso 3: Renderizando HTML...")
        config = {
            "whatsapp_number": test_data["whatsapp_number"],
            "phone_number": test_data["phone_number"],
            "gtm_id": test_data["gtm_id"],
            "webhook_url": None,
            "primary_keyword": context.primary_keyword
        }

        html_content = generator.render(content, config)
        print(f"   ✅ HTML renderizado: {len(html_content)} caracteres")

        # Paso 4: Publicar a GitHub Pages
        print("\n📄 Paso 4: Publicando a GitHub Pages...")
        result = generator.publish_as_github_pages(test_data["ad_group_id"], html_content)

        print("   ✅ Publicación exitosa!")
        print(f"   🌐 URL Final: {result['url']}")
        print(f"   🔗 Alias: {result['alias']}")
        print(f"   📝 Commit: {result['commit_sha']}")
        print(f"   📁 Ruta: {result['path']}")
        print(f"   📊 Tamaño: {result['size']} bytes")

        # Información importante sobre GitHub Pages
        print("\nℹ️  INFORMACIÓN IMPORTANTE SOBRE GITHUB PAGES:")
        print("   • La URL puede tardar hasta 10 minutos en estar disponible")
        print("   • GitHub Pages se activa automáticamente en el primer push")
        print("   • No requiere configuración manual de proyectos")
        print("   • Es completamente gratuito e ilimitado")
        print(f"   • URL patrón: https://{{usuario}}.github.io/{{repo}}/{{carpeta}}/")

        print("\n✅ Prueba completada exitosamente!")
        print(f"📍 Landing page publicada en: {result['url']}")

        return result

    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_github_pages_integration()