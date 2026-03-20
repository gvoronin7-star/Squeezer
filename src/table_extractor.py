"""
Модуль извлечения таблиц из PDF.

Использует pdfplumber для нахождения таблиц и опционально LLM для парсинга.
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class TableInfo:
    """Информация об извлечённой таблице."""
    table_id: str
    page_number: int
    rows: int
    cols: int
    headers: List[str]
    data: List[List[str]]
    raw_text: str
    bounding_box: Optional[tuple] = None


@dataclass
class TableWithLLM:
    """Таблица с интерпретацией от LLM."""
    table_id: str
    page_number: int
    description: str
    summary: str
    json_data: Dict[str, Any]
    headers: List[str]
    rows: List[Dict[str, str]]
    confidence: float


class TableExtractor:
    """
    Извлекает таблицы из PDF.
    
    Методы:
    1. Нативное извлечение (pdfplumber)
    2. OCR для сканированных таблиц
    3. LLM интерпретация (опционально)
    """
    
    def __init__(
        self,
        llm_model: str = "gpt-4o-mini",
        api_key: str = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1"
    ):
        """
        Инициализация экстрактора.
        
        Args:
            llm_model: Модель LLM для интерпретации.
            api_key: API ключ.
            api_base: Базовый URL.
        """
        self.llm_model = llm_model
        self.api_key = api_key
        self.api_base = api_base
        
        # Загружаем .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        import os
        if not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Проверяем доступность pdfplumber
        self.pdfplumber_available = self._check_pdfplumber()
    
    def _check_pdfplumber(self) -> bool:
        """Проверяет доступность pdfplumber."""
        try:
            import pdfplumber
            return True
        except ImportError:
            logger.warning("pdfplumber не установлен. Установите: pip install pdfplumber")
            return False
    
    def is_llm_available(self) -> bool:
        """Проверяет доступность LLM."""
        return bool(self.api_key)
    
    def extract_tables(
        self,
        pdf_path: str,
        use_llm: bool = False,
        min_rows: int = 2,
        min_cols: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Извлекает все таблицы из PDF.
        
        Args:
            pdf_path: Путь к PDF файлу.
            use_llm: Использовать ли LLM для интерпретации.
            min_rows: Минимальное количество строк.
            min_cols: Минимальное количество колонок.
        
        Returns:
            Список таблиц.
        """
        if not self.pdfplumber_available:
            logger.error("pdfplumber не доступен")
            return []
        
        try:
            import pdfplumber
        except ImportError:
            logger.error("Не удалось импортировать pdfplumber")
            return []
        
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"Начало извлечения таблиц из {len(pdf.pages)} страниц")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    # Извлекаем таблицы
                    page_tables = page.extract_tables()
                    
                    if page_tables:
                        logger.info(f"Страница {page_num}: найдено {len(page_tables)} таблиц")
                        
                        for table_idx, table in enumerate(page_tables):
                            if not table or not any(table):
                                continue
                            
                            # Проверяем размеры
                            rows = [row for row in table if any(cell is not None for cell in row)]
                            if len(rows) < min_rows:
                                continue
                            
                            cols = max(len(row) for row in rows) if rows else 0
                            if cols < min_cols:
                                continue
                            
                            # Обрабатываем таблицу
                            table_info = self._process_table(
                                rows, page_num, table_idx
                            )
                            
                            # Опционально - LLM интерпретация
                            if use_llm and self.is_llm_available():
                                table_with_llm = self._interpret_with_llm(
                                    table_info, pdf_path
                                )
                                tables.append(asdict(table_with_llm))
                            else:
                                tables.append(asdict(table_info))
                    else:
                        logger.debug(f"Страница {page_num}: таблицы не найдены")
        
        except Exception as e:
            logger.error(f"Ошибка при извлечении таблиц: {e}")
        
        logger.info(f"Извлечено таблиц: {len(tables)}")
        return tables
    
    def _process_table(
        self,
        rows: List[List],
        page_number: int,
        table_idx: int
    ) -> TableInfo:
        """Обрабатывает сырую таблицу."""
        # Извлекаем заголовки (первая строка)
        headers = []
        data = []
        
        if rows:
            # Первая строка - заголовки
            first_row = rows[0]
            headers = [self._clean_cell(cell) for cell in first_row]
            
            # Остальные строки - данные
            for row in rows[1:]:
                cleaned_row = [self._clean_cell(cell) for cell in row]
                # Дополняем до нужного количества колонок
                while len(cleaned_row) < len(headers):
                    cleaned_row.append("")
                data.append(cleaned_row[:len(headers)])
        
        # Формируем ID
        table_id = f"table_{page_number}_{table_idx}"
        
        # Создаём текстовое представление
        raw_text = self._table_to_text(headers, data)
        
        return TableInfo(
            table_id=table_id,
            page_number=page_number,
            rows=len(data),
            cols=len(headers),
            headers=headers,
            data=data,
            raw_text=raw_text
        )
    
    def _clean_cell(self, cell: Any) -> str:
        """Очищает содержимое ячейки."""
        if cell is None:
            return ""
        return str(cell).strip()
    
    def _table_to_text(self, headers: List[str], data: List[List[str]]) -> str:
        """Конвертирует таблицу в текст."""
        lines = []
        
        # Заголовки
        lines.append(" | ".join(headers))
        lines.append("-" * len(lines[-1]))
        
        # Данные
        for row in data:
            lines.append(" | ".join(row))
        
        return "\n".join(lines)
    
    def _interpret_with_llm(
        self,
        table_info: TableInfo,
        pdf_path: str
    ) -> TableWithLLM:
        """Интерпретирует таблицу с помощью LLM."""
        try:
            from src.llm_chunker import call_llm
            
            # Формируем промпт
            prompt = f"""Проанализируй таблицу из PDF документа и выполни:

1. Дай краткое описание таблицы (1-2 предложения)
2. Сделай краткое резюме (2-3 предложения)
3. Конвертируй в JSON формат

Таблица:
{table_info.raw_text}

Формат ответа:
```json
{{
  "description": "краткое описание",
  "summary": "краткое резюме",
  "json_data": {{"ключ": "значение"}},
  "confidence": 0.95
}}
```

Ответь ТОЛЬКО JSON (без markdown):"""

            response = call_llm(
                prompt=prompt,
                model=self.llm_model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.3,
                max_tokens=1000
            )
            
            if not response:
                return TableWithLLM(
                    table_id=table_info.table_id,
                    page_number=table_info.page_number,
                    description="Не удалось интерпретировать",
                    summary="Требуется ручной анализ",
                    json_data={},
                    headers=table_info.headers,
                    rows=[],
                    confidence=0.0
                )
            
            # Парсим JSON
            try:
                # Удаляем markdown если есть
                response = response.strip()
                if response.startswith("```"):
                    response = response.split("```")[1]
                    if response.startswith("json"):
                        response = response[4:]
                    response = response.strip()
                
                parsed = json.loads(response)
                
                # Конвертируем в построчный формат
                rows = []
                if table_info.data:
                    for row in table_info.data:
                        row_dict = {}
                        for i, header in enumerate(table_info.headers):
                            row_dict[header] = row[i] if i < len(row) else ""
                        rows.append(row_dict)
                
                return TableWithLLM(
                    table_id=table_info.table_id,
                    page_number=table_info.page_number,
                    description=parsed.get("description", ""),
                    summary=parsed.get("summary", ""),
                    json_data=parsed.get("json_data", {}),
                    headers=table_info.headers,
                    rows=rows,
                    confidence=parsed.get("confidence", 0.8)
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"Не удалось распарсить JSON: {e}")
                return TableWithLLM(
                    table_id=table_info.table_id,
                    page_number=table_info.page_number,
                    description="Ошибка парсинга",
                    summary="Требуется ручной анализ",
                    json_data={},
                    headers=table_info.headers,
                    rows=[],
                    confidence=0.0
                )
        
        except Exception as e:
            logger.error(f"LLM интерпретация не удалась: {e}")
            return TableWithLLM(
                table_id=table_info.table_id,
                page_number=table_info.page_number,
                description="Ошибка LLM",
                summary=str(e),
                json_data={},
                headers=table_info.headers,
                rows=[],
                confidence=0.0
            )


def extract_tables_from_pdf(
    pdf_path: str,
    use_llm: bool = False,
    llm_model: str = "gpt-4o-mini",
    api_key: str = None,
    api_base: str = "https://openai.api.proxyapi.ru/v1"
) -> List[Dict[str, Any]]:
    """
    Удобная функция для извлечения таблиц.
    
    Args:
        pdf_path: Путь к PDF.
        use_llm: Использовать LLM.
        llm_model: Модель LLM.
        api_key: API ключ.
        api_base: Базовый URL.
    
    Returns:
        Список таблиц.
    """
    extractor = TableExtractor(
        llm_model=llm_model,
        api_key=api_key,
        api_base=api_base
    )
    
    return extractor.extract_tables(pdf_path, use_llm=use_llm)
