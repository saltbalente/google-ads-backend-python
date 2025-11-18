"""
Circuit Breaker System - Sistema de Protección de Presupuesto
Monitorea campañas cada 30 minutos y pausa automáticamente si detecta gasto anormal
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
from typing import Dict, List, Optional

circuit_breaker_bp = Blueprint('circuit_breaker', __name__)

# Configuración
DB_PATH = os.getenv('CIRCUIT_BREAKER_DB', 'circuit_breaker.db')
NOTIFICATION_WEBHOOK = os.getenv('NOTIFICATION_WEBHOOK', '')  # Para Slack/Discord/Telegram

# Exchange rate COP to USD (aproximado, se puede obtener de API)
COP_TO_USD = 4000  # 1 USD = 4000 COP (actualizar según necesidad)

# ============================================
# DATABASE SETUP
# ============================================

def init_database():
    """Inicializa la base de datos de circuit breaker"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabla de configuración de límites por cuenta
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_limits (
            customer_id TEXT PRIMARY KEY,
            max_spend_per_hour_cop INTEGER DEFAULT 300000,
            max_spend_per_day_cop INTEGER DEFAULT 2000000,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de campañas monitoreadas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitored_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            campaign_name TEXT,
            status TEXT DEFAULT 'ACTIVE',
            last_check TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(customer_id, campaign_id)
        )
    ''')
    
    # Tabla de eventos (pausas, reactivaciones)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS circuit_breaker_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            reason TEXT,
            spend_amount_cop REAL,
            threshold_cop REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notified INTEGER DEFAULT 0
        )
    ''')
    
    # Tabla de gasto histórico (para cálculos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spend_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            hour_timestamp TIMESTAMP NOT NULL,
            spend_usd REAL NOT NULL,
            spend_cop REAL NOT NULL,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            conversions REAL DEFAULT 0,
            UNIQUE(customer_id, campaign_id, hour_timestamp)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Circuit Breaker database initialized")


# ============================================
# GOOGLE ADS CLIENT
# ============================================

def get_google_ads_client():
    """Crea cliente de Google Ads con credenciales del ambiente"""
    return GoogleAdsClient.load_from_dict({
        'developer_token': os.getenv('GOOGLE_ADS_DEVELOPER_TOKEN'),
        'client_id': os.getenv('GOOGLE_ADS_CLIENT_ID'),
        'client_secret': os.getenv('GOOGLE_ADS_CLIENT_SECRET'),
        'refresh_token': os.getenv('GOOGLE_ADS_REFRESH_TOKEN'),
        'login_customer_id': os.getenv('GOOGLE_ADS_LOGIN_CUSTOMER_ID'),
        'use_proto_plus': True
    })


# ============================================
# MONITORING LOGIC
# ============================================

def get_campaign_spend_last_hour(client, customer_id: str, campaign_id: str) -> Dict:
    """Obtiene el gasto de una campaña en la última hora"""
    try:
        ga_service = client.get_service("GoogleAdsService")
        
        # Fecha actual y hace 1 hora
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        
        # Query para obtener gasto de la última hora
        query = f"""
            SELECT
              campaign.id,
              campaign.name,
              campaign.status,
              metrics.cost_micros,
              metrics.impressions,
              metrics.clicks,
              metrics.conversions
            FROM campaign
            WHERE campaign.id = '{campaign_id}'
              AND segments.date = '{now.strftime("%Y-%m-%d")}'
              AND segments.hour = {one_hour_ago.hour}
        """
        
        response = ga_service.search(customer_id=customer_id.replace('-', ''), query=query)
        
        total_spend_usd = 0
        campaign_data = {}
        
        for row in response:
            total_spend_usd += row.metrics.cost_micros / 1_000_000
            campaign_data = {
                'campaign_id': str(row.campaign.id),
                'campaign_name': row.campaign.name,
                'status': row.campaign.status.name,
                'spend_usd': total_spend_usd,
                'spend_cop': total_spend_usd * COP_TO_USD,
                'impressions': int(row.metrics.impressions),
                'clicks': int(row.metrics.clicks),
                'conversions': float(row.metrics.conversions)
            }
        
        return campaign_data
        
    except Exception as e:
        print(f"❌ Error getting spend for campaign {campaign_id}: {e}")
        return {}


