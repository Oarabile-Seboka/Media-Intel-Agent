import os
import json
import yaml
import requests
from dotenv import load_dotenv

load_dotenv()

class ContentAnalyzer:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        
        if self.api_key:
            self.model_name = self.config.get('llm', {}).get('model', 'sonar-pro')
        else:
            self.model_name = None
            print("Warning: No PERPLEXITY_API_KEY found. Running in mock mode.")

    def _load_config(self, path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def analyze_article(self, article):
        if not self.api_key:
            return self._mock_analyze(article)

        prompt = self._construct_prompt(article)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a personal news intelligence assistant. You must output only valid JSON without any markdown code blocks or extra text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.config.get('llm', {}).get('temperature', 0.2)
        }
        
        try:
            response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content'].strip()
            
            # Remove potential markdown formatting for JSON
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            
            if not isinstance(result, dict):
                print(f"Warning: LLM returned non-dict response: {result}")
                return self._mock_analyze(article)
            return result
        except Exception as e:
            print(f"Error analyzing article: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Response details: {response.text}")
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
        Compare the article content against the User Interests, keeping in mind that the user performs second and third-order analysis.
        - If the article has NO bearing on the interests, even indirectly, set "relevance_score" to "Low".
        - If it provides background, foundational information, or is tangentially related (valuable for second-order analysis), set to "Medium".
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
