"""
Главный модуль системы тестирования качества RAG-баз.

Объединяет все тесты и предоставляет единый интерфейс.
"""

import json
import logging
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

# Добавляем родительскую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

@dataclass
class TestResult:
    """Результат одного теста."""
    test_name: str
    category: str
    passed: bool
    score: float  # 0.0 - 1.0
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CategoryResult:
    """Результат категории тестов."""
    category: str
    weight: float
    score: float  # 0 - 100
    passed: bool
    tests: List[TestResult] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class TestReport:
    """Полный отчёт тестирования."""
    db_path: str
    total_score: float  # 0 - 100
    passed: bool
    threshold: float
    categories: Dict[str, CategoryResult] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# ГЛАВНЫЙ КЛАСС
# ============================================================================

class RAGQualityTester:
    """
    Система тестирования качества RAG-баз.
    
    Категории тестов:
    - Structure: целостность файлов
    - Chunks: качество чанков
    - Search: качество поиска
    - Answers: качество ответов
    - Coverage: покрытие контента
    
    Пример использования:
        tester = RAGQualityTester(db_path="./output/vector_db")
        report = tester.run_all_tests()
        print(f"Оценка: {report.total_score}/100")
    """
    
    def __init__(
        self,
        db_path: str = None,
        config_path: str = None,
        api_key: str = None,
        llm_model: str = "gpt-4o-mini"
    ):
        """
        Инициализация тестировщика.
        
        Args:
            db_path: Путь к векторной БД.
            config_path: Путь к конфигурации.
            api_key: API ключ OpenAI.
            llm_model: Модель LLM для оценки.
        """
        self.db_path = Path(db_path) if db_path else None
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.llm_model = llm_model
        
        # Загружаем конфигурацию
        self.config = self._load_config(config_path)
        
        # Состояние
        self.index = None
        self.dataset = None
        self.metadata = None
        self._loaded = False
        
        # Результаты
        self.report: Optional[TestReport] = None
        
        # История
        self.history_file = Path(self.config['general']['history_file'])
        
        logger.info(f"RAGQualityTester инициализирован (threshold={self.config['general']['threshold']}%)")
    
    def _load_config(self, config_path: str = None) -> Dict:
        """Загружает конфигурацию."""
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Конфигурация загружена: {config_path}")
            return config
        except Exception as e:
            logger.warning(f"Ошибка загрузки конфигурации: {e}, используется default")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Конфигурация по умолчанию."""
        return {
            'general': {
                'version': '1.0.0',
                'threshold': 80,
                'save_history': True,
                'history_file': 'test_history.json'
            },
            'weights': {
                'structure': 0.10,
                'chunks': 0.25,
                'search': 0.30,
                'answers': 0.25,
                'coverage': 0.10
            },
            'chunk_tests': {
                'min_size': 100,
                'max_size': 1000,
                'max_duplicates_percent': 5
            },
            'search_tests': {
                'top_k_values': [5, 10, 20],
                'precision_threshold': 0.7,
                'recall_threshold': 0.7
            },
            'answer_tests': {
                'correctness_threshold': 0.7,
                'groundedness_threshold': 0.7
            },
            'coverage_tests': {
                'topic_coverage_threshold': 0.8
            },
            'llm': {
                'model': 'gpt-4o-mini',
                'temperature': 0.1
            },
            'api': {
                'base_url': 'https://openai.api.proxyapi.ru/v1'
            }
        }
    
    # ------------------------------------------------------------------------
    # ЗАГРУЗКА БАЗЫ
    # ------------------------------------------------------------------------
    
    def load_database(self, db_path: str = None) -> bool:
        """
        Загружает векторную БД.
        
        Args:
            db_path: Путь к БД (опционально).
        
        Returns:
            True при успехе.
        """
        if db_path:
            self.db_path = Path(db_path)
        
        if not self.db_path:
            logger.error("Путь к БД не указан")
            return False
        
        logger.info(f"Загрузка БД: {self.db_path}")
        
        try:
            import faiss
            
            # Загружаем индекс
            index_file = self.db_path / "index.faiss"
            if index_file.exists():
                self.index = faiss.read_index(str(index_file))
                logger.info(f"Индекс загружен: {self.index.ntotal} векторов")
            else:
                logger.error(f"Индекс не найден: {index_file}")
                return False
            
            # Загружаем датасет
            dataset_file = self.db_path / "dataset.json"
            if dataset_file.exists():
                with open(dataset_file, 'r', encoding='utf-8') as f:
                    self.dataset = json.load(f)
                logger.info(f"Датасет загружен: {len(self.dataset)} чанков")
            else:
                logger.error(f"Датасет не найден: {dataset_file}")
                return False
            
            # Загружаем метаданные
            metadata_file = self.db_path / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"Метаданные: {self.metadata.get('embedding_model')}")
            
            self._loaded = True
            return True
            
        except ImportError:
            logger.error("FAISS не установлен: pip install faiss-cpu")
            return False
        except Exception as e:
            logger.error(f"Ошибка загрузки БД: {e}")
            return False
    
    def is_loaded(self) -> bool:
        """Проверяет, загружена ли БД."""
        return self._loaded and self.index is not None and self.dataset is not None
    
    # ------------------------------------------------------------------------
    # ЗАПУСК ТЕСТОВ
    # ------------------------------------------------------------------------
    
    def run_all_tests(
        self,
        progress_callback: callable = None
    ) -> TestReport:
        """
        Запускает все тесты.
        
        Args:
            progress_callback: Функция для обновления прогресса (category, progress).
        
        Returns:
            Полный отчёт тестирования.
        """
        import time
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("ЗАПУСК ВСЕХ ТЕСТОВ")
        logger.info("=" * 60)
        
        if not self.is_loaded():
            if not self.load_database():
                return TestReport(
                    db_path=str(self.db_path),
                    total_score=0,
                    passed=False,
                    threshold=self.config['general']['threshold'],
                    metadata={'error': 'База данных не загружена'}
                )
        
        # Создаём отчёт
        self.report = TestReport(
            db_path=str(self.db_path),
            total_score=0,
            passed=False,
            threshold=self.config['general']['threshold'],
            metadata={
                'total_vectors': self.index.ntotal if self.index else 0,
                'total_chunks': len(self.dataset) if self.dataset else 0,
                'embedding_model': self.metadata.get('embedding_model') if self.metadata else 'unknown'
            }
        )
        
        # Категории тестов
        categories = ['structure', 'chunks', 'search', 'answers', 'coverage']
        
        for i, category in enumerate(categories):
            if progress_callback:
                progress_callback(category, i / len(categories))
            
            logger.info(f"\n--- Тестирование: {category.upper()} ---")
            
            result = self._run_category_tests(category)
            self.report.categories[category] = result
        
        # Вычисляем общий балл
        self.report.total_score = self._calculate_total_score()
        self.report.passed = self.report.total_score >= self.report.threshold
        self.report.duration_seconds = round(time.time() - start_time, 2)
        
        # Сохраняем историю
        if self.config['general']['save_history']:
            self._save_history()
        
        logger.info(f"\n{'=' * 60}")
        logger.info(f"ИТОГОВАЯ ОЦЕНКА: {self.report.total_score:.1f}/100")
        logger.info(f"СТАТУС: {'✅ ПРОЙДЕНО' if self.report.passed else '❌ НЕ ПРОЙДЕНО'}")
        logger.info(f"ВРЕМЯ: {self.report.duration_seconds} сек")
        logger.info(f"{'=' * 60}")
        
        return self.report
    
    def _run_category_tests(self, category: str) -> CategoryResult:
        """Запускает тесты категории."""
        weight = self.config['weights'].get(category, 0.1)
        
        result = CategoryResult(
            category=category,
            weight=weight,
            score=0,
            passed=False,
            tests=[],
            recommendations=[]
        )
        
        try:
            if category == 'structure':
                tests = self._test_structure()
            elif category == 'chunks':
                tests = self._test_chunks()
            elif category == 'search':
                tests = self._test_search()
            elif category == 'answers':
                tests = self._test_answers()
            elif category == 'coverage':
                tests = self._test_coverage()
            else:
                tests = []
            
            result.tests = tests
            
            # Вычисляем балл категории
            if tests:
                passed_count = sum(1 for t in tests if t.passed)
                result.score = (passed_count / len(tests)) * 100
                result.passed = result.score >= self.config['general']['threshold']
            
            # Генерируем рекомендации
            result.recommendations = self._generate_recommendations(category, tests)
            
        except Exception as e:
            logger.error(f"Ошибка тестирования {category}: {e}")
            result.recommendations.append(f"Ошибка: {str(e)}")
        
        return result
    
    # ------------------------------------------------------------------------
    # ТЕСТЫ СТРУКТУРЫ
    # ------------------------------------------------------------------------
    
    def _test_structure(self) -> List[TestResult]:
        """Тесты целостности структуры."""
        tests = []
        
        # Тест 1: Индекс существует
        index_file = self.db_path / "index.faiss"
        tests.append(TestResult(
            test_name="index_exists",
            category="structure",
            passed=index_file.exists(),
            score=1.0 if index_file.exists() else 0.0,
            message=f"Индекс {'найден' if index_file.exists() else 'не найден'}",
            details={'path': str(index_file)}
        ))
        
        # Тест 2: Датасет существует
        dataset_file = self.db_path / "dataset.json"
        tests.append(TestResult(
            test_name="dataset_exists",
            category="structure",
            passed=dataset_file.exists(),
            score=1.0 if dataset_file.exists() else 0.0,
            message=f"Датасет {'найден' if dataset_file.exists() else 'не найден'}",
            details={'path': str(dataset_file)}
        ))
        
        # Тест 3: Метаданные существуют
        metadata_file = self.db_path / "metadata.json"
        tests.append(TestResult(
            test_name="metadata_exists",
            category="structure",
            passed=metadata_file.exists(),
            score=1.0 if metadata_file.exists() else 0.0,
            message=f"Метаданные {'найдены' if metadata_file.exists() else 'не найдены'}",
            details={'path': str(metadata_file)}
        ))
        
        # Тест 4: Размер индекса совпадает с датасетом
        if self.index and self.dataset:
            vectors_match = self.index.ntotal == len(self.dataset)
            tests.append(TestResult(
                test_name="vectors_count_match",
                category="structure",
                passed=vectors_match,
                score=1.0 if vectors_match else 0.0,
                message=f"Векторов: {self.index.ntotal}, чанков: {len(self.dataset)}",
                details={
                    'vectors': self.index.ntotal,
                    'chunks': len(self.dataset)
                }
            ))
        
        # Тест 5: Размерность векторов
        if self.index:
            dim = self.index.d
            expected_dim = 1536  # text-embedding-3-small
            dim_ok = dim == expected_dim
            tests.append(TestResult(
                test_name="embedding_dimension",
                category="structure",
                passed=dim_ok,
                score=1.0 if dim_ok else 0.5,
                message=f"Размерность: {dim} {'(OK)' if dim_ok else f'(ожидалось {expected_dim})'}",
                details={'dimension': dim, 'expected': expected_dim}
            ))
        
        return tests
    
    # ------------------------------------------------------------------------
    # ТЕСТЫ ЧАНКОВ
    # ------------------------------------------------------------------------
    
    def _test_chunks(self) -> List[TestResult]:
        """Тесты качества чанков."""
        from Testing_vector_RAG_base.test_chunk_quality import ChunkQualityTests
        
        tester = ChunkQualityTests(
            dataset=self.dataset,
            config=self.config['chunk_tests']
        )
        
        return tester.run_all_tests()
    
    # ------------------------------------------------------------------------
    # ТЕСТЫ ПОИСКА
    # ------------------------------------------------------------------------
    
    def _test_search(self) -> List[TestResult]:
        """Тесты качества поиска."""
        from Testing_vector_RAG_base.test_search_quality import SearchQualityTests
        
        tester = SearchQualityTests(
            index=self.index,
            dataset=self.dataset,
            api_key=self.api_key,
            llm_model=self.llm_model,
            config=self.config['search_tests'],
            api_base=self.config['api']['base_url']
        )
        
        return tester.run_all_tests()
    
    # ------------------------------------------------------------------------
    # ТЕСТЫ ОТВЕТОВ
    # ------------------------------------------------------------------------
    
    def _test_answers(self) -> List[TestResult]:
        """Тесты качества ответов."""
        from Testing_vector_RAG_base.test_answer_quality import AnswerQualityTests
        
        tester = AnswerQualityTests(
            index=self.index,
            dataset=self.dataset,
            api_key=self.api_key,
            llm_model=self.llm_model,
            config=self.config['answer_tests'],
            api_base=self.config['api']['base_url']
        )
        
        return tester.run_all_tests()
    
    # ------------------------------------------------------------------------
    # ТЕСТЫ ПОКРЫТИЯ
    # ------------------------------------------------------------------------
    
    def _test_coverage(self) -> List[TestResult]:
        """Тесты покрытия контента."""
        from Testing_vector_RAG_base.test_coverage import CoverageTests
        
        tester = CoverageTests(
            dataset=self.dataset,
            config=self.config['coverage_tests']
        )
        
        return tester.run_all_tests()
    
    # ------------------------------------------------------------------------
    # РАСЧЁТЫ
    # ------------------------------------------------------------------------
    
    def _calculate_total_score(self) -> float:
        """Вычисляет общий балл."""
        if not self.report or not self.report.categories:
            return 0.0
        
        total = 0.0
        for category, result in self.report.categories.items():
            weight = self.config['weights'].get(category, 0.1)
            total += result.score * weight
        
        return round(total, 1)
    
    def _generate_recommendations(
        self,
        category: str,
        tests: List[TestResult]
    ) -> List[str]:
        """Генерирует рекомендации по результатам тестов."""
        recommendations = []
        
        for test in tests:
            if not test.passed:
                # Специфические рекомендации
                if test.test_name == "chunk_sizes":
                    recommendations.append("Оптимизируйте размер чанков (рекомендуется 300-600 символов)")
                elif test.test_name == "empty_chunks":
                    recommendations.append("Удалите пустые чанки из датасета")
                elif test.test_name == "duplicates":
                    recommendations.append("Удалите дубликаты чанков для улучшения качества поиска")
                elif test.test_name == "precision_at_k":
                    recommendations.append("Улучшите качество эмбеддингов или увеличьте top_k")
                elif test.test_name == "recall_at_k":
                    recommendations.append("Увеличьте top_k или улучшите перекрытие чанков")
                elif test.test_name == "latency":
                    recommendations.append("Оптимизируйте индекс (IVF, PQ) для ускорения поиска")
                elif test.test_name == "groundedness":
                    recommendations.append("Улучшите контекст для генерации ответов")
                elif test.test_name == "hallucinations":
                    recommendations.append("Настройте промпты для уменьшения галлюцинаций")
                else:
                    recommendations.append(f"Тест '{test.test_name}' не пройден: {test.message}")
        
        return recommendations
    
    # ------------------------------------------------------------------------
    # ИСТОРИЯ
    # ------------------------------------------------------------------------
    
    def _save_history(self) -> None:
        """Сохраняет историю тестов."""
        if not self.report:
            return
        
        history = self._load_history()
        
        entry = {
            'timestamp': self.report.timestamp,
            'db_path': self.report.db_path,
            'total_score': self.report.total_score,
            'passed': self.report.passed,
            'threshold': self.report.threshold,
            'duration_seconds': self.report.duration_seconds,
            'categories': {
                cat: {
                    'score': res.score,
                    'passed': res.passed
                }
                for cat, res in self.report.categories.items()
            }
        }
        
        history.append(entry)
        
        # Ограничиваем историю 100 записями
        history = history[-100:]
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            logger.info(f"История сохранена: {self.history_file}")
        except Exception as e:
            logger.error(f"Ошибка сохранения истории: {e}")
    
    def _load_history(self) -> List[Dict]:
        """Загружает историю тестов."""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def get_history(self) -> List[Dict]:
        """Возвращает историю тестов."""
        return self._load_history()
    
    # ------------------------------------------------------------------------
    # ЭКСПОРТ
    # ------------------------------------------------------------------------
    
    def export_report(
        self,
        output_path: str,
        format: str = "markdown"
    ) -> str:
        """
        Экспортирует отчёт.
        
        Args:
            output_path: Путь к файлу.
            format: Формат (markdown, json, html).
        
        Returns:
            Путь к созданному файлу.
        """
        from .generate_report import ReportGenerator
        
        generator = ReportGenerator(self.report, self.config)
        
        if format == "json":
            return generator.export_json(output_path)
        elif format == "html":
            return generator.export_html(output_path)
        else:
            return generator.export_markdown(output_path)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Тестирование качества RAG-базы")
    parser.add_argument("--db-path", required=True, help="Путь к векторной БД")
    parser.add_argument("--config", help="Путь к конфигурации")
    parser.add_argument("--report", default="report.md", help="Путь к отчёту")
    parser.add_argument("--format", choices=["markdown", "json", "html"], default="markdown")
    
    args = parser.parse_args()
    
    # Запускаем тесты
    tester = RAGQualityTester(
        db_path=args.db_path,
        config_path=args.config
    )
    
    report = tester.run_all_tests()
    
    print(f"\nРезультат: {report.total_score}/100")
    status = "ПРОЙДЕНО" if report.passed else "НЕ ПРОЙДЕНО"
    print(f"Статус: {status}")
    
    # Экспортируем отчёт
    tester.export_report(args.report, args.format)
    print(f"Отчёт: {args.report}")
