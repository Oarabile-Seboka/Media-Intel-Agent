import os
import json
import yaml
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class ContentAnalyzer:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use a model that supports JSON mode if available, or just standard Gemini Pro
            model_name = self.config.get('llm', {}).get('model', 'gemini-1.5-flash')
            self.model = genai.GenerativeModel(model_name,
                generation_config={"response_mime_type": "application/json"}
            )
        else:
            self.model = None
            print("Warning: No GEMINI_API_KEY found. Running in mock mode.")

    def _load_config(self, path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def analyze_article(self, article):
        if not self.model:
            return self._mock_analyze(article)

        prompt = self._construct_prompt(article)
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            if not isinstance(result, dict):
                print(f"Warning: LLM returned non-dict response: {result}")
                return self._mock_analyze(article)
            return result
        except Exception as e:
            print(f"Error analyzing article: {e}")
            return self._mock_analyze(article)

    def _construct_prompt(self, article):
        tagging_config = self.config.get('tagging', {})
        interests = tagging_config.get('interests', [])
        categories = tagging_config.get('categories', [])
        
        return f"""
        You are a personal news intelligence assistant. Analyze the following article and provide a structured JSON response.

        Article Details:
        Title: {article['title']}
        Content: {article['content'][:5000]}... (truncated if too long)
        
        Context:
        User Interests: {', '.join(interests)}
        Possible Categories: {', '.join(categories)}

        CRITICAL INSTRUCTION: 
        Compare the article content rigorously against the User Interests. 
        - If the article is NOT related to any of the interests, set "relevance_score" to "Low".
        - If it is tangentially related, set to "Medium".
        - If it directly impacts or discusses a core interest, set to "High".
        
        Required JSON Structure:
        {{
            "summary": "Concise 3-5 sentence summary. Focus on the 'So What?'",
            "relevance_score": "High, Medium, or Low",
            "usefulness": "Actionable, Informative, or Background",
            "impact_proximity": "Immediate, Short-term, Long-term, or Background",
            "category": "Select best fit from provided categories",
            "tags": ["tag1", "tag2", "tag3"]
        }}
        """

    def _mock_analyze(self, article):
        """Fallback for when no API key is present or on error."""
        return {
            "summary": "Mock summary: " + article['title'],
            "relevance_score": "Low",
            "usefulness": "Background",
            "impact_proximity": "Background",
            "category": "Uncategorized",
            "tags": ["mock", "test"]
        }
