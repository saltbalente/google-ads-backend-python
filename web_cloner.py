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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebClonerConfig:
    """Configuration for web cloning process"""
    def __init__(self):
        self.timeout = 30
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.max_retries = 3
        self.retry_delay = 2
        self.download_images = True
        self.download_css = True
        self.download_js = True
        self.download_fonts = True
        self.optimize_images = True
        self.max_image_size = 2048  # Max dimension in pixels


class ResourceDownloader:
    """Handles downloading of web resources with retry logic"""
    
    def __init__(self, config: WebClonerConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.user_agent,
            'Accept': '*/*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        self.downloaded_urls: Set[str] = set()
        
    def download(self, url: str, referer: Optional[str] = None) -> Optional[Tuple[bytes, str]]:
        """
        Download a resource from URL
        Returns: Tuple of (content_bytes, content_type) or None if failed
        """
        if url in self.downloaded_urls:
            logger.debug(f"Skipping already downloaded: {url}")
            return None
            
        # Validate URL
        if not self._is_valid_url(url):
            logger.warning(f"Invalid URL: {url}")
            return None
            
        headers = {}
        if referer:
            headers['Referer'] = referer
            
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Downloading {url} (attempt {attempt + 1}/{self.config.max_retries})")
                
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=self.config.timeout,
                    stream=True,
                    allow_redirects=True
                )
                
                # Check response status
                if response.status_code == 404:
                    logger.warning(f"Resource not found (404): {url}")
                    return None
                    
                response.raise_for_status()
                
                # Check content size
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.config.max_file_size:
                    logger.warning(f"File too large: {url} ({content_length} bytes)")
                    return None
                
                # Download content
                content = b''
                total_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        content += chunk
                        total_size += len(chunk)
                        if total_size > self.config.max_file_size:
                            logger.warning(f"File size exceeded during download: {url}")
                            return None
                
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
                
        # Apply content replacements
        html_str = str(soup)
        html_str = self._apply_replacements(html_str)
        
        return html_str, resource_urls
        
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
        processed_html, resource_list = self.processor.process_html(html_str, url)
        
        # Store main HTML
        self.resources['index.html'] = {
            'content': processed_html.encode('utf-8'),
            'type': 'text/html',
            'url': url
        }
        
        # Download resources
        logger.info(f"📦 Downloading {len(resource_list)} resources...")
        downloaded_count = 0
        
        for resource_type, resource_url, element in resource_list:
            # Skip if already downloaded
            resource_name = self._get_resource_name(resource_url)
            if resource_name in self.resources:
                continue
                
            # Download resource
            resource_result = self.downloader.download(resource_url, referer=url)
            if not resource_result:
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
                    logger.warning(f"Failed to process CSS: {str(e)}")
            
            # Optimize images if enabled
            if resource_type == 'img' and self.config.optimize_images:
                if any(img_type in resource_content_type.lower() for img_type in ['image/jpeg', 'image/png', 'image/jpg']):
                    resource_content = self.processor.optimize_image(resource_content, self.config.max_image_size)
            
            # Store resource
            self.resources[resource_name] = {
                'content': resource_content,
                'type': resource_content_type,
                'url': resource_url
            }
            
            downloaded_count += 1
            
        logger.info(f"✅ Downloaded {downloaded_count} resources successfully")
        
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

