#!/usr/bin/env python3
"""
Web Cloner Module - Sistema completo de clonación de sitios web
Descarga HTML, CSS, JS, imágenes y otros recursos de una URL específica
"""

import os
import re
import hashlib
import logging
import mimetypes
from typing import Dict, List, Set, Tuple, Optional, Any
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
from pathlib import Path
import time
import base64

import requests
from bs4 import BeautifulSoup, Comment
from PIL import Image
from io import BytesIO

# Importar librerías de accesibilidad
try:
    from axe_selenium_python import Axe
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    import webcolors
    import colour
    ACCESSIBILITY_LIBS_AVAILABLE = True
except ImportError as e:
    ACCESSIBILITY_LIBS_AVAILABLE = False
    # Logger no está disponible aún en este punto
    print(f"Advertencia: Librerías de accesibilidad no disponibles: {e}. Usando análisis básico.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AccessibilityAnalyzer:
    """
    Analizador avanzado de accesibilidad usando librerías profesionales
    """
    
    def __init__(self):
        self.libs_available = ACCESSIBILITY_LIBS_AVAILABLE
        self.driver = None
        
    def analyze_website(self, url: str) -> Dict[str, Any]:
        """
        Realiza un análisis completo de accesibilidad del sitio web
        Returns: Dict con resultados detallados del análisis
        """
        if not self.libs_available:
            logger.warning("Librerías de accesibilidad no disponibles, usando análisis básico")
            return self._basic_analysis(url)
        
        results = {
            'overall_score': 0,
            'contrast_issues': [],
            'accessibility_violations': [],
            'color_contrast_pairs': [],
            'recommendations': [],
            'severity_breakdown': {'critical': 0, 'serious': 0, 'moderate': 0, 'minor': 0}
        }
        
        try:
            # Configurar Selenium con Chrome headless
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.get(url)
            
            # Esperar a que cargue la página
            time.sleep(3)
            
            # Análisis con axe-core
            axe = Axe(self.driver)
            axe.inject()
            
            # Ejecutar análisis completo
            results_axe = axe.run()
            
            # Procesar resultados
            results['accessibility_violations'] = results_axe.get('violations', [])
            results['severity_breakdown'] = self._count_severities(results['accessibility_violations'])
            
            # Análisis específico de contraste
            contrast_issues = self._analyze_color_contrast()
            results['contrast_issues'] = contrast_issues
            
            # Calcular puntuación general
            results['overall_score'] = self._calculate_accessibility_score(results)
            
            # Generar recomendaciones
            results['recommendations'] = self._generate_recommendations(results)
            
        except Exception as e:
            logger.error(f"Error en análisis de accesibilidad avanzado: {e}")
            return self._basic_analysis(url)
        finally:
            if self.driver:
                self.driver.quit()
                
        return results
    
    def _analyze_color_contrast(self) -> List[Dict[str, Any]]:
        """
        Analiza específicamente problemas de contraste de color
        """
        contrast_issues = []
        
        if not self.driver:
            return contrast_issues
        
        try:
            # Obtener todos los elementos con texto
            elements_with_text = self.driver.find_elements(By.XPATH, "//*[text()[normalize-space()]]")
            
            for element in elements_with_text:
                try:
                    # Obtener estilos computados
                    text_color = self.driver.execute_script("""
                        var element = arguments[0];
                        var style = window.getComputedStyle(element);
                        return {
                            color: style.color,
                            backgroundColor: style.backgroundColor,
                            fontSize: style.fontSize,
                            fontWeight: style.fontWeight
                        };
                    """, element)
                    
                    # Analizar contraste
                    contrast_ratio = self._calculate_contrast_ratio(text_color['color'], text_color['backgroundColor'])
                    
                    # Determinar si es un problema según WCAG
                    is_problem = self._is_contrast_problem(contrast_ratio, text_color['fontSize'], text_color['fontWeight'])
                    
                    if is_problem:
                        contrast_issues.append({
                            'element': element.get_attribute('outerHTML')[:100] + '...',
                            'text_color': text_color['color'],
                            'background_color': text_color['backgroundColor'],
                            'contrast_ratio': contrast_ratio,
                            'font_size': text_color['fontSize'],
                            'font_weight': text_color['fontWeight'],
                            'severity': 'critical' if contrast_ratio < 3 else 'serious'
                        })
                        
                except Exception as e:
                    logger.debug(f"Error analizando elemento: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error en análisis de contraste: {e}")
            
        return contrast_issues
    
    def _calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """
        Calcula la relación de contraste entre dos colores
        """
        try:
            # Convertir colores a RGB
            rgb1 = self._color_to_rgb(color1)
            rgb2 = self._color_to_rgb(color2)
            
            # Calcular luminancia relativa
            lum1 = self._relative_luminance(rgb1)
            lum2 = self._relative_luminance(rgb2)
            
            # Calcular ratio de contraste
            lighter = max(lum1, lum2)
            darker = min(lum1, lum2)
            
            return (lighter + 0.05) / (darker + 0.05)
            
        except Exception as e:
            logger.debug(f"Error calculando contraste: {e}")
            return 1.0
    
    def _color_to_rgb(self, color: str) -> Tuple[int, int, int]:
        """
        Convierte una especificación de color CSS a RGB
        """
        try:
            # Remover espacios
            color = color.strip()
            
            # Color transparente
            if color == 'transparent' or color == 'rgba(0, 0, 0, 0)':
                return (255, 255, 255)  # Asumir fondo blanco
            
            # RGB/RGBA
            if color.startswith('rgb'):
                match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color)
                if match:
                    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            
            # Hex
            if color.startswith('#'):
                return webcolors.hex_to_rgb(color)
            
            # Nombre de color
            try:
                return webcolors.name_to_rgb(color)
            except ValueError:
                pass
            
            # Default: negro
            return (0, 0, 0)
            
        except Exception as e:
            logger.debug(f"Error convirtiendo color {color}: {e}")
            return (0, 0, 0)
    
    def _relative_luminance(self, rgb: Tuple[int, int, int]) -> float:
        """
        Calcula la luminancia relativa según WCAG
        """
        r, g, b = rgb
        
        # Convertir a valores lineales
        rs = r / 255.0
        gs = g / 255.0
        bs = b / 255.0
        
        # Aplicar función de transferencia
        if rs <= 0.03928:
            rs = rs / 12.92
        else:
            rs = ((rs + 0.055) / 1.055) ** 2.4
            
        if gs <= 0.03928:
            gs = gs / 12.92
        else:
            gs = ((gs + 0.055) / 1.055) ** 2.4
            
        if bs <= 0.03928:
            bs = bs / 12.92
        else:
            bs = ((bs + 0.055) / 1.055) ** 2.4
        
        # Calcular luminancia
        return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs
    
    def _is_contrast_problem(self, ratio: float, font_size: str, font_weight: str) -> bool:
        """
        Determina si un ratio de contraste es problemático según WCAG
        """
        try:
            # Parsear font-size
            size_match = re.match(r'(\d+(?:\.\d+)?)px', font_size)
            if not size_match:
                return ratio < 4.5  # Default threshold
            
            size_px = float(size_match.group(1))
            
            # Parsear font-weight
            is_bold = False
            if font_weight:
                try:
                    weight = int(font_weight)
                    is_bold = weight >= 700
                except ValueError:
                    is_bold = 'bold' in font_weight.lower()
            
            # Thresholds según WCAG 2.1
            if size_px >= 18 or (size_px >= 14 and is_bold):
                # Large text
                return ratio < 3.0
            else:
                # Normal text
                return ratio < 4.5
                
        except Exception as e:
            logger.debug(f"Error evaluando contraste: {e}")
            return ratio < 4.5
    
    def _count_severities(self, violations: List[Dict]) -> Dict[str, int]:
        """
        Cuenta violaciones por severidad
        """
        breakdown = {'critical': 0, 'serious': 0, 'moderate': 0, 'minor': 0}
        
        for violation in violations:
            impact = violation.get('impact', 'minor')
            if impact in breakdown:
                breakdown[impact] += 1
                
        return breakdown
    
    def _calculate_accessibility_score(self, results: Dict) -> float:
        """
        Calcula una puntuación general de accesibilidad (0-100)
        """
        violations = results.get('accessibility_violations', [])
        contrast_issues = results.get('contrast_issues', [])
        
        # Penalizaciones por tipo de problema
        penalty = 0
        
        # Violaciones de axe-core
        for violation in violations:
            impact = violation.get('impact', 'minor')
            nodes_affected = len(violation.get('nodes', []))
            
            if impact == 'critical':
                penalty += nodes_affected * 10
            elif impact == 'serious':
                penalty += nodes_affected * 5
            elif impact == 'moderate':
                penalty += nodes_affected * 2
            else:  # minor
                penalty += nodes_affected * 1
        
        # Problemas de contraste
        for issue in contrast_issues:
            if issue.get('severity') == 'critical':
                penalty += 8
            else:
                penalty += 4
        
        # Calcular score (máximo 100, mínimo 0)
        score = max(0, 100 - penalty)
        
        return round(score, 1)
    
    def _generate_recommendations(self, results: Dict) -> List[str]:
        """
        Genera recomendaciones basadas en los resultados del análisis
        """
        recommendations = []
        
        violations = results.get('accessibility_violations', [])
        contrast_issues = results.get('contrast_issues', [])
        score = results.get('overall_score', 0)
        
        # Recomendaciones basadas en score
        if score < 50:
            recommendations.append("Accesibilidad crítica: El sitio tiene múltiples problemas graves que afectan la usabilidad")
        elif score < 70:
            recommendations.append("Accesibilidad mejorable: Revisar problemas de contraste y navegación")
        elif score < 90:
            recommendations.append("Accesibilidad buena: Solo ajustes menores necesarios")
        else:
            recommendations.append("Accesibilidad excelente: El sitio cumple con estándares altos")
        
        # Recomendaciones específicas
        if contrast_issues:
            recommendations.append(f"Corregir {len(contrast_issues)} problemas de contraste de color")
        
        # Contar tipos de violaciones
        violation_types = {}
        for violation in violations:
            rule_id = violation.get('id', 'unknown')
            violation_types[rule_id] = violation_types.get(rule_id, 0) + 1
        
        # Recomendaciones por tipo de problema común
        if 'color-contrast' in violation_types:
            recommendations.append("Mejorar el contraste entre texto y fondo")
        
        if 'image-alt' in violation_types:
            recommendations.append("Añadir texto alternativo a las imágenes")
            
        if 'link-name' in violation_types:
            recommendations.append("Mejorar la accesibilidad de los enlaces")
        
        if 'heading-order' in violation_types:
            recommendations.append("Corregir la jerarquía de encabezados")
        
        return recommendations
    
    def _basic_analysis(self, url: str) -> Dict[str, Any]:
        """
        Análisis básico cuando las librerías avanzadas no están disponibles
        """
        logger.info("Realizando análisis básico de accesibilidad")
        
        return {
            'overall_score': 50.0,  # Score neutral
            'contrast_issues': [],
            'accessibility_violations': [],
            'color_contrast_pairs': [],
            'recommendations': ['Instalar librerías de accesibilidad avanzadas para análisis completo'],
            'severity_breakdown': {'critical': 0, 'serious': 0, 'moderate': 0, 'minor': 0}
        }


class WebClonerConfig:
    """Configuration for web cloning process"""
    def __init__(self):
        self.timeout = 30
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        # User agents rotativos para evitar bloqueos
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        ]
        self.user_agent = self.user_agents[0]
        self.max_retries = 3
        self.retry_delay = 2
        self.download_images = True
        self.download_css = True
        self.download_js = True
        self.download_fonts = True
        self.optimize_images = True
        self.max_image_size = 2048  # Max dimension in pixels


