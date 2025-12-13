"""
PROFIT GUARDIAN - Sistema Autónomo de Rentabilidad para Google Ads
===================================================================

Sistema inteligente que:
1. Distribuye presupuesto uniformemente durante el día
2. Pausa keywords/ads no rentables automáticamente
3. Protege el capital con límites de pérdida
4. Toma decisiones autónomas basadas en rendimiento real
5. Optimiza para PROFIT, no solo conversiones

Autor: GIGA-INGENIEUR
Fecha: Diciembre 2025
"""

from flask import Blueprint, request, jsonify
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf.field_mask_pb2 import FieldMask
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import os
import json
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

# Configurar logger
logger = logging.getLogger(__name__)

profit_guardian_bp = Blueprint('profit_guardian', __name__)

# ============================================
# ESTADO GLOBAL DEL SISTEMA
# ============================================

class GuardianState:
    """Estado global del Profit Guardian"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.enabled = False  # DESACTIVADO por defecto - tu decides cuando activar
            cls._instance.last_check = None
            cls._instance.total_decisions_today = 0
            cls._instance.keywords_paused_today = 0
            cls._instance.keywords_resumed_today = 0
        return cls._instance
    
    def enable(self):
        self.enabled = True
        print("🟢 Profit Guardian ACTIVADO")
        
    def disable(self):
        self.enabled = False
        print("🔴 Profit Guardian DESACTIVADO")
        
    def toggle(self):
        self.enabled = not self.enabled
        status = "ACTIVADO" if self.enabled else "DESACTIVADO"
        print(f"🔄 Profit Guardian {status}")
        return self.enabled
    
    def is_enabled(self):
        return self.enabled
    
    def update_stats(self, decisions=0, paused=0, resumed=0):
        self.total_decisions_today += decisions
        self.keywords_paused_today += paused
        self.keywords_resumed_today += resumed
        self.last_check = datetime.now()

# Instancia global
guardian_state = GuardianState()

# ============================================
# CONFIGURACIÓN DEL NEGOCIO
# ============================================

@dataclass
class BusinessConfig:
    """Configuración del negocio del cliente"""
    # Ingresos
    avg_service_price_cop: int = 825_000  # Promedio entre básico ($650K) y pro ($1M)
    lead_to_sale_rate: float = 0.60       # 60% de leads terminan pagando (3 de 5)
    
    # Objetivos
    target_cpa_cop: int = 45_000          # CPA objetivo (entre 40K-50K)
    max_cpa_cop: int = 60_000             # CPA máximo aceptable antes de pausar
    min_roi_percent: float = 500          # ROI mínimo aceptable (500% = 5x retorno)
    
    # Presupuesto
    daily_budget_cop: int = 300_000       # Presupuesto diario
    
    # Horarios activos
    active_hours_start: int = 7           # 7 AM
    active_hours_end: int = 23            # 11 PM (16 horas activas)
    
    # Horarios premium (mejor rendimiento observado)
    premium_hours: List[int] = None       # Se calcula dinámicamente
    
    # 🎯 Budget Pacing Horario - Manual Override
    custom_hourly_budget_cop: int = None  # Si se define, usa este valor en lugar del automático
    
    # Control
    check_interval_minutes: int = 15      # Revisar cada 15 minutos
    pause_duration_minutes: int = 45      # Pausar por 45 min si excede ritmo
    min_clicks_for_decision: int = 10     # Mínimo de clicks para tomar decisiones
    min_impressions_for_decision: int = 100
    
    def __post_init__(self):
        if self.premium_hours is None:
            # Horarios que mencionaste: 11-12, 15+, noche
            self.premium_hours = [11, 12, 15, 16, 17, 18, 19, 20, 21, 22]
    
    @property
    def hourly_budget_cop(self) -> int:
        """Presupuesto por hora (distribución uniforme o manual)"""
        # Si hay override manual, usarlo
        if self.custom_hourly_budget_cop is not None:
            return self.custom_hourly_budget_cop
        # Sino, calcular automáticamente
        active_hours = self.active_hours_end - self.active_hours_start
        return self.daily_budget_cop // active_hours
    
    @property
    def cost_per_sale_target(self) -> int:
        """Costo real por VENTA (considerando tasa de cierre)"""
        # Si CPA es $45K y 60% convierte, costo real por venta = $75K
        return int(self.target_cpa_cop / self.lead_to_sale_rate)
    
    @property
    def max_cost_per_sale(self) -> int:
        """Costo máximo por venta antes de ser no rentable"""
        return int(self.max_cpa_cop / self.lead_to_sale_rate)
    
    @property
    def profit_per_sale(self) -> int:
        """Profit estimado por venta"""
        return self.avg_service_price_cop - self.cost_per_sale_target


# ============================================
# ENUMS Y TIPOS
# ============================================

class DecisionType(Enum):
    PAUSE_KEYWORD = "PAUSE_KEYWORD"
    RESUME_KEYWORD = "RESUME_KEYWORD"
    PAUSE_AD = "PAUSE_AD"
    RESUME_AD = "RESUME_AD"
    PAUSE_CAMPAIGN = "PAUSE_CAMPAIGN"
    RESUME_CAMPAIGN = "RESUME_CAMPAIGN"
    ADJUST_BID_UP = "ADJUST_BID_UP"
    ADJUST_BID_DOWN = "ADJUST_BID_DOWN"
    REDISTRIBUTE_BUDGET = "REDISTRIBUTE_BUDGET"
    NO_ACTION = "NO_ACTION"


class PerformanceRating(Enum):
    EXCELLENT = "EXCELLENT"    # CPA < 70% del objetivo
    GOOD = "GOOD"              # CPA < objetivo
    ACCEPTABLE = "ACCEPTABLE"  # CPA < máximo
    POOR = "POOR"              # CPA > máximo pero < 150%
    TERRIBLE = "TERRIBLE"      # CPA > 150% del máximo


@dataclass
class KeywordPerformance:
    keyword_id: str
    keyword_text: str
    ad_group_id: str
    campaign_id: str
    customer_id: str
    
    impressions: int
    clicks: int
    conversions: float
    cost_micros: int
    
    # Calculados
    ctr: float = 0.0
    cpa_cop: float = 0.0
    cost_cop: float = 0.0
    rating: PerformanceRating = PerformanceRating.ACCEPTABLE
    
    def calculate_metrics(self, config: BusinessConfig):
        """Calcula métricas derivadas"""
        self.cost_cop = self.cost_micros / 1_000_000
        
        if self.impressions > 0:
            self.ctr = (self.clicks / self.impressions) * 100
        
        if self.conversions > 0:
            self.cpa_cop = self.cost_cop / self.conversions
        else:
            self.cpa_cop = float('inf') if self.cost_cop > 0 else 0
        
        # Determinar rating
        if self.conversions == 0:
            if self.cost_cop > config.max_cpa_cop:
                self.rating = PerformanceRating.TERRIBLE
            elif self.clicks >= config.min_clicks_for_decision:
                self.rating = PerformanceRating.POOR
            else:
                self.rating = PerformanceRating.ACCEPTABLE  # Sin suficientes datos
        else:
            target = config.target_cpa_cop
            max_cpa = config.max_cpa_cop
            
            if self.cpa_cop < target * 0.7:
                self.rating = PerformanceRating.EXCELLENT
            elif self.cpa_cop < target:
                self.rating = PerformanceRating.GOOD
            elif self.cpa_cop < max_cpa:
                self.rating = PerformanceRating.ACCEPTABLE
            elif self.cpa_cop < max_cpa * 1.5:
                self.rating = PerformanceRating.POOR
            else:
                self.rating = PerformanceRating.TERRIBLE


@dataclass
class Decision:
    """Representa una decisión tomada por el sistema"""
    decision_type: DecisionType
    entity_type: str  # keyword, ad, campaign
    entity_id: str
    customer_id: str
    campaign_id: str
    reason: str
    data: Dict
    timestamp: datetime = None
    executed: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


# ============================================
# DATABASE
# ============================================

DB_PATH = os.getenv('PROFIT_GUARDIAN_DB', 'profit_guardian.db')

def init_profit_guardian_db():
    """Inicializa la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Configuración por cuenta
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_config (
            customer_id TEXT PRIMARY KEY,
            config_json TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Campañas monitoreadas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitored_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            campaign_name TEXT,
            status TEXT DEFAULT 'ACTIVE',
            paused_by_guardian INTEGER DEFAULT 0,
            pause_reason TEXT,
            last_check TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(customer_id, campaign_id)
        )
    ''')
    
    # Agregar columna paused_at si no existe (para Budget Pacing reanudación)
    try:
        cursor.execute('ALTER TABLE monitored_campaigns ADD COLUMN paused_at TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Ya existe
    
    # Keywords pausadas por el guardian
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paused_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            ad_group_id TEXT NOT NULL,
            keyword_id TEXT NOT NULL,
            keyword_text TEXT,
            pause_reason TEXT,
            paused_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resume_at TIMESTAMP,
            auto_resume INTEGER DEFAULT 1,
            performance_data TEXT,
            UNIQUE(customer_id, keyword_id)
        )
    ''')
    
    # Historial de decisiones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS decision_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            campaign_id TEXT,
            decision_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            reason TEXT,
            data_json TEXT,
            executed INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Métricas por hora (para análisis de patrones)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hourly_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            date TEXT NOT NULL,
            hour INTEGER NOT NULL,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            conversions REAL DEFAULT 0,
            cost_micros INTEGER DEFAULT 0,
            keywords_paused INTEGER DEFAULT 0,
            keywords_resumed INTEGER DEFAULT 0,
            UNIQUE(customer_id, campaign_id, date, hour)
        )
    ''')
    
    # Performance por keyword (histórico para ML)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keyword_performance_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            keyword_id TEXT NOT NULL,
            keyword_text TEXT,
            date TEXT NOT NULL,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            conversions REAL DEFAULT 0,
            cost_micros INTEGER DEFAULT 0,
            cpa_cop REAL,
            rating TEXT,
            UNIQUE(customer_id, keyword_id, date)
        )
    ''')
    
    # Alertas y notificaciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            data_json TEXT,
            acknowledged INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Profit Guardian database initialized")


