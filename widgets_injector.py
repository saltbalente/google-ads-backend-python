"""
🔌 WIDGETS INJECTOR - Sistema de Widgets Inyectables
====================================================
Este módulo permite inyectar widgets de conversión en cualquier template HTML.
Los widgets son independientes y se pueden agregar a landings existentes.

Uso:
    from widgets_injector import WidgetsInjector
    
    injector = WidgetsInjector(config)
    html_with_widgets = injector.inject(html_original)
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class WidgetConfig:
    """Configuración de widgets para inyección"""
    whatsapp_number: str = "+573001234567"
    phone_number: str = ""
    primary_color: str = "#8B5CF6"
    secondary_color: str = "#6B46C1"
    
    # Widget toggles
    show_sticky_bars: bool = False
    show_vibrating_button: bool = False
    show_scroll_popup: bool = False
    show_live_consultations: bool = False
    show_live_questions: bool = False
    show_hypnotic_texts: bool = False
    show_typing_effect: bool = False
    
    # Widget styles
    sticky_bars_style: str = "whatsapp"  # whatsapp, mystical, elegant, urgency
    vibrating_button_style: str = "circular"  # circular, square, heart, bubble
    scroll_popup_style: str = "centered"  # centered, slide_up, slide_right, fullscreen
    live_consultations_style: str = "floating"  # floating, toast, timeline, carousel
    live_questions_style: str = "accordion"  # accordion, cards, chat, minimal
    hypnotic_texts_style: str = "cards"  # cards, highlight, quotes, flip
    typing_effect_style: str = "bubble"  # bubble, badge, ios, tooltip
    
    # Content for widgets
    sticky_bar_text: str = "💬 ¡Consulta GRATIS ahora mismo!"
    popup_title: str = "¡Espera! ¿Te vas sin tu consulta gratis?"
    popup_message: str = "Un experto está disponible ahora mismo para ayudarte"
    live_questions: List[Dict[str, str]] = field(default_factory=list)
    hypnotic_messages: List[str] = field(default_factory=list)
    typing_messages: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.phone_number:
            self.phone_number = self.whatsapp_number
        if not self.live_questions:
            self.live_questions = [
                {"q": "¿Cuánto tiempo tardan los resultados?", "a": "Los primeros efectos se sienten en 24-48 horas."},
                {"q": "¿Es 100% confidencial?", "a": "Absolutamente. Tu privacidad es sagrada para nosotros."},
                {"q": "¿Funcionará en mi caso?", "a": "Cada situación es única. Consulta gratis para evaluación."}
            ]
        if not self.hypnotic_messages:
            self.hypnotic_messages = [
                "Tu destino está a punto de cambiar...",
                "Las energías se están alineando a tu favor...",
                "El universo conspira para tu felicidad..."
            ]
        if not self.typing_messages:
            self.typing_messages = [
                "Un experto está revisando tu caso...",
                "Preparando tu consulta personalizada...",
                "Conectando con las energías universales..."
            ]


class WidgetsInjector:
    """
    Inyecta widgets de conversión en cualquier HTML.
    Los widgets se agregan antes de </body> y los estilos antes de </head>.
    """
    
    def __init__(self, config: Optional[WidgetConfig] = None):
        self.config = config or WidgetConfig()
    
    def inject(self, html: str, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Inyecta widgets en el HTML proporcionado.
        
        Args:
            html: HTML original
            config: Configuración opcional (sobreescribe self.config)
        
        Returns:
            HTML con widgets inyectados
        """
        if config:
            self._update_config(config)
        
        # Generar CSS y HTML de widgets
        widgets_css = self._generate_widgets_css()
        widgets_html = self._generate_widgets_html()
        widgets_js = self._generate_widgets_js()
        
        # Inyectar CSS antes de </head>
        if widgets_css:
            css_tag = f"<style id='widgets-injected-css'>\n{widgets_css}\n</style>\n</head>"
            html = html.replace("</head>", css_tag)
        
        # Inyectar HTML y JS antes de </body>
        if widgets_html or widgets_js:
            injection = ""
            if widgets_html:
                injection += f"\n<!-- WIDGETS INJECTED -->\n{widgets_html}\n"
            if widgets_js:
                injection += f"\n<script id='widgets-injected-js'>\n{widgets_js}\n</script>\n"
            injection += "</body>"
            html = html.replace("</body>", injection)
        
        logger.info(f"✅ Widgets inyectados: CSS={len(widgets_css)}b, HTML={len(widgets_html)}b, JS={len(widgets_js)}b")
        return html
    
    def _update_config(self, config: Dict[str, Any]):
        """Actualiza la configuración desde un diccionario"""
        for key, value in config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def _generate_widgets_css(self) -> str:
        """Genera el CSS para todos los widgets activos"""
        css_parts = []
        
        if self.config.show_sticky_bars:
            css_parts.append(self._get_sticky_bars_css())
        
        if self.config.show_vibrating_button:
            css_parts.append(self._get_vibrating_button_css())
        
        if self.config.show_scroll_popup:
            css_parts.append(self._get_scroll_popup_css())
        
        if self.config.show_live_consultations:
            css_parts.append(self._get_live_consultations_css())
        
        if self.config.show_live_questions:
            css_parts.append(self._get_live_questions_css())
        
        if self.config.show_hypnotic_texts:
            css_parts.append(self._get_hypnotic_texts_css())
        
        if self.config.show_typing_effect:
            css_parts.append(self._get_typing_effect_css())
        
        return "\n".join(css_parts)
    
    def _generate_widgets_html(self) -> str:
        """Genera el HTML para todos los widgets activos"""
        html_parts = []
        
        if self.config.show_sticky_bars:
            html_parts.append(self._get_sticky_bars_html())
        
        if self.config.show_vibrating_button:
            html_parts.append(self._get_vibrating_button_html())
        
        if self.config.show_scroll_popup:
            html_parts.append(self._get_scroll_popup_html())
        
        if self.config.show_live_consultations:
            html_parts.append(self._get_live_consultations_html())
        
        if self.config.show_live_questions:
            html_parts.append(self._get_live_questions_html())
        
        if self.config.show_hypnotic_texts:
            html_parts.append(self._get_hypnotic_texts_html())
        
        if self.config.show_typing_effect:
            html_parts.append(self._get_typing_effect_html())
        
        return "\n".join(html_parts)
    
    def _generate_widgets_js(self) -> str:
        """Genera el JavaScript para todos los widgets activos"""
        js_parts = []
        
        if self.config.show_scroll_popup:
            js_parts.append(self._get_scroll_popup_js())
        
        if self.config.show_live_consultations:
            js_parts.append(self._get_live_consultations_js())
        
        if self.config.show_live_questions:
            js_parts.append(self._get_live_questions_js())
        
        if self.config.show_hypnotic_texts:
            js_parts.append(self._get_hypnotic_texts_js())
        
        if self.config.show_typing_effect:
            js_parts.append(self._get_typing_effect_js())
        
        return "\n".join(js_parts)
    
    # ========================================
    # STICKY BARS
    # ========================================
    def _get_sticky_bars_css(self) -> str:
        style = self.config.sticky_bars_style
        base_css = """
/* Sticky Bars Widget */
.wa-sticky-bar {
    position: fixed;
    left: 0;
    right: 0;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 10px 16px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    transition: transform 0.3s ease;
}
.wa-sticky-top { top: 0; }
.wa-sticky-bottom { bottom: 0; }
.wa-sticky-text { font-size: 14px; font-weight: 600; }
.wa-sticky-btn {
    padding: 8px 20px;
    border-radius: 25px;
    text-decoration: none;
    font-weight: 700;
    font-size: 14px;
    transition: all 0.3s ease;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}
.wa-sticky-btn:hover { transform: scale(1.05); }
.wa-sticky-status {
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 12px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}
.wa-sticky-status .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
@media (max-width: 640px) {
    .wa-sticky-bar { flex-wrap: wrap; padding: 8px 12px; gap: 8px; }
    .wa-sticky-text { font-size: 12px; }
    .wa-sticky-btn { padding: 6px 14px; font-size: 12px; }
}
"""
        
        if style == "mystical":
            base_css += """
.wa-sticky-bar {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%);
}
.wa-sticky-text { color: #e0e7ff; text-shadow: 0 0 10px rgba(139,92,246,0.5); }
.wa-sticky-btn { background: linear-gradient(135deg, #8b5cf6, #a855f7); color: white; box-shadow: 0 0 20px rgba(139,92,246,0.4); }
.wa-sticky-status { background: rgba(139,92,246,0.3); color: #c4b5fd; }
.wa-sticky-status .dot { background: #a855f7; box-shadow: 0 0 10px #a855f7; }
"""
        elif style == "elegant":
            base_css += """
.wa-sticky-bar { background: linear-gradient(135deg, #1f2937, #111827); }
.wa-sticky-text { color: #f3f4f6; }
.wa-sticky-btn { background: linear-gradient(135deg, #d4af37, #fbbf24); color: #1f2937; }
.wa-sticky-status { background: rgba(212,175,55,0.2); color: #fcd34d; }
.wa-sticky-status .dot { background: #fbbf24; }
"""
        elif style == "urgency":
            base_css += """
.wa-sticky-bar { background: linear-gradient(135deg, #7f1d1d, #991b1b, #dc2626); }
.wa-sticky-text { color: #fef2f2; }
.wa-sticky-btn { background: #fbbf24; color: #7f1d1d; animation: urgentPulse 1s infinite; }
@keyframes urgentPulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
.wa-sticky-status { background: rgba(251,191,36,0.2); color: #fcd34d; }
.wa-sticky-status .dot { background: #fbbf24; }
"""
        else:  # whatsapp default
            base_css += """
.wa-sticky-bar { background: linear-gradient(135deg, #128C7E, #075E54); }
.wa-sticky-text { color: white; }
.wa-sticky-btn { background: #25D366; color: white; }
.wa-sticky-status { background: rgba(37,211,102,0.2); color: #dcfce7; }
.wa-sticky-status .dot { background: #25D366; }
"""
        return base_css
    
    def _get_sticky_bars_html(self) -> str:
        wa_link = f"https://wa.me/{self.config.whatsapp_number.replace('+', '').replace(' ', '')}?text=Hola%2C%20quiero%20informaci%C3%B3n"
        return f"""
<!-- Sticky Bar Top -->
<div class="wa-sticky-bar wa-sticky-top">
    <span class="wa-sticky-text">💬 {self.config.sticky_bar_text}</span>
    <span class="wa-sticky-status"><span class="dot"></span> En línea</span>
    <a href="{wa_link}" class="wa-sticky-btn" target="_blank">📱 WhatsApp</a>
</div>
<!-- Sticky Bar Bottom -->
<div class="wa-sticky-bar wa-sticky-bottom">
    <span class="wa-sticky-text">⚡ Respuesta inmediata garantizada</span>
    <a href="{wa_link}" class="wa-sticky-btn" target="_blank">💬 Consulta Ahora</a>
</div>
"""

    # ========================================
    # VIBRATING BUTTON
    # ========================================
    def _get_vibrating_button_css(self) -> str:
        style = self.config.vibrating_button_style
        base_css = """
/* Vibrating Button Widget */
.vibrating-wa-btn {
    position: fixed;
    bottom: 90px;
    right: 20px;
    z-index: 9998;
    cursor: pointer;
    animation: vibrate 2s infinite;
    transition: all 0.3s ease;
}
.vibrating-wa-btn:hover { animation: none; transform: scale(1.15); }
@keyframes vibrate {
    0%, 100% { transform: rotate(0deg); }
    10% { transform: rotate(-5deg) scale(1.1); }
    20% { transform: rotate(5deg) scale(1.1); }
    30% { transform: rotate(-5deg); }
    40% { transform: rotate(5deg); }
    50%, 100% { transform: rotate(0deg); }
}
.vibrating-wa-btn a {
    display: flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    color: white;
    font-size: 28px;
}
@media (max-width: 640px) {
    .vibrating-wa-btn { bottom: 100px; right: 15px; }
    .vibrating-wa-btn a { font-size: 24px; }
}
"""
        if style == "heart":
            base_css += """
.vibrating-wa-btn a {
    width: 65px; height: 60px;
    background: linear-gradient(135deg, #ec4899, #f43f5e);
    clip-path: path('M32.5,60 C32.5,60 5,40 5,20 C5,8 15,0 27.5,10 C32.5,14 32.5,14 32.5,14 C32.5,14 32.5,14 37.5,10 C50,0 60,8 60,20 C60,40 32.5,60 32.5,60 Z');
    box-shadow: 0 5px 25px rgba(236,72,153,0.5);
}
"""
        elif style == "square":
            base_css += """
.vibrating-wa-btn a {
    width: 60px; height: 60px;
    background: linear-gradient(135deg, #25D366, #128C7E);
    border-radius: 15px;
    box-shadow: 0 5px 25px rgba(37,211,102,0.4);
}
"""
        elif style == "bubble":
            base_css += """
.vibrating-wa-btn a {
    width: 65px; height: 65px;
    background: linear-gradient(135deg, #8b5cf6, #6366f1);
    border-radius: 50% 50% 50% 20%;
    box-shadow: 0 5px 25px rgba(139,92,246,0.5);
}
"""
        else:  # circular default
            base_css += """
.vibrating-wa-btn a {
    width: 60px; height: 60px;
    background: linear-gradient(135deg, #25D366, #128C7E);
    border-radius: 50%;
    box-shadow: 0 5px 25px rgba(37,211,102,0.4);
}
"""
        return base_css
    
    def _get_vibrating_button_html(self) -> str:
        wa_link = f"https://wa.me/{self.config.whatsapp_number.replace('+', '').replace(' ', '')}?text=Hola"
        icon = "❤️" if self.config.vibrating_button_style == "heart" else "💬"
        return f"""
<!-- Vibrating WhatsApp Button -->
<div class="vibrating-wa-btn">
    <a href="{wa_link}" target="_blank" aria-label="WhatsApp">{icon}</a>
</div>
"""

    # ========================================
    # SCROLL POPUP
    # ========================================
    def _get_scroll_popup_css(self) -> str:
        style = self.config.scroll_popup_style
        base_css = """
/* Scroll Popup Widget */
.scroll-popup-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    z-index: 10000;
    display: none;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(5px);
}
.scroll-popup-overlay.active { display: flex; }
.scroll-popup {
    background: linear-gradient(135deg, #1e1b4b, #312e81);
    border-radius: 20px;
    padding: 30px;
    max-width: 400px;
    width: 90%;
    text-align: center;
    color: white;
    box-shadow: 0 25px 50px rgba(0,0,0,0.5);
    animation: popupIn 0.4s ease-out;
}
@keyframes popupIn {
    from { opacity: 0; transform: scale(0.8) translateY(20px); }
    to { opacity: 1; transform: scale(1) translateY(0); }
}
.scroll-popup h3 { font-size: 1.5rem; margin-bottom: 10px; }
.scroll-popup p { color: #c4b5fd; margin-bottom: 20px; }
.scroll-popup-btn {
    display: inline-block;
    padding: 14px 30px;
    background: linear-gradient(135deg, #25D366, #128C7E);
    color: white;
    text-decoration: none;
    border-radius: 30px;
    font-weight: 700;
    transition: transform 0.3s;
}
.scroll-popup-btn:hover { transform: scale(1.05); }
.scroll-popup-close {
    position: absolute;
    top: 15px;
    right: 15px;
    background: rgba(255,255,255,0.1);
    border: none;
    color: white;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 18px;
}
"""
        if style == "slide_up":
            base_css += """
.scroll-popup {
    position: fixed;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    border-radius: 20px 20px 0 0;
    animation: slideUp 0.4s ease-out;
}
@keyframes slideUp { from { transform: translateX(-50%) translateY(100%); } to { transform: translateX(-50%) translateY(0); } }
"""
        elif style == "slide_right":
            base_css += """
.scroll-popup {
    position: fixed;
    right: 20px;
    top: 50%;
    transform: translateY(-50%);
    animation: slideRight 0.4s ease-out;
}
@keyframes slideRight { from { transform: translateY(-50%) translateX(100%); } to { transform: translateY(-50%) translateX(0); } }
"""
        elif style == "fullscreen":
            base_css += """
.scroll-popup {
    max-width: 100%;
    width: 100%;
    height: 100vh;
    border-radius: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
"""
        return base_css
    
    def _get_scroll_popup_html(self) -> str:
        wa_link = f"https://wa.me/{self.config.whatsapp_number.replace('+', '').replace(' ', '')}?text=Quiero%20mi%20consulta%20gratis"
        return f"""
<!-- Scroll Popup -->
<div class="scroll-popup-overlay" id="scrollPopup">
    <div class="scroll-popup">
        <button class="scroll-popup-close" onclick="document.getElementById('scrollPopup').classList.remove('active')">✕</button>
        <h3>🔮 {self.config.popup_title}</h3>
        <p>{self.config.popup_message}</p>
        <a href="{wa_link}" class="scroll-popup-btn" target="_blank">💬 Sí, quiero mi consulta</a>
    </div>
</div>
"""
    
    def _get_scroll_popup_js(self) -> str:
        return """
// Scroll Popup Logic
(function() {
    let popupShown = false;
    window.addEventListener('scroll', function() {
        if (popupShown) return;
        const scrollPercent = (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100;
        if (scrollPercent > 50) {
            document.getElementById('scrollPopup').classList.add('active');
            popupShown = true;
        }
    });
})();
"""

    # ========================================
    # LIVE CONSULTATIONS
    # ========================================
    def _get_live_consultations_css(self) -> str:
        return """
/* Live Consultations Widget */
.live-notification {
    position: fixed;
    bottom: 160px;
    left: 20px;
    background: linear-gradient(135deg, #1e1b4b, #312e81);
    border: 1px solid rgba(139,92,246,0.3);
    border-radius: 12px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    z-index: 9997;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    animation: slideInLeft 0.5s ease-out;
    max-width: 280px;
    opacity: 0;
    transform: translateX(-100%);
    transition: all 0.5s ease;
}
.live-notification.show { opacity: 1; transform: translateX(0); }
@keyframes slideInLeft { from { transform: translateX(-100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.live-notification-avatar {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, #8b5cf6, #a855f7);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
}
.live-notification-content { flex: 1; }
.live-notification-text { color: #e0e7ff; font-size: 13px; font-weight: 500; }
.live-notification-time { color: #a78bfa; font-size: 11px; margin-top: 2px; }
@media (max-width: 640px) {
    .live-notification { left: 10px; right: 10px; max-width: none; bottom: 170px; }
}
"""
    
    def _get_live_consultations_html(self) -> str:
        return """
<!-- Live Consultations Notification -->
<div class="live-notification" id="liveNotification">
    <div class="live-notification-avatar">👤</div>
    <div class="live-notification-content">
        <div class="live-notification-text" id="liveNotifText">María de CDMX acaba de consultar</div>
        <div class="live-notification-time">Hace unos segundos</div>
    </div>
</div>
"""
    
    def _get_live_consultations_js(self) -> str:
        return """
// Live Consultations Logic
(function() {
    const names = ['María', 'Carlos', 'Ana', 'Juan', 'Laura', 'Pedro', 'Sofía', 'Diego'];
    const cities = ['CDMX', 'Bogotá', 'Lima', 'Madrid', 'Buenos Aires', 'Guadalajara'];
    const actions = ['acaba de consultar', 'inició su ritual', 'recibió resultados', 'está en consulta'];
    
    function showNotification() {
        const name = names[Math.floor(Math.random() * names.length)];
        const city = cities[Math.floor(Math.random() * cities.length)];
        const action = actions[Math.floor(Math.random() * actions.length)];
        
        const notif = document.getElementById('liveNotification');
        const text = document.getElementById('liveNotifText');
        text.textContent = `${name} de ${city} ${action}`;
        
        notif.classList.add('show');
        setTimeout(() => notif.classList.remove('show'), 5000);
    }
    
    setTimeout(showNotification, 3000);
    setInterval(showNotification, 15000 + Math.random() * 10000);
})();
"""

    # ========================================
    # LIVE QUESTIONS
    # ========================================
    def _get_live_questions_css(self) -> str:
        style = self.config.live_questions_style
        base_css = """
/* Live Questions Widget */
.live-questions-section {
    padding: 40px 20px;
    background: linear-gradient(180deg, rgba(139,92,246,0.1) 0%, transparent 100%);
}
.live-questions-container { max-width: 800px; margin: 0 auto; }
.live-questions-title {
    text-align: center;
    font-size: 1.75rem;
    font-weight: 700;
    color: white;
    margin-bottom: 30px;
}
.live-question-item {
    background: rgba(30,27,75,0.8);
    border: 1px solid rgba(139,92,246,0.3);
    border-radius: 12px;
    margin-bottom: 15px;
    overflow: hidden;
}
.live-question-q {
    padding: 16px 20px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #e0e7ff;
    font-weight: 600;
}
.live-question-q:hover { background: rgba(139,92,246,0.1); }
.live-question-a {
    padding: 0 20px;
    max-height: 0;
    overflow: hidden;
    transition: all 0.3s ease;
    color: #a78bfa;
}
.live-question-item.open .live-question-a { max-height: 200px; padding: 16px 20px; }
.live-question-item.open .live-question-arrow { transform: rotate(180deg); }
.live-question-arrow { transition: transform 0.3s; }
"""
        if style == "chat":
            base_css += """
.live-question-item { border-radius: 18px 18px 18px 4px; background: linear-gradient(135deg, #312e81, #1e1b4b); }
.live-question-q::before { content: '💬'; margin-right: 10px; }
"""
        elif style == "cards":
            base_css += """
.live-questions-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
.live-question-item { height: 100%; }
.live-question-a { max-height: none !important; padding: 16px 20px !important; }
"""
        return base_css
    
    def _get_live_questions_html(self) -> str:
        questions_html = ""
        for i, q in enumerate(self.config.live_questions):
            questions_html += f"""
<div class="live-question-item" data-q="{i}">
    <div class="live-question-q" onclick="this.parentElement.classList.toggle('open')">
        <span>{q.get('q', '')}</span>
        <span class="live-question-arrow">▼</span>
    </div>
    <div class="live-question-a">{q.get('a', '')}</div>
</div>
"""
        return f"""
<!-- Live Questions Section -->
<section class="live-questions-section">
    <div class="live-questions-container">
        <h2 class="live-questions-title">🔮 Preguntas Frecuentes</h2>
        {questions_html}
    </div>
</section>
"""
    
    def _get_live_questions_js(self) -> str:
        return ""  # Questions work with CSS only

    # ========================================
    # HYPNOTIC TEXTS
    # ========================================
    def _get_hypnotic_texts_css(self) -> str:
        return """
/* Hypnotic Texts Widget */
.hypnotic-section {
    padding: 60px 20px;
    background: linear-gradient(180deg, rgba(139,92,246,0.15) 0%, transparent 100%);
    text-align: center;
}
.hypnotic-container { max-width: 800px; margin: 0 auto; }
.hypnotic-message {
    font-size: 1.5rem;
    color: #c4b5fd;
    font-style: italic;
    padding: 20px 30px;
    background: rgba(30,27,75,0.5);
    border-left: 4px solid #8b5cf6;
    border-radius: 0 12px 12px 0;
    margin-bottom: 20px;
    opacity: 0;
    transform: translateY(20px);
    animation: fadeInUp 0.8s ease forwards;
}
.hypnotic-message:nth-child(1) { animation-delay: 0.2s; }
.hypnotic-message:nth-child(2) { animation-delay: 0.5s; }
.hypnotic-message:nth-child(3) { animation-delay: 0.8s; }
@keyframes fadeInUp {
    to { opacity: 1; transform: translateY(0); }
}
@media (max-width: 640px) {
    .hypnotic-message { font-size: 1.1rem; padding: 15px 20px; }
}
"""
    
    def _get_hypnotic_texts_html(self) -> str:
        messages_html = ""
        for msg in self.config.hypnotic_messages[:3]:
            messages_html += f'<div class="hypnotic-message">"{msg}"</div>\n'
        return f"""
<!-- Hypnotic Texts Section -->
<section class="hypnotic-section">
    <div class="hypnotic-container">
        {messages_html}
    </div>
</section>
"""
    
    def _get_hypnotic_texts_js(self) -> str:
        return ""  # Animations work with CSS only

    # ========================================
    # TYPING EFFECT
    # ========================================
    def _get_typing_effect_css(self) -> str:
        style = self.config.typing_effect_style
        base_css = """
/* Typing Effect Widget */
.typing-indicator {
    position: fixed;
    bottom: 160px;
    right: 20px;
    background: linear-gradient(135deg, #1e1b4b, #312e81);
    border: 1px solid rgba(139,92,246,0.3);
    border-radius: 20px 20px 4px 20px;
    padding: 12px 18px;
    display: flex;
    align-items: center;
    gap: 10px;
    z-index: 9996;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    opacity: 0;
    transform: translateY(20px);
    transition: all 0.4s ease;
}
.typing-indicator.show { opacity: 1; transform: translateY(0); }
.typing-dots { display: flex; gap: 4px; }
.typing-dot {
    width: 8px; height: 8px;
    background: #8b5cf6;
    border-radius: 50%;
    animation: typingBounce 1.4s infinite ease-in-out;
}
.typing-dot:nth-child(1) { animation-delay: 0s; }
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes typingBounce {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
    40% { transform: scale(1); opacity: 1; }
}
.typing-text { color: #c4b5fd; font-size: 13px; }
@media (max-width: 640px) {
    .typing-indicator { right: 10px; left: 10px; bottom: 100px; }
}
"""
        if style == "ios":
            base_css += """
.typing-indicator { background: #e5e5ea; border: none; }
.typing-text { color: #8e8e93; }
.typing-dot { background: #8e8e93; }
"""
        elif style == "badge":
            base_css += """
.typing-indicator { border-radius: 30px; padding: 8px 16px; }
"""
        return base_css
    
    def _get_typing_effect_html(self) -> str:
        return """
<!-- Typing Effect Indicator -->
<div class="typing-indicator" id="typingIndicator">
    <div class="typing-dots">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
    </div>
    <span class="typing-text" id="typingText">Un experto está escribiendo...</span>
</div>
"""
    
    def _get_typing_effect_js(self) -> str:
        messages_json = json.dumps(self.config.typing_messages)
        return f"""
// Typing Effect Logic
(function() {{
    const messages = {messages_json};
    let idx = 0;
    
    function showTyping() {{
        const indicator = document.getElementById('typingIndicator');
        const text = document.getElementById('typingText');
        text.textContent = messages[idx % messages.length];
        idx++;
        
        indicator.classList.add('show');
        setTimeout(() => indicator.classList.remove('show'), 4000);
    }}
    
    setTimeout(showTyping, 5000);
    setInterval(showTyping, 20000);
}})();
"""


# ========================================
# HELPER FUNCTION FOR EASY USE
# ========================================
def inject_widgets(html: str, config: Dict[str, Any]) -> str:
    """
    Función helper para inyectar widgets fácilmente.
    
    Args:
        html: HTML original
        config: Diccionario con configuración de widgets
    
    Returns:
        HTML con widgets inyectados
    
    Ejemplo:
        config = {
            'whatsapp_number': '+573001234567',
            'show_sticky_bars': True,
            'show_vibrating_button': True,
            'sticky_bars_style': 'mystical'
        }
        html_with_widgets = inject_widgets(original_html, config)
    """
    widget_config = WidgetConfig(**{k: v for k, v in config.items() if hasattr(WidgetConfig, k) or k in WidgetConfig.__dataclass_fields__})
    injector = WidgetsInjector(widget_config)
    return injector.inject(html)
