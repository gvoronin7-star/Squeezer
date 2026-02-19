"""
Модуль 2.1: Пользовательский интерфейс для загрузки PDF-файла.

Реализует графический интерфейс для выбора, валидации и сохранения PDF файлов
во временное хранилище для дальнейшей обработки.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple, Callable
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
        'window_title': 'Соковыжималка — Загрузка PDF',
        'load_button': 'Загрузить PDF',
        'process_button': 'Обработать',
        'select_file': 'Выберите PDF-файл',
        'file_selected': 'Выбран файл: {}',
        'processing': 'Обработка...',
        'error_title': 'Ошибка',
        'success_title': 'Успех',
        'invalid_format': 'Неверный формат. Выберите файл .pdf',
        'cannot_open': 'Не удалось открыть файл. Проверьте целостность PDF',
        'no_access': 'Нет доступа к папке для временных файлов',
        'file_not_selected': 'Выберите PDF-файл',
        'processing_complete': 'Обработка завершена',
        'processing_failed': 'Обработка не удалась',
        'progress': 'Прогресс',
        'pages': 'страниц',
        'upload_complete': 'Загрузка завершена',
        'file_info': 'Информация о файле',
        'file_name': 'Имя файла',
        'file_size': 'Размер файла',
        'file_pages': 'Количество страниц',
        'cancel': 'Отмена'
    },
    'en': {
        'window_title': 'Squeezer — PDF Upload',
        'load_button': 'Upload PDF',
        'process_button': 'Process',
        'select_file': 'Select PDF file',
        'file_selected': 'Selected file: {}',
        'processing': 'Processing...',
        'error_title': 'Error',
        'success_title': 'Success',
        'invalid_format': 'Invalid format. Select .pdf file',
        'cannot_open': 'Failed to open file. Check PDF integrity',
        'no_access': 'No access to temporary files folder',
        'file_not_selected': 'Select PDF file',
        'processing_complete': 'Processing complete',
        'processing_failed': 'Processing failed',
        'progress': 'Progress',
        'pages': 'pages',
        'upload_complete': 'Upload complete',
        'file_info': 'File Information',
        'file_name': 'File Name',
        'file_size': 'File Size',
        'file_pages': 'Number of Pages',
        'cancel': 'Cancel'
    }
}


class PDFLoader:
    """
    Класс для загрузки и валидации PDF файлов.
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
        self.current_file_path: Optional[Path] = None
        self.temp_file_path: Optional[Path] = None

        # Создаём временную директорию
        self._ensure_temp_dir()

        logger.info(f"PDFLoader инициализирован (язык: {language})")

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

    def load_file(self, file_path: Path) -> Tuple[bool, Optional[Path], Optional[str]]:
        """
        Загружает и сохраняет PDF файл во временное хранилище.

        Args:
            file_path: Путь к исходному файлу.

        Returns:
            Кортеж (успех, путь к временному файлу, сообщение об ошибке).
        """
        # Валидация
        is_valid, error_msg = self._validate_pdf(file_path)
        if not is_valid:
            return False, None, error_msg

        try:
            # Создаём уникальное имя для временного файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_filename = f"{timestamp}_{file_path.stem}.pdf"
            temp_path = self.TEMP_DIR / temp_filename

            # Копируем файл во временную директорию
            shutil.copy2(file_path, temp_path)

            self.current_file_path = file_path
            self.temp_file_path = temp_path

            logger.info(f"Файл загружен: {file_path} -> {temp_path}")
            return True, temp_path, None

        except Exception as e:
            logger.error(f"Ошибка при копировании файла: {e}")
            return False, None, str(e)

    def get_file_info(self) -> dict:
        """
        Возвращает информацию о загруженном файле.

        Returns:
            Словарь с информацией о файле.
        """
        if not self.temp_file_path or not self.temp_file_path.exists():
            return {}

        try:
            file_size = self.temp_file_path.stat().st_size
            page_count = self._get_page_count(self.temp_file_path)

            return {
                'name': self.temp_file_path.name,
                'original_name': self.current_file_path.name if self.current_file_path else '',
                'size': file_size,
                'size_mb': file_size / (1024 * 1024),
                'pages': page_count,
                'path': str(self.temp_file_path)
            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о файле: {e}")
            return {}

    def cleanup(self) -> None:
        """Очищает временные файлы."""
        try:
            if self.temp_file_path and self.temp_file_path.exists():
                self.temp_file_path.unlink()
                logger.info(f"Временный файл удалён: {self.temp_file_path}")
        except Exception as e:
            logger.error(f"Ошибка при удалении временного файла: {e}")


class PDFLoaderUI:
    """
    Графический интерфейс для загрузки PDF файлов.
    """

    def __init__(
        self,
        master: tk.Tk,
        language: str = 'ru',
        on_file_loaded: Optional[Callable[[Path], None]] = None,
        on_processing_complete: Optional[Callable[[dict], None]] = None
    ):
        """
        Инициализация UI.

        Args:
            master: Родительское окно Tkinter.
            language: Язык интерфейса ('ru' или 'en').
            on_file_loaded: Callback при загрузке файла.
            on_processing_complete: Callback при завершении обработки.
        """
        if tk is None:
            raise ImportError("Tkinter не установлен. Установите python-tk")

        self.master = master
        self.language = language
        self.on_file_loaded = on_file_loaded
        self.on_processing_complete = on_processing_complete
        self.translations = TRANSLATIONS[language]

        self.loader = PDFLoader(language)
        self.file_info: Optional[dict] = None
        self.is_processing = False

        self._setup_ui()
        logger.info("PDFLoaderUI инициализирован")

    def _setup_ui(self) -> None:
        """Настраивает пользовательский интерфейс."""
        self.master.title(self.translations['window_title'])
        self.master.geometry('600x500')
        self.master.resizable(True, True)

        # Устанавливаем иконку (если есть)
        try:
            # self.master.iconbitmap('icon.ico')
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

        # Секция выбора файла
        file_frame = ttk.LabelFrame(main_frame, text=self.translations['select_file'], padding="10")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)

        # Кнопка выбора файла
        self.load_button = ttk.Button(
            file_frame,
            text=self.translations['load_button'],
            command=self._on_load_button_click
        )
        self.load_button.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Отображение выбранного файла
        self.file_label = ttk.Label(file_frame, text=self.translations['file_not_selected'], wraplength=500)
        self.file_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))

        # Информация о файле
        self.info_frame = ttk.LabelFrame(main_frame, text=self.translations['file_info'], padding="10")
        self.info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.info_frame.columnconfigure(1, weight=1)

        # Метки информации
        ttk.Label(self.info_frame, text=f"{self.translations['file_name']}:").grid(row=0, column=0, sticky=tk.W)
        self.name_label = ttk.Label(self.info_frame, text="-")
        self.name_label.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))

        ttk.Label(self.info_frame, text=f"{self.translations['file_size']}:").grid(row=1, column=0, sticky=tk.W)
        self.size_label = ttk.Label(self.info_frame, text="-")
        self.size_label.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))

        ttk.Label(self.info_frame, text=f"{self.translations['file_pages']}:").grid(row=2, column=0, sticky=tk.W)
        self.pages_label = ttk.Label(self.info_frame, text="-")
        self.pages_label.grid(row=2, column=1, sticky=tk.W)

        # Прогресс бар
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.progress_frame.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E))

        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.grid(row=1, column=0, pady=(5, 0))

        # Лог
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = ScrolledText(log_frame, height=8, width=50, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Кнопки действий
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, sticky=(tk.W, tk.E))

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
        main_frame.rowconfigure(4, weight=1)

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
        """Обработчик нажатия кнопки загрузки файла."""
        file_path = filedialog.askopenfilename(
            title=self.translations['load_button'],
            filetypes=[('PDF files', '*.pdf'), ('All files', '*.*')]
        )

        if not file_path:
            return

        self._load_file(Path(file_path))

    def _load_file(self, file_path: Path) -> None:
        """
        Загружает файл.

        Args:
            file_path: Путь к файлу.
        """
        self._log(f"Загрузка файла: {file_path.name}")

        # Загружаем файл
        success, temp_path, error_msg = self.loader.load_file(file_path)

        if not success:
            self._show_error(error_msg)
            self.file_label.config(text=self.translations['file_not_selected'])
            return

        # Получаем информацию о файле
        self.file_info = self.loader.get_file_info()

        # Обновляем UI
        self.file_label.config(text=self.translations['file_selected'].format(file_path.name))
        self.name_label.config(text=self.file_info.get('name', '-'))
        self.size_label.config(text=f"{self.file_info.get('size_mb', 0):.2f} MB")
        self.pages_label.config(text=str(self.file_info.get('pages', 0)))

        self.process_button.config(state='normal')

        self._log(self.translations['upload_complete'])
        self._log(f"Размер: {self.file_info.get('size_mb', 0):.2f} MB")
        self._log(f"Страниц: {self.file_info.get('pages', 0)}")

        # Callback
        if self.on_file_loaded and temp_path:
            self.on_file_loaded(temp_path)

    def _on_process_button_click(self) -> None:
        """Обработчик нажатия кнопки обработки."""
        if self.is_processing:
            return

        self.is_processing = True
        self.process_button.config(state='disabled')
        self.load_button.config(state='disabled')

        self.progress.start()
        self.progress_label.config(text=self.translations['processing'])
        self._log(self.translations['processing'])

        # Симуляция обработки (в реальности здесь будет вызов модуля обработки)
        self.master.after(100, self._simulate_processing)

    def _simulate_processing(self) -> None:
        """Симулирует обработку файла."""
        try:
            # Здесь будет вызов модуля обработки
            # from src.preprocessor import process_pdf
            # result = process_pdf(self.loader.temp_file_path, './output_module_2/')

            # Симуляция
            import time
            time.sleep(2)

            self.progress.stop()
            self.progress_label.config(text=self.translations['processing_complete'])
            self._log(self.translations['processing_complete'])

            messagebox.showinfo(
                self.translations['success_title'],
                self.translations['processing_complete']
            )

            # Callback
            if self.on_processing_complete and self.file_info:
                self.on_processing_complete(self.file_info)

        except Exception as e:
            self.progress.stop()
            self.progress_label.config(text=self.translations['processing_failed'])
            self._log(f"Ошибка: {str(e)}")
            self._show_error(self.translations['processing_failed'])

        finally:
            self.is_processing = False
            self.process_button.config(state='normal')
            self.load_button.config(state='normal')

    def _on_cancel_button_click(self) -> None:
        """Обработчик нажатия кнопки отмены."""
        if self.is_processing:
            self.is_processing = False
            self.progress.stop()
            self.progress_label.config(text="")
            self._log("Обработка отменена")

        self.loader.cleanup()

        # Сбрасываем UI
        self.file_label.config(text=self.translations['file_not_selected'])
        self.name_label.config(text="-")
        self.size_label.config(text="-")
        self.pages_label.config(text="-")
        self.process_button.config(state='disabled')
        self.log_text.delete(1.0, tk.END)

    def _show_error(self, message: str) -> None:
        """
        Показывает сообщение об ошибке.

        Args:
            message: Текст ошибки.
        """
        messagebox.showerror(self.translations['error_title'], message)
        self._log(f"ОШИБКА: {message}")

    def get_temp_file_path(self) -> Optional[Path]:
        """
        Возвращает путь к временному файлу.

        Returns:
            Путь к временному файлу или None.
        """
        return self.loader.temp_file_path

    def get_file_info(self) -> Optional[dict]:
        """
        Возвращает информацию о загруженном файле.

        Returns:
            Словарь с информацией о файле или None.
        """
        return self.file_info


def main():
    """Главная функция для запуска UI."""
    root = tk.Tk()

    # Настройка стиля
    style = ttk.Style()
    style.theme_use('clam')

    # Создаём UI
    app = PDFLoaderUI(root, language='ru')

    # Обработчики событий
    def on_file_loaded(file_path: Path):
        print(f"Файл загружен: {file_path}")

    def on_processing_complete(file_info: dict):
        print(f"Обработка завершена: {file_info}")

    app.on_file_loaded = on_file_loaded
    app.on_processing_complete = on_processing_complete

    # Обработка закрытия окна
    def on_closing():
        app.loader.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()


if __name__ == "__main__":
    main()