def pause_campaign(client, customer_id: str, campaign_id: str) -> bool:
    """Pausa una campaña"""
    try:
        campaign_service = client.get_service("CampaignService")
        
        resource_name = campaign_service.campaign_path(
            customer_id.replace('-', ''),
            campaign_id
        )
        
        campaign_operation = client.get_type("CampaignOperation")
        campaign = campaign_operation.update
        campaign.resource_name = resource_name
        campaign.status = client.enums.CampaignStatusEnum.PAUSED
        
        campaign_operation.update_mask.CopyFrom(
            FieldMask(paths=["status"])
        )
        
        response = campaign_service.mutate_campaigns(
            customer_id=customer_id.replace('-', ''),
            operations=[campaign_operation]
        )
        
        print(f"✅ Campaign {campaign_id} paused successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error pausing campaign {campaign_id}: {e}")
        return False


def resume_campaign(client, customer_id: str, campaign_id: str) -> bool:
    """Reanuda una campaña pausada"""
    try:
        campaign_service = client.get_service("CampaignService")
        
        resource_name = campaign_service.campaign_path(
            customer_id.replace('-', ''),
            campaign_id
        )
        
        campaign_operation = client.get_type("CampaignOperation")
        campaign = campaign_operation.update
        campaign.resource_name = resource_name
        campaign.status = client.enums.CampaignStatusEnum.ENABLED
        
        campaign_operation.update_mask.CopyFrom(
            FieldMask(paths=["status"])
        )
        
        response = campaign_service.mutate_campaigns(
            customer_id=customer_id.replace('-', ''),
            operations=[campaign_operation]
        )
        
        print(f"✅ Campaign {campaign_id} resumed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error resuming campaign {campaign_id}: {e}")
        return False


def send_notification(title: str, message: str, data: Dict = None):
    """Envía notificación (Slack, Discord, Telegram, etc.)"""
    if not NOTIFICATION_WEBHOOK:
        print(f"📢 Notification: {title} - {message}")
        return
    
    # Implementar según el servicio de notificaciones
    # Ejemplo para Slack:
    import requests
    
    payload = {
        "text": f"*{title}*\n{message}",
        "attachments": [{"text": json.dumps(data, indent=2)}] if data else []
    }
    
    try:
        requests.post(NOTIFICATION_WEBHOOK, json=payload)
    except Exception as e:
        print(f"❌ Error sending notification: {e}")


def check_campaign(customer_id: str, campaign_id: str):
    """Verifica una campaña específica"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Obtener límite configurado
    cursor.execute(
        "SELECT max_spend_per_hour_cop, enabled FROM account_limits WHERE customer_id = ?",
        (customer_id,)
    )
    result = cursor.fetchone()
    
    if not result or result[1] == 0:
        # Sin límite configurado o deshabilitado
        return
    
    max_spend_cop = result[0]
    
    # Obtener datos de la campaña
    client = get_google_ads_client()
    campaign_data = get_campaign_spend_last_hour(client, customer_id, campaign_id)
    
    if not campaign_data:
        return
    
    spend_cop = campaign_data['spend_cop']
    
    # Verificar si excede el límite
    if spend_cop > max_spend_cop:
        print(f"🚨 CIRCUIT BREAKER TRIGGERED: {campaign_data['campaign_name']}")
        print(f"   Spend: ${spend_cop:,.0f} COP > Limit: ${max_spend_cop:,.0f} COP")
        
        # Pausar campaña
        if pause_campaign(client, customer_id, campaign_id):
            # Registrar evento
            cursor.execute('''
                INSERT INTO circuit_breaker_events 
                (customer_id, campaign_id, event_type, reason, spend_amount_cop, threshold_cop)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                customer_id,
                campaign_id,
                'PAUSED',
                f'Gasto excedió límite en última hora',
                spend_cop,
                max_spend_cop
            ))
            
            # Actualizar estado de campaña monitoreada
            cursor.execute('''
                UPDATE monitored_campaigns 
                SET status = 'PAUSED_BY_CB', last_check = ?
                WHERE customer_id = ? AND campaign_id = ?
            ''', (datetime.utcnow(), customer_id, campaign_id))
            
            conn.commit()
            
            # Enviar notificación
            send_notification(
                "⚠️ Circuit Breaker Activado",
                f"Campaña '{campaign_data['campaign_name']}' pausada automáticamente",
                {
                    'customer_id': customer_id,
                    'campaign_id': campaign_id,
                    'spend_cop': f"${spend_cop:,.0f} COP",
                    'limit_cop': f"${max_spend_cop:,.0f} COP",
                    'will_resume_at': (datetime.utcnow() + timedelta(hours=1)).strftime("%H:%M")
                }
            )
    
    # Guardar historial
    cursor.execute('''
        INSERT OR REPLACE INTO spend_history
        (customer_id, campaign_id, hour_timestamp, spend_usd, spend_cop, impressions, clicks, conversions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        customer_id,
        campaign_id,
        datetime.utcnow().replace(minute=0, second=0, microsecond=0),
        campaign_data['spend_usd'],
        spend_cop,
        campaign_data['impressions'],
        campaign_data['clicks'],
        campaign_data['conversions']
    ))
    
    conn.commit()
    conn.close()


def check_paused_campaigns():
    """Verifica campañas pausadas y las reanuda después de 1 hora"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Buscar eventos de pausa hace más de 1 hora
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    cursor.execute('''
        SELECT DISTINCT customer_id, campaign_id
        FROM circuit_breaker_events
        WHERE event_type = 'PAUSED'
          AND timestamp < ?
          AND NOT EXISTS (
              SELECT 1 FROM circuit_breaker_events AS e2
              WHERE e2.customer_id = circuit_breaker_events.customer_id
                AND e2.campaign_id = circuit_breaker_events.campaign_id
                AND e2.event_type = 'RESUMED'
                AND e2.timestamp > circuit_breaker_events.timestamp
          )
    ''', (one_hour_ago,))
    
    campaigns_to_resume = cursor.fetchall()
    
    client = get_google_ads_client()
    
    for customer_id, campaign_id in campaigns_to_resume:
        print(f"🔄 Resuming campaign {campaign_id} after cooldown period")
        
        if resume_campaign(client, customer_id, campaign_id):
            # Registrar evento
            cursor.execute('''
                INSERT INTO circuit_breaker_events
                (customer_id, campaign_id, event_type, reason)
                VALUES (?, ?, ?, ?)
            ''', (customer_id, campaign_id, 'RESUMED', 'Auto-resume after 1 hour cooldown'))
            
            # Actualizar estado
            cursor.execute('''
                UPDATE monitored_campaigns
                SET status = 'ACTIVE', last_check = ?
                WHERE customer_id = ? AND campaign_id = ?
            ''', (datetime.utcnow(), customer_id, campaign_id))
            
            conn.commit()
            
            send_notification(
                "✅ Campaña Reanudada",
                f"Campaña ID {campaign_id} reanudada automáticamente después del período de enfriamiento",
                {'customer_id': customer_id, 'campaign_id': campaign_id}
            )
    
    conn.close()


