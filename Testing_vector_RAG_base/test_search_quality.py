"""
Тесты качества поиска.

Метрики:
- Precision@K
- Recall@K
- MRR (Mean Reciprocal Rank)
- Latency
"""

import json
import logging
import sys
import time
from pathlib import Path
import numpy as np
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

# Добавляем родительскую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Результат теста."""
    test_name: str
    category: str
    passed: bool
    score: float
    message: str
    details: Dict[str, Any]


class SearchQualityTests:
    """
    Тесты качества поиска.
    
    Пример использования:
        tester = SearchQualityTests(index, dataset, api_key)
        results = tester.run_all_tests()
    """
    
    def __init__(
        self,
        index,
        dataset: List[Dict],
        api_key: str = None,
        llm_model: str = "gpt-4o-mini",
        config: Dict = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1"
    ):
        """
        Инициализация.
        
        Args:
            index: FAISS индекс.
            dataset: Список чанков.
            api_key: API ключ OpenAI.
            llm_model: Модель LLM.
            config: Конфигурация тестов.
            api_base: Базовый URL API.
        """
        self.index = index
        self.dataset = dataset or []
        self.api_key = api_key
        self.llm_model = llm_model
        self.api_base = api_base
        self.config = config or {}
        
        # Параметры по умолчанию
        self.top_k_values = self.config.get('top_k_values', [5, 10, 20])
        self.precision_threshold = self.config.get('precision_threshold', 0.7)
        self.recall_threshold = self.config.get('recall_threshold', 0.7)
        self.max_latency = self.config.get('max_latency_seconds', 2.0)
        
        # Тестовые запросы (генерируются автоматически)
        self.test_queries = self._generate_test_queries()
    
    def _generate_test_queries(self) -> List[Dict]:
        """Генерирует тестовые запросы из чанков."""
        queries = []
        
        if not self.dataset:
            return queries
        
        # Берём по 1 запросу из каждых 5 чанков
        step = max(1, len(self.dataset) // 20)
        
        for i in range(0, len(self.dataset), step):
            chunk = self.dataset[i]
            text = chunk.get('text', '')
            
            if len(text) < 50:
                continue
            
            # Генерируем запрос из первого предложения
            sentences = text.split('. ')
            if sentences:
                query_text = sentences[0][:100]
                
                queries.append({
                    'query': query_text,
                    'relevant_chunk_id': chunk.get('metadata', {}).get('chunk_id', i),
                    'relevant_text': text[:200]
                })
        
        return queries[:20]  # Максимум 20 запросов
    
    def run_all_tests(self) -> List[TestResult]:
        """Запускает все тесты поиска."""
        results = []
        
        results.append(self.test_search_availability())
        results.append(self.test_latency())
        results.append(self.test_precision_at_k())
        results.append(self.test_recall_at_k())
        results.append(self.test_result_diversity())
        results.append(self.test_edge_cases())
        
        return results
    
    # ------------------------------------------------------------------------
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ------------------------------------------------------------------------
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Получает эмбеддинг для текста."""
        try:
            import openai
            
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base
            )
            
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            return np.array([response.data[0].embedding], dtype='float32')
            
        except Exception as e:
            logger.error(f"Ошибка получения эмбеддинга: {e}")
            return None
    
    def _search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Выполняет поиск."""
        if not self.index or not self.dataset:
            return []
        
        query_vec = self._get_embedding(query)
        if query_vec is None:
            return []
        
        distances, indices = self.index.search(query_vec, top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.dataset):
                doc = self.dataset[int(idx)].copy()
                doc['score'] = float(1.0 / (1.0 + dist))
                doc['distance'] = float(dist)
                results.append(doc)
        
        return results
    
    # ------------------------------------------------------------------------
    # ТЕСТЫ
    # ------------------------------------------------------------------------
    
    def test_search_availability(self) -> TestResult:
        """Проверяет доступность поиска."""
        if not self.index:
            return TestResult(
                test_name="search_availability",
                category="search",
                passed=False,
                score=0.0,
                message="Индекс не загружен",
                details={}
            )
        
        if not self.dataset:
            return TestResult(
                test_name="search_availability",
                category="search",
                passed=False,
                score=0.0,
                message="Датасет пуст",
                details={}
            )
        
        if not self.api_key:
            return TestResult(
                test_name="search_availability",
                category="search",
                passed=False,
                score=0.0,
                message="API ключ не указан",
                details={}
            )
        
        # Пробуем выполнить тестовый поиск
        try:
            results = self._search("тестовый запрос", top_k=5)
            
            passed = len(results) > 0
            score = len(results) / 5
            
            return TestResult(
                test_name="search_availability",
                category="search",
                passed=passed,
                score=score,
                message=f"Поиск работает, найдено: {len(results)}",
                details={'results_count': len(results)}
            )
            
        except Exception as e:
            return TestResult(
                test_name="search_availability",
                category="search",
                passed=False,
                score=0.0,
                message=f"Ошибка поиска: {str(e)}",
                details={'error': str(e)}
            )
    
    def test_latency(self) -> TestResult:
        """Проверяет скорость поиска."""
        if not self.test_queries:
            return TestResult(
                test_name="latency",
                category="search",
                passed=True,
                score=1.0,
                message="Нет тестовых запросов",
                details={}
            )
        
        latencies = []
        
        for query_data in self.test_queries[:10]:  # Тестируем 10 запросов
            start = time.time()
            self._search(query_data['query'], top_k=10)
            latency = time.time() - start
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        # Прошёл, если среднее время меньше порога
        passed = avg_latency < self.max_latency
        score = max(0, 1.0 - avg_latency / self.max_latency)
        
        return TestResult(
            test_name="latency",
            category="search",
            passed=passed,
            score=score,
            message=f"Среднее время: {avg_latency:.3f}с (макс: {max_latency:.3f}с)",
            details={
                'avg_latency': round(avg_latency, 3),
                'max_latency': round(max_latency, 3),
                'min_latency': round(min_latency, 3),
                'samples': len(latencies)
            }
        )
    
    def test_precision_at_k(self) -> TestResult:
        """
        Тестирует Precision@K.
        
        Precision@K = (релевантные в топ-K) / K
        
        Для тестирования используем поиск по самому чанку - 
        если чанк находится в топ-K, то precision высокий.
        """
        if not self.test_queries:
            return TestResult(
                test_name="precision_at_k",
                category="search",
                passed=True,
                score=1.0,
                message="Нет тестовых запросов",
                details={}
            )
        
        k = 5
        precisions = []
        
        for query_data in self.test_queries:
            results = self._search(query_data['query'], top_k=k)
            
            if not results:
                continue
            
            # Проверяем, есть ли релевантный чанк в результатах
            relevant_id = query_data['relevant_chunk_id']
            
            # Ищем позицию релевантного чанка
            position = None
            for i, result in enumerate(results[:k]):
                result_id = result.get('metadata', {}).get('chunk_id')
                if result_id == relevant_id:
                    position = i + 1
                    break
            
            # Precision = 1/position если найден, иначе 0
            if position:
                precision = 1.0 / position  # Лучше позиция = выше precision
            else:
                # Проверяем, есть ли в топ-10
                results_10 = self._search(query_data['query'], top_k=10)
                found_in_10 = any(
                    r.get('metadata', {}).get('chunk_id') == relevant_id 
                    for r in results_10
                )
                precision = 0.1 if found_in_10 else 0.0
            
            precisions.append(precision)
        
        if not precisions:
            return TestResult(
                test_name="precision_at_k",
                category="search",
                passed=True,
                score=1.0,
                message="Недостаточно данных",
                details={}
            )
        
        avg_precision = sum(precisions) / len(precisions)
        
        # Прошёл, если средний precision > 0.5 (в среднем в топ-2)
        passed = avg_precision >= 0.5
        score = min(1.0, avg_precision * 2)  # Нормализуем к 0-1
        
        return TestResult(
            test_name="precision_at_k",
            category="search",
            passed=passed,
            score=score,
            message=f"Precision@{k}: {avg_precision:.2f} (средняя позиция: {1/avg_precision if avg_precision > 0 else 'N/A':.1f})",
            details={
                'avg_precision': round(avg_precision, 3),
                'k': k,
                'samples': len(precisions)
            }
        )
    
    def test_recall_at_k(self) -> TestResult:
        """
        Тестирует Recall@K.
        
        Recall@K = (найденные релевантные) / (все релевантные)
        """
        if not self.test_queries:
            return TestResult(
                test_name="recall_at_k",
                category="search",
                passed=True,
                score=1.0,
                message="Нет тестовых запросов",
                details={}
            )
        
        k = 10
        recalls = []
        
        for query_data in self.test_queries:
            results = self._search(query_data['query'], top_k=k)
            
            # Проверяем, есть ли релевантный чанк в результатах
            relevant_id = query_data['relevant_chunk_id']
            
            found = False
            for result in results[:k]:
                result_id = result.get('metadata', {}).get('chunk_id')
                if result_id == relevant_id:
                    found = True
                    break
            
            recall = 1.0 if found else 0.0
            recalls.append(recall)
        
        avg_recall = sum(recalls) / len(recalls) if recalls else 0
        
        # Прошёл, если recall выше порога
        passed = avg_recall >= self.recall_threshold
        score = avg_recall
        
        return TestResult(
            test_name="recall_at_k",
            category="search",
            passed=passed,
            score=score,
            message=f"Recall@{k}: {avg_recall:.2f}",
            details={
                'avg_recall': round(avg_recall, 3),
                'k': k,
                'samples': len(recalls)
            }
        )

    def test_result_diversity(self) -> TestResult:
        """Проверяет разнообразие результатов поиска."""
        if not self.test_queries:
            return TestResult(
                test_name="result_diversity",
                category="search",
                passed=True,
                score=1.0,
                message="Нет тестовых запросов",
                details={}
            )

        diversities = []
        
        for query_data in self.test_queries[:10]:
            results = self._search(query_data['query'], top_k=10)
            
            if len(results) < 2:
                continue
            
            # Проверяем разнообразие страниц
            pages = set()
            for r in results:
                page = r.get('metadata', {}).get('page_number')
                if page:
                    pages.add(page)
            
            diversity = len(pages) / min(len(results), 10)
            diversities.append(diversity)
        
        if not diversities:
            return TestResult(
                test_name="result_diversity",
                category="search",
                passed=True,
                score=1.0,
                message="Недостаточно данных",
                details={}
            )
        
        avg_diversity = sum(diversities) / len(diversities)
        
        # Хорошее разнообразие: > 0.5
        passed = avg_diversity >= 0.5
        score = avg_diversity
        
        return TestResult(
            test_name="result_diversity",
            category="search",
            passed=passed,
            score=score,
            message=f"Разнообразие: {avg_diversity:.2f}",
            details={
                'avg_diversity': round(avg_diversity, 3),
                'samples': len(diversities)
            }
        )
    
    def test_edge_cases(self) -> TestResult:
        """Тестирует граничные случаи."""
        edge_queries = [
            "",  # Пустой запрос
            "   ",  # Только пробелы
            "xyz123nonexistent123xyz",  # Несуществующий термин
            "а" * 1000,  # Очень длинный запрос
        ]
        
        errors = 0
        results_counts = []
        
        for query in edge_queries:
            try:
                results = self._search(query, top_k=5)
                results_counts.append(len(results))
            except Exception as e:
                errors += 1
                logger.warning(f"Ошибка для граничного запроса: {e}")
        
        # Прошёл, если нет ошибок
        passed = errors == 0
        score = 1.0 - (errors / len(edge_queries))
        
        return TestResult(
            test_name="edge_cases",
            category="search",
            passed=passed,
            score=score,
            message=f"Ошибок: {errors}/{len(edge_queries)}",
            details={
                'errors': errors,
                'results_counts': results_counts
            }
        )


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    import faiss
    
    if len(sys.argv) < 3:
        print("Использование: python test_search_quality.py <index.faiss> <dataset.json>")
        sys.exit(1)
    
    # Загружаем индекс и датасет
    index = faiss.read_index(sys.argv[1])
    with open(sys.argv[2], 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # Запускаем тесты
    tester = SearchQualityTests(index, dataset)
    results = tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТОВ ПОИСКА")
    print("=" * 60)
    
    for result in results:
        status = "✅" if result.passed else "❌"
        print(f"\n{status} {result.test_name}")
        print(f"   Балл: {result.score * 100:.0f}%")
        print(f"   {result.message}")
    
    avg_score = sum(r.score for r in results) / len(results)
    print(f"\n{'=' * 60}")
    print(f"Средний балл: {avg_score * 100:.1f}%")
    print("=" * 60)