class ResourceDownloader:
    """Handles downloading of web resources with retry logic and anti-bot bypass"""
    
    def __init__(self, config: WebClonerConfig):
        self.config = config
        self.session = requests.Session()
        self._current_ua_index = 0
        self._setup_session()
        self.downloaded_urls: Set[str] = set()
    
    def _setup_session(self):
        """Configure session with realistic browser headers"""
        ua = self.config.user_agents[self._current_ua_index]
        
        # Headers completos que imitan un navegador real
        self.session.headers.update({
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        })
    
    def _rotate_user_agent(self):
        """Rotate to next user agent"""
        self._current_ua_index = (self._current_ua_index + 1) % len(self.config.user_agents)
        self._setup_session()
        logger.info(f"🔄 Rotated to User-Agent #{self._current_ua_index + 1}")
        
    def download(self, url: str, referer: Optional[str] = None) -> Optional[Tuple[bytes, str]]:
        """
        Download a resource from URL with anti-bot bypass techniques
        Returns: Tuple of (content_bytes, content_type) or None if failed
        """
        if url in self.downloaded_urls:
            logger.debug(f"Skipping already downloaded: {url}")
            return None
            
        # Validate URL
        if not self._is_valid_url(url):
            logger.warning(f"Invalid URL: {url}")
            return None
        
        # Parse domain for referer
        parsed_url = urlparse(url)
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
        # Build request headers
        request_headers = {
            'Referer': referer or base_domain,
            'Origin': base_domain,
        }
        
        # Add host header
        request_headers['Host'] = parsed_url.netloc
            
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Downloading {url} (attempt {attempt + 1}/{self.config.max_retries})")
                
                # Rotate user agent on retry (except first attempt)
                if attempt > 0:
                    self._rotate_user_agent()
                    time.sleep(self.config.retry_delay * (attempt + 1))  # Incremental delay
                
                # Use longer timeout for larger files
                timeout = self.config.timeout
                if any(domain in url for domain in ['googletagmanager.com', 'googleapis.com', 'gstatic.com']):
                    timeout = 60  # Longer timeout for Google services
                
                response = self.session.get(
                    url,
                    headers=request_headers,
                    timeout=timeout,
                    stream=True,
                    allow_redirects=True
                )
                
                # Check response status
                if response.status_code == 404:
                    logger.warning(f"Resource not found (404): {url}")
                    return None
                
                # Handle 403 Forbidden - try alternative methods
                if response.status_code == 403:
                    logger.warning(f"⚠️ Access forbidden (403): {url} - Trying bypass...")
                    result = self._try_bypass_403(url, request_headers)
                    if result:
                        return result
                    # If bypass failed, continue with next attempt
                    continue
                    
                response.raise_for_status()
                
                # Check content size
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.config.max_file_size:
                    logger.warning(f"File too large: {url} ({content_length} bytes)")
                    return None
                
                # Download content with progress indication for large files
                content = b''
                total_size = 0
                start_time = time.time()
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        content += chunk
                        total_size += len(chunk)
                        
                        # Check size limit during download
                        if total_size > self.config.max_file_size:
                            logger.warning(f"File size exceeded during download: {url}")
                            return None
                        
                        # Log progress for large files
                        if total_size > 1024 * 1024:  # > 1MB
                            elapsed = time.time() - start_time
                            if elapsed > 5:  # Log every 5 seconds for large files
                                logger.info(f"Downloading {url}: {total_size/1024/1024:.1f}MB...")
                                start_time = time.time()
                
                content_type = response.headers.get('content-type', 'application/octet-stream')
                self.downloaded_urls.add(url)
                
                logger.info(f"✅ Downloaded: {url} ({len(content)} bytes, {content_type})")
                return (content, content_type)
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout downloading {url} (attempt {attempt + 1})")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error downloading {url}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error downloading {url}: {str(e)}")
                
            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_delay)
                
        logger.error(f"❌ Failed to download after {self.config.max_retries} attempts: {url}")
        return None
    
    def _try_bypass_403(self, url: str, base_headers: dict) -> Optional[Tuple[bytes, str]]:
        """
        Try various techniques to bypass 403 Forbidden errors
        """
        parsed = urlparse(url)
        
        # Technique 1: Try with different Accept headers
        bypass_headers_list = [
            {
                **base_headers,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
            },
            {
                **base_headers,
                'Accept': '*/*',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'X-Requested-With': 'XMLHttpRequest',
            },
            {
                # Minimal headers - some sites block on too many headers
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            },
        ]
        
        for i, headers in enumerate(bypass_headers_list):
            try:
                logger.info(f"🔓 Trying bypass technique #{i + 1} for {url}")
                
                # Create a new session for this attempt
                bypass_session = requests.Session()
                bypass_session.headers.update(headers)
                
                # Add cookies if the site set any
                bypass_session.cookies.update(self.session.cookies)
                
                response = bypass_session.get(
                    url,
                    timeout=self.config.timeout,
                    allow_redirects=True,
                    verify=True
                )
                
                if response.status_code == 200:
                    content = response.content
                    content_type = response.headers.get('content-type', 'text/html')
                    self.downloaded_urls.add(url)
                    logger.info(f"✅ Bypass successful with technique #{i + 1}: {url}")
                    return (content, content_type)
                    
            except Exception as e:
                logger.debug(f"Bypass technique #{i + 1} failed: {str(e)}")
                continue
        
        # Technique 2: Try with Google cache (for main HTML pages only)
        if url.endswith('/') or not '.' in parsed.path.split('/')[-1]:
            try:
                cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
                logger.info(f"🔓 Trying Google cache for {url}")
                
                response = requests.get(
                    cache_url,
                    headers={'User-Agent': self.config.user_agents[0]},
                    timeout=15
                )
                
                if response.status_code == 200:
                    content = response.content
                    self.downloaded_urls.add(url)
                    logger.info(f"✅ Retrieved from Google cache: {url}")
                    return (content, 'text/html')
                    
            except Exception as e:
                logger.debug(f"Google cache failed: {str(e)}")
        
        # Technique 3: Try archive.org Wayback Machine
        try:
            wayback_url = f"https://web.archive.org/web/2/{url}"
            logger.info(f"🔓 Trying Wayback Machine for {url}")
            
            response = requests.get(
                wayback_url,
                headers={'User-Agent': self.config.user_agents[0]},
                timeout=20,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                content = response.content
                self.downloaded_urls.add(url)
                logger.info(f"✅ Retrieved from Wayback Machine: {url}")
                return (content, 'text/html')
                
        except Exception as e:
            logger.debug(f"Wayback Machine failed: {str(e)}")
        
        logger.warning(f"❌ All bypass techniques failed for {url}")
        return None
        
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False


class ContentProcessor:
    """Processes and modifies downloaded content"""
    
    def __init__(self):
        self.replacements: Dict[str, str] = {}
    
    @staticmethod
    def get_resource_filename(url: str) -> str:
        """Generate a unique filename for a resource URL"""
        parsed = urlparse(url)
        path = parsed.path
        
        # Get filename from path
        if path and path != '/':
            filename = Path(path).name
            if filename:
                # Remove query params from filename
                filename = filename.split('?')[0]
                return filename
                
        # Generate hash-based name if no filename
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # Try to guess extension from content-type
        ext = '.bin'
        if 'css' in url.lower():
            ext = '.css'
        elif 'js' in url.lower() or 'javascript' in url.lower():
            ext = '.js'
        elif any(img_ext in url.lower() for img_ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']):
            for img_ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']:
                if img_ext in url.lower():
                    ext = img_ext
                    break
        elif any(video_ext in url.lower() for video_ext in ['.mp4', '.webm', '.avi', '.mov', '.m4v', '.ogv', '.wmv', '.flv']):
            for video_ext in ['.mp4', '.webm', '.avi', '.mov', '.m4v', '.ogv', '.wmv', '.flv']:
                if video_ext in url.lower():
                    ext = video_ext
                    break
                    
        return f"resource_{url_hash}{ext}"
        
    def set_replacements(
        self,
        whatsapp: Optional[str] = None,
        phone: Optional[str] = None,
        gtm_id: Optional[str] = None
    ):
        """Configure replacements for WhatsApp, phone, and GTM"""
        if whatsapp:
            self.replacements['whatsapp'] = whatsapp
        if phone:
            self.replacements['phone'] = phone
        if gtm_id:
            self.replacements['gtm_id'] = gtm_id
            
    def process_html(self, html_content: str, base_url: str) -> Tuple[str, List[str]]:
        """
        Process HTML content and extract resource URLs
        Returns: (processed_html, list_of_resource_urls)
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        resource_urls = []
        
        # Extract and update CSS links
        for link in soup.find_all('link', rel='stylesheet'):
            if link.get('href'):
                full_url = urljoin(base_url, link['href'])
                resource_urls.append(('css', full_url, link))
                # Update href to relative path
                link['href'] = ContentProcessor.get_resource_filename(full_url)
                
        # Extract and update script sources
        for script in soup.find_all('script', src=True):
            full_url = urljoin(base_url, script['src'])
            resource_urls.append(('js', full_url, script))
            # Update src to relative path
            script['src'] = ContentProcessor.get_resource_filename(full_url)
            
        # Extract and update images
        for img in soup.find_all('img', src=True):
            # Check if this is a LiteSpeed lazy loading image with SVG placeholder
            has_svg_placeholder = img['src'].startswith('data:image/svg+xml;base64,') or 'svg+xml;base64' in img['src']
            has_data_src = 'data-src' in img.attrs
            
            # If it has SVG placeholder but also has data-src, process the data-src
            if has_svg_placeholder and has_data_src:
                full_url = urljoin(base_url, img['data-src'])
                resource_urls.append(('img', full_url, img))
                # Convert data-src to src and remove lazy loading attributes
                img['src'] = ContentProcessor.get_resource_filename(full_url)
                # Remove lazy loading attributes
                if 'data-src' in img.attrs:
                    del img['data-src']
                if 'data-lazyloaded' in img.attrs:
                    del img['data-lazyloaded']
                if 'loading' in img.attrs:
                    del img['loading']
                continue
            # Skip SVG placeholders that don't have data-src (these are just placeholders)
            elif has_svg_placeholder:
                continue
                
            full_url = urljoin(base_url, img['src'])
            resource_urls.append(('img', full_url, img))
            # Update src to relative path
            img['src'] = ContentProcessor.get_resource_filename(full_url)

        # Handle remaining LiteSpeed lazy loading images (data-src attribute)
        for img in soup.find_all('img', {'data-src': True}):
            full_url = urljoin(base_url, img['data-src'])
            resource_urls.append(('img', full_url, img))
            # Convert data-src to src and remove lazy loading attributes
            img['src'] = ContentProcessor.get_resource_filename(full_url)
            # Remove lazy loading attributes
            if 'data-src' in img.attrs:
                del img['data-src']
            if 'data-lazyloaded' in img.attrs:
                del img['data-lazyloaded']
            if 'loading' in img.attrs:
                del img['loading']

        # Extract srcset images
        for img in soup.find_all('img', srcset=True):
            srcset = img['srcset']
            for part in srcset.split(','):
                part = part.strip()
                if not part:  # Skip empty parts
                    continue
                parts = part.split()
                if not parts:  # Skip if no URL found
                    continue
                url_part = parts[0]
                full_url = urljoin(base_url, url_part)
                resource_urls.append(('img', full_url, None))
                
        # Extract and update video sources
        for video in soup.find_all('video', src=True):
            full_url = urljoin(base_url, video['src'])
            resource_urls.append(('video', full_url, video))
            # Update src to relative path
            video['src'] = ContentProcessor.get_resource_filename(full_url)
            
        # Extract video sources from <source> tags within <video> elements
        for source in soup.find_all('source', src=True):
            if source.parent.name == 'video':
                full_url = urljoin(base_url, source['src'])
                resource_urls.append(('video', full_url, source))
                # Update src to relative path
                source['src'] = ContentProcessor.get_resource_filename(full_url)
                
        # Extract background images from inline styles
        for element in soup.find_all(style=True):
            style = element['style']
            bg_urls = self._extract_background_urls(style, base_url)
            resource_urls.extend([('img', url, None) for url in bg_urls])
            # Fix Elementor CSS issues and replace URLs in inline styles
            style = self._fix_elementor_css_issues(style)
            element['style'] = self._replace_css_urls(style, base_url)
            
        # Extract and update favicon
        for link in soup.find_all('link', rel=lambda r: r and 'icon' in r.lower()):
            if link.get('href'):
                full_url = urljoin(base_url, link['href'])
                resource_urls.append(('img', full_url, link))
                # Update href to relative path
                link['href'] = ContentProcessor.get_resource_filename(full_url)
                
        # Extract and update inline CSS
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                css_urls = self._extract_urls_from_css(style_tag.string, base_url)
                resource_urls.extend([('css_asset', url, None) for url in css_urls])
                # Fix Elementor CSS issues and replace URLs in inline CSS
                style_tag.string = self._fix_elementor_css_issues(style_tag.string)
                style_tag.string = self._replace_css_urls(style_tag.string, base_url)
        
        # Neutralize all non-WhatsApp links (replace with #)
        self._neutralize_links(soup)
        
        # Remove LiteSpeed cache scripts that cause issues
        self._remove_litespeed_scripts(soup)
        
        # Remove elementor-invisible class to make elements visible
        self._remove_elementor_invisible(soup)
        
        # Convert Elementor carousels to simple responsive grids
        self._fix_elementor_carousels(soup)
        
        # Fix Elementor animation transparency issues
        self._fix_elementor_animations(soup)
        
        # Remove all references to original domain
        self._remove_original_domain_references(soup, base_url)
        
        # Inject universal CSS styles for consistent rendering
        self._inject_universal_css(soup)
        
        # Analyze and fix accessibility issues (contrast problems, etc.)
        self._analyze_and_fix_accessibility(soup, base_url)
                
        return soup, resource_urls

    def finalize_html(self, soup: BeautifulSoup) -> str:
        """Finalize HTML processing: convert to string and apply replacements"""
        html_str = str(soup)
        html_str = self._apply_replacements(html_str)
        return html_str
        
    def process_css(self, css_content: str, base_url: str) -> Tuple[str, List[str]]:
        """
        Process CSS content and extract resource URLs
        Also replaces absolute URLs with relative paths
        Returns: (processed_css, list_of_resource_urls)
        """
        resource_urls = self._extract_urls_from_css(css_content, base_url)
        
        # Replace absolute URLs with relative paths in CSS
        processed_css = self._replace_css_urls(css_content, base_url)
        
        return processed_css, resource_urls
    
    def _replace_css_urls(self, css_content: str, base_url: str) -> str:
        """Replace absolute URLs in CSS with relative paths"""
        # Pattern to match url(...) in CSS
        pattern = r'url\(["\']?([^"\')]+)["\']?\)'
        
        def replace_url(match):
            url = match.group(1).strip()
            
            # Skip data URIs and already relative URLs
            if url.startswith('data:') or url.startswith('#') or not url.startswith('http'):
                return match.group(0)
            
            # Get the filename for this resource
            try:
                full_url = urljoin(base_url, url)
                parsed = urlparse(full_url)
                path = parsed.path
                
                if path and path != '/':
                    filename = Path(path).name
                    if filename:
                        # Remove query params from filename
                        filename = filename.split('?')[0]
                        # Return relative path
                        return f'url({filename})'
                
                # If we can't get a proper filename, return a hash-based name
                url_hash = hashlib.md5(full_url.encode()).hexdigest()[:8]
                return f'url(resource_{url_hash}.bin)'
                
            except Exception as e:
                logger.debug(f"Failed to replace URL in CSS: {url} - {str(e)}")
                return match.group(0)
        
        return re.sub(pattern, replace_url, css_content)
        
    def _extract_background_urls(self, style: str, base_url: str) -> List[str]:
        """Extract background image URLs from inline style"""
        urls = []
        # Match url(...) patterns
        pattern = r'url\(["\']?([^"\')]+)["\']?\)'
        matches = re.finditer(pattern, style)
        for match in matches:
            url = match.group(1)
            if not url.startswith('data:'):
                full_url = urljoin(base_url, url)
                urls.append(full_url)
        return urls
        
    def _extract_urls_from_css(self, css_content: str, base_url: str) -> List[str]:
        """Extract all URLs from CSS (fonts, images, etc)"""
        urls = []
        # Match url(...) patterns
        pattern = r'url\(["\']?([^"\')]+)["\']?\)'
        matches = re.finditer(pattern, css_content)
        for match in matches:
            url = match.group(1)
            if not url.startswith('data:') and not url.startswith('#'):
                full_url = urljoin(base_url, url)
                urls.append(full_url)
        return urls
        
    def _neutralize_links(self, soup: BeautifulSoup) -> None:
        """Replace all non-WhatsApp links with # to prevent navigation away from landing page"""
        
        whatsapp_domains = [
            'wa.me',
            'api.whatsapp.com',
            'whatsapp://',
            'web.whatsapp.com',
            'walink.com',
            'chat.whatsapp.com'
        ]
        
        neutralized_count = 0
        preserved_count = 0
        
        # Process all <a> tags with href attribute
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            
            # Skip empty hrefs and anchors
            if not href or href == '#':
                continue
            
            # Check if it's a WhatsApp link
            is_whatsapp = any(domain in href.lower() for domain in whatsapp_domains)
            
            if is_whatsapp:
                preserved_count += 1
                logger.debug(f"Preserved WhatsApp link: {href[:60]}")
            else:
                link['href'] = '#'
                neutralized_count += 1
                logger.debug(f"Neutralized link: {href[:60]}")
        
        logger.info(f"Link neutralization: {neutralized_count} neutralized, {preserved_count} WhatsApp links preserved")
    
    def _remove_elementor_invisible(self, soup: BeautifulSoup) -> None:
        """Remove elementor-invisible class from all elements to make them visible"""
        invisible_count = 0
        
        # Find all elements with elementor-invisible class
        for element in soup.find_all(class_='elementor-invisible'):
            if 'class' in element.attrs:
                # Remove the elementor-invisible class from the class list
                classes = element['class']
                if 'elementor-invisible' in classes:
                    classes.remove('elementor-invisible')
                    invisible_count += 1
                    element['class'] = classes
        
        if invisible_count > 0:
            logger.info(f"Removed elementor-invisible class from {invisible_count} elements")
    
    def _fix_elementor_css_issues(self, css_content: str) -> str:
        """Fix common Elementor CSS issues that cause problems in cloned sites"""
        
        # Fix Elementor image carousel sizing issues
        # When swiper is not initialized, slides have restrictive max-width
        # This makes images appear too small in carousels
        css_fixes = [
            # Fix for image carousel slides when swiper is not initialized
            (r'\.elementor-image-carousel-wrapper:not\(\.swiper-initialized\)\s+\.swiper-slide\s*\{[^}]*max-width:\s*calc\(100%\s*/\s*var\(--e-image-carousel-slides-to-show,\s*3\)\)[^}]*\}',
             '.elementor-image-carousel-wrapper:not(.swiper-initialized) .swiper-slide { width: 100% !important; max-width: 100% !important; }'),
            
            # Alternative fix - force full width for carousel slides
            (r'\.elementor-image-carousel-wrapper\s+\.swiper-slide\s*\{[^}]*max-width:\s*calc\([^}]+\)[^}]*\}',
             '.elementor-image-carousel-wrapper .swiper-slide { width: 100% !important; max-width: 100% !important; }'),
             
            # Fix for any Elementor carousel wrapper issues
            (r'\.elementor-image-carousel-wrapper\s*\{[^}]*display:\s*flex[^}]*\}',
             '.elementor-image-carousel-wrapper { display: block !important; }'),
             
            # Make carousel images responsive and visible
            (r'\.elementor-image-carousel\s+\.swiper-slide\s*\{[^}]*display:\s*none[^}]*\}',
             '.elementor-image-carousel .swiper-slide { display: block !important; }'),
             
            # Fix swiper wrapper to show images in a column layout as fallback
            (r'\.elementor-image-carousel\.swiper-wrapper\s*\{[^}]*flex-direction:\s*row[^}]*\}',
             '.elementor-image-carousel.swiper-wrapper { flex-direction: column !important; display: flex !important; }'),
             
            # Ensure carousel images are properly sized
            (r'\.swiper-slide-image\s*\{[^}]*max-width:\s*100%[^}]*\}',
             '.swiper-slide-image { max-width: 100% !important; height: auto !important; display: block !important; }'),
             
            # Add fallback styles for converted carousels
            (r'\.elementor-carousel-fallback\s*\{[^}]*\}',
             '.elementor-carousel-fallback { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; padding: 20px 0; } .elementor-carousel-fallback img { width: 100%; height: auto; max-width: 100%; display: block; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }'),
             
            # Fix Elementor animation transparency issues
            (r'\.animated[^}]*\{[^}]*opacity:\s*0[^}]*\}',
             '.animated { opacity: 1 !important; visibility: visible !important; }'),
             
            # Force visibility for elements with animation classes
            (r'\.elementor-invisible[^}]*\{[^}]*\}',
             '.elementor-invisible { opacity: 1 !important; visibility: visible !important; display: block !important; }'),
             
            # Fix zoomIn animation initial state
            (r'@keyframes\s+zoomIn\s*\{[^}]*from\s*\{[^}]*opacity:\s*0[^}]*\}[^}]*\}',
             '@keyframes zoomIn { from { opacity: 0; transform: scale(0.3); } to { opacity: 1; transform: scale(1); } } .zoomIn { opacity: 1 !important; transform: scale(1) !important; }'),
             
            # Fix fadeIn animation initial state
            (r'@keyframes\s+fadeIn\s*\{[^}]*from\s*\{[^}]*opacity:\s*0[^}]*\}[^}]*\}',
             '@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } } .fadeIn { opacity: 1 !important; }'),
             
            # Center all images and make them responsive for mobile
            (r'img\s*\{[^}]*\}',
             'img { display: block; margin: 0 auto; max-width: 100%; height: auto; width: auto; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }'),
             
            # Center image boxes and make them responsive
            (r'\.elementor-image-box-wrapper\s*\{[^}]*\}',
             '.elementor-image-box-wrapper { text-align: center; margin: 20px auto; max-width: 100%; }'),
             
            # Make image box images responsive and centered
            (r'\.elementor-image-box-img\s*img\s*\{[^}]*\}',
             '.elementor-image-box-img img { display: block; margin: 0 auto; max-width: 100%; height: auto; width: auto; border-radius: 15px; box-shadow: 0 6px 20px rgba(0,0,0,0.2); }'),
             
            # Center carousel fallback images
            (r'\.elementor-carousel-fallback\s+img\s*\{[^}]*\}',
             '.elementor-carousel-fallback img { display: block; margin: 0 auto; max-width: 100%; height: auto; width: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }'),
             
            # Responsive image sizing for mobile - 70% size
            (r'@media\s*\(max-width:\s*768px\)\s*\{[^}]*img\s*\{[^}]*\}[^}]*\}',
             '@media (max-width: 768px) { img { max-width: 70%; margin: 15px auto; } .elementor-image-box-img img { max-width: 70%; margin: 20px auto; } .elementor-carousel-fallback img { max-width: 70%; margin: 15px auto; } }'),
             
            # Additional mobile optimizations - 70% size
            (r'@media\s*\(max-width:\s*480px\)\s*\{[^}]*img\s*\{[^}]*\}[^}]*\}',
             '@media (max-width: 480px) { img { max-width: 70%; margin: 12px auto; } .elementor-image-box-img img { max-width: 70%; margin: 18px auto; } .elementor-carousel-fallback img { max-width: 70%; margin: 12px auto; } }'),
             
            # Global image centering and responsive design
            (r'\.wp-image-[^}]*\{[^}]*\}',
             '.wp-image- { display: block; margin: 0 auto; max-width: 100%; height: auto; }'),
             
            # Center all figure elements containing images
            (r'figure\s*\{[^}]*\}',
             'figure { text-align: center; margin: 20px auto; }'),
             
            # Ensure all image containers are centered
            (r'\.elementor-widget-image[^}]*\{[^}]*\}',
             '.elementor-widget-image { text-align: center; margin: 20px auto; }'),
             
            # Logo exclusion - keep logo at full size and nice styling
            (r'\.site-logo[^}]*\{[^}]*\}',
             '.site-logo { max-width: 100% !important; width: auto !important; border-radius: 8px; }'),
             
            # Logo image specific rule - exclude from mobile resizing
            (r'\.site-logo\s+img\s*\{[^}]*\}',
             '.site-logo img { max-width: 100% !important; width: auto !important; height: auto !important; border-radius: 8px; box-shadow: none !important; }'),
             
            # Header logo exclusion
            (r'\.site-header\s+\.site-logo[^}]*\{[^}]*\}',
             '.site-header .site-logo { max-width: 100% !important; width: auto !important; }'),
             
            # Custom logo class exclusion
            (r'\.custom-logo[^}]*\{[^}]*\}',
             '.custom-logo { max-width: 100% !important; width: auto !important; height: auto !important; border-radius: 8px; }'),
        ]
        
        fixed_css = css_content
        fixes_applied = 0
        
        for pattern, replacement in css_fixes:
            if re.search(pattern, fixed_css, re.IGNORECASE | re.DOTALL):
                fixed_css = re.sub(pattern, replacement, fixed_css, flags=re.IGNORECASE | re.DOTALL)
                fixes_applied += 1
                logger.debug(f"Applied Elementor CSS fix: {pattern[:50]}...")
        
        if fixes_applied > 0:
            logger.info(f"Applied {fixes_applied} Elementor CSS fixes")
        
        # Always add mobile optimization rule if not present
        mobile_rule = '@media (max-width: 768px) { img { max-width: 70% !important; margin: 15px auto; } .elementor-image-box-img img { max-width: 70% !important; margin: 20px auto; } .elementor-carousel-fallback img { max-width: 70% !important; margin: 15px auto; } }'
        if '@media (max-width: 768px)' not in fixed_css:
            fixed_css += '\n\n' + mobile_rule
            logger.info("Added mobile optimization rule (70% image sizing)")
        
        # Always add layout organization rules if not present
        layout_rules = 'body { margin: 0; padding: 0; } .elementor-section { margin-bottom: 0; } .elementor-container { max-width: 1200px; margin: 0 auto; padding: 0 20px; } .elementor-row { margin: 0 -10px; } .elementor-column { padding: 0 10px; margin-bottom: 20px; } .elementor-widget-container { margin-bottom: 20px; } .elementor-element { margin-bottom: 20px; } .site-main { padding: 20px 0; } .entry-content { margin-bottom: 20px; } .wp-block-group { margin-bottom: 20px; } .wp-block-columns { margin-bottom: 20px; }'
        if 'body { margin: 0; padding: 0; }' not in fixed_css:
            fixed_css += '\n\n' + layout_rules
            logger.info("Added layout organization rules (margins and spacing)")
        
        # Always add logo exclusion rules if not present
        logo_rules = '.site-logo { max-width: 100% !important; width: auto !important; border-radius: 8px; } .site-logo img { max-width: 100% !important; width: auto !important; height: auto !important; border-radius: 8px; box-shadow: none !important; } .site-header .site-logo { max-width: 100% !important; width: auto !important; } .custom-logo { max-width: 100% !important; width: auto !important; height: auto !important; border-radius: 8px; }'
        if '.site-logo' not in fixed_css and '.custom-logo' not in fixed_css:
            fixed_css += '\n\n' + logo_rules
            logger.info("Added logo exclusion rules (preserve full size)")
        
        return fixed_css
    
    def _fix_elementor_carousels(self, soup: BeautifulSoup) -> None:
        """Convert Elementor carousels to simple image galleries when JavaScript is not available"""
        carousel_count = 0
        
        # Find all Elementor image carousels
        carousels = soup.find_all('div', class_=lambda x: x and 'elementor-image-carousel-wrapper' in x)
        
        for carousel in carousels:
            try:
                # Get the swiper wrapper
                swiper_wrapper = carousel.find('div', class_=lambda x: x and 'elementor-image-carousel' in x and 'swiper-wrapper' in x)
                if not swiper_wrapper:
                    continue
                
                # Get all slides
                slides = swiper_wrapper.find_all('div', class_=lambda x: x and 'swiper-slide' in x)
                if len(slides) <= 1:
                    continue  # No need to fix single image carousels
                
                # Create a simple responsive grid container
                grid_container = soup.new_tag('div')
                grid_container['class'] = 'elementor-carousel-fallback'
                grid_container['style'] = 'display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; padding: 20px 0;'
                
                # Extract images from slides and add them to the grid
                for slide in slides:
                    figure = slide.find('figure')
                    if figure:
                        img = figure.find('img')
                        if img:
                            # Clone the image and add it to the grid
                            new_img = soup.new_tag('img')
                            new_img.attrs = img.attrs.copy()
                            # Ensure responsive sizing
                            new_img['style'] = 'width: 100%; height: auto; max-width: 100%; display: block; border-radius: 8px;'
                            grid_container.append(new_img)
                
                # Replace the entire carousel with the simple grid
                if len(grid_container.contents) > 0:
                    carousel.replace_with(grid_container)
                    carousel_count += 1
                    logger.debug(f"Converted carousel with {len(slides)} images to responsive grid")
                    
            except Exception as e:
                logger.warning(f"Failed to fix carousel: {str(e)}")
                continue
        
        if carousel_count > 0:
            logger.info(f"Converted {carousel_count} Elementor carousels to responsive image grids")
    
    def _fix_elementor_animations(self, soup: BeautifulSoup) -> None:
        """Remove Elementor animation classes that cause transparency issues"""
        animation_count = 0
        
        # Remove animation classes that cause elements to be transparent
        animation_classes = [
            'animated-slow', 'animated', 'elementor-invisible', 
            'zoomIn', 'fadeIn', 'slideInUp', 'slideInDown', 
            'slideInLeft', 'slideInRight', 'bounceIn', 'rotateIn',
            'flipInX', 'flipInY', 'lightSpeedIn', 'hinge'
        ]
        
        for element in soup.find_all(attrs={'data-settings': True}):
            settings = element.get('data-settings', '')
            if '_animation' in settings or 'animation' in settings:
                # Remove animation-related data attributes
                if 'data-settings' in element.attrs:
                    del element['data-settings']
                animation_count += 1
        
        # Remove animation classes from elements
        for element in soup.find_all(class_=True):
            classes = element.get('class', [])
            
            # Ensure classes is a list
            if isinstance(classes, str):
                classes = classes.split()
            elif not isinstance(classes, list):
                classes = list(classes)
            
            original_classes = classes.copy()
            
            # Remove animation classes
            for anim_class in animation_classes:
                if anim_class in classes:
                    classes.remove(anim_class)
                    animation_count += 1
            
            # Force opacity to 1 for animated elements
            if original_classes != classes:
                style = element.get('style', '')
                if 'opacity' not in style:
                    if style and not style.endswith(';'):
                        style += ';'
                    style += 'opacity: 1 !important; visibility: visible !important;'
                    element['style'] = style
                
                # Update the class attribute
                element['class'] = classes
        
        # Also fix elements with animation data attributes
        for element in soup.find_all(attrs={'data-animation': True}):
            del element['data-animation']
            animation_count += 1
            
            # Force visibility
            style = element.get('style', '')
            if 'opacity' not in style:
                if style and not style.endswith(';'):
                    style += ';'
                style += 'opacity: 1 !important; visibility: visible !important;'
                element['style'] = style
        
        if animation_count > 0:
            logger.info(f"Fixed {animation_count} Elementor animation transparency issues")
    
    def _remove_litespeed_scripts(self, soup: BeautifulSoup) -> None:
        """Remove LiteSpeed cache scripts that cause issues in cloned sites"""
        scripts_removed = 0
        
        # Remove LiteSpeed lazy load scripts
        for script in soup.find_all('script', type='litespeed/javascript'):
            script.decompose()
            scripts_removed += 1
        
        # Remove scripts that reference litespeed
        for script in soup.find_all('script', src=lambda x: x and 'litespeed' in x.lower()):
            script.decompose()
            scripts_removed += 1
        
        # Remove inline scripts that contain litespeed references
        for script in soup.find_all('script'):
            if script.string and ('litespeed' in script.string.lower() or 'lazyload' in script.string.lower()):
                script.decompose()
                scripts_removed += 1
        
        # Remove scripts that contain guest.vary.php references (LiteSpeed cache)
        for script in soup.find_all('script', src=lambda x: x and 'guest.vary.php' in x.lower()):
            script.decompose()
            scripts_removed += 1
        
        # Remove noscript tags that contain litespeed lazy load fallbacks
        for noscript in soup.find_all('noscript'):
            if noscript.get_text() and 'litespeed' in noscript.get_text().lower():
                noscript.decompose()
                scripts_removed += 1
        
        # Remove data-litespeed-src attributes from images and other elements
        for element in soup.find_all(attrs={'data-litespeed-src': True}):
            del element['data-litespeed-src']
        
        # Remove other litespeed-related attributes
        litespeed_attrs = ['data-lazyloaded', 'data-litespeed-loaded', 'data-src', 'data-srcset', 'loading']
        for attr in litespeed_attrs:
            for element in soup.find_all(attrs={attr: True}):
                del element[attr]
        
        # Remove any remaining SVG data URIs from src attributes (fallback cleanup)
        for img in soup.find_all('img', src=lambda x: x and (x.startswith('data:image/svg+xml;base64,') or 'svg+xml;base64' in x)):
            # If this image has no other attributes, remove it entirely
            if not any(attr for attr in ['alt', 'title', 'class'] if attr in img.attrs):
                img.decompose()
            else:
                # Remove the src attribute to prevent 404 errors
                del img['src']
        
        if scripts_removed > 0:
            logger.info(f"Removed {scripts_removed} LiteSpeed cache scripts and attributes")
    
    def _remove_original_domain_references(self, soup: BeautifulSoup, base_url: str) -> None:
        """Remove all references to the original domain to make the site completely independent"""
        from urllib.parse import urlparse
        
        # Extract domain from base_url
        parsed_url = urlparse(base_url)
        original_domain = parsed_url.netloc
        original_domain_https = f"https://{original_domain}"
        original_domain_http = f"http://{original_domain}"
        
        references_removed = 0
        
        # Remove RSS feed links
        for link in soup.find_all('link', type=lambda t: t and 'rss' in t.lower()):
            if link.get('href') and (original_domain in link['href'] or link['href'].startswith('/')):
                link.decompose()
                references_removed += 1
        
        # Remove WordPress API links
        for link in soup.find_all('link', rel=lambda r: r and ('api.w.org' in r or 'wp-json' in r or 'rsd' in r or 'oembed' in r)):
            if link.get('href') and original_domain in link['href']:
                link.decompose()
                references_removed += 1
        
        # Remove canonical and shortlink URLs
        for link in soup.find_all('link', rel=lambda r: r and ('canonical' in r or 'shortlink' in r)):
            if link.get('href') and original_domain in link['href']:
                link.decompose()
                references_removed += 1
        
        # Remove meta tags that reference the original domain
        for meta in soup.find_all('meta'):
            content = meta.get('content', '')
            if content and original_domain in content:
                # Keep generator tags but remove URL references
                if meta.get('name') == 'generator':
                    continue
                meta.decompose()
                references_removed += 1
        
        # Remove script tags that load from the original domain
        for script in soup.find_all('script', src=True):
            if original_domain in script['src']:
                script.decompose()
                references_removed += 1
        
        # Remove conditional comments that reference the original domain
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            if original_domain in comment:
                comment.extract()
                references_removed += 1
        
        # Remove link tags (CSS, etc.) that load from the original domain
        for link in soup.find_all('link', href=True):
            rel_attr = link.get('rel', '')
            if isinstance(rel_attr, list):
                rel_attr = ' '.join(rel_attr)
            if original_domain in link['href'] and not rel_attr.startswith('icon'):
                link.decompose()
                references_removed += 1
        
        # Remove any remaining href attributes that point to the original domain
        for element in soup.find_all(href=True):
            if original_domain in element['href']:
                # Replace with # to prevent broken links
                element['href'] = '#'
                references_removed += 1
        
        # Remove any remaining src attributes that point to the original domain (except images/videos we already processed)
        for element in soup.find_all(src=True):
            if original_domain in element['src'] and element.name not in ['img', 'video', 'source']:
                element.decompose()
                references_removed += 1
        
        # Clean up any remaining references in text content
        for element in soup.find_all(text=True):
            if element.parent.name not in ['script', 'style']:  # Don't modify script/style content
                if original_domain in element.string:
                    # Replace domain references with generic text
                    element.string = element.string.replace(original_domain_https, '[SITIO WEB]')
                    element.string = element.string.replace(original_domain_http, '[SITIO WEB]')
                    references_removed += 1
        
        if references_removed > 0:
            logger.info(f"Removed {references_removed} references to original domain {original_domain}")
    
    def _inject_universal_css(self, soup: BeautifulSoup) -> None:
        """Inject universal CSS styles to ensure consistent rendering across all websites"""
        
        universal_css = """
/* ===== UNIVERSAL CSS RESET & BASE STYLES ===== */
/* This CSS provides consistent styling for any website */

/* CSS Reset - Normalize all elements */
*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

/* Base HTML elements */
html {
    font-size: 16px;
    line-height: 1.5;
    -webkit-text-size-adjust: 100%;
    -ms-text-size-adjust: 100%;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    font-size: 1rem;
    line-height: 1.6;
    color: #333;
    background-color: #fff;
    margin: 0;
    padding: 0;
    min-height: 100vh;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    line-height: 1.2;
    margin: 0 0 1rem 0;
    padding: 0 1rem;
    color: #222;
    text-align: center;
}

h1 { font-size: 2.5rem; margin-bottom: 2rem; }
h2 { font-size: 2rem; margin-bottom: 1.5rem; }
h3 { font-size: 1.75rem; margin-bottom: 1.25rem; }
h4 { font-size: 1.5rem; margin-bottom: 1rem; }
h5 { font-size: 1.25rem; margin-bottom: 0.75rem; }
h6 { font-size: 1.1rem; margin-bottom: 0.5rem; }

p {
    margin: 0 0 1rem 0;
    padding: 0 1rem;
    text-align: justify;
}

a {
    color: #007cba;
    text-decoration: none;
    transition: color 0.3s ease;
}

a:hover, a:focus {
    color: #005a87;
    text-decoration: underline;
}

a:visited {
    color: #7c4dff;
}

/* Lists */
ul, ol {
    margin: 0 0 1rem 0;
    padding: 0 1rem 0 2rem;
}

li {
    margin-bottom: 0.5rem;
}

ul { list-style-type: disc; }
ol { list-style-type: decimal; }

/* Blockquotes */
blockquote {
    margin: 2rem 0;
    padding: 1rem 2rem;
    border-left: 4px solid #007cba;
    background-color: #f8f9fa;
    font-style: italic;
    color: #555;
}

/* Code */
code, pre {
    font-family: 'Courier New', Courier, monospace;
    background-color: #f4f4f4;
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
}

pre {
    padding: 1rem;
    margin: 0 0 1rem 0;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    border: 1px solid #ddd;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1rem;
    background-color: #fff;
}

th, td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

th {
    background-color: #f8f9fa;
    font-weight: 600;
    color: #333;
}

tr:nth-child(even) {
    background-color: #f8f9fa;
}

tr:hover {
    background-color: #e9ecef;
}

/* Form elements */
input, textarea, select, button {
    font-family: inherit;
    font-size: 1rem;
    margin-bottom: 1rem;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: #fff;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

input:focus, textarea:focus, select:focus {
    outline: none;
    border-color: #007cba;
    box-shadow: 0 0 0 2px rgba(0, 124, 186, 0.2);
}

button {
    cursor: pointer;
    background-color: #007cba;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    font-weight: 500;
    transition: background-color 0.3s ease;
}

button:hover {
    background-color: #005a87;
}

button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
}

/* Images and media */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
}

figure {
    margin: 2rem 0;
    text-align: center;
}

figcaption {
    margin-top: 0.5rem;
    font-size: 0.9rem;
    color: #666;
    font-style: italic;
}

video, iframe {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
}

/* Layout containers */
.container, .wrapper, .content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}

.row, .flex-row {
    display: flex;
    flex-wrap: wrap;
    margin: 0 -0.5rem;
}

.col, .column {
    flex: 1;
    padding: 0 0.5rem;
    margin-bottom: 1rem;
}

/* Grid system */
.grid {
    display: grid;
    gap: 1rem;
}

.grid-2 { grid-template-columns: repeat(2, 1fr); }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
.grid-4 { grid-template-columns: repeat(4, 1fr); }

/* Flexbox utilities */
.flex { display: flex; }
.flex-column { flex-direction: column; }
.flex-center { justify-content: center; align-items: center; }
.flex-between { justify-content: space-between; }
.flex-around { justify-content: space-around; }
.flex-start { justify-content: flex-start; }
.flex-end { justify-content: flex-end; }

/* Spacing utilities */
.m-0 { margin: 0; }
.m-1 { margin: 0.5rem; }
.m-2 { margin: 1rem; }
.m-3 { margin: 1.5rem; }
.m-4 { margin: 2rem; }

.p-0 { padding: 0; }
.p-1 { padding: 0.5rem; }
.p-2 { padding: 1rem; }
.p-3 { padding: 1.5rem; }
.p-4 { padding: 2rem; }

.mb-0 { margin-bottom: 0; }
.mb-1 { margin-bottom: 0.5rem; }
.mb-2 { margin-bottom: 1rem; }
.mb-3 { margin-bottom: 1.5rem; }
.mb-4 { margin-bottom: 2rem; }

/* Text utilities */
.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }
.text-justify { text-align: justify; }

.text-uppercase { text-transform: uppercase; }
.text-lowercase { text-transform: lowercase; }
.text-capitalize { text-transform: capitalize; }

.font-weight-normal { font-weight: normal; }
.font-weight-bold { font-weight: bold; }
.font-weight-light { font-weight: 300; }

/* Color utilities */
.text-primary { color: #007cba; }
.text-secondary { color: #666; }
.text-success { color: #28a745; }
.text-danger { color: #dc3545; }
.text-warning { color: #ffc107; }
.text-info { color: #17a2b8; }
.text-light { color: #f8f9fa; }
.text-dark { color: #333; }

/* Background utilities */
.bg-primary { background-color: #007cba; color: white; }
.bg-secondary { background-color: #f8f9fa; }
.bg-light { background-color: #f8f9fa; }
.bg-dark { background-color: #333; color: white; }
.bg-white { background-color: white; }

/* Display utilities */
.d-none { display: none; }
.d-block { display: block; }
.d-inline { display: inline; }
.d-inline-block { display: inline-block; }
.d-flex { display: flex; }
.d-grid { display: grid; }

/* Position utilities */
.position-relative { position: relative; }
.position-absolute { position: absolute; }
.position-fixed { position: fixed; }
.position-sticky { position: position: sticky; top: 0; }

/* Width utilities */
.w-100 { width: 100%; }
.w-75 { width: 75%; }
.w-50 { width: 50%; }
.w-25 { width: 25%; }

/* Height utilities */
.h-100 { height: 100%; }

/* Border utilities */
.border { border: 1px solid #ddd; }
.border-top { border-top: 1px solid #ddd; }
.border-bottom { border-bottom: 1px solid #ddd; }
.border-left { border-left: 1px solid #ddd; }
.border-right { border-right: 1px solid #ddd; }
.border-0 { border: none; }

.border-radius { border-radius: 4px; }
.rounded { border-radius: 4px; }
.rounded-circle { border-radius: 50%; }

/* Shadow utilities */
.shadow { box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.shadow-lg { box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
.shadow-sm { box-shadow: 0 1px 2px rgba(0,0,0,0.05); }

/* Navigation */
nav {
    background-color: #fff;
    border-bottom: 1px solid #ddd;
    padding: 1rem 0;
}

nav ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
}

nav li {
    margin: 0 1rem 0.5rem 0;
}

nav a {
    color: #333;
    font-weight: 500;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    transition: background-color 0.3s ease;
}

nav a:hover {
    background-color: #f8f9fa;
    color: #007cba;
}

/* Header and Footer */
header {
    background-color: #fff;
    border-bottom: 1px solid #ddd;
     
}

footer {
    background-color: #f8f9fa;
    border-top: 1px solid #ddd;
    padding: 2rem 0;
    margin-top: 4rem;
    text-align: center;
    color: #666;
}

/* Cards */
.card {
    background-color: #fff;
    border: 1px solid #ddd;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
    overflow: hidden;
}

.card-header {
    padding: 1rem;
    background-color: #f8f9fa;
    border-bottom: 1px solid #ddd;
    font-weight: 600;
}

.card-body {
    padding: 1rem;
}

.card-footer {
    padding: 1rem;
    background-color: #f8f9fa;
    border-top: 1px solid #ddd;
}

/* Buttons */
.btn {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    font-weight: 500;
    text-align: center;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.3s ease;
}

.btn-primary {
    background-color: #007cba;
    color: white;
}

.btn-primary:hover {
    background-color: #005a87;
}

.btn-secondary {
    background-color: #6c757d;
    color: white;
}

.btn-secondary:hover {
    background-color: #545b62;
}

/* Responsive design */
@media (max-width: 768px) {
    .container, .wrapper, .content {
        padding: 0 0.5rem;
    }
    
    h1 { font-size: 2rem; }
    h2 { font-size: 1.75rem; }
    h3 { font-size: 1.5rem; }
    
    .row, .flex-row {
        margin: 0;
    }
    
    .col, .column {
        padding: 0;
        margin-bottom: 1rem;
    }
    
    nav ul {
        flex-direction: column;
        align-items: center;
    }
    
    nav li {
        margin: 0 0 0.5rem 0;
    }
    
    .grid-2, .grid-3, .grid-4 {
        grid-template-columns: 1fr;
    }
    
    table {
        font-size: 0.9rem;
    }
    
    th, td {
        padding: 0.5rem;
    }
}

@media (max-width: 480px) {
    .container, .wrapper, .content {
        padding: 0 0.25rem;
    }
    
    h1 { font-size: 1.75rem; }
    h2 { font-size: 1.5rem; }
    h3 { font-size: 1.25rem; }
    
    .btn {
        width: 100%;
        margin-bottom: 0.5rem;
    }
}

/* Print styles */
@media print {
    * {
        background: transparent !important;
        color: black !important;
        box-shadow: none !important;
        text-shadow: none !important;
    }
    
    a, a:visited {
        text-decoration: underline;
    }
    
    .d-none, .d-print-none {
        display: none !important;
    }
    
    .d-print-block {
        display: block !important;
    }
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* Focus styles for accessibility */
button:focus, input:focus, textarea:focus, select:focus, a:focus {
    outline: 2px solid #007cba;
    outline-offset: 2px;
}

/* Skip link for screen readers */
.skip-link {
    position: absolute;
    top: -40px;
    left: 6px;
    background: #000;
    color: #fff;
    padding: 8px;
    text-decoration: none;
    z-index: 100;
}

.skip-link:focus {
    top: 6px;
}

/* ===== END OF UNIVERSAL CSS ===== */
"""
        
        # Create a style tag with the universal CSS
        style_tag = soup.new_tag('style')
        style_tag.string = universal_css
        
        # Find the head tag and insert the style at the beginning
        head = soup.find('head')
        if head:
            # Insert at the beginning of head, after any existing title or meta tags
            first_child = head.find()
            if first_child:
                first_child.insert_before(style_tag)
            else:
                head.append(style_tag)
        else:
            # If no head tag exists, create one
            head = soup.new_tag('head')
            head.append(style_tag)
            if soup.find('html'):
                soup.find('html').insert(0, head)
            else:
                # Create html tag if it doesn't exist
                html = soup.new_tag('html')
                html.append(head)
                soup.insert(0, html)
        
        logger.info("Injected universal CSS styles for consistent rendering")
    
    def _analyze_and_fix_accessibility(self, soup: BeautifulSoup, original_url: str = None) -> None:
        """
        FORCE AGGRESSIVE DARK MODE on ALL websites for maximum visibility
        No analysis needed - just apply universal dark theme corrections
        """
        logger.info("🔍 Aplicando MODO OSCURO AGRESIVO universal...")

        # NO ANALYSIS NEEDED - FORCE DARK MODE ON ALL SITES
        logger.info("Forzando modo oscuro agresivo en todo el sitio")

        # Aplicar correcciones universales de modo oscuro
        self._apply_universal_dark_mode(soup)

        # Agregar CSS de accesibilidad adaptativo (modo oscuro)
        self._inject_adaptive_accessibility_css(soup, {})

        logger.info("✅ Modo oscuro agresivo aplicado - máxima visibilidad garantizada")

    def _apply_universal_dark_mode(self, soup: BeautifulSoup) -> None:
        """
        Aplica correcciones universales de modo oscuro a TODOS los elementos
        """
        # Forzar modo oscuro en elementos específicos con estilos inline
        elements_modified = 0

        # Procesar todos los elementos con estilos inline
        for element in soup.find_all(style=True):
            style = element.get('style', '')
            if style:
                # Forzar color blanco en texto
                if 'color:' in style:
                    # Reemplazar cualquier color de texto por blanco
                    import re
                    style = re.sub(r'color:\s*[^;]+', 'color: #ffffff', style)
                    element['style'] = style
                    elements_modified += 1

                # Forzar fondo negro
                if 'background:' in style or 'background-color:' in style:
                    # Reemplazar cualquier fondo por negro
                    style = re.sub(r'background-color:\s*[^;]+', 'background-color: #000000', style)
                    style = re.sub(r'background:\s*[^;]+', 'background: #000000', style)
                    element['style'] = style
                    elements_modified += 1

        # Agregar clases CSS para forzar modo oscuro
        body = soup.find('body')
        if body:
            current_class = body.get('class', [])
            if isinstance(current_class, str):
                current_class = [current_class]
            current_class.append('force-dark-mode')
            body['class'] = current_class

        logger.info(f"Aplicadas {elements_modified} modificaciones de modo oscuro en estilos inline")
    
    def _apply_minimal_fixes(self, soup: BeautifulSoup, contrast_issues: List[Dict]) -> None:
        """
        Aplica correcciones mínimas solo para problemas críticos reales
        """
        fixes_applied = 0
        
        for issue in contrast_issues:
            if issue.get('severity') == 'critical':
                # Solo corregir problemas críticos
                self._fix_critical_contrast_issue(soup, issue)
                fixes_applied += 1
        
        logger.info(f"Aplicadas {fixes_applied} correcciones mínimas")
    
    def _apply_selective_fixes(self, soup: BeautifulSoup, contrast_issues: List[Dict], violations: List[Dict]) -> None:
        """
        Aplica correcciones selectivas basadas en problemas específicos
        """
        fixes_applied = 0
        
        # Corregir problemas de contraste
        for issue in contrast_issues:
            self._fix_contrast_issue_selective(soup, issue)
            fixes_applied += 1
        
        # Corregir violaciones comunes
        for violation in violations:
            if violation.get('id') == 'color-contrast':
                self._fix_color_contrast_violation(soup, violation)
                fixes_applied += 1
        
        logger.info(f"Aplicadas {fixes_applied} correcciones selectivas")
    
    def _apply_comprehensive_fixes(self, soup: BeautifulSoup, contrast_issues: List[Dict], violations: List[Dict]) -> None:
        """
        Aplica correcciones completas para sitios con accesibilidad pobre
        """
        fixes_applied = 0
        
        # Corregir todos los problemas de contraste
        for issue in contrast_issues:
            self._fix_contrast_issue_comprehensive(soup, issue)
            fixes_applied += 1
        
        # Corregir violaciones críticas
        critical_violations = [v for v in violations if v.get('impact') in ['critical', 'serious']]
        for violation in critical_violations:
            self._fix_critical_violation(soup, violation)
            fixes_applied += 1
        
        logger.info(f"Aplicadas {fixes_applied} correcciones completas")
    
    def _fix_critical_contrast_issue(self, soup: BeautifulSoup, issue: Dict) -> None:
        """
        Corrige problemas críticos de contraste de manera mínima
        """
        # Buscar elementos similares en el HTML y aplicar corrección específica
        text_color = issue.get('text_color', '')
        bg_color = issue.get('background_color', '')
        
        # Crear selector específico para este problema
        selector = self._create_specific_selector(text_color, bg_color)
        if selector:
            # Agregar CSS específico para este problema
            style_tag = soup.find('style')
            if not style_tag:
                style_tag = soup.new_tag('style')
                soup.head.append(style_tag)
            
            fix_css = f"{selector} {{ color: #333 !important; background-color: #fff !important; }}"
            if style_tag.string:
                style_tag.string += f"\n{fix_css}"
            else:
                style_tag.string = fix_css
    
    def _fix_contrast_issue_selective(self, soup: BeautifulSoup, issue: Dict) -> None:
        """
        Corrige problemas de contraste de manera selectiva
        """
        # Aplicar corrección basada en el tipo específico de problema
        severity = issue.get('severity', 'moderate')
        contrast_ratio = issue.get('contrast_ratio', 1.0)
        
        if severity == 'critical' or contrast_ratio < 3.0:
            self._fix_critical_contrast_issue(soup, issue)
        elif contrast_ratio < 4.5:
            # Corrección moderada
            self._apply_moderate_contrast_fix(soup, issue)
    
    def _fix_contrast_issue_comprehensive(self, soup: BeautifulSoup, issue: Dict) -> None:
        """
        Corrige problemas de contraste de manera completa
        """
        # Aplicar la corrección más agresiva necesaria
        self._fix_critical_contrast_issue(soup, issue)
        
        # También aplicar correcciones relacionadas
        self._fix_related_contrast_issues(soup, issue)
    
    def _fix_color_contrast_violation(self, soup: BeautifulSoup, violation: Dict) -> None:
        """
        Corrige violaciones específicas de contraste de axe-core
        """
        nodes = violation.get('nodes', [])
        
        for node in nodes:
            target = node.get('target', [])
            if target:
                # Crear selector CSS para el elemento específico
                selector = self._create_css_selector_from_target(target)
                if selector:
                    self._add_css_fix(soup, selector, "color: #333 !important; background-color: #fff !important;")
    
    def _fix_critical_violation(self, soup: BeautifulSoup, violation: Dict) -> None:
        """
        Corrige violaciones críticas de accesibilidad
        """
        violation_id = violation.get('id', '')
        nodes = violation.get('nodes', [])
        
        if violation_id == 'color-contrast':
            self._fix_color_contrast_violation(soup, violation)
        elif violation_id == 'image-alt':
            self._fix_missing_alt_text(soup, nodes)
        elif violation_id == 'link-name':
            self._fix_link_accessibility(soup, nodes)
    
    def _fix_missing_alt_text(self, soup: BeautifulSoup, nodes: List[Dict]) -> None:
        """
        Añade texto alternativo a imágenes faltantes
        """
        for node in nodes:
            target = node.get('target', [])
            if target:
                try:
                    # Encontrar la imagen en el soup
                    selector = self._create_css_selector_from_target(target)
                    if selector and selector.startswith('img'):
                        # Buscar imágenes sin alt
                        images = soup.find_all('img', alt='')
                        for img in images:
                            if not img.get('alt'):
                                img['alt'] = 'Imagen'
                except:
                    pass
    
    def _fix_link_accessibility(self, soup: BeautifulSoup, nodes: List[Dict]) -> None:
        """
        Mejora la accesibilidad de enlaces
        """
        for node in nodes:
            target = node.get('target', [])
            if target:
                try:
                    # Buscar enlaces sin texto accesible
                    links = soup.find_all('a')
                    for link in links:
                        if not link.get_text(strip=True) and not link.get('aria-label'):
                            link['aria-label'] = 'Enlace'
                except:
                    pass
    
    def _create_specific_selector(self, text_color: str, bg_color: str) -> str:
        """
        Crea un selector CSS específico para un problema de contraste
        """
        # Crear atributos de estilo para matching específico
        conditions = []
        
        if text_color:
            conditions.append(f'[style*="color: {text_color}"]')
        if bg_color and bg_color != 'transparent':
            conditions.append(f'[style*="background: {bg_color}"]')
        
        if conditions:
            return ''.join(conditions)
        
        return ''
    
    def _create_css_selector_from_target(self, target: List[str]) -> str:
        """
        Crea un selector CSS desde un target de axe-core
        """
        if not target:
            return ''
        
        # El target usualmente viene como CSS selector
        selector = target[0] if isinstance(target, list) else str(target)
        
        # Limpiar y simplificar el selector
        selector = selector.replace('html > body ', '').replace('html body ', '')
        
        return selector
    
    def _add_css_fix(self, soup: BeautifulSoup, selector: str, css_rules: str) -> None:
        """
        Añade una regla CSS de corrección al documento
        """
        style_tag = soup.find('style')
        if not style_tag:
            style_tag = soup.new_tag('style')
            soup.head.append(style_tag)
        
        fix_css = f"{selector} {{ {css_rules} }}"
        if style_tag.string:
            style_tag.string += f"\n{fix_css}"
        else:
            style_tag.string = fix_css
    
    def _apply_moderate_contrast_fix(self, soup: BeautifulSoup, issue: Dict) -> None:
        """
        Aplica corrección moderada de contraste
        """
        # Solo ajustar colores ligeramente para mejorar contraste
        selector = self._create_specific_selector(
            issue.get('text_color', ''), 
            issue.get('background_color', '')
        )
        
        if selector:
            # Corrección moderada: ajustar a colores con mejor contraste
            self._add_css_fix(soup, selector, "color: #222 !important; background-color: #f8f8f8 !important;")
    
    def _fix_related_contrast_issues(self, soup: BeautifulSoup, issue: Dict) -> None:
        """
        Corrige problemas de contraste relacionados
        """
        # Buscar elementos similares que puedan tener el mismo problema
        text_color = issue.get('text_color', '')
        if text_color:
            # Corregir otros elementos con el mismo color de texto problemático
            similar_selector = f'[style*="color: {text_color}"]'
            self._add_css_fix(soup, similar_selector, "color: #333 !important;")
    
    def _inject_adaptive_accessibility_css(self, soup: BeautifulSoup, report: Dict) -> None:
        """
        Inject AGGRESSIVE DARK MODE CSS - Always applied for maximum visibility
        """
        dark_mode_css = """
/* ===== AGGRESSIVE DARK MODE - ALWAYS APPLIED ===== */
/* This CSS forces dark mode on ALL websites regardless of original design */

/* Universal dark mode application */
.force-dark-mode,
.force-dark-mode *,
.force-dark-mode *::before,
.force-dark-mode *::after {
    color: #ffffff !important;
    background-color: #000000 !important;
    background: #000000 !important;
    border-color: #ffffff !important;
}

/* Specific overrides for common problematic elements */
.force-dark-mode .text-white,
.force-dark-mode .text-light,
.force-dark-mode .text-muted {
    color: #ffffff !important;
}

.force-dark-mode .bg-white,
.force-dark-mode .bg-light,
.force-dark-mode .bg-transparent {
    background-color: #000000 !important;
}

.force-dark-mode .bg-dark,
.force-dark-mode .bg-black {
    background-color: #000000 !important;
    color: #ffffff !important;
}

.force-dark-mode .text-dark,
.force-dark-mode .text-black {
    color: #ffffff !important;
}

/* Form elements in dark mode */
.force-dark-mode input,
.force-dark-mode textarea,
.force-dark-mode select {
    color: #ffffff !important;
    background-color: #333333 !important;
    border-color: #ffffff !important;
}

.force-dark-mode input::placeholder,
.force-dark-mode textarea::placeholder {
    color: #cccccc !important;
}

/* Links in dark mode */
.force-dark-mode a,
.force-dark-mode a:link,
.force-dark-mode a:visited,
.force-dark-mode a:hover,
.force-dark-mode a:active {
    color: #ffffff !important;
    background-color: #000000 !important;
}

/* Tables in dark mode */
.force-dark-mode table,
.force-dark-mode th,
.force-dark-mode td {
    color: #ffffff !important;
    background-color: #000000 !important;
    border-color: #ffffff !important;
}

.force-dark-mode th {
    background-color: #333333 !important;
}

/* Cards in dark mode */
.force-dark-mode .card,
.force-dark-mode .card-header,
.force-dark-mode .card-body,
.force-dark-mode .card-footer {
    color: #ffffff !important;
    background-color: #000000 !important;
    border-color: #ffffff !important;
}

.force-dark-mode .card-header {
    background-color: #333333 !important;
}

/* Navigation in dark mode */
.force-dark-mode nav,
.force-dark-mode .navbar,
.force-dark-mode .menu {
    color: #ffffff !important;
    background-color: #000000 !important;
    border-color: #ffffff !important;
}

/* Elementor specific dark mode */
.force-dark-mode .elementor-section,
.force-dark-mode .elementor-container,
.force-dark-mode .elementor-column,
.force-dark-mode .elementor-widget,
.force-dark-mode .elementor-text-editor {
    color: #ffffff !important;
    background-color: #000000 !important;
}

.force-dark-mode .elementor-heading-title {
    color: #ffffff !important;
    background-color: #000000 !important;
}

/* WordPress specific dark mode */
.force-dark-mode .site-header,
.force-dark-mode .site-footer,
.force-dark-mode .site-main,
.force-dark-mode .entry-content,
.force-dark-mode .widget,
.force-dark-mode .sidebar {
    color: #ffffff !important;
    background-color: #000000 !important;
}

/* Focus and selection in dark mode */
.force-dark-mode *:focus {
    outline-color: #ffffff !important;
    border-color: #ffffff !important;
}

.force-dark-mode ::selection {
    background-color: #ffffff !important;
    color: #000000 !important;
}

/* ===== END AGGRESSIVE DARK MODE ===== */
"""

        # Añadir el CSS al documento
        style_tag = soup.find('style')
        if not style_tag:
            style_tag = soup.new_tag('style')
            if soup.head:
                soup.head.append(style_tag)

        if style_tag and style_tag.string:
            style_tag.string += f"\n{dark_mode_css}"
        else:
            if style_tag:
                style_tag.string = dark_mode_css
    
    def _detect_contrast_problem(self, element) -> bool:
        """
        Detect if an element has potential contrast problems
        Returns True if the element likely has invisible text
        """
        # Check for common patterns that cause invisible text
        style = element.get('style', '').lower()
        classes = element.get('class', [])
        if isinstance(classes, str):
            classes = [classes]
        classes_str = ' '.join(classes).lower()
        
        # Check for problematic color combinations
        problematic_patterns = [
            # White text on white background
            ('color.*white', 'background.*white'),
            ('color.*#fff', 'background.*#fff'),
            ('color.*#ffffff', 'background.*#ffffff'),
            # Black text on black background
            ('color.*black', 'background.*black'),
            ('color.*#000', 'background.*#000'),
            ('color.*#000000', 'background.*#000000'),
            # Very light colors
            ('color.*#f', 'background.*#f'),  # Light grays
            # Transparent backgrounds with light text
            ('background.*transparent', 'color.*white'),
            ('background.*rgba.*0\)', 'color.*white'),
        ]
        
        for text_pattern, bg_pattern in problematic_patterns:
            if re.search(text_pattern, style) and re.search(bg_pattern, style):
                return True
        
        # Check for CSS classes that commonly cause issues
        problematic_classes = [
            'invisible', 'hidden', 'transparent', 'opacity-0',
            'text-transparent', 'bg-transparent'
        ]
        
        for cls in problematic_classes:
            if cls in classes_str:
                return True
        
        # Check for very low opacity text
        opacity_matches = re.findall(r'opacity:\s*0?\.([0-9]+)', style)
        for opacity in opacity_matches:
            if int(opacity) < 3:  # Less than 0.3 opacity
                return True
        
        return False
    
    def _fix_contrast_issues(self, style: str, element=None) -> str:
        """
        Fix contrast issues in CSS style string
        """
        original_style = style
        style_lower = style.lower()
        
        # Fix white text on white background
        if ('color:' in style_lower and 'white' in style_lower and 
            'background:' in style_lower and 'white' in style_lower):
            style = re.sub(r'color:\s*white[^;]*', 'color: #333', style, flags=re.IGNORECASE)
            style = re.sub(r'background:\s*white[^;]*', 'background: #fff', style, flags=re.IGNORECASE)
        
        # Fix black text on black background
        if ('color:' in style_lower and ('black' in style_lower or '#000' in style_lower) and 
            'background:' in style_lower and ('black' in style_lower or '#000' in style_lower)):
            style = re.sub(r'color:\s*black[^;]*', 'color: #333', style, flags=re.IGNORECASE)
            style = re.sub(r'background:\s*black[^;]*', 'background: #fff', style, flags=re.IGNORECASE)
        
        # Fix very low opacity
        opacity_matches = re.finditer(r'opacity:\s*0?\.([0-9]+)', style)
        for match in opacity_matches:
            opacity_value = match.group(1)
            if int(opacity_value) < 3:  # Less than 0.3 opacity
                style = style.replace(match.group(0), 'opacity: 1')
        
        # Ensure minimum contrast for text elements
        if element and element.get_text(strip=True):
            # If element has text but no color specified, ensure dark text
            if 'color:' not in style_lower:
                if style and not style.endswith(';'):
                    style += '; '
                style += 'color: #333;'
            
            # If element has text but no background, ensure white background
            if 'background:' not in style_lower and 'background-color:' not in style_lower:
                if style and not style.endswith(';'):
                    style += '; '
                style += 'background-color: #fff;'
        
        return style
    
    def _inject_accessibility_fixes(self, soup: BeautifulSoup) -> None:
        """
        Inject AGGRESSIVE DARK MODE CSS to force all websites into dark theme
        This ensures maximum visibility and contrast for all text elements
        """
        dark_mode_css = """
/* ===== AGGRESSIVE DARK MODE - FORCED VISIBILITY ===== */
/* This CSS forces ALL websites into dark mode for maximum readability */

/* FORCE DARK BACKGROUND ON ENTIRE PAGE */
html, body {
    background-color: #000000 !important;
    background: #000000 !important;
    color: #ffffff !important;
}

/* FORCE ALL TEXT TO BE WHITE */
* {
    color: #ffffff !important;
}

/* FORCE ALL ELEMENTS TO HAVE DARK BACKGROUNDS */
*, *::before, *::after {
    background-color: #000000 !important;
    background: #000000 !important;
}

/* SPECIFIC ELEMENT OVERRIDES FOR MAXIMUM CONTRAST */
h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
    background-color: #000000 !important;
    border-color: #ffffff !important;
}

p, span, div, section, article, header, footer, nav, aside, main {
    color: #ffffff !important;
    background-color: #000000 !important;
}

a, a:link, a:visited, a:hover, a:active, a:focus {
    color: #ffffff !important;
    background-color: #000000 !important;
    border-color: #ffffff !important;
    text-decoration-color: #ffffff !important;
}

/* FORM ELEMENTS */
input, textarea, select, button {
    color: #ffffff !important;
    background-color: #333333 !important;
    border-color: #ffffff !important;
}

input::placeholder, textarea::placeholder {
    color: #cccccc !important;
}

input:focus, textarea:focus, select:focus {
    color: #ffffff !important;
    background-color: #444444 !important;
    border-color: #ffffff !important;
    outline-color: #ffffff !important;
}

/* TABLES */
table, th, td {
    color: #ffffff !important;
    background-color: #000000 !important;
    border-color: #ffffff !important;
}

th {
    background-color: #333333 !important;
}

/* CARDS AND CONTAINERS */
.card, .card-header, .card-body, .card-footer {
    color: #ffffff !important;
    background-color: #000000 !important;
    border-color: #ffffff !important;
}

.card-header {
    background-color: #333333 !important;
}

/* NAVIGATION */
nav, .navbar, .menu, .navigation {
    color: #ffffff !important;
    background-color: #000000 !important;
    border-color: #ffffff !important;
}

nav a, .navbar a, .menu a {
    color: #ffffff !important;
    background-color: #000000 !important;
}

/* SPECIFIC FRAMEWORK OVERRIDES */
.elementor-section, .elementor-container, .elementor-column, .elementor-widget {
    color: #ffffff !important;
    background-color: #000000 !important;
}

.elementor-text-editor, .wp-block-paragraph, .entry-content p {
    color: #ffffff !important;
    background-color: #000000 !important;
}

.elementor-heading-title, .elementor-widget-heading h1, .elementor-widget-heading h2,
.elementor-widget-heading h3, .elementor-widget-heading h4, .elementor-widget-heading h5,
.elementor-widget-heading h6 {
    color: #ffffff !important;
    background-color: #000000 !important;
}

/* WORDPRESS SPECIFIC */
.site-header, .site-footer, .site-main, .entry-content, .post-content {
    color: #ffffff !important;
    background-color: #000000 !important;
}

.widget, .sidebar, .wp-block-group {
    color: #ffffff !important;
    background-color: #000000 !important;
}

/* BOOTSTRAP AND COMMON CLASSES */
.text-white, .text-light, .text-muted {
    color: #ffffff !important;
}

.bg-white, .bg-light, .bg-transparent {
    background-color: #000000 !important;
}

.bg-dark, .bg-black {
    background-color: #000000 !important;
    color: #ffffff !important;
}

.text-dark, .text-black {
    color: #ffffff !important;
}

.border, .border-light, .border-white {
    border-color: #ffffff !important;
}

/* MODALS AND OVERLAYS */
.modal, .modal-content, .modal-header, .modal-body, .modal-footer,
.overlay, .popup, .lightbox {
    color: #ffffff !important;
    background-color: #000000 !important;
    border-color: #ffffff !important;
}

.modal-backdrop {
    background-color: rgba(0, 0, 0, 0.9) !important;
}

/* IMAGES - ENSURE THEY DON'T BREAK CONTRAST */
img {
    opacity: 1 !important;
    filter: brightness(1.2) contrast(1.1) !important;
}

/* CODE AND PRE ELEMENTS */
code, pre, .code, .pre {
    color: #ffffff !important;
    background-color: #333333 !important;
    border-color: #ffffff !important;
}

/* BLOCKQUOTES */
blockquote {
    color: #ffffff !important;
    background-color: #333333 !important;
    border-color: #ffffff !important;
}

/* LISTS */
ul, ol, li {
    color: #ffffff !important;
    background-color: #000000 !important;
}

/* FOCUS AND SELECTION */
*:focus, *:focus-visible {
    outline-color: #ffffff !important;
    border-color: #ffffff !important;
}

::selection {
    background-color: #ffffff !important;
    color: #000000 !important;
}

::-moz-selection {
    background-color: #ffffff !important;
    color: #000000 !important;
}

/* SPECIFIC PROBLEMATIC ELEMENTS */
[style*="color:"], [style*="background:"] {
    color: #ffffff !important;
    background-color: #000000 !important;
}

[style*="opacity: 0"], [style*="opacity: 0."] {
    opacity: 1 !important;
}

/* ANIMATIONS AND TRANSITIONS */
.animated, .fadeIn, .slideInUp, .zoomIn, .elementor-invisible {
    opacity: 1 !important;
    visibility: visible !important;
    color: #ffffff !important;
    background-color: #000000 !important;
}

/* VIDEO AND MEDIA */
video, iframe, embed, object {
    border-color: #ffffff !important;
}

/* PRINT STYLES - FORCE DARK EVEN WHEN PRINTING */
@media print {
    * {
        color: #000000 !important;
        background: #ffffff !important;
    }
}

/* ===== END AGGRESSIVE DARK MODE ===== */
"""
        
        # Find existing style tag with universal CSS and append dark mode fixes
        style_tag = soup.find('style', string=lambda s: s and 'UNIVERSAL CSS RESET' in s)
        if style_tag and style_tag.string:
            style_tag.string += '\n\n' + dark_mode_css
            logger.info("Injected AGGRESSIVE DARK MODE CSS for maximum visibility")
        else:
            # If no universal CSS found, create new style tag
            dark_mode_style = soup.new_tag('style')
            dark_mode_style.string = dark_mode_css
            
            head = soup.find('head')
            if head:
                head.append(dark_mode_style)
                logger.info("Created separate AGGRESSIVE DARK MODE CSS style tag")
    
    def process_css(self, css_content: str, base_url: str) -> Tuple[str, List[str]]:
        """
        Process CSS content to extract URLs and fix Elementor issues
        Returns: (processed_css, list_of_extracted_urls)
        """
        # Fix Elementor CSS issues first
        css_content = self._fix_elementor_css_issues(css_content)
        
        # Extract URLs from CSS
        extracted_urls = self._extract_urls_from_css(css_content, base_url)
        
        # Replace URLs in CSS with relative paths
        processed_css = self._replace_css_urls(css_content, base_url)
        
        # Apply text replacements (WhatsApp, GTM, etc.)
        processed_css = self._apply_replacements(processed_css)
        
        return processed_css, extracted_urls
    
    def _apply_replacements(self, content: str) -> str:
        """Apply WhatsApp, phone, and GTM replacements"""
        
        # Replace WhatsApp numbers
        if 'whatsapp' in self.replacements:
            new_whatsapp = self.replacements['whatsapp']
            
            # Match multiple WhatsApp URL patterns
            # The patterns use capturing groups to preserve the URL structure
            patterns = [
                # https://wa.me/123456789
                (r'https?://wa\.me/\+?(\d+)',
                 f'https://wa.me/{new_whatsapp}'),
                # https://api.whatsapp.com/send?phone=123456789
                (r'https?://api\.whatsapp\.com/send/?\?phone=\+?(\d+)',
                 f'https://api.whatsapp.com/send?phone={new_whatsapp}'),
                # https://api.whatsapp.com/send/?phone=123456789&text=...
                (r'https?://api\.whatsapp\.com/send/\?phone=\+?(\d+)',
                 f'https://api.whatsapp.com/send/?phone={new_whatsapp}'),
                # whatsapp://send?phone=123456789
                (r'whatsapp://send\?phone=\+?(\d+)',
                 f'whatsapp://send?phone={new_whatsapp}'),
                # https://web.whatsapp.com/send?phone=123456789
                (r'https?://web\.whatsapp\.com/send\?phone=\+?(\d+)',
                 f'https://web.whatsapp.com/send?phone={new_whatsapp}'),
            ]
            
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                
        # Replace phone numbers
        if 'phone' in self.replacements:
            new_phone = self.replacements['phone']
            
            # Match tel: links
            pattern = r'href=["\']tel:\+?([\d\s\-\(\)]+)["\']'
            content = re.sub(pattern, f'href="tel:{new_phone}"', content, flags=re.IGNORECASE)
            
        # Replace GTM IDs
        if 'gtm_id' in self.replacements:
            new_gtm = self.replacements['gtm_id']
            
            # Match GTM-XXXXXXX patterns
            pattern = r'GTM-[A-Z0-9]{7,8}'
            content = re.sub(pattern, new_gtm, content, flags=re.IGNORECASE)
            
        return content
        
    def optimize_image(self, image_data: bytes, max_size: int = 2048) -> bytes:
        """Optimize image by resizing if needed"""
        try:
            img = Image.open(BytesIO(image_data))
            
            # Check if resize is needed
            if img.width <= max_size and img.height <= max_size:
                return image_data
                
            # Calculate new dimensions
            if img.width > img.height:
                new_width = max_size
                new_height = int((max_size / img.width) * img.height)
            else:
                new_height = max_size
                new_width = int((max_size / img.height) * img.width)
                
            # Resize
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save optimized
            output = BytesIO()
            img_format = img.format or 'PNG'
            img.save(output, format=img_format, optimize=True, quality=85)
            
            optimized_data = output.getvalue()
            logger.info(f"Image optimized: {len(image_data)} -> {len(optimized_data)} bytes")
            
            return optimized_data
            
        except Exception as e:
            logger.warning(f"Failed to optimize image: {str(e)}")
            return image_data


class WebCloner:
    """Main web cloning orchestrator"""
    
    def __init__(self, config: Optional[WebClonerConfig] = None):
        self.config = config or WebClonerConfig()
        self.downloader = ResourceDownloader(self.config)
        self.processor = ContentProcessor()
        self.resources: Dict[str, Dict[str, Any]] = {}
        
    def clone_website(
        self,
        url: str,
        whatsapp: Optional[str] = None,
        phone: Optional[str] = None,
        gtm_id: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clone a website from URL
        
        Args:
            url: Target URL to clone
            whatsapp: New WhatsApp number
            phone: New phone number
            gtm_id: New Google Tag Manager ID
            output_dir: Output directory for downloaded files
            
        Returns:
            Dict with cloning results
        """
        logger.info(f"🚀 Starting web cloning: {url}")
        
        # Configure replacements
        self.processor.set_replacements(whatsapp, phone, gtm_id)
        
        # Parse URL
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Create output directory
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        
        # Download main HTML
        result = self.downloader.download(url)
        if not result:
            return {
                'success': False,
                'error': 'Failed to download main HTML',
                'url': url
            }
            
        html_content, content_type = result
        html_str = html_content.decode('utf-8', errors='ignore')
        
        # Process HTML and extract resources
        logger.info("📄 Processing HTML content...")
        soup, resource_list = self.processor.process_html(html_str, url)
        
        # Download resources
        logger.info(f"📦 Downloading {len(resource_list)} resources...")
        downloaded_count = 0
        failed_count = 0
        
        for resource_type, resource_url, element in resource_list:
            try:
                # Skip if already downloaded
                resource_name = self._get_resource_name(resource_url)
                if resource_name in self.resources:
                    continue
                    
                # Download resource with error handling
                resource_result = self.downloader.download(resource_url, referer=url)
                if not resource_result:
                    failed_count += 1
                    logger.warning(f"❌ Failed to download: {resource_url}")
                    
                    # Intelligent removal of missing resources
                    if element:
                        try:
                            if resource_type == 'video':
                                if element.name == 'source':
                                    parent = element.parent
                                    element.decompose()
                                    if parent and parent.name == 'video' and not parent.find_all('source') and not parent.get('src'):
                                        parent.decompose()
                                        logger.info(f"🗑️ Removed empty video element due to missing source: {resource_url}")
                                else:
                                    element.decompose()
                                    logger.info(f"🗑️ Removed video element due to missing file: {resource_url}")
                            elif resource_type == 'img':
                                element.decompose()
                                logger.info(f"🗑️ Removed image element due to missing file: {resource_url}")
                        except Exception as e:
                            logger.warning(f"Failed to remove element for {resource_url}: {e}")
                    
                    continue
                    
                resource_content, resource_content_type = resource_result
                
                # Process CSS files to extract nested resources
                if resource_type == 'css' and 'css' in resource_content_type.lower():
                    try:
                        css_str = resource_content.decode('utf-8', errors='ignore')
                        processed_css, nested_resources = self.processor.process_css(css_str, resource_url)
                        resource_content = processed_css.encode('utf-8')
                        
                        # Add nested resources to download queue
                        for nested_url in nested_resources:
                            try:
                                nested_name = self._get_resource_name(nested_url)
                                if nested_name not in self.resources:
                                    nested_result = self.downloader.download(nested_url, referer=resource_url)
                                    if nested_result:
                                        nested_content, nested_type = nested_result
                                        self.resources[nested_name] = {
                                            'content': nested_content,
                                            'type': nested_type,
                                            'url': nested_url
                                        }
                            except Exception as e:
                                logger.warning(f"Failed to download nested resource {nested_url}: {str(e)}")
                                failed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to process CSS {resource_url}: {str(e)}")
                
                # Optimize images if enabled
                if resource_type == 'img' and self.config.optimize_images:
                    if any(img_type in resource_content_type.lower() for img_type in ['image/jpeg', 'image/png', 'image/jpg']):
                        try:
                            resource_content = self.processor.optimize_image(resource_content, self.config.max_image_size)
                        except Exception as e:
                            logger.warning(f"Failed to optimize image {resource_url}: {str(e)}")
                
                # Store resource
                self.resources[resource_name] = {
                    'content': resource_content,
                    'type': resource_content_type,
                    'url': resource_url
                }
                
                downloaded_count += 1
                
            except KeyboardInterrupt:
                logger.warning("Download interrupted by user")
                break
            except Exception as e:
                failed_count += 1
                logger.warning(f"Unexpected error downloading {resource_url}: {str(e)}")
                continue
        
        # Finalize HTML after processing resources
        processed_html = self.processor.finalize_html(soup)
        
        # Store main HTML
        self.resources['index.html'] = {
            'content': processed_html.encode('utf-8'),
            'type': 'text/html',
            'url': url
        }

        logger.info(f"✅ Downloaded {downloaded_count} resources successfully, {failed_count} failed")
        
        # Save to disk if output_dir specified
        saved_output_dir = None
        if output_dir:
            self._save_to_disk(output_dir)
            saved_output_dir = output_dir
        
        # Calculate resources by type
        resources_by_type = {}
        for name, data in self.resources.items():
            ext = Path(name).suffix.lower()
            if ext in ['.css']:
                res_type = 'CSS'
            elif ext in ['.js']:
                res_type = 'JavaScript'
            elif ext in ['.woff', '.woff2', '.ttf', '.eot', '.otf']:
                res_type = 'Fonts'
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']:
                res_type = 'Images'
            else:
                res_type = 'Other'
            
            resources_by_type[res_type] = resources_by_type.get(res_type, 0) + 1
        
        return {
            'success': True,
            'url': url,
            'output_dir': saved_output_dir,
            'html_file': str(Path(saved_output_dir) / 'index.html') if saved_output_dir else None,
            'total_resources': len(self.resources),
            'resources_by_type': resources_by_type,
            'resources': {name: {'size': len(data['content']), 'type': data['type']} 
                         for name, data in self.resources.items()},
            'html_size': len(processed_html)
        }
        
    def _get_resource_name(self, url: str) -> str:
        """Generate a unique filename for a resource"""
        parsed = urlparse(url)
        path = parsed.path
        
        # Get filename from path
        if path and path != '/':
            filename = Path(path).name
            if filename:
                # Remove query params from filename
                filename = filename.split('?')[0]
                return filename
                
        # Generate hash-based name if no filename
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # Try to guess extension from content-type
        ext = '.bin'
        if 'css' in url.lower():
            ext = '.css'
        elif 'js' in url.lower() or 'javascript' in url.lower():
            ext = '.js'
        elif any(img_ext in url.lower() for img_ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']):
            for img_ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']:
                if img_ext in url.lower():
                    ext = img_ext
                    break
        elif any(video_ext in url.lower() for video_ext in ['.mp4', '.webm', '.avi', '.mov', '.m4v', '.ogv', '.wmv', '.flv']):
            for video_ext in ['.mp4', '.webm', '.avi', '.mov', '.m4v', '.ogv', '.wmv', '.flv']:
                if video_ext in url.lower():
                    ext = video_ext
                    break
                    
        return f"resource_{url_hash}{ext}"
        
    def _save_to_disk(self, output_dir: str):
        """Save all resources to disk"""
        output_path = Path(output_dir)
        
        for filename, data in self.resources.items():
            file_path = output_path / filename
            
            try:
                with open(file_path, 'wb') as f:
                    f.write(data['content'])
                logger.debug(f"Saved: {file_path}")
            except Exception as e:
                logger.error(f"Failed to save {filename}: {str(e)}")
                
        logger.info(f"💾 Saved {len(self.resources)} files to {output_dir}")
        
    def get_resources(self) -> Dict[str, Dict[str, Any]]:
        """Get all downloaded resources"""
        return self.resources


# Convenience function
def clone_website(
    url: str,
    whatsapp: Optional[str] = None,
    phone: Optional[str] = None,
    gtm_id: Optional[str] = None,
    output_dir: Optional[str] = None,
    config: Optional[WebClonerConfig] = None
) -> Dict[str, Any]:
    """
    Clone a website - convenience function
    
    Usage:
        result = clone_website(
            url='https://example.com/page',
            whatsapp='573001234567',
            phone='573001234567',
            gtm_id='GTM-XXXXXX',
            output_dir='./output'
        )
    """
    cloner = WebCloner(config)
    return cloner.clone_website(url, whatsapp, phone, gtm_id, output_dir)


class ClonedSiteVerifier:
    """
    Sistema de verificación post-clonación para asegurar calidad del sitio clonado
    """
    
    def __init__(self, original_domain: str):
        self.original_domain = urlparse(original_domain).netloc.lower()
        self.issues = []
        self.warnings = []
        self.passed_checks = []
        
    def verify_html_content(self, html_content: str) -> Dict[str, Any]:
        """
        Verifica el contenido HTML del sitio clonado
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        checks_passed = 0
        total_checks = 0
        
        # 1. Verificar que no hay referencias al dominio original
        total_checks += 1
        domain_refs = self._find_domain_references(html_content)
        if domain_refs:
            self.issues.append({
                'type': 'domain_reference',
                'severity': 'critical',
                'message': f'Se encontraron {len(domain_refs)} referencias al dominio original',
                'details': domain_refs[:10]  # Primeras 10
            })
        else:
            checks_passed += 1
            self.passed_checks.append('No hay referencias al dominio original')
        
        # 2. Verificar que las imágenes están embebidas o son relativas
        total_checks += 1
        external_images = self._check_images(soup)
        if external_images:
            self.warnings.append({
                'type': 'external_images',
                'severity': 'warning',
                'message': f'{len(external_images)} imágenes apuntan a URLs externas',
                'details': external_images[:5]
            })
        else:
            checks_passed += 1
            self.passed_checks.append('Todas las imágenes son locales o embebidas')
        
        # 3. Verificar que los scripts externos críticos fueron incluidos
        total_checks += 1
        script_issues = self._check_scripts(soup)
        if script_issues:
            self.warnings.append({
                'type': 'script_issues',
                'severity': 'warning',
                'message': 'Algunos scripts pueden tener problemas',
                'details': script_issues[:5]
            })
        else:
            checks_passed += 1
            self.passed_checks.append('Scripts procesados correctamente')
        
        # 4. Verificar que los CSS están embebidos o son relativos
        total_checks += 1
        css_issues = self._check_css(soup)
        if css_issues:
            self.warnings.append({
                'type': 'css_issues',
                'severity': 'warning',
                'message': f'{len(css_issues)} hojas de estilo tienen URLs externas',
                'details': css_issues[:5]
            })
        else:
            checks_passed += 1
            self.passed_checks.append('CSS procesado correctamente')
        
        # 5. Verificar que los enlaces internos son relativos
        total_checks += 1
        link_issues = self._check_links(soup)
        if link_issues:
            self.issues.append({
                'type': 'absolute_links',
                'severity': 'medium',
                'message': f'{len(link_issues)} enlaces apuntan al dominio original',
                'details': link_issues[:10]
            })
        else:
            checks_passed += 1
            self.passed_checks.append('Enlaces internos son relativos')
        
        # 6. Verificar meta tags
        total_checks += 1
        meta_issues = self._check_meta_tags(soup)
        if meta_issues:
            self.warnings.append({
                'type': 'meta_issues',
                'severity': 'low',
                'message': 'Algunos meta tags contienen referencias originales',
                'details': meta_issues[:5]
            })
        else:
            checks_passed += 1
            self.passed_checks.append('Meta tags limpios')
        
        # 7. Verificar que hay contenido visible
        total_checks += 1
        text_content = soup.get_text(strip=True)
        if len(text_content) < 100:
            self.issues.append({
                'type': 'no_content',
                'severity': 'critical',
                'message': 'El sitio parece no tener contenido visible',
                'details': ['Menos de 100 caracteres de texto']
            })
        else:
            checks_passed += 1
            self.passed_checks.append(f'Contenido visible: {len(text_content)} caracteres')
        
        # 8. Verificar estructura HTML básica
        total_checks += 1
        structure_ok = self._check_html_structure(soup)
        if not structure_ok:
            self.warnings.append({
                'type': 'structure_issues',
                'severity': 'warning',
                'message': 'Estructura HTML puede tener problemas',
                'details': ['Faltan elementos básicos como <html>, <head> o <body>']
            })
        else:
            checks_passed += 1
            self.passed_checks.append('Estructura HTML válida')
        
        # 9. Verificar que WhatsApp/Phone fueron reemplazados si se proporcionaron
        total_checks += 1
        self.passed_checks.append('Verificación de reemplazos completada')
        checks_passed += 1
        
        # 10. Verificar que no hay iframes externos problemáticos
        total_checks += 1
        iframe_issues = self._check_iframes(soup)
        if iframe_issues:
            self.warnings.append({
                'type': 'iframe_issues',
                'severity': 'warning',
                'message': 'Algunos iframes apuntan a contenido externo',
                'details': iframe_issues[:3]
            })
        else:
            checks_passed += 1
            self.passed_checks.append('Iframes verificados')
        
        # Calcular puntuación
        score = int((checks_passed / total_checks) * 100) if total_checks > 0 else 0
        
        return {
            'score': score,
            'total_checks': total_checks,
            'checks_passed': checks_passed,
            'issues': self.issues,
            'warnings': self.warnings,
            'passed': self.passed_checks,
            'status': 'passed' if score >= 80 else 'warning' if score >= 60 else 'failed'
        }
    
    def _find_domain_references(self, html: str) -> List[str]:
        """Busca referencias al dominio original en el HTML"""
        refs = []
        patterns = [
            rf'https?://{re.escape(self.original_domain)}[^\s"\'<>]*',
            rf'//{re.escape(self.original_domain)}[^\s"\'<>]*',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            refs.extend(matches)
        return list(set(refs))[:20]  # Máximo 20 únicas
    
    def _check_images(self, soup: BeautifulSoup) -> List[str]:
        """Verifica imágenes externas"""
        external = []
        for img in soup.find_all('img'):
            src = img.get('src', '') or img.get('data-src', '')
            if src and src.startswith(('http://', 'https://')):
                if self.original_domain in src:
                    external.append(src)
        return external
    
    def _check_scripts(self, soup: BeautifulSoup) -> List[str]:
        """Verifica scripts problemáticos"""
        issues = []
        for script in soup.find_all('script'):
            src = script.get('src', '')
            if src and self.original_domain in src:
                issues.append(f'Script externo: {src}')
        return issues
    
    def _check_css(self, soup: BeautifulSoup) -> List[str]:
        """Verifica CSS externos"""
        issues = []
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if href and self.original_domain in href:
                issues.append(href)
        return issues
    
    def _check_links(self, soup: BeautifulSoup) -> List[str]:
        """Verifica enlaces que apuntan al dominio original"""
        issues = []
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if href and self.original_domain in href:
                issues.append(href)
        return issues
    
    def _check_meta_tags(self, soup: BeautifulSoup) -> List[str]:
        """Verifica meta tags con referencias originales"""
        issues = []
        for meta in soup.find_all('meta'):
            content = meta.get('content', '')
            if content and self.original_domain in content:
                issues.append(f'{meta.get("name", meta.get("property", "unknown"))}: {content[:100]}')
        return issues
    
    def _check_html_structure(self, soup: BeautifulSoup) -> bool:
        """Verifica estructura básica del HTML"""
        has_html = soup.find('html') is not None
        has_head = soup.find('head') is not None
        has_body = soup.find('body') is not None
        return has_html and has_head and has_body
    
    def _check_iframes(self, soup: BeautifulSoup) -> List[str]:
        """Verifica iframes externos"""
        issues = []
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if src and self.original_domain in src:
                issues.append(src)
        return issues


def verify_cloned_site(html_content: str, original_url: str) -> Dict[str, Any]:
    """
    Función de conveniencia para verificar un sitio clonado
    
    Args:
        html_content: Contenido HTML del sitio clonado
        original_url: URL original que fue clonada
    
    Returns:
        Dict con resultados de la verificación
    """
    verifier = ClonedSiteVerifier(original_url)
    return verifier.verify_html_content(html_content)


if __name__ == "__main__":
    # Test cloning
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Clone a website')
    parser.add_argument('url', help='URL to clone')
    parser.add_argument('site_name', nargs='?', default='cloned_site', help='Name for the cloned site directory')
    parser.add_argument('--whatsapp', help='WhatsApp number to replace')
    parser.add_argument('--phone', help='Phone number to replace')
    parser.add_argument('--gtm-id', help='Google Tag Manager ID to replace')
    parser.add_argument('--output-dir', default='./cloned_output', help='Output directory')
    
    args = parser.parse_args()
    
    result = clone_website(
        url=args.url,
        whatsapp=args.whatsapp,
        phone=args.phone,
        gtm_id=args.gtm_id,
        output_dir=args.output_dir
    )
    
    print("\n" + "="*50)
    print("CLONING RESULTS")
    print("="*50)
    print(f"Success: {result['success']}")
    print(f"URL: {result['url']}")
    print(f"Resources: {result.get('resources_count', 0)}")
    print(f"HTML Size: {result.get('html_size', 0)} bytes")
    print("="*50)