def monitor_all_campaigns():
    """Función principal que monitorea todas las campañas"""
    print(f"🔍 [{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] Circuit Breaker check running...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Obtener todas las campañas monitoreadas activas
    cursor.execute('''
        SELECT customer_id, campaign_id
        FROM monitored_campaigns
        WHERE status IN ('ACTIVE', 'ENABLED')
    ''')
    
    campaigns = cursor.fetchall()
    conn.close()
    
    print(f"   Monitoring {len(campaigns)} campaigns...")
    
    for customer_id, campaign_id in campaigns:
        try:
            check_campaign(customer_id, campaign_id)
        except Exception as e:
            print(f"❌ Error checking campaign {campaign_id}: {e}")
    
    # Verificar campañas pausadas para reanudar
    check_paused_campaigns()
    
    print("✅ Circuit Breaker check completed")


# ============================================
# API ENDPOINTS
# ============================================

@circuit_breaker_bp.route('/api/circuit-breaker/accounts', methods=['POST'])
def add_account():
    """Agregar cuenta al monitoreo"""
    data = request.get_json()
    customer_id = data.get('customer_id')
    max_spend_per_hour_cop = data.get('max_spend_per_hour_cop', 300000)
    max_spend_per_day_cop = data.get('max_spend_per_day_cop', 2000000)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO account_limits
        (customer_id, max_spend_per_hour_cop, max_spend_per_day_cop, updated_at)
        VALUES (?, ?, ?, ?)
    ''', (customer_id, max_spend_per_hour_cop, max_spend_per_day_cop, datetime.utcnow()))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Account added to circuit breaker monitoring'})


@circuit_breaker_bp.route('/api/circuit-breaker/campaigns', methods=['POST'])
def add_campaign():
    """Agregar campaña al monitoreo"""
    data = request.get_json()
    customer_id = data.get('customer_id')
    campaign_id = data.get('campaign_id')
    campaign_name = data.get('campaign_name', '')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO monitored_campaigns
        (customer_id, campaign_id, campaign_name)
        VALUES (?, ?, ?)
    ''', (customer_id, campaign_id, campaign_name))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Campaign added to monitoring'})


