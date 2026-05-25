import sqlite3
import yaml
from concurrent.futures import ThreadPoolExecutor
from src.analyzer import ContentAnalyzer
from src.storage import Storage

analyzer = ContentAnalyzer()
storage = Storage()

conn = sqlite3.connect('data/news.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM articles")
rows = cursor.fetchall()
conn.close()

articles = [dict(row) for row in rows]
print(f"Total articles to evaluate: {len(articles)}")

def evaluate_and_delete(article):
    # Analyze the article content
    try:
        # Re-construct a minimal dict for analyzer
        art = {'title': article['title'], 'content': article['content']}
        analysis = analyzer.analyze_article(art)
        
        usefulness = analysis.get('usefulness', '').lower()
        if 'actionable' not in usefulness:
            return article['id'] # Return ID to delete
    except Exception as e:
        print(f"Error evaluating {article['id']}: {e}")
    return None

to_delete = []
with ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(evaluate_and_delete, articles)
    for res in results:
        if res is not None:
            to_delete.append(res)

if to_delete:
    print(f"Deleting {len(to_delete)} non-actionable articles...")
    conn = sqlite3.connect('data/news.db')
    cursor = conn.cursor()
    cursor.executemany("DELETE FROM articles WHERE id = ?", [(i,) for i in to_delete])
    conn.commit()
    conn.close()
    print("Deletion complete.")
else:
    print("No non-actionable articles found to delete.")