def get_db():
    """Obtiene conexión a la base de datos"""
    return sqlite3.connect(DB_PATH)


# ============================================
# GOOGLE ADS CLIENT
# ============================================

def get_google_ads_client(refresh_token: str = None):
    """Crea cliente de Google Ads"""
    config = {
        'developer_token': os.getenv('GOOGLE_ADS_DEVELOPER_TOKEN') or os.getenv('DEVELOPER_TOKEN'),
        'client_id': os.getenv('GOOGLE_ADS_CLIENT_ID') or os.getenv('CLIENT_ID'),
        'client_secret': os.getenv('GOOGLE_ADS_CLIENT_SECRET') or os.getenv('CLIENT_SECRET'),
        'use_proto_plus': True
    }
    
    # Solo agregar login_customer_id si existe y es válido
    login_customer_id = os.getenv('GOOGLE_ADS_LOGIN_CUSTOMER_ID') or os.getenv('LOGIN_CUSTOMER_ID')
    if login_customer_id and len(login_customer_id.replace('-', '')) == 10:
        config['login_customer_id'] = login_customer_id
    
    if refresh_token:
        config['refresh_token'] = refresh_token
    else:
        config['refresh_token'] = os.getenv('GOOGLE_ADS_REFRESH_TOKEN') or os.getenv('REFRESH_TOKEN')
    
    return GoogleAdsClient.load_from_dict(config)


# ============================================
# ANÁLISIS DE PERFORMANCE
# ============================================

def get_campaign_performance_today(client, customer_id: str, campaign_id: str) -> Dict:
    """Obtiene performance de campaña de los últimos 5 días (para considerar conversion lag)"""
    try:
        ga_service = client.get_service("GoogleAdsService")
        today = datetime.now()
        five_days_ago = (today - timedelta(days=5)).strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d')
        
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.cost_micros
            FROM campaign
            WHERE campaign.id = '{campaign_id}'
                AND segments.date BETWEEN '{five_days_ago}' AND '{today_str}'
        """
        
        response = ga_service.search(customer_id=customer_id.replace('-', ''), query=query)
        
        # Agregar métricas de todos los días (Google Ads API devuelve múltiples filas)
        totals = {
            'campaign_id': campaign_id,
            'campaign_name': '',
            'status': '',
            'impressions': 0,
            'clicks': 0,
            'conversions': 0.0,
            'cost_micros': 0,
            'cost_cop': 0.0
        }
        
        for row in response:
            totals['campaign_name'] = row.campaign.name
            totals['status'] = row.campaign.status.name
            totals['impressions'] += row.metrics.impressions
            totals['clicks'] += row.metrics.clicks
            totals['conversions'] += float(row.metrics.conversions)
            totals['cost_micros'] += row.metrics.cost_micros
        
        if totals['impressions'] > 0:
            totals['cost_cop'] = totals['cost_micros'] / 1_000_000
            return totals
        
        return {}
    except Exception as e:
        print(f"❌ Error getting campaign performance: {e}")
        return {}


def get_keywords_performance_today(client, customer_id: str, campaign_id: str, config: BusinessConfig) -> List[KeywordPerformance]:
    """Obtiene performance de keywords de los últimos 5 días (para considerar conversion lag)"""
    try:
        ga_service = client.get_service("GoogleAdsService")
        today = datetime.now()
        five_days_ago = (today - timedelta(days=5)).strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d')
        
        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group.id,
                campaign.id,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.cost_micros
            FROM keyword_view
            WHERE campaign.id = '{campaign_id}'
                AND segments.date BETWEEN '{five_days_ago}' AND '{today_str}'
                AND ad_group_criterion.status = 'ENABLED'
            ORDER BY metrics.cost_micros DESC
        """
        
        response = ga_service.search(customer_id=customer_id.replace('-', ''), query=query)
        
        # Agregar métricas por keyword de todos los días
        keyword_data = {}
        for row in response:
            keyword_id = str(row.ad_group_criterion.criterion_id)
            
            if keyword_id not in keyword_data:
                keyword_data[keyword_id] = {
                    'keyword_text': row.ad_group_criterion.keyword.text,
                    'ad_group_id': str(row.ad_group.id),
                    'campaign_id': str(row.campaign.id),
                    'customer_id': customer_id,
                    'impressions': 0,
                    'clicks': 0,
                    'conversions': 0.0,
                    'cost_micros': 0
                }
            
            keyword_data[keyword_id]['impressions'] += row.metrics.impressions
            keyword_data[keyword_id]['clicks'] += row.metrics.clicks
            keyword_data[keyword_id]['conversions'] += float(row.metrics.conversions)
            keyword_data[keyword_id]['cost_micros'] += row.metrics.cost_micros
        
        # Crear objetos KeywordPerformance con totales
        keywords = []
        for keyword_id, data in keyword_data.items():
            kw = KeywordPerformance(
                keyword_id=keyword_id,
                keyword_text=data['keyword_text'],
                ad_group_id=data['ad_group_id'],
                campaign_id=data['campaign_id'],
                customer_id=data['customer_id'],
                impressions=data['impressions'],
                clicks=data['clicks'],
                conversions=data['conversions'],
                cost_micros=data['cost_micros']
            )
            kw.calculate_metrics(config)
            keywords.append(kw)
        
        # Ordenar por costo descendente
        keywords.sort(key=lambda x: x.cost_micros, reverse=True)
        
        return keywords
    except Exception as e:
        print(f"❌ Error getting keywords performance: {e}")
        return []


def get_hourly_spend_today(client, customer_id: str, campaign_id: str) -> Dict[int, Dict]:
    """Obtiene gasto por hora del día actual"""
    try:
        ga_service = client.get_service("GoogleAdsService")
        today = datetime.now().strftime('%Y-%m-%d')
        
        query = f"""
            SELECT
                segments.hour,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.cost_micros
            FROM campaign
            WHERE campaign.id = '{campaign_id}'
                AND segments.date = '{today}'
        """
        
        response = ga_service.search(customer_id=customer_id.replace('-', ''), query=query)
        
        hourly = {}
        for row in response:
            hour = row.segments.hour
            if hour not in hourly:
                hourly[hour] = {
                    'impressions': 0,
                    'clicks': 0,
                    'conversions': 0,
                    'cost_micros': 0
                }
            hourly[hour]['impressions'] += row.metrics.impressions
            hourly[hour]['clicks'] += row.metrics.clicks
            hourly[hour]['conversions'] += float(row.metrics.conversions)
            hourly[hour]['cost_micros'] += row.metrics.cost_micros
        
        return hourly
    except Exception as e:
        print(f"❌ Error getting hourly spend: {e}")
        return {}


# ============================================
# MOTOR DE DECISIONES
# ============================================

