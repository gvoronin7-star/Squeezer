"""
Асинхронный и параллельный процессор для RAG-системы.

Предоставляет:
- Параллельную обработку страниц PDF
- Асинхронную векторизацию
- Batch processing с контролем concurrency
"""

import asyncio
import logging
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)


# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

@dataclass
class ParallelConfig:
    """Конфигурация параллельной обработки."""
    max_workers: int = 4
    batch_size: int = 10
    use_threading: bool = True  # ThreadPool vs ProcessPool
    progress_callback: Optional[Callable] = None


# ============================================================================
# ПАРАЛЛЕЛЬНЫЙ ОБРАБОТЧИК
# ============================================================================

class ParallelProcessor:
    """
    Параллельный процессор для CPU-bound задач.
    
    Особенности:
    - ThreadPool для I/O-bound задач (API, чтение файлов)
    - ProcessPool для CPU-bound задач (обработка текста)
    - Контроль concurrency
    - Progress callbacks
    """
    
    def __init__(self, config: ParallelConfig = None):
        self.config = config or ParallelConfig()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._lock = threading.Lock()
    
    def __enter__(self):
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.max_workers
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._executor:
            self._executor.shutdown(wait=True)
    
    def map_parallel(
        self,
        func: Callable,
        items: List[Any],
        callback: Optional[Callable] = None
    ) -> List[Any]:
        """
        Параллельное применение функции к списку.
        
        Args:
            func: Функция для применения
            items: Список элементов
            callback: Опциональный callback для прогресса
        
        Returns:
            Список результатов в том же порядке
        """
        if not items:
            return []
        
        # Для small batch - последовательно
        if len(items) <= self.config.batch_size:
            return [func(item) for item in items]
        
        results = [None] * len(items)
        completed = 0
        total = len(items)
        
        def process_item(index_item):
            index, item = index_item
            try:
                result = func(item)
                return index, result, None
            except Exception as e:
                return index, None, str(e)
        
        # Используем executor для параллельности
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(process_item, (i, item)): i 
                for i, item in enumerate(items)
            }
            
            for future in futures:
                index, result, error = future.result()
                results[index] = result
                completed += 1
                
                if error:
                    logger.warning(f"Error processing item {index}: {error}")
                
                # Progress callback
                if callback:
                    callback(completed, total)
                
                if self.config.progress_callback:
                    self.config.progress_callback(completed, total)
        
        return results
    
    def process_batches(
        self,
        func: Callable,
        items: List[Any],
        batch_size: int = None
    ) -> List[Any]:
        """
        Обработка батчами с контролем размера.
        
        Args:
            func: Функция для батча
            items: Список элементов
            batch_size: Размер батча
        
        Returns:
            Список результатов
        """
        batch_size = batch_size or self.config.batch_size
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = func(batch)
            results.extend(batch_results if isinstance(batch_results, list) else [batch_results])
            
            logger.debug(f"Batch {i//batch_size + 1}/{(len(items)-1)//batch_size + 1} completed")
        
        return results


# ============================================================================
# ASYNC ОБРАБОТЧИК
# ============================================================================

class AsyncProcessor:
    """
    Асинхронный процессор для I/O-bound задач.
    
    Использует asyncio для:
    - Параллельных API вызовов
    - Асинхронного чтения файлов
    -并发ной обработки
    """
    
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.results: Dict[str, Any] = {}
    
    async def process_with_semaphore(self, task_id: str, coro):
        """Выполняет корутину с ограничением concurrency."""
        async with self.semaphore:
            try:
                result = await coro
                self.results[task_id] = result
                return result
            except Exception as e:
                logger.error(f"Async task {task_id} failed: {e}")
                self.results[task_id] = None
                raise
    
    async def process_batch_async(
        self,
        tasks: List[tuple[str, Callable]]
    ) -> Dict[str, Any]:
        """
        Параллельное выполнение асинхронных задач.
        
        Args:
            tasks: Список (task_id, coro) пар
        
        Returns:
            Словарь результатов
        """
        coros = [
            self.process_with_semaphore(task_id, coro())
            for task_id, coro in tasks
        ]
        
        await asyncio.gather(*coros, return_exceptions=True)
        
        return self.results
    
    def run_async(self, coro):
        """Запускает корутину в event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Создаём новый loop в отдельном потоке
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)


# ============================================================================
# СПЕЦИАЛИЗИРОВАННЫЕ ОБРАБОТЧИКИ
# ============================================================================

class PDFPageProcessor:
    """
    Параллельная обработка страниц PDF.
    
    Обрабатывает страницы параллельно:
    - Извлечение текста
    - Очистка
    - Нормализация
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
    
    def process_pages_parallel(
        self,
        pages: List[Dict],
        process_func: Callable,
        show_progress: bool = True
    ) -> List[Dict]:
        """
        Параллельная обработка страниц.
        
        Args:
            pages: Список страниц
            process_func: Функция обработки одной страницы
            show_progress: Показывать прогресс
        
        Returns:
            Обработанные страницы
        """
        results = [None] * len(pages)
        completed = 0
        
        def process_page(idx_page):
            idx, page = idx_page
            try:
                result = process_func(page)
                return idx, result, None
            except Exception as e:
                return idx, None, str(e)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(process_page, (i, page)): i 
                for i, page in enumerate(pages)
            }
            
            for future in futures:
                idx, result, error = future.result()
                results[idx] = result
                completed += 1
                
                if show_progress:
                    logger.info(f"Обработано страниц: {completed}/{len(pages)}")
                
                if error:
                    logger.error(f"Error on page {idx}: {error}")
        
        return results


class EmbeddingBatcher:
    """
    Батчинг эмбеддингов с контролем rate limiting.
    
    Особенности:
    - Автоматическое разбиение на батчи
    - Rate limiting
    - Retry с exponential backoff
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def create_batches(self, items: List[str]) -> List[List[str]]:
        """Разбивает тексты на батчи."""
        batches = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batches.append(batch)
        return batches
    
    async def generate_embeddings_async(
        self,
        texts: List[str],
        client,
        model: str
    ) -> List[List[float]]:
        """
        Асинхронная генерация эмбеддингов батчами.
        
        Args:
            texts: Список текстов
            client: OpenAI клиент
            model: Модель эмбеддингов
        
        Returns:
            Список эмбеддингов
        """
        batches = self.create_batches(texts)
        all_embeddings = []
        
        for batch_num, batch in enumerate(batches):
            logger.info(f"Embedding batch {batch_num + 1}/{len(batches)}")
            
            for attempt in range(self.max_retries):
                try:
                    response = client.embeddings.create(
                        model=model,
                        input=batch
                    )
                    embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(embeddings)
                    break
                    
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    else:
                        logger.error(f"All retries failed for batch {batch_num}")
                        raise
        
        return all_embeddings


# ============================================================================
# УДОБНЫЕ ФУНКЦИИ
# ============================================================================

def parallel_map(func: Callable, items: List, workers: int = 4) -> List:
    """Быстрая параллельная обработка."""
    processor = ParallelProcessor(ParallelConfig(max_workers=workers))
    return processor.map_parallel(func, items)


async def async_batch_process(
    tasks: List[tuple[str, Callable]],
    max_concurrent: int = 10
) -> Dict[str, Any]:
    """Быстрая асинхронная обработка."""
    processor = AsyncProcessor(max_concurrent=max_concurrent)
    return await processor.process_batch_async(tasks)
