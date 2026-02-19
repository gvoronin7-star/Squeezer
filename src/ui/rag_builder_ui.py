"""
Модуль 2.2: Пользовательский интерфейс для создания RAG-баз данных.

Реализует графический интерфейс для выбора нескольких PDF-файлов,
назначения названия RAG-базы и создания векторной базы данных.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Callable, Tuple
from datetime import datetime

# Tkinter для GUI
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from tkinter.scrolledtext import ScrolledText
except ImportError:
    tk = None

# Настройка логирования
logger = logging.getLogger(__name__)


# Локализация
TRANSLATIONS = {
    'ru': {
        'window_title': 'Соковыжималка — Создание RAG-базы',
        'load_button': 'Добавить PDF',
        'remove_button': 'Удалить',
        'clear_button': 'Очистить все',
        'process_button': 'Создать RAG-базу',
        'select_files': 'Выберите PDF-файлы для базы',
        'rag_name_label': 'Название RAG-базы:',
        'rag_name_placeholder': 'Введите название (автоматически, если пусто)',
        'files_list': 'Выбранные файлы:',
        'no_files': 'Файлы не выбраны',
        'processing': 'Создание RAG-базы...',
        'error_title': 'Ошибка',
        'success_title': 'Успех',
        'invalid_format': 'Неверный формат. Выберите файлы .pdf',
        'cannot_open': 'Не удалось открыть файл. Проверьте целостность PDF',
        'no_access': 'Нет доступа к папке для временных файлов',
        'no_files_selected': 'Выберите хотя бы один PDF-файл',
        'processing_complete': 'RAG-база создана',
        'processing_failed': 'Не удалось создать RAG-базу',
        'progress': 'Прогресс',
        'pages': 'страниц',
        'upload_complete': 'Файл добавлен',
        'file_info': 'Информация о файле',
        'file_name': 'Имя файла',
        'file_size': 'Размер файла',
        'file_pages': 'Количество страниц',
        'cancel': 'Отмена',
        'rag_base_created': 'RAG-база успешно создана',
        'rag_base_location': 'Расположение базы: {}',
        'total_files': 'Всего файлов: {}',
        'total_pages': 'Всего страниц: {}',
        'total_chunks': 'Всего чанков: {}',
        'rag_name_error': 'Ошибка: название базы пустое'
    },
    'en': {
        'window_title': 'Squeezer — RAG Database Builder',
        'load_button': 'Add PDF',
        'remove_button': 'Remove',
        'clear_button': 'Clear All',
        'process_button': 'Create RAG Database',
        'select_files': 'Select PDF files for database',
        'rag_name_label': 'RAG Database Name:',
        'rag_name_placeholder': 'Enter name (auto if empty)',
        'files_list': 'Selected Files:',
        'no_files': 'No files selected',
        'processing': 'Creating RAG database...',
        'error_title': 'Error',
        'success_title': 'Success',
        'invalid_format': 'Invalid format. Select .pdf files',
        'cannot_open': 'Failed to open file. Check PDF integrity',
        'no_access': 'No access to temporary files folder',
        'no_files_selected': 'Select at least one PDF file',
        'processing_complete': 'RAG database created',
        'processing_failed': 'Failed to create RAG database',
        'progress': 'Progress',
        'pages': 'pages',
        'upload_complete': 'File added',
        'file_info': 'File Information',
        'file_name': 'File Name',
        'file_size': 'File Size',
        'file_pages': 'Number of Pages',
        'cancel': 'Cancel',
        'rag_base_created': 'RAG database created successfully',
        'rag_base_location': 'Database location: {}',
        'total_files': 'Total files: {}',
        'total_pages': 'Total pages: {}',
        'total_chunks': 'Total chunks: {}',
        'rag_name_error': 'Error: database name is empty'
    }
}


class RAGFileLoader:
    """
    Класс для загрузки и валидации нескольких PDF файлов.
    """

    TEMP_DIR = Path("temp_uploads")
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

    def __init__(self, language: str = 'ru'):
        """
        Инициализация загрузчика PDF.

        Args:
            language: Язык интерфейса ('ru' или 'en').
        """
        self.language = language
        self.loaded_files: List[dict] = []  # Список загруженных файлов

        # Создаём временную директорию
        self._ensure_temp_dir()

        logger.info(f"RAGFileLoader инициализирован (язык: {language})")

    def _ensure_temp_dir(self) -> None:
        """Создаёт временную директорию, если она не существует."""
        try:
            self.TEMP_DIR.mkdir(exist_ok=True)
            logger.debug(f"Временная директория: {self.TEMP_DIR}")
        except PermissionError:
            raise PermissionError(TRANSLATIONS[self.language]['no_access'])

    def _validate_pdf(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Валидирует PDF файл.

        Args:
            file_path: Путь к файлу.

        Returns:
            Кортеж (валидность, сообщение об ошибке).
        """
        # Проверка расширения
        if file_path.suffix.lower() != '.pdf':
            return False, TRANSLATIONS[self.language]['invalid_format']

        # Проверка существования файла
        if not file_path.exists():
            return False, TRANSLATIONS[self.language]['cannot_open']

        # Проверка размера файла
        try:
            file_size = file_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                return False, f"File too large (max {self.MAX_FILE_SIZE // (1024*1024)} MB)"
        except OSError:
            return False, TRANSLATIONS[self.language]['cannot_open']

        # Проверка чтения файла
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    return False, TRANSLATIONS[self.language]['invalid_format']
        except Exception as e:
            logger.error(f"Ошибка при чтении файла: {e}")
            return False, TRANSLATIONS[self.language]['cannot_open']

        return True, None

    def _get_page_count(self, file_path: Path) -> int:
        """
        Возвращает количество страниц в PDF.

        Args:
            file_path: Путь к файлу.

        Returns:
            Количество страниц.
        """
        try:
            import pypdf
            with open(file_path, 'rb') as f:
                pdf_reader = pypdf.PdfReader(f)
                return len(pdf_reader.pages)
        except Exception as e:
            logger.error(f"Ошибка при подсчёте страниц: {e}")
            return 0

    def load_file(self, file_path: Path) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Загружает и сохраняет PDF файл во временное хранилище.

        Args:
            file_path: Путь к исходному файлу.

        Returns:
            Кортеж (успех, информация о файле, сообщение об ошибке).
        """
        # Валидация
        is_valid, error_msg = self._validate_pdf(file_path)
        if not is_valid:
            return False, None, error_msg

        # Проверка на дубликаты
        if any(f['original_path'] == str(file_path) for f in self.loaded_files):
            return False, None, "Файл уже добавлен"

        try:
            # Создаём уникальное имя для временного файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            temp_filename = f"{timestamp}_{file_path.stem}.pdf"
            temp_path = self.TEMP_DIR / temp_filename

            # Копируем файл во временную директорию
            shutil.copy2(file_path, temp_path)

            # Получаем информацию о файле
            page_count = self._get_page_count(temp_path)
            file_size = temp_path.stat().st_size

            file_info = {
                'original_path': str(file_path),
                'original_name': file_path.name,
                'temp_path': str(temp_path),
                'name': temp_filename,
                'size': file_size,
                'size_mb': file_size / (1024 * 1024),
                'pages': page_count,
                'added_at': datetime.now().isoformat()
            }

            self.loaded_files.append(file_info)

            logger.info(f"Файл загружен: {file_path} -> {temp_path}")
            return True, file_info, None

        except Exception as e:
            logger.error(f"Ошибка при копировании файла: {e}")
            return False, None, str(e)

    def remove_file(self, temp_path: str) -> bool:
        """
        Удаляет файл из списка и временного хранилища.

        Args:
            temp_path: Путь к временному файлу.

        Returns:
            Успех удаления.
        """
        for i, file_info in enumerate(self.loaded_files):
            if file_info['temp_path'] == temp_path:
                # Удаляем временный файл
                try:
                    Path(file_info['temp_path']).unlink()
                except Exception as e:
                    logger.error(f"Ошибка при удалении файла: {e}")

                # Удаляем из списка
                del self.loaded_files[i]
                logger.info(f"Файл удалён: {temp_path}")
                return True

        return False

    def clear_all(self) -> None:
        """Удаляет все загруженные файлы."""
        for file_info in self.loaded_files:
            try:
                Path(file_info['temp_path']).unlink()
            except Exception as e:
                logger.error(f"Ошибка при удалении файла: {e}")

        self.loaded_files.clear()
        logger.info("Все файлы удалены")

    def get_total_stats(self) -> dict:
        """
        Возвращает общую статистику по загруженным файлам.

        Returns:
            Словарь со статистикой.
        """
        total_files = len(self.loaded_files)
        total_pages = sum(f['pages'] for f in self.loaded_files)
        total_size = sum(f['size'] for f in self.loaded_files)

        return {
            'total_files': total_files,
            'total_pages': total_pages,
            'total_size': total_size,
            'total_size_mb': total_size / (1024 * 1024)
        }

    def cleanup(self) -> None:
        """Очищает временные файлы."""
        self.clear_all()


class RAGBuilderUI:
    """
    Графический интерфейс для создания RAG-баз данных.
    """

    def __init__(
        self,
        master: tk.Tk,
        language: str = 'ru',
        on_rag_created: Optional[Callable[[dict], None]] = None
    ):
        """
        Инициализация UI.

        Args:
            master: Родительское окно Tkinter.
            language: Язык интерфейса ('ru' или 'en').
            on_rag_created: Callback при создании RAG-базы.
        """
        if tk is None:
            raise ImportError("Tkinter не установлен. Установите python-tk")

        self.master = master
        self.language = language
        self.on_rag_created = on_rag_created
        self.translations = TRANSLATIONS[language]

        self.loader = RAGFileLoader(language)
        self.is_processing = False

        self._setup_ui()
        logger.info("RAGBuilderUI инициализирован")

    def _setup_ui(self) -> None:
        """Настраивает пользовательский интерфейс."""
        self.master.title(self.translations['window_title'])
        self.master.geometry('700x700')
        self.master.resizable(True, True)

        # Устанавливаем иконку (если есть)
        try:
            pass
        except:
            pass

        # Основной контейнер
        main_frame = ttk.Frame(self.master, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Настраиваем вес строк и столбцов
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Заголовок
        title_label = ttk.Label(
            main_frame,
            text=self.translations['window_title'],
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 20), sticky=tk.W)

        # Секция названия RAG-базы
        name_frame = ttk.LabelFrame(main_frame, text=self.translations['rag_name_label'], padding="10")
        name_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        name_frame.columnconfigure(0, weight=1)

        self.rag_name_entry = ttk.Entry(name_frame)
        self.rag_name_entry.insert(0, self.translations['rag_name_placeholder'])
        self.rag_name_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.rag_name_entry.bind('<FocusIn>', self._on_name_entry_focus)

        # Секция выбора файлов
        file_frame = ttk.LabelFrame(main_frame, text=self.translations['select_files'], padding="10")
        file_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        # Кнопка выбора файла
        self.load_button = ttk.Button(
            file_frame,
            text=self.translations['load_button'],
            command=self._on_load_button_click
        )
        self.load_button.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        # Кнопки управления файлами
        self.remove_button = ttk.Button(
            file_frame,
            text=self.translations['remove_button'],
            command=self._on_remove_button_click,
            state='disabled'
        )
        self.remove_button.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))

        self.clear_button = ttk.Button(
            file_frame,
            text=self.translations['clear_button'],
            command=self._on_clear_button_click,
            state='disabled'
        )
        self.clear_button.grid(row=0, column=2, sticky=tk.W)

        # Список файлов
        list_frame = ttk.LabelFrame(main_frame, text=self.translations['files_list'], padding="10")
        list_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Treeview для списка файлов
        self.files_tree = ttk.Treeview(list_frame, columns=('name', 'pages', 'size'), show='headings', height=8)
        self.files_tree.heading('name', text=self.translations['file_name'])
        self.files_tree.heading('pages', text=self.translations['file_pages'])
        self.files_tree.heading('size', text=self.translations['file_size'])
        self.files_tree.column('name', width=300)
        self.files_tree.column('pages', width=100)
        self.files_tree.column('size', width=100)
        self.files_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Scrollbar для списка файлов
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.files_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.files_tree.configure(yscrollcommand=scrollbar.set)

        # Прогресс бар
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.progress_frame.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E))

        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.grid(row=1, column=0, pady=(5, 0))

        # Лог
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = ScrolledText(log_frame, height=6, width=50, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Кнопки действий
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, sticky=(tk.W, tk.E))

        self.process_button = ttk.Button(
            button_frame,
            text=self.translations['process_button'],
            command=self._on_process_button_click,
            state='disabled'
        )
        self.process_button.pack(side=tk.LEFT, padx=(0, 10))

        cancel_button = ttk.Button(
            button_frame,
            text=self.translations['cancel'],
            command=self._on_cancel_button_click
        )
        cancel_button.pack(side=tk.LEFT)

        # Настраиваем веса для растягивания
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(5, weight=1)

    def _on_name_entry_focus(self, event) -> None:
        """Обработчик фокуса на поле названия."""
        if self.rag_name_entry.get() == self.translations['rag_name_placeholder']:
            self.rag_name_entry.delete(0, tk.END)

    def _log(self, message: str) -> None:
        """
        Добавляет сообщение в лог.

        Args:
            message: Сообщение для логирования.
        """
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        logger.info(message)

    def _on_load_button_click(self) -> None:
        """Обработчик нажатия кнопки загрузки файлов."""
        file_paths = filedialog.askopenfilenames(
            title=self.translations['load_button'],
            filetypes=[('PDF files', '*.pdf'), ('All files', '*.*')]
        )

        if not file_paths:
            return

        for file_path in file_paths:
            self._load_file(Path(file_path))

        self._update_ui()

    def _load_file(self, file_path: Path) -> None:
        """
        Загружает файл.

        Args:
            file_path: Путь к файлу.
        """
        self._log(f"Загрузка файла: {file_path.name}")

        # Загружаем файл
        success, file_info, error_msg = self.loader.load_file(file_path)

        if not success:
            self._show_error(error_msg)
            return

        # Добавляем в Treeview
        self.files_tree.insert('', tk.END, values=(
            file_info['original_name'],
            file_info['pages'],
            f"{file_info['size_mb']:.2f} MB"
        ))

        self._log(self.translations['upload_complete'])
        self._log(f"Размер: {file_info['size_mb']:.2f} MB")
        self._log(f"Страниц: {file_info['pages']}")

    def _on_remove_button_click(self) -> None:
        """Обработчик нажатия кнопки удаления файла."""
        selected = self.files_tree.selection()
        if not selected:
            return

        # Удаляем выбранные файлы
        for item in selected:
            values = self.files_tree.item(item)['values']
            file_name = values[0]

            # Находим файл в списке
            for file_info in self.loader.loaded_files:
                if file_info['original_name'] == file_name:
                    self.loader.remove_file(file_info['temp_path'])
                    break

            self.files_tree.delete(item)
            self._log(f"Файл удалён: {file_name}")

        self._update_ui()

    def _on_clear_button_click(self) -> None:
        """Обработчик нажатия кнопки очистки всех файлов."""
        self.loader.clear_all()
        self.files_tree.delete(*self.files_tree.get_children())
        self._log("Все файлы удалены")
        self._update_ui()

    def _update_ui(self) -> None:
        """Обновляет состояние UI на основе загруженных файлов."""
        has_files = len(self.loader.loaded_files) > 0

        self.remove_button.config(state='normal' if has_files else 'disabled')
        self.clear_button.config(state='normal' if has_files else 'disabled')
        self.process_button.config(state='normal' if has_files else 'disabled')

    def _on_process_button_click(self) -> None:
        """Обработчик нажатия кнопки создания RAG-базы."""
        if self.is_processing:
            return

        # Проверяем наличие файлов
        if not self.loader.loaded_files:
            self._show_error(self.translations['no_files_selected'])
            return

        self.is_processing = True
        self.process_button.config(state='disabled')
        self.load_button.config(state='disabled')
        self.remove_button.config(state='disabled')
        self.clear_button.config(state='disabled')

        self.progress.start()
        self.progress_label.config(text=self.translations['processing'])
        self._log(self.translations['processing'])

        # Callback для создания RAG-базы
        if self.on_rag_created:
            self.master.after(100, lambda: self.on_rag_created(self._get_rag_config()))

    def _get_rag_config(self) -> dict:
        """
        Возвращает конфигурацию для создания RAG-базы.

        Returns:
            Словарь с конфигурацией.
        """
        rag_name = self.rag_name_entry.get().strip()

        # Автоматическая генерация названия
        if not rag_name or rag_name == self.translations['rag_name_placeholder']:
            if len(self.loader.loaded_files) == 1:
                # Один файл - используем его имя
                rag_name = Path(self.loader.loaded_files[0]['original_name']).stem
            else:
                # Несколько файлов - используем имя первого + count
                rag_name = f"{Path(self.loader.loaded_files[0]['original_name']).stem}_and_{len(self.loader.loaded_files) - 1}_others"

        # Очищаем название от недопустимых символов
        rag_name = ''.join(c for c in rag_name if c.isalnum() or c in ('_', '-', ' '))

        return {
            'rag_name': rag_name,
            'files': self.loader.loaded_files.copy(),
            'stats': self.loader.get_total_stats()
        }

    def _on_cancel_button_click(self) -> None:
        """Обработчик нажатия кнопки отмены."""
        if self.is_processing:
            self.is_processing = False
            self.progress.stop()
            self.progress_label.config(text="")
            self._log("Создание RAG-базы отменено")

        self.loader.cleanup()

        # Сбрасываем UI
        self.files_tree.delete(*self.files_tree.get_children())
        self.rag_name_entry.delete(0, tk.END)
        self.rag_name_entry.insert(0, self.translations['rag_name_placeholder'])
        self._update_ui()
        self.log_text.delete(1.0, tk.END)

    def _show_error(self, message: str) -> None:
        """
        Показывает сообщение об ошибке.

        Args:
            message: Текст ошибки.
        """
        messagebox.showerror(self.translations['error_title'], message)
        self._log(f"ОШИБКА: {message}")

    def _show_success(self, message: str, rag_info: dict) -> None:
        """
        Показывает сообщение об успехе.

        Args:
            message: Текст сообщения.
            rag_info: Информация о созданной RAG-базе.
        """
        full_message = f"{message}\n\n"
        full_message += self.translations['rag_base_location'].format(rag_info.get('rag_dir', ''))
        full_message += f"\n{self.translations['total_files'].format(rag_info.get('total_files', 0))}"
        full_message += f"\n{self.translations['total_pages'].format(rag_info.get('total_pages', 0))}"
        full_message += f"\n{self.translations['total_chunks'].format(rag_info.get('total_chunks', 0))}"

        messagebox.showinfo(self.translations['success_title'], full_message)

    def complete_processing(self, rag_info: dict) -> None:
        """
        Завершает обработку и показывает результаты.

        Args:
            rag_info: Информация о созданной RAG-базе.
        """
        self.progress.stop()
        self.progress_label.config(text=self.translations['processing_complete'])
        self._log(self.translations['processing_complete'])

        self._show_success(self.translations['rag_base_created'], rag_info)

        self.is_processing = False
        self.process_button.config(state='normal')
        self.load_button.config(state='normal')
        self._update_ui()


def main():
    """Главная функция для запуска UI."""
    root = tk.Tk()

    # Настройка стиля
    style = ttk.Style()
    style.theme_use('clam')

    # Создаём UI
    app = RAGBuilderUI(root, language='ru')

    # Обработчики событий
    def on_rag_created(config: dict):
        print(f"Создание RAG-базы: {config['rag_name']}")
        print(f"Файлов: {len(config['files'])}")
        print(f"Статистика: {config['stats']}")

        # Здесь будет вызов модуля создания RAG-базы
        # После завершения вызываем app.complete_processing(rag_info)

        # Симуляция
        import time
        time.sleep(2)

        rag_info = {
            'rag_dir': f'rag_bases/{config["rag_name"]}',
            'total_files': config['stats']['total_files'],
            'total_pages': config['stats']['total_pages'],
            'total_chunks': 1234
        }

        app.complete_processing(rag_info)

    app.on_rag_created = on_rag_created

    # Обработка закрытия окна
    def on_closing():
        app.loader.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()


if __name__ == "__main__":
    main()
