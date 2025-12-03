"""
🎯 PREMIUM POPUPS INJECTOR - Sistema de Popups Premium de Conversión
=====================================================================
Este módulo inyecta popups premium altamente visuales y optimizados para conversión.

Popups disponibles:
1. urgency_timer - Temporizador de urgencia con cuenta regresiva
2. flash_offer - Oferta flash con descuento limitado
3. exit_intent - Popup de intención de salida
4. social_proof - Prueba social con contador de visitantes
5. wheel_fortune - Ruleta de la fortuna interactiva
6. quiz_lead - Quiz de captura de leads
7. floating_cta - CTA flotante con animación
8. welcome_mat - Bienvenida en pantalla completa
9. notification_stack - Stack de notificaciones en tiempo real
10. video_popup - Popup con video embebido

Uso:
    from premium_popups_injector import PremiumPopupsInjector, inject_premium_popups
    
    injector = PremiumPopupsInjector(config)
    html_with_popups = injector.inject(html_original, ['urgency_timer', 'social_proof'])
"""

import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class PremiumPopupsInjector:
    """
    🎯 INYECTOR DE POPUPS PREMIUM
    ============================
    
    Inyecta popups premium de alta conversión en landing pages.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.whatsapp_number = self.config.get('whatsapp_number', '+573001234567')
        self.primary_color = self.config.get('primary_color', '#8B5CF6')
        self.secondary_color = self.config.get('secondary_color', '#6B46C1')
    
    def inject(self, html: str, popup_ids: List[str]) -> str:
        """
        🎯 Inyecta popups premium en el HTML
        
        Args:
            html: HTML original
            popup_ids: Lista de IDs de popups a inyectar
        
        Returns:
            HTML con popups inyectados
        """
        if not popup_ids:
            return html
        
        logger.info(f"🎯 Injecting {len(popup_ids)} premium popups: {', '.join(popup_ids)}")
        
        # Generate CSS
        css_code = self._generate_css()
        
        # Generate HTML for each popup
        html_code = ""
        for popup_id in popup_ids:
            popup_html = self._generate_popup_html(popup_id)
            if popup_html:
                html_code += popup_html + "\n"
        
        # Generate JavaScript
        js_code = self._generate_js(popup_ids)
        
        # Inject into HTML
        html = self._inject_code(html, css_code, html_code, js_code)
        
        logger.info(f"✅ Premium popups injected successfully")
        return html
    
    def _inject_code(self, html: str, css: str, html_code: str, js: str) -> str:
        """Inyecta CSS, HTML y JS en el documento"""
        # Inject CSS before </head>
        if "</head>" in html:
            html = html.replace("</head>", f"{css}</head>", 1)
        else:
            html = css + html
        
        # Inject HTML and JS before </body>
        if "</body>" in html:
            html = html.replace("</body>", f"{html_code}{js}</body>", 1)
        else:
            html = html + html_code + js
        
        return html
    
    def _generate_css(self) -> str:
        """Genera CSS base para todos los popups"""
        return f"""
<style id="premium-popups-css">
/* 🎯 PREMIUM POPUPS - Base Styles */
.premium-popup {{
    position: fixed;
    z-index: 2147483647;
    display: none;
    animation: premiumFadeIn 0.3s ease-out;
}}

.premium-popup.active {{
    display: flex !important;
}}

.premium-popup-overlay {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(8px);
    z-index: 2147483646;
}}

.premium-popup-content {{
    position: relative;
    background: white;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    max-width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    animation: premiumSlideUp 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}}

.premium-popup-close {{
    position: absolute;
    top: 15px;
    right: 15px;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: rgba(0, 0, 0, 0.1);
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #333;
    transition: all 0.3s;
    z-index: 10;
}}

.premium-popup-close:hover {{
    background: rgba(0, 0, 0, 0.2);
    transform: rotate(90deg);
}}

.premium-btn {{
    display: inline-block;
    padding: 15px 40px;
    background: {self.primary_color};
    color: white;
    border: none;
    border-radius: 50px;
    font-size: 18px;
    font-weight: bold;
    cursor: pointer;
    text-decoration: none;
    text-align: center;
    transition: all 0.3s;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
}}

.premium-btn:hover {{
    background: {self.secondary_color};
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
}}

@keyframes premiumFadeIn {{
    from {{ opacity: 0; }}
    to {{ opacity: 1; }}
}}

