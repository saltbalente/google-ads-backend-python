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
                
        # Extract and update script sources
        for script in soup.find_all('script', src=True):
            full_url = urljoin(base_url, script['src'])
            resource_urls.append(('js', full_url, script))
            
        # Extract and update images
        for img in soup.find_all('img', src=True):
            full_url = urljoin(base_url, img['src'])
            resource_urls.append(('img', full_url, img))
            
        # Extract srcset images
        for img in soup.find_all('img', srcset=True):
            srcset = img['srcset']
            for part in srcset.split(','):
                url_part = part.strip().split()[0]
                full_url = urljoin(base_url, url_part)
                resource_urls.append(('img', full_url, None))
                
        # Extract background images from inline styles
        for element in soup.find_all(style=True):
            style = element['style']
            bg_urls = self._extract_background_urls(style, base_url)
            resource_urls.extend([('img', url, None) for url in bg_urls])
            
        # Extract and update favicon
        for link in soup.find_all('link', rel=lambda r: r and 'icon' in r.lower()):
            if link.get('href'):
                full_url = urljoin(base_url, link['href'])
                resource_urls.append(('img', full_url, link))
                
        # Extract inline CSS
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                css_urls = self._extract_urls_from_css(style_tag.string, base_url)
                resource_urls.extend([('css_asset', url, None) for url in css_urls])
        
        # Neutralize all non-WhatsApp links (replace with #)
        self._neutralize_links(soup)
                
        # Apply content replacements
        html_str = str(soup)
        html_str = self._apply_replacements(html_str)
        
        return html_str, resource_urls
        
    def process_css(self, css_content: str, base_url: str) -> Tuple[str, List[str]]:
        """
        Process CSS content and extract resource URLs
        Returns: (processed_css, list_of_resource_urls)
        """
        resource_urls = self._extract_urls_from_css(css_content, base_url)
        return css_content, resource_urls
        
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

