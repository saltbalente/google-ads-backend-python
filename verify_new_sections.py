import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Mock data for the new sections
mock_premium_services = [
    {"title": "Lectura de Tarot Premium", "description": "Lectura profunda de 1 hora.", "whatsapp_message": "Hola, quiero la lectura premium"},
    {"title": "Limpieza Energética", "description": "Limpieza total de aura.", "whatsapp_message": "Hola, quiero la limpieza"}
]

mock_testimonials = [
    {"text": "Me cambió la vida totalmente.", "name": "María G.", "location": "Madrid"},
    {"text": "Increíble precisión.", "name": "Juan P.", "location": "Bogotá"}
]

mock_blog_articles = [
    {"title": "Cómo atraer el amor", "content": "<p>Consejos para atraer el amor...</p>"},
    {"title": "Significado de los sueños", "content": "<p>Soñar con agua significa...</p>"}
]

mock_faqs = [
    {"question": "¿Es seguro?", "answer": "Sí, totalmente seguro y confidencial."},
    {"question": "¿Cuánto tarda?", "answer": "Los resultados se ven en pocos días."}
]

mock_conversion_booster = {
    "popup_offer": "🎁 30 minutos de consulta GRATIS + diagnóstico de tu energía",
    "popup_text": "Habla directamente conmigo por WhatsApp ahora mismo y solo pagas si decides continuar después. Sin compromiso, sin riesgo.",
    "banner_text": "¡OFERTA ESPECIAL! Consulta GRATIS por tiempo limitado",
    "side_banner_title": "¡REGALO EXCLUSIVO!",
    "side_banner_text": "Respuesta a UNA pregunta urgente por WhatsApp ahora mismo 100% GRATIS",
    "whatsapp_message": "Hola, quiero mis 30 minutos GRATIS",
    "spots_available": 7,
    "popup_delay": 15000
}

mock_hypnotic_texts = {
    "trust_title": "¿Por qué confiar en mí?",
    "trust_builder": "Imagina por un momento cómo sería tu vida si tuvieras las respuestas que buscas. Esa sensación de certeza, de saber exactamente qué hacer.",
    "desire_title": "Lo que puedo hacer por ti",
    "desire_trigger": "En este preciso instante, mientras lees estas palabras, la solución que buscas está más cerca de lo que crees.",
    "urgency_title": "El momento es AHORA",
    "urgency_closer": "Cada minuto que pasa sin actuar es un minuto más de incertidumbre."
}

mock_live_questions = [
    {"question": "¿Cuánto tarda un amarre?", "answer": "Los primeros efectos suelen notarse entre 7 y 21 días.", "whatsapp_text": "Hola, quiero saber sobre tiempos"},
    {"question": "¿Es seguro?", "answer": "Totalmente seguro y confidencial.", "whatsapp_text": "Hola, tengo dudas sobre seguridad"}
]

# Mock design object (required by the template)
mock_design = {
    "design_id": "test_design",
    "design_name": "Test Design",
    "category": "Esoteric",
    "atmosphere_name": "Mystic",
    "timestamp": "2023-10-27",
    "font_import_url": "https://fonts.googleapis.com/css2?family=Roboto&display=swap",
    "fonts": {"heading": "Roboto", "body": "Roboto"},
    "colors": {
        "primary": "#8B5CF6", "primary_dark": "#6D28D9", "primary_light": "#A78BFA",
        "secondary": "#EC4899", "accent": "#F59E0B", "surface": "#1E293B", "background": "#0F172A"
    },
    "css_variables": "",
    "animation_css": "",
    "section_styles": {
        "hero": "", "hero_overlay": "", "content": "", "testimonial": "", "cta_button": "", "cta_button_hover": "", "footer": ""
    },
    "icons": ["🔮", "✨"],
    "mood_keywords": ["Místico", "Poderoso"],
    "hero_icon": "🔮",
    "layout": {
        "hero_style": "centered",
        "content_style": "single_column",
        "features_style": "grid_2"
    }
}

