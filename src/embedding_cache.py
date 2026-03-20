"""
Модуль кэширования эмбеддингов.

Экономит API вызовы и время при повторной обработке документов.
"""

import json
import hashlib
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Директория для кэша
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

EMBEDDINGS_CACHE_FILE = CACHE_DIR / "embeddings.json"
METADATA_CACHE_FILE = CACHE_DIR / "embeddings_metadata.json"


class EmbeddingCache:
    """
    Кэш для эмбеддингов.
    
    Особенности:
    - Хэширует текст + модель = уникальный ключ
    - Хранит метаданные (дата, модель, размерность)
    - Автоматическая очистка устаревших записей
    """
    
    def __init__(
        self,
        cache_dir: Path = CACHE_DIR,
        max_age_days: int = 30,
        max_size_mb: int = 100
    ):
        """
        Инициализация кэша.
        
        Args:
            cache_dir: Директория для кэша.
            max_age_days: Максимальный возраст записей (дней).
            max_size_mb: Максимальный размер кэша (МБ).
        """
        self.cache_dir = cache_dir
        self.max_age_days = max_age_days
        self.max_size_mb = max_size_mb
        self.cache_file = cache_dir / "embeddings.json"
        self.metadata_file = cache_dir / "embeddings_metadata.json"
        
        # Загружаем кэш в память
        self._cache: Dict[str, List[float]] = {}
        self._metadata: Dict[str, Dict] = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Загружает кэш из файла."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                logger.info(f"Загружено {len(self._cache)} записей из кэша")
            except Exception as e:
                logger.warning(f"Не удалось загрузить кэш: {e}")
                self._cache = {}
        
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self._metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Не удалось загрузить метаданные кэша: {e}")
                self._metadata = {}
    
    def _save_cache(self) -> None:
        """Сохраняет кэш в файл."""
        try:
            self.cache_dir.mkdir(exist_ok=True)
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f)
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, indent=2)
            
            logger.debug(f"Кэш сохранён: {len(self._cache)} записей")
        except Exception as e:
            logger.error(f"Не удалось сохранить кэш: {e}")
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """
        Генерирует ключ кэша.
        
        Args:
            text: Текст для хэширования.
            model: Модель эмбеддингов.
        
        Returns:
            Уникальный ключ.
        """
        # Используем хэш текста + модель
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """
        Получает эмбеддинг из кэша.
        
        Args:
            text: Текст.
            model: Модель эмбеддингов.
        
        Returns:
            Эмбеддинг или None, если не найден.
        """
        key = self._get_cache_key(text, model)
        
        if key in self._cache:
            # Проверяем возраст
            if key in self._metadata:
                created = self._metadata[key].get('created_at')
                if created:
                    created_date = datetime.fromisoformat(created)
                    age_days = (datetime.now() - created_date).days
                    
                    if age_days > self.max_age_days:
                        # Запись устарела
                        self.delete(text, model)
                        return None
            
            logger.debug(f"Найден в кэше: {key[:16]}...")
            return self._cache[key]
        
        return None
    
    def set(self, text: str, model: str, embedding: List[float], 
            metadata: Dict = None) -> None:
        """
        Сохраняет эмбеддинг в кэш.
        
        Args:
            text: Текст.
            model: Модель эмбеддингов.
            embedding: Вектор эмбеддинга.
            metadata: Дополнительные метаданные.
        """
        key = self._get_cache_key(text, model)
        
        self._cache[key] = embedding
        self._metadata[key] = {
            'created_at': datetime.now().isoformat(),
            'model': model,
            'text_length': len(text),
            'embedding_dim': len(embedding),
            **(metadata or {})
        }
        
        # Проверяем размер и очищаем если нужно
        self._check_size_and_cleanup()
        
        # Сохраняем
        self._save_cache()
        
        logger.debug(f"Сохранено в кэш: {key[:16]}...")
    
    def delete(self, text: str, model: str) -> None:
        """Удаляет запись из кэша."""
        key = self._get_cache_key(text, model)
        
        if key in self._cache:
            del self._cache[key]
        if key in self._metadata:
            del self._metadata[key]
        
        self._save_cache()
    
    def get_batch(self, texts: List[str], model: str) -> Dict[int, List[float]]:
        """
        Получает эмбеддинги для батча текстов.
        
        Args:
            texts: Список текстов.
            model: Модель эмбеддингов.
        
        Returns:
            Словарь {индекс: эмбеддинг} только для найденных в кэше.
        """
        results = {}
        
        for i, text in enumerate(texts):
            embedding = self.get(text, model)
            if embedding is not None:
                results[i] = embedding
        
        logger.info(f"Найдено в кэше: {len(results)}/{len(texts)}")
        return results
    
    def set_batch(self, texts: List[str], model: str, 
                  embeddings: List[List[float]]) -> None:
        """
        Сохраняет батч эмбеддингов в кэш.
        
        Args:
            texts: Список текстов.
            model: Модель эмбеддингов.
            embeddings: Список эмбеддингов.
        """
        for text, embedding in zip(texts, embeddings):
            self.set(text, model, embedding)
        
        logger.info(f"Сохранено в кэш: {len(embeddings)} эмбеддингов")
    
    def _check_size_and_cleanup(self) -> None:
        """Проверяет размер кэша и очищает при необходимости."""
        if not self.cache_file.exists():
            return
        
        size_mb = self.cache_file.stat().st_size / (1024 * 1024)
        
        if size_mb > self.max_size_mb:
            # Удаляем самые старые записи
            logger.info(f"Кэш превысил лимит {size_mb:.1f}MB, очищаем...")
            
            # Сортируем по дате
            sorted_keys = sorted(
                self._metadata.items(),
                key=lambda x: x[1].get('created_at', '')
            )
            
            # Удаляем 20% самых старых
            remove_count = len(sorted_keys) // 5
            for key, _ in sorted_keys[:remove_count]:
                self._cache.pop(key, None)
                self._metadata.pop(key, None)
            
            self._save_cache()
            logger.info(f"Удалено {remove_count} старых записей из кэша")
    
    def clear(self) -> None:
        """Очищает весь кэш."""
        self._cache = {}
        self._metadata = {}
        self._save_cache()
        logger.info("Кэш очищен")
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша."""
        size_mb = 0
        if self.cache_file.exists():
            size_mb = self.cache_file.stat().st_size / (1024 * 1024)
        
        return {
            'total_entries': len(self._cache),
            'size_mb': round(size_mb, 2),
            'max_age_days': self.max_age_days,
            'max_size_mb': self.max_size_mb
        }


# Глобальный экземпляр кэша
_global_cache: Optional[EmbeddingCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """Получает глобальный экземпляр кэша."""
    global _global_cache
    if _global_cache is None:
        _global_cache = EmbeddingCache()
    return _global_cache


def get_embedding_with_cache(
    text: str,
    model: str,
    openai_client,
    cache: EmbeddingCache = None
) -> List[float]:
    """
    Получает эмбеддинг с использованием кэша.
    
    Args:
        text: Текст.
        model: Модель эмбеддингов.
        openai_client: OpenAI клиент.
        cache: Экземпляр кэша (опционально).
    
    Returns:
        Эмбеддинг.
    """
    if cache is None:
        cache = get_embedding_cache()
    
    # Пробуем получить из кэша
    cached = cache.get(text, model)
    if cached is not None:
        return cached
    
    # Генерируем новый
    response = openai_client.embeddings.create(
        model=model,
        input=text
    )
    embedding = response.data[0].embedding
    
    # Сохраняем в кэш
    cache.set(text, model, embedding)
    
    return embedding


def get_embeddings_batch_with_cache(
    texts: List[str],
    model: str,
    openai_client,
    cache: EmbeddingCache = None
) -> List[List[float]]:
    """
    Получает эмбеддинги для батча с использованием кэша.
    
    Args:
        texts: Список текстов.
        model: Модель эмбеддингов.
        openai_client: OpenAI клиент.
        cache: Экземпляр кэша (опционально).
    
    Returns:
        Список эмбеддингов.
    """
    if cache is None:
        cache = get_embedding_cache()
    
    # Разделяем на кэшированные и новые
    cached_embeddings = cache.get_batch(texts, model)
    
    # Индексы, которые нужно получить из API
    new_indices = [i for i in range(len(texts)) if i not in cached_embeddings]
    new_texts = [texts[i] for i in new_indices]
    
    if new_texts:
        # Получаем новые эмбеддинги
        response = openai_client.embeddings.create(
            model=model,
            input=new_texts
        )
        new_embeddings = [item.embedding for item in response.data]
        
        # Сохраняем в кэш
        cache.set_batch(new_texts, model, new_embeddings)
    else:
        new_embeddings = []
    
    # Объединяем результаты
    result = []
    new_idx = 0
    for i in range(len(texts)):
        if i in cached_embeddings:
            result.append(cached_embeddings[i])
        else:
            result.append(new_embeddings[new_idx])
            new_idx += 1
    
    return result
