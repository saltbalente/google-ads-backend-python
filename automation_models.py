"""
Modelos de base de datos para el sistema de automatización en background.

Arquitectura:
- SQLAlchemy ORM para persistencia
- SQLite para simplicidad (escalable a PostgreSQL)
- Thread-safe con contextos de sesión
"""

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
import os

# Base para modelos
Base = declarative_base()

# Configuración de base de datos
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///automation_jobs.db')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if 'sqlite' in DATABASE_URL else {})

# Session factory thread-safe
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


class AutomationJob(Base):
    """
    Modelo para jobs de automatización.
    
    Estados posibles:
    - queued: Job creado, esperando procesamiento
    - running: Job en ejecución
    - completed: Job completado exitosamente
    - failed: Job falló con errores
    - cancelled: Job cancelado por usuario
    """
    
    __tablename__ = 'automation_jobs'
    
    # Identificadores
    id = Column(String(36), primary_key=True)  # UUID
    user_identifier = Column(String(255), index=True)  # Para multi-tenancy (customerId o email)
    
    # Configuración del job
    customer_id = Column(String(50), nullable=False, index=True)
    campaign_id = Column(String(50), nullable=False)
    report_id = Column(String(255), nullable=False)
    number_of_groups = Column(Integer, nullable=False)
    ads_per_group = Column(Integer, nullable=False)
    ai_provider = Column(String(50), nullable=False)  # openai, gemini, deepseek
    
    # Estado del job
    status = Column(String(20), nullable=False, default='queued', index=True)
    progress = Column(Float, default=0.0)  # 0.0 - 100.0
    current_step = Column(String(255), default='Iniciando...')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Resultados (JSON)
    results = Column(JSON, default=lambda: {
        'ad_groups_created': [],
        'keywords_added': 0,
        'ads_created': 0,
        'total_cost_estimate': 0.0
    })
    
    # Errores (JSON array)
    errors = Column(JSON, default=list)
    
    # Metadata adicional
    config_snapshot = Column(JSON, default=dict)  # Snapshot de configuración completa
    
    def __repr__(self):
        return f"<AutomationJob(id={self.id}, status={self.status}, progress={self.progress}%)>"
    
    def to_dict(self):
        """Serializa el job a diccionario para JSON response"""
        return {
            'id': self.id,
            'status': self.status,
            'progress': self.progress,
            'currentStep': self.current_step,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'startedAt': self.started_at.isoformat() if self.started_at else None,
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
            'results': self.results,
            'errors': self.errors,
            'config': {
                'customerId': self.customer_id,
                'campaignId': self.campaign_id,
                'reportId': self.report_id,
                'numberOfGroups': self.number_of_groups,
                'adsPerGroup': self.ads_per_group,
                'aiProvider': self.ai_provider
            }
        }


class AutomationLog(Base):
    """
    Modelo para logs detallados de cada job.
    Permite debugging y auditoría de operaciones.
    """
    
    __tablename__ = 'automation_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, SUCCESS
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Datos adicionales en formato JSON
    
    def __repr__(self):
        return f"<AutomationLog(job_id={self.job_id}, level={self.level}, message={self.message[:50]})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'jobId': self.job_id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'message': self.message,
            'data': self.data
        }


def init_db():
    """
    Inicializa la base de datos creando todas las tablas.
    Debe ejecutarse al iniciar la aplicación.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada correctamente")


def get_session():
    """
    Retorna una sesión de base de datos thread-safe.
    Usar con context manager:
    
    with get_session() as session:
        job = session.query(AutomationJob).filter_by(id=job_id).first()
    """
    return Session()


def close_session():
    """Cierra la sesión actual del thread"""
    Session.remove()


# Funciones helper para operaciones comunes

def create_job(job_id, config, user_identifier=None):
    """
    Crea un nuevo job en la base de datos.
    
    Args:
        job_id: UUID del job
        config: Dict con configuración del job
        user_identifier: Identificador del usuario (opcional)
    
    Returns:
        AutomationJob: Job creado
    """
    session = get_session()
    try:
        job = AutomationJob(
            id=job_id,
            user_identifier=user_identifier or config.get('customerId'),
            customer_id=config['customerId'],
            campaign_id=config['campaignId'],
            report_id=config['reportId'],
            number_of_groups=config['numberOfGroups'],
            ads_per_group=config['adsPerGroup'],
            ai_provider=config.get('aiProvider', 'openai'),
            config_snapshot=config
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job
    finally:
        close_session()


def get_job(job_id):
    """Obtiene un job por ID"""
    session = get_session()
    try:
        return session.query(AutomationJob).filter_by(id=job_id).first()
    finally:
        close_session()


def update_job(job_id, **kwargs):
    """
    Actualiza campos de un job.
    
    Ejemplo:
        update_job(job_id, status='running', progress=50.0, current_step='Creando ad groups...')
    """
    session = get_session()
    try:
        job = session.query(AutomationJob).filter_by(id=job_id).first()
        if job:
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            session.commit()
            session.refresh(job)
            return job
        return None
    finally:
        close_session()


def add_log(job_id, level, message, data=None):
    """
    Agrega un log entry para un job.
    
    Args:
        job_id: ID del job
        level: INFO, WARNING, ERROR, SUCCESS
        message: Mensaje descriptivo
        data: Datos adicionales (dict)
    """
    session = get_session()
    try:
        log = AutomationLog(
            job_id=job_id,
            level=level,
            message=message,
            data=data
        )
        session.add(log)
        session.commit()
    finally:
        close_session()


def get_job_logs(job_id, limit=100):
    """Obtiene logs de un job específico"""
    session = get_session()
    try:
        return session.query(AutomationLog)\
            .filter_by(job_id=job_id)\
            .order_by(AutomationLog.timestamp.desc())\
            .limit(limit)\
            .all()
    finally:
        close_session()


def get_user_jobs(user_identifier, limit=50, status=None):
    """
    Obtiene jobs de un usuario específico.
    
    Args:
        user_identifier: ID del usuario
        limit: Número máximo de jobs a retornar
        status: Filtrar por estado (opcional)
    """
    session = get_session()
    try:
        query = session.query(AutomationJob)\
            .filter_by(user_identifier=user_identifier)\
            .order_by(AutomationJob.created_at.desc())
        
        if status:
            query = query.filter_by(status=status)
        
        return query.limit(limit).all()
    finally:
        close_session()


def cleanup_old_jobs(days=30):
    """
    Limpia jobs completados más antiguos que X días.
    Útil para mantenimiento de la base de datos.
    
    Args:
        days: Días de antigüedad para limpiar
    
    Returns:
        int: Número de jobs eliminados
    """
    from datetime import timedelta
    
    session = get_session()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = session.query(AutomationJob)\
            .filter(AutomationJob.status.in_(['completed', 'failed']))\
            .filter(AutomationJob.completed_at < cutoff_date)\
            .delete()
        session.commit()
        return deleted
    finally:
        close_session()
