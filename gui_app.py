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
        """Выбор файлов для обработки с автоматическим анализом."""
        file_paths = filedialog.askopenfilenames(
            title=self.translations['load_files'],
            filetypes=[('PDF files', '*.pdf'), ('All files', '*.*')]
        )
        
        if not file_paths:
            return
        
        self.selected_files = [Path(p) for p in file_paths]
        self._update_files_list()
    
        # Автоматический анализ первого файла
        if self.selected_files:
            self._auto_analyze_file(self.selected_files[0])
    
    def _auto_analyze_file(self, file_path: Path) -> None:
        """
        Автоматический анализ файла с предложением оптимизации.
        Показывает 3 варианта LLM модели на выбор.
        
        Args:
            file_path: Путь к файлу для анализа.
        """
        self._log(f"🔍 Автоанализ: {file_path.name}")
        
        try:
            # Быстрый анализ без LLM
            from src.pdf_analyzer import (
                analyze_pdf, 
                estimate_processing_cost, 
                estimate_processing_time,
                format_time, 
                format_cost
            )

            analysis = analyze_pdf(
                str(file_path),
                sample_pages=5,
                use_llm=False  # Быстрый анализ без LLM
            )
            
            if "error" in analysis:
                self._log(f"⚠️ Анализ не удался: {analysis['error']}")
                return
            
            rec = analysis.get("recommendations", {})
            total_pages = analysis.get("total_pages", 0)
            estimated_chunks_per_file = rec.get("estimated_chunks", 10)
            
            # Если выбрано несколько файлов - умножаем на количество
            total_files = len(self.selected_files)
            total_ocr_pages = analysis.get('ocr_needed_pages', 0)  # OCR из первого файла
            
            if total_files > 1:
                # Суммируем страницы и OCR всех файлов для более точной оценки
                total_pages_all = 0
                total_ocr_all = total_ocr_pages  # Начинаем с первого файла
                
                for i, fp in enumerate(self.selected_files):
                    try:
                        # Анализируем каждый файл для подсчёта OCR
                        if i > 0:  # Первый уже проанализирован
                            file_analysis = analyze_pdf(str(fp), sample_pages=5, use_llm=False)
                            total_ocr_all += file_analysis.get('ocr_needed_pages', 0)
                            total_pages_all += file_analysis.get('total_pages', 0)
                        else:
                            total_pages_all += total_pages
                    except Exception:
                        total_pages_all += 10
                
                # Обновляем общее количество OCR страниц
                total_ocr_pages = total_ocr_all
                
                # Пересчитываем чанки пропорционально
                estimated_chunks = int(estimated_chunks_per_file * total_pages_all / max(total_pages, 1))
                self._log(f"📊 Множество файлов: {total_files} шт, {total_pages_all} стр, ~{estimated_chunks} чанков")
                if total_ocr_all > 0:
                    self._log(f"🔍 OCR нужен для {total_ocr_all} страниц (все файлы)")
            else:
                estimated_chunks = estimated_chunks_per_file
            
            # Получаем 4 варианта LLM
            llm_options = rec.get("llm_options", {})
            economy = llm_options.get("economy", {})
            budget = llm_options.get("budget", {})
            optimal = llm_options.get("optimal", {})
            premium = llm_options.get("premium", {})
            
            # Оценки стоимости для каждого варианта (полная стоимость RAG-базы)
            enable_llm = self.enable_llm_var.get()
            enable_vec = self.enable_vectorization_var.get()
            
            self._log(f"📊 Расчёт стоимости: чанков={estimated_chunks}, LLM={enable_llm}, Vec={enable_vec}")
            
            cost_economy = estimate_processing_cost(
                estimated_chunks, economy.get("model", "gpt-4o-mini"),
                enable_llm=enable_llm, 
                enable_vectorization=enable_vec
            )
            self._log(f"   Economy ({economy.get('model')}): LLM=${cost_economy['llm_cost']}, Vec=${cost_economy['embedding_cost']}, Total=${cost_economy['total_cost']}")
            
            cost_budget = estimate_processing_cost(
                estimated_chunks, budget.get("model", "claude-haiku-4-5"),
                enable_llm=enable_llm, 
                enable_vectorization=enable_vec
            )
            self._log(f"   Budget ({budget.get('model')}): LLM=${cost_budget['llm_cost']}, Vec=${cost_budget['embedding_cost']}, Total=${cost_budget['total_cost']}")
            
            cost_optimal = estimate_processing_cost(
                estimated_chunks, optimal.get("model", "claude-sonnet-4-6"),
                enable_llm=enable_llm, 
                enable_vectorization=enable_vec
            )
            self._log(f"   Optimal ({optimal.get('model')}): LLM=${cost_optimal['llm_cost']}, Vec=${cost_optimal['embedding_cost']}, Total=${cost_optimal['total_cost']}")
            
            cost_premium = estimate_processing_cost(
                estimated_chunks, premium.get("model", "claude-opus-4-6"),
                enable_llm=enable_llm, 
                enable_vectorization=enable_vec
            )
            self._log(f"   Premium ({premium.get('model')}): LLM=${cost_premium['llm_cost']}, Vec=${cost_premium['embedding_cost']}, Total=${cost_premium['total_cost']}")

            # Оценка времени (для рекомендуемой модели)
            time_est = estimate_processing_time(
                total_pages,
                enable_llm=self.enable_llm_var.get(),
                enable_vectorization=self.enable_vectorization_var.get(),
                llm_model=rec.get("recommended_llm_model", "gpt-4o-mini")
            )

            # Формируем сообщение
            doc_type_ru = {
                "textbook": "Учебник",
                "article": "Статья",
                "faq": "FAQ",
                "report": "Отчёт",
                "book": "Книга",
                "document": "Документ"
            }.get(analysis.get("document_type", "document"), "Документ")
            
            complexity_ru = {
                "simple": "Простая",
                "medium": "Средняя",
                "complex": "Сложная"
            }.get(analysis.get("complexity", "medium"), "Средняя")
            
            # Формируем красивое сообщение с 4 вариантами
            msg = f"📄 Документ: {file_path.name}\n"
            msg += f"{'─'*60}\n\n"
            msg += f"📋 Тип: {doc_type_ru} | Страниц: {total_pages} | Сложность: {complexity_ru}\n\n"
            
            msg += f"📊 Структура:\n"
            msg += f"   • Заголовков: {analysis.get('heading_count', 0)}\n"
            msg += f"   • Абзацев: {analysis.get('paragraph_count', 0)}\n"
            msg += f"   • Таблиц: {'Да' if analysis.get('has_tables') else 'Нет'}\n"
            msg += f"   • Формул: {'Да' if analysis.get('has_equations') else 'Нет'}\n"
            msg += f"   • Кода: {'Да' if analysis.get('has_code') else 'Нет'}\n"
            
            # OCR - только если нужен (суммарно для всех файлов)
            if total_ocr_pages > 0:
                msg += f"   • OCR: Требуется для {total_ocr_pages} стр.\n"
            msg += "\n"
            
            msg += f"🎯 Параметры чанкинга:\n"
            msg += f"   • Размер: {rec.get('chunk_size', 500)} (текущий: {self.chunk_size_var.get()})\n"
            msg += f"   • Overlap: {rec.get('overlap', 50)} (текущий: {self.overlap_var.get()})\n"
            if total_ocr_pages > 0:
                msg += f"   • OCR: Включён ({total_ocr_pages} стр.)\n"
            msg += "\n"
            
            msg += f"{'─'*60}\n"
            msg += f"🤖 ВЫБОР LLM МОДЕЛИ ДЛЯ RAG-БАЗЫ:\n"
            msg += f"{'─'*60}\n\n"
            
            # Вариант 1: Экономичный
            msg += f"1️⃣ ЭКОНОМИЧНЫЙ: {economy.get('model', 'gpt-4o-mini')}\n"
            msg += f"   💰 Цена: {economy.get('price_per_1m', '$0.15/$0.60')} за 1M токенов\n"
            msg += f"   📊 Стоимость RAG-базы:\n"
            if self.enable_llm_var.get():
                msg += f"      • LLM: {format_cost(cost_economy['llm_cost'])}\n"
            if self.enable_vectorization_var.get():
                msg += f"      • Векторы: {format_cost(cost_economy['embedding_cost'])}\n"
            msg += f"      • ИТОГО: {format_cost(cost_economy['total_cost'])}\n"
            msg += f"   ✨ {economy.get('reason', 'Дёшево и быстро')}\n\n"
            
            # Вариант 2: Бюджетный (Claude Haiku)
            msg += f"2️⃣ БЮДЖЕТНЫЙ: {budget.get('model', 'claude-haiku-4-5')}\n"
            msg += f"   💰 Цена: {budget.get('price_per_1m', '$0.25/$1.25')} за 1M токенов\n"
            msg += f"   📊 Стоимость RAG-базы:\n"
            if self.enable_llm_var.get():
                msg += f"      • LLM: {format_cost(cost_budget['llm_cost'])}\n"
            if self.enable_vectorization_var.get():
                msg += f"      • Векторы: {format_cost(cost_budget['embedding_cost'])}\n"
            msg += f"      • ИТОГО: {format_cost(cost_budget['total_cost'])}\n"
            msg += f"   ✨ {budget.get('reason', 'Дешёвый Claude')}\n\n"
            
            # Вариант 3: Оптимальный
            recommended = rec.get("recommended_llm_model", "gpt-4o-mini")
            rec_marker = " ⭐ РЕКОМЕНДУЕТСЯ" if optimal.get("model") == recommended else ""
            msg += f"3️⃣ ОПТИМАЛЬНЫЙ{rec_marker}: {optimal.get('model', 'claude-sonnet-4-6')}\n"
            msg += f"   💰 Цена: {optimal.get('price_per_1m', '$3.00/$15.00')} за 1M токенов\n"
            msg += f"   📊 Стоимость RAG-базы:\n"
            if self.enable_llm_var.get():
                msg += f"      • LLM: {format_cost(cost_optimal['llm_cost'])}\n"
            if self.enable_vectorization_var.get():
                msg += f"      • Векторы: {format_cost(cost_optimal['embedding_cost'])}\n"
            msg += f"      • ИТОГО: {format_cost(cost_optimal['total_cost'])}\n"
            msg += f"   ✨ {optimal.get('reason', 'Баланс цены и качества')}\n\n"
            
            # Вариант 4: Премиум
            msg += f"4️⃣ ПРЕМИУМ: {premium.get('model', 'claude-opus-4-6')}\n"
            msg += f"   💰 Цена: {premium.get('price_per_1m', '$15.00/$75.00')} за 1M токенов\n"
            msg += f"   📊 Стоимость RAG-базы:\n"
            if self.enable_llm_var.get():
                msg += f"      • LLM: {format_cost(cost_premium['llm_cost'])}\n"
            if self.enable_vectorization_var.get():
                msg += f"      • Векторы: {format_cost(cost_premium['embedding_cost'])}\n"
            msg += f"      • ИТОГО: {format_cost(cost_premium['total_cost'])}\n"
            msg += f"   ✨ {premium.get('reason', 'Максимальное качество')}\n\n"
            
            msg += f"{'─'*60}\n"
            msg += f"📈 Прогноз: ~{estimated_chunks} чанков, время: {format_time(time_est['total_time'])}\n"
            msg += f"{'─'*60}\n\n"
            
            # Обновляем rationale с правильным количеством OCR
            if rec.get("rationale"):
                msg += f"💡 Почему:\n"
                for r in rec["rationale"][:4]:
                    # Заменяем старое сообщение про OCR на новое
                    if "OCR нужен для" in r and total_ocr_pages > 0:
                        msg += f"   • 🔍 OCR нужен для {total_ocr_pages} страниц (все файлы)\n"
                    else:
                        msg += f"   • {r}\n"
            
            # Создаём кастомный диалог с 4 кнопками
            self._show_llm_selection_dialog(
                file_path, rec, economy, optimal, premium, msg, total_ocr_pages
            )

        except Exception as e:
            self._log(f"⚠️ Ошибка автоанализа: {str(e)}")
            logger.error(f"Ошибка автоанализа: {e}")
    
    def _show_llm_selection_dialog(self, file_path: Path, rec: dict, 
                                     economy: dict, optimal: dict, premium: dict,
                                     msg: str, total_ocr_pages: int = 0) -> None:
        """Показывает диалог выбора LLM модели с 4 вариантами."""
        
        # Получаем все 4 варианта
        llm_options = rec.get("llm_options", {})
        budget = llm_options.get("budget", {})
        
        # Создаём кастомное окно
        dialog = tk.Toplevel(self.root)
        dialog.title("🤖 Выбор LLM модели для RAG-базы")
        dialog.geometry("620x750")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Текст с анализом
        from tkinter.scrolledtext import ScrolledText
        text = ScrolledText(dialog, width=72, height=30, wrap=tk.WORD)
        text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        text.insert(tk.END, msg)
        text.config(state=tk.DISABLED)
        
        # Рамка для кнопок (2 ряда по 2 кнопки)
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=5)
        
        selected_model = [None]  # Используем список для mutable
        
        def on_economy():
            selected_model[0] = economy.get("model", "gpt-4o-mini")
            dialog.destroy()
            self._apply_selected_model(file_path, rec, selected_model[0], total_ocr_pages)
        
        def on_budget():
            selected_model[0] = budget.get("model", "claude-haiku-4-5")
            dialog.destroy()
            self._apply_selected_model(file_path, rec, selected_model[0], total_ocr_pages)
        
        def on_optimal():
            selected_model[0] = optimal.get("model", "claude-sonnet-4-6")
            dialog.destroy()
            self._apply_selected_model(file_path, rec, selected_model[0], total_ocr_pages)
        
        def on_premium():
            selected_model[0] = premium.get("model", "claude-opus-4-6")
            dialog.destroy()
            self._apply_selected_model(file_path, rec, selected_model[0], total_ocr_pages)
        
        def on_skip():
            dialog.destroy()
            self._log("ℹ️ Используются текущие параметры")
        
        # 1-й ряд кнопок
        row1 = ttk.Frame(btn_frame)
        row1.pack(pady=3)
        ttk.Button(row1, text="1️⃣ Экономичный", command=on_economy, width=18).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="2️⃣ Бюджетный", command=on_budget, width=18).pack(side=tk.LEFT, padx=5)
        
        # 2-й ряд кнопок
        row2 = ttk.Frame(btn_frame)
        row2.pack(pady=3)
        ttk.Button(row2, text="3️⃣ Оптимальный ⭐", command=on_optimal, width=18).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="4️⃣ Премиум", command=on_premium, width=18).pack(side=tk.LEFT, padx=5)
        
        # Кнопка пропуска
        ttk.Button(dialog, text="Пропустить (текущие параметры)", command=on_skip).pack(pady=10)
    
    def _apply_selected_model(self, file_path: Path, rec: dict, selected_model: str, total_ocr_pages: int = 0) -> None:
        """Применяет выбранную модель и параметры."""
        # Применяем параметры чанкинга
        self.chunk_size_var.set(rec.get('chunk_size', 500))
        self.overlap_var.set(rec.get('overlap', 50))
        
        # Устанавливаем выбранную LLM модель
        for i, (model_id, model_name) in enumerate(LLM_MODELS):
            if model_id == selected_model:
                self.llm_model_combo.current(i)
                break
        
        # OCR - включаем если нужен
        if total_ocr_pages > 0 or rec.get('ocr_enabled'):
            self.settings['ocr_enabled'] = True
        
        self._log(f"✅ Применено: chunk={rec.get('chunk_size')}, overlap={rec.get('overlap')}, LLM={selected_model}, OCR={self.settings['ocr_enabled']}")
    
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
            idx = self.llm_model_combo.current()
            llm_model = LLM_MODELS[idx][0] if idx >= 0 else "gpt-4o"
            
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
    
    def _check_api_balance(self) -> dict:
        """
        Проверяет доступность и баланс API.
        
        Returns:
            Словарь с результатами проверки:
            - openai_ok: bool - доступен ли OpenAI API
            - anthropic_ok: bool - доступен ли Anthropic API  
            - error_message: str - сообщение об ошибке (если есть)
        """
        import requests
        
        result = {
            'openai_ok': False,
            'anthropic_ok': False,
            'error_message': None
        }
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            result['error_message'] = "OPENAI_API_KEY не найден в переменных окружения"
            return result

        # Проверяем OpenAI (для эмбеддингов)
        try:
            response = requests.get(
                "https://openai.api.proxyapi.ru/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5
            )
            if response.status_code == 200:
                result['openai_ok'] = True
            elif response.status_code == 402:
                result['error_message'] = "Недостаточно средств на балансе API (OpenAI)"
            elif response.status_code == 401:
                result['error_message'] = "Неверный API ключ"
            else:
                result['error_message'] = f"Ошибка API OpenAI: {response.status_code}"
        except requests.exceptions.Timeout:
            result['error_message'] = "Таймаут подключения к API OpenAI"
        except Exception as e:
            result['error_message'] = f"Ошибка подключения к API OpenAI: {str(e)}"
        
        # Проверяем Anthropic (для Claude) - используем тот же endpoint
        try:
            response = requests.get(
                "https://api.proxyapi.ru/anthropic/v1/models",
                headers={"x-api-key": api_key},
                timeout=5
            )
            if response.status_code == 200:
                result['anthropic_ok'] = True
            elif response.status_code == 402 and not result['error_message']:
                result['error_message'] = "Недостаточно средств на балансе API (Anthropic)"
            elif response.status_code == 401 and not result['error_message']:
                result['error_message'] = "Неверный API ключ"
        except requests.exceptions.Timeout:
            if not result['error_message']:
                result['error_message'] = "Таймаут подключения к API Anthropic"
        except Exception as e:
            if not result['error_message']:
                result['error_message'] = f"Ошибка подключения к API Anthropic: {str(e)}"
        
        return result

    def _process_all_files(self) -> None:
        """Обрабатывает все выбранные файлы (с опцией параллельной обработки)."""
        if not self.selected_files:
            messagebox.showwarning('Предупреждение', self.translations['no_files'])
            return
        
        self._save_settings()
        
        # Спрашиваем про режим обработки ДО блокировки GUI
        if len(self.selected_files) > 1:
            use_parallel = messagebox.askyesno(
                "Режим обработки",
                f"Обработать {len(self.selected_files)} файлов параллельно?\n\n"
                "Да - быстрее (использует больше ресурсов)\n"
                "Нет - последовательно"
            )
        else:
            use_parallel = False

        # Проверяем API, если включены LLM или векторизация
        if self.settings['enable_llm'] or self.settings['enable_vectorization']:
            self._log("Проверка доступности API...")
            api_check = self._check_api_balance()
            
            if api_check['error_message']:
                # Показываем ошибку
                error_msg = api_check['error_message']
                self._log(f"❌ Ошибка API: {error_msg}")
                
                # Предлагаем продолжить без API
                if self.settings['enable_llm'] or self.settings['enable_vectorization']:
                    proceed = messagebox.askyesno(
                        "Ошибка API",
                        f"{error_msg}\n\n"
                        "Продолжить обработку БЕЗ LLM и векторизации?\n"
                        "(Будет выполнен только чанкинг)"
                    )
                    if proceed:
                        self.settings['enable_llm'] = False
                        self.settings['enable_vectorization'] = False
                        self._log("Обработка продолжится без LLM и векторизации")
                    else:
                        return
            else:
                # API работает
                status = []
                if api_check['openai_ok']:
                    status.append("OpenAI ✓")
                if api_check['anthropic_ok']:
                    status.append("Anthropic ✓")
                self._log(f"✅ API доступен: {', '.join(status)}")

        # Блокируем кнопки
        self.process_btn.config(state='disabled')
        self.load_files_btn.config(state='disabled')
        self.clear_btn.config(state='disabled')
        
        # Сбрасываем флаг отмены
        self._cancel_requested = False
        from src.llm_chunker import clear_cancel
        clear_cancel()
        
        # Добавляем кнопку отмены
        if not hasattr(self, 'cancel_btn'):
            self.cancel_btn = ttk.Button(
                self.root.winfo_children()[0],
                text="❌ Отменить",
                command=self._cancel_processing
            )
        self.cancel_btn.grid(row=5, column=0, sticky=tk.E, pady=(0, 10))

        # Инициализируем прогресс
        self.progress.config(mode='determinate', maximum=100, value=0)
        self._progress_value = 0
        self._current_stage = "Инициализация..."
        self._estimated_time = 60  # Дефолтная оценка 1 минута
        
        # Загружаем статистику для оценки времени
        self._load_processing_stats()
        
        # Оцениваем время ДО запуска потока
        total_pages = 0
        for fp in self.selected_files:
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(str(fp))
                total_pages += len(doc)
                doc.close()
            except Exception:
                total_pages += 10  # По умолчанию
        
        self._estimated_time = self._estimate_time(total_pages)
        self._total_pages = total_pages
        
        # Логируем оценку
        mins = int(self._estimated_time // 60)
        secs = int(self._estimated_time % 60)
        stats_summary = self._get_stats_summary()
        self._log(f"📄 Страниц: {total_pages} | ⏱️ Оценка: ~{mins}м {secs}с")
        self._log(stats_summary)
        
        # Запускаем обработку в отдельном потоке
        import threading
        
        self._processing_thread = threading.Thread(
            target=self._process_in_thread,
            args=(use_parallel,),
            daemon=True
        )
        self._processing_thread.start()
        
        # Запускаем мониторинг прогресса
        self._monitor_progress()
    
    def _load_processing_stats(self) -> None:
        """Загружает статистику обработки для оценки времени."""
        import json
        stats_file = Path("logs/processing_stats.json")
        self._processing_stats = {
            "sessions": [],  # История сессий (последние 20)
            "averages": {}   # Усреднённые значения по типам
        }
        
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Совместимость со старым форматом
                    if "sessions" not in data:
                        # Конвертируем старый формат
                        self._processing_stats["averages"] = data
                    else:
                        self._processing_stats = data
            except Exception:
                pass
    
    def _save_processing_stats(self, pages: int, chunks: int, duration: float, 
                                use_llm: bool, use_vec: bool) -> None:
        """Сохраняет статистику обработки с историей сессий."""
        import json
        stats_file = Path("logs/processing_stats.json")
        stats_file.parent.mkdir(exist_ok=True)
        
        # Ключ для типа обработки
        key = f"llm_{use_llm}_vec_{use_vec}"
        
        # Добавляем новую сессию
        session = {
            "timestamp": datetime.now().isoformat(),
            "pages": pages,
            "chunks": chunks,
            "duration": duration,
            "time_per_page": duration / pages if pages > 0 else 0,
            "type": key
        }
        
        # Добавляем в историю
        if "sessions" not in self._processing_stats:
            self._processing_stats["sessions"] = []
        
        self._processing_stats["sessions"].append(session)
        
        # Оставляем только последние 20 сессий
        self._processing_stats["sessions"] = self._processing_stats["sessions"][-20:]
        
        # Пересчитываем средние значения по типам
        type_sessions = {}
        for s in self._processing_stats["sessions"]:
            t = s["type"]
            if t not in type_sessions:
                type_sessions[t] = []
            type_sessions[t].append(s)
        
        # Вычисляем средневзвешенное время (с учётом объёма)
        self._processing_stats["averages"] = {}
        for t, sessions in type_sessions.items():
            total_pages = sum(s["pages"] for s in sessions)
            total_duration = sum(s["duration"] for s in sessions)
            
            # Средневзвешенное время на страницу
            avg_time = total_duration / total_pages if total_pages > 0 else 5.0
            
            # Медианное время (более устойчиво к выбросам)
            times = sorted([s["time_per_page"] for s in sessions])
            median_time = times[len(times) // 2] if times else 5.0
            
            self._processing_stats["averages"][t] = {
                "sessions_count": len(sessions),
                "total_pages": total_pages,
                "avg_time_per_page": round(avg_time, 2),
                "median_time_per_page": round(median_time, 2),
                "min_time_per_page": round(min(times), 2) if times else 5.0,
                "max_time_per_page": round(max(times), 2) if times else 5.0
            }
        
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self._processing_stats, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def _estimate_time(self, total_pages: int) -> float:
        """
        Оценивает время обработки в секундах на основе статистики.
        Использует медианное время (более устойчиво к выбросам).
        
        Реальные данные из теста 2026-03-23:
        - 15 страниц, 204 чанка
        - LLM (gpt-4o-mini): ~3.8 мин (~15 сек/страница)
        - Векторизация: ~4.5 мин (~18 сек/страница) - БЕЗ кэша
        - Итого: ~33 сек/страница с LLM + векторизацией
        """
        key = f"llm_{self.settings['enable_llm']}_vec_{self.settings['enable_vectorization']}"
        
        # Получаем статистику по типу обработки
        if "averages" in self._processing_stats and key in self._processing_stats["averages"]:
            stats = self._processing_stats["averages"][key]
            # Используем медианное время (более предсказуемо)
            base_time = stats.get("median_time_per_page", 5.0)
            sessions_count = stats.get("sessions_count", 0)
            
            # Если мало сессий, добавляем запас
            if sessions_count < 3:
                base_time *= 1.15  # +15% запас
        else:
            # Значения по умолчанию на основе реальных измерений
            base_time = 1.0  # Базовое время на страницу (извлечение текста + чанкинг)
            if self.settings['enable_llm']:
                # LLM добавляет ~15 сек/страница (gpt-4o-mini, батчи по 10 чанков)
                base_time += 15.0
            if self.settings['enable_vectorization']:
                # Векторизация добавляет ~18 сек/страница БЕЗ кэша
                # С кэшем ~0.3 сек/страница
                base_time += 18.0
        
        estimated = base_time * total_pages
        
        # Корректировка на кэш эмбеддингов
        if self.settings['enable_vectorization']:
            try:
                from src.embedding_cache import get_embedding_cache
                cache = get_embedding_cache()
                cache_stats = cache.get_stats()
                cached_entries = cache_stats.get('total_entries', 0)
                if cached_entries > 100:
                    # Если есть кэш с достаточным количеством записей
                    # Экономия ~95% времени на векторизации
                    cache_savings = min(cached_entries / 500, 0.95)  # Максимум 95% экономии
                    vec_time = 18.0 * total_pages  # Время векторизации без кэша
                    saved_time = vec_time * cache_savings
                    estimated -= saved_time
            except Exception:
                pass
        
        return estimated
    
    def _get_stats_summary(self) -> str:
        """Возвращает сводку статистики для отображения."""
        key = f"llm_{self.settings['enable_llm']}_vec_{self.settings['enable_vectorization']}"
        
        if "averages" in self._processing_stats and key in self._processing_stats["averages"]:
            stats = self._processing_stats["averages"][key]
            sessions = stats.get("sessions_count", 0)
            median = stats.get("median_time_per_page", 0)
            min_t = stats.get("min_time_per_page", 0)
            max_t = stats.get("max_time_per_page", 0)
            
            if sessions > 0:
                return f"📊 Статистика: {sessions} сессий, ~{median:.1f}с/стр ({min_t:.1f}-{max_t:.1f}с)"
        
        return "📊 Статистика: недостаточно данных"
    
    def _cancel_processing(self) -> None:
        """Отмена обработки."""
        self._cancel_requested = True
        # Отправляем сигнал отмены в LLM
        from src.llm_chunker import request_cancel
        request_cancel()
        self._log("Запрошена отмена обработки...")
        self.cancel_btn.config(state='disabled')
    
    def _monitor_progress(self) -> None:
        """Мониторинг прогресса обработки."""
        import time
        
        # Инициализируем start_time только один раз
        if not hasattr(self, '_monitor_start_time'):
            self._monitor_start_time = time.time()
        
        if hasattr(self, '_progress_value'):
            self.progress['value'] = self._progress_value
        
        # Формируем текст статуса
        current_stage = getattr(self, '_current_stage', 'Инициализация...')
        progress_pct = getattr(self, '_progress_value', 0)
        
        # Время с начала мониторинга
        elapsed = time.time() - self._monitor_start_time
        estimated_time = getattr(self, '_estimated_time', 60)
        
        # Countdown: оставшееся время
        remaining = estimated_time - elapsed
        
        if remaining > 0:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            time_str = f"~{mins}м {secs}с"
        else:
            # Адаптивная оценка после превышения
            if progress_pct > 10:
                # Пересчёт на основе текущей скорости
                real_total = elapsed / (progress_pct / 100)
                remaining_real = real_total - elapsed
                if remaining_real > 0:
                    mins = int(remaining_real // 60)
                    secs = int(remaining_real % 60)
                    time_str = f"~{mins}м {secs}с (уточн.)"
                else:
                    time_str = "завершение..."
            else:
                time_str = "завершение..."
        
        # Обновляем label с текущей операцией
        self.progress_label.config(
            text=f"{current_stage} | {progress_pct:.0f}% | Осталось: {time_str}"
        )
        
        # Проверяем, жив ли поток
        if hasattr(self, '_processing_thread') and self._processing_thread.is_alive():
            self.root.after(500, self._monitor_progress)  # Обновляем каждые 500мс
        else:
            # Поток завершён
            self._finish_processing()
    
    def _finish_processing(self) -> None:
        """Завершение обработки (вызывается из главного потока)."""
        import time
        
        # Скрываем кнопку отмены
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.grid_forget()
        
        # Разблокируем кнопки
        self.process_btn.config(state='normal')
        self.load_files_btn.config(state='normal')
        self.clear_btn.config(state='normal')
        
        # Вычисляем время обработки
        elapsed_str = ""
        if hasattr(self, '_monitor_start_time'):
            elapsed = time.time() - self._monitor_start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            elapsed_str = f"\nВремя обработки: {mins}м {secs}с"
        
        # Показываем результат
        if hasattr(self, '_processing_result'):
            result = self._processing_result
            if result.get('cancelled'):
                self.progress_label.config(text="Обработка отменена")
                self._log("Обработка отменена пользователем")
            else:
                self.progress_label.config(text="✅ Обработка завершена")
                result_msg = f"Обработка завершена успешно!{elapsed_str}\n\n"
                result_msg += f"Всего чанков: {result['total_chunks']}\n"
                result_msg += f"Обработано файлов: {result['processed_count']}/{len(self.selected_files)}\n"
                result_msg += f"\nРезультаты сохранены в: {self.settings['output_dir']}"
                
                self._log(f"Обработка завершена. Чанков: {result['total_chunks']}")
                messagebox.showinfo("Успешно", result_msg)
        
        self.progress['value'] = 0
    
        # Сбрасываем время мониторинга для следующего запуска
        if hasattr(self, '_monitor_start_time'):
            delattr(self, '_monitor_start_time')
    
    def _process_in_thread(self, use_parallel: bool) -> None:
        """Обработка файлов в отдельном потоке."""
        import time
        thread_start_time = time.time()  # Время начала для статистики
        self._current_stage = "📊 Подготовка..."
        
        total_chunks = 0
        processed_count = 0
        
        try:
            if use_parallel and len(self.selected_files) > 1:
                # Параллельная обработка
                self._current_stage = "⚡ Параллельная обработка"
                self._log_threadsafe(f"Параллельная обработка {len(self.selected_files)} файлов...")
                total_chunks, processed_count = self._process_parallel_threadsafe()
            else:
                # Последовательная обработка
                total_files = len(self.selected_files)
                for i, file_path in enumerate(self.selected_files, 1):
                    if self._cancel_requested:
                        break
                    
                    # Обновляем текущий файл
                    self._current_stage = f"📁 Файл {i}/{total_files}: {file_path.name[:20]}..."
                    base_progress = (i - 1) / total_files * 100
                    self._progress_value = base_progress
                    self._log_threadsafe(f"Обработка [{i}/{total_files}]: {file_path.name}")
                    
                    chunks = self._process_single_file_threadsafe(file_path, progress_base=base_progress, progress_step=100/total_files)
                    total_chunks += chunks
                    processed_count += 1
                    
                    # Финальный прогресс для файла
                    self._progress_value = i / total_files * 100
                    
                    # Добавляем в историю
                    self._add_to_history(file_path)
            
            # Сохраняем статистику
            duration = time.time() - thread_start_time
            total_pages = getattr(self, '_total_pages', 0)
            self._save_processing_stats(
                total_pages, total_chunks, duration,
                self.settings['enable_llm'], self.settings['enable_vectorization']
            )

            # Сохраняем результат
            self._processing_result = {
                'total_chunks': total_chunks,
                'processed_count': processed_count,
                'cancelled': self._cancel_requested
            }
            
        except Exception as e:
            self._log_threadsafe(f"Ошибка: {str(e)}")
            logger.error(f"Ошибка в потоке обработки: {e}")
            self._processing_result = {
                'total_chunks': total_chunks,
                'processed_count': processed_count,
                'cancelled': False,
                'error': str(e)
            }
    
    def _log_threadsafe(self, message: str) -> None:
        """Потокобезопасное логирование."""
        self.root.after(0, lambda: self._log(message))
    
    def _process_single_file_threadsafe(self, file_path: Path, progress_base: float = 0, progress_step: float = 100) -> int:
        """Обрабатывает один файл в потоке. Возвращает количество чанков."""
        try:
            # Создаём выходную директорию
            output_dir = Path(self.settings['output_dir'])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Создаём директорию для векторной БД заранее
            vector_db_dir = output_dir / "vector_db"
            vector_db_dir.mkdir(parents=True, exist_ok=True)
            
            self._log_threadsafe(f"Output dir: {output_dir}")
            
            # Проверяем API ключ
            api_key = os.getenv("OPENAI_API_KEY")
            
            if not api_key:
                self._log_threadsafe("WARNING: OPENAI_API_KEY not found. Skipping vectorization and LLM.")
                self.settings['enable_vectorization'] = False
                self.settings['enable_llm'] = False
            else:
                self._log_threadsafe(f"API key found. LLM model: {self.settings['llm_model']}")
        
            # Callback для обновления прогресса
            def progress_callback(stage: str, progress: float):
                self._current_stage = stage
                self._progress_value = progress_base + progress * progress_step
            
            result = process_pdf(
                str(file_path),
                str(output_dir),  # Передаём как строку
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
                llm_model=self.settings['llm_model'],
                progress_callback=progress_callback
            )

            # Логируем результат LLM-обогащения
            if result.get('llm_enhanced'):
                self._log_threadsafe(f"  -> LLM enrichment completed")

            chunks = len(result.get('chunks', []))
            self._current_stage = "✅ Завершение"
            self._progress_value = progress_base + progress_step
            self._log_threadsafe(f"  -> Done: {chunks} chunks")
            return chunks
            
        except Exception as e:
            self._log_threadsafe(f"  -> Error: {str(e)}")
            logger.error(f"Error processing {file_path.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0

    def _process_parallel_threadsafe(self) -> tuple:
        """Параллельная обработка файлов в потоке."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        total_chunks = 0
        processed_count = 0
        results_lock = threading.Lock()
        total_files = len(self.selected_files)
        
        def process_file_wrapper(file_path, idx):
            nonlocal total_chunks, processed_count
            if self._cancel_requested:
                return file_path, 0
            progress_base = idx / total_files * 100
            progress_step = 100 / total_files
            chunks = self._process_single_file_threadsafe(file_path, progress_base, progress_step)
            with results_lock:
                total_chunks += chunks
                processed_count += 1
                self._progress_value = processed_count / total_files * 100
            return file_path, chunks
        
        max_workers = min(4, total_files)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_file_wrapper, fp, i): fp for i, fp in enumerate(self.selected_files)}
            
            for future in as_completed(futures):
                if self._cancel_requested:
                    break
                file_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self._log_threadsafe(f"  → Ошибка: {str(e)}")
        
        return total_chunks, processed_count
    
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
