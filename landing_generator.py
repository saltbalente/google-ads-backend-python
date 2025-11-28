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

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv

from vercel_client import VercelClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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


class LandingPageGenerator:
    def __init__(
        self,
        google_ads_client_provider: Optional[Callable[[], Any]] = None,
        openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o"),
        github_owner: str = os.getenv("GITHUB_REPO_OWNER", ""),
        github_repo: str = os.getenv("GITHUB_REPO_NAME", "monorepo-landings"),
        github_token: str = os.getenv("GITHUB_TOKEN", ""),
        templates_dir: str = os.getenv("LANDING_TEMPLATES_DIR", "templates/landing"),
        vercel_project_id: Optional[str] = os.getenv("VERCEL_PROJECT_ID"),
        vercel_team_id: Optional[str] = os.getenv("VERCEL_TEAM_ID"),
        vercel_token: Optional[str] = os.getenv("VERCEL_TOKEN"),
        base_domain: str = os.getenv("LANDINGS_BASE_DOMAIN", "tudominio.com"),
        custom_domain: Optional[str] = os.getenv("GITHUB_PAGES_CUSTOM_DOMAIN"),
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
        if vercel_token and not vercel_token.strip():
            raise ValueError("VERCEL_TOKEN cannot be empty if provided")
        if vercel_project_id and not vercel_project_id.strip():
            raise ValueError("VERCEL_PROJECT_ID cannot be empty if provided")

        self.google_ads_client_provider = google_ads_client_provider
        self.openai_model = openai_model
        self.github_owner = github_owner.strip()
        self.github_repo = github_repo.strip()
        self.github_token = github_token.strip()
        self.vercel_token = vercel_token.strip() if vercel_token else None
        self.vercel_project_id = vercel_project_id.strip() if vercel_project_id else None

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

        # Vercel client (optional)
        if vercel_token and vercel_project_id:
            try:
                self.vercel = VercelClient(token=vercel_token.strip(), team_id=vercel_team_id, project_id=vercel_project_id.strip())
                logger.info("✅ Vercel client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Vercel client: {str(e)}")
                self.vercel = None
        else:
            self.vercel = None
            logger.info("ℹ️ Vercel client not initialized (optional)")

        # Domain validation
        if not base_domain or not base_domain.strip():
            raise ValueError("LANDINGS_BASE_DOMAIN cannot be empty")
        self.base_domain = base_domain.strip()
        self.custom_domain = custom_domain.strip() if custom_domain else None

        # Configuration parameters
        self.max_retries = max(1, max_retries)
        self.request_timeout = max(10, request_timeout)
        self.health_check_timeout = max(5, health_check_timeout)

        logger.info(f"LandingPageGenerator initialized successfully with model: {self.openai_model}")

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

    def _system_prompt(self) -> str:
        return (
            "Eres un generador experto de contenido para Landing Pages de alta conversión. "
            "Recibirás contexto de un Ad Group de Google Ads con keywords principales, mensajes de anuncios y ubicación. "
            "Responde SOLO con un JSON válido con las claves: "
            "headline_h1, subheadline, cta_text, social_proof (lista de 3 strings con testimonios falsos pero altamente creíbles y persuasivos), benefits (lista de 4 strings), "
            "seo_title, seo_description. El tono debe alinearse con los titulares y la keyword principal. "
            "Usa el idioma del usuario en español mexicano."
        )

    def generate_content(self, ctx: AdGroupContext) -> GeneratedContent:
        """Generate landing page content using AI with comprehensive error handling."""
        if not ctx or not isinstance(ctx, AdGroupContext):
            raise ValueError("Valid AdGroupContext is required")

        logger.info(f"Generating content using model: {self.openai_model}")

        # Validate context has minimum required data
        if not ctx.keywords and not ctx.headlines and not ctx.descriptions:
            raise ValueError("AdGroupContext must contain at least keywords, headlines, or descriptions")

        payload = {
            "keywords": ctx.keywords[:5],  # Limit to prevent token overflow
            "headlines": ctx.headlines[:5],
            "descriptions": ctx.descriptions[:5],
            "locations": ctx.locations[:3],
            "primary_keyword": ctx.primary_keyword or "servicio"
        }

        content = ""

        try:
            if self.openai_model.startswith("gemini"):
                content = self._generate_with_gemini(payload)
            else:
                content = self._generate_with_openai(payload)
        except Exception as e:
            logger.error(f"AI content generation failed: {str(e)}")
            raise RuntimeError(f"Failed to generate content with {self.openai_model}: {str(e)}")

        logger.info("AI response received, processing JSON")
        return self._parse_ai_response(content)

    def _generate_with_gemini(self, payload: dict) -> str:
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

        prompt = f"{self._system_prompt()}\n\nContexto:\n{json.dumps(payload, ensure_ascii=False)}"

        generation_config = genai.types.GenerationConfig(temperature=0.7)

        # Use JSON mode for newer models
        if "1.5" in self.openai_model:
            generation_config.response_mime_type = "application/json"

        response = model.generate_content(prompt, generation_config=generation_config)

        if not response or not response.text:
            raise RuntimeError("Gemini API returned empty response")

        return response.text

    def _generate_with_openai(self, payload: dict) -> str:
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
                {"role": "system", "content": self._system_prompt()},
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
            )
        except Exception as e:
            raise RuntimeError(f"Error processing AI response data: {str(e)}")

    def render(self, gen: GeneratedContent, config: Dict[str, Any]) -> str:
        try:
            # Check if template is explicitly selected from iOS app
            selected_template = config.get("selected_template")

            if selected_template:
                # Validate selected template exists
                available_templates = self.get_available_templates()
                if selected_template in available_templates:
                    template_name = selected_template
                    logger.info(f"🎨 Using user-selected template: {template_name}")
                else:
                    logger.warning(f"⚠️ Selected template '{selected_template}' not available, falling back to auto-selection")
                    selected_template = None

            if not selected_template:
                # Seleccionar template basado en la palabra clave principal (auto-selection)
                primary_keyword = config.get("primary_keyword", "").lower()

                # Lógica de selección de template
                if "tarot" in primary_keyword or "cartas" in primary_keyword:
                    template_name = "mystical.html"  # Template místico para tarot
                elif "amor" in primary_keyword or "pareja" in primary_keyword:
                    template_name = "romantic.html"  # Template romántico para temas de amor
                elif "dinero" in primary_keyword or "riqueza" in primary_keyword:
                    template_name = "prosperity.html"  # Template de prosperidad
                else:
                    template_name = "base.html"  # Template por defecto

                logger.info(f"🎨 Auto-selected template: {template_name}")

            tpl = self.env.get_template(template_name)
        except Exception as e:
            # Fallback a base.html si el template específico no existe
            try:
                tpl = self.env.get_template("base.html")
            except Exception as fallback_error:
                raise RuntimeError(f"Template 'base.html' not found or invalid: {str(fallback_error)}")

        try:
            return tpl.render(
                headline_h1=gen.headline_h1,
                subheadline=gen.subheadline,
                cta_text=gen.cta_text,
                social_proof=gen.social_proof,
                benefits=gen.benefits,
                seo_title=gen.seo_title,
                seo_description=gen.seo_description,
                whatsapp_number=config["whatsapp_number"],
                phone_number=config.get("phone_number", config["whatsapp_number"]),
                webhook_url=config.get("webhook_url", ""),
                gtm_id=config["gtm_id"],
                primary_keyword=config.get("primary_keyword", ""),
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
            else:
                template_info[template] = {
                    "name": template_name.title(),
                    "description": f"Template {template_name}",
                    "preview_url": f"/api/templates/preview/{template_name}"
                }

        return template_info

    @staticmethod
    def get_templates_static() -> Dict[str, Dict[str, str]]:
        """Static method to get template information without requiring full initialization."""
        templates = ["base.html", "mystical.html", "romantic.html", "prosperity.html"]
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
        folder = alias
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
                if self.custom_domain:
                    # Use subdomain: https://alias.customdomain.com/
                    github_pages_url = f"https://{alias}.{self.custom_domain}/"
                    logger.info(f"🌐 Custom domain URL: {github_pages_url}")
                else:
                    # Use default GitHub Pages: https://owner.github.io/repo/folder/
                    github_pages_url = f"https://{self.github_owner}.github.io/{self.github_repo}/{folder}/"
                    logger.info(f"🌐 GitHub Pages URL: {github_pages_url}")

                return {
                    "commit_sha": commit_sha,
                    "url": github_pages_url,
                    "alias": alias,
                    "path": path,
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

    def wait_vercel_ready_for_commit(self, commit_sha: Optional[str] = None, timeout_sec: int = None) -> Dict[str, Any]:
        """Wait for Vercel deployment to be ready for a specific commit."""
        if timeout_sec is None:
            timeout_sec = 900  # 15 minutes default

        if not commit_sha:
            logger.warning("No commit SHA provided, fetching latest deployment")
            try:
                deployments = self.vercel.list_deployments(limit=1)
                deployments_list = deployments.get("deployments", [])
                if not deployments_list:
                    raise RuntimeError("No deployments found")
                return deployments_list[0]
            except Exception as e:
                raise RuntimeError(f"Failed to get latest deployment: {str(e)}")

        logger.info(f"Waiting for Vercel deployment of commit: {commit_sha}")

        search = {"meta-githubCommitSha": commit_sha}
        start_time = time.time()

        # Poll for deployment creation
        while time.time() - start_time < 120:  # Wait up to 2 minutes for deployment to be created
            try:
                deployments = self.vercel.list_deployments(limit=50, search=search)
                deployments_list = deployments.get("deployments", [])

                if deployments_list:
                    target = deployments_list[0]
                    dep_id = target.get("uid") or target.get("id")
                    if not dep_id:
                        raise RuntimeError("Deployment found but no ID available")

                    logger.info(f"Deployment found: {dep_id}. Waiting for READY status...")
                    # Once found, poll for readiness
                    return self.vercel.poll_ready(dep_id, timeout_sec=timeout_sec - int(time.time() - start_time))

                logger.debug("No deployment found yet, waiting...")
                time.sleep(3)

            except Exception as e:
                logger.warning(f"Error checking deployments: {str(e)}")
                time.sleep(3)

        raise RuntimeError(f"No deployment found for commit {commit_sha} after waiting 2 minutes")

    def deploy_to_vercel(self, folder_name: str, commit_sha: str, custom_domain: Optional[str] = None) -> Dict[str, Any]:
        """Deploy the landing page to Vercel after successful GitHub publishing."""
        if not self.vercel_token:
            logger.warning("Vercel token not configured, skipping Vercel deployment")
            return {"skipped": True, "reason": "Vercel token not configured"}

        if not self.vercel:
            logger.warning("Vercel client not initialized, skipping Vercel deployment")
            return {"skipped": True, "reason": "Vercel client not initialized"}

        try:
            logger.info(f"🚀 Starting Vercel deployment for folder: {folder_name}")

            # Create deployment from GitHub repository
            deployment = self.vercel.create_deployment(
                github_repo=self.github_repo,
                github_owner=self.github_owner,
                branch="main",
                project_name=f"landing-{folder_name}"
            )

            deployment_id = deployment.get("id") or deployment.get("uid")
            if not deployment_id:
                raise RuntimeError("Deployment created but no ID returned")

            logger.info(f"✅ Vercel deployment created: {deployment_id}")

            # Wait for deployment to be ready
            logger.info("⏳ Waiting for Vercel deployment to be ready...")
            ready_deployment = self.vercel.poll_ready(deployment_id, timeout_sec=600)  # 10 minutes timeout

            vercel_url = ready_deployment.get("url")
            if not vercel_url:
                raise RuntimeError("Deployment ready but no URL provided")

            logger.info(f"✅ Vercel deployment ready: {vercel_url}")

            # Assign custom domain if provided
            final_url = vercel_url
            if custom_domain:
                try:
                    logger.info(f"🔗 Assigning custom domain: {custom_domain}")
                    self.vercel.create_alias(deployment_id, custom_domain)
                    final_url = f"https://{custom_domain}"
                    logger.info(f"✅ Custom domain assigned: {final_url}")
                except Exception as e:
                    logger.warning(f"Failed to assign custom domain {custom_domain}: {str(e)}")
                    logger.info(f"Using Vercel URL instead: {vercel_url}")

            return {
                "success": True,
                "deployment_id": deployment_id,
                "vercel_url": vercel_url,
                "final_url": final_url,
                "custom_domain_assigned": custom_domain is not None and final_url.startswith("https://"),
                "commit_sha": commit_sha
            }

        except Exception as e:
            logger.error(f"❌ Vercel deployment failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "folder_name": folder_name,
                "commit_sha": commit_sha
            }

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

    def update_final_urls(self, customer_id: str, ad_group_id: str, final_url: str):
        """Update Final URLs for all ads in the Ad Group."""
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
                logger.warning(f"No active ads found in Ad Group {ad_group_id}")
                return

            logger.info(f"Found {len(resource_names)} ads to update")

            # Prepare operations
            operations = []
            for resource_name in resource_names:
                update = client.get_type("AdGroupAd")
                update.resource_name = resource_name
                update.ad = client.get_type("Ad")
                # Clear existing final URLs and add new one
                del update.ad.final_urls[:]
                update.ad.final_urls.append(final_url)

                op = client.get_type("AdGroupAdOperation")
                op.update = update
                op.update_mask.CopyFrom(client.get_type("FieldMask")(paths=["ad.final_urls"]))
                operations.append(op)

            if operations:
                logger.info(f"Sending {len(operations)} update operations to Google Ads")
                response = ag_svc.mutate_ad_group_ads(customer_id=customer_id, operations=operations)

                success_count = len(response.results)
                logger.info(f"Successfully updated {success_count} ads")

                if success_count != len(operations):
                    logger.warning(f"Expected {len(operations)} updates but got {success_count} results")
            else:
                logger.info("No operations to perform")

        except Exception as e:
            logger.error(f"Failed to update Final URLs: {str(e)}")
            raise RuntimeError(f"Google Ads URL update failed: {str(e)}")

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

    def run(self, customer_id: str, ad_group_id: str, whatsapp_number: str, gtm_id: str, phone_number: Optional[str] = None, webhook_url: Optional[str] = None, selected_template: Optional[str] = None) -> Dict[str, Any]:
        """Execute the complete landing page generation pipeline."""
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

        logger.info(f"🚀 Starting landing page generation for Ad Group: {ad_group_id}")

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
            gen = self.generate_content(ctx)
            logger.info("✅ Content generated successfully")

            # Step 3: Prepare configuration
            config = {
                "whatsapp_number": whatsapp_number,
                "phone_number": phone_number,
                "gtm_id": gtm_id,
                "webhook_url": webhook_url,
                "primary_keyword": ctx.primary_keyword,
                "folder_name": folder_name,
                "selected_template": selected_template
            }

            # Step 4: Render HTML
            logger.info("🎨 Step 3: Rendering HTML template...")
            html = self.render(gen, config)
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

            # Step 6: Deploy to Vercel (if configured)
            vercel_result = None
            vercel_url = None
            if self.vercel_token and self.vercel:
                logger.info("⚡ Step 5: Deploying to Vercel...")
                vercel_result = self.deploy_to_vercel(folder_name, commit_sha, self.custom_domain)
                if vercel_result.get("success"):
                    vercel_url = vercel_result.get("final_url")
                    final_url = vercel_url  # Use Vercel URL as the primary URL
                    logger.info(f"✅ Deployed to Vercel: {vercel_url}")
                else:
                    logger.warning(f"Vercel deployment failed: {vercel_result.get('error', 'Unknown error')}")
            else:
                logger.info("ℹ️ Vercel not configured, using GitHub Pages URL")

            # Step 7: Health check
            logger.info("🏥 Step 6: Performing health check...")
            ok = self.health_check(final_url, whatsapp_number, phone_number, gtm_id)
            if not ok:
                logger.warning(f"Health check failed for {final_url}, but continuing (GitHub Pages may take time to deploy)")
            else:
                logger.info("✅ Health check passed")

            # Step 7: Update Google Ads Final URLs
            logger.info("🔄 Step 6: Updating Google Ads Final URLs...")
            self.update_final_urls(customer_id, ad_group_id, final_url)
            logger.info("✅ Google Ads URLs updated")

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
                "headlines_found": len(ctx.headlines)
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
            "VERCEL_TOKEN": os.getenv("VERCEL_TOKEN"),
            "VERCEL_PROJECT_ID": self.vercel_project_id,
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

        # Test Vercel API
        try:
            deployments = self.vercel.list_deployments(limit=1)
            if "deployments" in deployments:
                results["checks"]["vercel_api"] = "✅"
            else:
                results["checks"]["vercel_api"] = "❌"
                results["errors"].append("Vercel API returned unexpected response")
        except Exception as e:
            results["checks"]["vercel_api"] = "❌"
            results["errors"].append(f"Vercel API test failed: {str(e)}")

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
