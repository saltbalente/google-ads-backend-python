import os
import base64
import json
import time
import re
import random
import unicodedata
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable, Tuple
import io
import uuid
import hashlib
import time

import requests
from PIL import Image
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv
from google.protobuf.field_mask_pb2 import FieldMask

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
DEFAULT_PUBLIC_DOMAIN = os.getenv("DEFAULT_PUBLIC_LANDING_DOMAIN", "consultadebrujosgratis.store")

# Color Palettes for Landing Pages
COLOR_PALETTES = {
    "mystical": {
        "primary": "#8B5CF6",      # mystic-500
        "secondary": "#F59E0B",    # gold-500
        "accent": "#EC4899",       # pink-500
        "background": "#0F172A",   # slate-900
        "surface": "#1E293B",      # slate-800
        "text": "#F8FAFC",         # slate-50
        "textSecondary": "#94A3B8" # slate-400
    },
    "oceanic": {
        "primary": "#06B6D4",      # cyan-500
        "secondary": "#0891B2",    # cyan-600
        "accent": "#0EA5E9",       # sky-500
        "background": "#0C4A6E",   # sky-900
        "surface": "#075985",      # sky-800
        "text": "#F0FDFA",         # teal-50
        "textSecondary": "#5EEAD4" # teal-300
    },
    "forest": {
        "primary": "#16A34A",      # green-600
        "secondary": "#15803D",    # green-700
        "accent": "#65A30D",       # lime-600
        "background": "#14532D",   # green-900
        "surface": "#166534",      # green-800
        "text": "#F0FDF4",         # green-50
        "textSecondary": "#86EFAC" # green-300
    },
    "sunset": {
        "primary": "#EA580C",      # orange-600
        "secondary": "#DC2626",    # red-600
        "accent": "#EC4899",       # pink-500
        "background": "#7C2D12",   # orange-900
        "surface": "#9A3412",      # orange-800
        "text": "#FFF7ED",         # orange-50
        "textSecondary": "#FED7AA" # orange-200
    },
    "cosmic": {
        "primary": "#1E1B4B",      # indigo-950 - Azul cósmico profundo
        "secondary": "#581C87",    # violet-900 - Púrpura espacial
        "accent": "#C4B5FD",       # violet-300 - Plata cósmica
        "background": "#0F0A19",   # Negro espacial
        "surface": "#1F1633",      # Violeta muy oscuro
        "text": "#F5F3FF",         # Indigo-50 - Blanco cósmico
        "textSecondary": "#A5B4FC" # Indigo-300 - Azul claro cósmico
    }
}

# Paragraph Templates for AI Optimization
PARAGRAPH_TEMPLATES = {
    "curandero_services": "Soy un curandero experto con años de experiencia ayudando a personas a recuperar su bienestar espiritual y emocional. Mis servicios están garantizados y son totalmente confidenciales.",
    "consultoria_esoterica": "Ofrezco consultoría esotérica profesional para guiarte en los momentos más difíciles. Utilizo técnicas ancestrales para brindarte claridad y soluciones efectivas.",
    "lectura_cartas": "Lectura de cartas profesional y detallada para revelar tu pasado, presente y futuro. Obtén respuestas claras a tus preguntas más profundas.",
    "limpieza_energetica": "Realizo limpiezas energéticas profundas para eliminar bloqueos y atraer energía positiva a tu vida. Siente la diferencia desde la primera sesión.",
    "amarres_amor": "Especialista en amarres de amor efectivos y seguros. Recupera a tu pareja y fortalece tu relación con mis rituales personalizados."
}



@dataclass
class AdGroupContext:
    keywords: List[str]
    headlines: List[str]
    descriptions: List[str]
    locations: List[str]
    primary_keyword: str


@dataclass
class GeneratedContent:
    headline_h1: str
    subheadline: str
    cta_text: str
    social_proof: List[str]
    benefits: List[str]
    seo_title: str
    seo_description: str
    additional_ctas: List[Dict[str, str]]
    optimized_paragraph: str = ""


@dataclass
class ImageOptimizationMetrics:
    """Métricas de optimización de imágenes con IA"""
    original_size: int
    optimized_size: int
    reduction_percentage: float
    processing_time: float
    position: str
    ai_used: bool
    format_conversion: str  # e.g., "PNG -> WebP"
    resolution: str  # e.g., "1920x1080 -> 1600x900"


@dataclass
class ImageOptimizationMetrics:
    """Métricas de optimización de imágenes con IA"""
    original_size: int
    optimized_size: int
    reduction_percentage: float
    processing_time: float
    position: str
    ai_used: bool
    format_conversion: str  # e.g., "PNG -> WebP"
    resolution: str  # e.g., "1920x1080 -> 1600x900"