@circuit_breaker_bp.route('/api/circuit-breaker/status', methods=['GET'])
def get_status():
    """Obtener estado del circuit breaker"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Cuentas monitoreadas
    cursor.execute('SELECT COUNT(*) FROM account_limits WHERE enabled = 1')
    accounts_count = cursor.fetchone()[0]
    
    # Campañas monitoreadas
    cursor.execute('SELECT COUNT(*) FROM monitored_campaigns')
    campaigns_count = cursor.fetchone()[0]
    
    # Eventos recientes (últimas 24 horas)
    yesterday = datetime.utcnow() - timedelta(days=1)
    cursor.execute('SELECT COUNT(*) FROM circuit_breaker_events WHERE timestamp > ?', (yesterday,))
    recent_events = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'success': True,
        'accounts_monitored': accounts_count,
        'campaigns_monitored': campaigns_count,
        'events_last_24h': recent_events,
        'status': 'active'
    })


# ============================================
# SCHEDULER SETUP
# ============================================

scheduler = BackgroundScheduler()

def start_circuit_breaker_scheduler():
    """Inicia el scheduler de circuit breaker"""
    init_database()
    
    # Ejecutar cada 30 minutos
    scheduler.add_job(
        func=monitor_all_campaigns,
        trigger=IntervalTrigger(minutes=30),
        id='circuit_breaker_monitor',
        name='Monitor campaigns for circuit breaker',
        replace_existing=True
    )
    
    scheduler.start()
    print("✅ Circuit Breaker Scheduler started (every 30 minutes)")
    
    # Ejecutar una vez al inicio
    monitor_all_campaigns()


def stop_circuit_breaker_scheduler():
    """Detiene el scheduler"""
    scheduler.shutdown()
    print("⏹️ Circuit Breaker Scheduler stopped")

# ==========================================
# ENDPOINTS DE ACTIVACIÓN/DESACTIVACIÓN
# ==========================================

@circuit_breaker_bp.route('/accounts/<customer_id>/disable', methods=['POST'])
def disable_account(customer_id):
    '''Desactivar Circuit Breaker para una cuenta'''
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si existe
        cursor.execute(
            'SELECT customer_id FROM account_limits WHERE customer_id = ?',
            (customer_id,)
        )
        
        if not cursor.fetchone():
            return jsonify({
                'success': False,
                'error': 'Cuenta no encontrada en Circuit Breaker'
            }), 404
        
        # Desactivar
        cursor.execute(
            'UPDATE account_limits SET enabled = 0 WHERE customer_id = ?',
            (customer_id,)
        )
        conn.commit()
        conn.close()
        
        print(f"✅ Circuit Breaker desactivado para cuenta {customer_id}")
        
        return jsonify({
            'success': True,
            'message': f'Circuit Breaker desactivado para cuenta {customer_id}'
        })
        
    except Exception as e:
        print(f"❌ Error desactivando Circuit Breaker: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@circuit_breaker_bp.route('/accounts/<customer_id>/enable', methods=['POST'])
def enable_account(customer_id):
    '''Reactivar Circuit Breaker para una cuenta'''
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si existe
        cursor.execute(
            'SELECT customer_id FROM account_limits WHERE customer_id = ?',
            (customer_id,)
        )
        
        if not cursor.fetchone():
            return jsonify({
                'success': False,
                'error': 'Cuenta no encontrada en Circuit Breaker'
            }), 404
        
        # Reactivar
        cursor.execute(
            'UPDATE account_limits SET enabled = 1 WHERE customer_id = ?',
            (customer_id,)
        )
        conn.commit()
        conn.close()
        
        print(f"✅ Circuit Breaker reactivado para cuenta {customer_id}")
        
        return jsonify({
            'success': True,
            'message': f'Circuit Breaker reactivado para cuenta {customer_id}'
        })
        
    except Exception as e:
        print(f"❌ Error reactivando Circuit Breaker: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@circuit_breaker_bp.route('/accounts/<customer_id>', methods=['GET'])
def get_account_config(customer_id):
    '''Obtener configuración de una cuenta'''
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT customer_id, max_spend_per_hour_cop, max_spend_per_day_cop, enabled, created_at
            FROM account_limits
            WHERE customer_id = ?
        ''', (customer_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({
                'success': False,
                'error': 'Cuenta no encontrada',
                'is_configured': False
            }), 404
        
        return jsonify({
            'success': True,
            'is_configured': True,
            'config': {
                'customer_id': row[0],
                'max_spend_per_hour_cop': row[1],
                'max_spend_per_day_cop': row[2],
                'enabled': bool(row[3]),
                'created_at': row[4]
            }
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo configuración: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