class DecisionEngine:
    """Motor de decisiones autónomas"""
    
    def __init__(self, config: BusinessConfig):
        self.config = config
        self.decisions: List[Decision] = []
    
    def analyze_budget_pace(self, hourly_spend: Dict[int, Dict], total_spend_cop: float) -> List[Decision]:
        """Analiza si el ritmo de gasto es sostenible"""
        decisions = []
        current_hour = datetime.now().hour
        
        # Horas transcurridas desde inicio
        hours_active = current_hour - self.config.active_hours_start
        if hours_active <= 0:
            return decisions
        
        # Horas restantes
        hours_remaining = self.config.active_hours_end - current_hour
        
        # Presupuesto restante
        budget_remaining = self.config.daily_budget_cop - total_spend_cop
        
        # Ritmo actual vs ideal
        ideal_spend_so_far = self.config.hourly_budget_cop * hours_active
        spend_ratio = total_spend_cop / ideal_spend_so_far if ideal_spend_so_far > 0 else 0
        
        print(f"   📊 Budget Analysis:")
        print(f"      Spent: ${total_spend_cop:,.0f} COP ({total_spend_cop/self.config.daily_budget_cop*100:.1f}%)")
        print(f"      Ideal: ${ideal_spend_so_far:,.0f} COP")
        print(f"      Pace: {spend_ratio:.2f}x (1.0 = on track)")
        print(f"      Remaining: ${budget_remaining:,.0f} COP for {hours_remaining}h")
        
        # ❌ DESHABILITADO: No pausar campañas completas
        # Las keywords malas afectan stats de keywords buenas
        # Mejor estrategia: pausar SOLO keywords problemáticas
        """
        if spend_ratio > 1.5:
            # Gastando 50% más rápido de lo ideal
            decisions.append(Decision(
                decision_type=DecisionType.PAUSE_CAMPAIGN,
                entity_type="campaign",
                entity_id="",  # Se llena después
                customer_id="",
                campaign_id="",
                reason=f"Ritmo de gasto muy alto ({spend_ratio:.1f}x). Pausar para distribuir mejor.",
                data={
                    'spend_ratio': spend_ratio,
                    'total_spend': total_spend_cop,
                    'budget_remaining': budget_remaining,
                    'pause_minutes': self.config.pause_duration_minutes
                }
            ))
        """
        
        if budget_remaining < self.config.hourly_budget_cop and hours_remaining > 2:
            # Casi sin presupuesto pero quedan muchas horas
            decisions.append(Decision(
                decision_type=DecisionType.REDISTRIBUTE_BUDGET,
                entity_type="campaign",
                entity_id="",
                customer_id="",
                campaign_id="",
                reason=f"Presupuesto bajo (${budget_remaining:,.0f}) para {hours_remaining}h restantes",
                data={
                    'budget_remaining': budget_remaining,
                    'hours_remaining': hours_remaining,
                    'recommended_hourly': budget_remaining / hours_remaining
                }
            ))
        
        return decisions
    
    def analyze_hourly_budget_pacing(self, hourly_spend: Dict[int, Dict]) -> List[Decision]:
        """🚀 BUDGET PACING HORARIO - Pausa campaña si excede cuota horaria"""
        decisions = []
        current_hour = datetime.now().hour
        
        # Verificar que estamos en horario activo
        if current_hour < self.config.active_hours_start or current_hour >= self.config.active_hours_end:
            return decisions
        
        # Obtener gasto en la HORA ACTUAL
        current_hour_spend_micros = hourly_spend.get(current_hour, {}).get('cost_micros', 0)
        current_hour_spend_cop = current_hour_spend_micros / 1_000_000
        
        # Cuota permitida por hora
        hourly_budget = self.config.hourly_budget_cop
        
        print(f"   ⏰ Budget Pacing (Hora {current_hour}h):")
        print(f"      Gastado esta hora: ${current_hour_spend_cop:,.0f} COP")
        print(f"      Cuota horaria: ${hourly_budget:,.0f} COP")
        print(f"      Progreso: {(current_hour_spend_cop/hourly_budget*100):.1f}%")
        
        # Si ya gastó >= 95% de la cuota horaria, PAUSAR hasta próxima hora
        if current_hour_spend_cop >= (hourly_budget * 0.95):
            decisions.append(Decision(
                decision_type=DecisionType.PAUSE_CAMPAIGN,
                entity_type="campaign",
                entity_id="",
                customer_id="",
                campaign_id="",
                reason=f"⏰ Cuota horaria alcanzada: ${current_hour_spend_cop:,.0f}/${hourly_budget:,.0f} COP. Pausando hasta {current_hour+1}:00h",
                data={
                    'pause_type': 'hourly_budget_pacing',
                    'current_hour_spend': current_hour_spend_cop,
                    'hourly_budget': hourly_budget,
                    'resume_at_hour': current_hour + 1,
                    'auto_resume': True
                }
            ))
            print(f"      🛑 DECISIÓN: Pausar campaña (cuota horaria alcanzada)")
        elif current_hour_spend_cop >= (hourly_budget * 0.80):
            print(f"      ⚠️ ALERTA: 80% de cuota horaria consumida")
        else:
            print(f"      ✅ Gasto horario dentro del límite")
        
        return decisions
    
    def analyze_keywords(self, keywords: List[KeywordPerformance]) -> List[Decision]:
        """Analiza keywords y decide cuáles pausar/mantener"""
        decisions = []
        
        for kw in keywords:
            # Solo tomar decisiones con suficientes datos
            if kw.clicks < self.config.min_clicks_for_decision:
                continue
            
            if kw.rating == PerformanceRating.TERRIBLE:
                decisions.append(Decision(
                    decision_type=DecisionType.PAUSE_KEYWORD,
                    entity_type="keyword",
                    entity_id=kw.keyword_id,
                    customer_id=kw.customer_id,
                    campaign_id=kw.campaign_id,
                    reason=f"CPA terrible (${kw.cpa_cop:,.0f} > ${self.config.max_cpa_cop * 1.5:,.0f})",
                    data={
                        'keyword_text': kw.keyword_text,
                        'ad_group_id': kw.ad_group_id,
                        'clicks': kw.clicks,
                        'conversions': kw.conversions,
                        'cost_cop': kw.cost_cop,
                        'cpa_cop': kw.cpa_cop,
                        'rating': kw.rating.value,
                        'auto_resume': False  # No reanudar automáticamente
                    }
                ))
            
            elif kw.rating == PerformanceRating.POOR:
                # Gasta mucho sin convertir, pausar temporalmente
                if kw.cost_cop > self.config.target_cpa_cop and kw.conversions == 0:
                    decisions.append(Decision(
                        decision_type=DecisionType.PAUSE_KEYWORD,
                        entity_type="keyword",
                        entity_id=kw.keyword_id,
                        customer_id=kw.customer_id,
                        campaign_id=kw.campaign_id,
                        reason=f"${kw.cost_cop:,.0f} gastados sin conversiones",
                        data={
                            'keyword_text': kw.keyword_text,
                            'ad_group_id': kw.ad_group_id,
                            'clicks': kw.clicks,
                            'conversions': kw.conversions,
                            'cost_cop': kw.cost_cop,
                            'rating': kw.rating.value,
                            'auto_resume': True,
                            'resume_after_hours': 3  # Reanudar después de 3 horas
                        }
                    ))
            
            elif kw.rating == PerformanceRating.EXCELLENT:
                # Keyword excelente, considerar aumentar bid
                decisions.append(Decision(
                    decision_type=DecisionType.ADJUST_BID_UP,
                    entity_type="keyword",
                    entity_id=kw.keyword_id,
                    customer_id=kw.customer_id,
                    campaign_id=kw.campaign_id,
                    reason=f"CPA excelente (${kw.cpa_cop:,.0f} < ${self.config.target_cpa_cop * 0.7:,.0f})",
                    data={
                        'keyword_text': kw.keyword_text,
                        'ad_group_id': kw.ad_group_id,
                        'cpa_cop': kw.cpa_cop,
                        'conversions': kw.conversions,
                        'suggested_bid_increase': 0.15  # +15%
                    }
                ))
        
        return decisions
    
    def analyze_zero_conversion_spend(self, keywords: List[KeywordPerformance]) -> List[Decision]:
        """Identifica keywords que gastan sin convertir"""
        decisions = []
        
        # Keywords con gasto significativo pero 0 conversiones
        wasteful = [kw for kw in keywords 
                    if kw.conversions == 0 
                    and kw.cost_cop >= self.config.target_cpa_cop * 0.8]
        
        total_wasted = sum(kw.cost_cop for kw in wasteful)
        
        if total_wasted > self.config.hourly_budget_cop:
            # Más de 1 hora de presupuesto desperdiciado
            for kw in wasteful[:5]:  # Top 5 más costosas
                decisions.append(Decision(
                    decision_type=DecisionType.PAUSE_KEYWORD,
                    entity_type="keyword",
                    entity_id=kw.keyword_id,
                    customer_id=kw.customer_id,
                    campaign_id=kw.campaign_id,
                    reason=f"Gasto sin conversión: ${kw.cost_cop:,.0f} ({kw.clicks} clicks)",
                    data={
                        'keyword_text': kw.keyword_text,
                        'ad_group_id': kw.ad_group_id,
                        'clicks': kw.clicks,
                        'cost_cop': kw.cost_cop,
                        'auto_resume': True,
                        'resume_after_hours': 2
                    }
                ))
        
        return decisions


# ============================================
# EJECUTOR DE DECISIONES
# ============================================