@keyframes premiumSlideUp {{
    from {{ transform: translateY(50px) scale(0.9); opacity: 0; }}
    to {{ transform: translateY(0) scale(1); opacity: 1; }}
}}

@keyframes premiumPulse {{
    0%, 100% {{ transform: scale(1); }}
    50% {{ transform: scale(1.05); }}
}}

@keyframes premiumShake {{
    0%, 100% {{ transform: translateX(0); }}
    25% {{ transform: translateX(-5px); }}
    75% {{ transform: translateX(5px); }}
}}

/* Responsive */
@media (max-width: 768px) {{
    .premium-popup-content {{
        max-width: 95%;
        border-radius: 15px;
    }}
    
    .premium-btn {{
        padding: 12px 30px;
        font-size: 16px;
    }}
}}
</style>
"""
    
    def _generate_popup_html(self, popup_id: str) -> str:
        """Genera HTML para un popup específico"""
        popups = {
            'urgency_timer': self._html_urgency_timer,
            'flash_offer': self._html_flash_offer,
            'exit_intent': self._html_exit_intent,
            'social_proof': self._html_social_proof,
            'wheel_fortune': self._html_wheel_fortune,
            'quiz_lead': self._html_quiz_lead,
            'floating_cta': self._html_floating_cta,
            'welcome_mat': self._html_welcome_mat,
            'notification_stack': self._html_notification_stack,
            'video_popup': self._html_video_popup,
        }
        
        generator = popups.get(popup_id)
        if generator:
            return generator()
        else:
            logger.warning(f"⚠️ Unknown popup ID: {popup_id}")
            return ""
    
    def _html_urgency_timer(self) -> str:
        """Popup de temporizador de urgencia"""
        return f"""
<div id="premium-popup-urgency-timer" class="premium-popup" style="align-items: center; justify-content: center;">
    <div class="premium-popup-overlay" onclick="closePremiumPopup('urgency-timer')"></div>
    <div class="premium-popup-content" style="padding: 40px; text-align: center; max-width: 500px;">
        <button class="premium-popup-close" onclick="closePremiumPopup('urgency-timer')">×</button>
        
        <div style="font-size: 48px; margin-bottom: 20px;">⏰</div>
        <h2 style="color: #1a1a1a; font-size: 32px; margin-bottom: 15px;">¡Oferta por Tiempo Limitado!</h2>
        <p style="color: #666; font-size: 18px; margin-bottom: 30px;">Esta promoción expira en:</p>
        
        <div id="urgency-countdown" style="display: flex; gap: 20px; justify-content: center; margin-bottom: 30px;">
            <div style="text-align: center;">
                <div id="urgency-hours" style="font-size: 48px; font-weight: bold; color: {self.primary_color};">00</div>
                <div style="font-size: 14px; color: #999;">Horas</div>
            </div>
            <div style="font-size: 48px; color: {self.primary_color};">:</div>
            <div style="text-align: center;">
                <div id="urgency-minutes" style="font-size: 48px; font-weight: bold; color: {self.primary_color};">00</div>
                <div style="font-size: 14px; color: #999;">Minutos</div>
            </div>
            <div style="font-size: 48px; color: {self.primary_color};">:</div>
            <div style="text-align: center;">
                <div id="urgency-seconds" style="font-size: 48px; font-weight: bold; color: {self.primary_color};">00</div>
                <div style="font-size: 14px; color: #999;">Segundos</div>
            </div>
        </div>
        
        <a href="https://wa.me/{self.whatsapp_number.replace('+', '')}" class="premium-btn" style="animation: premiumPulse 2s infinite;">
            ¡Consultar Ahora! 💬
        </a>
    </div>
</div>
"""
    
    def _html_flash_offer(self) -> str:
        """Popup de oferta flash"""
        return f"""