def verify_template_rendering():
    templates_dir = os.path.join(os.getcwd(), "templates/landing")
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=select_autoescape(["html"]))
    template = env.get_template("dynamic_ai.html")

    # Render with ALL sections enabled
    output = template.render(
        seo_title="Test Page",
        seo_description="Test Description",
        keywords=["test"],
        design=mock_design,
        headline="Test Headline",
        subheadline="Test Subheadline",
        whatsapp="1234567890",
        gtm_id="GTM-TEST",
        intro_paragraph="<p>Intro</p>",
        body_paragraph="<p>Body</p>",
        
        # Original Sections
        show_premium_services=True,
        premium_services=mock_premium_services,
        
        show_testimonials=True,
        testimonials=mock_testimonials,
        
        show_blog=True,
        blog_articles=mock_blog_articles,
        
        show_faq=True,
        faqs=mock_faqs,
        
        # Conversion Booster
        show_conversion_booster=True,
        conversion_booster=mock_conversion_booster,
        
        # NEW: Hypnotic Texts
        show_hypnotic_texts=True,
        hypnotic_texts=mock_hypnotic_texts,
        
        # NEW: WhatsApp Sticky Bars
        show_whatsapp_sticky_bars=True,
        
        # NEW: Vibrating Button
        show_vibrating_button=True,
        
        # NEW: Scroll Popup
        show_scroll_popup=True,
        
        # NEW: Live Consultations
        show_live_consultations=True,
        
        # NEW: Live Questions
        show_live_questions=True,
        live_questions=mock_live_questions,
        
        # NEW: Typing Effect
        show_typing_effect=True
    )

    # Verification
    errors = []
    
    print("=" * 60)
    print("🧪 VERIFICACIÓN DE SECCIONES OPCIONALES")
    print("=" * 60)
    
    # Original sections
    if "Lectura de Tarot Premium" not in output:
        errors.append("❌ Premium Services section not rendered")
    else:
        print("✅ Premium Services section rendered")

    if "Me cambió la vida totalmente" not in output:
        errors.append("❌ Testimonials section not rendered")
    else:
        print("✅ Testimonials section rendered")

    if "Cómo atraer el amor" not in output:
        errors.append("❌ Blog section not rendered")
    else:
        print("✅ Blog section rendered")

    if "¿Es seguro?" not in output:
        errors.append("❌ FAQ section not rendered")
    else:
        print("✅ FAQ section rendered")

    # Conversion Booster
    if "floating-whatsapp" in output or "exit-popup" in output:
        print("✅ Conversion Booster (Pop-ups/Banners) rendered")
    else:
        errors.append("❌ Conversion Booster not rendered")
    
    print("\n--- NUEVAS FUNCIONALIDADES ---\n")
    
    # Hypnotic Texts
    if "¿Por qué confiar en mí?" in output and "trust_builder" in output or "Imagina por un momento" in output:
        print("✅ Textos Hipnóticos rendered")
    else:
        errors.append("❌ Textos Hipnóticos not rendered")
    
    # WhatsApp Sticky Bars
    if "wa-sticky-top" in output and "wa-sticky-bottom" in output:
        print("✅ WhatsApp Sticky Bars (top + bottom) rendered")
    else:
        errors.append("❌ WhatsApp Sticky Bars not rendered")
    
    # Vibrating Button
    if "vibrating-wa-btn" in output and "colorCycle" in output:
        print("✅ Botón Vibrante con cambio de color rendered")
    else:
        errors.append("❌ Botón Vibrante not rendered")
    
    # Scroll Popup
    if "scroll-popup" in output and "45%" in output:
        print("✅ Pop-up de Scroll (45%) rendered")
    else:
        errors.append("❌ Pop-up de Scroll not rendered")
    
    # Live Consultations
    if "live-consultations" in output and "Últimas consultas" in output:
        print("✅ Consultas en Vivo rendered")
    else:
        errors.append("❌ Consultas en Vivo not rendered")
    
    # Live Questions
    if "Preguntas que más me hacen" in output or "¿Cuánto tarda un amarre?" in output:
        print("✅ Preguntas del Día rendered")
    else:
        errors.append("❌ Preguntas del Día not rendered")
    
    # Typing Effect
    if "typing-wa-container" in output and "Escribiendo..." in output:
        print("✅ Efecto Escribiendo... rendered")
    else:
        errors.append("❌ Efecto Escribiendo not rendered")

    print("\n" + "=" * 60)
    
    if errors:
        print("❌ ERRORES ENCONTRADOS:")
        for error in errors:
            print(f"   {error}")
        exit(1)
    else:
        print("🎉 TODAS LAS SECCIONES VERIFICADAS EXITOSAMENTE!")
        
        # Save test output for visual inspection
        with open("test_all_features_output.html", "w") as f:
            f.write(output)
        print(f"📄 Output guardado en: test_all_features_output.html ({len(output):,} bytes)")
        
        exit(0)

if __name__ == "__main__":
    verify_template_rendering()
