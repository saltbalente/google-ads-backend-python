"""
Landing Page Quality Assurance Module
=====================================
Sistema de validación y calidad para landing pages enterprise.
Garantiza que cada landing generada cumpla con estándares de calidad.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Niveles de calidad de la landing page"""
    CRITICAL = "critical"    # Errores que impiden el funcionamiento
    WARNING = "warning"      # Problemas que afectan la calidad
    INFO = "info"           # Sugerencias de mejora


@dataclass
class QualityIssue:
    """Representa un problema de calidad detectado"""
    level: QualityLevel
    category: str
    message: str
    suggestion: str = ""
    location: str = ""


@dataclass
class QualityReport:
    """Reporte completo de calidad de una landing page"""
    is_valid: bool
    score: int  # 0-100
    issues: List[QualityIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def add_issue(self, level: QualityLevel, category: str, message: str, 
                  suggestion: str = "", location: str = ""):
        self.issues.append(QualityIssue(level, category, message, suggestion, location))
    
    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.level == QualityLevel.CRITICAL)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.level == QualityLevel.WARNING)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "score": self.score,
            "critical_issues": self.critical_count,
            "warnings": self.warning_count,
            "issues": [
                {
                    "level": i.level.value,
                    "category": i.category,
                    "message": i.message,
                    "suggestion": i.suggestion,
                    "location": i.location
                }
                for i in self.issues
            ],
            "metrics": self.metrics
        }


