"""
Тесты покрытия контента.

Метрики:
- Topic coverage (покрытие тем)
- Keyword coverage (покрытие ключевых слов)
- Question coverage (покрытие вопросов)
- Information density (плотность информации)
"""

import json
import logging
import re
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


class CoverageTests:
    """
    Тесты покрытия контента.
    
    Пример использования:
        tester = CoverageTests(dataset)
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
        self.topic_coverage_threshold = self.config.get('topic_coverage_threshold', 0.8)
        self.keyword_coverage_threshold = self.config.get('keyword_coverage_threshold', 0.7)
        self.question_coverage_threshold = self.config.get('question_coverage_threshold', 0.6)
        self.min_information_density = self.config.get('min_information_density', 0.5)
    
    def run_all_tests(self) -> List[TestResult]:
        """Запускает все тесты покрытия."""
        results = []
        
        results.append(self.test_topic_coverage())
        results.append(self.test_keyword_coverage())
        results.append(self.test_question_coverage())
        results.append(self.test_information_density())
        results.append(self.test_source_coverage())
        
        return results
    
    # ------------------------------------------------------------------------
    # ТЕСТ ПОКРЫТИЯ ТЕМ
    # ------------------------------------------------------------------------
    
    def test_topic_coverage(self) -> TestResult:
        """
        Проверяет покрытие тем в датасете.
        
        Извлекает потенциальные темы из текста и проверяет разнообразие.
        """
        if not self.dataset:
            return TestResult(
                test_name="topic_coverage",
                category="coverage",
                passed=False,
                score=0.0,
                message="Датасет пуст",
                details={}
            )
        
        # Извлекаем "темы" - существительные и ключевые фразы
        topics = []
        
        for chunk in self.dataset:
            text = chunk.get('text', '')
            
            # Простое извлечение: слова с заглавной буквы (потенциальные имена/термины)
            capitalized = re.findall(r'\b[А-ЯЁA-Z][а-яёa-z]{2,}\b', text)
            topics.extend(capitalized)
            
            # Слова после "раздел", "глава", "тема"
            section_topics = re.findall(
                r'(?:раздел|глава|тема|разделе|главе)\s+([А-ЯЁа-яё0-9\s]+)',
                text,
                re.IGNORECASE
            )
            topics.extend([t.strip() for t in section_topics if t.strip()])
        
            # Добавляем ключевые слова (существительные - слова длиной > 4 символов)
            words = re.findall(r'\b[а-яёa-z]{5,}\b', text.lower())
            topics.extend(words[:10])  # Топ-10 слов из чанка
        
        # Подсчитываем уникальные темы
        topic_counts = Counter(topics)
        unique_topics = len(topic_counts)
        
        # Оценка: больше уникальных тем = лучше покрытие
        # Нормализуем: 10+ уникальных тем на 100 чанков = отлично
        topics_per_100_chunks = (unique_topics / len(self.dataset)) * 100
        
        # Шкала:
        # 0-5 тем/100 чанков = 0-20%
        # 5-10 тем/100 чанков = 20-50%
        # 10+ тем/100 чанков = 50-100%
        
        if topics_per_100_chunks < 5:
            score = topics_per_100_chunks / 5 * 0.2
        elif topics_per_100_chunks < 10:
            score = 0.2 + (topics_per_100_chunks - 5) / 5 * 0.3
        else:
            score = min(1.0, 0.5 + (topics_per_100_chunks - 10) / 20 * 0.5)
        
        passed = score >= 0.5
        
        # Топ-10 тем
        top_topics = topic_counts.most_common(10)
        
        return TestResult(
            test_name="topic_coverage",
            category="coverage",
            passed=passed,
            score=score,
            message=f"Уникальных тем: {unique_topics} ({topics_per_100_chunks:.1f} на 100 чанков)",
            details={
                'unique_topics': unique_topics,
                'topics_per_100_chunks': round(topics_per_100_chunks, 1),
                'top_topics': top_topics
            }
        )

    # ------------------------------------------------------------------------
    # ТЕСТ ПОКРЫТИЯ КЛЮЧЕВЫХ СЛОВ
    # ------------------------------------------------------------------------

    def test_keyword_coverage(self) -> TestResult:
        """
        Проверяет покрытие ключевых слов.
        
        Анализирует распределение ключевых слов по чанкам.
        """
        if not self.dataset:
            return TestResult(
                test_name="keyword_coverage",
                category="coverage",
                passed=False,
                score=0.0,
                message="Датасет пуст",
                details={}
            )
        
        # Извлекаем все слова
        all_words = []
        chunk_words = []
        
        for chunk in self.dataset:
            text = chunk.get('text', '').lower()
            
            # Удаляем пунктуацию и разбиваем на слова
            words = re.findall(r'\b[а-яёa-z]{3,}\b', text)
            all_words.extend(words)
            chunk_words.append(set(words))
        
        # Подсчитываем частоту слов
        word_counts = Counter(all_words)
        
        # Определяем "ключевые слова" - слова в топ-20% по частоте
        total_unique = len(word_counts)
        top_threshold = max(10, int(total_unique * 0.2))  # Минимум 10 слов
        
        keywords = set([w for w, _ in word_counts.most_common(top_threshold)])
        
        # Сколько чанков содержат ключевые слова
        chunks_with_keywords = 0
        keyword_coverage_per_chunk = []
        
        for words_set in chunk_words:
            if not keywords:
                coverage = 0
            else:
                coverage = len(words_set & keywords) / len(keywords)
            keyword_coverage_per_chunk.append(coverage)
            
            if coverage > 0.1:  # Хотя бы 10% ключевых слов
                chunks_with_keywords += 1
        
        # Средний процент чанков, содержащих ключевые слова
        chunks_with_keywords_percent = (chunks_with_keywords / len(self.dataset)) * 100
        
        # Оценка: больше чанков с ключевыми словами = лучше
        # 70%+ чанков с ключевыми словами = отлично
        score = min(1.0, chunks_with_keywords_percent / 70)
        
        passed = score >= 0.5
        
        return TestResult(
            test_name="keyword_coverage",
            category="coverage",
            passed=passed,
            score=score,
            message=f"Чанков с ключевыми словами: {chunks_with_keywords_percent:.1f}%",
            details={
                'total_words': len(all_words),
                'unique_words': total_unique,
                'keywords_count': len(keywords),
                'chunks_with_keywords_percent': round(chunks_with_keywords_percent, 1)
            }
        )
    
        # Извлекаем все слова
        all_words = []
        chunk_words = []
        
        for chunk in self.dataset:
            text = chunk.get('text', '').lower()
            
            # Удаляем пунктуацию и разбиваем на слова
            words = re.findall(r'\b[а-яёa-z]{3,}\b', text)
            all_words.extend(words)
            chunk_words.append(set(words))
        
        # Подсчитываем частоту слов
        word_counts = Counter(all_words)
        
        # Определяем "ключевые слова" - слова в топ-20% по частоте
        total_unique = len(word_counts)
        top_threshold = int(total_unique * 0.2)
        
        keywords = set([w for w, _ in word_counts.most_common(top_threshold)])
        
        # Сколько чанков содержат ключевые слова
        chunks_with_keywords = 0
        keyword_coverage_per_chunk = []
        
        for words_set in chunk_words:
            coverage = len(words_set & keywords) / len(keywords) if keywords else 0
            keyword_coverage_per_chunk.append(coverage)
            
            if coverage > 0.1:  # Хотя бы 10% ключевых слов
                chunks_with_keywords += 1
        
        avg_coverage = sum(keyword_coverage_per_chunk) / len(keyword_coverage_per_chunk)
        
        passed = avg_coverage >= self.keyword_coverage_threshold
        score = avg_coverage
        
        return TestResult(
            test_name="keyword_coverage",
            category="coverage",
            passed=passed,
            score=score,
            message=f"Среднее покрытие ключевых слов: {avg_coverage:.2f}",
            details={
                'total_words': len(all_words),
                'unique_words': total_unique,
                'keywords_count': len(keywords),
                'avg_coverage': round(avg_coverage, 3)
            }
        )
    
    # ------------------------------------------------------------------------
    # ТЕСТ ПОКРЫТИЯ ВОПРОСОВ
    # ------------------------------------------------------------------------
    
    def test_question_coverage(self) -> TestResult:
        """
        Проверяет, содержит ли датасет ответы на типичные вопросы.
        
        Анализирует наличие вопросительных конструкций и ответов на них.
        """
        if not self.dataset:
            return TestResult(
                test_name="question_coverage",
                category="coverage",
                passed=False,
                score=0.0,
                message="Датасет пуст",
                details={}
            )
        
        # Ищем вопросительные конструкции
        question_patterns = [
            r'что\s+такое',
            r'как\s+(?:сделать|работает|настроить|использовать)',
            r'зачем\s+нужно',
            r'почему\s+',
            r'когда\s+',
            r'где\s+',
            r'какой\s+',
            r'сколько\s+',
            r'какие\s+',
            r'\?',  # Просто вопросительный знак
        ]
        
        found_questions = 0
        found_answers = 0
        total_text_length = 0
        
        for chunk in self.dataset:
            text = chunk.get('text', '')
            total_text_length += len(text)
            
            # Проверяем наличие вопросов
            has_question = False
            for pattern in question_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    found_questions += 1
                    has_question = True
                    break
            
            # Проверяем наличие ответов (предложения после "?")
            if '?' in text:
                parts = text.split('?')
                if len(parts) > 1 and len(parts[1].strip()) > 20:
                    found_answers += 1
        
        # Оценка на основе содержания
        # Если есть вопросы и ответы - хорошо
        # Если текст информативный (длинный) - тоже хорошо
        
        avg_chunk_size = total_text_length / len(self.dataset)
        
        # Комбинированная оценка
        # 1. Наличие вопросов/ответов
        qa_score = min(1.0, (found_questions + found_answers) / (len(self.dataset) * 0.5))
        
        # 2. Информативность (средний размер чанка)
        # Оптимально: 300-600 символов
        if avg_chunk_size < 100:
            info_score = avg_chunk_size / 100
        elif avg_chunk_size > 1000:
            info_score = 1000 / avg_chunk_size
        else:
            info_score = 1.0
        
        # Итоговая оценка (70% информативность, 30% вопросы)
        score = info_score * 0.7 + qa_score * 0.3
        
        passed = score >= 0.5
        
        return TestResult(
            test_name="question_coverage",
            category="coverage",
            passed=passed,
            score=score,
            message=f"Средний размер чанка: {avg_chunk_size:.0f} символов, вопросов: {found_questions}",
            details={
                'questions_found': found_questions,
                'answers_found': found_answers,
                'avg_chunk_size': round(avg_chunk_size, 0),
                'qa_score': round(qa_score, 2),
                'info_score': round(info_score, 2)
            }
        )

    # ------------------------------------------------------------------------
    # ТЕСТ ПЛОТНОСТИ ИНФОРМАЦИИ
    # ------------------------------------------------------------------------

    def test_information_density(self) -> TestResult:
        """
        Проверяет плотность информации в чанках.
        
        Анализирует соотношение значимой информации к общему объёму.
        """
        if not self.dataset:
            return TestResult(
                test_name="information_density",
                category="coverage",
                passed=False,
                score=0.0,
                message="Датасет пуст",
                details={}
            )
        
        densities = []
        
        for chunk in self.dataset:
            text = chunk.get('text', '')
            
            if not text:
                continue
            
            # Метрики плотности
            total_chars = len(text)
            
            # Удаляем "шум" (пробелы, переносы, пунктуация)
            noise_chars = len(re.findall(r'[\s\n\r\t.,;:!?()\[\]{}"\'-]', text))
            
            # Значимые символы
            meaningful_chars = total_chars - noise_chars
            
            # Плотность = значимые / общие
            density = meaningful_chars / total_chars if total_chars > 0 else 0
            
            densities.append(density)
        
        if not densities:
            return TestResult(
                test_name="information_density",
                category="coverage",
                passed=False,
                score=0.0,
                message="Нет данных для анализа",
                details={}
            )
        
        avg_density = sum(densities) / len(densities)
        
        passed = avg_density >= self.min_information_density
        score = avg_density
        
        return TestResult(
            test_name="information_density",
            category="coverage",
            passed=passed,
            score=score,
            message=f"Средняя плотность: {avg_density:.2f}",
            details={
                'avg_density': round(avg_density, 3),
                'min_density': round(min(densities), 3),
                'max_density': round(max(densities), 3)
            }
        )

    # ------------------------------------------------------------------------
    # ТЕСТ ПОКРЫТИЯ ИСТОЧНИКОВ
    # ------------------------------------------------------------------------

    def test_source_coverage(self) -> TestResult:
        """
        Проверяет покрытие источников (страниц, файлов).
        
        Анализирует распределение чанков по источникам.
        """
        if not self.dataset:
            return TestResult(
                test_name="source_coverage",
                category="coverage",
                passed=False,
                score=0.0,
                message="Датасет пуст",
                details={}
            )
        
        # Группируем по источникам
        sources = {}
        pages = {}
        
        for chunk in self.dataset:
            metadata = chunk.get('metadata', {})
            
            source = metadata.get('source', 'unknown')
            page = metadata.get('page_number', 'unknown')
            
            sources[source] = sources.get(source, 0) + 1
            pages[page] = pages.get(page, 0) + 1
        
        # Оценка на основе распределения
        # Хорошее покрытие: чанки распределены по многим страницам
        unique_pages = len(pages)
        unique_sources = len(sources)
        
        # Среднее количество чанков на страницу
        avg_chunks_per_page = len(self.dataset) / unique_pages if unique_pages > 0 else 0
        
        # Идеально: 3-10 чанков на страницу
        if avg_chunks_per_page < 3:
            page_score = avg_chunks_per_page / 3
        elif avg_chunks_per_page > 10:
            page_score = 10 / avg_chunks_per_page
        else:
            page_score = 1.0
        
        score = page_score
        
        passed = score >= 0.7
        
        return TestResult(
            test_name="source_coverage",
            category="coverage",
            passed=passed,
            score=score,
            message=f"Страниц: {unique_pages}, источников: {unique_sources}",
            details={
                'unique_pages': unique_pages,
                'unique_sources': unique_sources,
                'avg_chunks_per_page': round(avg_chunks_per_page, 1),
                'pages_distribution': dict(list(pages.items())[:10])
            }
        )


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python test_coverage.py <dataset.json>")
        sys.exit(1)
    
    # Загружаем датасет
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # Запускаем тесты
    tester = CoverageTests(dataset)
    results = tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТОВ ПОКРЫТИЯ")
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
