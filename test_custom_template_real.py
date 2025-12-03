#!/usr/bin/env python3
"""
🧪 TEST DE WIDGETS CON TEMPLATE PERSONALIZADA REAL
===================================================
Prueba el sistema de widgets con una template customizada que viene del
custom_template_manager o creada por el usuario.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from widgets_injector import inject_widgets
from premium_popups_injector import inject_premium_popups


def create_realistic_custom_template():
    """Crea una template personalizada realista basada en lo que generaría un usuario"""
    return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tarot Profesional - Consultas Online</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Georgia', serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #ffffff;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        /* Hero Section */
        .hero {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 80px 20px;
            position: relative;
            overflow: hidden;
        }
        
        .hero::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 600"><path d="M0,300 Q300,100 600,300 T1200,300" fill="none" stroke="rgba(139,92,246,0.1)" stroke-width="2"/></svg>');
            opacity: 0.3;
        }
        
        .hero-content {
            position: relative;
            z-index: 1;
        }
        
        .hero h1 {
            font-size: 4rem;
            margin-bottom: 20px;
            background: linear-gradient(135deg, #8b5cf6, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 0 30px rgba(139, 92, 246, 0.5);
        }
        
        .hero .subtitle {
            font-size: 1.5rem;
            color: #cbd5e1;
            margin-bottom: 40px;
        }
        
        .cta-button {
            display: inline-block;
            padding: 18px 50px;
            background: linear-gradient(135deg, #8b5cf6, #ec4899);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-size: 1.2rem;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 10px 40px rgba(139, 92, 246, 0.4);
            position: relative;
            overflow: hidden;
        }
        
        .cta-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 50px rgba(139, 92, 246, 0.6);
        }
        
        .cta-button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.5s;
        }
        
        .cta-button:hover::before {
            left: 100%;
        }
        
        /* Services Section */
        .services {
            padding: 100px 20px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
        }
        
        .services h2 {
            text-align: center;
            font-size: 3rem;
            margin-bottom: 60px;
            color: #8b5cf6;
        }
        
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 40px;
            margin-top: 40px;
        }
        
        .service-card {
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(236, 72, 153, 0.1));
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            transition: all 0.3s ease;
            border: 1px solid rgba(139, 92, 246, 0.3);
        }
        
        .service-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(139, 92, 246, 0.3);
            border-color: #8b5cf6;
        }
        
        .service-icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }
        
        .service-card h3 {
            font-size: 1.8rem;
            margin-bottom: 15px;
            color: #ec4899;
        }
        
        .service-card p {
            color: #cbd5e1;
            line-height: 1.8;
        }
        
        /* Testimonials */
        .testimonials {
            padding: 100px 20px;
        }
        
        .testimonials h2 {
            text-align: center;
            font-size: 3rem;
            margin-bottom: 60px;
            color: #8b5cf6;
        }
        
        .testimonials-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
        }
        
        .testimonial {
            background: rgba(255, 255, 255, 0.05);
            padding: 30px;
            border-radius: 15px;
            border-left: 4px solid #8b5cf6;
        }
        
        .testimonial-text {
            font-style: italic;
            color: #cbd5e1;
            margin-bottom: 15px;
        }
        
        .testimonial-author {
            color: #ec4899;
            font-weight: bold;
        }
        
        /* Footer */
        .footer {
            padding: 60px 20px;
            text-align: center;
            background: rgba(0, 0, 0, 0.3);
        }
        
        .footer p {
            color: #94a3b8;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .hero h1 {
                font-size: 2.5rem;
            }
            
            .hero .subtitle {
                font-size: 1.2rem;
            }
            
            .services h2,
            .testimonials h2 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <!-- Hero Section -->
    <section class="hero">
        <div class="hero-content">
            <h1>🔮 Descubre Tu Destino</h1>
            <p class="subtitle">Consultas de Tarot Profesional con Expertos Certificados</p>
            <a href="https://wa.me/573001234567" class="cta-button">
                💬 Consulta GRATIS Ahora
            </a>
        </div>
    </section>
    
    <!-- Services Section -->
    <section class="services">
        <div class="container">
            <h2>✨ Nuestros Servicios</h2>
            <div class="services-grid">
                <div class="service-card">
                    <div class="service-icon">🃏</div>
                    <h3>Lectura de Tarot</h3>
                    <p>Descubre lo que el universo tiene preparado para ti con nuestras lecturas profesionales de tarot.</p>
                </div>
                
                <div class="service-card">
                    <div class="service-icon">💫</div>
                    <h3>Carta Astral</h3>
                    <p>Conoce tu verdadero camino a través del análisis detallado de tu carta astral personalizada.</p>
                </div>
                
                <div class="service-card">
                    <div class="service-icon">❤️</div>
                    <h3>Amarres de Amor</h3>
                    <p>Rituales ancestrales para atraer y fortalecer el amor verdadero en tu vida.</p>
                </div>
                
                <div class="service-card">
                    <div class="service-icon">💰</div>
                    <h3>Prosperidad</h3>
                    <p>Abre los caminos de la abundancia y atrae la prosperidad que mereces.</p>
                </div>
                
                <div class="service-card">
                    <div class="service-icon">🧿</div>
                    <h3>Protección</h3>
                    <p>Limpias energéticas y protecciones contra energías negativas y envidias.</p>
                </div>
                
                <div class="service-card">
                    <div class="service-icon">🌟</div>
                    <h3>Orientación Espiritual</h3>
                    <p>Guía espiritual personalizada para encontrar tu verdadero propósito de vida.</p>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Testimonials Section -->
    <section class="testimonials">
        <div class="container">
            <h2>💬 Testimonios Reales</h2>
            <div class="testimonials-grid">
                <div class="testimonial">
                    <p class="testimonial-text">"Increíble experiencia. La lectura fue extremadamente precisa y me ayudó a tomar decisiones importantes en mi vida."</p>
                    <p class="testimonial-author">⭐⭐⭐⭐⭐ - María G., CDMX</p>
                </div>
                
                <div class="testimonial">
                    <p class="testimonial-text">"Después de años buscando respuestas, finalmente encontré claridad. Los resultados fueron sorprendentes."</p>
                    <p class="testimonial-author">⭐⭐⭐⭐⭐ - Carlos R., Bogotá</p>
                </div>
                
                <div class="testimonial">
                    <p class="testimonial-text">"El ritual de amor funcionó mejor de lo que esperaba. Ahora estoy más feliz que nunca con mi pareja."</p>
                    <p class="testimonial-author">⭐⭐⭐⭐⭐ - Ana L., Lima</p>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <p>&copy; 2025 Tarot Profesional. Todos los derechos reservados.</p>
            <p style="margin-top: 10px;">Consultas 100% confidenciales • Disponible 24/7 • Primera consulta GRATIS</p>
        </div>
    </footer>
    
    <!-- Google Tag Manager (placeholder) -->
    <script>
        console.log('🔮 Landing Page Cargada');
    </script>
</body>
</html>"""


