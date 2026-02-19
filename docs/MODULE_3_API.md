# Модуль 3: Гибридный чанкинг и метаданные — Документация API

**Версия системы:** 2.1.0  
**Автор:** [Line_GV](https://t.me/Line_GV)  
**Дата обновления:** 2026-02-18

## Обзор

Модуль 3 реализует этапы 5–6 обработки PDF-документов: гибридное разбиение текста на чанки и добавление метаданных. Это критически важный этап для подготовки данных к использованию в RAG-системах.

## Функциональность

### Этап 5: Гибридный чанкинг

Гибридный подход к разбиению текста на чанки:
1. **Семантическое разбиение**: текст сначала разбивается на смысловые блоки (абзацы, списки, заголовки)
2. **Фиксированное разбиение**: если блок превышает `max_chunk_size`, он разбивается с перекрытием

### Этап 6: Добавление метаданных

Каждому чанку присваиваются метаданные:
- `source`: путь к исходному PDF-файлу
- `page_number`: номер страницы
- `chunk_id`: уникальный идентификатор чанка
- `timestamp`: время создания чанка
- `chunk_type`: тип чанка (heading, paragraph, list, list_item)
- `char_count`: количество символов
- `word_count`: количество слов

## API

### `hybrid_chunking(structured_text, max_chunk_size, overlap)`

Выполняет гибридное разбиение структурированного текста на чанки.

**Параметры:**
- `structured_text` (Dict[str, Any]): Структурированный текст (результат `structure_text`)
- `max_chunk_size` (int): Максимальный размер чанка в символах (по умолчанию: 500)
- `overlap` (int): Перекрытие между чанками в символах (по умолчанию: 50)

**Возвращает:**
- `List[Dict[str, Any]]`: Список чанков с текстом и типом блока

**Пример:**
```python
from src.chunker import hybrid_chunking

chunks = hybrid_chunking(
    structured_text=structure,
    max_chunk_size=500,
    overlap=50
)

for chunk in chunks:
    print(f"Тип: {chunk['type']}")
    print(f"Текст: {chunk['text'][:100]}...")
```

---

### `add_metadata(chunks, pdf_path, page_number)`

Добавляет метаданные к каждому чанку.

**Параметры:**
- `chunks` (List[Dict[str, Any]]): Список чанков
- `pdf_path` (str): Путь к исходному PDF-файлу
- `page_number` (int): Номер страницы (по умолчанию: 1)

**Возвращает:**
- `List[Dict[str, Any]]`: Список чанков с добавленными метаданными

**Пример:**
```python
from src.chunker import add_metadata

chunks_with_metadata = add_metadata(
    chunks=chunks,
    pdf_path="document.pdf",
    page_number=1
)

for chunk in chunks_with_metadata:
    print(f"ID: {chunk['metadata']['chunk_id']}")
    print(f"Символов: {chunk['metadata']['char_count']}")
    print(f"Слов: {chunk['metadata']['word_count']}")
```

---

### `validate_chunks(chunks)`

Валидирует чанки и вычисляет статистику.

**Параметры:**
- `chunks` (List[Dict[str, Any]]): Список чанков для валидации

**Возвращает:**
- `Dict[str, Any]`: Словарь с результатами валидации и статистикой

**Пример:**
```python
from src.chunker import validate_chunks

validation = validate_chunks(chunks)

print(f"Всего чанков: {validation['stats']['total_chunks']}")
print(f"Средняя длина: {validation['stats']['avg_char_count']:.2f}")
print(f"Пустых чанков: {len(validation['empty_chunks'])}")
```

---

### `generate_chunking_report(validation_result, max_chunk_size, overlap, output_file)`

Генерирует отчёт по чанкингу в формате Markdown.

**Параметры:**
- `validation_result` (Dict[str, Any]): Результаты валидации чанков
- `max_chunk_size` (int): Максимальный размер чанка
- `overlap` (int): Перекрытие между чанками
- `output_file` (str): Путь к файлу отчёта

**Возвращает:**
- `str`: Путь к созданному файлу

---

### `generate_chunking_demo(chunks, processed_pages, output_file)`

Генерирует демонстрационный файл с результатами чанкинга.

**Параметры:**
- `chunks` (List[Dict[str, Any]]): Список чанков с метаданными
- `processed_pages` (List[Dict[str, Any]]): Обработанные страницы с исходным текстом
- `output_file` (str): Путь к файлу демонстрации

**Возвращает:**
- `str`: Путь к созданному файлу

**Пример:**
```python
from src.chunker import generate_chunking_demo

demo_path = generate_chunking_demo(
    chunks=chunks,
    processed_pages=processed_pages,
    output_file="output_module_3/content_demonstrator.txt"
)

print(f"Демонстрация сохранена: {demo_path}")
```

**Формат файла:**
```markdown
# Демонстрация результатов Модуля 3: Гибридный чанкинг и метаданные

## Часть 1: Исходный структурированный текст
## Часть 2: Результаты чанкинга (Этапы 5-6)
## Часть 3: Примеры полных метаданных
## Часть 4: Статистика по чанкам
## Часть 5: Распределение чанков по типам
## Заключение
```

---

### `process_chunks(processed_pages, pdf_path, output_dir, max_chunk_size, overlap, generate_demo)`

Полный цикл обработки чанков для всех страниц.

**Параметры:**
- `processed_pages` (List[Dict[str, Any]]): Обработанные страницы с результатами структурирования
- `pdf_path` (str): Путь к исходному PDF-файлу
- `output_dir` (str): Директория для сохранения результатов
- `max_chunk_size` (int): Максимальный размер чанка
- `overlap` (int): Перекрытие между чанками
- `generate_demo` (bool): Генерировать демонстрационный файл (по умолчанию: True)

**Возвращает:**
- `Dict[str, Any]`: Словарь с результатами обработки чанков

**Пример:**
```python
from src.chunker import process_chunks

result = process_chunks(
    processed_pages=processed_pages,
    pdf_path="document.pdf",
    output_dir="output_module_3/",
    max_chunk_size=500,
    overlap=50,
    generate_demo=True  # Генерировать демонстрационный файл
)

chunks = result["chunks"]
validation = result["validation"]
report_path = result["report_path"]
demo_path = result["demo_path"]  # Путь к демонстрационному файлу
```

---

## Интеграция с процессом обработки

Модуль 3 интегрирован в функцию `process_pdf` из `src/preprocessor.py`:

```python
from src.preprocessor import process_pdf

result = process_pdf(
    pdf_path="document.pdf",
    output_dir="output_module_2/",
    enable_chunking=True,      # Включить этапы 5-6
    max_chunk_size=500,        # Максимальный размер чанка
    overlap=50,                # Перекрытие между чанками
    generate_demo=True         # Генерировать демонстрационный файл
)

# Доступ к чанкам
chunks = result["chunks"]
for chunk in chunks:
    print(f"{chunk['metadata']['chunk_id']}: {chunk['text'][:50]}...")

# Доступ к отчётам
chunking_report = result["chunking_report_path"]  # output_module_3/chunking_report.txt
chunking_demo = result["chunking_demo_path"]      # output_module_3/content_demonstrator.txt
```

---

## Критерии приёмки

✅ Чанки сохраняют смысловые блоки  
✅ Метаданные корректно привязаны  
✅ Отчёт содержит полную статистику  
✅ Пустые чанки выявляются  
✅ Слишком короткие чанки выявляются  
✅ Статистика по типам чанков собирается  

---

## Формат отчёта

Отчёт по чанкингу сохраняется в `output_module_3/chunking_report.txt` и содержит:

```markdown
# Отчёт по чанкингу

**Дата генерации:** 2026-02-18 17:00:00

## Этап 5: Гибридный чанкинг

**Параметры:**
- Максимальный размер: 500 символов
- Перекрытие: 50 символов

**Статистика:**
| Параметр | Значение |
|----------|----------|
| Всего чанков | 25 |
| Всего символов | 12500 |
| Всего слов | 2100 |
| Средняя длина (символы) | 500.00 |
| Минимальная длина (символы) | 150 |
| Максимальная длина (символы) | 550 |
| Средняя длина (слова) | 84.00 |
| Минимальная длина (слова) | 25 |
| Максимальная длина (слова) | 110 |

**Распределение по типам:**
| Тип | Количество |
|-----|-----------|
| heading | 5 |
| paragraph | 15 |
| list | 3 |
| list_item | 2 |

## Валидация

- Пустых чанков: 0
- Слишком коротких чанков (< 10 символов): 0

**Статус:** ✅ Все чанки прошли валидацию
```

---

## Лицензия и контакты

**Автор:** Line_GV  
**Telegram:** [@Line_GV](https://t.me/Line_GV)

Проект разработан для образовательных целей в рамках обучения Prompt Engineering 3.0 от Zerocoder.
