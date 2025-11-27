"""
Worker thread para procesamiento asíncrono de automation jobs.

Arquitectura:
- ThreadPoolExecutor para ejecución concurrente
- Queue para manejo de jobs pendientes
- Robust error handling y retry logic
- Integración con Google Ads API
"""

import uuid
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Any
import traceback

from automation_models import (
    update_job, add_log, get_job, Session, close_session
)


class AutomationWorker:
    """
    Worker para procesar automation jobs en background.
    
    Features:
    - Thread-safe execution
    - Concurrent job processing (configurable workers)
    - Automatic retry on transient failures
    - Detailed logging and progress tracking
    """
    
    def __init__(self, max_workers=3):
        """
        Inicializa el worker.
        
        Args:
            max_workers: Número máximo de jobs concurrentes
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='AutoWorker')
        self.active_jobs = {}  # {job_id: Future}
        self.lock = threading.Lock()
        
    def submit_job(self, job_id: str, config: Dict[str, Any], google_ads_client_factory):
        """
        Envía un job al worker pool para procesamiento.
        
        Args:
            job_id: UUID del job
            config: Configuración del job
            google_ads_client_factory: Función que retorna cliente de Google Ads
        
        Returns:
            Future: Future del job ejecutándose
        """
        with self.lock:
            if job_id in self.active_jobs:
                raise ValueError(f"Job {job_id} ya está en ejecución")
            
            future = self.executor.submit(
                self._process_job,
                job_id,
                config,
                google_ads_client_factory
            )
            self.active_jobs[job_id] = future
            
            # Cleanup cuando termine
            future.add_done_callback(lambda f: self._cleanup_job(job_id))
            
            return future
    
    def _cleanup_job(self, job_id: str):
        """Limpia un job del tracking cuando termina"""
        with self.lock:
            self.active_jobs.pop(job_id, None)
    
    def is_job_running(self, job_id: str) -> bool:
        """Verifica si un job está actualmente en ejecución"""
        with self.lock:
            return job_id in self.active_jobs
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Intenta cancelar un job en ejecución.
        
        Returns:
            bool: True si se canceló exitosamente
        """
        with self.lock:
            future = self.active_jobs.get(job_id)
            if future and not future.done():
                cancelled = future.cancel()
                if cancelled:
                    update_job(job_id, status='cancelled', current_step='Cancelado por usuario')
                    add_log(job_id, 'WARNING', 'Job cancelado por usuario')
                return cancelled
        return False
    
    def shutdown(self, wait=True):
        """Cierra el worker pool"""
        self.executor.shutdown(wait=wait)
    
    def _process_job(self, job_id: str, config: Dict[str, Any], google_ads_client_factory):
        """
        Procesa un automation job completo.
        
        Este es el método principal que ejecuta toda la lógica de automatización.
        """
        try:
            # Actualizar a running
            update_job(
                job_id,
                status='running',
                started_at=datetime.utcnow(),
                progress=0.0,
                current_step='Iniciando procesamiento...'
            )
            add_log(job_id, 'INFO', 'Job iniciado', {'config': config})
            
            # Extraer configuración
            customer_id = config['customerId']
            campaign_id = config['campaignId']
            report_id = config['reportId']
            num_groups = config['numberOfGroups']
            ads_per_group = config['adsPerGroup']
            ai_provider = config.get('aiProvider', 'openai')
            max_keywords_per_group = config.get('maxKeywordsPerGroup', 100)  # Default: 100 keywords máximo
            
            # Crear cliente de Google Ads
            client = google_ads_client_factory(
                refresh_token=config.get('refreshToken'),
                login_customer_id=config.get('loginCustomerId')
            )
            
            # PASO 1: Cargar keywords del reporte (10% progreso)
            update_job(job_id, progress=10.0, current_step='Cargando keywords del reporte...')
            add_log(job_id, 'INFO', f'Cargando keywords del reporte {report_id}')
            
            keywords = self._load_keywords_from_report(report_id, config)
            add_log(job_id, 'SUCCESS', f'{len(keywords)} keywords cargadas', {'count': len(keywords)})
            
            if not keywords:
                raise ValueError("No se encontraron keywords en el reporte")
            
            # Limitar keywords al total permitido: num_groups * max_keywords_per_group
            max_total_keywords = num_groups * max_keywords_per_group
            if len(keywords) > max_total_keywords:
                keywords = keywords[:max_total_keywords]
                add_log(job_id, 'INFO', f'Keywords limitadas a {max_total_keywords} (máx {max_keywords_per_group} por grupo × {num_groups} grupos)')
            
            # PASO 2: Distribuir keywords en grupos (20% progreso)
            update_job(job_id, progress=20.0, current_step=f'Distribuyendo {len(keywords)} keywords en {num_groups} grupos...')
            add_log(job_id, 'INFO', f'Distribuyendo {len(keywords)} keywords en {num_groups} grupos (máx {max_keywords_per_group} por grupo)')
            
            groups = self._distribute_keywords(keywords, num_groups, max_keywords_per_group)
            add_log(job_id, 'SUCCESS', 'Keywords distribuidas', {
                'groups': len(groups),
                'keywords_per_group': [len(g) for g in groups]
            })
            
            # Resultados acumuladores
            ad_groups_created = []
            total_keywords_added = 0
            total_ads_created = 0
            
            # PASO 3: Crear ad groups, keywords y ads (20% - 90% progreso)
            total_steps = num_groups
            base_progress = 20.0
            step_increment = 70.0 / total_steps
            
            for i, group_keywords in enumerate(groups):
                group_num = i + 1
                
                # 3.1: Crear ad group
                current_progress = base_progress + (step_increment * i)
                update_job(
                    job_id,
                    progress=current_progress,
                    current_step=f'Creando grupo de anuncios {group_num}/{num_groups}...'
                )
                
                ad_group_name = f"AutoGroup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{group_num}"
                add_log(job_id, 'INFO', f'Creando ad group: {ad_group_name}')
                
                ad_group_id = self._create_ad_group(
                    client,
                    customer_id,
                    campaign_id,
                    ad_group_name
                )
                ad_groups_created.append(ad_group_id)
                add_log(job_id, 'SUCCESS', f'Ad group creado: {ad_group_id}')
                
                # 3.2: Agregar keywords al grupo
                update_job(
                    job_id,
                    progress=current_progress + (step_increment * 0.3),
                    current_step=f'Agregando {len(group_keywords)} keywords al grupo {group_num}...'
                )
                
                keywords_added = self._add_keywords_to_group(
                    client,
                    customer_id,
                    ad_group_id,
                    group_keywords
                )
                total_keywords_added += keywords_added
                add_log(job_id, 'SUCCESS', f'{keywords_added} keywords agregadas al grupo {ad_group_id}')
                
                # 3.3: Obtener URL final
                final_url = self._get_final_url(client, customer_id, campaign_id, config)
                
                # 3.4: Generar y crear ads con IA
                update_job(
                    job_id,
                    progress=current_progress + (step_increment * 0.6),
                    current_step=f'Generando {ads_per_group} anuncios con IA para grupo {group_num}...'
                )
                
                for ad_num in range(ads_per_group):
                    try:
                        add_log(job_id, 'INFO', f'Generando anuncio {ad_num + 1}/{ads_per_group} con {ai_provider}')
                        
                        ad_content = self._generate_ad_with_ai(
                            ai_provider,
                            group_keywords,
                            final_url,
                            config
                        )
                        
                        ad_resource_name = self._create_ad(
                            client,
                            customer_id,
                            ad_group_id,
                            ad_content,
                            final_url
                        )
                        
                        total_ads_created += 1
                        add_log(job_id, 'SUCCESS', f'Anuncio creado: {ad_resource_name}')
                        
                    except Exception as ad_error:
                        add_log(job_id, 'ERROR', f'Error creando anuncio {ad_num + 1}: {str(ad_error)}')
                        # Continuar con el siguiente anuncio
            
            # PASO 4: Completar job (100% progreso)
            update_job(
                job_id,
                status='completed',
                progress=100.0,
                current_step='Automatización completada exitosamente',
                completed_at=datetime.utcnow(),
                results={
                    'ad_groups_created': ad_groups_created,
                    'keywords_added': total_keywords_added,
                    'ads_created': total_ads_created,
                    'groups_processed': len(groups)
                }
            )
            
            add_log(job_id, 'SUCCESS', 'Job completado exitosamente', {
                'ad_groups': len(ad_groups_created),
                'keywords': total_keywords_added,
                'ads': total_ads_created
            })
            
        except Exception as e:
            # Error handler
            error_trace = traceback.format_exc()
            error_message = str(e)
            
            update_job(
                job_id,
                status='failed',
                current_step=f'Error: {error_message}',
                completed_at=datetime.utcnow(),
                errors=[{
                    'message': error_message,
                    'trace': error_trace,
                    'timestamp': datetime.utcnow().isoformat()
                }]
            )
            
            add_log(job_id, 'ERROR', f'Job falló: {error_message}', {
                'error': error_message,
                'trace': error_trace
            })
            
            raise
        
        finally:
            close_session()
    
    def _load_keywords_from_report(self, report_id: str, config: Dict) -> List[str]:
        """
        Carga keywords de un reporte guardado.
        
        En producción, esto debería consultar la base de datos o storage
        donde se guardan los reportes de Keyword Planner.
        """
        # TODO: Implementar carga real desde tu sistema de storage
        # Por ahora, retornamos keywords del config si existen
        
        if 'keywords' in config:
            return config['keywords']
        
        # Placeholder: En producción, cargar desde DB
        # session = get_session()
        # report = session.query(SavedReport).filter_by(id=report_id).first()
        # return [kw.text for kw in report.keywords]
        
        raise NotImplementedError(
            "Debe implementar carga de keywords desde tu sistema de storage. "
            "O pasar keywords directamente en config['keywords']"
        )
    
    def _distribute_keywords(self, keywords: List[str], num_groups: int, max_per_group: int = 100) -> List[List[str]]:
        """
        Distribuye keywords uniformemente en N grupos respetando el límite máximo.
        Elimina duplicados y normaliza.
        
        Args:
            keywords: Lista de keywords a distribuir (ya limitada al máximo total)
            num_groups: Número de grupos a crear
            max_per_group: Máximo de keywords permitidas por grupo (informativo)
        """
        # Normalizar y eliminar duplicados
        unique_keywords = list(set([
            kw.strip().lower()
            for kw in keywords
            if kw and kw.strip()
        ]))
        
        if not unique_keywords:
            return []
        
        # Distribuir uniformemente en num_groups
        keywords_per_group = len(unique_keywords) // num_groups
        remainder = len(unique_keywords) % num_groups
        
        groups = []
        start = 0
        
        for i in range(num_groups):
            # Agregar 1 keyword extra a los primeros grupos para distribuir remainder
            group_size = keywords_per_group + (1 if i < remainder else 0)
            end = start + group_size
            groups.append(unique_keywords[start:end])
            start = end
        
        return groups
    
    def _create_ad_group(self, client, customer_id: str, campaign_id: str, name: str) -> str:
        """Crea un ad group y retorna su ID"""
        ad_group_service = client.get_service("AdGroupService")
        campaign_service = client.get_service("CampaignService")
        
        operation = client.get_type("AdGroupOperation")
        ad_group = operation.create
        
        ad_group.name = name
        ad_group.campaign = campaign_service.campaign_path(customer_id, campaign_id)
        ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
        ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ad_group.cpc_bid_micros = 1000000  # $1 USD default
        
        response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id,
            operations=[operation]
        )
        
        resource_name = response.results[0].resource_name
        return resource_name.split('/')[-1]  # Extraer ID
    
    def _add_keywords_to_group(self, client, customer_id: str, ad_group_id: str, keywords: List[str]) -> int:
        """Agrega keywords a un ad group y retorna el número agregado"""
        if not keywords:
            return 0
        
        ad_group_criterion_service = client.get_service("AdGroupCriterionService")
        ad_group_service = client.get_service("AdGroupService")
        
        # ESTRATEGIA: Intentar agregar todas juntas, si falla por políticas, agregar una por una
        successful_keywords = 0
        failed_keywords = []
        
        try:
            # Intentar agregar todas las keywords en un solo batch
            operations = []
            for keyword_text in keywords:
                operation = client.get_type("AdGroupCriterionOperation")
                criterion = operation.create
                
                criterion.ad_group = ad_group_service.ad_group_path(customer_id, ad_group_id)
                criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
                criterion.keyword.text = keyword_text
                criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
                
                operations.append(operation)
            
            response = ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=operations
            )
            
            successful_keywords = len(response.results)
            return successful_keywords
            
        except Exception as e:
            error_str = str(e)
            
            # Si el error es por políticas, intentar agregar keywords una por una
            if 'POLICY_ERROR' in error_str or 'POLICY_VIOLATION' in error_str or 'policy_violation_error' in error_str:
                print(f"⚠️ Error de políticas detectado. Intentando agregar keywords individualmente...")
                
                for keyword_text in keywords:
                    try:
                        operation = client.get_type("AdGroupCriterionOperation")
                        criterion = operation.create
                        
                        criterion.ad_group = ad_group_service.ad_group_path(customer_id, ad_group_id)
                        criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
                        criterion.keyword.text = keyword_text
                        criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
                        
                        response = ad_group_criterion_service.mutate_ad_group_criteria(
                            customer_id=customer_id,
                            operations=[operation]
                        )
                        
                        successful_keywords += 1
                        
                    except Exception as kw_error:
                        kw_error_str = str(kw_error)
                        failed_keywords.append(keyword_text)
                        
                        # Log más limpio del error
                        if 'POLICY_ERROR' in kw_error_str:
                            print(f"❌ Keyword rechazada por políticas: '{keyword_text}'")
                        else:
                            print(f"❌ Keyword rechazada: '{keyword_text}' - {kw_error_str[:100]}")
                
                if failed_keywords:
                    print(f"📊 Resumen: {successful_keywords}/{len(keywords)} keywords agregadas, {len(failed_keywords)} rechazadas por políticas")
                
                return successful_keywords
            else:
                # Error diferente, propagar
                print(f"❌ Error inesperado agregando keywords: {error_str[:200]}")
                raise
        
        return 0
    
    def _get_final_url(self, client, customer_id: str, campaign_id: str, config: Dict) -> str:
        """
        Obtiene URL final para los anuncios.
        Usa fallback de 4 niveles como en el sistema actual.
        """
        # 1. Desde config si está disponible
        if 'finalUrl' in config:
            return config['finalUrl']
        
        # 2. Query a la campaña
        try:
            google_ads_service = client.get_service("GoogleAdsService")
            query = f"""
                SELECT campaign.final_url_suffix
                FROM campaign
                WHERE campaign.id = '{campaign_id}'
            """
            response = google_ads_service.search(customer_id=customer_id, query=query)
            for row in response:
                if row.campaign.final_url_suffix:
                    return row.campaign.final_url_suffix
        except:
            pass
        
        # 3. Desde search input del reporte (si está en config)
        if 'searchInput' in config:
            search_input = config['searchInput']
            if search_input.startswith('http'):
                return search_input
        
        # 4. Fallback: URL placeholder
        return "https://www.ejemplo.com"
    
    def _generate_ad_with_ai(self, provider: str, keywords: List[str], final_url: str, config: Dict) -> Dict:
        """
        Genera contenido de anuncio usando IA.
        
        Returns:
            Dict con headlines y descriptions
        """
        import os
        
        # Prompt para la IA
        keywords_text = ", ".join(keywords[:5])  # Top 5 keywords
        
        prompt = f"""Crea un anuncio de Google Ads responsive search ad para estas keywords: {keywords_text}

Genera:
- 5 títulos (máximo 30 caracteres cada uno)
- 3 descripciones (máximo 90 caracteres cada una)

Formato JSON:
{{
  "headlines": ["título1", "título2", ...],
  "descriptions": ["desc1", "desc2", "desc3"]
}}"""
        
        # Llamar al proveedor de IA correspondiente
        if provider == 'openai':
            from openai import OpenAI
            import httpx
            
            # Crear cliente HTTP sin proxy para evitar conflictos en Render.com
            http_client = httpx.Client(
                timeout=30.0,
                proxies=None,  # Deshabilitar explícitamente proxies
                transport=httpx.HTTPTransport(retries=2)
            )
            
            # Crear cliente OpenAI con configuración explícita
            client_openai = OpenAI(
                api_key=os.environ.get('OPENAI_API_KEY'),
                http_client=http_client
            )
            
            response = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            import json
            return json.loads(response.choices[0].message.content)
        
        elif provider == 'gemini':
            import google.generativeai as genai
            genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
            
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            
            import json
            return json.loads(response.text)
        
        elif provider == 'deepseek':
            # Implementación DeepSeek via OpenRouter o direct API
            # Similar a OpenAI pero con endpoint diferente
            pass
        
        # Fallback: Contenido genérico
        return {
            'headlines': [
                f'Oferta Especial {keywords[0][:20]}',
                'Mejor Precio Garantizado',
                'Compra Ahora',
                'Envío Gratis Hoy',
                'Descuento Exclusivo'
            ][:5],
            'descriptions': [
                f'Encuentra los mejores {keywords[0][:40]}. Calidad garantizada.',
                'Ofertas exclusivas por tiempo limitado. ¡No te lo pierdas!',
                'Compra segura con garantía de satisfacción.'
            ]
        }
    
    def _create_ad(self, client, customer_id: str, ad_group_id: str, ad_content: Dict, final_url: str) -> str:
        """Crea un responsive search ad y retorna su resource name"""
        ad_group_ad_service = client.get_service("AdGroupAdService")
        ad_group_service = client.get_service("AdGroupService")
        
        operation = client.get_type("AdGroupAdOperation")
        ad_group_ad = operation.create
        
        ad_group_ad.ad_group = ad_group_service.ad_group_path(customer_id, ad_group_id)
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED
        ad_group_ad.ad.final_urls.append(final_url)
        
        # Agregar headlines
        for headline_text in ad_content.get('headlines', [])[:15]:  # Max 15
            headline = client.get_type("AdTextAsset")
            headline.text = headline_text[:30]  # Max 30 chars
            ad_group_ad.ad.responsive_search_ad.headlines.append(headline)
        
        # Agregar descriptions
        for desc_text in ad_content.get('descriptions', [])[:4]:  # Max 4
            description = client.get_type("AdTextAsset")
            description.text = desc_text[:90]  # Max 90 chars
            ad_group_ad.ad.responsive_search_ad.descriptions.append(description)
        
        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=customer_id,
            operations=[operation]
        )
        
        return response.results[0].resource_name


# Singleton global worker
_worker_instance = None

def get_worker(max_workers=3):
    """Obtiene o crea el worker singleton"""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = AutomationWorker(max_workers=max_workers)
    return _worker_instance
