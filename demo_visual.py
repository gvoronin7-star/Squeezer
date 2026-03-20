#!/usr/bin/env python3
"""
Визуальный демонстратор анализа PDF в HTML.
Создает красивый отчет с визуализацией.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.pdf_analyzer import analyze_pdf


def generate_html_report(results: list) -> str:
    """Генерирует HTML отчет."""
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Анализ PDF - Squeezer</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        h1 {{
            text-align: center;
            color: #00d4ff;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .file-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .file-icon {{
            font-size: 40px;
        }}
        .file-name {{
            font-size: 1.5em;
            color: #fff;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric {{
            background: rgba(0,212,255,0.1);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            color: #00d4ff;
            font-weight: bold;
        }}
        .metric-label {{
            color: #888;
            font-size: 0.9em;
        }}
        
        .type-badge {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.9em;
        }}
        .type-faq {{ background: #ff6b6b; color: #fff; }}
        .type-textbook {{ background: #4ecdc4; color: #000; }}
        .type-article {{ background: #45b7d1; color: #fff; }}
        .type-report {{ background: #96ceb4; color: #000; }}
        .type-book {{ background: #ffeaa7; color: #000; }}
        
        .recommendations {{
            background: linear-gradient(135deg, rgba(0,212,255,0.1) 0%, rgba(0,255,136,0.1) 100%);
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
        }}
        .rec-title {{
            color: #00ff88;
            font-size: 1.3em;
            margin-bottom: 15px;
        }}
        
        .rec-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .rec-item {{
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            padding: 15px;
        }}
        .rec-label {{
            color: #888;
            font-size: 0.85em;
            margin-bottom: 5px;
        }}
        .rec-value {{
            color: #00ff88;
            font-size: 1.2em;
            font-weight: bold;
        }}
        .rec-default {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        .rationale {{
            margin-top: 20px;
            padding: 15px;
            background: rgba(255,107,107,0.1);
            border-radius: 10px;
        }}
        .rationale-title {{
            color: #ff6b6b;
            margin-bottom: 10px;
        }}
        .rationale-item {{
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }}
        .rationale-item:before {{
            content: "→";
            position: absolute;
            left: 0;
            color: #ff6b6b;
        }}
        
        .comparison {{
            margin-top: 30px;
        }}
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .comparison-table th {{
            background: rgba(0,212,255,0.2);
            padding: 15px;
            text-align: left;
            color: #00d4ff;
        }}
        .comparison-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .comparison-table tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 5px;
            font-size: 0.85em;
        }}
        .badge-ok {{ background: #00ff88; color: #000; }}
        .badge-diff {{ background: #ffeaa7; color: #000; }}
        
        .summary {{
            text-align: center;
            margin-top: 40px;
            padding: 30px;
            background: linear-gradient(135deg, rgba(0,212,255,0.2) 0%, rgba(0,255,136,0.2) 100%);
            border-radius: 15px;
        }}
        .summary h2 {{ color: #00d4ff; margin-bottom: 15px; }}
        .summary-stats {{
            display: flex;
            justify-content: center;
            gap: 40px;
            flex-wrap: wrap;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5em;
            color: #00ff88;
            font-weight: bold;
        }}
        .stat-label {{ color: #888; }}
        
    </style>
</head>
<body>
    <div class="container">
        <h1>🔬 Squeezer PDF Analyzer</h1>
        <p class="subtitle">Отчет о предварительном анализе документов | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
    
    # Карточки файлов
    for r in results:
        analysis = r["analysis"]
        rec = r["recommendations"]
        
        doc_type = analysis.get("document_type", "document")
        
        html += f"""
        <div class="card">
            <div class="file-header">
                <span class="file-icon">📄</span>
                <span class="file-name">{r['file']}</span>
                <span class="type-badge type-{doc_type}">{doc_type}</span>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{analysis['total_pages']}</div>
                    <div class="metric-label">Страниц</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{analysis['avg_chars_per_page']}</div>
                    <div class="metric-label">Символов/стр</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{analysis['density']}</div>
                    <div class="metric-label">Плотность</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{analysis['complexity']}</div>
                    <div class="metric-label">Сложность</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{analysis['heading_count']}</div>
                    <div class="metric-label">Заголовков</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{analysis['paragraph_count']}</div>
                    <div class="metric-label">Абзацев</div>
                </div>
            </div>
            
            <div class="recommendations">
                <div class="rec-title">🎯 Рекомендации по обработке</div>
                <div class="rec-grid">
                    <div class="rec-item">
                        <div class="rec-label">Размер чанка</div>
                        <div class="rec-value">{rec.get('chunk_size')}</div>
                        <div class="rec-default">Дефолт: 500</div>
                    </div>
                    <div class="rec-item">
                        <div class="rec-label">Overlap</div>
                        <div class="rec-value">{rec.get('overlap')}</div>
                        <div class="rec-default">Дефолт: 50</div>
                    </div>
                    <div class="rec-item">
                        <div class="rec-label">Стратегия</div>
                        <div class="rec-value">{rec.get('chunking_strategy')}</div>
                    </div>
                    <div class="rec-item">
                        <div class="rec-label">OCR</div>
                        <div class="rec-value">{'Да' if rec.get('ocr_enabled') else 'Нет'}</div>
                    </div>
                    <div class="rec-item">
                        <div class="rec-label">LLM</div>
                        <div class="rec-value">{'Да' if rec.get('llm_enabled') else 'Нет'}</div>
                    </div>
                </div>
            </div>
        """
        
        if rec.get("rationale"):
            html += '<div class="rationale"><div class="rationale-title">💡 Почему такие настройки:</div>'
            for rationale in rec["rationale"]:
                html += f'<div class="rationale-item">{rationale}</div>'
            html += '</div>'
        
        html += '</div>'
    
    # Таблица сравнения
    html += """
        <div class="card comparison">
            <h2>📊 Сравнение рекомендаций</h2>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Файл</th>
                        <th>Тип</th>
                        <th>Рекоменд. chunk</th>
                        <th>Дефолт chunk</th>
                        <th>Изменение</th>
                        <th>Эффект</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for r in results:
        analysis = r["analysis"]
        rec = r["recommendations"]
        doc_type = analysis.get("document_type", "document")
        
        rec_chunk = rec.get("chunk_size", 500)
        default_chunk = 500
        
        if rec_chunk < default_chunk:
            change = "↓"
            badge_class = "badge-ok"
            effect = "Оптимально"
        elif rec_chunk > default_chunk:
            change = "↑"
            badge_class = "badge-ok"
            effect = "Больше контекста"
        else:
            change = "="
            badge_class = "badge-diff"
            effect = "Без изменений"
        
        html += f"""
                    <tr>
                        <td>{r['file']}</td>
                        <td><span class="type-badge type-{doc_type}">{doc_type}</span></td>
                        <td><strong>{rec_chunk}</strong></td>
                        <td>{default_chunk}</td>
                        <td>{change}</td>
                        <td><span class="badge {badge_class}">{effect}</span></td>
                    </tr>
        """
    
    html += """
                </tbody>
            </table>
        </div>
    """
    
    # Итоги
    avg_chunk = sum(r["recommendations"].get("chunk_size", 500) for r in results) / len(results)
    avg_overlap = sum(r["recommendations"].get("overlap", 50) for r in results) / len(results)
    
    types_count = {}
    for r in results:
        t = r["analysis"]["document_type"]
        types_count[t] = types_count.get(t, 0) + 1
    
    html += f"""
        <div class="summary">
            <h2>📈 Итоги анализа</h2>
            <div class="summary-stats">
                <div class="stat">
                    <div class="stat-value">{len(results)}</div>
                    <div class="stat-label">Документов</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{avg_chunk:.0f}</div>
                    <div class="stat-label">Средний chunk_size</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{avg_overlap:.0f}</div>
                    <div class="stat-label">Средний overlap</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(types_count)}</div>
                    <div class="stat-label">Типов документов</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    return html


def main():
    print("=" * 60)
    print("SQUEEZER PDF ANALYZER - VISUAL REPORT")
    print("=" * 60)
    
    pdf_dir = Path("pdfs")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("PDF files not found!")
        return
    
    print(f"\nFound {len(pdf_files)} PDF files\n")
    
    results = []
    for pdf_file in pdf_files:
        print(f"Analyzing: {pdf_file.name}...", end=" ")
        analysis = analyze_pdf(str(pdf_file))
        
        if "error" not in analysis:
            results.append({
                "file": pdf_file.name,
                "analysis": analysis,
                "recommendations": analysis.get("recommendations", {})
            })
            print(f"OK - {analysis.get('document_type')}")
        else:
            print(f"ERROR - {analysis['error']}")
    
    # Generate HTML
    html = generate_html_report(results)
    output_file = "pdf_analysis_report.html"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"\n[OK] HTML report saved: {output_file}")
    print(f"\nOpen in browser to see visual report!")
    
    # Also print text summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for r in results:
        rec = r["recommendations"]
        print(f"\n{r['file']}:")
        print(f"  Type: {r['analysis']['document_type']}")
        print(f"  chunk_size: {rec.get('chunk_size')} (default: 500)")
        print(f"  overlap: {rec.get('overlap')} (default: 50)")
        print(f"  strategy: {rec.get('chunking_strategy')}")


if __name__ == "__main__":
    main()