class DecisionExecutor:
    """Ejecuta las decisiones tomadas"""
    
    def __init__(self, client):
        self.client = client
    
    def execute(self, decision: Decision) -> bool:
        """Ejecuta una decisión"""
        try:
            if decision.decision_type == DecisionType.PAUSE_KEYWORD:
                return self._pause_keyword(decision)
            elif decision.decision_type == DecisionType.RESUME_KEYWORD:
                return self._resume_keyword(decision)
            elif decision.decision_type == DecisionType.PAUSE_CAMPAIGN:
                return self._pause_campaign(decision)
            elif decision.decision_type == DecisionType.RESUME_CAMPAIGN:
                return self._resume_campaign(decision)
            elif decision.decision_type == DecisionType.ADJUST_BID_UP:
                return self._adjust_bid_up(decision)
            elif decision.decision_type == DecisionType.ADJUST_BID_DOWN:
                return self._adjust_bid_down(decision)
            else:
                print(f"   ℹ️ Tipo de decisión {decision.decision_type.value} registrado pero no ejecutado")
                return True
        except Exception as e:
            print(f"   ❌ Error ejecutando decisión: {e}")
            return False
    
    def _pause_keyword(self, decision: Decision) -> bool:
        """Pausa un keyword"""
        try:
            customer_id = decision.customer_id.replace('-', '')
            ad_group_id = decision.data.get('ad_group_id')
            criterion_id = decision.entity_id
            
            agc_service = self.client.get_service("AdGroupCriterionService")
            
            resource_name = agc_service.ad_group_criterion_path(
                customer_id, ad_group_id, criterion_id
            )
            
            operation = self.client.get_type("AdGroupCriterionOperation")
            operation.update.resource_name = resource_name
            operation.update.status = self.client.enums.AdGroupCriterionStatusEnum.PAUSED
            operation.update_mask.CopyFrom(FieldMask(paths=["status"]))
            
            agc_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[operation]
            )
            
            # Guardar en DB
            conn = get_db()
            cursor = conn.cursor()
            
            resume_at = None
            if decision.data.get('auto_resume'):
                hours = decision.data.get('resume_after_hours', 2)
                resume_at = datetime.utcnow() + timedelta(hours=hours)
            
            cursor.execute('''
                INSERT OR REPLACE INTO paused_keywords
                (customer_id, campaign_id, ad_group_id, keyword_id, keyword_text, 
                 pause_reason, resume_at, auto_resume, performance_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                decision.customer_id,
                decision.campaign_id,
                ad_group_id,
                criterion_id,
                decision.data.get('keyword_text', ''),
                decision.reason,
                resume_at,
                1 if decision.data.get('auto_resume') else 0,
                json.dumps(decision.data)
            ))
            conn.commit()
            conn.close()
            
            print(f"   ⏸️ Keyword pausada: {decision.data.get('keyword_text', criterion_id)}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error pausando keyword: {e}")
            return False
    
    def _resume_keyword(self, decision: Decision) -> bool:
        """Reanuda un keyword"""
        try:
            customer_id = decision.customer_id.replace('-', '')
            ad_group_id = decision.data.get('ad_group_id')
            criterion_id = decision.entity_id
            
            agc_service = self.client.get_service("AdGroupCriterionService")
            
            resource_name = agc_service.ad_group_criterion_path(
                customer_id, ad_group_id, criterion_id
            )
            
            operation = self.client.get_type("AdGroupCriterionOperation")
            operation.update.resource_name = resource_name
            operation.update.status = self.client.enums.AdGroupCriterionStatusEnum.ENABLED
            operation.update_mask.CopyFrom(FieldMask(paths=["status"]))
            
            agc_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[operation]
            )
            
            # Remover de DB
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM paused_keywords WHERE customer_id = ? AND keyword_id = ?',
                (decision.customer_id, criterion_id)
            )
            conn.commit()
            conn.close()
            
            print(f"   ▶️ Keyword reactivada: {decision.data.get('keyword_text', criterion_id)}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error reactivando keyword: {e}")
            return False
    
    def _pause_campaign(self, decision: Decision) -> bool:
        """Pausa una campaña temporalmente"""
        try:
            customer_id = decision.customer_id.replace('-', '')
            campaign_id = decision.campaign_id
            
            campaign_service = self.client.get_service("CampaignService")
            
            resource_name = campaign_service.campaign_path(customer_id, campaign_id)
            
            operation = self.client.get_type("CampaignOperation")
            operation.update.resource_name = resource_name
            operation.update.status = self.client.enums.CampaignStatusEnum.PAUSED
            operation.update_mask.CopyFrom(FieldMask(paths=["status"]))
            
            campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[operation]
            )
            
            # Actualizar DB
            conn = get_db()
            cursor = conn.cursor()
            paused_at = datetime.now().isoformat()  # Timestamp de pausa
            cursor.execute('''
                UPDATE monitored_campaigns
                SET status = 'PAUSED_BY_GUARDIAN', 
                    paused_by_guardian = 1,
                    pause_reason = ?,
                    paused_at = ?,
                    last_check = ?
                WHERE customer_id = ? AND campaign_id = ?
            ''', (decision.reason, paused_at, datetime.utcnow(), decision.customer_id, campaign_id))
            conn.commit()
            conn.close()
            
            print(f"   ⏸️ Campaña pausada: {campaign_id} (hora {datetime.now().hour}h)")
            return True
            
        except Exception as e:
            print(f"   ❌ Error pausando campaña: {e}")
            return False
    
    def _resume_campaign(self, decision: Decision) -> bool:
        """Reanuda una campaña"""
        try:
            customer_id = decision.customer_id.replace('-', '')
            campaign_id = decision.campaign_id
            
            campaign_service = self.client.get_service("CampaignService")
            
            resource_name = campaign_service.campaign_path(customer_id, campaign_id)
            
            operation = self.client.get_type("CampaignOperation")
            operation.update.resource_name = resource_name
            operation.update.status = self.client.enums.CampaignStatusEnum.ENABLED
            operation.update_mask.CopyFrom(FieldMask(paths=["status"]))
            
            campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[operation]
            )
            
            # Actualizar DB
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE monitored_campaigns
                SET status = 'ACTIVE', 
                    paused_by_guardian = 0,
                    pause_reason = NULL,
                    paused_at = NULL,
                    last_check = ?
                WHERE customer_id = ? AND campaign_id = ?
            ''', (datetime.utcnow(), decision.customer_id, campaign_id))
            conn.commit()
            conn.close()
            
            print(f"   ▶️ Resumed campaign: {campaign_id}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error resuming campaign: {e}")
            return False
    
    def _adjust_bid_up(self, decision: Decision) -> bool:
        """Aumenta la puja de una keyword que está convirtiendo bien"""
        try:
            customer_id = decision.customer_id.replace('-', '')
            criterion_id = decision.entity_id
            ad_group_id = decision.data.get('ad_group_id')
            
            if not ad_group_id:
                print(f"   ⚠️ No se puede ajustar bid: falta ad_group_id")
                return False
            
            agc_service = self.client.get_service("AdGroupCriterionService")
            
            # Obtener bid actual
            resource_name = agc_service.ad_group_criterion_path(
                customer_id, ad_group_id, criterion_id
            )
            
            # Obtener criterio actual
            ga_service = self.client.get_service("GoogleAdsService")
            query = f"""
                SELECT 
                    ad_group_criterion.cpc_bid_micros,
                    ad_group_criterion.keyword.text
                FROM ad_group_criterion
                WHERE ad_group_criterion.criterion_id = {criterion_id}
                  AND ad_group.id = {ad_group_id}
            """
            
            response = ga_service.search(customer_id=customer_id, query=query)
            
            current_bid_micros = 0
            keyword_text = decision.data.get('keyword_text', criterion_id)
            
            for row in response:
                current_bid_micros = row.ad_group_criterion.cpc_bid_micros
                keyword_text = row.ad_group_criterion.keyword.text
                break
            
            if current_bid_micros == 0:
                print(f"   ⚠️ No se puede ajustar bid: bid actual es 0")
                return False
            
            # Aumentar bid según sugerencia
            bid_increase = decision.data.get('suggested_bid_increase', 0.15)  # Default 15%
            new_bid_micros = int(current_bid_micros * (1 + bid_increase))
            
            # Límite de seguridad: máximo 50% de aumento
            max_bid_micros = int(current_bid_micros * 1.5)
            new_bid_micros = min(new_bid_micros, max_bid_micros)
            
            # Actualizar bid
            operation = self.client.get_type("AdGroupCriterionOperation")
            operation.update.resource_name = resource_name
            operation.update.cpc_bid_micros = new_bid_micros
            operation.update_mask.CopyFrom(FieldMask(paths=["cpc_bid_micros"]))
            
            agc_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[operation]
            )
            
            old_bid_cop = current_bid_micros / 1_000_000
            new_bid_cop = new_bid_micros / 1_000_000
            
            print(f"   📈 Bid aumentado para '{keyword_text}': ${old_bid_cop:,.0f} → ${new_bid_cop:,.0f} COP (+{bid_increase*100:.0f}%)")
            return True
            
        except Exception as e:
            print(f"   ❌ Error ajustando bid: {e}")
            return False
    
    def _adjust_bid_down(self, decision: Decision) -> bool:
        """Reduce la puja de una keyword con CPA alto"""
        try:
            customer_id = decision.customer_id.replace('-', '')
            criterion_id = decision.entity_id
            ad_group_id = decision.data.get('ad_group_id')
            
            if not ad_group_id:
                print(f"   ⚠️ No se puede ajustar bid: falta ad_group_id")
                return False
            
            agc_service = self.client.get_service("AdGroupCriterionService")
            
            # Obtener bid actual
            resource_name = agc_service.ad_group_criterion_path(
                customer_id, ad_group_id, criterion_id
            )
            
            # Obtener criterio actual
            ga_service = self.client.get_service("GoogleAdsService")
            query = f"""
                SELECT 
                    ad_group_criterion.cpc_bid_micros,
                    ad_group_criterion.keyword.text
                FROM ad_group_criterion
                WHERE ad_group_criterion.criterion_id = {criterion_id}
                  AND ad_group.id = {ad_group_id}
            """
            
            response = ga_service.search(customer_id=customer_id, query=query)
            
            current_bid_micros = 0
            keyword_text = decision.data.get('keyword_text', criterion_id)
            
            for row in response:
                current_bid_micros = row.ad_group_criterion.cpc_bid_micros
                keyword_text = row.ad_group_criterion.keyword.text
                break
            
            if current_bid_micros == 0:
                print(f"   ⚠️ No se puede ajustar bid: bid actual es 0")
                return False
            
            # Reducir bid según sugerencia
            bid_decrease = decision.data.get('suggested_bid_decrease', 0.20)  # Default 20%
            new_bid_micros = int(current_bid_micros * (1 - bid_decrease))
            
            # Límite de seguridad: mínimo $100 COP
            min_bid_micros = 100_000_000  # $100 COP en micros
            new_bid_micros = max(new_bid_micros, min_bid_micros)
            
            # Actualizar bid
            operation = self.client.get_type("AdGroupCriterionOperation")
            operation.update.resource_name = resource_name
            operation.update.cpc_bid_micros = new_bid_micros
            operation.update_mask.CopyFrom(FieldMask(paths=["cpc_bid_micros"]))
            
            agc_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=[operation]
            )
            
            old_bid_cop = current_bid_micros / 1_000_000
            new_bid_cop = new_bid_micros / 1_000_000
            
            print(f"   📉 Bid reducido para '{keyword_text}': ${old_bid_cop:,.0f} → ${new_bid_cop:,.0f} COP (-{bid_decrease*100:.0f}%)")
            return True
            
        except Exception as e:
            print(f"   ❌ Error ajustando bid: {e}")
            return False


# ============================================
# MONITOR PRINCIPAL
# ============================================