<div id="premium-popup-flash-offer" class="premium-popup" style="align-items: center; justify-content: center;">
    <div class="premium-popup-overlay" onclick="closePremiumPopup('flash-offer')"></div>
    <div class="premium-popup-content" style="padding: 40px; text-align: center; max-width: 500px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
        <button class="premium-popup-close" onclick="closePremiumPopup('flash-offer')" style="color: white; background: rgba(255,255,255,0.2);">×</button>
        
        <div style="font-size: 64px; margin-bottom: 20px;">⚡</div>
        <div style="background: rgba(255,255,255,0.2); padding: 10px 30px; border-radius: 50px; display: inline-block; margin-bottom: 20px; font-weight: bold;">
            OFERTA FLASH
        </div>
        
        <h2 style="font-size: 36px; margin-bottom: 15px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">¡50% de Descuento!</h2>
        <p style="font-size: 20px; margin-bottom: 30px; opacity: 0.95;">Solo para los primeros 10 clientes de hoy</p>
        
        <div style="background: rgba(255,255,255,0.2); padding: 20px; border-radius: 15px; margin-bottom: 30px;">
            <div style="font-size: 16px; opacity: 0.9; margin-bottom: 10px;">Consultas restantes:</div>
            <div style="display: flex; gap: 10px; justify-content: center;">
                <div id="flash-slot-1" class="flash-slot" style="width: 40px; height: 40px; background: rgba(255,255,255,0.3); border-radius: 8px;"></div>
                <div id="flash-slot-2" class="flash-slot" style="width: 40px; height: 40px; background: rgba(255,255,255,0.3); border-radius: 8px;"></div>
                <div id="flash-slot-3" class="flash-slot" style="width: 40px; height: 40px; background: rgba(255,255,255,0.3); border-radius: 8px;"></div>
            </div>
        </div>
        
        <a href="https://wa.me/{self.whatsapp_number.replace('+', '')}" class="premium-btn" style="background: white; color: #667eea;">
            ¡Aprovechar Ahora! 🎁
        </a>
    </div>
</div>
"""
    
    def _html_exit_intent(self) -> str:
        """Popup de intención de salida"""
        return f"""
<div id="premium-popup-exit-intent" class="premium-popup" style="align-items: center; justify-content: center;">
    <div class="premium-popup-overlay" onclick="closePremiumPopup('exit-intent')"></div>
    <div class="premium-popup-content" style="padding: 40px; text-align: center; max-width: 550px;">
        <button class="premium-popup-close" onclick="closePremiumPopup('exit-intent')">×</button>
        
        <div style="font-size: 64px; margin-bottom: 20px;">🛑</div>
        <h2 style="color: #1a1a1a; font-size: 32px; margin-bottom: 15px;">¡Espera! No te vayas sin tu consulta</h2>
        <p style="color: #666; font-size: 18px; margin-bottom: 30px;">
            Miles de personas han transformado su vida con nuestra ayuda. ¿Seguro que quieres irte sin intentarlo?
        </p>
        
        <div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 25px; border-radius: 15px; margin-bottom: 30px;">
            <p style="font-size: 20px; font-weight: bold; color: #333; margin-bottom: 10px;">
                🎁 Bonus Especial para Ti
            </p>
            <p style="font-size: 16px; color: #666;">
                Primera consulta 100% GRATIS + Lectura energética de regalo
            </p>
        </div>
        
        <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
            <a href="https://wa.me/{self.whatsapp_number.replace('+', '')}" class="premium-btn">
                Sí, Quiero Mi Consulta 💬
            </a>
            <button onclick="closePremiumPopup('exit-intent')" style="padding: 15px 40px; background: transparent; color: #999; border: 2px solid #ddd; border-radius: 50px; font-size: 16px; cursor: pointer;">
                No, gracias
            </button>
        </div>
    </div>
</div>
"""
    
    def _html_social_proof(self) -> str:
        """Popup de prueba social"""
        return f"""
<div id="premium-popup-social-proof" class="premium-popup" style="align-items: center; justify-content: center;">
    <div class="premium-popup-overlay" onclick="closePremiumPopup('social-proof')"></div>
    <div class="premium-popup-content" style="padding: 40px; text-align: center; max-width: 500px;">
        <button class="premium-popup-close" onclick="closePremiumPopup('social-proof')">×</button>
        
        <div style="font-size: 48px; margin-bottom: 20px;">👥</div>
        <h2 style="color: #1a1a1a; font-size: 28px; margin-bottom: 25px;">¡Únete a Miles de Personas Satisfechas!</h2>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white;">
                <div style="font-size: 36px; font-weight: bold;" id="social-visitors">2,847</div>
                <div style="font-size: 14px; opacity: 0.9;">Visitantes hoy</div>
            </div>
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 15px; color: white;">
                <div style="font-size: 36px; font-weight: bold;">4.9⭐</div>
                <div style="font-size: 14px; opacity: 0.9;">Calificación</div>
            </div>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 15px; margin-bottom: 30px; text-align: left;">
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
                <div style="width: 50px; height: 50px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"></div>
                <div>
                    <div style="font-weight: bold; color: #333;">María G.</div>
                    <div style="font-size: 14px; color: #999;">Hace 5 minutos</div>
                </div>
            </div>
            <p style="color: #666; font-size: 15px; margin: 0;">
                "¡Increíble! Los resultados fueron inmediatos. Totalmente recomendado ⭐⭐⭐⭐⭐"
            </p>
        </div>
        
        <a href="https://wa.me/{self.whatsapp_number.replace('+', '')}" class="premium-btn">
            Comenzar Mi Consulta 💬
        </a>
    </div>
