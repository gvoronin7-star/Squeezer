#!/usr/bin/env python
"""
Запуск GUI тестирования качества RAG-баз.

Использование:
    python run_gui.py
"""

import sys
import os

# Добавляем родительскую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Testing_vector_RAG_base.gui_tester import main

if __name__ == "__main__":
    main()
