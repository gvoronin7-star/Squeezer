"""
Генератор отчётов тестирования.

Форматы:
- Markdown
- HTML
- JSON
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Добавляем родительскую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Генератор отчётов.
    
    Пример использования:
        generator = ReportGenerator(report, config)
        generator.export_markdown("report.md")
        generator.export_html("report.html")
    """
    
    def __init__(self, report, config: Dict = None):
        """
        Инициализация.
        
        Args:
            report: Объект TestReport.
            config: Конфигурация.
        """
        self.report = report
        self.config = config or {}
    
    def export_markdown(self, output_path: str) -> str:
        """Экспортирует отчёт в Markdown."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown())
        
        logger.info(f"Markdown отчёт сохранён: {path}")
        return str(path)
    
    def export_html(self, output_path: str) -> str:
        """Экспортирует отчёт в HTML."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self._generate_html())
        
        logger.info(f"HTML отчёт сохранён: {path}")
        return str(path)
    
    def export_json(self, output_path: str) -> str:
        """Экспортирует отчёт в JSON."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON отчёт сохранён: {path}")
        return str(path)
    
    # ------------------------------------------------------------------------
    # GENERATORS
    # ------------------------------------------------------------------------
    
    def _generate_markdown(self) -> str:
        """Генерирует Markdown контент."""
        lines = []
        
        # Заголовок
        lines.append(f"# Отчёт о качестве RAG-базы\n")
        lines.append(f"**Дата:** {self.report.timestamp}\n")
        lines.append(f"**Путь:** `{self.report.db_path}`\n")
        lines.append(f"**Время выполнения:** {self.report.duration_seconds} сек\n")
        
        # Общая оценка
        status = "✅ ПРОЙДЕНО" if self.report.passed else "❌ НЕ ПРОЙДЕНО"
        lines.append(f"\n## Общая оценка: {self.report.total_score:.1f}/100 {status}\n")
        
        # Порог
        lines.append(f"**Порог качества:** {self.report.threshold}%\n")
        
        # Сводка по категориям
        lines.append("\n## Сводка по категориям\n")
        lines.append("| Категория | Балл | Статус | Вес |")
        lines.append("|-----------|------|--------|-----|")
        
        for cat, result in self.report.categories.items():
            cat_status = "✅" if result.passed else "❌"
            lines.append(f"| {cat.capitalize()} | {result.score:.1f}/100 | {cat_status} | {result.weight * 100:.0f}% |")
        
        # Детали по категориям
        for cat, result in self.report.categories.items():
            lines.append(f"\n## {cat.capitalize()} ({result.score:.1f}/100)\n")
            
            # Тесты
            lines.append("### Тесты\n")
            lines.append("| Тест | Статус | Балл | Результат |")
            lines.append("|------|--------|------|----------|")
            
            for test in result.tests:
                test_status = "✅" if test.passed else "❌"
                lines.append(f"| {test.test_name} | {test_status} | {test.score * 100:.0f}% | {test.message} |")
            
            # Рекомендации
            if result.recommendations:
                lines.append("\n### Рекомендации\n")
                for rec in result.recommendations:
                    lines.append(f"- {rec}")
        
        # Метаданные
        if self.report.metadata:
            lines.append("\n## Метаданные базы\n")
            for key, value in self.report.metadata.items():
                lines.append(f"- **{key}:** {value}")
        
        lines.append(f"\n---\n*Отчёт сгенерирован автоматически*\n")
        
        return "\n".join(lines)
    
    def _generate_html(self) -> str:
        """Генерирует HTML контент."""
        # CSS стили
        css = """
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
            h2 { color: #444; margin-top: 30px; }
            .score-card { background: white; border-radius: 10px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .score-big { font-size: 48px; font-weight: bold; text-align: center; }
            .passed { color: #4CAF50; }
            .failed { color: #F44336; }
            table { width: 100%; border-collapse: collapse; margin: 15px 0; background: white; border-radius: 5px; overflow: hidden; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
            th { background: #4CAF50; color: white; }
            tr:hover { background: #f9f9f9; }
            .progress-bar { height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden; }
            .progress-fill { height: 100%; transition: width 0.3s; }
            .recommendations { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }
            .metadata { background: #e3f2fd; padding: 15px; border-radius: 5px; }
        </style>
        """
        
        # Основной контент
        status_class = "passed" if self.report.passed else "failed"
        status_text = "✅ ПРОЙДЕНО" if self.report.passed else "❌ НЕ ПРОЙДЕНО"
        
        # Прогресс бары для категорий
        category_bars = ""
        for cat, result in self.report.categories.items():
            color = "#4CAF50" if result.passed else "#F44336"
            category_bars += f"""
            <div style="margin: 10px 0;">
                <strong>{cat.capitalize()}</strong>: {result.score:.1f}%
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {result.score}%; background: {color};"></div>
                </div>
            </div>
            """
        
        # Таблица тестов
        tests_html = ""
        for cat, result in self.report.categories.items():
            tests_html += f"<h3>{cat.capitalize()}</h3><table>"
            tests_html += "<tr><th>Тест</th><th>Статус</th><th>Балл</th><th>Результат</th></tr>"
            
            for test in result.tests:
                test_status = "✅" if test.passed else "❌"
                test_class = "passed" if test.passed else "failed"
                tests_html += f"""
                <tr>
                    <td>{test.test_name}</td>
                    <td class="{test_class}">{test_status}</td>
                    <td>{test.score * 100:.0f}%</td>
                    <td>{test.message}</td>
                </tr>
                """
            
            tests_html += "</table>"
            
            if result.recommendations:
                tests_html += '<div class="recommendations"><strong>Рекомендации:</strong><ul>'
                for rec in result.recommendations:
                    tests_html += f"<li>{rec}</li>"
                tests_html += "</ul></div>"
        
        # Метаданные
        metadata_html = ""
        if self.report.metadata:
            metadata_html = '<div class="metadata"><h3>Метаданные базы</h3><ul>'
            for key, value in self.report.metadata.items():
                metadata_html += f"<li><strong>{key}:</strong> {value}</li>"
            metadata_html += "</ul></div>"
        
        html = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Отчёт о качестве RAG-базы</title>
            {css}
        </head>
        <body>
            <h1>📊 Отчёт о качестве RAG-базы</h1>
            
            <div class="score-card">
                <p><strong>Дата:</strong> {self.report.timestamp}</p>
                <p><strong>Путь:</strong> <code>{self.report.db_path}</code></p>
                <p><strong>Время выполнения:</strong> {self.report.duration_seconds} сек</p>
                <p><strong>Порог качества:</strong> {self.report.threshold}%</p>
            </div>
            
            <div class="score-card">
                <div class="score-big {status_class}">
                    {self.report.total_score:.1f}/100
                </div>
                <p style="text-align: center; font-size: 24px;" class="{status_class}">
                    {status_text}
                </p>
            </div>
            
            <h2>📈 Распределение по категориям</h2>
            <div class="score-card">
                {category_bars}
            </div>
            
            <h2>📋 Детали тестов</h2>
            <div class="score-card">
                {tests_html}
            </div>
            
            {metadata_html}
            
            <p style="text-align: center; color: #666; margin-top: 30px;">
                <em>Отчёт сгенерирован автоматически</em>
            </p>
        </body>
        </html>
        """
        
        return html
    
    def _to_dict(self) -> Dict:
        """Конвертирует отчёт в словарь."""
        result = {
            'timestamp': self.report.timestamp,
            'db_path': self.report.db_path,
            'total_score': self.report.total_score,
            'passed': self.report.passed,
            'threshold': self.report.threshold,
            'duration_seconds': self.report.duration_seconds,
            'categories': {},
            'metadata': self.report.metadata
        }
        
        for cat, cat_result in self.report.categories.items():
            result['categories'][cat] = {
                'score': cat_result.score,
                'passed': cat_result.passed,
                'weight': cat_result.weight,
                'tests': [
                    {
                        'test_name': t.test_name,
                        'passed': t.passed,
                        'score': t.score,
                        'message': t.message,
                        'details': t.details
                    }
                    for t in cat_result.tests
                ],
                'recommendations': cat_result.recommendations
            }
        
        return result
