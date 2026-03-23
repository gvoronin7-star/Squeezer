"""
Тесты качества чанков.

Метрики:
- Размер чанков
- Пустые чанки
- Дубликаты
- Полнота метаданных
- Когерентность
"""

import json
import logging
from collections import Counter
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

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


class ChunkQualityTests:
    """
    Тесты качества чанков.
    
    Пример использования:
        tester = ChunkQualityTests(dataset=dataset)
        results = tester.run_all_tests()
    """
    
    def __init__(
        self,
        dataset: List[Dict],
        config: Dict = None
    ):
        """
        Инициализация.
        
        Args:
            dataset: Список чанков.
            config: Конфигурация тестов.
        """
        self.dataset = dataset or []
        self.config = config or {}
        
        # Параметры по умолчанию
        self.min_size = self.config.get('min_size', 100)
        self.max_size = self.config.get('max_size', 1000)
        self.max_duplicates_percent = self.config.get('max_duplicates_percent', 5)
        self.required_metadata = self.config.get('required_metadata', [
            'chunk_id', 'source', 'page_number'
        ])
        self.coherence_threshold = self.config.get('coherence_threshold', 0.7)
    
    def run_all_tests(self) -> List[TestResult]:
        """Запускает все тесты чанков."""
        results = []
        
        results.append(self.test_chunk_sizes())
        results.append(self.test_empty_chunks())
        results.append(self.test_duplicates())
        results.append(self.test_metadata_completeness())
        results.append(self.test_text_quality())
        results.append(self.test_overlap_quality())
        
        return results
    
    # ------------------------------------------------------------------------
    # ТЕСТ РАЗМЕРА ЧАНКОВ
    # ------------------------------------------------------------------------
    
    def test_chunk_sizes(self) -> TestResult:
        """
        Проверяет распределение размеров чанков.
        
        Критерии:
        - Средний размер: 300-600 символов
        - Минимум: 100 символов
        - Максимум: 1000 символов
        """
        if not self.dataset:
            return TestResult(
                test_name="chunk_sizes",
                category="chunks",
                passed=False,
                score=0.0,
                message="Датасет пуст",
                details={}
            )
        
        sizes = [len(chunk.get('text', '')) for chunk in self.dataset]
        
        avg_size = sum(sizes) / len(sizes)
        min_size = min(sizes)
        max_size = max(sizes)
        
        # Распределение по категориям
        too_small = sum(1 for s in sizes if s < self.min_size)
        too_large = sum(1 for s in sizes if s > self.max_size)
        optimal = sum(1 for s in sizes if self.min_size <= s <= self.max_size)
        
        # Оценка
        optimal_percent = (optimal / len(sizes)) * 100
        
        # Прошёл, если большинство чанков оптимального размера
        passed = optimal_percent >= 70
        
        # Балл зависит от процента оптимальных
        score = optimal_percent / 100
        
        details = {
            'total_chunks': len(sizes),
            'avg_size': round(avg_size, 1),
            'min_size': min_size,
            'max_size': max_size,
            'optimal_count': optimal,
            'optimal_percent': round(optimal_percent, 1),
            'too_small_count': too_small,
            'too_large_count': too_large
        }
        
        message = f"Средний: {avg_size:.0f}, оптимальных: {optimal_percent:.1f}%"
        if too_small > 0:
            message += f", слишком маленьких: {too_small}"
        if too_large > 0:
            message += f", слишком больших: {too_large}"
        
        return TestResult(
            test_name="chunk_sizes",
            category="chunks",
            passed=passed,
            score=score,
            message=message,
            details=details
        )
    
    # ------------------------------------------------------------------------
    # ТЕСТ ПУСТЫХ ЧАНКОВ
    # ------------------------------------------------------------------------
    
    def test_empty_chunks(self) -> TestResult:
        """
        Проверяет наличие пустых чанков.
        
        Критерий: пустых чанков должно быть 0.
        """
        if not self.dataset:
            return TestResult(
                test_name="empty_chunks",
                category="chunks",
                passed=False,
                score=0.0,
                message="Датасет пуст",
                details={}
            )
        
        empty_indices = []
        for i, chunk in enumerate(self.dataset):
            text = chunk.get('text', '').strip()
            if not text:
                empty_indices.append(i)
        
        empty_count = len(empty_indices)
        empty_percent = (empty_count / len(self.dataset)) * 100
        
        # Прошёл только если нет пустых
        passed = empty_count == 0
        score = 1.0 if passed else max(0, 1.0 - empty_percent / 100)
        
        return TestResult(
            test_name="empty_chunks",
            category="chunks",
            passed=passed,
            score=score,
            message=f"Пустых чанков: {empty_count} ({empty_percent:.1f}%)",
            details={
                'empty_count': empty_count,
                'empty_percent': round(empty_percent, 2),
                'empty_indices': empty_indices[:10]  # Первые 10
            }
        )
    
    # ------------------------------------------------------------------------
    # ТЕСТ ДУБЛИКАТОВ
    # ------------------------------------------------------------------------
    
    def test_duplicates(self) -> TestResult:
        """
        Проверяет наличие дубликатов чанков.
        
        Критерий: дубликатов должно быть < 5%.
        """
        if not self.dataset:
            return TestResult(
                test_name="duplicates",
                category="chunks",
                passed=False,
                score=0.0,
                message="Датасет пуст",
                details={}
            )
        
        # Подсчитываем хеши текстов
        text_hashes = []
        for chunk in self.dataset:
            text = chunk.get('text', '').strip()
            # Простой хеш - первые 100 символов + длина
            h = hash(text[:100] + str(len(text)))
            text_hashes.append(h)
        
        # Находим дубликаты
        hash_counts = Counter(text_hashes)
        duplicates = sum(count - 1 for count in hash_counts.values() if count > 1)
        duplicate_percent = (duplicates / len(self.dataset)) * 100
        
        # Прошёл, если дубликатов меньше порога
        passed = duplicate_percent < self.max_duplicates_percent
        score = max(0, 1.0 - duplicate_percent / self.max_duplicates_percent)
        
        return TestResult(
            test_name="duplicates",
            category="chunks",
            passed=passed,
            score=score,
            message=f"Дубликатов: {duplicates} ({duplicate_percent:.1f}%)",
            details={
                'duplicate_count': duplicates,
                'duplicate_percent': round(duplicate_percent, 2),
                'unique_count': len(hash_counts)
            }
        )
    
    # ------------------------------------------------------------------------
    # ТЕСТ МЕТАДАННЫХ
    # ------------------------------------------------------------------------
    
    def test_metadata_completeness(self) -> TestResult:
        """
        Проверяет полноту метаданных.
        
        Критерий: все обязательные поля должны быть заполнены.
        """
        if not self.dataset:
            return TestResult(
                test_name="metadata_completeness",
                category="chunks",
                passed=False,
                score=0.0,
                message="Датасет пуст",
                details={}
            )
        
        # Подсчитываем заполненность каждого поля
        field_counts = {field: 0 for field in self.required_metadata}
        
        for chunk in self.dataset:
            metadata = chunk.get('metadata', {})
            for field in self.required_metadata:
                if field in metadata and metadata[field] is not None:
                    field_counts[field] += 1
                elif field in chunk and chunk[field] is not None:
                    field_counts[field] += 1
        
        # Вычисляем полноту
        completeness = {}
        for field, count in field_counts.items():
            completeness[field] = (count / len(self.dataset)) * 100
        
        # Средняя полнота
        avg_completeness = sum(completeness.values()) / len(completeness)
        
        # Прошёл, если все поля заполнены на 100%
        passed = all(c == 100 for c in completeness.values())
        score = avg_completeness / 100
        
        # Формируем сообщение
        missing_fields = [f for f, c in completeness.items() if c < 100]
        if missing_fields:
            message = f"Не все поля заполнены: {', '.join(missing_fields)}"
        else:
            message = "Все обязательные поля заполнены"
        
        return TestResult(
            test_name="metadata_completeness",
            category="chunks",
            passed=passed,
            score=score,
            message=message,
            details={
                'completeness': completeness,
                'avg_completeness': round(avg_completeness, 1),
                'missing_fields': missing_fields
            }
        )
    
    # ------------------------------------------------------------------------
    # ТЕСТ КАЧЕСТВА ТЕКСТА
    # ------------------------------------------------------------------------
    
    def test_text_quality(self) -> TestResult:
        """
        Проверяет качество текста в чанках.
        
        Критерии:
        - Нет артефактов OCR
        - Нет HTML-тегов
        - Нет избытка спецсимволов
        """
        if not self.dataset:
            return TestResult(
                test_name="text_quality",
                category="chunks",
                passed=False,
                score=0.0,
                message="Датасет пуст",
                details={}
            )
        
        import re
        
        issues = {
            'html_tags': 0,
            'ocr_artifacts': 0,
            'excess_whitespace': 0,
            'control_chars': 0
        }
        
        for chunk in self.dataset:
            text = chunk.get('text', '')
            
            # HTML теги
            if re.search(r'<[^>]+>', text):
                issues['html_tags'] += 1
            
            # OCR артефакты (частые ошибки)
            if re.search(r'[|\[\]{}]{3,}', text):
                issues['ocr_artifacts'] += 1
            
            # Избыток пробелов
            if re.search(r' {3,}', text) or re.search(r'\n{4,}', text):
                issues['excess_whitespace'] += 1
            
            # Управляющие символы
            if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', text):
                issues['control_chars'] += 1
        
        # Подсчитываем проблемные чанки
        total_issues = sum(issues.values())
        issue_percent = (total_issues / len(self.dataset)) * 100
        
        # Прошёл, если проблем< 10%
        passed = issue_percent < 10
        score = max(0, 1.0 - issue_percent / 100)
        
        return TestResult(
            test_name="text_quality",
            category="chunks",
            passed=passed,
            score=score,
            message=f"Проблемных чанков: {total_issues} ({issue_percent:.1f}%)",
            details={
                'issues': issues,
                'issue_percent': round(issue_percent, 2)
            }
        )
    
    # ------------------------------------------------------------------------
    # ТЕСТ КАЧЕСТВА ПЕРЕКРЫТИЯ
    # ------------------------------------------------------------------------
    
    def test_overlap_quality(self) -> TestResult:
        """
        Проверяет качество перекрытия между соседними чанками.
        
        Критерий: перекрытие должно обеспечивать связность контекста.
        """
        if not self.dataset or len(self.dataset) < 2:
            return TestResult(
                test_name="overlap_quality",
                category="chunks",
                passed=True,
                score=1.0,
                message="Недостаточно чанков для проверки",
                details={}
            )
        
        # Проверяем перекрытие между соседними чанками одной страницы
        overlaps = []
        
        # Группируем по страницам
        from collections import defaultdict
        by_page = defaultdict(list)
        
        for i, chunk in enumerate(self.dataset):
            page = chunk.get('metadata', {}).get('page_number', 0)
            # Преобразуем в число если это строка
            try:
                page = int(page) if page is not None else 0
            except (ValueError, TypeError):
                page = 0
            by_page[page].append((i, chunk))
        
        # Проверяем перекрытие в каждой странице
        for page, chunks in by_page.items():
            if len(chunks) < 2:
                continue
            
            # Сортируем по chunk_id (преобразуем в число)
            def get_sort_key(item):
                idx, chunk = item
                chunk_id = chunk.get('metadata', {}).get('chunk_id', idx)
                try:
                    return int(chunk_id) if chunk_id is not None else idx
                except (ValueError, TypeError):
                    return idx
            
            chunks.sort(key=get_sort_key)
            
            for i in range(len(chunks) - 1):
                text1 = chunks[i][1].get('text', '')
                text2 = chunks[i + 1][1].get('text', '')
                
                # Ищем общие слова в конце первого и начале второго
                words1 = text1.split()[-20:]  # Последние 20 слов
                words2 = text2.split()[:20]   # Первые 20 слов
                
                common = set(words1) & set(words2)
                if common:
                    overlaps.append(len(common))
        
        if not overlaps:
            return TestResult(
                test_name="overlap_quality",
                category="chunks",
                passed=True,
                score=1.0,
                message="Перекрытие не требуется",
                details={'has_overlap': False}
            )
        
        avg_overlap = sum(overlaps) / len(overlaps)
        
        # Хорошее перекрытие: 3-10 общих слов
        good_overlap = sum(1 for o in overlaps if 3 <= o <= 10)
        good_percent = (good_overlap / len(overlaps)) * 100
        
        passed = good_percent >= 50
        score = good_percent / 100
        
        return TestResult(
            test_name="overlap_quality",
            category="chunks",
            passed=passed,
            score=score,
            message=f"Среднее перекрытие: {avg_overlap:.1f} слов, хорошее: {good_percent:.1f}%",
            details={
                'avg_overlap': round(avg_overlap, 1),
                'good_overlap_percent': round(good_percent, 1),
                'samples_checked': len(overlaps)
            }
        )


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python test_chunk_quality.py <dataset.json>")
        sys.exit(1)
    
    # Загружаем датасет
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # Запускаем тесты
    tester = ChunkQualityTests(dataset)
    results = tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТОВ ЧАНКОВ")
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