</div>
"""
    
    def _html_wheel_fortune(self) -> str:
        """Popup de ruleta de la fortuna"""
        return f"""
<div id="premium-popup-wheel-fortune" class="premium-popup" style="align-items: center; justify-content: center;">
    <div class="premium-popup-overlay" onclick="closePremiumPopup('wheel-fortune')"></div>
    <div class="premium-popup-content" style="padding: 40px; text-align: center; max-width: 500px;">
        <button class="premium-popup-close" onclick="closePremiumPopup('wheel-fortune')">×</button>
        
        <h2 style="color: #1a1a1a; font-size: 28px; margin-bottom: 15px;">🎡 Gira la Ruleta de la Suerte</h2>
        <p style="color: #666; font-size: 16px; margin-bottom: 30px;">¡Todos ganan! Descubre tu premio especial</p>
        
        <div id="fortune-wheel" style="width: 300px; height: 300px; margin: 0 auto 30px; border-radius: 50%; background: conic-gradient(from 0deg, #ff6b6b 0deg 60deg, #4ecdc4 60deg 120deg, #ffe66d 120deg 180deg, #a8e6cf 180deg 240deg, #ffd3b6 240deg 300deg, #ffaaa5 300deg 360deg); position: relative; box-shadow: 0 10px 30px rgba(0,0,0,0.2); transition: transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99);">
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 60px; height: 60px; background: white; border-radius: 50%; box-shadow: 0 4px 15px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; color: {self.primary_color};">
                GIRA
            </div>
            <div style="position: absolute; top: -20px; left: 50%; transform: translateX(-50%); font-size: 30px;">🔽</div>
        </div>
        
        <div id="wheel-result" style="display: none; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px;">
            <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;">🎉 ¡Felicidades!</div>
            <div id="wheel-prize" style="font-size: 18px;">Has ganado: Consulta GRATIS + Lectura Tarot</div>
        </div>
        
        <button onclick="spinWheel()" id="spin-btn" class="premium-btn">
            Girar Ahora 🎯
        </button>
        
        <a href="https://wa.me/{self.whatsapp_number.replace('+', '')}" id="claim-prize-btn" class="premium-btn" style="display: none;">
            Reclamar Mi Premio 🎁
        </a>
    </div>
</div>
"""
    
    def _html_quiz_lead(self) -> str:
        """Popup de quiz para captura de leads"""
        return f"""
