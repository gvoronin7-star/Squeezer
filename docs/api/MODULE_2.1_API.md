# Модуль 2.1: Пользовательский интерфейс для загрузки PDF — Документация API

**Версия системы:** 3.3.0
**Автор:** [Line_GV](https://t.me/Line_GV)  
**Дата обновления:** 2026-03-20

## Обзор

Модуль 2.1 предоставляет графический интерфейс для загрузки, валидации и сохранения PDF файлов во временное хранилище для дальнейшей обработки.

## Компоненты

### 1. PDFLoader

Класс для загрузки и валидации PDF файлов.

#### Инициализация

```python
from src.ui.pdf_loader import PDFLoader

loader = PDFLoader(language='ru')
```

**Параметры:**
- `language` (str): Язык интерфейса ('ru' или 'en'). По умолчанию 'ru'.

#### Методы

##### `load_file(file_path: Path) -> Tuple[bool, Optional[Path], Optional[str]]`

Загружает и сохраняет PDF файл во временное хранилище.

**Параметры:**
- `file_path` (Path): Путь к исходному файлу.

**Возвращает:**
- Кортеж (успех, путь к временному файлу, сообщение об ошибке):
  - `bool`: True, если файл успешно загружен
  - `Path`: Путь к временному файлу или None
  - `str`: Сообщение об ошибке или None

**Пример:**

```python
from pathlib import Path
from src.ui.pdf_loader import PDFLoader

loader = PDFLoader(language='ru')
success, temp_path, error = loader.load_file(Path('document.pdf'))

if success:
    print(f"Файл загружен: {temp_path}")
else:
    print(f"Ошибка: {error}")
```

##### `get_file_info() -> dict`

Возвращает информацию о загруженном файле.

**Возвращает:**
- Словарь с информацией:
  - `name` (str): Имя временного файла
  - `original_name` (str): Имя исходного файла
  - `size` (int): Размер в байтах
  - `size_mb` (float): Размер в мегабайтах
  - `pages` (int): Количество страниц
  - `path` (str): Путь к временному файлу

**Пример:**

```python
info = loader.get_file_info()
print(f"Страниц: {info['pages']}")
print(f"Размер: {info['size_mb']:.2f} MB")
```

##### `cleanup() -> None`

Очищает временные файлы.

**Пример:**

```python
loader.cleanup()
```

#### Атрибуты

- `current_file_path` (Optional[Path]): Путь к исходному файлу
- `temp_file_path` (Optional[Path]): Путь к временному файлу
- `TEMP_DIR` (Path): Директория для временных файлов (по умолчанию: "temp_uploads")
- `MAX_FILE_SIZE` (int): Максимальный размер файла (50 MB)

### 2. PDFLoaderUI

Графический интерфейс для загрузки PDF файлов на базе Tkinter.

#### Инициализация

```python
import tkinter as tk
from src.ui.pdf_loader import PDFLoaderUI

root = tk.Tk()
ui = PDFLoaderUI(
    root,
    language='ru',
    on_file_loaded=lambda path: print(f"Загружен: {path}"),
    on_processing_complete=lambda info: print(f"Готово: {info}")
)
```

**Параметры:**
- `master` (tk.Tk): Родительское окно Tkinter
- `language` (str): Язык интерфейса ('ru' или 'en'). По умолчанию 'ru'
- `on_file_loaded` (Optional[Callable[[Path], None]]): Callback при загрузке файла
- `on_processing_complete` (Optional[Callable[[dict], None]]): Callback при завершении обработки

#### Методы

##### `get_temp_file_path() -> Optional[Path]`

Возвращает путь к временному файлу.

**Возвращает:**
- Путь к временному файлу или None

##### `get_file_info() -> Optional[dict]`

Возвращает информацию о загруженном файле.

**Возвращает:**
- Словарь с информацией о файле или None

#### Атрибуты

- `language` (str): Текущий язык интерфейса
- `loader` (PDFLoader): Экземпляр загрузчика PDF
- `file_info` (Optional[dict]): Информация о загруженном файле
- `is_processing` (bool): Флаг обработки

### 3. SqueezerApp

Основное приложение, интегрирующее UI с модулем обработки.

#### Инициализация

```python
import tkinter as tk
from gui_app import SqueezerApp

root = tk.Tk()
app = SqueezerApp(root, language='ru')
app.run()
```

**Параметры:**
- `root` (tk.Tk): Корневое окно Tkinter
- `language` (str): Язык интерфейса ('ru' или 'en'). По умолчанию 'ru'

#### Методы

##### `process_pdf_file(file_path: Path, output_dir: str = './output_module_2/') -> dict`

Обрабатывает PDF файл.

**Параметры:**
- `file_path` (Path): Путь к PDF файлу
- `output_dir` (str): Директория для сохранения результатов

**Возвращает:**
- Результаты обработки (словарь с полями `pages`, `stats`, `report_path`, `demo_path`)

##### `run() -> None`

Запускает приложение.

## Примеры использования

### Пример 1: Загрузка файла через код

```python
from pathlib import Path
from src.ui.pdf_loader import PDFLoader

# Создаём загрузчик
loader = PDFLoader(language='ru')

# Загружаем файл
success, temp_path, error = loader.load_file(Path('document.pdf'))

if success:
    # Получаем информацию о файле
    info = loader.get_file_info()
    print(f"Файл: {info['name']}")
    print(f"Страниц: {info['pages']}")
    print(f"Размер: {info['size_mb']:.2f} MB")

    # Теперь можно использовать temp_path для обработки
    from src.preprocessor import process_pdf
    result = process_pdf(str(temp_path), './output_module_2/')

    # Очищаем временные файлы
    loader.cleanup()
else:
    print(f"Ошибка загрузки: {error}")
```

### Пример 2: Использование UI с обработкой

```python
import tkinter as tk
from gui_app import SqueezerApp

root = tk.Tk()
app = SqueezerApp(root, language='ru')

# Опционально: можно добавить свои обработчики
def on_file_loaded(file_path):
    print(f"Файл загружен: {file_path}")

def on_processing_complete(file_info):
    print(f"Обработка завершена: {file_info}")

app.ui.on_file_loaded = on_file_loaded
app.ui.on_processing_complete = on_processing_complete

# Запускаем приложение
app.run()
```

### Пример 3: Интеграция в существующее приложение

```python
import tkinter as tk
from src.ui.pdf_loader import PDFLoaderUI

class MyApplication:
    def __init__(self, root):
        self.root = root
        self.pdf_path = None

        # Создаём UI загрузчика PDF
        self.pdf_loader = PDFLoaderUI(
            root,
            language='ru',
            on_file_loaded=self._on_pdf_loaded,
            on_processing_complete=self._on_processing_complete
        )

        # Добавляем свои компоненты
        self.add_custom_ui()

    def _on_pdf_loaded(self, file_path):
        self.pdf_path = file_path
        print(f"PDF загружен: {file_path}")

    def _on_processing_complete(self, file_info):
        print(f"Обработка завершена")
        # Обновляем свой UI

    def add_custom_ui(self):
        # Добавляем свои элементы интерфейса
        pass

    def run(self):
        self.root.mainloop()

# Запуск
root = tk.Tk()
app = MyApplication(root)
app.run()
```

## Локализация

Модуль поддерживает два языка: русский ('ru') и английский ('en').

### Доступные переводы

```python
TRANSLATIONS = {
    'ru': {
        'window_title': 'Соковыжималка — Загрузка PDF',
        'load_button': 'Загрузить PDF',
        'process_button': 'Обработать',
        'select_file': 'Выберите PDF-файл',
        # ... и другие
    },
    'en': {
        'window_title': 'Squeezer — PDF Upload',
        'load_button': 'Upload PDF',
        'process_button': 'Process',
        'select_file': 'Select PDF file',
        # ... и другие
    }
}
```

## Обработка ошибок

Модуль обрабатывает следующие ошибки:

1. **Неверный формат файла**: Сообщение "Неверный формат. Выберите файл .pdf"
2. **Файл не существует**: Сообщение "Не удалось открыть файл. Проверьте целостность PDF"
3. **Нет доступа к временной директории**: Сообщение "Нет доступа к папке для временных файлов"
4. **Файл слишком большой**: Сообщение о превышении максимального размера (50 MB)
5. **Ошибка при чтении**: Сообщение "Не удалось открыть файл. Проверьте целостность PDF"

## Безопасность

Модуль включает следующие меры безопасности:

1. **Валидация формата**: Проверка расширения .pdf и заголовка PDF
2. **Ограничение размера**: Максимальный размер файла 50 MB
3. **Изолированное хранение**: Временные файлы хранятся в отдельной директории
4. **Очистка ресурсов**: Автоматическое удаление временных файлов при закрытии

## Требования

- Python 3.10+
- Tkinter (обычно включён в стандартную установку Python)
- pypdf (для подсчёта страниц)

## Зависимости

```
tkinter  # Входит в стандартную библиотеку Python
pypdf>=3.0.0
```

## Критерии приёмки

✅ Пользователь может выбрать PDF-файл через интерфейс
✅ Система отображает имя файла после загрузки
✅ Некорректные форматы блокируются с пояснением ошибки
✅ Файл сохраняется во временное хранилище и доступен для обработки
✅ Все ошибки обрабатываются без краша приложения
✅ Интерфейс адаптивен (поддержка ПК и планшетов)
✅ Локализация: русский и английский языки
✅ Время загрузки не более 10 сек для документов до 50 страниц

## История изменений

### v2.1.0 (2026-02-18)
- Интеграция с Модулем 3 (гибридный чанкинг и метаданные)
- Добавлено отображение статистики чанкинга в диалоговом окне
- Обновлена функция `process_pdf_file()` с параметрами чанкинга
- Добавлено отображение информации о демонстрационном файле

### v2.0.0 (2026-02-18)
- Добавлен класс `PDFLoaderUI` с полной поддержкой GUI
- Реализована локализация RU/EN
- Добавлена визуальная обратная связь (индикатор прогресса, статус-бар)
- Интеграция с модулем обработки через `SqueezerApp`
- Исправлен импорт `ttk` в `gui_app.py`
- Настроена кодировка UTF-8 для логов

## Лицензия и контакты

**Автор:** Line_GV  
**Telegram:** [@Line_GV](https://t.me/Line_GV)

Проект разработан для образовательных целей в рамках обучения Prompt Engineering 3.0 от Zerocoder.
