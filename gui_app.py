"""
Графическое приложение "Соковыжималка" для обработки PDF файлов.

Интегрирует UI загрузки PDF с модулем предобработки текста.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.pdf_loader import PDFLoaderUI
from src.preprocessor import process_pdf
from src.pdf_analyzer import analyze_pdf

# Настройка логирования
def setup_logging():
    """Настраивает логирование с поддержкой UTF-8."""
    # Убедимся, что директория для логов существует
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Очищаем существующие обработчики
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Устанавливаем уровень логирования
    root_logger.setLevel(logging.INFO)

    # Формат логов
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Файловый обработчик с кодировкой UTF-8
    file_handler = logging.FileHandler('logs/gui_app.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

setup_logging()
logger = logging.getLogger(__name__)


# Расширенные переводы для нового UI
EXTENDED_TRANSLATIONS = {
    'ru': {
        'window_title': 'Соковыжималка — Обработка PDF',
        'settings': 'Настройки',
        'chunk_size': 'Размер чанка',
        'overlap': 'Перекрытие',
        'embedding_model': 'Модель эмбеддингов',
        'llm_model': 'Модель LLM',
        'output_dir': 'Выходная директория',
        'enable_vectorization': 'Включить векторизацию',
        'enable_chunking': 'Включить чанкинг',
        'enable_llm': 'Включить LLM (обогащение метаданных)',
        'browse': 'Обзор',
        'load_files': 'Загрузить файлы',
        'process_all': 'Обработать все',
        'files_selected': 'Выбрано файлов: {}',
        'no_files': 'Файлы не выбраны',
        'processing_file': 'Обработка: {}',
        'all_processed': 'Все файлы обработаны!',
        'total_chunks': 'Всего чанков',
        'total_vectors': 'Всего векторов',
        'clear_list': 'Очистить',
        'select_output': 'Выберите выходную директорию',
        'llm_enhanced': 'LLM-обогащение',
    },
    'en': {
        'window_title': 'Squeezer — PDF Processing',
        'settings': 'Settings',
        'chunk_size': 'Chunk size',
        'overlap': 'Overlap',
        'embedding_model': 'Embedding model',
        'llm_model': 'LLM model',
        'output_dir': 'Output directory',
        'enable_vectorization': 'Enable vectorization',
        'enable_chunking': 'Enable chunking',
        'enable_llm': 'Enable LLM (metadata enrichment)',
        'browse': 'Browse',
        'load_files': 'Load files',
        'process_all': 'Process all',
        'files_selected': 'Files selected: {}',
        'no_files': 'No files selected',
        'processing_file': 'Processing: {}',
        'all_processed': 'All files processed!',
        'total_chunks': 'Total chunks',
        'total_vectors': 'Total vectors',
        'clear_list': 'Clear',
        'select_output': 'Select output directory',
        'llm_enhanced': 'LLM-enhanced',
    }
}

# Модели эмбеддингов
EMBEDDING_MODELS = [
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002"
]

# Модели LLM с пояснениями для GUI
# Формат: (model_name, display_name, description, use_case)
LLM_MODELS = [
    # === OpenAI ===
    ("gpt-4o-mini", "GPT-4o Mini", "⚡ Быстрая и дешёвая", "Для обычной обработки"),
    ("gpt-4o", "GPT-4o", "⭐ Лучшее качество OpenAI", "Для важных задач"),
    
    # === Anthropic (Claude) ===
    ("claude-sonnet-4-6", "Claude Sonnet 4.6", "🏆 Лучший баланс (1M контекст)", "Рекомендуется"),
    ("claude-haiku-4-5", "Claude Haiku 4.5", "💨 Быстрый Claude", "Для экономии"),
    ("claude-opus-4-6", "Claude Opus 4.6", "👑 Максимальное качество", "Для сложных задач"),
]


class SqueezerApp:
    """
    Основное приложение "Соковыжималка".
    """

    # Цветовые темы
    THEMES = {
        'light': {
            'bg': '#ffffff',
            'fg': '#000000',
            'entry_bg': '#ffffff',
            'button_bg': '#e0e0e0',
            'button_fg': '#000000',
            'accent': '#0078d4',
            'highlight': '#f0f0f0',
            'border': '#cccccc',
            'listbox_bg': '#ffffff',
            'listbox_fg': '#000000',
            'text_bg': '#ffffff',
            'text_fg': '#000000',
        },
        'dark': {
            'bg': '#1e1e1e',
            'fg': '#d4d4d4',
            'entry_bg': '#2d2d2d',
            'button_bg': '#3d3d3d',
            'button_fg': '#d4d4d4',
            'accent': '#0078d4',
            'highlight': '#2d2d2d',
            'border': '#3d3d3d',
            'listbox_bg': '#2d2d2d',
            'listbox_fg': '#d4d4d4',
            'text_bg': '#1e1e1e',
            'text_fg': '#d4d4d4',
        }
    }

    def __init__(self, root, language='ru'):
        """
        Инициализация приложения.

        Args:
            root: Корневое окно Tkinter.
            language: Язык интерфейса ('ru' или 'en').
        """
        self.root = root
        self.language = language
        self.translations = {**EXTENDED_TRANSLATIONS.get(language, EXTENDED_TRANSLATIONS['ru'])}
        self.current_file_path = None
        self.processing_result = None
        self.selected_files: List[Path] = []
        self.current_theme = 'light'  # По умолчанию светлая тема
        self.theme_colors = self.THEMES[self.current_theme]

        # История файлов
        self.file_history: List[Path] = []
        self.max_history = 20

        # Настройки по умолчанию
        self.settings = {
            'chunk_size': 500,
            'overlap': 50,
            'embedding_model': 'text-embedding-3-small',
            'llm_model': LLM_MODELS[0][0],  # Первая модель из списка (gpt-4o-mini)
            'output_dir': './output/',
            'enable_vectorization': True,
            'enable_chunking': True,
            'enable_llm': True,  # LLM включен по умолчанию
            'ocr_enabled': True
        }

        # Создаём UI
        self.ui = PDFLoaderUI(
            root,
            language=language,
            on_file_loaded=self._on_file_loaded,
            on_processing_complete=self._on_processing_complete
        )

        # Добавляем расширенный UI
        self._setup_extended_ui()

        logger.info("Приложение инициализировано")

    def _setup_extended_ui(self) -> None:
        """Настраивает расширенный пользовательский интерфейс с настройками."""
        self.root.title(self.translations['window_title'])
        self.root.geometry('700x750')
        
        # Загружаем историю
        self._load_history()
        
        # Очищаем и перестраиваем основной контейнер
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Основной контейнер с прокруткой
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Верхняя панель с заголовком и кнопками
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        top_frame.columnconfigure(1, weight=1)
        
        # Заголовок
        title_label = ttk.Label(
            top_frame,
            text=self.translations['window_title'],
            font=('Arial', 18, 'bold')
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Кнопки темы и истории (справа)
        self.theme_btn = ttk.Button(
            top_frame,
            text="🌙 Тёмная",
            command=self._toggle_theme,
            width=15
        )
        self.theme_btn.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))
        
        # Кнопка истории
        history_btn = ttk.Menubutton(
            top_frame,
            text="📋 История",
            width=12
        )
        history_btn.grid(row=0, column=2, sticky=tk.E, padx=(10, 0))
        
        # Создаём меню истории
        self.history_menu = tk.Menu(history_btn, tearoff=0)
        history_btn.configure(menu=self.history_menu)
        self._update_history_menu()
        
        # === Секция выбора файлов ===
        file_section = ttk.LabelFrame(main_frame, text=self.translations['load_files'], padding="10")
        file_section.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_section.columnconfigure(0, weight=1)
        
        # Кнопки выбора файлов
        button_row = ttk.Frame(file_section)
        button_row.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.load_files_btn = ttk.Button(
            button_row,
            text=self.translations['load_files'],
            command=self._select_files
        )
        self.load_files_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_btn = ttk.Button(
            button_row,
            text=self.translations['clear_list'],
            command=self._clear_files
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Кнопка анализа
        self.analyze_btn = ttk.Button(
            button_row,
            text="Анализ",
            command=self._analyze_files
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Список файлов
        self.files_listbox = tk.Listbox(file_section, height=6, selectmode=tk.EXTENDED)
        self.files_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.files_scroll = ttk.Scrollbar(file_section, orient=tk.VERTICAL, command=self.files_listbox.yview)
        self.files_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.files_listbox.config(yscrollcommand=self.files_scroll.set)
        
        self.files_count_label = ttk.Label(file_section, text=self.translations['no_files'])
        self.files_count_label.grid(row=2, column=0, sticky=tk.W)
        
        # Галочка для LLM-анализа
        self.llm_analysis_var = tk.BooleanVar(value=True)  # По умолчанию включено
        ttk.Checkbutton(
            file_section,
            text="LLM-анализ (AI)",
            variable=self.llm_analysis_var
        ).grid(row=3, column=0, sticky=tk.W, pady=(10, 0))
        
        # === Секция настроек ===
        settings_section = ttk.LabelFrame(main_frame, text=self.translations['settings'], padding="10")
        settings_section.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_section.columnconfigure(1, weight=1)
        
        # Размер чанка
        ttk.Label(settings_section, text=self.translations['chunk_size']).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.chunk_size_var = tk.IntVar(value=self.settings['chunk_size'])
        self.chunk_size_spin = ttk.Spinbox(settings_section, from_=100, to=2000, increment=50, textvariable=self.chunk_size_var, width=15)
        self.chunk_size_spin.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Перекрытие
        ttk.Label(settings_section, text=self.translations['overlap']).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.overlap_var = tk.IntVar(value=self.settings['overlap'])
        self.overlap_spin = ttk.Spinbox(settings_section, from_=0, to=200, increment=10, textvariable=self.overlap_var, width=15)
        self.overlap_spin.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Модель эмбеддингов
        ttk.Label(settings_section, text=self.translations['embedding_model']).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.embedding_model_var = tk.StringVar(value=self.settings['embedding_model'])
        self.embedding_model_combo = ttk.Combobox(
            settings_section, 
            textvariable=self.embedding_model_var,
            values=EMBEDDING_MODELS,
            state='readonly',
            width=25
        )
        self.embedding_model_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Выходная директория
        ttk.Label(settings_section, text=self.translations['output_dir']).grid(row=3, column=0, sticky=tk.W, pady=5)
        output_frame = ttk.Frame(settings_section)
        output_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        output_frame.columnconfigure(0, weight=1)
        
        self.output_dir_var = tk.StringVar(value=self.settings['output_dir'])
        ttk.Entry(output_frame, textvariable=self.output_dir_var).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(output_frame, text=self.translations['browse'], command=self._browse_output_dir).grid(row=0, column=1)
        
        # Чекбоксы
        self.enable_chunking_var = tk.BooleanVar(value=self.settings['enable_chunking'])
        ttk.Checkbutton(
            settings_section, 
            text=self.translations['enable_chunking'],
            variable=self.enable_chunking_var
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        self.enable_llm_var = tk.BooleanVar(value=self.settings['enable_llm'])
        ttk.Checkbutton(
            settings_section, 
            text=self.translations['enable_llm'],
            variable=self.enable_llm_var
        ).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Модель LLM (выбор модели для обогащения)
        ttk.Label(settings_section, text=self.translations['llm_model']).grid(row=6, column=0, sticky=tk.W, pady=5)
        
        # Создаём отображаемые названия для combobox
        llm_display_names = [f"{m[1]} - {m[3]}" for m in LLM_MODELS]
        self.llm_model_display_var = tk.StringVar(value=llm_display_names[0])  # По умолчанию первая
        
        self.llm_model_combo = ttk.Combobox(
            settings_section, 
            textvariable=self.llm_model_display_var,
            values=llm_display_names,
            state='readonly',
            width=40
        )
        self.llm_model_combo.grid(row=6, column=1, sticky=tk.W, pady=5)
        
        # Описание выбранной модели
        self.llm_model_desc_label = ttk.Label(
            settings_section, 
            text=LLM_MODELS[0][2],  # Описание первой модели
            font=('Arial', 9, 'italic'),
            foreground='gray'
        )
        self.llm_model_desc_label.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # Callback для обновления описания при смене модели
        def on_model_change(event):
            idx = self.llm_model_combo.current()
            if idx >= 0:
                self.llm_model_desc_label.config(text=LLM_MODELS[idx][2])
                self.settings['llm_model'] = LLM_MODELS[idx][0]
        
        self.llm_model_combo.bind('<<ComboboxSelected>>', on_model_change)
        
        self.enable_vectorization_var = tk.BooleanVar(value=self.settings['enable_vectorization'])
        ttk.Checkbutton(
            settings_section, 
            text=self.translations['enable_vectorization'],
            variable=self.enable_vectorization_var
        ).grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # === Прогресс ===
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.progress_label = ttk.Label(main_frame, text="")
        self.progress_label.grid(row=4, column=0, sticky=tk.W, pady=(0, 10))
        
        # === Кнопка обработки ===
        self.process_btn = ttk.Button(
            main_frame,
            text=self.translations['process_all'],
            command=self._process_all_files,
            state='disabled'
        )
        self.process_btn.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # === Лог ===
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        from tkinter.scrolledtext import ScrolledText
        self.log_text = ScrolledText(log_frame, height=10, width=60, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        main_frame.rowconfigure(6, weight=1)
        
        # Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _select_files(self) -> None:
        """Выбор файлов для обработки."""
        file_paths = filedialog.askopenfilenames(
            title=self.translations['load_files'],
            filetypes=[('PDF files', '*.pdf'), ('All files', '*.*')]
        )
        
        if not file_paths:
            return
        
        self.selected_files = [Path(p) for p in file_paths]
        self._update_files_list()
    
    def _update_files_list(self) -> None:
        """Обновляет список выбранных файлов."""
        self.files_listbox.delete(0, tk.END)
        
        for file_path in self.selected_files:
            self.files_listbox.insert(tk.END, file_path.name)
        
        count = len(self.selected_files)
        self.files_count_label.config(text=self.translations['files_selected'].format(count))
        self.process_btn.config(state='normal' if count > 0 else 'disabled')
    
    def _clear_files(self) -> None:
        """Очищает список файлов."""
        self.selected_files = []
        self._update_files_list()
    
    def _analyze_files(self) -> None:
        """Анализирует выбранные файлы и показывает рекомендации."""
        if not self.selected_files:
            messagebox.showwarning('Предупреждение', 'Сначала выберите файлы')
            return
        
        if len(self.selected_files) > 1:
            messagebox.showinfo('Информация', 'Анализ будет проведён для первого файла')
        
        # Проверяем использование LLM
        use_llm = self.llm_analysis_var.get()
        
        # Анализируем первый файл
        file_path = self.selected_files[0]
        self._log(f"Анализ файла: {file_path.name}" + (" с LLM" if use_llm else ""))
        
        try:
            # Получаем API ключ
            api_key = os.getenv("OPENAI_API_KEY")
            if use_llm and not api_key:
                messagebox.showwarning('Внимание', 'OPENAI_API_KEY не найден. LLM-анализ недоступен.')
                use_llm = False
            
            # Вызываем анализ
            llm_model = self.llm_model_var.get() if use_llm else "gpt-4o"
            
            analysis = analyze_pdf(
                str(file_path),
                use_llm=use_llm,
                llm_model=llm_model,
                api_key=api_key,
                api_base="https://openai.api.proxyapi.ru/v1"
            )

            if "error" in analysis:
                messagebox.showerror('Ошибка', f"Анализ не удался: {analysis['error']}")
                return
            
            rec = analysis.get("recommendations", {})
            
            # Показываем индикатор LLM
            llm_badge = " [AI]" if use_llm and analysis.get("llm_analysis") else ""
            
            # LLM анализ
            llm_info = ""
            if analysis.get("llm_analysis"):
                llm = analysis["llm_analysis"]
                llm_info = f"\n\n[AI Анализ]\n"
                llm_info += f"Описание: {llm.get('description', 'N/A')}\n"
                llm_info += f"Темы: {', '.join(llm.get('topics', []))}\n"
                llm_info += f"Стиль: {llm.get('language_style', 'N/A')}\n"
                if llm.get("reasoning"):
                    llm_info += f"Обоснование: {llm['reasoning']}"
            
            # Формируем сообщение с результатами
            msg = f"[ANALIZ DOKUMENTA{llm_badge}]\n"
            msg += f"{'='*40}\n\n"
            msg += f"Tip dokumenta: {analysis.get('document_type', 'unknown')}\n"
            msg += f"Yazik: {analysis.get('languages', ['unknown'])}\n"
            msg += f"Stranic: {analysis.get('total_pages')}\n"
            msg += f"Plotnost: {analysis.get('density')}\n"
            msg += f"Slozhnost: {analysis.get('complexity')}\n"
            msg += llm_info + "\n"
            
            msg += f"\n[REKOMENDACII:]\n"
            msg += f"  Razmer chanka: {rec.get('chunk_size')}\n"
            msg += f"  Overlap: {rec.get('overlap')}\n"
            msg += f"  Strategiya: {rec.get('chunking_strategy')}\n"
            msg += f"  OCR: {'Da' if rec.get('ocr_enabled') else 'Net'}\n"
            msg += f"  LLM: {'Da' if rec.get('llm_enabled') else 'Net'}\n\n"
            
            if rec.get("rationale"):
                msg += f"[OBOSNOVANIE:]\n"
                for r in rec.get("rationale", []):
                    msg += f"  - {r}\n"
            
            msg += f"\n{'='*40}\n"
            msg += f"Primenit rekomendacii?"
            
            # Показываем результат и спрашиваем
            result = messagebox.askyesno("Результаты анализа", msg)
            
            if result:
                # Применяем рекомендации
                self.chunk_size_var.set(rec.get('chunk_size', 500))
                self.overlap_var.set(rec.get('overlap', 50))
                
                if rec.get('ocr_enabled'):
                    self.settings['ocr_enabled'] = True
                
                self._log(f"Рекомендации применены: chunk={rec.get('chunk_size')}, overlap={rec.get('overlap')}")
                messagebox.showinfo("Готово", "Рекомендации применены к настройкам")
            
        except Exception as e:
            self._log(f"Ошибка анализа: {str(e)}")
            messagebox.showerror('Ошибка', f"Анализ не удался: {str(e)}")
    
    def _browse_output_dir(self) -> None:
        """Выбор выходной директории."""
        dir_path = filedialog.askdirectory(title=self.translations['select_output'])
        if dir_path:
            self.output_dir_var.set(dir_path)
    
    def _save_settings(self) -> None:
        """Сохраняет текущие настройки из UI."""
        self.settings['chunk_size'] = self.chunk_size_var.get()
        self.settings['overlap'] = self.overlap_var.get()
        self.settings['embedding_model'] = self.embedding_model_var.get()
        
        # Получаем модель LLM из индекса combobox
        idx = self.llm_model_combo.current()
        if idx >= 0:
            self.settings['llm_model'] = LLM_MODELS[idx][0]
        
        self.settings['output_dir'] = self.output_dir_var.get()
        self.settings['enable_chunking'] = self.enable_chunking_var.get()
        self.settings['enable_llm'] = self.enable_llm_var.get()
        self.settings['enable_vectorization'] = self.enable_vectorization_var.get()
    
    def _log(self, message: str) -> None:
        """Добавляет сообщение в лог."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        logger.info(message)
    
    def _process_all_files(self) -> None:
        """Обрабатывает все выбранные файлы (с опцией параллельной обработки)."""
        if not self.selected_files:
            messagebox.showwarning('Предупреждение', self.translations['no_files'])
            return
        
        self._save_settings()
        
        # Спрашиваем про режим обработки
        if len(self.selected_files) > 1:
            use_parallel = messagebox.askyesno(
                "Режим обработки",
                f"Обработать {len(self.selected_files)} файлов параллельно?\n\n"
                "Да - быстрее (использует больше ресурсов)\n"
                "Нет - последовательно"
            )
        else:
            use_parallel = False

        # Блокируем кнопки
        self.process_btn.config(state='disabled')
        self.load_files_btn.config(state='disabled')
        self.clear_btn.config(state='disabled')
        
        # Запускаем прогресс
        self.progress.start()
        
        total_chunks = 0
        processed_count = 0
        
        if use_parallel and len(self.selected_files) > 1:
            # Параллельная обработка
            self._log(f"Параллельная обработка {len(self.selected_files)} файлов...")
            total_chunks, processed_count = self._process_parallel()
        else:
            # Последовательная обработка
            for i, file_path in enumerate(self.selected_files, 1):
                self.progress_label.config(text=self.translations['processing_file'].format(file_path.name))
                self._log(f"Обработка [{i}/{len(self.selected_files)}]: {file_path.name}")
                
                chunks = self._process_single_file(file_path)
                total_chunks += chunks
                processed_count += 1
                
                # Добавляем в историю
                self._add_to_history(file_path)
        
        # Останавливаем прогресс
        self.progress.stop()
        self.progress_label.config(text=self.translations['all_processed'])
        
        # Разблокируем кнопки
        self.process_btn.config(state='normal')
        self.load_files_btn.config(state='normal')
        self.clear_btn.config(state='normal')
        
        # Итоговое сообщение
        result_msg = f"{self.translations['all_processed']}\n\n"
        result_msg += f"{self.translations['total_chunks']}: {total_chunks}\n"
        result_msg += f"Обработано файлов: {processed_count}/{len(self.selected_files)}\n"
        result_msg += f"\nРезультаты сохранены в: {self.settings['output_dir']}"
        
        self._log(f"Обработка завершена. Чанков: {total_chunks}")
        
        messagebox.showinfo(self.translations['success_title'], result_msg)

    def _process_single_file(self, file_path: Path) -> int:
        """Обрабатывает один файл. Возвращает количество чанков."""
        try:
            # Проверяем API ключ (единый для всех моделей через proxyAPI)
            api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                self._log("WARNING: OPENAI_API_KEY not found. Skipping vectorization and LLM.")
                self.settings['enable_vectorization'] = False
                self.settings['enable_llm'] = False
            else:
                self._log(f"API key found. LLM model: {self.settings['llm_model']}")
        
            result = process_pdf(
                str(file_path),
                self.settings['output_dir'],
                ocr_enabled=self.settings['ocr_enabled'],
                ocr_lang='rus+eng',
                enable_chunking=self.settings['enable_chunking'],
                max_chunk_size=self.settings['chunk_size'],
                overlap=self.settings['overlap'],
                enable_vectorization=self.settings['enable_vectorization'],
                embedding_model=self.settings['embedding_model'],
                api_key=api_key,
                api_base="https://openai.api.proxyapi.ru/v1",
                use_llm=self.settings['enable_llm'],
                llm_model=self.settings['llm_model']
            )

            # Логируем результат LLM-обогащения
            if result.get('llm_enhanced'):
                self._log(f"  -> LLM enrichment completed")

            chunks = len(result.get('chunks', []))
            self._log(f"  -> Done: {chunks} chunks")
            return chunks
            
        except Exception as e:
            self._log(f"  -> Error: {str(e)}")
            logger.error(f"Error processing {file_path.name}: {e}")
            return 0

    def _process_parallel(self) -> tuple:
        """Параллельная обработка файлов."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        total_chunks = 0
        processed_count = 0
        results_lock = threading.Lock()
        
        def process_file_wrapper(file_path):
            nonlocal total_chunks, processed_count
            chunks = self._process_single_file(file_path)
            with results_lock:
                total_chunks += chunks
                processed_count += 1
            return file_path, chunks
        
        # Используем ThreadPoolExecutor для параллельной обработки
        max_workers = min(4, len(self.selected_files))  # Максимум 4 потока
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_file_wrapper, fp): fp for fp in self.selected_files}
            
            for future in as_completed(futures):
                file_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self._log(f"  → Ошибка: {str(e)}")
        
        return total_chunks, processed_count
    
    def _on_closing(self) -> None:
        """Обработка закрытия окна."""
        self.root.destroy()

    def _toggle_theme(self) -> None:
        """Переключение между светлой и тёмной темой."""
        if self.current_theme == 'light':
            self.current_theme = 'dark'
            self.theme_btn.config(text="☀️ Светлая")
        else:
            self.current_theme = 'light'
            self.theme_btn.config(text="🌙 Тёмная")
        
        self.theme_colors = self.THEMES[self.current_theme]
        self._apply_theme()
        logger.info(f"Тема изменена на: {self.current_theme}")

    def _apply_theme(self) -> None:
        """Применяет текущую тему к элементам интерфейса."""
        colors = self.theme_colors
        
        # Основное окно
        self.root.configure(bg=colors['bg'])
        
        # Применяем ко всем элементам (рекурсивно)
        self._apply_theme_to_widget(self.root, colors)

    def _apply_theme_to_widget(self, widget, colors: dict) -> None:
        """Рекурсивно применяет тему к виджету и его потомкам."""
        try:
            # Основные виджеты
            widget_class = widget.winfo_class()
            
            if widget_class in ['TFrame', 'TLabelframe']:
                widget.configure(style='Custom.T' + widget_class)
            elif widget_class == 'TLabel':
                widget.configure(foreground=colors['fg'])
            elif widget_class == 'TButton':
                widget.configure(style='Custom.TButton')
            elif widget_class == 'TCheckbutton':
                widget.configure(foreground=colors['fg'])
            elif widget_class == 'TEntry':
                widget.configure(fieldbackground=colors['entry_bg'], foreground=colors['fg'])
            elif widget_class == 'TSpinbox':
                widget.configure(fieldbackground=colors['entry_bg'], foreground=colors['fg'])
            elif widget_class == 'TCombobox':
                widget.configure(fieldbackground=colors['entry_bg'], foreground=colors['fg'])
            
            # Listbox
            if widget_class == 'Listbox':
                widget.configure(bg=colors['listbox_bg'], fg=colors['listbox_fg'], selectbackground=colors['accent'])
            
            # Text/ScrolledText
            if widget_class in ['Text', 'ScrolledText']:
                widget.configure(bg=colors['text_bg'], fg=colors['text_fg'], insertbackground=colors['fg'])
            
        except Exception:
            pass  # Игнорируем ошибки для неподдерживаемых виджетов
        
        # Рекурсивно обрабатываем потомков
        try:
            for child in widget.winfo_children():
                self._apply_theme_to_widget(child, colors)
        except Exception:
            pass

    def _load_history(self) -> None:
        """Загружает историю файлов."""
        history_file = Path('logs/file_history.txt')
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        path = Path(line.strip())
                        if path.exists() and path.suffix.lower() == '.pdf':
                            self.file_history.append(path)
                
                # Ограничиваем историю
                self.file_history = self.file_history[-self.max_history:]
                logger.info(f"Загружено {len(self.file_history)} файлов из истории")
            except Exception as e:
                logger.warning(f"Не удалось загрузить историю: {e}")

    def _save_history(self) -> None:
        """Сохраняет историю файлов."""
        history_file = Path('logs/file_history.txt')
        history_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                for path in self.file_history[-self.max_history:]:
                    f.write(str(path) + '\n')
        except Exception as e:
            logger.warning(f"Не удалось сохранить историю: {e}")

    def _add_to_history(self, file_path: Path) -> None:
        """Добавляет файл в историю."""
        if file_path not in self.file_history:
            self.file_history.insert(0, file_path)
            # Ограничиваем историю
            if len(self.file_history) > self.max_history:
                self.file_history = self.file_history[:self.max_history]
            self._save_history()
            self._update_history_menu()

    def _update_history_menu(self) -> None:
        """Обновляет меню истории."""
        if hasattr(self, 'history_menu'):
            # Очищаем меню
            self.history_menu.delete(0, tk.END)
            
            if not self.file_history:
                self.history_menu.add_command(label="История пуста", state='disabled')
            else:
                for i, path in enumerate(self.file_history[:10]):  # Показываем последние 10
                    self.history_menu.add_command(
                        label=f"{i+1}. {path.name}",
                        command=lambda p=path: self._load_from_history(p)
                    )

    def _load_from_history(self, file_path: Path) -> None:
        """Загружает файл из истории."""
        if file_path.exists():
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)
                self._update_files_list()
            self._log(f"Загружен из истории: {file_path.name}")
        else:
            messagebox.showwarning('Файл не найден', f'Файл удалён: {file_path}')
            # Удаляем из истории
            if file_path in self.file_history:
                self.file_history.remove(file_path)
                self._save_history()
                self._update_history_menu()

    def _on_file_loaded(self, file_path: Path):
        """
        Callback при загрузке файла.

        Args:
            file_path: Путь к загруженному файлу.
        """
        self.current_file_path = file_path
        logger.info(f"Файл загружен через UI: {file_path}")

    def _on_processing_complete(self, file_info: dict):
        """
        Callback при завершении обработки.

        Args:
            file_info: Информация о файле.
        """
        logger.info(f"Обработка завершена: {file_info}")

        # Обновляем UI с результатами
        if self.processing_result:
            stats = self.processing_result.get('stats', {})

            result_message = f"""
{self.ui.translations['processing_complete']}

