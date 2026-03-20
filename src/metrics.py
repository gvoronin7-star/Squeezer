"""
Модуль метрик и мониторинга для RAG-системы.

Собирает метрики производительности и использования.
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


# ============================================================================
# МЕТРИКИ
# ============================================================================

@dataclass
class OperationMetric:
    """Метрика одной операции."""
    operation: str
    duration: float
    success: bool
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MetricsCollector:
    """
    Сборщик метрик для мониторинга системы.
    
    Собирает:
    - Время выполнения операций
    - Успешность/ошибки
    - Количество API вызовов
    - Использование токенов
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton паттерн."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._metrics: list[OperationMetric] = []
        self._counters: Dict[str, int] = defaultdict(int)
        self._timers: Dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        
        logger.info("MetricsCollector инициализирован")
    
    def record_operation(
        self,
        operation: str,
        duration: float,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Записывает метрику операции."""
        with self._lock:
            metric = OperationMetric(
                operation=operation,
                duration=duration,
                success=success,
                error=error
            )
            self._metrics.append(metric)
            
            # Обновляем счётчики
            self._counters[f"{operation}_total"] += 1
            if success:
                self._counters[f"{operation}_success"] += 1
            else:
                self._counters[f"{operation}_error"] += 1
            
            # Обновляем таймеры
            self._timers[operation].append(duration)
    
    def increment(self, counter: str, value: int = 1) -> None:
        """Увеличивает счётчик."""
        with self._lock:
            self._counters[counter] += value
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику метрик."""
        with self._lock:
            # Вычисляем статистику по операциям
            operation_stats = {}
            
            for op, durations in self._timers.items():
                if durations:
                    operation_stats[op] = {
                        "count": len(durations),
                        "total_time": sum(durations),
                        "avg_time": sum(durations) / len(durations),
                        "min_time": min(durations),
                        "max_time": max(durations)
                    }
            
            return {
                "total_operations": len(self._metrics),
                "success_count": sum(1 for m in self._metrics if m.success),
                "error_count": sum(1 for m in self._metrics if not m.success),
                "counters": dict(self._counters),
                "operations": operation_stats,
                "uptime": datetime.now().isoformat()
            }
    
    def reset(self) -> None:
        """Сбрасывает все метрики."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._timers.clear()
            logger.info("Метрики сброшены")
    
    def export_prometheus(self) -> str:
        """Экспортирует метрики в формате Prometheus."""
        lines = []
        stats = self.get_stats()
        
        # Счётчики
        for name, value in stats["counters"].items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # Операции
        for op, op_stats in stats["operations"].items():
            safe_name = op.replace(".", "_").replace("-", "_")
            lines.append(f"# TYPE {safe_name}_duration_seconds summary")
            lines.append(f'{safe_name}_duration_seconds_count {op_stats["count"]}')
            lines.append(f'{safe_name}_duration_seconds_sum {op_stats["total_time"]}')
        
        return "\n".join(lines)


# Глобальный экземпляр
_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Получает глобальный экземпляр сборщика метрик."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


# ============================================================================
# КОНТЕКСТНЫЙ МЕНЕДЖЕР ДЛЯ ЗАМЕРА ВРЕМЕНИ
# ============================================================================

class Timer:
    """Контекстный менеджер для замера времени операций."""
    
    def __init__(self, operation: str, log_success: bool = True):
        self.operation = operation
        self.log_success = log_success
        self.start_time = 0
        self.error: Optional[str] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        
        # Записываем метрику
        get_metrics().record_operation(
            operation=self.operation,
            duration=duration,
            success=success,
            error=error
        )
        
        # Логируем
        if self.log_success:
            if success:
                logger.debug(f"{self.operation} completed in {duration:.3f}s")
            else:
                logger.error(f"{self.operation} failed: {error} ({duration:.3f}s)")
        
        return False  # Не подавляем исключения


# ============================================================================
# ДЕКОРАТОР ДЛЯ АВТОМАТИЧЕСКОГО ЗАМЕРА
# ============================================================================

def timed(operation: str = None):
    """Декоратор для автоматического замера времени функций."""
    def decorator(func):
        op_name = operation or func.__name__
        
        def wrapper(*args, **kwargs):
            with Timer(op_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# ПРОМЕЖУТОЧНЫЙ СЛОЙ ДЛЯ API ВЫЗОВОВ
# ============================================================================

class APIMetrics:
    """
    Промежуточный слой для API вызовов с метриками.
    
    Пример использования:
        api = APIMetrics('openai', 'gpt-4o-mini')
        response = api.call(lambda: client.chat.completions.create(...))
    """
    
    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        self.metrics = get_metrics()
    
    def call(self, func, *args, **kwargs):
        """Выполняет API вызов с замером времени."""
        operation = f"api.{self.provider}.{self.model}"
        
        with Timer(operation, log_success=False):
            try:
                result = func(*args, **kwargs)
                
                # Подсчитываем токены если есть
                if hasattr(result, 'usage'):
                    self.metrics.increment(f"tokens_{self.provider}_input", 
                                           result.usage.prompt_tokens or 0)
                    self.metrics.increment(f"tokens_{self.provider}_output",
                                           result.usage.completion_tokens or 0)
                
                return result
                
            except Exception as e:
                self.metrics.increment(f"api_errors_{self.provider}")
                raise
    
    def call_batch(self, func, items: list, batch_size: int = 10):
        """Выполняет батч API вызовов."""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            with Timer(f"api.{self.provider}.batch", log_success=True):
                try:
                    result = func(batch)
                    results.extend(result if isinstance(result, list) else [result])
                except Exception as e:
                    logger.error(f"Batch API error: {e}")
        
        return results