class LandingPageValidator:
    """
    Validador de landing pages con múltiples verificaciones.
    """
    
    # Elementos esenciales que debe tener una landing page
    REQUIRED_ELEMENTS = {
        "title": "Título de la página",
        "meta_description": "Meta descripción para SEO",
        "h1": "Encabezado principal H1",
        "cta": "Botón o enlace de llamada a la acción",
        "whatsapp_link": "Enlace de WhatsApp para contacto"
    }
    
    # Patrones de WhatsApp válidos
    WHATSAPP_PATTERNS = [
        r'https://wa\.me/\d{10,15}',
        r'https://api\.whatsapp\.com/send\?phone=\d{10,15}'
    ]
    
    def __init__(self):
        self.soup = None
        self.html = ""
    
    def validate(self, html: str, config: Dict[str, Any] = None) -> QualityReport:
        """
        Realiza validación completa de una landing page.
        
        Args:
            html: Contenido HTML de la landing
            config: Configuración con valores esperados (whatsapp, gtm, etc.)
        
        Returns:
            QualityReport con todos los problemas encontrados
        """
        self.html = html
        self.soup = BeautifulSoup(html, 'html.parser')
        config = config or {}
        
        report = QualityReport(is_valid=True, score=100)
        
        # Ejecutar todas las validaciones
        self._validate_structure(report)
        self._validate_seo(report)
        self._validate_contact_info(report, config)
        self._validate_accessibility(report)
        self._validate_performance(report)
        self._validate_amp_compatibility(report)
        self._validate_content_quality(report)
        
        # Calcular score final
        report.score = self._calculate_score(report)
        report.is_valid = report.critical_count == 0
        
        return report
    
    def _validate_structure(self, report: QualityReport):
        """Valida la estructura básica del HTML"""
        
        # DOCTYPE
        if '<!doctype html>' not in self.html.lower() and '<!DOCTYPE html>' not in self.html:
            report.add_issue(
                QualityLevel.WARNING,
                "structure",
                "Falta declaración DOCTYPE",
                "Agregar <!DOCTYPE html> al inicio del documento"
            )
        
        # <html> tag
        html_tag = self.soup.find('html')
        if not html_tag:
            report.add_issue(
                QualityLevel.CRITICAL,
                "structure",
                "Falta etiqueta <html>",
                "El documento debe tener una etiqueta <html>"
            )
        elif not html_tag.get('lang'):
            report.add_issue(
                QualityLevel.WARNING,
                "structure",
                "Falta atributo lang en <html>",
                "Agregar lang='es' para accesibilidad"
            )
        
        # <head> section
        head = self.soup.find('head')
        if not head:
            report.add_issue(
                QualityLevel.CRITICAL,
                "structure",
                "Falta sección <head>",
                "El documento debe tener una sección <head>"
            )
        
        # <body> section
        body = self.soup.find('body')
        if not body:
            report.add_issue(
                QualityLevel.CRITICAL,
                "structure",
                "Falta sección <body>",
                "El documento debe tener una sección <body>"
            )
        
        # Charset
        charset = self.soup.find('meta', charset=True) or \
                  self.soup.find('meta', attrs={'http-equiv': 'Content-Type'})
        if not charset:
            report.add_issue(
                QualityLevel.WARNING,
                "structure",
                "Falta declaración de charset",
                "Agregar <meta charset='utf-8'>"
            )
        
        # Viewport
        viewport = self.soup.find('meta', attrs={'name': 'viewport'})
        if not viewport:
            report.add_issue(
                QualityLevel.WARNING,
                "structure",
                "Falta meta viewport",
                "Agregar meta viewport para diseño responsivo"
            )
    
    def _validate_seo(self, report: QualityReport):
        """Valida elementos SEO"""
        
        # Title
        title = self.soup.find('title')
        if not title or not title.string:
            report.add_issue(
                QualityLevel.CRITICAL,
                "seo",
                "Falta título de página",
                "Agregar <title> con texto descriptivo"
            )
        elif len(title.string) < 30:
            report.add_issue(
                QualityLevel.WARNING,
                "seo",
                f"Título muy corto ({len(title.string)} caracteres)",
                "El título debería tener entre 50-60 caracteres"
            )
        elif len(title.string) > 70:
            report.add_issue(
                QualityLevel.WARNING,
                "seo",
                f"Título muy largo ({len(title.string)} caracteres)",
                "El título debería tener máximo 60 caracteres"
            )
        
        report.metrics["title_length"] = len(title.string) if title and title.string else 0
        
        # Meta description
        meta_desc = self.soup.find('meta', attrs={'name': 'description'})
        if not meta_desc or not meta_desc.get('content'):
            report.add_issue(
                QualityLevel.CRITICAL,
                "seo",
                "Falta meta descripción",
                "Agregar meta description para SEO"
            )
        else:
            desc_len = len(meta_desc.get('content', ''))
            if desc_len < 120:
                report.add_issue(
                    QualityLevel.WARNING,
                    "seo",
                    f"Meta descripción muy corta ({desc_len} caracteres)",
                    "La descripción debería tener entre 150-160 caracteres"
                )
            elif desc_len > 170:
                report.add_issue(
                    QualityLevel.WARNING,
                    "seo",
                    f"Meta descripción muy larga ({desc_len} caracteres)",
                    "La descripción debería tener máximo 160 caracteres"
                )
            report.metrics["description_length"] = desc_len
        
        # H1
        h1_tags = self.soup.find_all('h1')
        if len(h1_tags) == 0:
            report.add_issue(
                QualityLevel.CRITICAL,
                "seo",
                "Falta encabezado H1",
                "Agregar un encabezado H1 principal"
            )
        elif len(h1_tags) > 1:
            report.add_issue(
                QualityLevel.WARNING,
                "seo",
                f"Múltiples H1 encontrados ({len(h1_tags)})",
                "Debería haber solo un H1 por página"
            )
        
        report.metrics["h1_count"] = len(h1_tags)
        
        # Open Graph tags
        og_title = self.soup.find('meta', property='og:title')
        og_desc = self.soup.find('meta', property='og:description')
        if not og_title:
            report.add_issue(
                QualityLevel.INFO,
                "seo",
                "Falta og:title",
                "Agregar Open Graph para mejor sharing en redes sociales"
            )
        if not og_desc:
            report.add_issue(
                QualityLevel.INFO,
                "seo",
                "Falta og:description",
                "Agregar Open Graph description"
            )
        
        # Canonical URL
        canonical = self.soup.find('link', rel='canonical')
        if not canonical:
            report.add_issue(
                QualityLevel.INFO,
                "seo",
                "Falta URL canónica",
                "Agregar link rel='canonical' para evitar contenido duplicado"
            )
    
    def _validate_contact_info(self, report: QualityReport, config: Dict[str, Any]):
        """Valida información de contacto"""
        
        expected_whatsapp = config.get("whatsapp_number", "")
        expected_phone = config.get("phone_number", expected_whatsapp)
        expected_gtm = config.get("gtm_id", "")
        
        # WhatsApp links
        whatsapp_links = []
        for pattern in self.WHATSAPP_PATTERNS:
            whatsapp_links.extend(re.findall(pattern, self.html))
        
        if not whatsapp_links:
            report.add_issue(
                QualityLevel.CRITICAL,
                "contact",
                "No se encontraron enlaces de WhatsApp",
                "Agregar enlace wa.me o api.whatsapp.com"
            )
        else:
            report.metrics["whatsapp_links_count"] = len(whatsapp_links)
            
            # Verificar que el número sea el correcto
            if expected_whatsapp:
                clean_expected = expected_whatsapp.replace("+", "").replace(" ", "").replace("-", "")
                correct_links = sum(1 for link in whatsapp_links if clean_expected in link)
                if correct_links == 0:
                    report.add_issue(
                        QualityLevel.CRITICAL,
                        "contact",
                        f"WhatsApp no coincide con el número esperado ({expected_whatsapp})",
                        "Verificar que el número de WhatsApp sea correcto"
                    )
        
        # Phone links
        phone_links = re.findall(r'href="tel:[^"]*"', self.html)
        report.metrics["phone_links_count"] = len(phone_links)
        
        # GTM
        if expected_gtm:
            if expected_gtm not in self.html:
                report.add_issue(
                    QualityLevel.WARNING,
                    "tracking",
                    f"GTM ID {expected_gtm} no encontrado",
                    "Verificar que el código de GTM esté correctamente insertado"
                )
            else:
                report.metrics["gtm_present"] = True
        
        # CTA buttons
        cta_elements = self.soup.find_all(['a', 'button'], class_=lambda c: c and any(
            x in str(c).lower() for x in ['cta', 'button', 'whatsapp', 'contact', 'consulta', 'llamar']
        ))
        report.metrics["cta_count"] = len(cta_elements)
        
        if len(cta_elements) == 0:
            report.add_issue(
                QualityLevel.WARNING,
                "conversion",
                "No se detectaron botones CTA claros",
                "Agregar botones con clases descriptivas como 'cta-button'"
            )
        elif len(cta_elements) < 2:
            report.add_issue(
                QualityLevel.INFO,
                "conversion",
                "Pocos CTAs detectados",
                "Considerar agregar más CTAs a lo largo de la página"
            )
    
    def _validate_accessibility(self, report: QualityReport):
        """Valida accesibilidad básica"""
        
        # Images without alt
        images = self.soup.find_all(['img', 'amp-img'])
        images_without_alt = [img for img in images if not img.get('alt')]
        
        if images_without_alt:
            report.add_issue(
                QualityLevel.WARNING,
                "accessibility",
                f"{len(images_without_alt)} imágenes sin atributo alt",
                "Agregar texto alt descriptivo a todas las imágenes"
            )
        
        report.metrics["images_count"] = len(images)
        report.metrics["images_without_alt"] = len(images_without_alt)
        
        # Links without href or with empty href
        links = self.soup.find_all('a')
        broken_links = [a for a in links if not a.get('href') or a.get('href') in ['#', 'javascript:void(0)']]
        
        if len(broken_links) > 2:  # Algunos # links son normales para navegación
            report.add_issue(
                QualityLevel.WARNING,
                "accessibility",
                f"{len(broken_links)} enlaces sin destino válido",
                "Revisar enlaces con href vacío o '#'"
            )
        
        # Form inputs without labels
        inputs = self.soup.find_all('input')
        for inp in inputs:
            if inp.get('type') not in ['hidden', 'submit', 'button']:
                inp_id = inp.get('id')
                if inp_id:
                    label = self.soup.find('label', attrs={'for': inp_id})
                    if not label and not inp.get('aria-label'):
                        report.add_issue(
                            QualityLevel.INFO,
                            "accessibility",
                            f"Input '{inp_id}' sin label asociado",
                            "Agregar <label for=''> o aria-label"
                        )
    
    def _validate_performance(self, report: QualityReport):
        """Valida aspectos de rendimiento"""
        
        html_size = len(self.html.encode('utf-8'))
        report.metrics["html_size_bytes"] = html_size
        report.metrics["html_size_kb"] = round(html_size / 1024, 2)
        
        # HTML muy grande
        if html_size > 500000:  # 500KB
            report.add_issue(
                QualityLevel.WARNING,
                "performance",
                f"HTML muy grande ({html_size // 1024}KB)",
                "Considerar optimizar el código HTML"
            )
        
        # Inline styles excesivos
        inline_styles = self.soup.find_all(style=True)
        if len(inline_styles) > 50:
            report.add_issue(
                QualityLevel.INFO,
                "performance",
                f"Muchos estilos inline ({len(inline_styles)})",
                "Considerar mover estilos a CSS externo o <style>"
            )
        
        # Scripts externos
        external_scripts = self.soup.find_all('script', src=True)
        report.metrics["external_scripts"] = len(external_scripts)
        
        if len(external_scripts) > 10:
            report.add_issue(
                QualityLevel.WARNING,
                "performance",
                f"Muchos scripts externos ({len(external_scripts)})",
                "Considerar consolidar o eliminar scripts innecesarios"
            )
    
    def _validate_amp_compatibility(self, report: QualityReport):
        """Valida compatibilidad AMP si es una página AMP"""
        
        html_tag = self.soup.find('html')
        is_amp = html_tag and ('⚡' in str(html_tag) or 'amp' in html_tag.get('class', []))
        
        report.metrics["is_amp"] = is_amp
        
        if is_amp:
            # AMP boilerplate
            if 'amp-boilerplate' not in self.html:
                report.add_issue(
                    QualityLevel.CRITICAL,
                    "amp",
                    "Falta AMP boilerplate CSS",
                    "Agregar el CSS boilerplate requerido por AMP"
                )
            
            # AMP runtime
            if 'cdn.ampproject.org/v0.js' not in self.html:
                report.add_issue(
                    QualityLevel.CRITICAL,
                    "amp",
                    "Falta AMP runtime script",
                    "Agregar <script src='https://cdn.ampproject.org/v0.js'>"
                )
            
            # No custom JavaScript in AMP
            custom_scripts = self.soup.find_all('script', src=False)
            for script in custom_scripts:
                if script.string and 'application/ld+json' not in str(script.get('type', '')):
                    if 'gtm' not in script.string.lower() and 'amp' not in script.string.lower():
                        report.add_issue(
                            QualityLevel.WARNING,
                            "amp",
                            "Script inline detectado en página AMP",
                            "AMP no permite JavaScript personalizado"
                        )
                        break
            
            # Check for forbidden tags in AMP
            forbidden_tags = ['img', 'video', 'audio', 'iframe', 'frame', 'frameset', 'object', 'param', 'applet', 'embed']
            for tag in forbidden_tags:
                if tag == 'img':
                    # img is allowed but should be amp-img
                    regular_imgs = self.soup.find_all('img')
                    if regular_imgs:
                        report.add_issue(
                            QualityLevel.CRITICAL,
                            "amp",
                            f"Encontradas {len(regular_imgs)} etiquetas <img>",
                            "Usar <amp-img> en lugar de <img> para AMP"
                        )
    
    def _validate_content_quality(self, report: QualityReport):
        """Valida calidad del contenido"""
        
        # Texto total
        text = self.soup.get_text(separator=' ', strip=True)
        word_count = len(text.split())
        report.metrics["word_count"] = word_count
        
        if word_count < 200:
            report.add_issue(
                QualityLevel.WARNING,
                "content",
                f"Contenido muy corto ({word_count} palabras)",
                "Agregar más contenido para mejor SEO"
            )
        
        # Verificar que no hay placeholders obvios
        placeholder_patterns = [
            r'\{\{[^}]+\}\}',  # Jinja2 templates no procesados
            r'\[\s*PLACEHOLDER\s*\]',
            r'Lorem ipsum',
            r'XXX',
            r'\$\{[^}]+\}'  # JavaScript templates
        ]
        
        for pattern in placeholder_patterns:
            matches = re.findall(pattern, self.html, re.IGNORECASE)
            if matches:
                report.add_issue(
                    QualityLevel.CRITICAL,
                    "content",
                    f"Placeholder no procesado encontrado: {matches[0]}",
                    "Verificar que todo el contenido dinámico se procesó correctamente"
                )
        
        # Verificar contenido duplicado obvio
        paragraphs = self.soup.find_all('p')
        paragraph_texts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
        
        if len(paragraph_texts) != len(set(paragraph_texts)):
            report.add_issue(
                QualityLevel.WARNING,
                "content",
                "Se detectó contenido duplicado",
                "Revisar párrafos repetidos"
            )
    
    def _calculate_score(self, report: QualityReport) -> int:
        """Calcula score final basado en issues encontrados"""
        score = 100
        
        for issue in report.issues:
            if issue.level == QualityLevel.CRITICAL:
                score -= 20
            elif issue.level == QualityLevel.WARNING:
                score -= 5
            elif issue.level == QualityLevel.INFO:
                score -= 1
        
        return max(0, score)


