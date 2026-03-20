#!/usr/bin/env python3
"""
Автоматическая очистка репозитория от временных и устаревших файлов.

Использование:
    python cleanup_repository.py [--dry-run] [--full]

Параметры:
    --dry-run    Только показать, что будет удалено (без удаления)
    --full       Полная очистка (включая реорганизацию файлов)
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime


class RepositoryCleaner:
    """Класс для очистки репозитория."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.deleted_files = []
        self.deleted_dirs = []
        self.moved_files = []
        
    def print_header(self, title: str):
        """Выводит заголовок."""
        print("\n" + "=" * 70)
        print(title)
        print("=" * 70)
    
    def print_action(self, action: str, path: str):
        """Выводит действие."""
        if self.dry_run:
            print(f"[DRY-RUN] {action}: {path}")
        else:
            print(f"{action}: {path}")
    
    def delete_file(self, file_path: Path) -> bool:
        """Удаляет файл."""
        if not file_path.exists():
            return False
        
        if self.dry_run:
            self.print_action("WOULD DELETE FILE", str(file_path))
        else:
            self.print_action("DELETING FILE", str(file_path))
            file_path.unlink()
        
        self.deleted_files.append(str(file_path))
        return True
    
    def delete_dir(self, dir_path: Path) -> bool:
        """Удаляет директорию."""
        if not dir_path.exists():
            return False
        
        if self.dry_run:
            self.print_action("WOULD DELETE DIR", str(dir_path))
        else:
            self.print_action("DELETING DIR", str(dir_path))
            shutil.rmtree(dir_path)
        
        self.deleted_dirs.append(str(dir_path))
        return True
    
    def move_file(self, src: Path, dst: Path) -> bool:
        """Перемещает файл."""
        if not src.exists():
            return False
        
        # Создаём директорию назначения
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        if self.dry_run:
            self.print_action("WOULD MOVE", f"{src} -> {dst}")
        else:
            self.print_action("MOVING", f"{src} -> {dst}")
            shutil.move(str(src), str(dst))
        
        self.moved_files.append((str(src), str(dst)))
        return True
    
    def cleanup_temp_files(self):
        """Очищает временные файлы."""
        self.print_header("CLEANUP: Temporary Files")
        
        # Удаляем логи
        logs_dir = Path("logs")
        if logs_dir.exists():
            self.delete_dir(logs_dir)
        
        # Удаляем выходные данные
        output_dirs = [
            "output",
            "output_module_2",
            "output_module_3",
            "output_module_4",
            # Дополнительные временные директории от тестирования
            "cache",
            "demo_output",
            "final_test",
            "final_test2",
            "output_full",
            "output_test",
            "test_analysis_output",
            "test_batch_output",
            "test_final",
            "test_full_pipeline",
            "test_llm_output",
            "test_pipeline_output",
            "test_quick_output",
            "test_rag_output"
        ]
        for dir_name in output_dirs:
            dir_path = Path(dir_name)
            if dir_path.exists():
                self.delete_dir(dir_path)
        
        # Удаляем временные файлы
        temp_files = [
            "pdf_analysis_report.html",
            "test_results_final.json"
        ]
        
        for file_name in temp_files:
            file_path = Path(file_name)
            if file_path.exists():
                self.delete_file(file_path)
    
    def cleanup_old_docs(self):
        """Удаляет устаревшую документацию."""
        self.print_header("CLEANUP: Old Documentation")
        
        old_docs = [
            "FINAL_INSTRUCTIONS.md",
            "GITHUB_PREPARATION_REPORT.md",
            "README_PRODUCTION.md",
            "DOCS_INDEX.md",
            "RAG_BUILDER_GUIDE.md",
            "BACKUP_GUIDE.md",
            "ISSUE_TEMPLATE.md",
            "PULL_REQUEST_TEMPLATE.md",
            "PROJECT_SUMMARY.md"
        ]
        
        for doc in old_docs:
            doc_path = Path(doc)
            if doc_path.exists():
                self.delete_file(doc_path)
    
    def reorganize_files(self):
        """Реорганизует файлы."""
        self.print_header("REORGANIZATION: Moving Files")
        
        # Создаём директории
        dirs_to_create = ["examples", "tests", "utils"]
        for dir_name in dirs_to_create:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                if self.dry_run:
                    print(f"[DRY-RUN] WOULD CREATE DIR: {dir_path}")
                else:
                    print(f"CREATING DIR: {dir_path}")
                    dir_path.mkdir(exist_ok=True)
        
        # Перемещаем демо-файлы
        demo_files = [
            "demo_advanced_rag.py",
            "demo_analyzer.py",
            "demo_improved_rag.py",
            "demo_vectorization.py",
            "demo_visual.py"
        ]
        
        for demo in demo_files:
            src = Path(demo)
            if src.exists():
                dst = Path("examples") / demo
                self.move_file(src, dst)
        
        # Перемещаем тесты
        test_files = [
            "test_final.py",
            "test_improved_rag_real.py",
            "test_llm_enrichment.py",
            "test_llm_models.py",
            "test_rag_comparison.py",
            "test_search.py",
            "test_system.py",
            "test_vectorizer.py",
            "run_test.py"
        ]
        
        for test in test_files:
            src = Path(test)
            if src.exists():
                dst = Path("tests") / test
                self.move_file(src, dst)
        
        # Перемещаем утилиты
        util_files = [
            "analyze_pdf.py",
            "check_models.py",
            "create_backup.py",
            "restore_backup.py"
        ]
        
        for util in util_files:
            src = Path(util)
            if src.exists():
                dst = Path("utils") / util
                self.move_file(src, dst)
        
        # Создаём __init__.py в tests/
        init_file = Path("tests/__init__.py")
        if not init_file.exists():
            if self.dry_run:
                print(f"[DRY-RUN] WOULD CREATE: {init_file}")
            else:
                print(f"CREATING: {init_file}")
                init_file.touch()
    
    def update_gitignore(self):
        """Обновляет .gitignore."""
        self.print_header("UPDATE: .gitignore")
        
        gitignore_path = Path(".gitignore")
        if not gitignore_path.exists():
            print("WARNING: .gitignore not found")
            return
    
        # Читаем текущий .gitignore
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Добавляем новые записи
        new_entries = [
            "",
            "# Auto-added by cleanup script",
            "logs/",
            "output/",
            "output_module_2/",
            "output_module_3/",
            "output_module_4/",
            "*.html",
            "*.json.bak",
            "test_results*.json",
            ""
        ]
        
        # Проверяем, нужно ли добавлять
        needs_update = False
        for entry in new_entries:
            if entry and entry not in content:
                needs_update = True
                break
        
        if needs_update:
            if self.dry_run:
                print("[DRY-RUN] WOULD UPDATE: .gitignore")
            else:
                print("UPDATING: .gitignore")
                with open(gitignore_path, 'a', encoding='utf-8') as f:
                    f.write('\n'.join(new_entries))
        else:
            print("OK: .gitignore already up to date")
    
    def print_summary(self):
        """Выводит итоговый отчёт."""
        self.print_header("CLEANUP SUMMARY")
        
        print(f"\nDeleted files: {len(self.deleted_files)}")
        print(f"Deleted directories: {len(self.deleted_dirs)}")
        print(f"Moved files: {len(self.moved_files)}")
        
        if self.dry_run:
            print("\n[DRY-RUN MODE] No actual changes were made.")
            print("Run without --dry-run to apply changes.")
        else:
            print("\n[CHANGES APPLIED] Repository has been cleaned.")
            print("Please test the application to ensure everything works.")
    
    def run(self, full: bool = False):
        """Выполняет очистку."""
        print("=" * 70)
        print("REPOSITORY CLEANUP SCRIPT")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: {'DRY-RUN' if self.dry_run else 'LIVE'}")
        print(f"Full cleanup: {full}")
        print("=" * 70)
        
        # Этап 1: Удаление временных файлов
        self.cleanup_temp_files()
        
        # Этап 2: Удаление устаревшей документации
        self.cleanup_old_docs()
        
        # Этап 3: Обновление .gitignore
        self.update_gitignore()
        
        # Этап 4: Реорганизация (только если указан --full)
        if full:
            self.reorganize_files()
        
        # Итоговый отчёт
        self.print_summary()


def main():
    """Главная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Cleanup repository from temporary and outdated files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show what would be deleted (without actually deleting)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full cleanup including file reorganization"
    )
    
    args = parser.parse_args()
    
    # Предупреждение для режима live
    if not args.dry_run:
        print("\n" + "!" * 70)
        print("WARNING: You are about to DELETE and MOVE files!")
        print("!" * 70)
        print("\nThis will:")
        print("  - Delete temporary files (logs/, output*/, *.html)")
        print("  - Delete outdated documentation")
        print("  - Update .gitignore")
        
        if args.full:
            print("  - Reorganize files (create examples/, tests/, utils/)")
        
        print("\nRecommendation: Run with --dry-run first to see what will happen.")
        
        response = input("\nContinue? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            return
    
    # Запускаем очистку
    cleaner = RepositoryCleaner(dry_run=args.dry_run)
    cleaner.run(full=args.full)


if __name__ == "__main__":
    main()