<div id="premium-popup-quiz-lead" class="premium-popup" style="align-items: center; justify-content: center;">
    <div class="premium-popup-overlay" onclick="closePremiumPopup('quiz-lead')"></div>
    <div class="premium-popup-content" style="padding: 40px; max-width: 550px;">
        <button class="premium-popup-close" onclick="closePremiumPopup('quiz-lead')">×</button>
        
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 48px; margin-bottom: 15px;">🔮</div>
            <h2 style="color: #1a1a1a; font-size: 28px; margin-bottom: 10px;">Descubre Tu Camino</h2>
            <p style="color: #666; font-size: 16px;">Responde 3 preguntas y recibe tu lectura personalizada GRATIS</p>
        </div>
        
        <div id="quiz-progress" style="background: #f0f0f0; height: 8px; border-radius: 10px; margin-bottom: 30px; overflow: hidden;">
            <div id="quiz-bar" style="background: linear-gradient(90deg, {self.primary_color}, {self.secondary_color}); height: 100%; width: 33%; transition: width 0.3s;"></div>
        </div>
        
        <div id="quiz-question-1" class="quiz-question" style="display: block;">
            <h3 style="color: #333; font-size: 20px; margin-bottom: 20px;">1. ¿Qué área de tu vida quieres mejorar?</h3>
            <div style="display: grid; gap: 15px;">
                <button onclick="nextQuizQuestion(2)" style="padding: 15px; background: white; border: 2px solid #e0e0e0; border-radius: 10px; cursor: pointer; text-align: left; transition: all 0.3s;">
                    ❤️ Amor y Relaciones
                </button>
                <button onclick="nextQuizQuestion(2)" style="padding: 15px; background: white; border: 2px solid #e0e0e0; border-radius: 10px; cursor: pointer; text-align: left; transition: all 0.3s;">
                    💰 Dinero y Prosperidad
                </button>
                <button onclick="nextQuizQuestion(2)" style="padding: 15px; background: white; border: 2px solid #e0e0e0; border-radius: 10px; cursor: pointer; text-align: left; transition: all 0.3s;">
                    🌟 Crecimiento Personal
                </button>
            </div>
        </div>
        
        <div id="quiz-question-2" class="quiz-question" style="display: none;">
            <h3 style="color: #333; font-size: 20px; margin-bottom: 20px;">2. ¿Qué tan urgente es tu situación?</h3>
            <div style="display: grid; gap: 15px;">
                <button onclick="nextQuizQuestion(3)" style="padding: 15px; background: white; border: 2px solid #e0e0e0; border-radius: 10px; cursor: pointer; text-align: left; transition: all 0.3s;">
                    🔥 Muy urgente
                </button>
                <button onclick="nextQuizQuestion(3)" style="padding: 15px; background: white; border: 2px solid #e0e0e0; border-radius: 10px; cursor: pointer; text-align: left; transition: all 0.3s;">
                    ⏰ Moderada
                </button>
                <button onclick="nextQuizQuestion(3)" style="padding: 15px; background: white; border: 2px solid #e0e0e0; border-radius: 10px; cursor: pointer; text-align: left; transition: all 0.3s;">
                    🌱 Explorando opciones
                </button>
            </div>
        </div>
        
        <div id="quiz-question-3" class="quiz-question" style="display: none;">
            <h3 style="color: #333; font-size: 20px; margin-bottom: 20px;">3. ¿Has consultado antes con expertos?</h3>
            <div style="display: grid; gap: 15px;">
                <button onclick="showQuizResult()" style="padding: 15px; background: white; border: 2px solid #e0e0e0; border-radius: 10px; cursor: pointer; text-align: left; transition: all 0.3s;">
                    ✅ Sí, varias veces
                </button>
                <button onclick="showQuizResult()" style="padding: 15px; background: white; border: 2px solid #e0e0e0; border-radius: 10px; cursor: pointer; text-align: left; transition: all 0.3s;">
                    👤 Una vez
                </button>
                <button onclick="showQuizResult()" style="padding: 15px; background: white; border: 2px solid #e0e0e0; border-radius: 10px; cursor: pointer; text-align: left; transition: all 0.3s;">
                    🆕 Es mi primera vez
                </button>
            </div>
        </div>
        
        <div id="quiz-result" style="display: none; text-align: center;">
            <div style="font-size: 64px; margin-bottom: 20px;">🎉</div>
            <h3 style="color: #333; font-size: 24px; margin-bottom: 15px;">¡Perfecto! Tu perfil está listo</h3>
            <p style="color: #666; font-size: 16px; margin-bottom: 30px;">
                Basado en tus respuestas, tenemos la solución perfecta para ti. Un experto te está esperando.
            </p>
            <a href="https://wa.me/{self.whatsapp_number.replace('+', '')}" class="premium-btn">
                Recibir Mi Lectura GRATIS 🔮
            </a>
        </div>
    </div>
</div>
"""
    
    def _html_floating_cta(self) -> str:
        """CTA flotante con animación"""
        return f"""
<div id="premium-popup-floating-cta" style="position: fixed; bottom: 20px; right: 20px; z-index: 2147483645; display: none;">
    <div style="background: linear-gradient(135deg, {self.primary_color} 0%, {self.secondary_color} 100%); color: white; padding: 20px 30px; border-radius: 50px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); display: flex; align-items: center; gap: 15px; cursor: pointer; animation: premiumPulse 2s infinite;" onclick="window.open('https://wa.me/{self.whatsapp_number.replace('+', '')}', '_blank')">
        <div style="width: 50px; height: 50px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px;">
            💬
        </div>
        <div>
            <div style="font-size: 18px; font-weight: bold;">¡Habla con un Experto!</div>
            <div style="font-size: 14px; opacity: 0.9;">Online ahora - Respuesta inmediata</div>
        </div>
    </div>
    <button onclick="document.getElementById('premium-popup-floating-cta').style.display='none'" style="position: absolute; top: -5px; right: -5px; width: 24px; height: 24px; border-radius: 50%; background: white; border: none; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-size: 16px; color: #666;">
        ×
    </button>
