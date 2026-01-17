import json
from duckduckgo_search import DDGS
from .storage import Storage
from .analyzer import ContentAnalyzer

class QueryInterface:
    def __init__(self, storage: Storage, analyzer: ContentAnalyzer):
        self.storage = storage
        self.analyzer = analyzer

    def handle_query(self, user_query):
        """
        Interprets the user query and retrieves relevant articles.
        """
        # 1. Try to understand intent using LLM (if available)
        if self.analyzer.model:
            intent = self._extract_intent(user_query)
            
            if intent.get('type') == 'web_search':
                return self._search_web(intent.get('keywords', user_query))
            elif intent.get('type') == 'search':
                return self.storage.search_articles(intent.get('keywords', user_query))
            elif intent.get('type') == 'filter':
                return self.storage.get_articles(
                    relevance=intent.get('relevance'),
                    category=intent.get('category')
                )
        
        # 2. Fallback: Simple keyword search
        return self.storage.search_articles(user_query)

    def _extract_intent(self, query):
        try:
            prompt = f"""
            Extract search intent from the user query. 
            Query: "{query}"
            
            Determine if the user wants to search the "web" (general knowledge, current events not in feed) or "local" (saved news articles).
            
            Return JSON with:
            - type: "web_search", "search" (local), or "filter"
            - keywords: (for search) extracted keywords
            - category: (optional) inferred category
            - relevance: (optional) inferred relevance level (High/Medium/Low)
            """
            
            response = self.analyzer.model.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
            print(f"Error extracting intent: {e}")
            return {"type": "search", "keywords": query}

    def _search_web(self, query):
        print(f"Searching web for: {query}")
        try:
            results = DDGS().text(query, max_results=5)
            formatted_results = []
            for r in results:
                formatted_results.append({
                    'title': r['title'],
                    'url': r['href'],
                    'summary': r['body'],
                    'published_date': 'Just now',
                    'category': 'Web Result',
                    'relevance_score': 'External',
                    'tags': ['web'],
                    'image_url': None
                })
            return formatted_results
        except Exception as e:
            print(f"Web search error: {e}")
            return []

    def format_results(self, articles):
        if not articles:
            return "No matching articles found."
            
        output = []
        for article in articles:
            output.append(f"Title: {article['title']}")
            output.append(f"Date: {article['published_date']}")
            output.append(f"Category: {article['category']} | Relevance: {article['relevance_score']}")
            output.append(f"Summary: {article['summary']}")
            output.append(f"URL: {article['url']}")
            output.append("-" * 40)
            
        return "\n".join(output)
