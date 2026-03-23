"""
GUI для системы тестирования качества RAG-баз.

Версия: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import json
import os
from pathlib import Path
from datetime import datetime

# Матрица для графиков
try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class RAGQualityTesterGUI:
    """
    GUI для тестирования качества RAG-баз.
    
    Функции:
    - Выбор пути к RAG-базе
    - Запуск тестирования
    - Отображение результатов
    - Просмотр истории
    - Экспорт отчётов
    """
    
    def __init__(self, root: tk.Tk):
        """Инициализация GUI."""
        self.root = root
        self.root.title("🔍 Тестирование качества RAG-базы v1.0.0")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
        # Переменные
        self.db_path = tk.StringVar()
        self.threshold = tk.IntVar(value=80)
        self.test_results = None
        self.history = []
        
        # Состояние
        self.testing_in_progress = False
        
        # Создаём интерфейс
        self._create_menu()
        self._create_main_frame()
        self._load_history()
        
        # Центрируем окно
        self._center_window()
    
    def _center_window(self):
        """Центрирует окно на экране."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def _create_menu(self):
        """Создаёт меню."""
        menubar = tk.Menu(self.root)
        
        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Открыть базу...", command=self._browse_db)
        file_menu.add_separator()
        file_menu.add_command(label="Экспорт в Markdown", command=lambda: self._export_report("markdown"))
        file_menu.add_command(label="Экспорт в HTML", command=lambda: self._export_report("html"))
        file_menu.add_command(label="Экспорт в JSON", command=lambda: self._export_report("json"))
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)
        
        # Меню Тесты
        test_menu = tk.Menu(menubar, tearoff=0)
        test_menu.add_command(label="Запустить все тесты", command=self._run_tests)
        test_menu.add_separator()
        test_menu.add_command(label="Только структура", command=lambda: self._run_category("structure"))
        test_menu.add_command(label="Только чанки", command=lambda: self._run_category("chunks"))
        test_menu.add_command(label="Только поиск", command=lambda: self._run_category("search"))
        test_menu.add_command(label="Только ответы", command=lambda: self._run_category("answers"))
        test_menu.add_command(label="Только покрытие", command=lambda: self._run_category("coverage"))
        menubar.add_cascade(label="Тесты", menu=test_menu)
        
        # Меню Вид
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="История тестов", command=self._show_history)
        view_menu.add_command(label="Очистить историю", command=self._clear_history)
        menubar.add_cascade(label="Вид", menu=view_menu)
        
        # Меню Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self._show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def _create_main_frame(self):
        """Создаёт основной интерфейс."""
        # Главный контейнер
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Верхняя панель - выбор базы
        self._create_db_selector(main_frame)
        
        # Средняя панель - результаты
        self._create_results_panel(main_frame)
        
        # Нижняя панель - прогресс и кнопки
        self._create_bottom_panel(main_frame)
    
    def _create_db_selector(self, parent):
        """Создаёт панель выбора базы."""
        frame = ttk.LabelFrame(parent, text="📁 Выбор RAG-базы", padding="10")
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # Путь к базе
        ttk.Label(frame, text="Путь:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        entry = ttk.Entry(frame, textvariable=self.db_path, width=80)
        entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 10))
        
        ttk.Button(frame, text="Обзор...", command=self._browse_db).grid(row=0, column=2)
        
        # Порог качества
        ttk.Label(frame, text="Порог (%):").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        threshold_spin = ttk.Spinbox(frame, from_=50, to=100, textvariable=self.threshold, width=10)
        threshold_spin.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        # Информация о базе
        self.db_info_label = ttk.Label(frame, text="База не выбрана", foreground="gray")
        self.db_info_label.grid(row=1, column=2, sticky=tk.E, pady=(10, 0))
        
        frame.columnconfigure(1, weight=1)
    
    def _create_results_panel(self, parent):
        """Создаёт панель результатов."""
        # Notebook с вкладками
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка 1: Обзор
        self.overview_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.overview_tab, text="📊 Обзор")
        self._create_overview_tab(self.overview_tab)
        
        # Вкладка 2: Детали
        self.details_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.details_tab, text="📋 Детали")
        self._create_details_tab(self.details_tab)
        
        # Вкладка 3: Графики
        self.charts_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.charts_tab, text="📈 Графики")
        self._create_charts_tab(self.charts_tab)
        
        # Вкладка 4: Рекомендации
        self.recommendations_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.recommendations_tab, text="💡 Рекомендации")
        self._create_recommendations_tab(self.recommendations_tab)
    
    def _create_overview_tab(self, parent):
        """Создаёт вкладку обзора."""
        # Большая оценка
        score_frame = ttk.Frame(parent)
        score_frame.pack(fill=tk.X, pady=10)
        
        self.score_label = ttk.Label(
            score_frame,
            text="--/100",
            font=("Helvetica", 48, "bold"),
            foreground="gray"
        )
        self.score_label.pack(side=tk.LEFT, padx=20)
        
        self.status_label = ttk.Label(
            score_frame,
            text="Ожидание тестирования",
            font=("Helvetica", 24),
            foreground="gray"
        )
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        # Индикаторы категорий
        categories_frame = ttk.LabelFrame(parent, text="Категории", padding="10")
        categories_frame.pack(fill=tk.X, pady=10)
        
        self.category_labels = {}
        self.category_bars = {}
        
        categories = [
            ("structure", "Структура", 0.10),
            ("chunks", "Чанки", 0.25),
            ("search", "Поиск", 0.30),
            ("answers", "Ответы", 0.25),
            ("coverage", "Покрытие", 0.10)
        ]
        
        for i, (cat_id, cat_name, weight) in enumerate(categories):
            ttk.Label(categories_frame, text=f"{cat_name} ({weight*100:.0f}%):").grid(
                row=i, column=0, sticky=tk.W, pady=2
            )
            
            # Прогресс бар
            bar = ttk.Progressbar(categories_frame, length=300, mode='determinate')
            bar.grid(row=i, column=1, sticky=tk.W, padx=10, pady=2)
            self.category_bars[cat_id] = bar
            
            # Метка с баллом
            label = ttk.Label(categories_frame, text="--", width=15)
            label.grid(row=i, column=2, sticky=tk.W, pady=2)
            self.category_labels[cat_id] = label
        
        # Метаданные
        metadata_frame = ttk.LabelFrame(parent, text="Метаданные базы", padding="10")
        metadata_frame.pack(fill=tk.X, pady=10)
        
        self.metadata_text = ScrolledText(metadata_frame, height=5, state='disabled')
        self.metadata_text.pack(fill=tk.X)
    
    def _create_details_tab(self, parent):
        """Создаёт вкладку деталей."""
        # Treeview для тестов
        columns = ('test', 'category', 'status', 'score', 'message')
        
        self.tests_tree = ttk.Treeview(parent, columns=columns, show='headings', height=20)
        
        self.tests_tree.heading('test', text='Тест')
        self.tests_tree.heading('category', text='Категория')
        self.tests_tree.heading('status', text='Статус')
        self.tests_tree.heading('score', text='Балл')
        self.tests_tree.heading('message', text='Результат')
        
        self.tests_tree.column('test', width=200)
        self.tests_tree.column('category', width=100)
        self.tests_tree.column('status', width=80)
        self.tests_tree.column('score', width=80)
        self.tests_tree.column('message', width=400)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tests_tree.yview)
        self.tests_tree.configure(yscrollcommand=scrollbar.set)
        
        self.tests_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Теги для цветов
        self.tests_tree.tag_configure('passed', foreground='green')
        self.tests_tree.tag_configure('failed', foreground='red')
    
    def _create_charts_tab(self, parent):
        """Создаёт вкладку графиков."""
        if MATPLOTLIB_AVAILABLE:
            # Фигура matplotlib
            self.fig = Figure(figsize=(10, 6), dpi=100)
            self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(
                parent,
                text="Для отображения графиков установите matplotlib:\npip install matplotlib",
                foreground="orange"
            ).pack(pady=50)
    
    def _create_recommendations_tab(self, parent):
        """Создаёт вкладку рекомендаций."""
        self.recommendations_text = ScrolledText(parent, height=30, wrap=tk.WORD)
        self.recommendations_text.pack(fill=tk.BOTH, expand=True)
    
    def _create_bottom_panel(self, parent):
        """Создаёт нижнюю панель."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(10, 0))
        
        # Прогресс
        self.progress_bar = ttk.Progressbar(frame, mode='determinate', length=400)
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 10))
        
        self.progress_label = ttk.Label(frame, text="")
        self.progress_label.pack(side=tk.LEFT)
        
        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side=tk.RIGHT)
        
        self.run_btn = ttk.Button(btn_frame, text="▶️ Запустить тесты", command=self._run_tests)
        self.run_btn.pack(side=tk.LEFT, padx=5)
        
        self.export_btn = ttk.Button(btn_frame, text="📤 Экспорт", command=lambda: self._export_report("html"))
        self.export_btn.pack(side=tk.LEFT, padx=5)
        self.export_btn.config(state='disabled')
    
    # ------------------------------------------------------------------------
    # ДЕЙСТВИЯ
    # ------------------------------------------------------------------------
    
    def _browse_db(self):
        """Открывает диалог выбора базы."""
        folder = filedialog.askdirectory(
            title="Выберите папку с RAG-базой",
            initialdir=self.db_path.get() or "."
        )
        
        if folder:
            self.db_path.set(folder)
            self._check_db()
    
    def _check_db(self):
        """Проверяет выбранную базу."""
        path = Path(self.db_path.get())
        
        if not path.exists():
            self.db_info_label.config(text="❌ Папка не существует", foreground="red")
            return
        
        # Проверяем файлы
        index_file = path / "index.faiss"
        dataset_file = path / "dataset.json"
        metadata_file = path / "metadata.json"
        
        status = []
        
        if index_file.exists():
            status.append("✓ index.faiss")
        else:
            status.append("✗ index.faiss")
        
        if dataset_file.exists():
            status.append("✓ dataset.json")
        else:
            status.append("✗ dataset.json")
        
        if metadata_file.exists():
            status.append("✓ metadata.json")
        else:
            status.append("✗ metadata.json")
        
        # Загружаем метаданные
        info = " | ".join(status)
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                info += f" | {meta.get('total_vectors', '?')} векторов"
            except Exception:
                pass
        
        self.db_info_label.config(text=info, foreground="green" if "✗" not in info else "orange")
    
    def _run_tests(self):
        """Запускает тестирование."""
        if not self.db_path.get():
            messagebox.showwarning("Предупреждение", "Выберите папку с RAG-базой")
            return
        
        if self.testing_in_progress:
            return
        
        self.testing_in_progress = True
        self.run_btn.config(state='disabled')
        self.progress_bar['value'] = 0
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self._run_tests_thread, daemon=True)
        thread.start()
    
    def _run_tests_thread(self):
        """Выполняет тестирование в потоке."""
        try:
            from .rag_quality_tester import RAGQualityTester
            
            # Создаём тестировщик
            tester = RAGQualityTester(
                db_path=self.db_path.get()
            )
            
            # Обновляем порог
            tester.config['general']['threshold'] = self.threshold.get()
            
            # Прогресс-колбэк
            def progress_callback(category, progress):
                self.root.after(0, lambda: self._update_progress(category, progress))
            
            # Запускаем тесты
            self.test_results = tester.run_all_tests(progress_callback=progress_callback)
            
            # Обновляем UI
            self.root.after(0, self._display_results)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        
        finally:
            self.testing_in_progress = False
            self.root.after(0, lambda: self.run_btn.config(state='normal'))
    
    def _update_progress(self, category, progress):
        """Обновляет прогресс."""
        self.progress_bar['value'] = progress * 100
        self.progress_label.config(text=f"Тестирование: {category}...")
    
    def _display_results(self):
        """Отображает результаты."""
        if not self.test_results:
            return
        
        report = self.test_results
        
        # Общая оценка
        score = report.total_score
        passed = report.passed
        
        self.score_label.config(text=f"{score:.0f}/100")
        
        if passed:
            self.score_label.config(foreground="green")
            self.status_label.config(text="✅ ПРОЙДЕНО", foreground="green")
        else:
            self.score_label.config(foreground="red")
            self.status_label.config(text="❌ НЕ ПРОЙДЕНО", foreground="red")
        
        # Категории
        for cat_id, result in report.categories.items():
            if cat_id in self.category_bars:
                self.category_bars[cat_id]['value'] = result.score
                self.category_labels[cat_id].config(
                    text=f"{result.score:.0f}% {'✅' if result.passed else '❌'}"
                )
        
        # Метаданные
        self.metadata_text.config(state='normal')
        self.metadata_text.delete(1.0, tk.END)
        
        meta_text = f"Путь: {report.db_path}\n"
        meta_text += f"Время: {report.duration_seconds} сек\n"
        meta_text += f"Порог: {report.threshold}%\n"
        
        for key, value in report.metadata.items():
            meta_text += f"{key}: {value}\n"
        
        self.metadata_text.insert(tk.END, meta_text)
        self.metadata_text.config(state='disabled')
        
        # Детали тестов
        self.tests_tree.delete(*self.tests_tree.get_children())
        
        for cat, result in report.categories.items():
            for test in result.tests:
                status = "✅" if test.passed else "❌"
                tag = 'passed' if test.passed else 'failed'
                
                self.tests_tree.insert('', tk.END, values=(
                    test.test_name,
                    cat,
                    status,
                    f"{test.score * 100:.0f}%",
                    test.message
                ), tags=(tag,))
        
        # Графики
        self._draw_charts()
        
        # Рекомендации
        self.recommendations_text.delete(1.0, tk.END)
        
        rec_text = "📋 РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ\n"
        rec_text += "=" * 50 + "\n\n"
        
        for cat, result in report.categories.items():
            if result.recommendations:
                rec_text += f"\n{cat.upper()}\n"
                rec_text += "-" * 30 + "\n"
                for rec in result.recommendations:
                    rec_text += f"• {rec}\n"
        
        if rec_text.count('\n') < 5:
            rec_text += "\n✅ База данных соответствует требованиям качества!\n"
        
        self.recommendations_text.insert(tk.END, rec_text)
        
        # Активируем экспорт
        self.export_btn.config(state='normal')
        
        # Обновляем прогресс
        self.progress_bar['value'] = 100
        self.progress_label.config(text=f"Завершено за {report.duration_seconds} сек")
    
    def _draw_charts(self):
        """Рисует графики."""
        if not MATPLOTLIB_AVAILABLE or not self.test_results:
            return
        
        self.fig.clear()
        
        # График 1: Баллы по категориям
        ax1 = self.fig.add_subplot(121)
        
        categories = list(self.test_results.categories.keys())
        scores = [self.test_results.categories[c].score for c in categories]
        colors = ['#4CAF50' if self.test_results.categories[c].passed else '#F44336' for c in categories]
        
        bars = ax1.bar(categories, scores, color=colors)
        ax1.set_ylabel('Балл (%)')
        ax1.set_title('Баллы по категориям')
        ax1.set_ylim(0, 100)
        ax1.axhline(y=self.threshold.get(), color='orange', linestyle='--', label=f'Порог ({self.threshold.get()}%)')
        ax1.legend()
        
        # Подписи на барах
        for bar, score in zip(bars, scores):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
                    f'{score:.0f}%', ha='center', va='bottom')
        
        # График 2: Круговая диаграмма весов
        ax2 = self.fig.add_subplot(122)
        
        weights = [self.test_results.categories[c].weight for c in categories]
        ax2.pie(weights, labels=categories, autopct='%1.0f%%', startangle=90)
        ax2.set_title('Вес категорий')
        
        self.canvas.draw()
    
    def _run_category(self, category: str):
        """Запускает тесты одной категории."""
        messagebox.showinfo("Информация", f"Запуск тестов категории: {category}")
        # TODO: Реализовать запуск отдельной категории
        pass
    
    def _export_report(self, format: str):
        """Экспортирует отчёт."""
        if not self.test_results:
            messagebox.showwarning("Предупреждение", "Сначала запустите тестирование")
            return
        
        # Выбор файла
        extensions = {
            'markdown': '.md',
            'html': '.html',
            'json': '.json'
        }
        
        file_path = filedialog.asksaveasfilename(
            title="Сохранить отчёт",
            defaultextension=extensions.get(format, '.txt'),
            filetypes=[
                (f"{format.upper()} files", f"*{extensions.get(format, '.txt')}"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            from .generate_report import ReportGenerator
            
            generator = ReportGenerator(self.test_results)
            
            if format == 'markdown':
                generator.export_markdown(file_path)
            elif format == 'html':
                generator.export_html(file_path)
            elif format == 'json':
                generator.export_json(file_path)
            
            messagebox.showinfo("Успех", f"Отчёт сохранён: {file_path}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def _load_history(self):
        """Загружает историю тестов."""
        history_file = Path("Testing_vector_RAG_base/test_history.json")
        
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []
    
    def _show_history(self):
        """Показывает историю тестов."""
        if not self.history:
            messagebox.showinfo("История", "История тестов пуста")
            return
        
        # Создаём окно истории
        window = tk.Toplevel(self.root)
        window.title("История тестов")
        window.geometry("800x500")
        
        # Treeview
        columns = ('date', 'path', 'score', 'status')
        
        tree = ttk.Treeview(window, columns=columns, show='headings')
        
        tree.heading('date', text='Дата')
        tree.heading('path', text='Путь')
        tree.heading('score', text='Балл')
        tree.heading('status', text='Статус')
        
        tree.column('date', width=150)
        tree.column('path', width=400)
        tree.column('score', width=80)
        tree.column('status', width=100)
        
        # Заполняем
        for entry in reversed(self.history[-50:]):  # Последние 50
            status = "✅ Пройден" if entry.get('passed') else "❌ Не пройден"
            tree.insert('', tk.END, values=(
                entry.get('timestamp', 'N/A'),
                entry.get('db_path', 'N/A'),
                f"{entry.get('total_score', 0):.0f}%",
                status
            ))
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def _clear_history(self):
        """Очищает историю."""
        if messagebox.askyesno("Подтверждение", "Очистить историю тестов?"):
            self.history = []
            
            history_file = Path("Testing_vector_RAG_base/test_history.json")
            if history_file.exists():
                history_file.unlink()
            
            messagebox.showinfo("Успех", "История очищена")
    
    def _show_about(self):
        """Показывает информацию о программе."""
        messagebox.showinfo(
            "О программе",
            "🔍 Система тестирования качества RAG-баз\n\n"
            "Версия: 1.0.0\n\n"
            "Категории тестов:\n"
            "• Структура (10%)\n"
            "• Чанки (25%)\n"
            "• Поиск (30%)\n"
            "• Ответы (25%)\n"
            "• Покрытие (10%)\n\n"
            "Автор: Line_GV\n"
            "Telegram: @Line_GV"
        )


# ============================================================================
# ЗАПУСК
# ============================================================================

def main():
    """Запускает GUI."""
    root = tk.Tk()
    app = RAGQualityTesterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