def check_campaigns_to_resume():
    """Verifica si hay keywords/campañas que deben reanudarse"""
    conn = get_db()
    cursor = conn.cursor()
    
    now = datetime.utcnow()
    
    # Keywords para reanudar
    cursor.execute('''
        SELECT customer_id, campaign_id, ad_group_id, keyword_id, keyword_text
        FROM paused_keywords
        WHERE auto_resume = 1 AND resume_at <= ?
    ''', (now,))
    
    keywords_to_resume = cursor.fetchall()
    
    if keywords_to_resume:
        print(f"   🔄 Resuming {len(keywords_to_resume)} keywords...")
        
        client = get_google_ads_client()
        executor = DecisionExecutor(client)
        
        for customer_id, campaign_id, ad_group_id, keyword_id, keyword_text in keywords_to_resume:
            decision = Decision(
                decision_type=DecisionType.RESUME_KEYWORD,
                entity_type="keyword",
                entity_id=keyword_id,
                customer_id=customer_id,
                campaign_id=campaign_id,
                reason="Auto-resume after cooldown",
                data={'ad_group_id': ad_group_id, 'keyword_text': keyword_text}
            )
            executor.execute(decision)
    
    conn.close()


def resume_campaigns_for_new_hour():
    """🔄 Reactiva campañas pausadas por budget pacing al inicio de cada hora"""
    current_hour = datetime.now().hour
    conn = get_db()
    cursor = conn.cursor()
    
    # Buscar campañas pausadas por budget pacing cuyo resume_at_hour ya pasó
    cursor.execute('''
        SELECT customer_id, campaign_id, campaign_name, pause_reason, paused_at
        FROM monitored_campaigns
        WHERE status = 'PAUSED_BY_GUARDIAN' 
          AND paused_by_guardian = 1
          AND pause_reason LIKE '%Cuota horaria%'
    ''')
    
    campaigns_to_resume = cursor.fetchall()
    
    if not campaigns_to_resume:
        conn.close()
        return
    
    print(f"   🔄 Verificando campañas pausadas por budget pacing...")
    
    client = get_google_ads_client()
    executor = DecisionExecutor(client)
    resumed_count = 0
    
    for customer_id, campaign_id, campaign_name, pause_reason, paused_at in campaigns_to_resume:
        # Extraer hora de pausa (formato ISO: 2025-12-12T10:30:45)
        try:
            paused_datetime = datetime.fromisoformat(paused_at)
            paused_hour = paused_datetime.hour
            
            # Solo reactivar si estamos en una NUEVA hora diferente
            if current_hour != paused_hour:
                decision = Decision(
                    decision_type=DecisionType.RESUME_CAMPAIGN,
                    entity_type="campaign",
                    entity_id="",
                    customer_id=customer_id,
                    campaign_id=campaign_id,
                    reason=f"Nueva hora iniciada: {current_hour}:00h - Cuota horaria renovada (pausada a las {paused_hour}:00h)",
                    data={'campaign_name': campaign_name, 'paused_hour': paused_hour}
                )
                success = executor.execute(decision)
                if success:
                    resumed_count += 1
                    print(f"      ✅ {campaign_name or campaign_id} reactivada (pausada hora {paused_hour}h → activa hora {current_hour}h)")
            else:
                # Misma hora - no reactivar aún
                print(f"      ⏸️ {campaign_name or campaign_id} sigue pausada (misma hora {current_hour}h)")
        except Exception as e:
            print(f"      ⚠️ Error procesando {campaign_id}: {e}")
    
    if resumed_count > 0:
        print(f"   🎉 {resumed_count} campañas reactivadas para nueva hora ({current_hour}:00h)")
    
    conn.close()


def run_profit_guardian_check():
    """Ejecuta el ciclo principal del Profit Guardian"""
    
    logger.info("🔵 run_profit_guardian_check() INICIADO")
    
    # ⚡ VERIFICAR SI ESTÁ ACTIVADO
    is_enabled = guardian_state.is_enabled()
    logger.info(f"🔍 Estado del Guardian: {'ACTIVADO' if is_enabled else 'DESACTIVADO'}")
    
    if not is_enabled:
        logger.warning("⏸️ Profit Guardian está DESACTIVADO - Saltando check")
        print(f"⏸️ Profit Guardian está DESACTIVADO - Saltando check")
        return
    
    logger.info("✅ Guardian ACTIVADO - Continuando análisis...")
    print(f"\n{'='*60}")
    print(f"🛡️ PROFIT GUARDIAN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   📅 Analizando últimos 5 días (para considerar conversion lag)")
    print(f"{'='*60}")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener campañas monitoreadas activas
    cursor.execute('''
        SELECT mc.customer_id, mc.campaign_id, mc.campaign_name, ac.config_json
        FROM monitored_campaigns mc
        JOIN account_config ac ON mc.customer_id = ac.customer_id
        WHERE mc.status IN ('ACTIVE', 'ENABLED')
          AND ac.enabled = 1
    ''')
    
    campaigns = cursor.fetchall()
    conn.close()
    
    logger.info(f"📊 Campañas encontradas en DB: {len(campaigns)}")
    
    if not campaigns:
        logger.warning("⚠️ No campaigns configured for monitoring")
        print("   ℹ️ No campaigns configured for monitoring")
        return
    
    logger.info(f"✅ Monitoring {len(campaigns)} campaigns...")
    print(f"   📊 Monitoring {len(campaigns)} campaigns...")
    
    client = get_google_ads_client()
    executor = DecisionExecutor(client)
    
    for customer_id, campaign_id, campaign_name, config_json in campaigns:
        print(f"\n   📍 Campaign: {campaign_name or campaign_id}")
        
        # Cargar configuración
        try:
            config_dict = json.loads(config_json) if config_json else {}
            config = BusinessConfig(**config_dict)
        except:
            config = BusinessConfig()
        
        # Obtener performance
        campaign_perf = get_campaign_performance_today(client, customer_id, campaign_id)
        if not campaign_perf:
            print(f"      ⚠️ No data available")
            continue
        
        total_spend = campaign_perf.get('cost_cop', 0)
        total_conv = campaign_perf.get('conversions', 0)
        
        print(f"      💰 Spend: ${total_spend:,.0f} COP | Conv: {total_conv}")
        
        # Obtener performance por keyword
        keywords = get_keywords_performance_today(client, customer_id, campaign_id, config)
        
        # Obtener gasto por hora
        hourly_spend = get_hourly_spend_today(client, customer_id, campaign_id)
        
        # Motor de decisiones
        engine = DecisionEngine(config)
        
        # Análisis 0: 🚀 BUDGET PACING HORARIO (prioridad máxima)
        hourly_pacing_decisions = engine.analyze_hourly_budget_pacing(hourly_spend)
        
        # Análisis 1: Ritmo de presupuesto (deshabilitado - usamos hourly pacing)
        # budget_decisions = engine.analyze_budget_pace(hourly_spend, total_spend)
        
        # Análisis 2: Keywords individuales
        keyword_decisions = engine.analyze_keywords(keywords)
        
        # Análisis 3: Gasto sin conversión
        waste_decisions = engine.analyze_zero_conversion_spend(keywords)
        
        # Combinar decisiones (hourly pacing tiene prioridad)
        all_decisions = hourly_pacing_decisions + keyword_decisions + waste_decisions
        
        if not all_decisions:
            print(f"      ✅ Todas las métricas dentro del rango aceptable")
            continue
        
        print(f"      🎯 {len(all_decisions)} decisiones a ejecutar:")
        
        # Ejecutar decisiones
        for decision in all_decisions:
            decision.customer_id = customer_id
            decision.campaign_id = campaign_id
            
            # Log decision
            log_decision(decision)
            
            # Execute
            success = executor.execute(decision)
            decision.executed = success
        
        # Resumen
        executed = sum(1 for d in all_decisions if d.executed)
        print(f"      📋 Ejecutado: {executed}/{len(all_decisions)}")
    
    # 🔄 Reactivar campañas para nueva hora (Budget Pacing)
    resume_campaigns_for_new_hour()
    
    # Verificar keywords para reanudar
    check_campaigns_to_resume()
    
    print(f"\n{'='*60}")
    print(f"✅ Profit Guardian check completado")
    print(f"{'='*60}\n")