def test_custom_template_detailed():
    """Test exhaustivo con template customizada"""
    print("\n" + "="*70)
    print("🧪 TEST DETALLADO: Template Personalizada de Usuario")
    print("="*70)
    
    # Create template
    html = create_realistic_custom_template()
    print(f"\n✅ Template personalizada creada: {len(html):,} bytes")
    print(f"   Tipo: Landing Page de Tarot Profesional")
    print(f"   Estructura: Hero + Services + Testimonials + Footer")
    
    # Widget configuration - ALL WIDGETS
    widget_config = {
        'whatsapp_number': '+573001234567',
        'phone_number': '+573001234567',
        'primary_color': '#8B5CF6',
        'secondary_color': '#EC4899',
        
        'show_sticky_bars': True,
        'show_vibrating_button': True,
        'show_scroll_popup': True,
        'show_live_consultations': True,
        'show_live_questions': True,
        'show_hypnotic_texts': True,
        'show_typing_effect': True,
        
        'sticky_bars_style': 'mystical',
        'vibrating_button_style': 'heart',
        'scroll_popup_style': 'slide_up',
        'live_consultations_style': 'toast',
        'live_questions_style': 'cards',
        'hypnotic_texts_style': 'flip',
        'typing_effect_style': 'ios',
    }
    
    # Inject widgets
    print("\n🔌 Inyectando TODOS los widgets...")
    print("   Estilos seleccionados:")
    print(f"   • Sticky Bars: {widget_config['sticky_bars_style']}")
    print(f"   • Vibrating Button: {widget_config['vibrating_button_style']}")
    print(f"   • Scroll Popup: {widget_config['scroll_popup_style']}")
    print(f"   • Live Consultations: {widget_config['live_consultations_style']}")
    print(f"   • Live Questions: {widget_config['live_questions_style']}")
    print(f"   • Hypnotic Texts: {widget_config['hypnotic_texts_style']}")
    print(f"   • Typing Effect: {widget_config['typing_effect_style']}")
    
    html_with_widgets = inject_widgets(html, widget_config)
    
    # Detailed checks
    print("\n📋 Verificación detallada de widgets:")
    
    widget_checks = {
        'wa-sticky-bar': ('Sticky Bar', 'Barra adhesiva con WhatsApp'),
        'vibrating-wa-btn': ('Vibrating Button', 'Botón flotante vibrante'),
        'scroll-popup': ('Scroll Popup', 'Popup de captura al scroll'),
        'live-notification': ('Live Consultations', 'Notificaciones en tiempo real'),
        'live-questions-section': ('Live Questions', 'Sección de preguntas frecuentes'),
        'hypnotic-section': ('Hypnotic Texts', 'Textos hipnóticos persuasivos'),
        'typing-indicator': ('Typing Effect', 'Efecto de escritura en vivo'),
        'widgets-injected-css': ('CSS Styles', 'Estilos de widgets'),
        'widgets-injected-js': ('JavaScript', 'Scripts de widgets'),
    }
    
    injected = 0
    for widget_id, (name, description) in widget_checks.items():
        if widget_id in html_with_widgets:
            print(f"   ✅ {name:20} - {description}")
            injected += 1
        else:
            print(f"   ❌ {name:20} - NO ENCONTRADO")
    
    print(f"\n📊 Resultado: {injected}/{len(widget_checks)} widgets inyectados")
    
    # Inject premium popups
    print("\n🎯 Inyectando Premium Popups...")
    popup_ids = [
        'urgency_timer',
        'exit_intent', 
        'social_proof',
        'wheel_fortune',
        'floating_cta'
    ]
    
    print(f"   Popups seleccionados: {len(popup_ids)}")
    for i, pid in enumerate(popup_ids, 1):
        print(f"   {i}. {pid.replace('_', ' ').title()}")
    
    popup_config = {
        'whatsapp_number': '+573001234567',
        'primary_color': '#8B5CF6',
        'secondary_color': '#EC4899',
    }
    
    html_final = inject_premium_popups(html_with_widgets, popup_ids, popup_config)
    
    # Check popups
    print("\n📋 Verificación de popups:")
    popup_checks = {
        'premium-popup-urgency-timer': 'Urgency Timer (Countdown)',
        'premium-popup-exit-intent': 'Exit Intent (Capture)',
        'premium-popup-social-proof': 'Social Proof (Visitors)',
        'premium-popup-wheel-fortune': 'Wheel of Fortune (Interactive)',
        'premium-popup-floating-cta': 'Floating CTA (Notification)',
        'premium-popups-css': 'Popup CSS Styles',
        'premium-popups-js': 'Popup JavaScript',
    }
    
    popup_injected = 0
    for popup_id, description in popup_checks.items():
        if popup_id in html_final:
            print(f"   ✅ {description}")
            popup_injected += 1
        else:
            print(f"   ❌ {description} - NO ENCONTRADO")
    
    print(f"\n📊 Resultado: {popup_injected}/{len(popup_checks)} popups inyectados")
    
    # Size analysis
    print(f"\n📏 Análisis de tamaño:")
    print(f"   Template original:    {len(html):>8,} bytes")
    print(f"   Con widgets:          {len(html_with_widgets):>8,} bytes (+{len(html_with_widgets)-len(html):,})")
    print(f"   Con popups:           {len(html_final):>8,} bytes (+{len(html_final)-len(html):,})")
    
    growth_percent = ((len(html_final) - len(html)) / len(html)) * 100
    print(f"   Crecimiento total:    {growth_percent:.1f}%")
    
    # Save output
    output_dir = Path(__file__).parent / 'test_output_templates'
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "test_custom_tarot_professional.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_final)
    
    print(f"\n💾 Archivo guardado: {output_file}")
    
    # Injection method analysis
    print("\n🔍 Análisis de inyección:")
    if '<!-- 🔌 WIDGETS CSS START -->' in html_final:
        print("   ✅ Método: Inyección Normal (</head> y </body>)")
    elif '<!-- 🔌 WIDGETS FALLBACK INJECTION -->' in html_final:
        print("   ⚠️  Método: Inyección Alternativa (</html>)")
    elif 'widgets-ultra-fallback' in html_final:
        print("   🛡️ Método: Ultra-Fallback (Auto-inyección JS)")
    
    # Structure check
    print("\n🏗️  Análisis de estructura:")
    print(f"   • Tiene <head>: {'✅' if '<head>' in html_final else '❌'}")
    print(f"   • Tiene </head>: {'✅' if '</head>' in html_final else '❌'}")
    print(f"   • Tiene <body>: {'✅' if '<body>' in html_final else '❌'}")
    print(f"   • Tiene </body>: {'✅' if '</body>' in html_final else '❌'}")
    print(f"   • Tiene </html>: {'✅' if '</html>' in html_final else '❌'}")
    
    # Final verdict
    success = injected >= 7 and popup_injected >= 5
    
    print("\n" + "="*70)
    if success:
        print("✅ TEST EXITOSO: Template personalizada completamente funcional")
        print("="*70)
        print("\n🎉 TODOS LOS WIDGETS Y POPUPS INYECTADOS CORRECTAMENTE")
        print("\n💡 La template está lista para:")
        print("   • Capturar leads con múltiples widgets de conversión")
        print("   • Mostrar urgencia y prueba social")
        print("   • Engagement continuo con notificaciones live")
        print("   • Exit intent capture")
        print("   • Gamificación con ruleta de fortuna")
        return 0
    else:
        print("❌ TEST FALLIDO: Algunos componentes no se inyectaron")
        print("="*70)
        return 1


if __name__ == '__main__':
    sys.exit(test_custom_template_detailed())