class LandingPageGenerator:
    def __init__(
        self,
        google_ads_client_provider: Optional[Callable[[], Any]] = None,
        openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o"),
        github_owner: str = os.getenv("GITHUB_REPO_OWNER", ""),
        github_repo: str = os.getenv("GITHUB_REPO_NAME", "monorepo-landings"),
        github_token: str = os.getenv("GITHUB_TOKEN", ""),
        templates_dir: str = os.getenv("LANDING_TEMPLATES_DIR", "templates/landing"),
        base_domain: str = os.getenv("LANDINGS_BASE_DOMAIN", "tudominio.com"),
        custom_domain: Optional[str] = os.getenv("GITHUB_PAGES_CUSTOM_DOMAIN"),
        public_base_url: Optional[str] = os.getenv("LANDING_PUBLIC_BASE_URL"),
        max_retries: int = 5,
        request_timeout: int = 60,
        health_check_timeout: int = 30,
    ):
        # Comprehensive environment validation
        required_env_vars = {
            "OPENAI_API_KEY": "OpenAI API key is required for content generation",
            "GITHUB_REPO_OWNER": "GitHub repository owner is required",
            "GITHUB_TOKEN": "GitHub token is required for repository access",
        }

        optional_env_vars = {
            "VERCEL_TOKEN": "Vercel token for deployment (optional)",
            "VERCEL_PROJECT_ID": "Vercel project ID (optional)",
        }

        missing_vars = []
        for var, message in required_env_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{var}: {message}")

        if missing_vars:
            raise ValueError(f"Missing required environment variables:\n" + "\n".join(missing_vars))

        # Log optional vars
        for var, message in optional_env_vars.items():
            if not os.getenv(var):
                logger.warning(f"Optional environment variable not set: {var} - {message}")

        # Additional validations
        if not github_owner.strip():
            raise ValueError("GITHUB_REPO_OWNER cannot be empty")
        if not github_token.strip():
            raise ValueError("GITHUB_TOKEN cannot be empty")

        self.google_ads_client_provider = google_ads_client_provider
        self.openai_model = openai_model
        self.github_owner = github_owner.strip()
        self.github_repo = github_repo.strip()
        self.github_token = github_token.strip()

        # Templates directory validation
        td = templates_dir
        if not os.path.isabs(td):
            td = os.path.abspath(os.path.join(os.path.dirname(__file__), td))
        if not os.path.exists(td):
            raise ValueError(f"Templates directory does not exist: {td}")
        if not os.path.isdir(td):
            raise ValueError(f"Templates path is not a directory: {td}")

        self.templates_dir = td
        self.env = Environment(loader=FileSystemLoader(td), autoescape=select_autoescape(["html"]))

        # Domain validation
        if not base_domain or not base_domain.strip():
            raise ValueError("LANDINGS_BASE_DOMAIN cannot be empty")
        self.base_domain = base_domain.strip()
        self.custom_domain = custom_domain.strip() if custom_domain else None
        self.public_base_url = self._normalize_public_base_url(public_base_url or self.custom_domain or DEFAULT_PUBLIC_DOMAIN)
        if not self.public_base_url:
            logger.warning("No public landing domain configured; defaulting to GitHub Pages URLs")

        # Configuration parameters
        self.max_retries = max(1, max_retries)
        self.request_timeout = max(10, request_timeout)
        self.health_check_timeout = max(5, health_check_timeout)

        logger.info(f"LandingPageGenerator initialized successfully with model: {self.openai_model}")

    def _normalize_public_base_url(self, base: Optional[str]) -> Optional[str]:
        if not base:
            return None
        base = base.strip()
        if not base:
            return None
        if not base.startswith(("http://", "https://")):
            base = f"https://{base}"
        return base.rstrip("/")

    def _get_public_url(self, folder_name: str) -> str:
        if self.public_base_url:
            return f"{self.public_base_url}/{folder_name}/"
        # Fallback to GitHub Pages when no domain is configured
        return f"https://{self.github_owner}.github.io/{self.github_repo}/{folder_name}/"

    def _get_google_ads_client(self):
        """Get Google Ads client with comprehensive error handling."""
        if self.google_ads_client_provider:
            try:
                client = self.google_ads_client_provider()
                if not client:
                    raise ValueError("Google Ads client provider returned None")
                return client
            except Exception as e:
                raise RuntimeError(f"Failed to get Google Ads client from provider: {str(e)}")

        try:
            from app import get_google_ads_client
            client = get_google_ads_client()
            if not client:
                raise ValueError("get_google_ads_client() returned None")
            return client
        except ImportError:
            raise ImportError("Google Ads client provider not available and app.get_google_ads_client not found")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Ads client: {str(e)}")

    def extract_ad_group_context(self, customer_id: str, ad_group_id: str) -> AdGroupContext:
        """Extract comprehensive context from Google Ads Ad Group with robust error handling."""
        # Input validation
        if not customer_id or not isinstance(customer_id, str):
            raise ValueError("customer_id must be a non-empty string")
        if not ad_group_id or not isinstance(ad_group_id, str):
            raise ValueError("ad_group_id must be a non-empty string")

        logger.info(f"Extracting context for Customer ID: {customer_id}, Ad Group ID: {ad_group_id}")

        try:
            client = self._get_google_ads_client()
            svc = client.get_service("GoogleAdsService")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Ads client: {str(e)}")

        # Normalize IDs
        customer_id = customer_id.replace("-", "")
        ad_group_id = ad_group_id.replace("-", "")

        if not customer_id.isdigit():
            raise ValueError(f"Invalid customer_id format: {customer_id}")
        if not ad_group_id.isdigit():
            raise ValueError(f"Invalid ad_group_id format: {ad_group_id}")

        keywords = []
        headlines = []
        descriptions = []
        locations = []

        # Extract keywords with multiple fallback strategies
        keywords = self._extract_keywords(svc, customer_id, ad_group_id)

        # Extract ad content
        headlines, descriptions = self._extract_ad_content(svc, customer_id, ad_group_id)

        # Extract locations
        locations = self._extract_locations(svc, customer_id, ad_group_id)

        # Determine primary keyword
        primary_keyword = self._determine_primary_keyword(keywords, headlines, descriptions)

        context = AdGroupContext(
            keywords=keywords,
            headlines=headlines,
            descriptions=descriptions,
            locations=locations,
            primary_keyword=primary_keyword
        )

        logger.info(f"Context extraction completed: {len(keywords)} keywords, {len(headlines)} headlines, {len(descriptions)} descriptions, {len(locations)} locations")
        return context

    def _extract_keywords(self, svc, customer_id: str, ad_group_id: str) -> List[str]:
        """Extract keywords from Ad Group with multiple fallback strategies."""
        logger.info("Extracting keywords from Ad Group")

        # Primary query for active keywords
        try:
            kw_query = f"""
                SELECT ad_group_criterion.criterion_id,
                       ad_group_criterion.keyword.text,
                       metrics.impressions
                FROM keyword_view
                WHERE ad_group_criterion.status != REMOVED
                  AND ad_group.id = {ad_group_id}
                ORDER BY metrics.impressions DESC
                LIMIT 50
            """
            kw_rows = svc.search(customer_id=customer_id, query=kw_query)
            keywords = []
            for row in kw_rows:
                text = row.ad_group_criterion.keyword.text
                if text and text.strip():
                    keywords.append(text.strip())

            if keywords:
                logger.info(f"Found {len(keywords)} keywords from primary query")
                return keywords[:10]  # Limit to top 10

        except Exception as e:
            logger.warning(f"Primary keywords query failed: {str(e)}")

        # Fallback 1: All keywords regardless of status
        try:
            kw_fallback = svc.search(customer_id=customer_id, query=f"""
                SELECT ad_group_criterion.keyword.text, metrics.impressions
                FROM keyword_view
                WHERE ad_group.id = {ad_group_id}
                ORDER BY metrics.impressions DESC
                LIMIT 20
            """)
            keywords = [r.ad_group_criterion.keyword.text.strip() for r in kw_fallback if r.ad_group_criterion.keyword.text and r.ad_group_criterion.keyword.text.strip()]
            if keywords:
                logger.info(f"Found {len(keywords)} keywords from fallback query")
                return keywords[:10]
        except Exception as e:
            logger.warning(f"Fallback keywords query failed: {str(e)}")

        # Fallback 2: Keywords from ad group criteria directly
        try:
            criteria_query = f"""
                SELECT ad_group_criterion.keyword.text
                FROM ad_group_criterion
                WHERE ad_group.id = {ad_group_id}
                  AND ad_group_criterion.type = KEYWORD
                LIMIT 10
            """
            criteria_rows = svc.search(customer_id=customer_id, query=criteria_query)
            keywords = [r.ad_group_criterion.keyword.text.strip() for r in criteria_rows if r.ad_group_criterion.keyword.text and r.ad_group_criterion.keyword.text.strip()]
            if keywords:
                logger.info(f"Found {len(keywords)} keywords from criteria query")
                return keywords
        except Exception as e:
            logger.warning(f"Criteria keywords query failed: {str(e)}")

        logger.warning("No keywords found from any query")
        return []

    def _extract_ad_content(self, svc, customer_id: str, ad_group_id: str) -> Tuple[List[str], List[str]]:
        """Extract headlines and descriptions from ads."""
        logger.info("Extracting ad content (headlines and descriptions)")

        headlines = []
        descriptions = []

        try:
            ads_query = f"""
                SELECT ad_group_ad.ad.id,
                       ad_group_ad.ad.responsive_search_ad.headlines,
                       ad_group_ad.ad.responsive_search_ad.descriptions,
                       metrics.impressions,
                       metrics.clicks
                FROM ad_group_ad
                WHERE ad_group_ad.ad.type = RESPONSIVE_SEARCH_AD
                  AND ad_group_ad.status != REMOVED
                  AND ad_group.id = {ad_group_id}
                ORDER BY metrics.impressions DESC
                LIMIT 10
            """
            ads_rows = svc.search(customer_id=customer_id, query=ads_query)

            for row in ads_rows:
                ad = row.ad_group_ad.ad
                if ad.responsive_search_ad:
                    # Extract headlines
                    if ad.responsive_search_ad.headlines:
                        for h in ad.responsive_search_ad.headlines:
                            if h.text and h.text.strip():
                                headlines.append(h.text.strip())

                    # Extract descriptions
                    if ad.responsive_search_ad.descriptions:
                        for d in ad.responsive_search_ad.descriptions:
                            if d.text and d.text.strip():
                                descriptions.append(d.text.strip())

            logger.info(f"Extracted {len(headlines)} headlines and {len(descriptions)} descriptions")

        except Exception as e:
            logger.error(f"Failed to extract ad content: {str(e)}")

        return headlines[:10], descriptions[:10]  # Limit results

    def _extract_locations(self, svc, customer_id: str, ad_group_id: str) -> List[str]:
        """Extract location targeting from campaign."""
        logger.info("Extracting location targeting")

        locations = []

        try:
            # Get campaign resource name first
            camp_query = f"SELECT ad_group.campaign FROM ad_group WHERE ad_group.id = {ad_group_id}"
            camp_rows = svc.search(customer_id=customer_id, query=camp_query)

            campaign_resource_name = None
            for row in camp_rows:
                campaign_resource_name = row.ad_group.campaign
                break

            if campaign_resource_name:
                logger.info(f"Found campaign: {campaign_resource_name}")

                # Get locations from campaign
                loc_query = f"""
                    SELECT campaign_criterion.criterion_id,
                           campaign_criterion.location.geo_target_constant
                    FROM campaign_criterion
                    WHERE campaign_criterion.type = LOCATION
                      AND campaign.resource_name = '{campaign_resource_name}'
                    LIMIT 20
                """
                loc_rows = svc.search(customer_id=customer_id, query=loc_query)

                for row in loc_rows:
                    rn = row.campaign_criterion.location.geo_target_constant
                    if rn:
                        locations.append(str(rn))

                logger.info(f"Found {len(locations)} location targets")
            else:
                logger.warning("No campaign found for ad group")

        except Exception as e:
            logger.error(f"Failed to extract locations: {str(e)}")

        return locations

    def _determine_primary_keyword(self, keywords: List[str], headlines: List[str], descriptions: List[str]) -> str:
        """Determine the most relevant primary keyword."""
        if keywords:
            return keywords[0]

        # Fallback: extract from headlines
        if headlines:
            # Find the most common words in headlines
            from collections import Counter
            words = []
            for headline in headlines[:3]:  # Check top headlines
                words.extend(re.findall(r'\b\w+\b', headline.lower()))

            # Filter out common stop words
            stop_words = {'de', 'la', 'el', 'en', 'y', 'a', 'que', 'los', 'las', 'un', 'una', 'con', 'por', 'para'}
            filtered_words = [w for w in words if w not in stop_words and len(w) > 2]

            if filtered_words:
                most_common = Counter(filtered_words).most_common(1)
                if most_common:
                    return most_common[0][0].title()

        # Last fallback: extract from descriptions
        if descriptions:
            words = []
            for desc in descriptions[:2]:
                words.extend(re.findall(r'\b\w+\b', desc.lower()))

            filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
            if filtered_words:
                most_common = Counter(filtered_words).most_common(1)
                if most_common:
                    return most_common[0][0].title()

        return "landing"

    def _detect_niche(self, keywords: List[str]) -> str:
        """Detect the niche based on keywords."""
        esoteric_keywords = [
            "amarre", "brujeria", "brujería", "hechizo", "retorno", "tarot", "vidente", 
            "espiritual", "limpia", "endulzamiento", "dominio", "separacion", "alejar",
            "magia", "negra", "blanca", "santeria", "santería"
        ]
        text = " ".join(keywords).lower()
        if any(k in text for k in esoteric_keywords):
            return "esoteric"
        return "general"

    def _generate_image_optimization_prompt(self, keywords: List[str], position: str) -> str:
        """Generate dynamic prompt for Gemini image optimization.
        
        Args:
            keywords: Keywords from the ad group
            position: Image position (top, middle, bottom, hero_bg, etc.)
        
        Returns:
            Optimized prompt string for Gemini
        """
        primary_keyword = keywords[0] if keywords else "servicio profesional"
        
        # Build context-aware prompt
        prompt_parts = [
            f"Optimiza esta imagen para una landing page de '{primary_keyword}'.",
            "Mantén la esencia visual y estilo de la imagen original.",
            "Mejora la estética, nitidez y coherencia visual.",
            "Asegúrate de que la imagen sea profesional y apta para publicidad."
        ]
        
        # Position-specific enhancements
        if position in ["top", "hero_bg"]:
            prompt_parts.append("Esta es la imagen principal/hero: debe ser impactante y captar atención inmediata.")
        elif position in ["benefits", "promo"]:
            prompt_parts.append("Esta imagen debe transmitir confianza y profesionalismo.")
        elif position.startswith("cta"):
            prompt_parts.append("Esta imagen debe motivar acción y conversión.")
        
        # Niche-specific context
        niche = self._detect_niche(keywords)
        if niche == "esoteric":
            prompt_parts.append("Debe tener un tono místico, espiritual y resonar emocionalmente.")
        
        prompt_parts.append("Genera una variación única y optimizada manteniendo los elementos clave.")
        
        return " ".join(prompt_parts)

    def _optimize_image_with_gemini(self, image_bytes: bytes, keywords: List[str], position: str) -> Tuple[bytes, ImageOptimizationMetrics]:
        """Optimize image using Gemini Vision API.
        
        Args:
            image_bytes: Original image bytes
            keywords: Keywords from ad group
            position: Image position in landing
        
        Returns:
            Tuple of (optimized_image_bytes, metrics)
        """
        start_time = time.time()
        original_size = len(image_bytes)
        
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai required. Install: pip install google-generativeai")
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable required for Gemini")
        
        genai.configure(api_key=api_key)
        
        # Load original image
        with io.BytesIO(image_bytes) as buf:
            original_image = Image.open(buf)
            original_format = original_image.format or "JPEG"
            original_resolution = f"{original_image.width}x{original_image.height}"
            
            # Convert to RGB if needed
            if original_image.mode in ('P', 'RGBA', 'LA', 'CMYK'):
                original_image = original_image.convert('RGB')
            
            # Load image data into memory before buffer closes
            original_image.load()
        
        logger.info(f"🤖 Starting Gemini optimization for {position} ({original_resolution}, {original_format})")
        
        # Generate prompt
        prompt = self._generate_image_optimization_prompt(keywords, position)
        
        # Use Gemini for image analysis and enhancement
        # Note: Gemini 2.0 Flash can analyze images, but cannot generate new images
        # We'll use it to analyze and then apply PIL enhancements based on analysis
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Convert image to bytes for Gemini
        with io.BytesIO() as temp_buf:
            original_image.save(temp_buf, format='JPEG', quality=95)
            img_data = temp_buf.getvalue()
        
        # Get AI analysis
        response = model.generate_content([
            prompt + " Analiza esta imagen y sugiere mejoras específicas (brillo, contraste, saturación, encuadre).",
            {"mime_type": "image/jpeg", "data": img_data}
        ])
        
        ai_suggestions = response.text
        logger.info(f"🧠 Gemini analysis: {ai_suggestions[:200]}...")
        
        # Apply AI-guided enhancements using PIL
        enhanced_image = self._apply_ai_enhancements(original_image, ai_suggestions)
        
        # Post-processing: compression and quality control
        optimized_bytes = self._post_process_image(enhanced_image, original_format)
        optimized_size = len(optimized_bytes)
        
        # Calculate metrics
        reduction_pct = ((original_size - optimized_size) / original_size) * 100 if original_size > 0 else 0
        processing_time = time.time() - start_time
        
        # Validate quality
        with io.BytesIO(optimized_bytes) as buf:
            final_img = Image.open(buf)
            final_img.load()  # Load into memory before buffer closes
            final_resolution = f"{final_img.width}x{final_img.height}"
        
        metrics = ImageOptimizationMetrics(
            original_size=original_size,
            optimized_size=optimized_size,
            reduction_percentage=round(reduction_pct, 2),
            processing_time=round(processing_time, 2),
            position=position,
            ai_used=True,
            format_conversion=f"{original_format} -> WebP",
            resolution=f"{original_resolution} -> {final_resolution}"
        )
        
        logger.info(f"✅ Optimized {position}: {original_size//1024}KB -> {optimized_size//1024}KB ({reduction_pct:.1f}% reduction, {processing_time:.1f}s)")
        
        return optimized_bytes, metrics
        
    def _apply_ai_enhancements(self, image: Image.Image, ai_suggestions: str) -> Image.Image:
        """Apply AI-suggested enhancements to image using PIL.
        
        Args:
            image: PIL Image object
            ai_suggestions: Text suggestions from Gemini
        
        Returns:
            Enhanced PIL Image
        """
        from PIL import ImageEnhance, ImageFilter
        
        enhanced = image.copy()
        suggestions_lower = ai_suggestions.lower()
        
        # Apply brightness adjustment
        if "oscur" in suggestions_lower or "brillo" in suggestions_lower or "brightness" in suggestions_lower:
            enhancer = ImageEnhance.Brightness(enhanced)
            enhanced = enhancer.enhance(1.15)  # Increase brightness 15%
            logger.info("📊 Applied brightness enhancement")
        
        # Apply contrast adjustment
        if "contrast" in suggestions_lower or "contraste" in suggestions_lower:
            enhancer = ImageEnhance.Contrast(enhanced)
            enhanced = enhancer.enhance(1.2)  # Increase contrast 20%
            logger.info("📊 Applied contrast enhancement")
        
        # Apply sharpness
        if "nitidez" in suggestions_lower or "sharp" in suggestions_lower or "blur" in suggestions_lower:
            enhanced = enhanced.filter(ImageFilter.SHARPEN)
            logger.info("📊 Applied sharpness filter")
        
        # Apply color saturation
        if "saturaci" in suggestions_lower or "color" in suggestions_lower or "vibrant" in suggestions_lower:
            enhancer = ImageEnhance.Color(enhanced)
            enhanced = enhancer.enhance(1.15)  # Increase saturation 15%
            logger.info("📊 Applied color saturation")
        
        return enhanced
    
    def _post_process_image(self, image: Image.Image, original_format: str) -> bytes:
        """Post-process image: resize, compress, convert to WebP.
        
        Args:
            image: PIL Image to process
            original_format: Original image format
        
        Returns:
            Optimized image bytes (WebP format)
        """
        # Resize if too large (responsive optimization)
        max_dimension = 1600
        if image.width > max_dimension or image.height > max_dimension:
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            logger.info(f"📏 Resized to max {max_dimension}px")
        
        # Quality control: minimum resolution
        min_dimension = 400
        if image.width < min_dimension or image.height < min_dimension:
            logger.warning(f"⚠️ Image below minimum resolution ({image.width}x{image.height})")
        
        # Remove EXIF metadata for privacy and smaller file size
        # Create new image without metadata
        data = list(image.getdata())
        image_without_exif = Image.new(image.mode, image.size)
        image_without_exif.putdata(data)
        logger.info("🔒 Removed EXIF metadata")
        
        # Convert to WebP with intelligent compression
        with io.BytesIO() as output_buf:
            # Use higher quality for small images, lower for large
            quality = 85 if max(image.width, image.height) < 800 else 80
            
            image_without_exif.save(
                output_buf, 
                format="WEBP", 
                quality=quality, 
                method=6, 
                optimize=True,
                exif=b''  # Ensure no EXIF data
            )
            return output_buf.getvalue()

    def _compress_image_standard(self, image_bytes: bytes, position: str) -> bytes:
        """Standard image compression without AI (fallback method).
        
        Args:
            image_bytes: Original image bytes
            position: Image position
        
        Returns:
            Compressed WebP bytes
        """
        with io.BytesIO(image_bytes) as input_buf:
            image = Image.open(input_buf)
            original_format = image.format or "JPEG"
            
            # Convert to RGB if mode is not compatible
            if image.mode in ('P', 'CMYK', 'RGBA', 'LA'):
                image = image.convert('RGB')
            
            # Resize if too large
            max_dimension = 1600
            if image.width > max_dimension or image.height > max_dimension:
                image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                logger.info(f"📏 Resized {position} to max {max_dimension}px")
            
            # Remove EXIF metadata
            data = list(image.getdata())
            image_without_exif = Image.new(image.mode, image.size)
            image_without_exif.putdata(data)
            logger.info(f"🔒 Removed EXIF metadata from {position}")
            
            with io.BytesIO() as output_buf:
                # Save as WebP with compression (no EXIF)
                image_without_exif.save(
                    output_buf, 
                    format="WEBP", 
                    quality=80, 
                    optimize=True,
                    exif=b''
                )
                return output_buf.getvalue()

    def _system_prompt(self, niche: str = "general", paragraph_template_text: Optional[str] = None) -> str:
        base_prompt = (
            "Eres un generador experto de contenido para Landing Pages de alta conversión. "
            "Recibirás contexto de un Ad Group de Google Ads con keywords principales, mensajes de anuncios y ubicación. "
            "Responde SOLO con un JSON válido con las claves: "
            "headline_h1, subheadline, cta_text, social_proof (lista de 3 strings con testimonios falsos pero altamente creíbles y persuasivos), benefits (lista de 4 strings), "
            "seo_title, seo_description, additional_ctas (lista de 4 objetos, cada uno con 'headline', 'tag', 'description'), "
            "optimized_paragraph (string, párrafo de alta conversión basado en el template proporcionado). "
        )
        
        if niche == "esoteric":
            base_prompt += (
                "DETECTADO NICHO ESOTÉRICO/BRUJERÍA. "
                "IMPORTANTE: Genera headlines con ALTA URGENCIA y CONEXIÓN EMOCIONAL. "
                "Usa palabras como 'Inmediato', 'Hoy Mismo', 'Garantizado', 'Recupera', 'Regresa'. "
                "El tono debe ser místico pero directo y seguro. "
                "Enfócate en solucionar el dolor del usuario (amor perdido, mala suerte) AHORA MISMO. "
                "Ejemplos de H1: 'Recupera a tu Pareja Hoy Mismo - Amarres Garantizados', '¿Sientes que se Aleja? Haz que Regrese Suplicando'. "
            )
        else:
            base_prompt += "El tono debe alinearse con los titulares y la keyword principal. "

        if paragraph_template_text:
            base_prompt += (
                f"\n\nPARA optimized_paragraph: DEBES reescribir y optimizar el siguiente texto base "
                f"usando las keywords proporcionadas. Mantén la estructura profesional, agrega urgencia sutil y "
                f"asegúrate de que el texto sea fácil de leer y persuasivo:\n\n"
                f"\"{paragraph_template_text}\"\n\n"
                f"Integra las keywords de forma natural y mantén un tono profesional pero cercano."
            )
        else:
            base_prompt += (
                "\n\nPARA optimized_paragraph: Como no se proporcionó paragraph_template, "
                "deja optimized_paragraph vacío ('')."
            )
        
        base_prompt += "\n\nUsa el idioma del usuario en español mexicano."
        return base_prompt

    def generate_content(self, ctx: AdGroupContext, paragraph_template: Optional[str] = None) -> GeneratedContent:
        """Generate landing page content using AI with comprehensive error handling."""
        if not ctx or not isinstance(ctx, AdGroupContext):
            raise ValueError("Valid AdGroupContext is required")

        logger.info(f"Generating content using model: {self.openai_model}")

        # Validate context has minimum required data
        if not ctx.keywords and not ctx.headlines and not ctx.descriptions:
            raise ValueError("AdGroupContext must contain at least keywords, headlines, or descriptions")

        # Get template text if template is specified
        template_text = None
        if paragraph_template and paragraph_template != "none" and paragraph_template in PARAGRAPH_TEMPLATES:
            template_text = PARAGRAPH_TEMPLATES[paragraph_template]
            logger.info(f"Using paragraph template: {paragraph_template}")

        payload = {
            "keywords": ctx.keywords[:5],  # Limit to prevent token overflow
            "headlines": ctx.headlines[:5],
            "descriptions": ctx.descriptions[:5],
            "locations": ctx.locations[:3],
            "primary_keyword": ctx.primary_keyword or "servicio"
        }

        # Detect niche for prompt fine-tuning
        niche = self._detect_niche(ctx.keywords + [ctx.primary_keyword or ""])
        logger.info(f"Detected niche: {niche}")

        content = ""

        try:
            if self.openai_model.startswith("gemini"):
                content = self._generate_with_gemini(payload, niche, template_text)
            else:
                content = self._generate_with_openai(payload, niche, template_text)
        except Exception as e:
            logger.error(f"AI content generation failed: {str(e)}")
            raise RuntimeError(f"Failed to generate content with {self.openai_model}: {str(e)}")

        logger.info("AI response received, processing JSON")
        return self._parse_ai_response(content)

    def _generate_with_gemini(self, payload: dict, niche: str = "general", template_text: Optional[str] = None) -> str:
        """Generate content using Google Gemini API."""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai package is required for Gemini models. Install with: pip install google-generativeai")

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required for Gemini models")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.openai_model)

        prompt = f"{self._system_prompt(niche, template_text)}\n\nContexto:\n{json.dumps(payload, ensure_ascii=False)}"

        generation_config = genai.types.GenerationConfig(temperature=0.7)

        # Use JSON mode for newer models
        if "1.5" in self.openai_model:
            generation_config.response_mime_type = "application/json"

        response = model.generate_content(prompt, generation_config=generation_config)

        if not response or not response.text:
            raise RuntimeError("Gemini API returned empty response")

        return response.text

    def _generate_with_openai(self, payload: dict, niche: str = "general", template_text: Optional[str] = None) -> str:
        """Generate content using OpenAI API."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is required")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        request_payload = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": self._system_prompt(niche, template_text)},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=request_payload,
            timeout=self.request_timeout
        )

        if response.status_code != 200:
            error_msg = f"OpenAI API error: {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg += f" - {error_data['error'].get('message', 'Unknown error')}"
            except:
                error_msg += f" - {response.text[:200]}"
            raise RuntimeError(error_msg)

        result = response.json()
        if "choices" not in result or not result["choices"]:
            raise RuntimeError("OpenAI API returned no choices")

        content = result["choices"][0]["message"]["content"]
        if not content:
            raise RuntimeError("OpenAI API returned empty content")

        return content

    def _parse_ai_response(self, content: str) -> GeneratedContent:
        """Parse and validate AI response content."""
        if not content or not isinstance(content, str):
            raise RuntimeError("AI returned empty or invalid content")

        # Strip markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        content = content.strip()
        if not content:
            raise RuntimeError("AI returned empty content after stripping markdown")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Raw content (first 500 chars): {content[:500]}")
            raise RuntimeError(f"AI returned invalid JSON: {str(e)}")

        # Validate required keys
        required_keys = ["headline_h1", "subheadline", "cta_text", "social_proof", "benefits", "seo_title", "seo_description"]
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            raise RuntimeError(f"AI response missing required keys: {missing_keys}")

        # Validate and sanitize data
        try:
            return GeneratedContent(
                headline_h1=str(data["headline_h1"]).strip(),
                subheadline=str(data["subheadline"]).strip(),
                cta_text=str(data["cta_text"]).strip(),
                social_proof=[str(p).strip() for p in data.get("social_proof", [])[:3] if p],
                benefits=[str(b).strip() for b in data.get("benefits", [])[:4] if b],
                seo_title=str(data["seo_title"]).strip(),
                seo_description=str(data["seo_description"]).strip(),
                additional_ctas=data.get("additional_ctas", []),
                optimized_paragraph=str(data.get("optimized_paragraph", "")).strip()
            )
        except Exception as e:
            raise RuntimeError(f"Error processing AI response data: {str(e)}")

    def render(self, gen: GeneratedContent, config: Dict[str, Any], selected_color_palette: str = "mystical") -> str:
        try:
            # Get color palette
            color_palette = COLOR_PALETTES.get(selected_color_palette, COLOR_PALETTES["mystical"])
            
            # Check if custom template content is provided (from custom templates)
            custom_template_content = config.get("custom_template_content")
            
            if custom_template_content:
                # Use the custom template content directly
                # This is a complete HTML file, not a Jinja2 template
                logger.info(f"🎨 Using custom template content ({len(custom_template_content)} chars)")
                
                # The custom template is already a complete HTML, just do variable substitutions
                html = custom_template_content
                import re
                
                # Get values from config
                whatsapp_number = config.get("whatsapp_number", "")
                phone_number = config.get("phone_number", whatsapp_number)
                gtm_id = config.get("gtm_id", "")
                
                # Replace WhatsApp URLs - multiple patterns
                if whatsapp_number:
                    # Clean the number for URL (remove +, spaces, dashes)
                    clean_number = whatsapp_number.replace("+", "").replace(" ", "").replace("-", "")
                    
                    # Pattern 1: wa.me URLs
                    html = re.sub(r'href="https://wa\.me/\d+"', f'href="https://wa.me/{clean_number}"', html)
                    html = re.sub(r"href='https://wa\.me/\d+'", f"href='https://wa.me/{clean_number}'", html)
                    
                    # Pattern 2: api.whatsapp.com URLs
                    html = re.sub(r'href="https://api\.whatsapp\.com/send\?phone=\d+"', f'href="https://api.whatsapp.com/send?phone={clean_number}"', html)
                    html = re.sub(r"href='https://api\.whatsapp\.com/send\?phone=\d+'", f"href='https://api.whatsapp.com/send?phone={clean_number}'", html)
                    
                    # Pattern 3: Replace phone numbers in text content (formatted display)
                    # Look for patterns like +1 803 549 8658 or +18035498658
                    html = re.sub(r'\+1\s*\d{3}\s*\d{3}\s*\d{4}', whatsapp_number, html)
                    html = re.sub(r'\+\d{10,15}', whatsapp_number, html)
                    
                    logger.info(f"📱 Replaced WhatsApp number with: {whatsapp_number}")
                
                # Replace phone numbers in tel: links
                if phone_number:
                    # Pattern for tel: links
                    html = re.sub(r'href="tel:\+?\d+"', f'href="tel:{phone_number}"', html)
                    html = re.sub(r"href='tel:\+?\d+'", f"href='tel:{phone_number}'", html)
                    logger.info(f"📞 Replaced phone number with: {phone_number}")
                
                # Replace GTM ID
                if gtm_id:
                    html = re.sub(r'GTM-[A-Z0-9]{6,10}', gtm_id, html)
                    logger.info(f"📊 Replaced GTM ID with: {gtm_id}")
                
                # Add tracking pixels if not present
                if gtm_id and 'gtm.js' not in html.lower():
                    gtm_script = f'''
    <!-- Google Tag Manager -->
    <script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
    new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
    j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
    'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
    }})(window,document,'script','dataLayer','{gtm_id}');</script>
    <!-- End Google Tag Manager -->'''
                    # Insert after <head> tag
                    html = re.sub(r'(<head[^>]*>)', r'\1' + gtm_script, html, count=1)
                    logger.info(f"📈 Injected GTM script for: {gtm_id}")
                
                return html
            
            # Initialize template_name variable
            template_name = None
            
            # Check if template is explicitly selected from iOS app
            selected_template = config.get("selected_template")

            if selected_template:
                # El nombre del template ya viene con .html desde la app
                template_name = selected_template if selected_template.endswith('.html') else f"{selected_template}.html"
                
                # Validate selected template exists
                available_templates = self.get_available_templates()
                if template_name in available_templates:
                    logger.info(f"🎨 Using user-selected template: {template_name}")
                else:
                    logger.warning(f"⚠️ Selected template '{template_name}' not available, falling back to auto-selection")
                    template_name = None  # Reset to trigger auto-selection

            # Only auto-select if no valid template was specified
            if not template_name:
                # Seleccionar template basado en la palabra clave principal (auto-selection)
                primary_keyword = config.get("primary_keyword", "").lower()

                # Lógica de selección de template
                if "tarot" in primary_keyword or "cartas" in primary_keyword:
                    template_name = "mystical.html"  # Template místico para tarot
                elif "brujeria" in primary_keyword or "brujo" in primary_keyword or "amarres" in primary_keyword:
                    template_name = "jose-amp.html"  # Template AMP para brujería y amarres
                elif "amor" in primary_keyword or "pareja" in primary_keyword:
                    template_name = "romantic.html"  # Template romántico para temas de amor
                elif "dinero" in primary_keyword or "riqueza" in primary_keyword:
                    template_name = "prosperity.html"  # Template de prosperidad
                else:
                    template_name = "base.html"  # Template por defecto

                logger.info(f"🎨 Auto-selected template based on keyword: {template_name}")

            tpl = self.env.get_template(template_name)
        except Exception as e:
            # Fallback a base.html si el template específico no existe
            try:
                tpl = self.env.get_template("base.html")
            except Exception as fallback_error:
                raise RuntimeError(f"Template 'base.html' not found or invalid: {str(fallback_error)}")

        # Process user images
        user_images = config.get("user_images", [])
        img_context = {}
        if user_images:
            for img in user_images:
                pos = img.get("position", "").lower()
                url = img.get("url", "")
                if pos and url:
                    img_context[f"user_image_{pos}"] = url
        
        # Process user videos
        user_videos = config.get("user_videos", [])
        video_context = {}
        if user_videos:
            for video in user_videos:
                pos = video.get("position", "").lower()
                video_url = video.get("video_url", "")
                thumbnail_url = video.get("thumbnail_url", "")
                if pos and video_url:
                    video_context[f"user_video_{pos}"] = video_url
                    if thumbnail_url:
                        video_context[f"user_video_{pos}_thumbnail"] = thumbnail_url

        try:
            # Shuffle additional CTAs for variety
            additional_ctas = getattr(gen, 'additional_ctas', [])
            if additional_ctas:
                random.shuffle(additional_ctas)

            return tpl.render(
                headline_h1=gen.headline_h1,
                subheadline=gen.subheadline,
                cta_text=gen.cta_text,
                social_proof=gen.social_proof,
                benefits=gen.benefits,
                seo_title=gen.seo_title,
                seo_description=gen.seo_description,
                additional_ctas=additional_ctas,
                optimized_paragraph=getattr(gen, 'optimized_paragraph', ''),
                whatsapp_number=config["whatsapp_number"],
                phone_number=config.get("phone_number", config["whatsapp_number"]),
                webhook_url=config.get("webhook_url", ""),
                gtm_id=config["gtm_id"],
                primary_keyword=config.get("primary_keyword", ""),
                user_images=user_images,  # Pass the full list for templates that need it
                user_videos=user_videos,  # Pass the full list for templates that need it
                color_palette=color_palette,  # Add color palette to template context
                **img_context,
                **video_context
            )
        except Exception as e:
            raise RuntimeError(f"Template rendering failed: {str(e)}")

    def get_available_templates(self) -> List[str]:
        """Get list of available landing page templates."""
        try:
            templates_dir = self.env.loader.searchpath[0] if self.env.loader.searchpath else "templates/landing"
            import os
            if os.path.exists(templates_dir):
                templates = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
                return sorted(templates)
            else:
                # Fallback to hardcoded list if directory not found
                return ["base.html", "mystical.html", "prosperity.html", "romantic.html"]
        except Exception as e:
            logger.warning(f"Could not list templates: {str(e)}, using fallback list")
            return ["base.html", "mystical.html", "prosperity.html", "romantic.html"]

    def get_template_info(self) -> Dict[str, Dict[str, str]]:
        """Get information about available templates for iOS app selection."""
        templates = self.get_available_templates()
        template_info = {}

        for template in templates:
            template_name = template.replace('.html', '')

            # Provide user-friendly names and descriptions
            if template_name == "base":
                template_info[template] = {
                    "name": "Clásica",
                    "description": "Diseño clásico y profesional",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "base_optimized":
                template_info[template] = {
                    "name": "🚀 Optimizada Pro",
                    "description": "Conversión 5x • 7 CTAs • Tracking avanzado • SEO potenciado",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "mystical":
                template_info[template] = {
                    "name": "Mística",
                    "description": "Perfecta para tarot, videncia y temas espirituales",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "romantic":
                template_info[template] = {
                    "name": "Romántica",
                    "description": "Ideal para temas de amor y relaciones",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "prosperity":
                template_info[template] = {
                    "name": "Prosperidad",
                    "description": "Diseñada para dinero, riqueza y abundancia",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "llama-gemela":
                template_info[template] = {
                    "name": "Llama Gemela",
                    "description": "Rituales de amor y reconciliación",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "llamado-del-alma":
                template_info[template] = {
                    "name": "El Llamado del Alma",
                    "description": "Sanación espiritual y chamanismo",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "el-libro-prohibido":
                template_info[template] = {
                    "name": "El Libro Prohibido",
                    "description": "Magia negra y trabajos fuertes",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "la-luz":
                template_info[template] = {
                    "name": "La Luz",
                    "description": "Magia blanca y sanación angelical",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            else:
                template_info[template] = {
                    "name": template_name.title(),
                    "description": f"Template {template_name}",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }

        return template_info

    def get_ad_group_final_url(self, customer_id: str, ad_group_id: str) -> Optional[str]:
        """
        Retrieves the final URL from the first available ad in the ad group.
        """
        try:
            client = self._get_google_ads_client()
            ga_service = client.get_service("GoogleAdsService")
            
            # Normalize IDs
            customer_id = customer_id.replace("-", "")
            ad_group_id = ad_group_id.replace("-", "")
            
            query = f"""
                SELECT ad_group_ad.ad.final_urls
                FROM ad_group_ad
                WHERE ad_group.id = {ad_group_id}
                  AND ad_group_ad.status != REMOVED
                  AND ad_group_ad.ad.type = RESPONSIVE_SEARCH_AD
                LIMIT 1
            """

            response = ga_service.search(customer_id=customer_id, query=query)
            for row in response:
                if row.ad_group_ad.ad.final_urls:
                    return row.ad_group_ad.ad.final_urls[0]
        except Exception as e:
            logger.error(f"Error fetching final URL for ad group {ad_group_id}: {e}")
        
        return None

    def extract_contact_info(self, url: str) -> Dict[str, Optional[str]]:
        """
        Scrapes the given URL to extract phone number, WhatsApp link, and GTM ID.
        """
        info = {
            "phone": None,
            "whatsapp": None,
            "gtm_id": None
        }
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            html_content = response.text
            
            # Extract WhatsApp
            # Look for wa.me or api.whatsapp.com
            whatsapp_pattern = r'(https?://(?:wa\.me|api\.whatsapp\.com/send)\/?\??(?:phone=)?\+?(\d+))'
            whatsapp_match = re.search(whatsapp_pattern, html_content)
            if whatsapp_match:
                info["whatsapp"] = whatsapp_match.group(2) # Extract just the number
            
            # Extract Phone
            # Look for tel: links
            tel_pattern = r'href=["\']tel:\+?([\d\s\-\(\)]+)["\']'
            tel_match = re.search(tel_pattern, html_content)
            if tel_match:
                info["phone"] = re.sub(r'[^\d]', '', tel_match.group(1))
            else:
                # Fallback: Look for patterns like +57 300 123 4567
                # This is a bit risky as it might match other numbers, but let's try a specific format often used
                # Maybe just look for the whatsapp number if found?
                if info["whatsapp"] and not info["phone"]:
                     info["phone"] = info["whatsapp"]

            # Extract GTM ID
            # Look for GTM-XXXXXXXX pattern in scripts, comments, or data attributes
            gtm_pattern = r'GTM-[A-Z0-9]{7,8}'
            gtm_match = re.search(gtm_pattern, html_content, re.IGNORECASE)
            if gtm_match:
                info["gtm_id"] = gtm_match.group(0).upper()  # Ensure uppercase format
            
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {e}")
            
        return info

    @staticmethod
    def get_templates_static() -> Dict[str, Dict[str, str]]:
        """Static method to get template information without requiring full initialization."""
        templates = [
            "base.html", "base_optimized.html", "mystical.html", "romantic.html", "prosperity.html", "llama-gemela.html", 
            "llamado-del-alma.html", "el-libro-prohibido.html", "la-luz.html", "amarre-eterno.html",
            "tarot-akashico.html", "brujeria-blanca.html", "santeria-prosperidad.html", 
            "curanderismo-ancestral.html", "brujeria-negra-venganza.html", "ritual-amor-eterno.html",
            "lectura-aura-sanacion.html", "hechizos-abundancia.html", "conexion-guias-espirituales.html",
            "nocturnal.html"
        ]
        template_info = {}

        for template in templates:
            template_name = template.replace('.html', '')

            # Provide user-friendly names and descriptions
            if template_name == "base":
                template_info[template] = {
                    "name": "Clásica",
                    "description": "Diseño clásico y profesional",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "base_optimized":
                template_info[template] = {
                    "name": "🚀 Optimizada Pro",
                    "description": "Conversión 5x • 7 CTAs • Tracking avanzado • SEO potenciado",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "mystical":
                template_info[template] = {
                    "name": "Mística",
                    "description": "Perfecta para tarot, videncia y temas espirituales",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "romantic":
                template_info[template] = {
                    "name": "Romántica",
                    "description": "Ideal para temas de amor y relaciones",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "prosperity":
                template_info[template] = {
                    "name": "Prosperidad",
                    "description": "Diseñada para dinero, riqueza y abundancia",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "llama-gemela":
                template_info[template] = {
                    "name": "Llama Gemela",
                    "description": "Rituales de amor y reconciliación",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "llamado-del-alma":
                template_info[template] = {
                    "name": "El Llamado del Alma",
                    "description": "Sanación espiritual y chamanismo",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "el-libro-prohibido":
                template_info[template] = {
                    "name": "El Libro Prohibido",
                    "description": "Magia negra y trabajos fuertes",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "la-luz":
                template_info[template] = {
                    "name": "La Luz",
                    "description": "Magia blanca y sanación angelical",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "amarre-eterno":
                template_info[template] = {
                    "name": "Amarre Eterno",
                    "description": "Amarres de amor eternos y magia blanca",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "tarot-akashico":
                template_info[template] = {
                    "name": "Tarot Akáshico",
                    "description": "Lecturas de tarot y registros akáshicos",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "brujeria-blanca":
                template_info[template] = {
                    "name": "Brujería Blanca",
                    "description": "Rituales de magia blanca y protección espiritual",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "santeria-prosperidad":
                template_info[template] = {
                    "name": "Santería Prosperidad",
                    "description": "Rituales de santería para abundancia y prosperidad",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "curanderismo-ancestral":
                template_info[template] = {
                    "name": "Curanderismo Ancestral",
                    "description": "Sabiduría ancestral y curación tradicional",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "brujeria-negra-venganza":
                template_info[template] = {
                    "name": "Brujería Negra Venganza",
                    "description": "Trabajos de magia negra y venganza espiritual",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "ritual-amor-eterno":
                template_info[template] = {
                    "name": "Ritual Amor Eterno",
                    "description": "Rituales poderosos para amor eterno",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "lectura-aura-sanacion":
                template_info[template] = {
                    "name": "Lectura Aura Sanación",
                    "description": "Lectura de aura y sanación energética",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "hechizos-abundancia":
                template_info[template] = {
                    "name": "Hechizos Abundancia",
                    "description": "Hechizos para riqueza y prosperidad infinita",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "conexion-guias-espirituales":
                template_info[template] = {
                    "name": "Conexión Guías Espirituales",
                    "description": "Conectar con ángeles y maestros espirituales",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            elif template_name == "nocturnal":
                template_info[template] = {
                    "name": "Nocturnal",
                    "description": "Diseño oscuro y misterioso para la noche",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }
            else:
                template_info[template] = {
                    "name": template_name.title(),
                    "description": f"Template {template_name}",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }

        return template_info

    def _github_headers(self) -> Dict[str, str]:
        """Get GitHub API headers with authentication."""
        token = self.github_token
        if not token:
            raise RuntimeError("GitHub token not configured")
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def _github_api(self, path: str) -> str:
        """Build GitHub API URL."""
        if path and not path.startswith("/"):
            path = f"/{path}"
        return f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}{path}"

    def _github_get(self, path: str, retries: int = None) -> requests.Response:
        """Make GET request to GitHub API with retry logic."""
        if retries is None:
            retries = self.max_retries

        url = self._github_api(path)
        headers = self._github_headers()

        for attempt in range(retries):
            try:
                logger.debug(f"GitHub GET attempt {attempt + 1}/{retries}: {url}")
                response = requests.get(url, headers=headers, timeout=self.request_timeout)

                if response.status_code == 401:
                    raise RuntimeError("GitHub authentication failed. Check GITHUB_TOKEN.")
                if response.status_code == 403:
                    if "rate limit" in response.text.lower():
                        raise RuntimeError("GitHub API rate limit exceeded. Please wait before retrying.")
                    raise RuntimeError("GitHub API access forbidden. Check repository permissions.")
                if response.status_code == 404:
                    # 404 is acceptable - caller should handle it
                    return response

                # For other errors, retry
                if response.status_code >= 500:
                    if attempt == retries - 1:
                        raise RuntimeError(f"GitHub API server error: {response.status_code} - {response.text}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue

                return response

            except requests.RequestException as e:
                if attempt == retries - 1:
                    raise RuntimeError(f"GitHub API request failed after {retries} attempts: {str(e)}")
                logger.warning(f"GitHub API request failed (attempt {attempt + 1}): {str(e)}")
                time.sleep(2 ** attempt)

        raise RuntimeError("GitHub API request failed after all retries")

    def _github_put(self, path: str, payload: dict, retries: int = None, allow_404_for_new: bool = False) -> requests.Response:
        """Make PUT request to GitHub API with retry logic."""
        if retries is None:
            retries = self.max_retries

        url = self._github_api(path)
        headers = self._github_headers()

        for attempt in range(retries):
            try:
                logger.debug(f"GitHub PUT attempt {attempt + 1}/{retries}: {url}")
                response = requests.put(url, headers=headers, json=payload, timeout=self.request_timeout)

                if response.status_code == 401:
                    raise RuntimeError("GitHub authentication failed. Check GITHUB_TOKEN.")
                if response.status_code == 403:
                    if "rate limit" in response.text.lower():
                        raise RuntimeError("GitHub API rate limit exceeded. Please wait before retrying.")
                    raise RuntimeError("GitHub API access forbidden. Check repository permissions.")
                if response.status_code == 404:
                    # For file creation, 404 might be acceptable if we're creating a new file
                    if allow_404_for_new and "sha" not in payload:
                        logger.warning(f"GitHub returned 404 for new file creation, this might be expected: {url}")
                        return response  # Return the 404 response so caller can handle it
                    else:
                        raise RuntimeError(f"GitHub repository or path not found: {url}")
                if response.status_code == 422:
                    raise RuntimeError(f"GitHub validation error: {response.text}")

                # For server errors, retry
                if response.status_code >= 500:
                    if attempt == retries - 1:
                        raise RuntimeError(f"GitHub API server error: {response.status_code} - {response.text}")
                    time.sleep(2 ** attempt)
                    continue

                return response

            except requests.RequestException as e:
                if attempt == retries - 1:
                    raise RuntimeError(f"GitHub API request failed after {retries} attempts: {str(e)}")
                logger.warning(f"GitHub API request failed (attempt {attempt + 1}): {str(e)}")
                time.sleep(2 ** attempt)

        raise RuntimeError("GitHub API request failed after all retries")

    def _github_post(self, path: str, payload: dict, retries: int = None) -> requests.Response:
        """Make POST request to GitHub API with retry logic."""
        if retries is None:
            retries = self.max_retries

        url = self._github_api(path)
        headers = self._github_headers()

        for attempt in range(retries):
            try:
                logger.debug(f"GitHub POST attempt {attempt + 1}/{retries}: {url}")
                response = requests.post(url, headers=headers, json=payload, timeout=self.request_timeout)

                if response.status_code == 401:
                    raise RuntimeError("GitHub authentication failed. Check GITHUB_TOKEN.")
                if response.status_code == 403:
                    if "rate limit" in response.text.lower():
                        raise RuntimeError("GitHub API rate limit exceeded. Please wait before retrying.")
                    raise RuntimeError("GitHub API access forbidden. Check repository permissions.")
                if response.status_code == 404:
                    raise RuntimeError(f"GitHub repository or path not found: {url}")
                if response.status_code == 422:
                    raise RuntimeError(f"GitHub validation error: {response.text}")

                # For server errors, retry
                if response.status_code >= 500:
                    if attempt == retries - 1:
                        raise RuntimeError(f"GitHub API server error: {response.status_code} - {response.text}")
                    time.sleep(2 ** attempt)
                    continue

                return response

            except requests.RequestException as e:
                if attempt == retries - 1:
                    raise RuntimeError(f"GitHub API request failed after {retries} attempts: {str(e)}")
                logger.warning(f"GitHub API request failed (attempt {attempt + 1}): {str(e)}")
                time.sleep(2 ** attempt)

        raise RuntimeError("GitHub API request failed after all retries")

    def _verify_github_repository_access(self) -> Dict[str, Any]:
        """Verify GitHub repository exists and check permissions."""
        try:
            response = self._github_get("")
            if response.status_code == 200:
                repo_data = response.json()
                permissions = repo_data.get("permissions", {})

                result = {
                    "exists": True,
                    "name": repo_data.get("full_name"),
                    "private": repo_data.get("private"),
                    "permissions": {
                        "push": permissions.get("push", False),
                        "pull": permissions.get("pull", False),
                        "admin": permissions.get("admin", False)
                    }
                }

                # Check if we have push permissions
                if not permissions.get("push", False):
                    logger.warning(f"No push permissions to repository {result['name']}")
                    result["can_push"] = False
                else:
                    result["can_push"] = True

                return result
            elif response.status_code == 404:
                return {"exists": False, "error": "Repository not found"}
            elif response.status_code == 401:
                return {"exists": False, "error": "Authentication failed"}
            else:
                return {"exists": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"exists": False, "error": str(e)}

    def publish_to_github(self, ad_group_id: str, html_content: str, branch: str = "main") -> Dict[str, Any]:
        """Publish HTML content to GitHub repository."""
        if not ad_group_id or not isinstance(ad_group_id, str):
            raise ValueError("ad_group_id must be a non-empty string")
        if not html_content or not isinstance(html_content, str):
            raise ValueError("html_content must be a non-empty string")
        if not branch or not isinstance(branch, str):
            raise ValueError("branch must be a non-empty string")

        # Validate HTML content is not too large (GitHub limit is 100MB per file, but be reasonable)
        content_size = len(html_content.encode('utf-8'))
        if content_size > 50 * 1024 * 1024:  # 50MB limit
            raise ValueError(f"HTML content too large: {content_size} bytes. Maximum allowed: 50MB")

        # First, verify repository exists and is accessible
        logger.info(f"Verifying repository access: {self.github_owner}/{self.github_repo}")
        repo_check = self._verify_github_repository_access()
        if not repo_check.get("exists"):
            raise RuntimeError(f"GitHub repository verification failed: {repo_check.get('error', 'Unknown error')}")

        if not repo_check.get("can_push", False):
            raise RuntimeError(f"No push permissions to repository {repo_check.get('name', 'unknown')}")

        logger.info(f"Repository verified: {repo_check.get('name')} (push access: {repo_check.get('can_push')})")

        folder = f"landing-{ad_group_id}"
        path = f"/{folder}/index.html"

        logger.info(f"Publishing landing page to GitHub: {folder}/index.html")

        try:
            # Check if file already exists
            get_response = self._github_get(f"/contents{path}")
            sha = None

            if get_response.status_code == 200:
                try:
                    file_data = get_response.json()
                    sha = file_data.get("sha")
                    logger.info(f"File exists with SHA: {sha}")
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Could not parse existing file data: {str(e)}")
            elif get_response.status_code == 404:
                logger.info("File does not exist, will create new file")
            else:
                raise RuntimeError(f"Unexpected GitHub response when checking file: {get_response.status_code} - {get_response.text}")

            # Prepare content for upload
            try:
                content_b64 = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
            except (UnicodeEncodeError, UnicodeDecodeError) as e:
                raise RuntimeError(f"Failed to encode HTML content: {str(e)}")

            payload = {
                "message": f"feat: add/update landing page {folder}",
                "content": content_b64,
                "branch": branch
            }

            if sha:
                payload["sha"] = sha

            # Upload file - GitHub allows creating files in new paths
            put_response = self._github_put(f"/contents{path}", payload, allow_404_for_new=True)

            # Handle the case where PUT returns 404 for new file creation
            if put_response.status_code == 404 and "sha" not in payload:
                # This might happen if the repository doesn't exist or has permission issues
                # Let's verify the repository exists
                try:
                    repo_check = self._github_get("")
                    if repo_check.status_code != 200:
                        raise RuntimeError(f"Repository verification failed: {repo_check.status_code}")
                except Exception as e:
                    raise RuntimeError(f"Repository access verification failed: {str(e)}")

                # If repository exists but PUT still fails, it might be a permission issue
                raise RuntimeError(f"GitHub file creation failed with 404. Repository exists but may have permission issues.")

            if put_response.status_code not in [200, 201]:
                error_msg = f"GitHub file upload failed: {put_response.status_code}"
                try:
                    error_data = put_response.json()
                    if "message" in error_data:
                        error_msg += f" - {error_data['message']}"
                except:
                    error_msg += f" - {put_response.text[:200]}"
                raise RuntimeError(error_msg)

            try:
                result = put_response.json()
                logger.info(f"Successfully published to GitHub. Commit: {result.get('commit', {}).get('sha', 'unknown')}")
                return result
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse GitHub response: {str(e)}")

        except Exception as e:
            logger.error(f"GitHub publishing failed: {str(e)}")
            raise

    def setup_custom_domain(self) -> bool:
        """Configure custom domain for GitHub Pages."""
        if not self.custom_domain:
            logger.info("ℹ️ No custom domain configured, using default GitHub Pages URL")
            return True

        try:
            logger.info(f"🔧 Setting up custom domain: {self.custom_domain}")

            # Create CNAME file in the root of the repository
            cname_content = self.custom_domain

            # Check if CNAME file exists
            get_response = self._github_get("/contents/CNAME")
            sha = None

            if get_response.status_code == 200:
                try:
                    file_data = get_response.json()
                    sha = file_data.get("sha")
                    logger.info("📄 CNAME file exists, updating...")
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Could not parse CNAME file data: {str(e)}")
            elif get_response.status_code == 404:
                logger.info("📄 CNAME file does not exist, creating...")
            else:
                logger.warning(f"Unexpected response checking CNAME: {get_response.status_code}")
                return False

            # Encode and upload CNAME file
            try:
                content_b64 = base64.b64encode(cname_content.encode("utf-8")).decode("ascii")
            except (UnicodeEncodeError, UnicodeDecodeError) as e:
                raise RuntimeError(f"Failed to encode CNAME content: {str(e)}")

            payload = {
                "message": f"🚀 Configure custom domain: {self.custom_domain}",
                "content": content_b64,
                "branch": "main"
            }

            if sha:
                payload["sha"] = sha

            put_response = self._github_put("/contents/CNAME", payload)

            if put_response.status_code not in [200, 201]:
                logger.warning(f"Failed to upload CNAME file: {put_response.status_code} - {put_response.text}")
                return False

            logger.info("✅ Custom domain CNAME file created/updated")
            return True

        except Exception as e:
            logger.warning(f"Could not setup custom domain: {str(e)}")
            return False

    def setup_github_pages(self) -> bool:
        """Setup GitHub Pages for the repository if not already enabled."""
        try:
            logger.info("Setting up GitHub Pages for repository...")

            # Check if GitHub Pages is already enabled
            get_response = self._github_get("/pages")
            if get_response.status_code == 200:
                pages_data = get_response.json()
                current_source = pages_data.get("source", {})
                if current_source.get("branch") == "main" and current_source.get("path") == "/":
                    logger.info("✅ GitHub Pages already enabled with correct configuration")
                    return True
                else:
                    logger.info(f"GitHub Pages enabled but with different config: {current_source}")
                    # Could update here if needed, but for now just proceed

            # Enable GitHub Pages with main branch and root path
            payload = {
                "source": {
                    "branch": "main",
                    "path": "/"
                }
            }

            post_response = self._github_post("/pages", payload)
            if post_response.status_code in [201, 204]:
                logger.info("✅ GitHub Pages enabled successfully")
                return True
            elif post_response.status_code == 409:
                logger.warning("GitHub Pages setup conflict - may already be configured")
                return True  # Consider it successful
            else:
                logger.warning(f"Failed to setup GitHub Pages: {post_response.status_code} - {post_response.text}")
                return False

        except Exception as e:
            logger.warning(f"Could not setup GitHub Pages: {str(e)}")
            return False

    def upload_asset_to_github(self, content_bytes: bytes, filename: str) -> str:
        """Upload an asset to GitHub and return the jsdelivr URL."""
        path = f"assets/images/{filename}"
        
        # Check if file exists (to get SHA for update)
        get_response = self._github_get(f"/contents/{path}")
        sha = None
        if get_response.status_code == 200:
            try:
                sha = get_response.json().get("sha")
            except:
                pass
            
        # Encode content
        content_b64 = base64.b64encode(content_bytes).decode("ascii")
        
        payload = {
            "message": f"Upload asset: {filename}",
            "content": content_b64,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha
            
        put_response = self._github_put(f"/contents/{path}", payload)
        
        if put_response.status_code not in [200, 201]:
             raise RuntimeError(f"Failed to upload asset {filename}: {put_response.text}")
             
        # Return jsdelivr URL
        return f"https://cdn.jsdelivr.net/gh/{self.github_owner}/{self.github_repo}@main/{path}"

    def _verify_asset_availability(self, filename: str, max_retries: int = 3) -> bool:
        """
        Diagnostic: Verify that the asset was successfully uploaded and is accessible.
        Checks the raw GitHub URL for immediate availability.
        """
        raw_url = f"https://raw.githubusercontent.com/{self.github_owner}/{self.github_repo}/main/assets/images/{filename}"
        
        for i in range(max_retries):
            try:
                response = requests.head(raw_url, timeout=5)
                if response.status_code == 200:
                    logger.info(f"✅ Asset verification successful: {filename}")
                    return True
                elif response.status_code == 404:
                    logger.warning(f"Asset not found yet (attempt {i+1}/{max_retries}): {filename}")
                else:
                    logger.warning(f"Asset verification returned {response.status_code} (attempt {i+1}/{max_retries})")
            except Exception as e:
                logger.warning(f"Asset verification error (attempt {i+1}/{max_retries}): {e}")
            
            if i < max_retries - 1:
                time.sleep(1) # Wait before retry
                
        logger.error(f"❌ Asset verification failed after {max_retries} attempts: {filename}")
        return False

    def publish_as_github_pages(self, folder_name: str, html_content: str) -> Dict[str, Any]:
        """Publish landing page optimized for GitHub Pages."""
        if not folder_name or not isinstance(folder_name, str):
            raise ValueError("folder_name must be a non-empty string")
        if not html_content or not isinstance(html_content, str):
            raise ValueError("html_content must be a non-empty string")

        # Validate HTML content size
        content_size = len(html_content.encode('utf-8'))
        if content_size > 50 * 1024 * 1024:  # 50MB limit
            raise ValueError(f"HTML content too large: {content_size} bytes. Maximum allowed: 50MB")

        # Setup GitHub Pages first
        self.setup_github_pages()

        # Setup custom domain if configured
        if self.custom_domain:
            self.setup_custom_domain()

        # Use provided folder name for subdomain-friendly alias
        alias = self.build_alias_domain(folder_name)
        # For GitHub Pages, use the clean folder name (not the full domain alias)
        folder = folder_name
        path = f"{folder}/index.html"

        logger.info(f"🚀 Publishing to GitHub Pages: {folder}/index.html")

        try:
            # Check if file exists
            get_response = self._github_get(f"/contents/{path}")
            sha = None

            if get_response.status_code == 200:
                try:
                    file_data = get_response.json()
                    sha = file_data.get("sha")
                    logger.info(f"📄 File exists, updating...")
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Could not parse existing file data: {str(e)}")
            elif get_response.status_code == 404:
                logger.info("📄 File does not exist, creating new...")
            else:
                error_msg = f"Unexpected GitHub response: {get_response.status_code}"
                try:
                    error_data = get_response.json()
                    if "message" in error_data:
                        error_msg += f" - {error_data['message']}"
                except:
                    error_msg += f" - {get_response.text[:200]}"
                raise RuntimeError(error_msg)

            # Encode content
            try:
                content_b64 = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
            except (UnicodeEncodeError, UnicodeDecodeError) as e:
                raise RuntimeError(f"Failed to encode HTML content: {str(e)}")

            # Prepare payload
            payload = {
                "message": f"🚀 Deploy landing page: {alias}",
                "content": content_b64,
                "branch": "main"
            }

            if sha:
                payload["sha"] = sha

            # Upload file
            put_response = self._github_put(f"/contents/{path}", payload)

            if put_response.status_code not in [200, 201]:
                error_msg = f"GitHub upload failed: {put_response.status_code}"
                try:
                    error_data = put_response.json()
                    if "message" in error_data:
                        error_msg += f" - {error_data['message']}"
                except:
                    error_msg += f" - {put_response.text[:200]}"
                raise RuntimeError(error_msg)

            try:
                result = put_response.json()
                commit_sha = result.get("commit", {}).get("sha")
                logger.info(f"✅ Published to GitHub Pages (commit: {commit_sha})")

                # Generate URL based on domain configuration
                public_url = self._get_public_url(folder_name)
                github_preview_url = f"https://{self.github_owner}.github.io/{self.github_repo}/{folder_name}/"
                logger.info(f"🌐 Public landing URL: {public_url}")
                if public_url != github_preview_url:
                    logger.info(f"🔎 GitHub preview URL: {github_preview_url}")

                return {
                    "commit_sha": commit_sha,
                    "url": public_url,
                    "alias": public_url,  # Alias always matches the public URL
                    "github_preview_url": github_preview_url,
                    "path": f"{folder_name}/index.html",
                    "size": content_size,
                    "custom_domain": self.custom_domain
                }

            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse GitHub response: {str(e)}")

        except Exception as e:
            logger.error(f"GitHub Pages publishing failed: {str(e)}")
            raise

    def build_alias_domain(self, keyword: str) -> str:
        k = keyword.lower().strip()
        # Normalize to remove accents
        k = unicodedata.normalize('NFKD', k).encode('ASCII', 'ignore').decode('ASCII')
        # Replace non-alphanumeric with dashes
        k = re.sub(r'[^a-z0-9]+', '-', k)
        # Remove leading/trailing dashes
        k = k.strip('-')
        # Truncate to 63 chars (DNS limit)
        if len(k) > 63:
            k = k[:63].strip('-')
        return f"{k}.{self.base_domain}"

    def health_check(self, url: str, whatsapp_number: str, phone_number: str, gtm_id: str) -> bool:
        """Perform comprehensive health check on deployed landing page."""
        if not url or not isinstance(url, str):
            raise ValueError("url must be a non-empty string")
        if not whatsapp_number or not isinstance(whatsapp_number, str):
            raise ValueError("whatsapp_number must be a non-empty string")
        if not phone_number or not isinstance(phone_number, str):
            raise ValueError("phone_number must be a non-empty string")
        if not gtm_id or not isinstance(gtm_id, str):
            raise ValueError("gtm_id must be a non-empty string")

        logger.info(f"Performing health check on: {url}")

        try:
            response = requests.get(url, timeout=self.health_check_timeout, allow_redirects=True)

            if response.status_code != 200:
                logger.error(f"Health check failed: HTTP {response.status_code}")
                return False

            html = response.text
            if not html or len(html.strip()) < 100:
                logger.error("Health check failed: HTML content too small or empty")
                return False

            # Critical content checks
            checks = [
                (f"wa.me/{whatsapp_number.replace('+', '')}", "WhatsApp link"),
                (f"tel:{phone_number}", "Phone number link"),
                (gtm_id, "GTM ID"),
                ("<h1", "H1 heading tag"),
                ("<title>", "Title tag"),
                ('name="description"', "Meta description"),
                ("</html>", "HTML closing tag"),
            ]

            failed_checks = []
            for check_content, check_name in checks:
                if check_content not in html:
                    failed_checks.append(check_name)

            if failed_checks:
                logger.error(f"Health check failed: Missing content: {', '.join(failed_checks)}")
                return False

            # Additional validation: Check for basic HTML structure
            if "<!DOCTYPE html>" not in html and "<html" not in html:
                logger.error("Health check failed: Invalid HTML structure")
                return False

            logger.info("Health check passed successfully")
            return True

        except requests.Timeout:
            logger.error(f"Health check failed: Request timeout after {self.health_check_timeout}s")
            return False
        except requests.RequestException as e:
            logger.error(f"Health check failed: Request error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Health check failed: Unexpected error: {str(e)}")
            return False

    def update_final_urls(self, customer_id: str, ad_group_id: str, final_url: str, ctx: AdGroupContext = None) -> bool:
        """
        Update Final URLs for existing ads in an ad group.

        Args:
            customer_id: Google Ads customer ID
            ad_group_id: Ad group ID
            final_url: New final URL to set
            ctx: Ad group context

        Returns:
            True if URLs were updated successfully, False if update failed (ads should be created instead)
        """
        if not customer_id or not isinstance(customer_id, str):
            raise ValueError("customer_id must be a non-empty string")
        if not ad_group_id or not isinstance(ad_group_id, str):
            raise ValueError("ad_group_id must be a non-empty string")
        if not final_url or not isinstance(final_url, str):
            raise ValueError("final_url must be a non-empty string")

        # Validate URL format
        if not final_url.startswith(('http://', 'https://')):
            raise ValueError("final_url must start with http:// or https://")

        logger.info(f"Updating Final URLs for Ad Group {ad_group_id} to: {final_url}")

        try:
            client = self._get_google_ads_client()
            ga_svc = client.get_service("GoogleAdsService")
            ag_svc = client.get_service("AdGroupAdService")

            # Normalize IDs
            customer_id = customer_id.replace("-", "")
            ad_group_id = ad_group_id.replace("-", "")

            if not customer_id.isdigit():
                raise ValueError(f"Invalid customer_id format: {customer_id}")
            if not ad_group_id.isdigit():
                raise ValueError(f"Invalid ad_group_id format: {ad_group_id}")

            # Query for ad resource names
            query = f"""
                SELECT ad_group_ad.resource_name
                FROM ad_group_ad
                WHERE ad_group.id = {ad_group_id}
                  AND ad_group_ad.status != REMOVED
                  AND ad_group_ad.ad.type = RESPONSIVE_SEARCH_AD
            """

            rows = ga_svc.search(customer_id=customer_id, query=query)
            resource_names = [row.ad_group_ad.resource_name for row in rows]

            if not resource_names:
                logger.info(f"No active ads found in Ad Group {ad_group_id}, will create new ads with landing page content...")
                return self.create_ads_for_ad_group(customer_id, ad_group_id, final_url, ctx)

            logger.info(f"Found {len(resource_names)} ads to update")

            # Prepare operations - Update tracking URL template instead of final_urls
            # Since final_urls cannot be modified on existing ads, we'll update tracking_url_template - Update tracking URL template instead of final_urls
            # Since final_urls cannot be modified on existing ads, we'll update tracking_url_template
            operations = []
            for resource_name in resource_names:
                update = client.get_type("AdGroupAd")
                update.resource_name = resource_name
                update.ad = client.get_type("Ad")

                # Instead of modifying final_urls (immutable), update tracking_url_template
                # This allows redirecting to new URL while preserving the original final_url
                update.ad.tracking_url_template = final_url + "?utm_source=google&utm_medium=cpc&utm_campaign={{campaign.name}}&ad_group={{ad_group.name}}"

                op = client.get_type("AdGroupAdOperation")
                op.update = update
                op.update_mask.CopyFrom(FieldMask(paths=["ad.tracking_url_template"]))
                operations.append(op)

            if operations:
                logger.info(f"Sending {len(operations)} update operations to Google Ads (updating tracking URL templates)")
                try:
                    response = ag_svc.mutate_ad_group_ads(customer_id=customer_id, operations=operations)

                    success_count = len(response.results)
                    logger.info(f"Successfully updated {success_count} ads with new tracking URL templates")

                    if success_count != len(operations):
                        logger.warning(f"Expected {len(operations)} updates but got {success_count} results")
                        return True  # Partial success still counts as success
                except Exception as api_error:
                    # Check if this is still an immutable field error (shouldn't happen with tracking_url_template)
                    error_str = str(api_error).lower()
                    if "immutable_field" in error_str or "cannot be modified" in error_str:
                        logger.warning(f"Cannot update tracking URL template on existing ads: {str(api_error)}")
                        logger.info("Landing page published successfully, but existing ads will keep their current tracking settings")
                        logger.info("Consider creating new ads with the new landing page URL")
                        # Return False to indicate update failed - caller should create new ads
                        return False
                    else:
                        # Re-raise other API errors
                        raise api_error
            else:
                logger.info("No operations to perform")
                return True

        except Exception as e:
            logger.error(f"Failed to update Final URLs: {str(e)}")
            raise RuntimeError(f"Google Ads URL update failed: {str(e)}")

        return True

    def create_ads_for_ad_group(self, customer_id: str, ad_group_id: str, final_url: str, ctx: AdGroupContext) -> None:
        """Create new ads for an ad group using landing page context."""
        if not customer_id or not isinstance(customer_id, str):
            raise ValueError("customer_id must be a non-empty string")
        if not ad_group_id or not isinstance(ad_group_id, str):
            raise ValueError("ad_group_id must be a non-empty string")
        if not final_url or not isinstance(final_url, str):
            raise ValueError("final_url must be a non-empty string")
        if not ctx or not isinstance(ctx, AdGroupContext):
            raise ValueError("ctx must be a valid AdGroupContext")

        logger.info(f"Creating new ads for Ad Group {ad_group_id} with landing page URL: {final_url}")

        try:
            client = self._get_google_ads_client()
            ag_svc = client.get_service("AdGroupAdService")

            # Normalize IDs
            customer_id = customer_id.replace("-", "")
            ad_group_id = ad_group_id.replace("-", "")

            if not customer_id.isdigit():
                raise ValueError(f"Invalid customer_id format: {customer_id}")
            if not ad_group_id.isdigit():
                raise ValueError(f"Invalid ad_group_id format: {ad_group_id}")

            # Create multiple ad variations for A/B testing
            operations = []
            num_ads_to_create = min(3, len(ctx.headlines), len(ctx.descriptions))  # Create up to 3 ads

            for i in range(num_ads_to_create):
                # Create AdGroupAd
                ad_group_ad = client.get_type("AdGroupAd")
                ad_group_ad.ad_group = client.get_resource("ad_group", ad_group_id)
                ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

                # Create Responsive Search Ad
                ad = client.get_type("Ad")
                ad.type = client.enums.AdTypeEnum.RESPONSIVE_SEARCH_AD
                ad.final_urls.append(final_url)

                # Add headlines (rotate through available headlines)
                headlines_to_add = []
                for j in range(min(3, len(ctx.headlines))):  # Max 3 headlines per ad
                    headline_idx = (i + j) % len(ctx.headlines)
                    headline = client.get_type("AdTextAsset")
                    headline.text = ctx.headlines[headline_idx][:30]  # Max 30 chars
                    headlines_to_add.append(headline)
                ad.responsive_search_ad.headlines.extend(headlines_to_add)

                # Add descriptions (rotate through available descriptions)
                descriptions_to_add = []
                for j in range(min(2, len(ctx.descriptions))):  # Max 2 descriptions per ad
                    desc_idx = (i + j) % len(ctx.descriptions)
                    description = client.get_type("AdTextAsset")
                    description.text = ctx.descriptions[desc_idx][:90]  # Max 90 chars
                    descriptions_to_add.append(description)
                ad.responsive_search_ad.descriptions.extend(descriptions_to_add)

                # Set the ad path (optional)
                if hasattr(ad.responsive_search_ad, 'path1'):
                    ad.responsive_search_ad.path1 = ctx.primary_keyword[:15]  # Max 15 chars

                ad_group_ad.ad = ad

                # Create operation
                operation = client.get_type("AdGroupAdOperation")
                operation.create = ad_group_ad
                operations.append(operation)

            if operations:
                logger.info(f"Creating {len(operations)} new ads for Ad Group {ad_group_id}")
                response = ag_svc.mutate_ad_group_ads(customer_id=customer_id, operations=operations)

                success_count = len(response.results)
                logger.info(f"Successfully created {success_count} new ads")

                if success_count != len(operations):
                    logger.warning(f"Expected {len(operations)} creations but got {success_count} results")
            else:
                logger.warning("No ad operations to perform")

        except Exception as e:
            logger.error(f"Failed to create ads for Ad Group {ad_group_id}: {str(e)}")
            raise RuntimeError(f"Google Ads ad creation failed: {str(e)}")

    def automate_ad_group_complete_setup(self, customer_id: str, ad_group_id: str, whatsapp_number: str, gtm_id: str, phone_number: Optional[str] = None, webhook_url: Optional[str] = None, selected_template: Optional[str] = None, google_ads_mode: str = "none") -> Dict[str, Any]:
        """
        Complete automation: Extract context, generate landing page, publish, and setup ads.

        This method provides a single entry point for the complete automation workflow:
        1. Extract ad group context (keywords, headlines, descriptions, locations)
        2. Generate AI-powered landing page content
        3. Render HTML with selected template
        4. Publish to GitHub Pages
        5. Setup Google Ads (update existing ads or create new ones)
        6. Health check
        7. Return complete results

        Args:
            customer_id: Google Ads customer ID
            ad_group_id: Ad group ID to work with
            whatsapp_number: WhatsApp number for the landing page
            gtm_id: Google Tag Manager ID
            phone_number: Optional phone number
            webhook_url: Optional webhook URL for notifications
            selected_template: Optional template name (defaults to 'base.html')
            google_ads_mode: Control Google Ads integration
                - "none": Only create landing page, no Google Ads changes
                - "update_only": Update existing ads tracking URLs only
                - "create_only": Create new ads if group is empty, don't update existing
                - "auto": Full automation (default) - update existing or create new as needed

        Returns:
            Dict with complete automation results
        """
        logger.info("🚀 Starting complete ad group automation...")
        logger.info(f"Customer ID: {customer_id}, Ad Group ID: {ad_group_id}")

        return self.run(
            customer_id=customer_id,
            ad_group_id=ad_group_id,
            whatsapp_number=whatsapp_number,
            gtm_id=gtm_id,
            phone_number=phone_number,
            webhook_url=webhook_url,
            selected_template=selected_template,
            google_ads_mode=google_ads_mode
        )

    def _generate_folder_name(self, keywords: List[str]) -> str:
        """Generate a unique folder name based on a random keyword from the list."""
        if not keywords:
            # Fallback if no keywords available
            return f"landing-{random.randint(1000, 9999)}"

        # Select a random keyword
        selected_keyword = random.choice(keywords)
        logger.info(f"🎯 Selected keyword for folder: '{selected_keyword}'")

        # Create slug: normalize, remove accents, replace spaces with hyphens, remove special chars
        slug = unicodedata.normalize('NFD', selected_keyword)
        slug = ''.join(c for c in slug if unicodedata.category(c) != 'Mn')  # Remove accents
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', slug)  # Remove special characters except spaces and hyphens
        slug = re.sub(r'\s+', '-', slug.lower())  # Replace spaces with hyphens and lowercase
        slug = re.sub(r'-+', '-', slug)  # Replace multiple hyphens with single
        slug = slug.strip('-')  # Remove leading/trailing hyphens

        # Ensure slug is not empty
        if not slug:
            slug = f"keyword-{random.randint(1000, 9999)}"

        # Generate unique number (1-999) to avoid duplicates
        unique_number = random.randint(1, 999)

        folder_name = f"{slug}-{unique_number}"
        logger.info(f"📁 Generated folder name: '{folder_name}'")

        return folder_name

    def _get_existing_ads_count(self, customer_id: str, ad_group_id: str) -> int:
        """
        Get the count of existing ads in an ad group.

        Args:
            customer_id: Google Ads customer ID
            ad_group_id: Ad group ID to check

        Returns:
            Number of existing ads in the ad group
        """
        try:
            client = self.google_ads_client_provider()
            google_ads_service = client.get_service("GoogleAdsService")

            query = f"""
                SELECT ad_group_ad.ad.id
                FROM ad_group_ad
                WHERE ad_group_ad.ad_group = 'customers/{customer_id}/adGroups/{ad_group_id}'
                  AND ad_group_ad.status != 'REMOVED'
                  AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
            """

            response = google_ads_service.search(customer_id=customer_id, query=query)
            count = sum(1 for _ in response)
            logger.debug(f"Found {count} existing ads in ad group {ad_group_id}")
            return count

        except Exception as e:
            logger.warning(f"Could not get existing ads count for ad group {ad_group_id}: {str(e)}")
            return 0

    def run(self, customer_id: str, ad_group_id: str, whatsapp_number: str, gtm_id: str, phone_number: Optional[str] = None, webhook_url: Optional[str] = None, selected_template: Optional[str] = None, google_ads_mode: str = "none", user_images: Optional[List[Dict[str, str]]] = None, user_videos: Optional[List[Dict[str, str]]] = None, paragraph_template: Optional[str] = None, optimize_images_with_ai: bool = False, selected_color_palette: str = "mystical", custom_template_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the complete landing page generation pipeline.

        Args:
            customer_id: Google Ads customer ID
            ad_group_id: Ad group ID to work with
            whatsapp_number: WhatsApp number for the landing page
            gtm_id: Google Tag Manager ID
            phone_number: Optional phone number
            webhook_url: Optional webhook URL for notifications
            selected_template: Optional template name (defaults to 'base.html')
            google_ads_mode: Control Google Ads integration
                - "none": Only create landing page, no Google Ads changes
                - "update_only": Update existing ads tracking URLs only
                - "create_only": Create new ads if group is empty, don't update existing
                - "auto": Full automation (default) - update existing or create new as needed
            user_images: Optional list of user provided images with position info
            paragraph_template: Optional paragraph template ID for AI optimization
            optimize_images_with_ai: If True, use Gemini to optimize images
            selected_color_palette: Color palette for the landing page theme
        """
        start_time = time.time()

        # Comprehensive input validation
        if not customer_id or not isinstance(customer_id, str):
            raise ValueError("customer_id must be a non-empty string")
        if not ad_group_id or not isinstance(ad_group_id, str):
            raise ValueError("ad_group_id must be a non-empty string")
        if not whatsapp_number or not isinstance(whatsapp_number, str):
            raise ValueError("whatsapp_number must be a non-empty string")
        if not gtm_id or not isinstance(gtm_id, str):
            raise ValueError("gtm_id must be a non-empty string")

        # Validate WhatsApp number format
        if not whatsapp_number.startswith("+"):
            raise ValueError("whatsapp_number must start with + (e.g., +52551234567)")
        if not whatsapp_number[1:].isdigit() or len(whatsapp_number) < 10:
            raise ValueError("whatsapp_number must be a valid international number")

        # Validate GTM ID format
        if not gtm_id.startswith("GTM-") or len(gtm_id) < 8:
            raise ValueError("gtm_id must be in format GTM-XXXXXXX")

        # Validate google_ads_mode
        valid_modes = ["none", "update_only", "create_only", "auto"]
        if google_ads_mode not in valid_modes:
            raise ValueError(f"google_ads_mode must be one of: {', '.join(valid_modes)}")

        logger.info(f"🚀 Starting landing page generation for Ad Group: {ad_group_id} (Google Ads mode: {google_ads_mode})")

        try:
            # Set default phone number
            if not phone_number:
                phone_number = whatsapp_number
            elif not phone_number.startswith("+"):
                phone_number = f"+{phone_number}"

            # Step 1: Extract Ad Group context
            logger.info("📊 Step 1: Extracting Ad Group context...")
            ctx = self.extract_ad_group_context(customer_id, ad_group_id)
            logger.info(f"✅ Context extracted: {len(ctx.keywords)} keywords, {len(ctx.headlines)} headlines")

            # Generate unique folder name based on random keyword
            folder_name = self._generate_folder_name(ctx.keywords)
            logger.info(f"📁 Using folder name: '{folder_name}'")

            # Validate we have minimum required data
            if not ctx.primary_keyword:
                logger.warning("No primary keyword found, using fallback")
                ctx.primary_keyword = f"landing-{ad_group_id}"

            # Step 2: Generate content with AI
            logger.info("🤖 Step 2: Generating content with AI...")
            
            # Inject paragraph template into payload if provided
            if paragraph_template:
                logger.info(f"📝 Using paragraph template: {paragraph_template}")
            
            gen = self.generate_content(ctx, paragraph_template)
            logger.info("✅ Content generated successfully")

            # Process user images if provided
            image_metrics = []  # Track optimization metrics
            
            if user_images:
                processed_images = []
                
                # Log AI optimization status
                if optimize_images_with_ai:
                    logger.info("🎨 AI Image Optimization ENABLED - Images will be processed with Gemini")
                else:
                    logger.info("📸 AI Image Optimization DISABLED - Images will be compressed only")
                
                # Deduplication Strategy 1: Filter by position (Last one wins)
                # This prevents processing multiple images for the same slot
                unique_positions = {}
                for img in user_images:
                    pos = img.get("position", "middle")
                    unique_positions[pos] = img
                
                # Deduplication Strategy 2: Content Hashing
                # Avoid uploading the exact same image twice in the same run
                content_hash_map = {} # hash -> url
                
                for pos, img in unique_positions.items():
                    image_bytes = None
                    
                    # Case 1: Base64 Content
                    if img.get("content"):
                        try:
                            b64_data = img["content"]
                            if "," in b64_data:
                                b64_data = b64_data.split(",")[1]
                            image_bytes = base64.b64decode(b64_data)
                        except Exception as e:
                            logger.error(f"Failed to decode base64 for user image at {pos}: {e}")
                            continue

                    # Case 2: URL Content
                    elif img.get("url"):
                        url = img["url"]
                        # If it's already our CDN URL, keep it as is
                        if "cdn.jsdelivr.net" in url and self.github_repo in url:
                             processed_images.append(img)
                             continue
                        
                        try:
                            logger.info(f"Downloading image from URL: {url}")
                            resp = requests.get(url, timeout=15)
                            if resp.status_code == 200:
                                image_bytes = resp.content
                            else:
                                logger.warning(f"Failed to download image from {url}: {resp.status_code}")
                        except Exception as e:
                            logger.error(f"Error downloading image from {url}: {e}")

                    # Process and Upload if we have bytes
                    if image_bytes:
                        try:
                            # Calculate hash for deduplication
                            img_hash = hashlib.md5(image_bytes).hexdigest()
                            
                            if img_hash in content_hash_map:
                                # Reuse existing URL for this content
                                url = content_hash_map[img_hash]
                                logger.info(f"♻️ Reusing uploaded image for {pos} (Hash match)")
                            else:
                                # AI OPTIMIZATION BRANCH
                                if optimize_images_with_ai:
                                    try:
                                        # Use Gemini to optimize image
                                        optimized_bytes, metrics = self._optimize_image_with_gemini(
                                            image_bytes, 
                                            ctx.keywords, 
                                            pos
                                        )
                                        image_metrics.append(metrics)
                                        
                                        # Use optimized bytes
                                        webp_data = optimized_bytes
                                    except Exception as ai_error:
                                        logger.error(f"❌ AI optimization failed for {pos}: {ai_error}")
                                        logger.info("⚠️ Falling back to standard compression")
                                        # Fallback: standard compression
                                        webp_data = self._compress_image_standard(image_bytes, pos)
                                else:
                                    # STANDARD COMPRESSION (No AI)
                                    webp_data = self._compress_image_standard(image_bytes, pos)
                                
                                # Generate filename
                                filename = f"{uuid.uuid4()}.webp"
                                
                                # Upload
                                url = self.upload_asset_to_github(webp_data, filename)
                                
                                # Diagnostic: Verify upload
                                if self._verify_asset_availability(filename):
                                    content_hash_map[img_hash] = url
                                else:
                                    logger.error(f"❌ Image verification failed for {pos}. Skipping.")
                                    continue
                            
                            processed_images.append({
                                "url": url,
                                "position": pos
                            })
                            logger.info(f"✅ Processed and uploaded user image to {url}")
                        except Exception as e:
                            logger.error(f"Failed to process/upload user image: {e}")
                
                # Update user_images with processed ones
                user_images = processed_images
                
                # Log metrics summary if AI was used
                if optimize_images_with_ai and image_metrics:
                    total_reduction = sum(m.reduction_percentage for m in image_metrics) / len(image_metrics)
                    total_time = sum(m.processing_time for m in image_metrics)
                    logger.info(f"📊 AI Optimization Summary: {len(image_metrics)} images, {total_reduction:.1f}% avg reduction, {total_time:.1f}s total")

            # Step 3: Prepare configuration
            config = {
                "whatsapp_number": whatsapp_number,
                "phone_number": phone_number or whatsapp_number,
                "webhook_url": webhook_url or "",
                "gtm_id": gtm_id,
                "primary_keyword": ctx.primary_keyword,
                "selected_template": selected_template,
                "user_images": user_images or [],
                "user_videos": user_videos or [],
                "folder_name": folder_name,
                "custom_template_content": custom_template_content
            }

            # Step 4: Render HTML
            logger.info("🎨 Step 3: Rendering HTML template...")
            html = self.render(gen, config, selected_color_palette)
            html_size = len(html.encode('utf-8'))
            logger.info(f"✅ HTML rendered successfully ({html_size} bytes)")

            # Step 5: Publish to GitHub Pages
            logger.info("📄 Step 4: Publishing to GitHub Pages...")
            gh_result = self.publish_as_github_pages(folder_name, html)
            commit_sha = gh_result.get("commit_sha")
            final_url = gh_result.get("url")
            alias = gh_result.get("alias")
            logger.info(f"✅ Published to GitHub Pages (commit: {commit_sha})")
            logger.info(f"🌐 GitHub Pages URL: {final_url}")

            # Step 6: Health check
            logger.info("🏥 Step 6: Performing health check...")
            ok = self.health_check(final_url, whatsapp_number, phone_number, gtm_id)
            if not ok:
                logger.warning(f"Health check failed for {final_url}, but continuing (GitHub Pages may take time to deploy)")
            else:
                logger.info("✅ Health check passed")

            # Step 7: Handle Google Ads based on selected mode
            google_ads_result = None
            if google_ads_mode == "none":
                logger.info("🚫 Step 7: Skipping Google Ads integration (mode: none)")
            elif google_ads_mode == "update_only":
                logger.info("🔄 Step 7: Updating existing ads final URLs only (mode: update_only)")
                try:
                    update_success = self.update_final_urls(customer_id, ad_group_id, final_url, ctx)
                    if update_success:
                        google_ads_result = {"action": "updated_existing", "message": "Updated final URLs for existing ads"}
                        logger.info("✅ Google Ads URLs updated successfully")
                    else:
                        google_ads_result = {"action": "update_failed", "message": "Cannot update existing ads - Google Ads limitation", "suggestion": "Use 'auto' mode to create new ads"}
                        logger.warning("⚠️ Could not update existing ads due to Google Ads API limitations")
                except Exception as url_error:
                    logger.warning(f"Could not update Google Ads URLs: {str(url_error)}")
                    google_ads_result = {"action": "failed", "error": str(url_error)}
            elif google_ads_mode == "create_only":
                logger.info("🆕 Step 7: Creating new ads if group is empty (mode: create_only)")
                try:
                    # Check if ad group has existing ads
                    existing_ads = self._get_existing_ads_count(customer_id, ad_group_id)
                    if existing_ads == 0:
                        # Create new ads directly
                        self.create_ads_for_ad_group(customer_id, ad_group_id, final_url, ctx)
                        google_ads_result = {"action": "created_new", "ads_created": "multiple", "message": "Created new ads in empty ad group"}
                        logger.info("✅ Created new ads in empty ad group")
                    else:
                        logger.info(f"ℹ️ Ad group already has {existing_ads} ads, skipping creation (create_only mode)")
                        google_ads_result = {"action": "skipped", "reason": "ads_already_exist", "existing_count": existing_ads}
                except Exception as create_error:
                    logger.warning(f"Could not create new ads: {str(create_error)}")
                    google_ads_result = {"action": "failed", "error": str(create_error)}
            elif google_ads_mode == "auto":
                logger.info("🤖 Step 7: Full Google Ads automation (mode: auto)")
                try:
                    # First try to update existing ads
                    update_success = self.update_final_urls(customer_id, ad_group_id, final_url, ctx)

                    if update_success:
                        google_ads_result = {
                            "action": "updated_existing",
                            "message": "Updated final URLs for existing ads"
                        }
                        logger.info("✅ Google Ads URLs updated successfully")
                    else:
                        # Update failed, create new ads instead
                        logger.info("🔄 Update failed, creating new ads with landing page content...")
                        self.create_ads_for_ad_group(customer_id, ad_group_id, final_url, ctx)
                        google_ads_result = {
                            "action": "created_new",
                            "message": "Created new ads (existing ads could not be updated)"
                        }
                        logger.info("✅ Created new ads with landing page URL")
                except Exception as auto_error:
                    logger.warning(f"Could not complete Google Ads automation: {str(auto_error)}")
                    google_ads_result = {"action": "failed", "error": str(auto_error)}
            else:
                logger.warning(f"Unknown google_ads_mode: {google_ads_mode}, skipping Google Ads operations")

            # Success!
            execution_time = time.time() - start_time
            result = {
                "url": final_url,
                "alias": alias,
                "folder_name": folder_name,
                "commit_sha": commit_sha,
                "execution_time_seconds": round(execution_time, 2),
                "primary_keyword": ctx.primary_keyword,
                "keywords_found": len(ctx.keywords),
                "headlines_found": len(ctx.headlines),
                "google_ads_mode": google_ads_mode,
                "google_ads_result": google_ads_result
            }

            logger.info(f"🎉 Landing page generation completed successfully in {execution_time:.2f}s")
            logger.info(f"📍 Final URL: {final_url}")

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Landing page generation failed after {execution_time:.2f}s: {str(e)}")

            # Log additional context for debugging
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            # Re-raise with context
            raise RuntimeError(f"Landing page generation failed: {str(e)}") from e

    def validate_system_configuration(self) -> Dict[str, Any]:
        """Validate that all required services and configurations are working."""
        logger.info("🔍 Validating system configuration...")

        results = {
            "overall_status": "unknown",
            "checks": {},
            "errors": []
        }

        # Check environment variables
        env_checks = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "GITHUB_REPO_OWNER": self.github_owner,
            "GITHUB_TOKEN": self.github_token,
        }

        for var, value in env_checks.items():
            status = "✅" if value else "❌"
            results["checks"][f"env_{var.lower()}"] = status
            if not value:
                results["errors"].append(f"Missing environment variable: {var}")

        # Check templates directory
        try:
            if os.path.exists(self.templates_dir):
                template_file = os.path.join(self.templates_dir, "base.html")
                if os.path.exists(template_file):
                    results["checks"]["templates_dir"] = "✅"
                else:
                    results["checks"]["templates_dir"] = "❌"
                    results["errors"].append("base.html template not found")
            else:
                results["checks"]["templates_dir"] = "❌"
                results["errors"].append("Templates directory not found")
        except Exception as e:
            results["checks"]["templates_dir"] = "❌"
            results["errors"].append(f"Template check error: {str(e)}")

        # Test GitHub API
        try:
            # First test repository access
            repo_response = self._github_get("")
            if repo_response.status_code == 200:
                results["checks"]["github_repo_exists"] = "✅"
                # Then test file access
                file_response = self._github_get("/contents/README.md")
                if file_response.status_code in [200, 404]:  # 404 is OK if no README
                    results["checks"]["github_api"] = "✅"
                else:
                    results["checks"]["github_api"] = "❌"
                    results["errors"].append(f"GitHub file API error: {file_response.status_code}")
            elif repo_response.status_code == 404:
                results["checks"]["github_api"] = "❌"
                results["checks"]["github_repo_exists"] = "❌"
                results["errors"].append(f"GitHub repository '{self.github_owner}/{self.github_repo}' not found")
            elif repo_response.status_code == 401:
                results["checks"]["github_api"] = "❌"
                results["checks"]["github_repo_exists"] = "❌"
                results["errors"].append("GitHub authentication failed")
            else:
                results["checks"]["github_api"] = "❌"
                results["checks"]["github_repo_exists"] = "❌"
                results["errors"].append(f"GitHub API error: {repo_response.status_code}")
        except Exception as e:
            results["checks"]["github_api"] = "❌"
            results["checks"]["github_repo_exists"] = "❌"
            results["errors"].append(f"GitHub API test failed: {str(e)}")

        # Test OpenAI API
        try:
            if self.openai_model.startswith("gemini"):
                # Test Gemini API
                import google.generativeai as genai
                api_key = os.getenv("GOOGLE_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(self.openai_model)
                    response = model.generate_content("Test", generation_config=genai.types.GenerationConfig(max_output_tokens=10))
                    if response and response.text:
                        results["checks"]["ai_api"] = "✅"
                    else:
                        results["checks"]["ai_api"] = "❌"
                        results["errors"].append("Gemini API test failed: empty response")
                else:
                    results["checks"]["ai_api"] = "❌"
                    results["errors"].append("GOOGLE_API_KEY not set for Gemini model")
            else:
                # Test OpenAI API
                headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}", "Content-Type": "application/json"}
                payload = {
                    "model": self.openai_model,
                    "messages": [{"role": "user", "content": "Test"}],
                    "max_tokens": 10
                }
                response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
                if response.status_code == 200:
                    results["checks"]["ai_api"] = "✅"
                else:
                    results["checks"]["ai_api"] = "❌"
                    results["errors"].append(f"OpenAI API error: {response.status_code}")
        except ImportError:
            results["checks"]["ai_api"] = "❌"
            results["errors"].append("Required AI package not installed")
        except Exception as e:
            results["checks"]["ai_api"] = "❌"
            results["errors"].append(f"AI API test failed: {str(e)}")

        # Overall status
        if results["errors"]:
            results["overall_status"] = "❌ FAILED"
        else:
            results["overall_status"] = "✅ OK"

        logger.info(f"System validation completed: {results['overall_status']}")
        if results["errors"]:
            logger.error(f"Errors found: {len(results['errors'])}")

        return results

    def diagnose_github_issues(self) -> Dict[str, Any]:
        """Diagnose GitHub-related issues for debugging."""
        logger.info("Running GitHub diagnostics...")

        results = {
            "timestamp": time.time(),
            "checks": {},
            "recommendations": []
        }

        # Check environment variables
        env_vars = {
            "GITHUB_REPO_OWNER": self.github_owner,
            "GITHUB_REPO_NAME": self.github_repo,
            "GITHUB_TOKEN": "***" + self.github_token[-4:] if self.github_token else None
        }

        results["environment"] = env_vars

        # Check repository access
        repo_check = self._verify_github_repository_access()
        results["repository_check"] = repo_check

        if not repo_check.get("exists"):
            results["checks"]["repository_exists"] = "❌"
            results["recommendations"].append(f"Repository '{self.github_owner}/{self.github_repo}' not found. Check repository name and owner.")
        else:
            results["checks"]["repository_exists"] = "✅"
            results["recommendations"].append(f"Repository found: {repo_check.get('name')}")

        if not repo_check.get("can_push", False):
            results["checks"]["push_permissions"] = "❌"
            results["recommendations"].append("No push permissions to repository. Check token permissions.")
        else:
            results["checks"]["push_permissions"] = "✅"

        # Test token validity
        try:
            user_response = requests.get("https://api.github.com/user", headers=self._github_headers(), timeout=10)
            if user_response.status_code == 200:
                user_data = user_response.json()
                results["checks"]["token_valid"] = "✅"
                results["token_user"] = user_data.get("login")
                results["recommendations"].append(f"Token belongs to user: {user_data.get('login')}")
            else:
                results["checks"]["token_valid"] = "❌"
                results["recommendations"].append(f"Token validation failed: HTTP {user_response.status_code}")
        except Exception as e:
            results["checks"]["token_valid"] = "❌"
            results["recommendations"].append(f"Token validation error: {str(e)}")

        # Test file creation simulation
        try:
            # Try to get a non-existent file to test API access
            test_path = f"/contents/test-diagnostic-{int(time.time())}.txt"
            test_response = self._github_get(test_path)
            if test_response.status_code == 404:
                results["checks"]["api_file_access"] = "✅"
                results["recommendations"].append("File API access working (404 for non-existent file is expected)")
            else:
                results["checks"]["api_file_access"] = "❌"
                results["recommendations"].append(f"Unexpected file API response: {test_response.status_code}")
        except Exception as e:
            results["checks"]["api_file_access"] = "❌"
            results["recommendations"].append(f"File API access error: {str(e)}")

        # Overall assessment
        all_checks_pass = all("✅" in str(status) for status in results["checks"].values())
        results["overall_status"] = "✅ PASS" if all_checks_pass else "❌ ISSUES FOUND"

        logger.info(f"GitHub diagnostics completed: {results['overall_status']}")
        return results

    def system_prompt_text(self) -> str:
        return self._system_prompt()

    @staticmethod
    def get_available_templates() -> List[str]:
        """Retorna la lista de nombres de templates disponibles con extensión .html"""
        templates = LandingPageGenerator.get_templates_static()
        return [template["name"] + ".html" if not template["name"].endswith(".html") else template["name"] for template in templates]

    @staticmethod
    def get_templates_static() -> List[Dict[str, Any]]:
        """Retorna la lista estática de templates disponibles para landing pages"""
        return [
            {
                "name": "base_optimized",
                "title": "Base Optimizada (Recomendado)",
                "description": "Template de alto rendimiento con carga rápida, SEO avanzado y soporte para 6 imágenes.",
                "category": "general",
                "preview": "/static/previews/base-optimized-preview.jpg"
            },
            {
                "name": "base",
                "title": "Template Base",
                "description": "Template básico y versátil para cualquier tipo de campaña",
                "category": "general",
                "preview": "/static/previews/base-preview.jpg"
            },
            {
                "name": "mystical",
                "title": "Místico",
                "description": "Template con diseño místico para servicios espirituales y tarot",
                "category": "esoterismo",
                "preview": "/static/previews/mystical-preview.jpg"
            },
            {
                "name": "romantic",
                "title": "Romántico",
                "description": "Template romántico para servicios de amor y pareja",
                "category": "amor",
                "preview": "/static/previews/romantic-preview.jpg"
            },
            {
                "name": "prosperity",
                "title": "Prosperidad",
                "description": "Template para servicios de abundancia y prosperidad económica",
                "category": "prosperidad",
                "preview": "/static/previews/prosperity-preview.jpg"
            },
            {
                "name": "llama-gemela",
                "title": "Llama Gemela",
                "description": "Template especializado en conexión con el alma gemela",
                "category": "esoterismo",
                "preview": "/static/previews/llama-gemela-preview.jpg"
            },
            {
                "name": "llamado-del-alma",
                "title": "Llamado del Alma",
                "description": "Template para guía espiritual y llamado del alma",
                "category": "esoterismo",
                "preview": "/static/previews/llamado-del-alma-preview.jpg"
            },
            {
                "name": "el-libro-prohibido",
                "title": "El Libro Prohibido",
                "description": "Template misterioso para conocimientos ocultos",
                "category": "esoterismo",
                "preview": "/static/previews/el-libro-prohibido-preview.jpg"
            },
            {
                "name": "la-luz",
                "title": "La Luz",
                "description": "Template luminoso para sanación y luz espiritual",
                "category": "sanacion",
                "preview": "/static/previews/la-luz-preview.jpg"
            },
            {
                "name": "amarre-eterno",
                "title": "Amarre Eterno",
                "description": "Template para rituales de amor eterno",
                "category": "amor",
                "preview": "/static/previews/amarre-eterno-preview.jpg"
            },
            {
                "name": "tarot-akashico",
                "title": "Tarot Akáshico",
                "description": "Template para lecturas de tarot y registros akáshicos",
                "category": "esoterismo",
                "preview": "/static/previews/tarot-akashico-preview.jpg"
            },
            {
                "name": "brujeria-blanca",
                "title": "Brujería Blanca",
                "description": "Template para prácticas de brujería blanca y magia positiva",
                "category": "esoterismo",
                "preview": "/static/previews/brujeria-blanca-preview.jpg"
            },
            {
                "name": "santeria-prosperidad",
                "title": "Santería Prosperidad",
                "description": "Template para rituales de santería y prosperidad",
                "category": "esoterismo",
                "preview": "/static/previews/santeria-prosperidad-preview.jpg"
            },
            {
                "name": "curanderismo-ancestral",
                "title": "Curanderismo Ancestral",
                "description": "Template para curanderismo y medicina ancestral",
                "category": "sanacion",
                "preview": "/static/previews/curanderismo-ancestral-preview.jpg"
            },
            {
                "name": "brujeria-negra-venganza",
                "title": "Brujería Negra Venganza",
                "description": "Template para rituales de venganza y justicia",
                "category": "esoterismo",
                "preview": "/static/previews/brujeria-negra-venganza-preview.jpg"
            },
            {
                "name": "ritual-amor-eterno",
                "title": "Ritual Amor Eterno",
                "description": "Template para rituales de amor eterno y compromiso",
                "category": "amor",
                "preview": "/static/previews/ritual-amor-eterno-preview.jpg"
            },
            {
                "name": "lectura-aura-sanacion",
                "title": "Lectura de Aura Sanación",
                "description": "Template para lectura de aura y sanación energética",
                "category": "sanacion",
                "preview": "/static/previews/lectura-aura-sanacion-preview.jpg"
            },
            {
                "name": "hechizos-abundancia",
                "title": "Hechizos Abundancia",
                "description": "Template para hechizos de abundancia y riqueza",
                "category": "prosperidad",
                "preview": "/static/previews/hechizos-abundancia-preview.jpg"
            },
            {
                "name": "conexion-guias-espirituales",
                "title": "Conexión Guías Espirituales",
                "description": "Template para conexión con guías espirituales",
                "category": "esoterismo",
                "preview": "/static/previews/conexion-guias-espirituales-preview.jpg"
            },
            {
                "name": "nocturnal",
                "title": "Nocturnal",
                "description": "Template nocturno para rituales y ceremonias nocturnas",
                "category": "esoterismo",
                "preview": "/static/previews/nocturnal-preview.jpg"
            },
            {
                "name": "jose-amp",
                "title": "José AMP",
                "description": "Template AMP de alta conversión para servicios espirituales y esoterismo",
                "category": "esoterismo",
                "preview": "/static/previews/jose-amp-preview.jpg"
            }
        ]
