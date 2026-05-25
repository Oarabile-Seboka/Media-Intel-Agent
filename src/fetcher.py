import feedparser
import yaml
from datetime import datetime
from .storage import Storage

class RSSFetcher:
    def __init__(self, config_path="config.yaml", storage: Storage = None):
        self.config = self._load_config(config_path)
        self.storage = storage

    def _load_config(self, path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def fetch_all(self):
        all_feeds_articles = []
        feeds = self.config.get('feeds', [])
        
        for feed_config in feeds:
            print(f"Fetching {feed_config['name']}...")
            try:
                feed = feedparser.parse(feed_config['url'])
            except Exception as e:
                print(f"Error fetching {feed_config['name']}: {e}")
                continue
                
            feed_articles = []
            for entry in feed.entries:
                url = entry.link
                
                # Check for duplicates if storage is provided
                if self.storage and self.storage.article_exists(url):
                    continue
                
                # Extract content (prefer full content if available, else summary)
                content = ""
                if 'content' in entry:
                    content = entry.content[0].value
                elif 'summary' in entry:
                    content = entry.summary
                
                # Extract images
                image_url = None
                if 'media_content' in entry and len(entry.media_content) > 0:
                    image_url = entry.media_content[0]['url']
                elif 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
                     image_url = entry.media_thumbnail[0]['url']
                elif 'enclosures' in entry and len(entry.enclosures) > 0:
                    for enclosure in entry.enclosures:
                        if enclosure.type.startswith('image/'):
                            image_url = enclosure.href
                            break
                
                # If no image found in standard fields, try to find the first img tag in content
                if not image_url and content and ('<' in content and '>' in content):
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    img_tag = soup.find('img')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag['src']

                published = entry.get('published', datetime.now().isoformat())
                
                article = {
                    'title': entry.title,
                    'url': url,
                    'published_date': published,
                    'content': content,
                    'source': feed_config['name'],
                    'category_hint': feed_config.get('category'), # Pass hint from feed config
                    'image_url': image_url
                }
                feed_articles.append(article)
            
            all_feeds_articles.append(feed_articles)
            
        # Interleave articles from all feeds to ensure fair distribution
        new_articles = []
        if all_feeds_articles:
            max_len = max(len(fa) for fa in all_feeds_articles)
            for i in range(max_len):
                for fa in all_feeds_articles:
                    if i < len(fa):
                        new_articles.append(fa[i])
                        
        return new_articles
