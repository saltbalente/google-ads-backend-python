#!/usr/bin/env python3
"""
Playwright-based Web Cloner - Sistema profesional de clonación de sitios web

Usa un navegador headless real para:
- Bypass de protecciones anti-bot (Cloudflare, etc.)
- Captura de recursos cargados dinámicamente con JavaScript
- Interceptación de TODAS las peticiones de red
- Espera a que el DOM esté completamente cargado
"""

import os
import re
import json
import hashlib
import logging
import asyncio
import base64
import mimetypes
from typing import Dict, List, Set, Tuple, Optional, Any
from urllib.parse import urljoin, urlparse, urlunparse
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright, Page, Response, Route
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")


class PlaywrightCloner:
    """
    Clonador de sitios web usando Playwright para máxima compatibilidad
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.timeout = self.config.get('timeout', 60000)  # 60 seconds
        self.wait_for_idle = self.config.get('wait_for_idle', 5000)  # 5 seconds
        
        # Resources captured from network
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.captured_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        
        # Original domain for cleanup
        self.original_domain: str = ""
        self.original_url: str = ""
        
        # Replacements
        self.whatsapp: str = ""
        self.phone: str = ""
        self.gtm_id: str = ""
        
    async def clone_website(
        self,
        url: str,
        whatsapp: str = None,
        phone: str = None,
        gtm_id: str = None,
        progress_callback: callable = None
    ) -> Dict[str, Any]:
        """
        Clone a website using Playwright
        
        Args:
            url: URL to clone
            whatsapp: WhatsApp number to inject
            phone: Phone number to inject
            gtm_id: Google Tag Manager ID to inject
            progress_callback: Callback function for progress updates
            
        Returns:
            Dict with success status and resources
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'success': False,
                'error': 'Playwright not installed. Run: pip install playwright && playwright install chromium'
            }
        
        self.original_url = url
        parsed = urlparse(url)
        self.original_domain = parsed.netloc
        self.whatsapp = whatsapp or ""
        self.phone = phone or ""
        self.gtm_id = gtm_id or ""
        
        logger.info(f"🚀 Starting Playwright cloning: {url}")
        
        if progress_callback:
            progress_callback(5, "Iniciando navegador...")
        
        try:
            async with async_playwright() as p:
                # Launch browser with stealth settings
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--disable-gpu',
                        '--window-size=1920,1080',
                        '--disable-blink-features=AutomationControlled',
                    ]
                )
                
                # Create context with realistic settings
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='es-ES',
                    timezone_id='America/Bogota',
                    extra_http_headers={
                        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    }
                )
                
                # Create page
                page = await context.new_page()
                
                # Enable stealth mode
                await self._apply_stealth(page)
                
                if progress_callback:
                    progress_callback(10, "Interceptando peticiones de red...")
                
                # Intercept all network requests
                await page.route("**/*", self._handle_route)
                
                # Listen to responses to capture resources
                page.on("response", lambda response: asyncio.create_task(self._capture_response(response)))
                
                if progress_callback:
                    progress_callback(15, "Navegando al sitio...")
                
                # Navigate to the page
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                except Exception as e:
                    logger.warning(f"Initial navigation warning: {e}")
                
                if progress_callback:
                    progress_callback(30, "Esperando carga completa del DOM...")
                
                # Wait for network to be idle
                try:
                    await page.wait_for_load_state('networkidle', timeout=self.wait_for_idle)
                except:
                    pass  # Continue even if timeout
                
                # Additional wait for dynamic content
                await asyncio.sleep(3)
                
                # Scroll to trigger lazy loading
                if progress_callback:
                    progress_callback(40, "Cargando contenido lazy...")
                
                await self._scroll_page(page)
                
                # Wait again for lazy loaded content
                await asyncio.sleep(2)
                
                if progress_callback:
                    progress_callback(50, "Capturando HTML final...")
                
                # Get the final HTML after JavaScript execution
                html_content = await page.content()
                
                if progress_callback:
                    progress_callback(60, "Procesando recursos...")
                
                # Process and clean the HTML
                processed_html = self._process_html(html_content)
                
                # Store main HTML
                self.resources['index.html'] = {
                    'content': processed_html.encode('utf-8'),
                    'type': 'text/html',
                    'url': url
                }
                
                if progress_callback:
                    progress_callback(70, "Limpiando referencias al dominio original...")
                
                # Clean all resources
                self._clean_all_resources()
                
                if progress_callback:
                    progress_callback(80, "Finalizando...")
                
                # Close browser
                await browser.close()
                
                logger.info(f"✅ Cloning complete: {len(self.resources)} resources captured")
                
                return {
                    'success': True,
                    'url': url,
                    'resources_count': len(self.resources),
                    'html_size': len(processed_html),
                    'captured_urls': len(self.captured_urls),
                    'failed_urls': len(self.failed_urls)
                }
                
        except Exception as e:
            logger.error(f"❌ Cloning failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _apply_stealth(self, page: Page):
        """Apply stealth techniques to avoid bot detection"""
        await page.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override navigator.plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override navigator.languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-ES', 'es', 'en']
            });
            
            // Override chrome
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
    
    async def _handle_route(self, route: Route):
        """Handle intercepted routes - allows all requests but logs them"""
        try:
            await route.continue_()
        except Exception as e:
            logger.debug(f"Route continue failed: {e}")
            try:
                await route.abort()
            except:
                pass
    
    async def _capture_response(self, response: Response):
        """Capture response content for resources"""
        url = response.url
        
        # Skip already captured
        if url in self.captured_urls:
            return
            
        # Skip data URLs
        if url.startswith('data:'):
            return
            
        # Skip tracking/analytics URLs
        skip_patterns = [
            'google-analytics.com',
            'googletagmanager.com',
            'facebook.net',
            'doubleclick.net',
            'analytics',
            'tracking',
            'pixel',
        ]
        if any(pattern in url.lower() for pattern in skip_patterns):
            return
        
        try:
            status = response.status
            if status != 200:
                self.failed_urls.add(url)
                return
            
            content_type = response.headers.get('content-type', '')
            
            # Determine resource type and filename
            parsed = urlparse(url)
            path = parsed.path
            filename = Path(path).name if path and path != '/' else None
            
            # Generate filename if needed
            if not filename or filename == '':
                ext = self._get_extension_from_content_type(content_type)
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"resource_{url_hash}{ext}"
            
            # Clean filename
            filename = self._sanitize_filename(filename)
            
            # Get content
            try:
                body = await response.body()
            except:
                self.failed_urls.add(url)
                return
            
            # Store resource
            self.resources[filename] = {
                'content': body,
                'type': content_type,
                'url': url,
                'original_filename': filename
            }
            
            self.captured_urls.add(url)
            logger.debug(f"✅ Captured: {filename} ({len(body)} bytes)")
            
        except Exception as e:
            logger.debug(f"Failed to capture {url}: {e}")
            self.failed_urls.add(url)
    
    async def _scroll_page(self, page: Page):
        """Scroll page to trigger lazy loading"""
        try:
            # Get page height
            height = await page.evaluate("document.body.scrollHeight")
            viewport_height = 1080
            
            # Scroll in steps
            current = 0
            while current < height:
                await page.evaluate(f"window.scrollTo(0, {current})")
                await asyncio.sleep(0.3)
                current += viewport_height // 2
                
                # Update height (might have changed due to lazy loading)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height > height:
                    height = new_height
            
            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
            
        except Exception as e:
            logger.warning(f"Scroll failed: {e}")
    
    def _process_html(self, html: str) -> str:
        """Process and clean HTML content"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Update resource URLs to relative paths
        self._update_resource_urls(soup)
        
        # Remove scripts that reference original domain
        self._remove_external_scripts(soup)
        
        # Clean meta tags
        self._clean_meta_tags(soup)
        
        # Remove tracking pixels
        self._remove_tracking(soup)
        
        # Inject WhatsApp/Phone replacements
        if self.whatsapp or self.phone:
            self._inject_contact_replacements(soup)
        
        # Inject GTM if provided
        if self.gtm_id:
            self._inject_gtm(soup)
        
        # Fix visibility issues
        self._fix_visibility(soup)
        
        # Convert to string
        html_str = str(soup)
        
        # Final cleanup with regex
        html_str = self._final_cleanup(html_str)
        
        return html_str
    
    def _update_resource_urls(self, soup):
        """Update all resource URLs to relative paths"""
        from bs4 import BeautifulSoup
        
        # Update CSS links
        for link in soup.find_all('link', href=True):
            href = link['href']
            if self._should_localize_url(href):
                filename = self._url_to_filename(href)
                if filename in self.resources:
                    link['href'] = filename
        
        # Update script sources
        for script in soup.find_all('script', src=True):
            src = script['src']
            if self._should_localize_url(src):
                filename = self._url_to_filename(src)
                if filename in self.resources:
                    script['src'] = filename
        
        # Update images
        for img in soup.find_all('img'):
            for attr in ['src', 'data-src', 'data-lazy-src']:
                if img.get(attr):
                    url = img[attr]
                    if self._should_localize_url(url):
                        filename = self._url_to_filename(url)
                        if filename in self.resources:
                            img[attr] = filename
            
            # Clean srcset attribute (multiple URLs with size descriptors)
            if img.get('srcset'):
                srcset = img['srcset']
                # Parse srcset entries (format: "url 2048w, url 1024w, ...")
                entries = []
                for entry in srcset.split(','):
                    entry = entry.strip()
                    if not entry:
                        continue
                    
                    # Split URL and descriptor (e.g., "image.jpg 2048w")
                    parts = entry.split()
                    if len(parts) >= 1:
                        url = parts[0]
                        descriptor = parts[1] if len(parts) > 1 else ''
                        
                        # Only keep entries with valid URLs
                        if self._should_localize_url(url) and not url.endswith('w'):
                            filename = self._url_to_filename(url)
                            if filename in self.resources:
                                if descriptor:
                                    entries.append(f"{filename} {descriptor}")
                                else:
                                    entries.append(filename)
                
                # Update or remove srcset
                if entries:
                    img['srcset'] = ', '.join(entries)
                else:
                    # Remove invalid srcset to avoid errors
                    del img['srcset']
        
        # Update source elements (used in <picture> tags)
        for source in soup.find_all('source'):
            if source.get('srcset'):
                srcset = source['srcset']
                entries = []
                for entry in srcset.split(','):
                    entry = entry.strip()
                    if not entry:
                        continue
                    
                    parts = entry.split()
                    if len(parts) >= 1:
                        url = parts[0]
                        descriptor = parts[1] if len(parts) > 1 else ''
                        
                        if self._should_localize_url(url) and not url.endswith('w'):
                            filename = self._url_to_filename(url)
                            if filename in self.resources:
                                if descriptor:
                                    entries.append(f"{filename} {descriptor}")
                                else:
                                    entries.append(filename)
                
                if entries:
                    source['srcset'] = ', '.join(entries)
                else:
                    del source['srcset']
        
        # Update background images in style attributes
        for element in soup.find_all(style=True):
            style = element['style']
            if 'url(' in style:
                element['style'] = self._replace_css_urls(style)
    
    def _should_localize_url(self, url: str) -> bool:
        """Check if URL should be converted to local path"""
        if not url:
            return False
        if url.startswith('data:'):
            return False
        if url.startswith('#'):
            return False
        if url.startswith('javascript:'):
            return False
        return True
    
    def _url_to_filename(self, url: str) -> str:
        """Convert URL to local filename"""
        parsed = urlparse(url)
        path = parsed.path
        
        if path and path != '/':
            filename = Path(path).name
            if filename:
                return self._sanitize_filename(filename.split('?')[0])
        
        # Generate hash-based name
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        ext = self._guess_extension(url)
        return f"resource_{url_hash}{ext}"
    
    def _remove_external_scripts(self, soup):
        """Remove scripts that load from external domains"""
        for script in soup.find_all('script', src=True):
            src = script['src']
            if self.original_domain in src:
                # Check if we have this resource locally
                filename = self._url_to_filename(src)
                if filename not in self.resources:
                    script.decompose()
    
    def _clean_meta_tags(self, soup):
        """Clean meta tags that reference original domain"""
        for meta in soup.find_all('meta'):
            content = meta.get('content', '')
            if self.original_domain in content:
                # Remove URL-related meta tags
                name = meta.get('name', '') or meta.get('property', '')
                if any(x in name.lower() for x in ['url', 'site', 'domain', 'canonical']):
                    meta.decompose()
    
    def _remove_tracking(self, soup):
        """Remove tracking pixels and analytics"""
        # Remove tracking images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if any(x in src.lower() for x in ['pixel', 'tracking', 'analytics', 'beacon']):
                img.decompose()
        
        # Remove noscript tracking
        for noscript in soup.find_all('noscript'):
            text = str(noscript)
            if any(x in text.lower() for x in ['facebook', 'pixel', 'tracking']):
                noscript.decompose()
    
    def _inject_contact_replacements(self, soup):
        """Inject WhatsApp and phone replacements"""
        html_str = str(soup)
        
        # WhatsApp patterns
        wa_patterns = [
            r'wa\.me/\d+',
            r'api\.whatsapp\.com/send\?phone=\d+',
            r'whatsapp\.com/send\?phone=\d+',
        ]
        
        if self.whatsapp:
            for pattern in wa_patterns:
                if 'wa.me' in pattern:
                    html_str = re.sub(pattern, f'wa.me/{self.whatsapp}', html_str)
                else:
                    html_str = re.sub(pattern, f'api.whatsapp.com/send?phone={self.whatsapp}', html_str)
        
        # Phone patterns
        if self.phone:
            phone_pattern = r'tel:\+?\d+'
            html_str = re.sub(phone_pattern, f'tel:{self.phone}', html_str)
        
        # Re-parse the modified HTML
        return html_str
    
    def _inject_gtm(self, soup):
        """Inject Google Tag Manager"""
        if not self.gtm_id:
            return
        
        # GTM script for head
        gtm_head = soup.new_tag('script')
        gtm_head.string = f"""
        (function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
        new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
        j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
        'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
        }})(window,document,'script','dataLayer','{self.gtm_id}');
        """
        
        head = soup.find('head')
        if head:
            head.insert(0, gtm_head)
        
        # GTM noscript for body
        gtm_body = soup.new_tag('noscript')
        iframe = soup.new_tag('iframe', src=f"https://www.googletagmanager.com/ns.html?id={self.gtm_id}",
                              height="0", width="0", style="display:none;visibility:hidden")
        gtm_body.append(iframe)
        
        body = soup.find('body')
        if body:
            body.insert(0, gtm_body)
    
    def _fix_visibility(self, soup):
        """Fix visibility issues from animations and lazy loading"""
        # Remove animation classes
        animation_classes = [
            'animated', 'elementor-invisible', 'aos-init',
            'fadeIn', 'fadeOut', 'slideIn', 'slideOut'
        ]
        
        for element in soup.find_all(class_=True):
            classes = element.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()
            
            new_classes = [c for c in classes if c not in animation_classes]
            if new_classes != classes:
                element['class'] = new_classes
                # Force visibility
                style = element.get('style', '')
                if 'opacity' not in style.lower():
                    element['style'] = f"{style}; opacity: 1 !important; visibility: visible !important;"
    
    def _final_cleanup(self, html: str) -> str:
        """Final cleanup of HTML string"""
        domain = self.original_domain
        
        # Remove escaped URLs
        html = re.sub(rf'https?:\\/\\/{re.escape(domain)}[^\s"\'<>\\]*', '', html)
        
        # Remove normal URLs to original domain
        html = re.sub(rf'https?://{re.escape(domain)}[^\s"\'<>]*', '', html)
        
        # Clean remaining domain references in text
        html = html.replace(domain, '')
        
        # Clean empty URL references
        html = re.sub(r'(href|src|action)=["\']["\']\s*', r'\1="#" ', html)
        
        return html
    
    def _clean_all_resources(self):
        """Clean all captured resources to remove domain references"""
        domain = self.original_domain
        
        for filename, resource in self.resources.items():
            content_type = resource.get('type', '')
            content = resource.get('content', b'')
            
            # Only clean text-based resources
            if any(t in content_type for t in ['text', 'javascript', 'json', 'css', 'html', 'xml']):
                try:
                    text = content.decode('utf-8', errors='ignore')
                    
                    # Remove domain references
                    text = re.sub(rf'https?:\\/\\/{re.escape(domain)}[^\s"\'<>\\]*', '', text)
                    text = re.sub(rf'https?://{re.escape(domain)}[^\s"\'<>]*', '', text)
                    text = text.replace(domain, '')
                    
                    # Update URLs to relative
                    text = self._convert_urls_to_relative(text)
                    
                    resource['content'] = text.encode('utf-8')
                    
                except Exception as e:
                    logger.debug(f"Failed to clean {filename}: {e}")
    
    def _convert_urls_to_relative(self, content: str) -> str:
        """Convert absolute URLs to relative in content"""
        # Pattern for URLs
        url_pattern = rf'(https?://[^\s"\'<>]+)'
        
        def replace_url(match):
            url = match.group(1)
            filename = self._url_to_filename(url)
            if filename in self.resources:
                return filename
            return url
        
        return re.sub(url_pattern, replace_url, content)
    
    def _replace_css_urls(self, css: str) -> str:
        """Replace URLs in CSS content"""
        pattern = r'url\(["\']?([^"\')]+)["\']?\)'
        
        def replace(match):
            url = match.group(1)
            if url.startswith('data:'):
                return match.group(0)
            filename = self._url_to_filename(url)
            if filename in self.resources:
                return f'url("{filename}")'
            return match.group(0)
        
        return re.sub(pattern, replace, css)
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type"""
        mapping = {
            'text/html': '.html',
            'text/css': '.css',
            'text/javascript': '.js',
            'application/javascript': '.js',
            'application/json': '.json',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/svg+xml': '.svg',
            'font/woff': '.woff',
            'font/woff2': '.woff2',
            'application/font-woff': '.woff',
            'application/font-woff2': '.woff2',
        }
        
        for mime, ext in mapping.items():
            if mime in content_type:
                return ext
        
        return ''
    
    def _guess_extension(self, url: str) -> str:
        """Guess file extension from URL"""
        parsed = urlparse(url)
        path = parsed.path
        
        if '.' in path:
            ext = Path(path).suffix
            if ext and len(ext) <= 5:
                return ext
        
        return ''
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem"""
        # Remove query params
        filename = filename.split('?')[0]
        
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Limit length
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:90] + ext
        
        return filename
    
    def get_resources(self) -> Dict[str, Dict[str, Any]]:
        """Get all captured resources"""
        return self.resources


# Synchronous wrapper for the async cloner
def clone_with_playwright(
    url: str,
    whatsapp: str = None,
    phone: str = None,
    gtm_id: str = None,
    progress_callback: callable = None
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """
    Synchronous wrapper to clone a website using Playwright
    
    Returns:
        Tuple of (result_dict, resources_dict)
    """
    cloner = PlaywrightCloner()
    
    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            cloner.clone_website(url, whatsapp, phone, gtm_id, progress_callback)
        )
        return result, cloner.get_resources()
    finally:
        loop.close()


# Test function
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python playwright_cloner.py <url> [whatsapp] [phone] [gtm_id]")
        sys.exit(1)
    
    url = sys.argv[1]
    whatsapp = sys.argv[2] if len(sys.argv) > 2 else None
    phone = sys.argv[3] if len(sys.argv) > 3 else None
    gtm_id = sys.argv[4] if len(sys.argv) > 4 else None
    
    def progress(pct, msg):
        print(f"[{pct}%] {msg}")
    
    result, resources = clone_with_playwright(url, whatsapp, phone, gtm_id, progress)
    
    print("\n" + "="*50)
    print("CLONING RESULTS")
    print("="*50)
    print(f"Success: {result.get('success')}")
    print(f"Resources: {len(resources)}")
    
    if resources:
        print("\nCaptured resources:")
        for name, info in list(resources.items())[:20]:
            size = len(info.get('content', b''))
            print(f"  - {name}: {size} bytes")
        
        if len(resources) > 20:
            print(f"  ... and {len(resources) - 20} more")