def log_decision(decision: Decision):
    """Guarda decisión en historial"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO decision_history
        (customer_id, campaign_id, decision_type, entity_type, entity_id, reason, data_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        decision.customer_id,
        decision.campaign_id,
        decision.decision_type.value,
        decision.entity_type,
        decision.entity_id,
        decision.reason,
        json.dumps(decision.data)
    ))
    
    conn.commit()
    conn.close()


# ============================================
# API ENDPOINTS
# ============================================

@profit_guardian_bp.route('/api/profit-guardian/config', methods=['POST'])
def configure_account():
    """Configura una cuenta para monitoreo"""
    data = request.get_json()
    customer_id = data.get('customer_id')
    
    if not customer_id:
        return jsonify({'success': False, 'error': 'customer_id required'}), 400
    
    # Construir configuración
    config = {
        'avg_service_price_cop': data.get('avg_service_price_cop', 825000),
        'lead_to_sale_rate': data.get('lead_to_sale_rate', 0.60),
        'target_cpa_cop': data.get('target_cpa_cop', 45000),
        'max_cpa_cop': data.get('max_cpa_cop', 60000),
        'daily_budget_cop': data.get('daily_budget_cop', 300000),
        'active_hours_start': data.get('active_hours_start', 7),
        'active_hours_end': data.get('active_hours_end', 23),
        'check_interval_minutes': data.get('check_interval_minutes', 15),
        'pause_duration_minutes': data.get('pause_duration_minutes', 45),
        'min_clicks_for_decision': data.get('min_clicks_for_decision', 10)
    }
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO account_config
        (customer_id, config_json, enabled, updated_at)
        VALUES (?, ?, 1, ?)
    ''', (customer_id, json.dumps(config), datetime.utcnow()))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Account configured for Profit Guardian',
        'config': config
    })


@profit_guardian_bp.route('/api/profit-guardian/campaigns', methods=['POST'])
def add_campaign_monitoring():
    """Agrega campaña al monitoreo"""
    data = request.get_json()
    customer_id = data.get('customer_id')
    campaign_id = data.get('campaign_id')
    campaign_name = data.get('campaign_name', '')
    
    if not customer_id or not campaign_id:
        return jsonify({'success': False, 'error': 'customer_id and campaign_id required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO monitored_campaigns
        (customer_id, campaign_id, campaign_name, status, last_check)
        VALUES (?, ?, ?, 'ACTIVE', ?)
    ''', (customer_id, campaign_id, campaign_name, datetime.utcnow()))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': f'Campaign {campaign_name or campaign_id} added to monitoring'
    })


@profit_guardian_bp.route('/api/profit-guardian/add-all-campaigns', methods=['POST'])
def add_all_campaigns():
    """Agrega TODAS las campañas activas de una cuenta al monitoreo"""
    data = request.get_json()
    customer_id = data.get('customer_id')
    
    if not customer_id:
        return jsonify({'success': False, 'error': 'customer_id required'}), 400
    
    try:
        # Obtener cliente de Google Ads usando variables de entorno
        client = get_google_ads_client()
        ga_service = client.get_service("GoogleAdsService")
        
        # Query para obtener todas las campañas activas
        query = """
            SELECT 
                campaign.id,
                campaign.name,
                campaign.status
            FROM campaign
            WHERE campaign.status = 'ENABLED'
        """
        
        response = ga_service.search(customer_id=customer_id, query=query)
        
        conn = get_db()
        cursor = conn.cursor()
        added_count = 0
        
        # Agregar cada campaña encontrada
        for row in response:
            campaign = row.campaign
            cursor.execute('''
                INSERT OR REPLACE INTO monitored_campaigns
                (customer_id, campaign_id, campaign_name, status, last_check)
                VALUES (?, ?, ?, 'ACTIVE', ?)
            ''', (customer_id, str(campaign.id), campaign.name, datetime.utcnow()))
            added_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'campaigns_added': added_count,
            'message': f'Se agregaron {added_count} campañas al monitoreo'
        })
        
    except GoogleAdsException as ex:
        return jsonify({
            'success': False,
            'error': f'Google Ads API error: {ex.failure.errors[0].message}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@profit_guardian_bp.route('/api/profit-guardian/status', methods=['GET'])
def get_status():
    """Obtiene estado actual del sistema"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Estadísticas
    cursor.execute('SELECT COUNT(*) FROM account_config WHERE enabled = 1')
    accounts = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM monitored_campaigns WHERE status = "ACTIVE"')
    campaigns = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM paused_keywords')
    paused_keywords = cursor.fetchone()[0]
    
    # Decisiones hoy
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT COUNT(*), decision_type 
        FROM decision_history 
        WHERE DATE(timestamp) = ?
        GROUP BY decision_type
    ''', (today,))
    decisions_today = {row[1]: row[0] for row in cursor.fetchall()}
    
    conn.close()
    
    return jsonify({
        'success': True,
        'status': 'active',
        'accounts_monitored': accounts,
        'campaigns_monitored': campaigns,
        'keywords_paused_by_guardian': paused_keywords,
        'decisions_today': decisions_today
    })


@profit_guardian_bp.route('/api/profit-guardian/decisions', methods=['GET'])
def get_decisions():
    """Obtiene historial de decisiones"""
    customer_id = request.args.get('customer_id')
    limit = int(request.args.get('limit', 50))
    
    conn = get_db()
    cursor = conn.cursor()
    
    if customer_id:
        cursor.execute('''
            SELECT * FROM decision_history
            WHERE customer_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (customer_id, limit))
    else:
        cursor.execute('''
            SELECT * FROM decision_history
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
    
    columns = ['id', 'customer_id', 'campaign_id', 'decision_type', 
               'entity_type', 'entity_id', 'reason', 'data_json', 
               'executed', 'timestamp']
    
    decisions = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'success': True,
        'decisions': decisions
    })


@profit_guardian_bp.route('/api/profit-guardian/paused-keywords', methods=['GET'])
def get_paused_keywords():
    """Obtiene keywords pausadas por el guardian"""
    customer_id = request.args.get('customer_id')
    
    conn = get_db()
    cursor = conn.cursor()
    
    if customer_id:
        cursor.execute('''
            SELECT * FROM paused_keywords
            WHERE customer_id = ?
            ORDER BY paused_at DESC
        ''', (customer_id,))
    else:
        cursor.execute('SELECT * FROM paused_keywords ORDER BY paused_at DESC')
    
    columns = ['id', 'customer_id', 'campaign_id', 'ad_group_id', 
               'keyword_id', 'keyword_text', 'pause_reason', 
               'paused_at', 'resume_at', 'auto_resume', 'performance_data']
    
    keywords = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'success': True,
        'paused_keywords': keywords
    })


@profit_guardian_bp.route('/api/profit-guardian/run-now', methods=['POST'])
def run_now():
    """Ejecuta un check manualmente"""
    try:
        # Temporalmente habilitar para ejecución manual
        was_enabled = guardian_state.is_enabled()
        if not was_enabled:
            guardian_state.enable()
        
        run_profit_guardian_check()
        
        # Restaurar estado original
        if not was_enabled:
            guardian_state.disable()
            
        return jsonify({'success': True, 'message': 'Check completed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# 🔘 TOGGLE ENDPOINTS - ACTIVAR/DESACTIVAR
# ============================================

@profit_guardian_bp.route('/api/profit-guardian/enable', methods=['POST'])
def enable_guardian():
    """Activa el Profit Guardian"""
    guardian_state.enable()
    return jsonify({
        'success': True,
        'enabled': True,
        'message': '🟢 Profit Guardian ACTIVADO - Monitoreando cada 15 minutos'
    })


@profit_guardian_bp.route('/api/profit-guardian/disable', methods=['POST'])
def disable_guardian():
    """Desactiva el Profit Guardian"""
    guardian_state.disable()
    return jsonify({
        'success': True,
        'enabled': False,
        'message': '🔴 Profit Guardian DESACTIVADO - Sin monitoreo automático'
    })


@profit_guardian_bp.route('/api/profit-guardian/toggle', methods=['POST'])
def toggle_guardian():
    """Alterna el estado del Profit Guardian"""
    new_state = guardian_state.toggle()
    return jsonify({
        'success': True,
        'enabled': new_state,
        'message': f'{"🟢 ACTIVADO" if new_state else "🔴 DESACTIVADO"}'
    })


@profit_guardian_bp.route('/api/profit-guardian/state', methods=['GET'])
def get_guardian_state():
    """Obtiene el estado actual del Profit Guardian"""
    return jsonify({
        'success': True,
        'enabled': guardian_state.is_enabled(),
        'last_check': guardian_state.last_check.isoformat() if guardian_state.last_check else None,
        'stats_today': {
            'total_decisions': guardian_state.total_decisions_today,
            'keywords_paused': guardian_state.keywords_paused_today,
            'keywords_resumed': guardian_state.keywords_resumed_today
        }
    })


@profit_guardian_bp.route('/api/profit-guardian/activity', methods=['GET'])
def get_activity_log():
    """Obtiene el historial de actividad reciente del Profit Guardian"""
    customer_id = request.args.get('customer_id')
    limit = int(request.args.get('limit', 50))
    hours = int(request.args.get('hours', 24))  # Últimas 24 horas por defecto
    
    if not customer_id:
        return jsonify({
            'success': False,
            'error': 'customer_id requerido'
        }), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Obtener decisiones recientes
        since = datetime.now() - timedelta(hours=hours)
        cursor.execute('''
            SELECT 
                decision_type,
                entity_type,
                entity_id,
                reason,
                data_json,
                timestamp
            FROM decision_history
            WHERE customer_id = ?
            AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (customer_id, since.isoformat(), limit))
        
        decisions = []
        for row in cursor.fetchall():
            data = json.loads(row[4]) if row[4] else {}
            decisions.append({
                'type': row[0],
                'entity_type': row[1],
                'entity_id': row[2],
                'reason': row[3] or 'Sin razón especificada',
                'metrics_before': data.get('metrics_before'),
                'metrics_after': data.get('metrics_after'),
                'timestamp': row[5]
            })
        
        # Obtener stats del día
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cursor.execute('''
            SELECT decision_type, COUNT(*)
            FROM decision_history
            WHERE customer_id = ?
            AND timestamp >= ?
            GROUP BY decision_type
        ''', (customer_id, today_start.isoformat()))
        
        stats_today = {}
        for row in cursor.fetchall():
            stats_today[row[0]] = row[1]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'activity': decisions,
            'stats_today': stats_today,
            'total_decisions_today': sum(stats_today.values()),
            'hours': hours
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@profit_guardian_bp.route('/api/profit-guardian/budget-pacing', methods=['GET'])
def get_budget_pacing_status():
    """Obtiene el estado actual del budget pacing horario"""
    customer_id = request.args.get('customer_id')
    campaign_id = request.args.get('campaign_id')
    
    if not customer_id:
        return jsonify({
            'success': False,
            'error': 'customer_id requerido'
        }), 400
    
    try:
        client = get_google_ads_client()
        
        # Cargar configuración
        config = load_guardian_config(customer_id)
        if not config:
            return jsonify({
                'success': False,
                'error': 'No hay configuración para esta cuenta'
            }), 404
        
        # Obtener gasto por hora de hoy
        hourly_spend = get_hourly_spend_today(client, customer_id, campaign_id)
        
        # Hora actual
        current_hour = datetime.now().hour
        current_hour_spend_micros = hourly_spend.get(current_hour, {}).get('cost_micros', 0)
        current_hour_spend_cop = current_hour_spend_micros / 1_000_000
        
        # Presupuesto por hora
        hourly_budget = config.hourly_budget_cop
        
        # Calcular totales del día
        total_spend_today = sum(h.get('cost_micros', 0) for h in hourly_spend.values()) / 1_000_000
        hours_active = max(1, current_hour - config.active_hours_start + 1)
        ideal_spend_so_far = hourly_budget * hours_active
        
        # Detectar si está pausado por cuota horaria
        is_paused_by_pacing = current_hour_spend_cop >= (hourly_budget * 0.95)
        
        return jsonify({
            'success': True,
            'current_hour': current_hour,
            'hourly_budget_cop': hourly_budget,
            'current_hour_spend_cop': current_hour_spend_cop,
            'current_hour_percentage': (current_hour_spend_cop / hourly_budget * 100) if hourly_budget > 0 else 0,
            'is_paused_by_pacing': is_paused_by_pacing,
            'resume_at_hour': current_hour + 1 if is_paused_by_pacing else None,
            'daily_budget_cop': config.daily_budget_cop,
            'total_spend_today_cop': total_spend_today,
            'daily_budget_percentage': (total_spend_today / config.daily_budget_cop * 100) if config.daily_budget_cop > 0 else 0,
            'ideal_spend_so_far': ideal_spend_so_far,
            'spend_vs_ideal': total_spend_today - ideal_spend_so_far,
            'active_hours_start': config.active_hours_start,
            'active_hours_end': config.active_hours_end,
            'hourly_breakdown': {
                str(hour): {
                    'spend_cop': data.get('cost_micros', 0) / 1_000_000,
                    'conversions': data.get('conversions', 0),
                    'clicks': data.get('clicks', 0)
                }
                for hour, data in hourly_spend.items()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@profit_guardian_bp.route('/api/profit-guardian/update-hourly-budget', methods=['POST'])
def update_hourly_budget():
    """🎯 Actualiza la cuota horaria máxima (override manual)"""
    data = request.get_json()
    customer_id = data.get('customer_id')
    custom_hourly_budget = data.get('custom_hourly_budget_cop')
    
    if not customer_id:
        return jsonify({
            'success': False,
            'error': 'customer_id requerido'
        }), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Cargar configuración actual
        cursor.execute('SELECT config_json FROM account_config WHERE customer_id = ?', (customer_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({
                'success': False,
                'error': 'No existe configuración para esta cuenta'
            }), 404
        
        config_dict = json.loads(row[0])
        
        # Actualizar custom_hourly_budget_cop
        if custom_hourly_budget is None or custom_hourly_budget == 0:
            # Eliminar override - volver a automático
            config_dict.pop('custom_hourly_budget_cop', None)
            message = 'Cuota horaria restaurada a cálculo automático'
        else:
            config_dict['custom_hourly_budget_cop'] = int(custom_hourly_budget)
            message = f'Cuota horaria actualizada a ${custom_hourly_budget:,.0f} COP/hora'
        
        # Guardar
        cursor.execute('''
            UPDATE account_config 
            SET config_json = ?, updated_at = ?
            WHERE customer_id = ?
        ''', (json.dumps(config_dict), datetime.utcnow(), customer_id))
        conn.commit()
        conn.close()
        
        # Calcular valores para respuesta
        config = BusinessConfig(**config_dict)
        active_hours = config.active_hours_end - config.active_hours_start
        automatic_hourly = config.daily_budget_cop // active_hours
        
        return jsonify({
            'success': True,
            'message': message,
            'custom_hourly_budget_cop': config.custom_hourly_budget_cop,
            'automatic_hourly_budget_cop': automatic_hourly,
            'daily_budget_cop': config.daily_budget_cop,
            'active_hours': active_hours,
            'is_manual_override': config.custom_hourly_budget_cop is not None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# 💰 PRESUPUESTO COMPARTIDO
# ============================================

@profit_guardian_bp.route('/api/profit-guardian/create-shared-budget', methods=['POST'])
def create_shared_budget():
    """Crea un presupuesto compartido maestro para una cuenta"""
    data = request.get_json()
    customer_id = data.get('customer_id')
    budget_name = data.get('budget_name', 'Presupuesto Guardian Master')
    daily_amount_cop = data.get('daily_amount_cop')
    
    if not customer_id or not daily_amount_cop:
        return jsonify({
            'success': False,
            'error': 'customer_id y daily_amount_cop requeridos'
        }), 400
    
    try:
        client = get_google_ads_client()
        campaign_budget_service = client.get_service("CampaignBudgetService")
        
        # Crear operación
        campaign_budget_operation = client.get_type("CampaignBudgetOperation")
        campaign_budget = campaign_budget_operation.create
        
        campaign_budget.name = budget_name
        campaign_budget.amount_micros = int(daily_amount_cop * 1_000_000)
        campaign_budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        campaign_budget.explicitly_shared = True  # ✅ Presupuesto compartido
        
        # Ejecutar
        response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=customer_id.replace('-', ''),
            operations=[campaign_budget_operation]
        )
        
        budget_resource_name = response.results[0].resource_name
        
        return jsonify({
            'success': True,
            'budget_resource_name': budget_resource_name,
            'budget_name': budget_name,
            'daily_amount_cop': daily_amount_cop,
            'message': f'✅ Presupuesto compartido creado: ${daily_amount_cop:,.0f} COP/día'
        })
        
    except GoogleAdsException as ex:
        return jsonify({
            'success': False,
            'error': f'Google Ads API error: {ex.failure.errors[0].message}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@profit_guardian_bp.route('/api/profit-guardian/assign-shared-budget', methods=['POST'])
def assign_shared_budget():
    """Asigna un presupuesto compartido a TODAS las campañas activas"""
    data = request.get_json()
    customer_id = data.get('customer_id')
    budget_resource_name = data.get('budget_resource_name')
    
    if not customer_id or not budget_resource_name:
        return jsonify({
            'success': False,
            'error': 'customer_id y budget_resource_name requeridos'
        }), 400
    
    try:
        client = get_google_ads_client()
        ga_service = client.get_service("GoogleAdsService")
        campaign_service = client.get_service("CampaignService")
        
        # Obtener campañas ACTIVAS con estrategia de puja y tipo de canal
        query = """
            SELECT 
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.bidding_strategy_type,
                campaign.bidding_strategy,
                campaign.experiment_type,
                campaign.advertising_channel_type
            FROM campaign
            WHERE campaign.status = 'ENABLED'
        """
        
        response = ga_service.search(customer_id=customer_id.replace('-', ''), query=query)
        
        print(f"\n🔍 Analizando campañas para asignación de presupuesto compartido:")
        
        operations = []
        campaign_names = []
        skipped_campaigns = []
        
        # Crear operación solo para campañas compatibles
        for row in response:
            campaign_id = str(row.campaign.id)
            campaign_name = row.campaign.name
            bidding_strategy_type = row.campaign.bidding_strategy_type.name
            channel_type = row.campaign.advertising_channel_type.name
            
            # Detectar portfolio strategy
            is_portfolio = bool(row.campaign.bidding_strategy)
            
            # Detectar experimentos
            experiment_type = row.campaign.experiment_type.name
            has_experiment = experiment_type != 'BASE'
            
            # Detectar Performance Max (no soporta shared budgets)
            is_performance_max = channel_type == 'PERFORMANCE_MAX'
            
            print(f"  - {campaign_name}: {bidding_strategy_type}, Canal={channel_type}, Portfolio={is_portfolio}, Experiment={experiment_type}")
            
            if is_performance_max:
                skipped_campaigns.append({
                    'name': campaign_name,
                    'strategy': bidding_strategy_type,
                    'reason': 'Performance Max no soporta presupuestos compartidos'
                })
            elif has_experiment:
                skipped_campaigns.append({
                    'name': campaign_name,
                    'strategy': bidding_strategy_type,
                    'reason': 'Tiene experimentos de campaña activos'
                })
            elif is_portfolio:
                skipped_campaigns.append({
                    'name': campaign_name,
                    'strategy': bidding_strategy_type,
                    'reason': 'Portfolio Strategy (compartida en biblioteca)'
                })
            else:
                # Guardar solo los datos, crear operación después
                operations.append({
                    'name': campaign_name,
                    'id': campaign_id
                })
        
        if not operations:
            pmax_count = sum(1 for c in skipped_campaigns if 'Performance Max' in c.get('reason', ''))
            portfolio_count = sum(1 for c in skipped_campaigns if 'Portfolio' in c.get('reason', ''))
            return jsonify({
                'success': False,
                'error': f'No se encontraron campañas compatibles. {len(skipped_campaigns)} campañas omitidas ({pmax_count} Performance Max, {portfolio_count} Portfolio)',
                'skipped_campaigns': skipped_campaigns
            }), 404
        
        # Ejecutar operaciones UNA POR UNA para que si una falla, las demás continúen
        successful_campaigns = []
        
        print(f"\n🚀 Asignando presupuesto compartido a {len(operations)} campañas...")
        for op_data in operations:
            try:
                # Crear la operación
                campaign_operation = client.get_type("CampaignOperation")
                campaign_resource_name = campaign_service.campaign_path(
                    customer_id.replace('-', ''),
                    op_data['id']
                )
                
                campaign_operation.update.resource_name = campaign_resource_name
                campaign_operation.update.campaign_budget = budget_resource_name
                campaign_operation.update_mask.CopyFrom(FieldMask(paths=["campaign_budget"]))
                
                # Ejecutar
                campaign_service.mutate_campaigns(
                    customer_id=customer_id.replace('-', ''),
                    operations=[campaign_operation]
                )
                successful_campaigns.append(op_data['name'])
                print(f"  ✅ {op_data['name']}")
            except GoogleAdsException as gex:
                error_msg = gex.failure.errors[0].message if gex.failure.errors else str(gex)
                print(f"  ❌ {op_data['name']}: {error_msg}")
                skipped_campaigns.append({
                    'name': op_data['name'],
                    'strategy': 'Unknown',
                    'reason': f'Error al asignar: {error_msg}'
                })
            except Exception as ex:
                print(f"  ❌ {op_data['name']}: {str(ex)}")
                skipped_campaigns.append({
                    'name': op_data['name'],
                    'strategy': 'Unknown',
                    'reason': f'Error: {str(ex)}'
                })
        
        message = f'✅ {len(successful_campaigns)} campañas asignadas al presupuesto compartido'
        if skipped_campaigns:
            message += f' | ⚠️ {len(skipped_campaigns)} campañas omitidas'
        
        return jsonify({
            'success': True,
            'campaigns_updated': len(successful_campaigns),
            'campaigns_skipped': len(skipped_campaigns),
            'campaign_names': successful_campaigns,
            'skipped_campaigns': skipped_campaigns,
            'message': message
        })
        
    except GoogleAdsException as ex:
        return jsonify({
            'success': False,
            'error': f'Google Ads API error: {ex.failure.errors[0].message}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@profit_guardian_bp.route('/api/profit-guardian/setup-shared-budget', methods=['POST'])
def setup_shared_budget():
    """🚀 TODO EN UNO: Crea presupuesto compartido Y lo asigna a todas las campañas"""
    data = request.get_json()
    customer_id = data.get('customer_id')
    # Generar nombre único con timestamp para evitar duplicados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    budget_name = data.get('budget_name', f'Guardian Master {timestamp}')
    daily_amount_cop = data.get('daily_amount_cop')
    
    if not customer_id or not daily_amount_cop:
        return jsonify({
            'success': False,
            'error': 'customer_id y daily_amount_cop requeridos'
        }), 400
    
    try:
        # PASO 1: Crear presupuesto compartido
        client = get_google_ads_client()
        campaign_budget_service = client.get_service("CampaignBudgetService")
        
        campaign_budget_operation = client.get_type("CampaignBudgetOperation")
        campaign_budget = campaign_budget_operation.create
        
        campaign_budget.name = budget_name
        campaign_budget.amount_micros = int(daily_amount_cop * 1_000_000)
        campaign_budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        campaign_budget.explicitly_shared = True
        
        response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=customer_id.replace('-', ''),
            operations=[campaign_budget_operation]
        )
        
        budget_resource_name = response.results[0].resource_name
        
        # PASO 2: Asignar a campañas compatibles (excluir portfolio strategies)
        ga_service = client.get_service("GoogleAdsService")
        campaign_service = client.get_service("CampaignService")
        
        query = """
            SELECT 
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.bidding_strategy_type,
                campaign.bidding_strategy,
                campaign.experiment_type,
                campaign.advertising_channel_type
            FROM campaign
            WHERE campaign.status = 'ENABLED'
        """
        
        search_response = ga_service.search(customer_id=customer_id.replace('-', ''), query=query)
        
        operations = []
        campaign_names = []
        skipped_campaigns = []
        
        print(f"🔍 Analizando campañas para customer {customer_id}...")
        
        for row in search_response:
            campaign_id = str(row.campaign.id)
            campaign_name = row.campaign.name
            bidding_strategy_type = row.campaign.bidding_strategy_type.name
            channel_type = row.campaign.advertising_channel_type.name
            
            # Detectar si es portfolio strategy (tiene resource_name en bidding_strategy)
            is_portfolio = bool(row.campaign.bidding_strategy)
            
            # Detectar si tiene experimentos (BASE = sin experimento, DRAFT/EXPERIMENT = con experimento)
            experiment_type = row.campaign.experiment_type.name
            has_experiment = experiment_type != 'BASE'
            
            # Detectar Performance Max (no soporta shared budgets)
            is_performance_max = channel_type == 'PERFORMANCE_MAX'
            
            print(f"  - {campaign_name}: {bidding_strategy_type}, Canal={channel_type}, Portfolio={is_portfolio}, Experiment={experiment_type}")
            
            # Excluir Performance Max, portfolio strategies y experimentos
            if is_performance_max:
                skipped_campaigns.append({
                    'name': campaign_name,
                    'strategy': bidding_strategy_type,
                    'reason': 'Performance Max no soporta presupuestos compartidos'
                })
            elif has_experiment:
                skipped_campaigns.append({
                    'name': campaign_name,
                    'strategy': bidding_strategy_type,
                    'reason': 'Tiene experimentos de campaña activos'
                })
            elif is_portfolio:
                skipped_campaigns.append({
                    'name': campaign_name,
                    'strategy': bidding_strategy_type,
                    'reason': 'Portfolio Strategy (compartida en biblioteca)'
                })
            else:
                # Compatible: guardar solo los datos
                operations.append({
                    'name': campaign_name,
                    'id': campaign_id
                })
        
        print(f"✅ {len(operations)} compatibles, ⚠️ {len(skipped_campaigns)} omitidas")
        
        # Ejecutar operaciones UNA POR UNA para que si una falla, las demás continúen
        successful_campaigns = []
        
        if operations:
            print(f"\n🚀 Asignando presupuesto compartido a {len(operations)} campañas...")
            for op_data in operations:
                campaign_operation = client.get_type("CampaignOperation")
                campaign_resource_name = campaign_service.campaign_path(
                    customer_id.replace('-', ''),
                    op_data['id']
                )
                
                campaign_operation.update.resource_name = campaign_resource_name
                campaign_operation.update.campaign_budget = budget_resource_name
                campaign_operation.update_mask.CopyFrom(FieldMask(paths=["campaign_budget"]))
                
                try:
                    campaign_service.mutate_campaigns(
                        customer_id=customer_id.replace('-', ''),
                        operations=[campaign_operation]
                    )
                    successful_campaigns.append(op_data['name'])
                    print(f"  ✅ {op_data['name']}")
                except GoogleAdsException as gex:
                    error_msg = gex.failure.errors[0].message if gex.failure.errors else str(gex)
                    print(f"  ❌ {op_data['name']}: {error_msg}")
                    skipped_campaigns.append({
                        'name': op_data['name'],
                        'strategy': 'Unknown',
                        'reason': f'Error al asignar: {error_msg}'
                    })
                except Exception as ex:
                    print(f"  ❌ {op_data['name']}: {str(ex)}")
                    skipped_campaigns.append({
                        'name': op_data['name'],
                        'strategy': 'Unknown',
                        'reason': f'Error: {str(ex)}'
                    })
        
        message = f'✅ Presupuesto compartido creado (${daily_amount_cop:,.0f}/día) y asignado a {len(successful_campaigns)} campañas'
        if skipped_campaigns:
            message += f' | ⚠️ {len(skipped_campaigns)} campañas omitidas'
        
        return jsonify({
            'success': True,
            'budget_resource_name': budget_resource_name,
            'budget_name': budget_name,
            'daily_amount_cop': daily_amount_cop,
            'campaigns_updated': len(successful_campaigns),
            'campaigns_skipped': len(skipped_campaigns),
            'campaign_names': successful_campaigns,
            'skipped_campaigns': skipped_campaigns,
            'message': message
        })
        
    except GoogleAdsException as ex:
        return jsonify({
            'success': False,
            'error': f'Google Ads API error: {ex.failure.errors[0].message}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# SCHEDULER
# ============================================

guardian_scheduler = BackgroundScheduler()

def start_profit_guardian():
    """
    Inicia el scheduler del Profit Guardian.
    ⚠️ IMPORTANTE: El sistema inicia DESACTIVADO por defecto.
    Debes llamar a /api/profit-guardian/enable para activarlo.
    """
    init_profit_guardian_db()
    
    # 🔧 MODO DEBUG: Ejecutar cada 1 minuto (temporal para testing)
    # TODO: Cambiar a 15 minutos en producción
    guardian_scheduler.add_job(
        func=run_profit_guardian_check,
        trigger=IntervalTrigger(minutes=1),
        id='profit_guardian_monitor',
        name='Profit Guardian - Monitor campaigns',
        replace_existing=True
    )
    
    guardian_scheduler.start()
    
    print("=" * 60)
    print("🛡️ PROFIT GUARDIAN - SCHEDULER INICIADO")
    print("🔧 MODO DEBUG: Intervalo de 1 minuto (cambiar a 15 en prod)")
    print("=" * 60)
    print("   ⚠️  Estado: DESACTIVADO (esperando tu orden)")
    print("   ")
    print("   Para ACTIVAR el sistema autónomo:")
    print("   POST /api/profit-guardian/enable")
    print("   ")
    print("   Para ejecutar análisis MANUAL sin activar:")
    print("   POST /api/profit-guardian/run-now")
    print("=" * 60)


def stop_profit_guardian():
    """Detiene el Profit Guardian"""
    guardian_scheduler.shutdown()
    guardian_state.disable()
    print("⏹️ Profit Guardian stopped")
