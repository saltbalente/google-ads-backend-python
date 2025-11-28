#!/usr/bin/env python3
"""
Script de prueba para el template José AMP
Verifica que el template se renderiza correctamente con datos dinámicos
"""

import json
import os
from jinja2 import Environment, FileSystemLoader

def test_jose_amp_template():
    """Prueba el template José AMP con datos de ejemplo"""

    # Configurar Jinja2
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates', 'landing')
    env = Environment(loader=FileSystemLoader(templates_dir))

    # Cargar configuración del template
    config_file = os.path.join(templates_dir, 'jose-amp-config.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Datos de ejemplo para testing
    test_data = {
        # SEO y sitio
        "seo_title": "Amarres de Amor - José | Especialista en Rituales de Amor Efectivos",
        "seo_description": "Servicio profesional de amarres de amor con José. Rituales efectivos, discretos y garantizados. Resultados reales en Colombia.",
        "canonical_url": "https://tu-dominio.com/landing/jose-amp",
        "meta_keywords": "amarres de amor, rituales de amor, brujeria, hechizos de amor, Jose",

        # Contacto
        "phone_number": "+573001234567",
        "display_phone": "+57 300 123 4567",
        "whatsapp_number": "573001234567",
        "whatsapp_message": "Hola José, necesito ayuda con amarres de amor",
        "site_name": "José - Maestro Espiritual",
        "header_tagline": "Especialista en Amarres de Amor",

        # Experto
        "expert_name": "José",
        "expert_title": "Maestro Espiritual",
        "expert_description": "José es un especialista reconocido en amarres de amor con más de 15 años de experiencia ayudando a personas en Colombia y alrededores.",
        "experience_years": "15",

        # Contenido dinámico
        "main_keyword": "amarres de amor",
        "service_type": "amarres de amor",
        "location": "Colombia",
        "secondary_keywords": ["rituales espirituales", "limpias energéticas", "hechizos de amor", "consultas espirituales"],

        "main_description": "Descubre el poder de los amarres de amor con José, especialista reconocido en rituales de amor. Más de 15 años de experiencia ayudando a parejas a reconectar con el amor verdadero. Resultados garantizados o te devolvemos tu dinero.",

        "success_message": "¡Miles de parejas felices gracias a nuestros amarres de amor!",

        "whatsapp_cta": "¡Contactar por WhatsApp Ahora!",
        "main_cta": "SOLICITAR AMARRES DE AMOR AHORA",

        "free_consultation_text": "CONSULTA GRATUITA - Sin compromiso",

        "services_description": "Nuestros amarres de amor incluyen rituales ancestrales, limpias energéticas, hechizos personalizados y consultas espirituales. Cada servicio está diseñado específicamente para tu situación particular.",

        "comprehensive_services": "SERVICIOS INTEGRALES DE AMARRES DE AMOR - RESULTADOS GARANTIZADOS",

        "services_info": "Como especialista en amarres de amor, José combina técnicas tradicionales con conocimientos modernos para ofrecerte soluciones efectivas y duraderas.",

        "services_benefits": "Beneficios de nuestros servicios: Resultados rápidos, discreción total, seguimiento personalizado, garantía de satisfacción.",

        "expertise_description": "José ha ayudado a más de 5000 personas a recuperar el amor perdido, solucionar problemas de pareja y encontrar la felicidad que merecen.",

        "guarantee_title": "¡GARANTÍA TOTAL DE RESULTADOS!",
        "guarantee_description": "Si no obtienes los resultados prometidos en amarres de amor, te devolvemos el 100% de tu dinero. ¡Sin preguntas, sin excusas!",

        "banner_title": "¡No esperes más!",
        "banner_description": "Contacta ahora mismo con José y comienza tu camino hacia el amor verdadero. Consulta gratuita y confidencial.",
        "banner_cta": "INICIAR CONSULTA GRATUITA",

        "chat_button_text": "Chatear con José",
        "whatsapp_button_text": "Contactar por WhatsApp",
        "call_button_text": "Llamar Ahora",

        "online_status": "En línea",

        "footer_text": "© 2024 José - Maestro Espiritual. Todos los derechos reservados. Servicio confidencial y discreto.",

        # Keywords
        "keywords_cloud": [
            "amarres de amor", "rituales de amor", "hechizos efectivos", "consultas espirituales",
            "limpias energéticas", "problemas de pareja", "amor perdido", "reconquista amorosa",
            "unión de parejas", "rituales ancestrales", "magia blanca", "especialista espiritual",
            "Colombia", "servicio discreto", "resultados garantizados"
        ],

        "keyword_definitions": [
            {
                "term": "Amarres de amor",
                "definition": "Rituales espirituales diseñados para reconectar parejas y fortalecer vínculos amorosos mediante técnicas ancestrales y energías positivas."
            },
            {
                "term": "Rituales ancestrales",
                "definition": "Ceremonias tradicionales transmitidas por generaciones, combinadas con conocimientos modernos para resultados efectivos."
            },
            {
                "term": "Limpias energéticas",
                "definition": "Proceso de purificación espiritual que elimina energías negativas y bloqueos que impiden el flujo natural del amor."
            },
            {
                "term": "Consultas espirituales",
                "definition": "Sesiones personalizadas donde se analiza tu situación amorosa y se diseña un plan espiritual específico para tu caso."
            },
            {
                "term": "Magia blanca",
                "definition": "Prácticas espirituales positivas que buscan el bien mayor, utilizando energías constructivas y respetando el libre albedrío."
            }
        ],

        # Analytics
        "gtm_id": "GTM-XXXXXXX",
        "statcounter_project": "12345678",
        "statcounter_security": "abcdef12",

        # Media (URLs reales para contenido de brujería/esoterismo)
        "main_video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
        "video_poster": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1280&h=720&fit=crop",
        "services_video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_2mb.mp4",
        "services_video_2": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_5mb.mp4",
        "testimonial_video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_10mb.mp4",

        "main_image": "https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=1080&h=1920&fit=crop",
        "main_image_alt": "Especialista José en amarres de amor",

        "expert_image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&h=800&fit=crop",
        "expert_image_alt": "Foto de José",

        "expert_portrait": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=600&h=800&fit=crop",
        "portrait_alt": "Retrato profesional de José",

        "chat_icon": "https://img.icons8.com/color/96/whatsapp.png",
        "whatsapp_logo": "https://img.icons8.com/color/96/whatsapp.png",
        "whatsapp_icon": "https://img.icons8.com/color/96/whatsapp.png",
        "call_icon": "https://img.icons8.com/color/96/phone.png",

        "gallery_images": [
            {
                "src": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=600&fit=crop",
                "alt": "Ritual de amarres de amor"
            },
            {
                "src": "https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=400&h=600&fit=crop",
                "alt": "Ceremonia espiritual"
            },
            {
                "src": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=600&fit=crop",
                "alt": "Hierbas y elementos naturales"
            },
            {
                "src": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=400&h=600&fit=crop",
                "alt": "Cristales y piedras sagradas"
            },
            {
                "src": "https://images.unsplash.com/photo-1465146344425-f00d5f5c8f07?w=400&h=600&fit=crop",
                "alt": "Velas y elementos rituales"
            },
            {
                "src": "https://images.unsplash.com/photo-1507699622140-4e6bf2cce243?w=400&h=600&fit=crop",
                "alt": "Altar espiritual"
            }
        ],

        # Testimonios
        "testimonials": [
            {
                "text": "Gracias a José, mi relación se salvó. Los amarres de amor funcionaron más allá de mis expectativas. ¡Increíble!",
                "date": "Hace 2 semanas - Colombia",
                "name": "María González",
                "city": "Bogotá",
                "image": "https://images.unsplash.com/photo-1494790108755-2616b612b786?w=60&h=60&fit=crop&crop=face"
            },
            {
                "text": "Después de 6 meses separados, mi esposo regresó gracias a los rituales de José. Servicio profesional y discreto.",
                "date": "Hace 1 mes - Colombia",
                "name": "Ana Rodríguez",
                "city": "Medellín",
                "image": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=60&h=60&fit=crop&crop=face"
            },
            {
                "text": "Los amarres de amor de José son realmente efectivos. Mi pareja cambió completamente su actitud. ¡Recomendado!",
                "date": "Hace 3 semanas - Colombia",
                "name": "Carlos Mendoza",
                "city": "Cali",
                "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=60&h=60&fit=crop&crop=face"
            }
        ],

        # User images (para testing de integración con iOS app)
        "user_images": [
            "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=1080&h=1920&fit=crop",  # main_image override
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600&h=800&fit=crop",  # expert_image override
            "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=400&h=600&fit=crop",  # gallery image 1
            "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=600&fit=crop",  # gallery image 2
            "https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=400&h=600&fit=crop"   # gallery image 3
        ],

        # User image overrides for video
        "user_image_main_video": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_2mb.mp4",
        "user_image_video_poster": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=1280&h=720&fit=crop"
    }

    try:
        # Cargar y renderizar template
        template = env.get_template('jose-amp.html')
        rendered_html = template.render(**test_data)

        # Verificar que el renderizado fue exitoso
        assert 'José' in rendered_html, "Nombre del experto no encontrado en el HTML renderizado"
        assert 'Amarres de Amor' in rendered_html, "Servicio principal no encontrado"
        assert 'whatsapp' in rendered_html.lower(), "WhatsApp no encontrado en el HTML"
        assert '<!DOCTYPE html>' in rendered_html, "DOCTYPE no encontrado"
        assert 'amp-video' in rendered_html, "Componentes AMP no encontrados"

        # Guardar resultado para inspección
        output_file = os.path.join(os.path.dirname(__file__), 'test_jose_amp_output.html')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        print("✅ Template José AMP renderizado correctamente")
        print(f"📄 Archivo de salida guardado: {output_file}")
        print(f"📊 Tamaño del HTML generado: {len(rendered_html)} caracteres")

        # Verificar elementos clave
        checks = [
            ('Título SEO', 'Amarres de Amor - José' in rendered_html),
            ('Descripción SEO', 'Servicio profesional de amarres de amor' in rendered_html),
            ('Teléfono', '+57 300 123 4567' in rendered_html),
            ('Testimonios', 'María González' in rendered_html),
            ('Galería', 'images.unsplash.com' in rendered_html),
            ('Videos', 'sample-videos.com' in rendered_html),
            ('AMP válido', 'amp-video' in rendered_html)
        ]

        print("\n🔍 Verificación de elementos:")
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")

        all_checks_pass = all(result for _, result in checks)
        if all_checks_pass:
            print("\n🎉 ¡Todas las verificaciones pasaron exitosamente!")
        else:
            print("\n⚠️  Algunas verificaciones fallaron")

        return True

    except Exception as e:
        print(f"❌ Error al renderizar template: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Probando template José AMP...")
    success = test_jose_amp_template()
    exit(0 if success else 1)