{self.ui.translations['file_name']}: {file_info.get('name', '')}
{self.ui.translations['file_pages']}: {file_info.get('pages', 0)}

{self.ui.translations['file_info']}:
  {self.ui.translations['file_pages']}: {stats.get('structuring', {}).get('headings', 0)} заголовков
  Абзацев: {stats.get('structuring', {}).get('paragraphs', 0)}
  Списков: {stats.get('structuring', {}).get('lists', 0)}
"""

            # Добавляем информацию о чанкинге, если он был выполнен
            if 'chunks' in self.processing_result:
                chunks = self.processing_result.get('chunks', [])
                result_message += f"""
Этап 5-6: Чанкинг и метаданные
  Всего чанков: {len(chunks)}
  Средняя длина: {sum(c['metadata']['char_count'] for c in chunks) / len(chunks):.2f} символов
  Мин/Макс длина: {min(c['metadata']['char_count'] for c in chunks)}/{max(c['metadata']['char_count'] for c in chunks)}

Отчёт по чанкингу: output_module_3/chunking_report.txt
"""

                # Добавляем информацию о демонстрационном файле
                if 'chunking_demo_path' in self.processing_result:
                    result_message += f"""
Демонстрация чанкинга: output_module_3/content_demonstrator.txt
"""

            # Добавляем информацию о векторизации, если она была выполнена
            if 'vectorization' in self.processing_result:
                vectorization = self.processing_result.get('vectorization', {})
                vec_stats = vectorization.get('validation', {}).get('stats', {})
                vec_result = vectorization.get('vectorization', {})

                result_message += f"""
