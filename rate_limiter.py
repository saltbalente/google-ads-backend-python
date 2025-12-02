"""
Rate Limiting and Request Queue Module
======================================
Sistema de rate limiting para proteger el backend de sobrecarga.
Implementa límites por usuario y globales.
"""

import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Callable, Any
from collections import defaultdict
from functools import wraps
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuración de rate limiting"""
    requests_per_minute: int = 10
    requests_per_hour: int = 100
    burst_limit: int = 5  # Requests rápidos consecutivos permitidos
    cooldown_seconds: float = 2.0  # Tiempo mínimo entre requests


@dataclass
class UserRequestStats:
    """Estadísticas de requests por usuario"""
    request_times: List[float] = field(default_factory=list)
    last_request_time: float = 0
    total_requests: int = 0
    blocked_requests: int = 0
    
    def cleanup_old_requests(self, window_seconds: float = 3600):
        """Limpia requests antiguos fuera de la ventana"""
        cutoff = time.time() - window_seconds
        self.request_times = [t for t in self.request_times if t > cutoff]
    
    def requests_in_window(self, window_seconds: float) -> int:
        """Cuenta requests dentro de una ventana de tiempo"""
        cutoff = time.time() - window_seconds
        return sum(1 for t in self.request_times if t > cutoff)


class RateLimiter:
    """
    Rate limiter por usuario con ventana deslizante.
    Soporta límites por minuto, hora, y control de burst.
    """
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self._user_stats: Dict[str, UserRequestStats] = defaultdict(UserRequestStats)
        self._lock = threading.Lock()
        self._global_stats = UserRequestStats()
        
        # Configuración de límites globales
        self.global_limit_per_minute = 100  # Total de requests por minuto del sistema
        self.global_limit_per_hour = 1000
    
    def _get_user_key(self, user_id: str = None, ip: str = None, customer_id: str = None) -> str:
        """Genera una clave única para identificar al usuario"""
        parts = [user_id or "", ip or "", customer_id or ""]
        combined = ":".join(filter(None, parts)) or "anonymous"
        return hashlib.md5(combined.encode()).hexdigest()[:16]
    
    def check_rate_limit(
        self, 
        user_id: str = None, 
        ip: str = None, 
        customer_id: str = None
    ) -> tuple[bool, Optional[str], Optional[float]]:
        """
        Verifica si el request está dentro de los límites.
        
        Returns:
            Tuple de (allowed, error_message, retry_after_seconds)
        """
        user_key = self._get_user_key(user_id, ip, customer_id)
        current_time = time.time()
        
        with self._lock:
            stats = self._user_stats[user_key]
            stats.cleanup_old_requests()
            
            # 1. Verificar cooldown entre requests
            time_since_last = current_time - stats.last_request_time
            if time_since_last < self.config.cooldown_seconds and stats.last_request_time > 0:
                retry_after = self.config.cooldown_seconds - time_since_last
                stats.blocked_requests += 1
                return False, "Too many requests. Please wait.", retry_after
            
            # 2. Verificar límite por minuto
            requests_last_minute = stats.requests_in_window(60)
            if requests_last_minute >= self.config.requests_per_minute:
                stats.blocked_requests += 1
                return False, f"Rate limit exceeded ({self.config.requests_per_minute}/min)", 60.0
            
            # 3. Verificar límite por hora
            requests_last_hour = stats.requests_in_window(3600)
            if requests_last_hour >= self.config.requests_per_hour:
                stats.blocked_requests += 1
                # Calcular tiempo hasta que expire el request más antiguo
                oldest_in_hour = min((t for t in stats.request_times if t > current_time - 3600), default=current_time)
                retry_after = 3600 - (current_time - oldest_in_hour)
                return False, f"Hourly limit exceeded ({self.config.requests_per_hour}/hour)", retry_after
            
            # 4. Verificar límite global
            self._global_stats.cleanup_old_requests()
            if self._global_stats.requests_in_window(60) >= self.global_limit_per_minute:
                return False, "System is busy. Please try again later.", 30.0
            
            # Request permitido - registrar
            stats.request_times.append(current_time)
            stats.last_request_time = current_time
            stats.total_requests += 1
            self._global_stats.request_times.append(current_time)
            
            return True, None, None
    
    def record_request(self, user_key: str, success: bool, duration: float):
        """Registra métricas adicionales de un request"""
        with self._lock:
            # Aquí se podrían agregar más métricas
            pass
    
    def get_user_stats(self, user_id: str = None, ip: str = None, customer_id: str = None) -> Dict[str, Any]:
        """Obtiene estadísticas de un usuario"""
        user_key = self._get_user_key(user_id, ip, customer_id)
        
        with self._lock:
            stats = self._user_stats.get(user_key, UserRequestStats())
            stats.cleanup_old_requests()
            
            return {
                "requests_last_minute": stats.requests_in_window(60),
                "requests_last_hour": stats.requests_in_window(3600),
                "total_requests": stats.total_requests,
                "blocked_requests": stats.blocked_requests,
                "limit_per_minute": self.config.requests_per_minute,
                "limit_per_hour": self.config.requests_per_hour
            }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas globales del sistema"""
        with self._lock:
            self._global_stats.cleanup_old_requests()
            
            return {
                "global_requests_last_minute": self._global_stats.requests_in_window(60),
                "global_requests_last_hour": self._global_stats.requests_in_window(3600),
                "active_users": len(self._user_stats),
                "global_limit_per_minute": self.global_limit_per_minute
            }