</div>
"""
    
    def _html_welcome_mat(self) -> str:
        """Bienvenida en pantalla completa"""
        return f"""
<div id="premium-popup-welcome-mat" class="premium-popup" style="align-items: center; justify-content: center; background: linear-gradient(135deg, {self.primary_color} 0%, {self.secondary_color} 100%);">
    <div class="premium-popup-content" style="background: transparent; box-shadow: none; max-width: 700px; color: white; text-align: center; padding: 60px 40px;">
        <button class="premium-popup-close" onclick="closePremiumPopup('welcome-mat')" style="color: white; background: rgba(255,255,255,0.2);">×</button>
        
        <div style="font-size: 80px; margin-bottom: 30px;">✨</div>
        <h1 style="font-size: 48px; margin-bottom: 20px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
            Bienvenido a Tu Transformación
        </h1>
        <p style="font-size: 24px; margin-bottom: 40px; opacity: 0.95;">
            Miles de personas ya han cambiado su vida. Ahora es tu turno.
        </p>
        
        <div style="background: rgba(255,255,255,0.2); backdrop-filter: blur(10px); padding: 30px; border-radius: 20px; margin-bottom: 40px;">
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px;">
                <div>
                    <div style="font-size: 36px; margin-bottom: 10px;">⚡</div>
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 5px;">Respuesta Rápida</div>
                    <div style="font-size: 14px; opacity: 0.9;">En menos de 5 min</div>
                </div>
                <div>
                    <div style="font-size: 36px; margin-bottom: 10px;">🔒</div>
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 5px;">100% Confidencial</div>
                    <div style="font-size: 14px; opacity: 0.9;">Tu privacidad es sagrada</div>
                </div>
                <div>
                    <div style="font-size: 36px; margin-bottom: 10px;">⭐</div>
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 5px;">Expertos Certificados</div>
                    <div style="font-size: 14px; opacity: 0.9;">+10 años experiencia</div>
                </div>
            </div>
        </div>
        
        <a href="https://wa.me/{self.whatsapp_number.replace('+', '')}" class="premium-btn" style="background: white; color: {self.primary_color}; font-size: 20px; padding: 18px 50px;">
            Comenzar Mi Consulta GRATIS 🎁
        </a>
        
        <div style="margin-top: 30px; opacity: 0.8; font-size: 14px;">
            <button onclick="closePremiumPopup('welcome-mat')" style="background: transparent; border: none; color: white; text-decoration: underline; cursor: pointer; font-size: 14px;">
                Continuar navegando →
            </button>
        </div>
    </div>
</div>
"""
    
    def _html_notification_stack(self) -> str:
        """Stack de notificaciones en tiempo real"""
        return f"""
<div id="premium-popup-notification-stack" style="position: fixed; bottom: 20px; left: 20px; z-index: 2147483645; display: flex; flex-direction: column; gap: 15px; max-width: 350px;">
</div>
"""
    
    def _html_video_popup(self) -> str:
        """Popup con video embebido"""
        return f"""
<div id="premium-popup-video" class="premium-popup" style="align-items: center; justify-content: center;">
    <div class="premium-popup-overlay" onclick="closePremiumPopup('video')"></div>
    <div class="premium-popup-content" style="padding: 0; max-width: 800px; border-radius: 20px; overflow: hidden;">
        <button class="premium-popup-close" onclick="closePremiumPopup('video')" style="background: rgba(0,0,0,0.5); color: white;">×</button>
        
        <div style="position: relative; padding-bottom: 56.25%; height: 0; background: #000;">
            <iframe id="video-player" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" src="" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
        </div>
        
        <div style="padding: 30px; text-align: center; background: white;">
            <h3 style="color: #333; font-size: 24px; margin-bottom: 15px;">¿Listo para transformar tu vida?</h3>
            <p style="color: #666; font-size: 16px; margin-bottom: 25px;">
                Nuestros expertos están disponibles 24/7 para ayudarte
            </p>
            <a href="https://wa.me/{self.whatsapp_number.replace('+', '')}" class="premium-btn">
                Iniciar Mi Consulta Ahora 💬
            </a>
        </div>
    </div>
