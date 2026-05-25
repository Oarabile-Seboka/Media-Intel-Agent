import sqlite3
import json
import os
from datetime import datetime
from dateutil import parser

class Storage:
    def __init__(self, db_path="data/news.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT UNIQUE,
                published_date TEXT,
                content TEXT,
                summary TEXT,
                tags TEXT,
                relevance_score TEXT,
                category TEXT,
                image_url TEXT,
                created_at TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def add_article(self, article_data):
        """
        Adds an article to the database.
        article_data should be a dict with keys:
        title, url, published_date, content, summary, tags (list), relevance_score, category, image_url
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if column exists (migration)
            cursor.execute("PRAGMA table_info(articles)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'image_url' not in columns:
                cursor.execute("ALTER TABLE articles ADD COLUMN image_url TEXT")

            # Normalize published_date to YYYY-MM-DD for easier filtering
            date_str = article_data.get('published_date', '')
            try:
                # Common RSS date formats can be complex; let's attempt to parse
                dt = parser.parse(date_str)
                iso_date = dt.strftime('%Y-%m-%d')
            except:
                iso_date = datetime.now().strftime('%Y-%m-%d')

            cursor.execute('''
                INSERT OR IGNORE INTO articles (
                    title, url, published_date, content, summary, tags, 
                    relevance_score, category, image_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article_data['title'],
                article_data['url'],
                iso_date,
                article_data['content'],
                article_data.get('summary', ''),
                json.dumps(article_data.get('tags', [])),
                article_data.get('relevance_score', 'Low'),
                article_data.get('category', 'Uncategorized'),
                article_data.get('image_url'),
                datetime.now().isoformat()
            ))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
        finally:
            conn.close()

    def article_exists(self, url):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM articles WHERE url = ?', (url,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def get_articles(self, limit=50, relevance=None, category=None, start_date=None, end_date=None):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM articles'
        params = []
        conditions = []

        if relevance:
            conditions.append('relevance_score = ?')
            params.append(relevance)
        
        if category:
            conditions.append('category = ?')
            params.append(category)
            
        if start_date:
            conditions.append('published_date >= ?')
            params.append(start_date)
            
        if end_date:
            conditions.append('published_date <= ?')
            params.append(end_date)
            
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
            
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        articles = []
        for row in rows:
            article = dict(row)
            article['tags'] = json.loads(article['tags'] or '[]')
            articles.append(article)
            
        return articles

    def get_unique_categories(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT category FROM articles WHERE category IS NOT NULL AND category != ""')
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def search_articles(self, query_text):
        # Simple LIKE search for now
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = '''
            SELECT * FROM articles 
            WHERE title LIKE ? OR summary LIKE ? OR content LIKE ?
            ORDER BY created_at DESC LIMIT 20
        '''
        search_term = f"%{query_text}%"
        cursor.execute(sql, (search_term, search_term, search_term))
        
        rows = cursor.fetchall()
        conn.close()
        
        articles = []
        for row in rows:
            article = dict(row)
            article['tags'] = json.loads(article['tags'] or '[]')
            articles.append(article)
            
        return articles

    def delete_article(self, article_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM articles WHERE id = ?', (article_id,))
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes > 0

    def delete_all_articles(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM articles')
        conn.commit()
        changes = conn.total_changes
        conn.close()
        return changes

    def export_to_csv(self, output_path="data/articles_export.csv", limit=None):
        import csv
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM articles ORDER BY created_at DESC'
        if limit is not None:
            query += f' LIMIT {int(limit)}'
            
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            return None
            
        fieldnames = rows[0].keys()
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
                
        conn.close()
        return output_path