class LandingPageSanitizer:
    """
    Sanitiza y corrige problemas comunes en landing pages.
    """
    
    def sanitize(self, html: str, config: Dict[str, Any] = None) -> Tuple[str, List[str]]:
        """
        Sanitiza el HTML corrigiendo problemas comunes.
        
        Returns:
            Tuple de (HTML corregido, lista de correcciones aplicadas)
        """
        config = config or {}
        corrections = []
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Asegurar DOCTYPE
        if '<!doctype html>' not in html.lower():
            html = '<!DOCTYPE html>\n' + html
            corrections.append("Agregado DOCTYPE")
        
        # 2. Asegurar charset
        head = soup.find('head')
        if head and not soup.find('meta', charset=True):
            charset_tag = soup.new_tag('meta', charset='utf-8')
            head.insert(0, charset_tag)
            corrections.append("Agregado charset UTF-8")
        
        # 3. Asegurar viewport
        if head and not soup.find('meta', attrs={'name': 'viewport'}):
            viewport_tag = soup.new_tag('meta', attrs={
                'name': 'viewport',
                'content': 'width=device-width, initial-scale=1, minimum-scale=1'
            })
            head.append(viewport_tag)
            corrections.append("Agregado meta viewport")
        
        # 4. Asegurar lang en html
        html_tag = soup.find('html')
        if html_tag and not html_tag.get('lang'):
            html_tag['lang'] = 'es'
            corrections.append("Agregado lang='es' a html")
        
        # 5. Limpiar scripts vacíos
        for script in soup.find_all('script'):
            if not script.get('src') and not script.string:
                script.decompose()
                corrections.append("Eliminado script vacío")
        
        # 6. Asegurar alt en imágenes
        for img in soup.find_all(['img', 'amp-img']):
            if not img.get('alt'):
                img['alt'] = 'Imagen'
                corrections.append(f"Agregado alt genérico a imagen")
        
        if corrections:
            html = str(soup)
        
        return html, corrections


def validate_landing_page(html: str, config: Dict[str, Any] = None) -> QualityReport:
    """
    Función de conveniencia para validar una landing page.
    
    Args:
        html: Contenido HTML
        config: Configuración con valores esperados
    
    Returns:
        QualityReport con resultados de validación
    """
    validator = LandingPageValidator()
    return validator.validate(html, config)


def sanitize_landing_page(html: str, config: Dict[str, Any] = None) -> Tuple[str, QualityReport]:
    """
    Sanitiza y valida una landing page.
    
    Returns:
        Tuple de (HTML sanitizado, QualityReport)
    """
    sanitizer = LandingPageSanitizer()
    sanitized_html, corrections = sanitizer.sanitize(html, config)
    
    if corrections:
        logger.info(f"🔧 Aplicadas {len(corrections)} correcciones automáticas")
        for c in corrections:
            logger.debug(f"  - {c}")
    
    validator = LandingPageValidator()
    report = validator.validate(sanitized_html, config)
    
    return sanitized_html, report
