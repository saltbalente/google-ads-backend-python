"""
Retry and Circuit Breaker Module
================================
Sistema robusto de reintentos y circuit breaker para operaciones críticas.
Garantiza resiliencia ante fallos temporales de servicios externos.
"""

import time
import logging
import functools
import threading
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, List, Dict, Type
from enum import Enum
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Estados del circuit breaker"""
    CLOSED = "closed"      # Operación normal
    OPEN = "open"          # Circuito abierto, rechazando llamadas
    HALF_OPEN = "half_open"  # Probando si el servicio se recuperó


@dataclass
class RetryConfig:
    """Configuración para reintentos"""
    max_retries: int = 3
    base_delay: float = 1.0  # segundos
    max_delay: float = 60.0  # segundos
    exponential_base: float = 2.0
    jitter: bool = True  # Agregar variación aleatoria
    retryable_exceptions: tuple = (Exception,)
    non_retryable_exceptions: tuple = ()


@dataclass
class CircuitBreakerConfig:
    """Configuración del circuit breaker"""
    failure_threshold: int = 5  # Fallos antes de abrir
    success_threshold: int = 2  # Éxitos para cerrar en half-open
    timeout: float = 30.0  # Segundos antes de pasar a half-open


class CircuitBreakerOpenError(Exception):
    """Excepción cuando el circuit breaker está abierto"""
    pass


class MaxRetriesExceededError(Exception):
    """Excepción cuando se exceden los reintentos máximos"""
    def __init__(self, message: str, last_exception: Exception = None):
        super().__init__(message)
        self.last_exception = last_exception


@dataclass
class RetryStats:
    """Estadísticas de reintentos"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_retries: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    def record_success(self):
        self.total_calls += 1
        self.successful_calls += 1
    
    def record_failure(self, error: str):
        self.total_calls += 1
        self.failed_calls += 1
        self.last_error = error
        self.last_error_time = datetime.now()
    
    def record_retry(self):
        self.total_retries += 1
    
    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "total_retries": self.total_retries,
            "success_rate": f"{self.success_rate * 100:.1f}%",
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None
        }


class CircuitBreaker:
    """
    Implementación de Circuit Breaker pattern.
    Protege contra llamadas repetidas a servicios fallidos.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self._lock = threading.Lock()
        self.stats = RetryStats()
    
    def _should_allow_request(self) -> bool:
        """Determina si se debe permitir la solicitud"""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # Verificar si ha pasado el timeout
                if self.last_failure_time:
                    elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                    if elapsed >= self.config.timeout:
                        logger.info(f"🔄 Circuit '{self.name}' transitioning to HALF_OPEN")
                        self.state = CircuitState.HALF_OPEN
                        self.success_count = 0
                        return True
                return False
            
            # HALF_OPEN: permitir una solicitud de prueba
            return True
    
    def _record_success(self):
        """Registra una llamada exitosa"""
        with self._lock:
            self.stats.record_success()
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    logger.info(f"✅ Circuit '{self.name}' transitioning to CLOSED")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
            else:
                self.failure_count = 0
    
    def _record_failure(self, error: Exception):
        """Registra una llamada fallida"""
        with self._lock:
            self.stats.record_failure(str(error))
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitState.HALF_OPEN:
                logger.warning(f"⚠️ Circuit '{self.name}' transitioning back to OPEN")
                self.state = CircuitState.OPEN
                self.failure_count = self.config.failure_threshold
            else:
                self.failure_count += 1
                if self.failure_count >= self.config.failure_threshold:
                    logger.warning(f"🔴 Circuit '{self.name}' transitioning to OPEN after {self.failure_count} failures")
                    self.state = CircuitState.OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta una función protegida por el circuit breaker.
        
        Raises:
            CircuitBreakerOpenError: Si el circuito está abierto
        """
        if not self._should_allow_request():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service appears to be unavailable. Try again in {self.config.timeout} seconds."
            )
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure(e)
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del circuit breaker"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "stats": self.stats.to_dict()
        }


class RetryHandler:
    """
    Manejador de reintentos con backoff exponencial.
    """
    
    def __init__(self, config: RetryConfig = None, circuit_breaker: CircuitBreaker = None):
        self.config = config or RetryConfig()
        self.circuit_breaker = circuit_breaker
        self.stats = RetryStats()
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calcula el delay para el próximo reintento"""
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            # Agregar jitter de ±25%
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def _is_retryable(self, exception: Exception) -> bool:
        """Determina si la excepción es reintentable"""
        if isinstance(exception, self.config.non_retryable_exceptions):
            return False
        return isinstance(exception, self.config.retryable_exceptions)
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta una función con reintentos automáticos.
        
        Args:
            func: Función a ejecutar
            *args, **kwargs: Argumentos para la función
        
        Returns:
            Resultado de la función
        
        Raises:
            MaxRetriesExceededError: Si se exceden los reintentos
            CircuitBreakerOpenError: Si el circuit breaker está abierto
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Si hay circuit breaker, usarlo
                if self.circuit_breaker:
                    result = self.circuit_breaker.call(func, *args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                self.stats.record_success()
                return result
                
            except CircuitBreakerOpenError:
                # No reintentar si el circuit breaker está abierto
                raise
                
            except Exception as e:
                last_exception = e
                
                if not self._is_retryable(e):
                    logger.error(f"❌ Non-retryable error: {e}")
                    self.stats.record_failure(str(e))
                    raise
                
                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"⚠️ Attempt {attempt + 1}/{self.config.max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    self.stats.record_retry()
                    time.sleep(delay)
                else:
                    logger.error(f"❌ All {self.config.max_retries + 1} attempts failed")
                    self.stats.record_failure(str(e))
        
        raise MaxRetriesExceededError(
            f"Operation failed after {self.config.max_retries + 1} attempts",
            last_exception
        )


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,),
    circuit_breaker_name: str = None
):
    """
    Decorador para agregar reintentos a una función.
    
    Usage:
        @with_retry(max_retries=3, base_delay=1.0)
        def call_external_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            retryable_exceptions=retryable_exceptions
        )
        
        circuit_breaker = None
        if circuit_breaker_name:
            circuit_breaker = get_or_create_circuit_breaker(circuit_breaker_name)
        
        handler = RetryHandler(config, circuit_breaker)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return handler.execute(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


# Global registry of circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_cb_lock = threading.Lock()


def get_or_create_circuit_breaker(
    name: str, 
    config: CircuitBreakerConfig = None
) -> CircuitBreaker:
    """Obtiene o crea un circuit breaker por nombre"""
    with _cb_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, config)
        return _circuit_breakers[name]


def get_all_circuit_breaker_stats() -> Dict[str, Any]:
    """Obtiene estadísticas de todos los circuit breakers"""
    return {name: cb.get_status() for name, cb in _circuit_breakers.items()}


# Pre-configured circuit breakers for common services
OPENAI_CIRCUIT = get_or_create_circuit_breaker(
    "openai", 
    CircuitBreakerConfig(failure_threshold=3, timeout=60)
)

GITHUB_CIRCUIT = get_or_create_circuit_breaker(
    "github",
    CircuitBreakerConfig(failure_threshold=5, timeout=30)
)

GOOGLE_ADS_CIRCUIT = get_or_create_circuit_breaker(
    "google_ads",
    CircuitBreakerConfig(failure_threshold=3, timeout=45)
)
