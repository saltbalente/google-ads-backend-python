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
from google.protobuf.field_mask_pb2 import FieldMask

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

    @staticmethod
    def get_templates_static() -> Dict[str, Dict[str, str]]:
        """Static method to get template information without requiring full initialization."""
        templates = ["base.html", "mystical.html", "romantic.html", "prosperity.html", "llama-gemela.html", "llamado-del-alma.html", "el-libro-prohibido.html", "la-luz.html"]
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
                if self.custom_domain:
                    # Construct URL: https://customdomain.com/folder/
                    github_pages_url = f"https://{self.custom_domain}/{folder_name}/"
                    logger.info(f"🌐 Custom domain URL: {github_pages_url}")
                else:
                    # Use default GitHub Pages: https://owner.github.io/repo/folder/
                    github_pages_url = f"https://{self.github_owner}.github.io/{self.github_repo}/{folder_name}/"
                    logger.info(f"🌐 GitHub Pages URL: {github_pages_url}")

                return {
                    "commit_sha": commit_sha,
                    "url": github_pages_url,
                    "alias": alias,
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

    def automate_ad_group_complete_setup(self, customer_id: str, ad_group_id: str, whatsapp_number: str, gtm_id: str, phone_number: Optional[str] = None, webhook_url: Optional[str] = None, selected_template: Optional[str] = None, google_ads_mode: str = "auto") -> Dict[str, Any]:
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

    def run(self, customer_id: str, ad_group_id: str, whatsapp_number: str, gtm_id: str, phone_number: Optional[str] = None, webhook_url: Optional[str] = None, selected_template: Optional[str] = None, google_ads_mode: str = "auto") -> Dict[str, Any]:
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