</div>
"""
    
    def _generate_js(self, popup_ids: List[str]) -> str:
        """Genera JavaScript para manejar los popups"""
        return f"""
<script id="premium-popups-js">
(function() {{
    'use strict';
    
    const POPUP_IDS = {json.dumps(popup_ids)};
    const WHATSAPP = '{self.whatsapp_number}';
    
    // 🎯 Control de popups
    let popupsShown = new Set();
    let currentPopup = null;
    
    // Cerrar popup
    window.closePremiumPopup = function(id) {{
        const popup = document.getElementById('premium-popup-' + id);
        if (popup) {{
            popup.classList.remove('active');
            popupsShown.add(id);
            currentPopup = null;
        }}
    }};
    
    // Mostrar popup
    function showPopup(id) {{
        if (popupsShown.has(id) || currentPopup) return;
        
        const popup = document.getElementById('premium-popup-' + id);
        if (popup) {{
            popup.classList.add('active');
            currentPopup = id;
            
            // Ejecutar lógica específica del popup
            if (id === 'urgency-timer') startUrgencyTimer();
            if (id === 'social-proof') animateSocialProof();
            if (id === 'notification-stack') startNotifications();
            if (id === 'floating-cta') showFloatingCTA();
        }}
    }}
    
    // ⏰ Temporizador de urgencia
    function startUrgencyTimer() {{
        const endTime = Date.now() + (2 * 60 * 60 * 1000); // 2 horas
        
        function updateTimer() {{
            const now = Date.now();
            const diff = Math.max(0, endTime - now);
            
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);
            
            const h = document.getElementById('urgency-hours');
            const m = document.getElementById('urgency-minutes');
            const s = document.getElementById('urgency-seconds');
            
            if (h) h.textContent = String(hours).padStart(2, '0');
            if (m) m.textContent = String(minutes).padStart(2, '0');
            if (s) s.textContent = String(seconds).padStart(2, '0');
            
            if (diff > 0) {{
                setTimeout(updateTimer, 1000);
            }}
        }}
        
        updateTimer();
    }}
    
    // 👥 Animar prueba social
    function animateSocialProof() {{
        const el = document.getElementById('social-visitors');
        if (!el) return;
        
        let count = 2847;
        setInterval(() => {{
            count += Math.floor(Math.random() * 5);
            el.textContent = count.toLocaleString();
        }}, 5000);
    }}
    
    // 🎡 Girar ruleta
    window.spinWheel = function() {{
        const wheel = document.getElementById('fortune-wheel');
        const btn = document.getElementById('spin-btn');
        const result = document.getElementById('wheel-result');
        const claimBtn = document.getElementById('claim-prize-btn');
        
        if (!wheel || !btn) return;
        
        btn.disabled = true;
        btn.style.opacity = '0.5';
        
        const spins = 5 + Math.random() * 3;
        const degrees = (spins * 360) + (Math.random() * 360);
        wheel.style.transform = `rotate(${{degrees}}deg)`;
        
        setTimeout(() => {{
            if (result) result.style.display = 'block';
            if (claimBtn) {{
                claimBtn.style.display = 'inline-block';
                btn.style.display = 'none';
            }}
        }}, 4000);
    }};
    
    // 📝 Quiz
    window.nextQuizQuestion = function(num) {{
        document.querySelectorAll('.quiz-question').forEach(q => q.style.display = 'none');
        const next = document.getElementById('quiz-question-' + num);
        if (next) next.style.display = 'block';
        
        const bar = document.getElementById('quiz-bar');
        if (bar) bar.style.width = (num * 33) + '%';
    }};
    
    window.showQuizResult = function() {{
        document.querySelectorAll('.quiz-question').forEach(q => q.style.display = 'none');
        const result = document.getElementById('quiz-result');
        if (result) result.style.display = 'block';
        
        const bar = document.getElementById('quiz-bar');
        if (bar) bar.style.width = '100%';
    }};
    
    // 🔔 Notificaciones
    function startNotifications() {{
        const container = document.getElementById('premium-popup-notification-stack');
        if (!container) return;
        
        const notifications = [
            {{ name: 'María G.', city: 'Bogotá', action: 'acaba de consultar' }},
            {{ name: 'Carlos R.', city: 'Medellín', action: 'recibió su lectura' }},
            {{ name: 'Ana L.', city: 'Cali', action: 'confirmó su cita' }},
            {{ name: 'José M.', city: 'Barranquilla', action: 'está en consulta' }},
        ];
        
        let index = 0;
        
        function showNotification() {{
            const notif = notifications[index % notifications.length];
            index++;
            
            const el = document.createElement('div');
            el.style.cssText = 'background: white; padding: 15px 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); display: flex; align-items: center; gap: 15px; animation: premiumSlideUp 0.3s ease-out;';
            el.innerHTML = `
                <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, {self.primary_color}, {self.secondary_color}); flex-shrink: 0;"></div>
                <div style="flex: 1;">
                    <div style="font-weight: bold; color: #333; font-size: 14px;">${{notif.name}} - ${{notif.city}}</div>
                    <div style="color: #666; font-size: 13px;">${{notif.action}}</div>
                </div>
            `;
            
            container.appendChild(el);
            
            setTimeout(() => {{
                el.style.animation = 'premiumFadeOut 0.3s ease-out';
                setTimeout(() => el.remove(), 300);
            }}, 5000);
            
            setTimeout(showNotification, 8000 + Math.random() * 4000);
        }}
        
        showNotification();
    }}
    
    // 💬 CTA Flotante
    function showFloatingCTA() {{
        const cta = document.getElementById('premium-popup-floating-cta');
        if (cta) {{
            setTimeout(() => {{
                cta.style.display = 'block';
            }}, 3000);
        }}
    }}
    
    // 🎯 Estrategia de activación
    function activatePopups() {{
        if (!POPUP_IDS || POPUP_IDS.length === 0) return;
        
        // Exit Intent
        if (POPUP_IDS.includes('exit_intent')) {{
            let hasExited = false;
            document.addEventListener('mouseleave', (e) => {{
                if (e.clientY < 10 && !hasExited) {{
                    hasExited = true;
                    showPopup('exit-intent');
                }}
            }});
        }}
        
        // Welcome Mat (inmediato)
        if (POPUP_IDS.includes('welcome_mat')) {{
            setTimeout(() => showPopup('welcome-mat'), 1000);
        }}
        
        // Urgency Timer (5 segundos)
        if (POPUP_IDS.includes('urgency_timer')) {{
            setTimeout(() => showPopup('urgency-timer'), 5000);
        }}
        
        // Flash Offer (10 segundos)
        if (POPUP_IDS.includes('flash_offer')) {{
            setTimeout(() => showPopup('flash-offer'), 10000);
        }}
        
        // Social Proof (15 segundos)
        if (POPUP_IDS.includes('social_proof')) {{
            setTimeout(() => showPopup('social-proof'), 15000);
        }}
        
        // Wheel Fortune (20 segundos)
        if (POPUP_IDS.includes('wheel_fortune')) {{
            setTimeout(() => showPopup('wheel-fortune'), 20000);
        }}
        
        // Quiz Lead (25 segundos)
        if (POPUP_IDS.includes('quiz_lead')) {{
            setTimeout(() => showPopup('quiz-lead'), 25000);
        }}
        
        // Video Popup (30 segundos)
        if (POPUP_IDS.includes('video_popup')) {{
            setTimeout(() => showPopup('video'), 30000);
        }}
        
        // Floating CTA (scroll 50%)
        if (POPUP_IDS.includes('floating_cta')) {{
            let shown = false;
            window.addEventListener('scroll', () => {{
                if (shown) return;
                const scrolled = (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100;
                if (scrolled > 50) {{
                    shown = true;
                    showFloatingCTA();
                }}
            }});
        }}
        
        // Notification Stack (inmediato si está incluido)
        if (POPUP_IDS.includes('notification_stack')) {{
            startNotifications();
        }}
    }}
    
    // Iniciar cuando el DOM esté listo
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', activatePopups);
    }} else {{
        activatePopups();
    }}
    
    console.log('🎯 Premium Popups loaded:', POPUP_IDS.length, 'popups');
}})();
</script>
"""


def inject_premium_popups(html: str, popup_ids: List[str], config: Optional[Dict[str, Any]] = None) -> str:
    """
    🎯 Función helper para inyectar popups premium
    
    Args:
        html: HTML original
        popup_ids: Lista de IDs de popups a inyectar
        config: Configuración opcional
    
    Returns:
        HTML con popups inyectados
    """
    injector = PremiumPopupsInjector(config)
    return injector.inject(html, popup_ids)
