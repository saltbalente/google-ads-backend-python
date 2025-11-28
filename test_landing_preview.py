#!/usr/bin/env python3
"""
Script de prueba para mostrar qué archivos genera el Landing Page Generator
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

def test_landing_page_generation():
    """Prueba la generación de landing page y muestra el resultado"""

    print("\n🧪 PRUEBA DEL GENERADOR DE LANDING PAGES")
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
            "primary_keyword": "tarot gratis"  # Agregar keyword para probar selección de template
        }

        html_content = generator.render(content, config)
        print(f"   ✅ HTML renderizado: {len(html_content)} caracteres")

        # Guardar el archivo localmente para mostrarlo
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)

        html_file = output_dir / "landing-test.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"\n💾 Archivo guardado: {html_file.absolute()}")

        # Mostrar información del archivo
        print("\n📁 Archivos que se generarían:")
        print(f"   📄 landing-{test_data['ad_group_id']}/index.html ({len(html_content)} bytes)")

        # Mostrar preview del contenido
        print("\n🔍 Preview del contenido generado:")
        print("   Título H1:", content.headline_h1)
        print("   Subtítulo:", content.subheadline)
        print("   CTA:", content.cta_text)
        print(f"   Beneficios: {len(content.benefits)} items")
        print(f"   Social Proof: {len(content.social_proof)} items")

        print("\n✅ Prueba completada exitosamente!")
        print(f"📂 Revisa el archivo generado en: {html_file}")

        return html_file

    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_landing_page_generation()