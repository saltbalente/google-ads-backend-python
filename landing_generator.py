import os
import base64
import json
import time
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

from vercel_client import VercelClient


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
    ):
        # Validate critical environment variables
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        if not vercel_token:
            raise ValueError("VERCEL_TOKEN environment variable is required")
        if not vercel_project_id:
            raise ValueError("VERCEL_PROJECT_ID environment variable is required")

        self.google_ads_client_provider = google_ads_client_provider
        self.openai_model = openai_model
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.github_token = github_token
        td = templates_dir
        if not os.path.isabs(td):
            td = os.path.abspath(os.path.join(os.path.dirname(__file__), td))
        if not os.path.exists(td):
            raise ValueError(f"Templates directory does not exist: {td}")
        self.templates_dir = td
        self.env = Environment(loader=FileSystemLoader(td), autoescape=select_autoescape(["html"]))
        self.vercel = VercelClient(token=vercel_token, team_id=vercel_team_id, project_id=vercel_project_id)
        self.base_domain = base_domain

    def _get_google_ads_client(self):
        if self.google_ads_client_provider:
            return self.google_ads_client_provider()
        from app import get_google_ads_client
        return get_google_ads_client()

    def extract_ad_group_context(self, customer_id: str, ad_group_id: str) -> AdGroupContext:
        if not customer_id or not ad_group_id:
            raise ValueError("customer_id and ad_group_id are required")
        
        print(f"  🔍 [Context] Extrayendo datos para CID: {customer_id}, AdGroup: {ad_group_id}")
        try:
            client = self._get_google_ads_client()
            svc = client.get_service("GoogleAdsService")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Ads client: {str(e)}")
        
        customer_id = customer_id.replace("-", "")
        ad_group_id = ad_group_id.replace("-", "")

        # Keywords
        print("  🔍 [Context] Consultando keywords...")
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
        except Exception as e:
            raise RuntimeError(f"Failed to query keywords: {str(e)}")
        
        keywords = []
        for row in kw_rows:
            text = row.ad_group_criterion.keyword.text
            if text:
                keywords.append(text)
        print(f"  ✅ [Context] {len(keywords)} keywords encontradas (Primary)")
        
        if not keywords:
            print("  🔍 [Context] Intentando fallback de keywords...")
            try:
                kw_fallback = svc.search(customer_id=customer_id, query=f"""
                    SELECT ad_group_criterion.keyword.text, metrics.impressions
                    FROM keyword_view
                    WHERE ad_group.id = {ad_group_id}
                    ORDER BY metrics.impressions DESC
                    LIMIT 20
                """)
                keywords = [r.ad_group_criterion.keyword.text for r in kw_fallback if r.ad_group_criterion.keyword.text]
            except Exception as e:
                print(f"  ⚠️ [Context] Fallback keywords query failed: {str(e)}")
        
        if len(keywords) > 10:
            keywords = keywords[:10]

        # Ads
        print("  🔍 [Context] Consultando anuncios...")
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
        except Exception as e:
            raise RuntimeError(f"Failed to query ads: {str(e)}")
        
        headlines = []
        descriptions = []
        locations = []
        for row in ads_rows:
            ad = row.ad_group_ad.ad
            if ad.responsive_search_ad and ad.responsive_search_ad.headlines:
                headlines.extend([h.text for h in ad.responsive_search_ad.headlines if h.text])
            if ad.responsive_search_ad and ad.responsive_search_ad.descriptions:
                descriptions.extend([d.text for d in ad.responsive_search_ad.descriptions if d.text])
        print(f"  ✅ [Context] {len(headlines)} titulares y {len(descriptions)} descripciones encontradas")

        # Locations
        print("  🔍 [Context] Consultando ubicación (Campaign Resource Name)...")
        try:
            camp_query = f"SELECT ad_group.campaign FROM ad_group WHERE ad_group.id = {ad_group_id}"
            camp_rows = svc.search(customer_id=customer_id, query=camp_query)
        except Exception as e:
            print(f"  ⚠️ [Context] Campaign query failed: {str(e)}")
            campaign_resource_name = None
        else:
            campaign_resource_name = None
            for row in camp_rows:
                campaign_resource_name = row.ad_group.campaign
                break
            
        if campaign_resource_name:
            print(f"  🔍 [Context] Campaña encontrada: {campaign_resource_name}")
            try:
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
                print(f"  ✅ [Context] {len(locations)} ubicaciones encontradas")
            except Exception as e:
                print(f"  ⚠️ [Context] Locations query failed: {str(e)}")
        else:
            print("  ⚠️ [Context] No se encontró la campaña asociada")

        primary_keyword = keywords[0] if keywords else ""
        return AdGroupContext(keywords=keywords, headlines=headlines, descriptions=descriptions, locations=locations, primary_keyword=primary_keyword)

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
        print(f"  🤖 [AI] Iniciando generación con modelo: {self.openai_model}")
        payload = {
            "keywords": ctx.keywords,
            "headlines": ctx.headlines,
            "descriptions": ctx.descriptions,
            "locations": ctx.locations,
            "primary_keyword": ctx.primary_keyword,
        }
        
        content = ""
        
        if self.openai_model.startswith("gemini"):
            try:
                import google.generativeai as genai
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("GOOGLE_API_KEY environment variable is not set")
                
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(self.openai_model)
                
                # Construct prompt for Gemini
                prompt = f"{self._system_prompt()}\n\nContexto:\n{json.dumps(payload, ensure_ascii=False)}"
                
                generation_config = genai.types.GenerationConfig(
                    temperature=0.7,
                )
                
                # Try to use JSON mode if supported by the model (Gemini 1.5+)
                if "1.5" in self.openai_model:
                     generation_config.response_mime_type = "application/json"

                response = model.generate_content(prompt, generation_config=generation_config)
                content = response.text
            except ImportError:
                raise ImportError("Please install google-generativeai package: pip install google-generativeai")
            except Exception as e:
                raise RuntimeError(f"Gemini API Error: {str(e)}")
        else:
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            rsp = openai.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "system", "content": self._system_prompt()}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            content = rsp.choices[0].message.content
        
        print("  ✅ [AI] Respuesta recibida. Procesando JSON...")
        # Strip markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"  ❌ [AI] Error parsing JSON: {e}")
            print(f"  ❌ [AI] Raw content: {content[:500]}...")
            raise RuntimeError(f"AI returned invalid JSON: {str(e)}")
        
        # Validate required keys
        required_keys = ["headline_h1", "subheadline", "cta_text", "social_proof", "benefits", "seo_title", "seo_description"]
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            raise RuntimeError(f"AI response missing required keys: {missing_keys}")
        
        return GeneratedContent(
            headline_h1=data["headline_h1"],
            subheadline=data["subheadline"],
            cta_text=data["cta_text"],
            social_proof=data.get("social_proof", [])[:3],
            benefits=data.get("benefits", [])[:4],
            seo_title=data["seo_title"],
            seo_description=data["seo_description"],
        )

    def render(self, gen: GeneratedContent, config: Dict[str, Any]) -> str:
        try:
            tpl = self.env.get_template("base.html")
        except Exception as e:
            raise RuntimeError(f"Template 'base.html' not found or invalid: {str(e)}")
        
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

    def _github_headers(self):
        return {"Authorization": f"Bearer {self.github_token}", "Accept": "application/vnd.github+json"}

    def _github_api(self, path: str):
        return f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}{path}"

    def _github_get(self, path: str, retries: int = 3):
        for attempt in range(retries):
            try:
                r = requests.get(self._github_api(path), headers=self._github_headers(), timeout=30)
                if r.status_code == 401:
                    raise RuntimeError("GitHub authentication failed. Check GITHUB_TOKEN.")
                if r.status_code == 403:
                    raise RuntimeError("GitHub API rate limit exceeded or insufficient permissions.")
                return r
            except requests.RequestException as e:
                if attempt == retries - 1:
                    raise RuntimeError(f"GitHub API request failed after {retries} attempts: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def _github_put(self, path: str, payload: dict, retries: int = 3):
        for attempt in range(retries):
            try:
                r = requests.put(self._github_api(path), headers=self._github_headers(), json=payload, timeout=60)
                if r.status_code == 401:
                    raise RuntimeError("GitHub authentication failed. Check GITHUB_TOKEN.")
                if r.status_code == 403:
                    raise RuntimeError("GitHub API rate limit exceeded or insufficient permissions.")
                return r
            except requests.RequestException as e:
                if attempt == retries - 1:
                    raise RuntimeError(f"GitHub API request failed after {retries} attempts: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff

    def publish_to_github(self, ad_group_id: str, html_content: str, branch: str = "main") -> Dict[str, Any]:
        print(f"  🐙 [GitHub] Publicando landing-{ad_group_id}...")
        folder = f"landing-{ad_group_id}"
        path = f"/{folder}/index.html"
        content_b64 = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
        get_rsp = self._github_get(f"/contents{path}")
        sha = None
        if get_rsp.status_code == 200:
            sha = get_rsp.json().get("sha")
            print(f"  ℹ️ [GitHub] Archivo existente encontrado (SHA: {sha})")
        payload = {"message": f"feat: add landing {folder}", "content": content_b64, "branch": branch}
        if sha:
            payload["sha"] = sha
        put_rsp = self._github_put(f"/contents{path}", payload)
        if put_rsp.status_code not in [200, 201]:
            print(f"  ❌ [GitHub] Error publicando: {put_rsp.status_code} - {put_rsp.text}")
        put_rsp.raise_for_status()
        return put_rsp.json()

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

    def wait_vercel_ready_for_commit(self, commit_sha: Optional[str] = None, timeout_sec: int = 900) -> Dict[str, Any]:
        print(f"  ▲ [Vercel] Esperando despliegue para commit: {commit_sha}")
        if not commit_sha:
            # Fallback if no SHA provided (should not happen in normal flow)
            return self.vercel.list_deployments(limit=1)["deployments"][0]
            
        search = {"meta-githubCommitSha": commit_sha}
        
        # Poll for the deployment to appear in the list (Vercel webhook latency)
        start_wait = time.time()
        while time.time() - start_wait < 120:  # Wait up to 2 minutes for deployment to be created
            deployments = self.vercel.list_deployments(limit=50, search=search).get("deployments", [])
            if deployments:
                target = deployments[0]
                dep_id = target.get("uid") or target.get("id")
                print(f"  ▲ [Vercel] Despliegue encontrado: {dep_id}. Esperando estado READY...")
                # Once found, poll for readiness
                return self.vercel.poll_ready(dep_id, timeout_sec=timeout_sec)
            time.sleep(3)
            
        raise RuntimeError(f"No deployment found for commit {commit_sha} after waiting")

    def health_check(self, url: str, whatsapp_number: str, phone_number: str, gtm_id: str) -> bool:
        print(f"  🏥 [Health] Verificando {url}...")
        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                print(f"  ❌ [Health] Status {r.status_code}")
                return False
            html = r.text
            
            # Content checks
            checks = [
                (f"wa.me/{whatsapp_number}", "WhatsApp number"),
                (f"tel:{phone_number}", "Phone number"),
                (gtm_id, "GTM ID"),
                ("<h1", "H1 tag"),
                ("<title>", "Title tag"),
                ('name="description"', "Meta description"),
            ]
            
            for check_content, check_name in checks:
                if check_content not in html:
                    print(f"  ❌ [Health] Missing {check_name}")
                    return False
                
            return True
        except requests.RequestException as e:
            print(f"  ❌ [Health] Request failed: {str(e)}")
            return False
        except Exception as e:
            print(f"  ❌ [Health] Unexpected error: {str(e)}")
            return False

    def update_final_urls(self, customer_id: str, ad_group_id: str, final_url: str):
        print(f"  🔄 [GoogleAds] Actualizando Final URLs para AdGroup {ad_group_id}...")
        client = self._get_google_ads_client()
        ga_svc = client.get_service("GoogleAdsService")
        ag_svc = client.get_service("AdGroupAdService")
        customer_id = customer_id.replace("-", "")
        ad_group_id = ad_group_id.replace("-", "")
        q = f"""
            SELECT ad_group_ad.resource_name FROM ad_group_ad
            WHERE ad_group.id = {ad_group_id}
              AND ad_group_ad.status != REMOVED
        """
        rows = ga_svc.search(customer_id=customer_id, query=q)
        ops = []
        for row in rows:
            update = client.get_type("AdGroupAd")
            update.resource_name = row.ad_group_ad.resource_name
            update.ad = client.get_type("Ad")
            del update.ad.final_urls[:]
            update.ad.final_urls.append(final_url)
            op = client.get_type("AdGroupAdOperation")
            op.update = update
            op.update_mask.CopyFrom(client.get_type("FieldMask")(paths=["ad.final_urls"]))
            ops.append(op)
        if ops:
            print(f"  🔄 [GoogleAds] Enviando {len(ops)} operaciones de actualización...")
            ag_svc.mutate_ad_group_ads(customer_id=customer_id, operations=ops)

    def run(self, customer_id: str, ad_group_id: str, whatsapp_number: str, gtm_id: str, phone_number: Optional[str] = None, webhook_url: Optional[str] = None) -> Dict[str, Any]:
        # Input validation
        if not customer_id or not ad_group_id:
            raise ValueError("customer_id and ad_group_id are required")
        if not whatsapp_number or not gtm_id:
            raise ValueError("whatsapp_number and gtm_id are required")
        if not whatsapp_number.startswith("+"):
            raise ValueError("whatsapp_number must start with +")
        
        print(f"🚀 Iniciando generación de landing para AdGroup: {ad_group_id}")
        try:
            if not phone_number:
                phone_number = whatsapp_number
                
            print("📊 Extrayendo contexto del Ad Group...")
            ctx = self.extract_ad_group_context(customer_id, ad_group_id)
            print(f"✅ Contexto extraído. Keywords: {len(ctx.keywords)}, Ads: {len(ctx.headlines)}")
            
            print("🤖 Generando contenido con IA...")
            gen = self.generate_content(ctx)
            print("✅ Contenido generado correctamente")
            
            config = {
                "whatsapp_number": whatsapp_number,
                "phone_number": phone_number,
                "gtm_id": gtm_id,
                "webhook_url": webhook_url,
                "primary_keyword": ctx.primary_keyword
            }
            
            print("🎨 Renderizando HTML...")
            html = self.render(gen, config)
            
            print("🐙 Publicando a GitHub...")
            gh = self.publish_to_github(ad_group_id, html)
            print(f"✅ Publicado en GitHub. SHA: {gh.get('commit', {}).get('sha')}")
            
            alias = self.build_alias_domain(ctx.primary_keyword or f"landing-{ad_group_id}")
            print(f"🔗 Alias construido: {alias}")
            
            print("⏳ Esperando despliegue en Vercel...")
            try:
                dep = self.wait_vercel_ready_for_commit(commit_sha=gh.get("commit", {}).get("sha"))
                print(f"✅ Despliegue listo. UID: {dep.get('uid')}")
            except Exception as e:
                raise RuntimeError(f"Vercel deployment failed: {str(e)}")
            
            print(f"🌐 Creando alias {alias}...")
            try:
                self.vercel.create_alias(dep.get("uid") or dep.get("id"), alias)
            except Exception as e:
                raise RuntimeError(f"Failed to create Vercel alias: {str(e)}")
            
            url = f"https://{alias}"
            print(f"✅ URL final: {url}")
            
            print("🏥 Ejecutando Health Check...")
            try:
                ok = self.health_check(url, whatsapp_number, phone_number, gtm_id)
                if not ok:
                    print("❌ Health check falló")
                    raise RuntimeError(f"Health check failed for {url}")
                print("✅ Health check exitoso")
            except Exception as e:
                raise RuntimeError(f"Health check error: {str(e)}")
                
            print("🔄 Actualizando Final URLs en Google Ads...")
            try:
                self.update_final_urls(customer_id, ad_group_id, url)
                print("✅ Final URLs actualizadas")
            except Exception as e:
                raise RuntimeError(f"Failed to update Google Ads URLs: {str(e)}")
            
            return {"url": url, "alias": alias}
            
        except Exception as e:
            import traceback
            print(f"❌ ERROR CRÍTICO en LandingPageGenerator: {str(e)}")
            traceback.print_exc()
            raise e

    def system_prompt_text(self) -> str:
        return self._system_prompt()