Этап 7-8: Векторизация и векторная БД
  Проверено чанков: {vec_stats.get('total_chunks', 0)}
  Пустых чанков: {vec_stats.get('empty_chunks', 0)}
  Средняя длина: {vec_stats.get('avg_char_count', 0):.2f} символов

  Модель эмбеддингов: {vec_result.get('embedding_dim', 0)}D ({vec_result.get('total_vectors', 0)} векторов)
  Тип БД: FAISS
  Путь к индексу: output/vector_db/index.faiss
  Путь к датасету: output/vector_db/dataset.json

Отчёт по векторизации: output_module_4/vectorization_report.txt
"""

            result_message += f"""
Результаты сохранены в: output_module_2/
"""

            from tkinter import messagebox
            messagebox.showinfo(
                self.ui.translations['success_title'],
                result_message.strip()
            )

    def process_pdf_file(
        self,
        file_path: Path,
        output_dir: str = './output_module_2/',
        enable_vectorization: bool = True,
        embedding_model: str = "text-embedding-3-small",
        vector_db_type: str = "faiss",
        api_key: str = None,
        api_base: str = "https://openai.api.proxyapi.ru/v1"
    ) -> dict:
        """
        Обрабатывает PDF файл.

        Args:
            file_path: Путь к PDF файлу.
            output_dir: Директория для сохранения результатов.
            enable_vectorization: Включить этапы 7-8 (векторизация и БД).
            embedding_model: Модель эмбеддингов.
            vector_db_type: Тип векторной БД.
            api_key: API ключ OpenAI.
            api_base: Базовый URL API.

        Returns:
            Результаты обработки.
        """
        logger.info(f"Начало обработки файла: {file_path}")

        try:
            result = process_pdf(
                str(file_path),
                output_dir,
                ocr_enabled=False,
                ocr_lang='rus+eng',
                enable_chunking=True,      # Включаем этапы 5-6 (чанкинг)
                max_chunk_size=500,        # Максимальный размер чанка
                overlap=50,                # Перекрытие между чанками
                enable_vectorization=enable_vectorization,  # Включаем этапы 7-8
                embedding_model=embedding_model,
                vector_db_type=vector_db_type,
                api_key=api_key,
                api_base=api_base
            )

            self.processing_result = result
            return result

        except Exception as e:
            logger.error(f"Ошибка при обработке файла: {e}")
            raise

    def run(self):
        """Запускает приложение."""
        # Заменяем симуляцию обработки на реальную
        original_simulate = self.ui._simulate_processing

        def real_processing():
            try:
                if not self.current_file_path:
                    raise Exception("Файл не загружен")

                # Обрабатываем PDF
                result = self.process_pdf_file(self.current_file_path)

                # Останавливаем прогресс бар
                self.ui.progress.stop()
                self.ui.progress_label.config(text=self.ui.translations['processing_complete'])
                self.ui._log(self.ui.translations['processing_complete'])

                # Показываем результаты
                file_info = self.ui.get_file_info()
                self._on_processing_complete(file_info)

            except Exception as e:
                self.ui.progress.stop()
                self.ui.progress_label.config(text=self.ui.translations['processing_failed'])
                self.ui._log(f"Ошибка: {str(e)}")
                self.ui._show_error(self.ui.translations['processing_failed'])

            finally:
                self.ui.is_processing = False
                self.ui.process_button.config(state='normal')
                self.ui.load_button.config(state='normal')

        # Подменяем метод
        self.ui._simulate_processing = real_processing

        # Запускаем главный цикл
        self.root.mainloop()


def main():
    """Главная функция для запуска приложения."""
    root = tk.Tk()

    # Настройка стиля
    style = ttk.Style()
    style.theme_use('clam')

    # Создаём приложение
    app = SqueezerApp(root, language='ru')

    # Запускаем главный цикл
    root.mainloop()


if __name__ == "__main__":
    main()