# Instancia global del rate limiter
# Configuración para usuarios enterprise (más generosa)
_rate_limiter = RateLimiter(RateLimitConfig(
    requests_per_minute=20,  # 20 landings por minuto por usuario
    requests_per_hour=200,   # 200 landings por hora por usuario
    burst_limit=5,
    cooldown_seconds=1.0     # 1 segundo mínimo entre requests
))


def rate_limit(func: Callable = None):
    """
    Decorador para aplicar rate limiting a un endpoint.
    
    Usage:
        @app.route('/api/landing/build')
        @rate_limit
        def build_landing():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import request, jsonify, make_response
            
            # Extraer identificadores del usuario
            user_id = request.headers.get('X-User-Id')
            ip = request.remote_addr
            customer_id = None
            
            # Intentar obtener customer_id del body
            try:
                data = request.get_json(silent=True) or {}
                customer_id = data.get('customerId') or data.get('customer_id')
            except:
                pass
            
            # Verificar rate limit
            allowed, error_msg, retry_after = _rate_limiter.check_rate_limit(
                user_id=user_id,
                ip=ip,
                customer_id=customer_id
            )
            
            if not allowed:
                response = make_response(jsonify({
                    'success': False,
                    'error': error_msg,
                    'retry_after': retry_after
                }), 429)
                response.headers['Retry-After'] = str(int(retry_after or 60))
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            
            return f(*args, **kwargs)
        
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


def get_rate_limiter() -> RateLimiter:
    """Obtiene la instancia global del rate limiter"""
    return _rate_limiter


class RequestQueue:
    """
    Cola de requests para procesamiento ordenado.
    Útil para operaciones que deben ejecutarse secuencialmente.
    """
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._queue_size = 0
        self._lock = threading.Lock()
        self._processing_count = 0
    
    def acquire(self, timeout: float = 300) -> bool:
        """
        Intenta adquirir un slot en la cola.
        
        Args:
            timeout: Tiempo máximo de espera en segundos
        
        Returns:
            True si se adquirió el slot, False si timeout
        """
        with self._lock:
            self._queue_size += 1
        
        acquired = self._semaphore.acquire(timeout=timeout)
        
        with self._lock:
            self._queue_size -= 1
            if acquired:
                self._processing_count += 1
        
        return acquired
    
    def release(self):
        """Libera un slot en la cola"""
        with self._lock:
            self._processing_count -= 1
        self._semaphore.release()
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado de la cola"""
        with self._lock:
            return {
                "max_concurrent": self.max_concurrent,
                "currently_processing": self._processing_count,
                "waiting_in_queue": self._queue_size,
                "available_slots": self.max_concurrent - self._processing_count
            }


# Cola global para generación de landings
# Limita a 5 generaciones simultáneas para no sobrecargar APIs externas
_landing_queue = RequestQueue(max_concurrent=5)


def get_landing_queue() -> RequestQueue:
    """Obtiene la cola de generación de landings"""
    return _landing_queue
