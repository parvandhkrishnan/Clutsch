import json
import abc
import os

class AIProvider(abc.ABC):
    @abc.abstractmethod
    def analyze(self, text):
        pass

class MockAIProvider(AIProvider):
    def analyze(self, text):
        """
        Mocks an LLM analysis of the text.
        """
        text_lower = text.lower()
        urgency = 0.2
        importance = 0.2
        summary = "Standard communication."
        action_suggested = "Review"

        if "asap" in text_lower or "urgent" in text_lower or "immediately" in text_lower:
            urgency = 0.9
            summary = "High urgency detected via keywords."
            action_suggested = "Reply ASAP"
        elif "soon" in text_lower or "today" in text_lower:
            urgency = 0.6
            summary = "Moderate urgency based on timeline mentions."
            action_suggested = "Schedule for today"

        if "critical" in text_lower or "important" in text_lower or "blocker" in text_lower:
            importance = 0.9
            summary += " High importance due to impact keywords."
        elif "update" in text_lower or "fyi" in text_lower:
            importance = 0.3
            summary += " Likely informational/update."
            action_suggested = "Archive"

        # Semantic Analysis (New)
        semantics = []
        if "revenue" in text_lower or "budget" in text_lower or "payment" in text_lower:
            semantics.append("financial_impact")
        if "bug" in text_lower or "refactor" in text_lower or "legacy" in text_lower:
            semantics.append("technical_debt")
        if "customer" in text_lower or "client" in text_lower or "user feedback" in text_lower:
            semantics.append("customer_success")
        if "legal" in text_lower or "policy" in text_lower or "gdpr" in text_lower:
            semantics.append("compliance")

        return {
            "urgency": urgency,
            "importance": importance,
            "summary": summary.strip(),
            "action_suggested": action_suggested,
            "semantics": semantics
        }

from security import sanitize_pii
import hashlib
from utils.cache import config_cache

class AIAnalyzer:
    def __init__(self, provider: AIProvider = None):
        # Use a sub-cache for AI analysis
        self.cache = config_cache 
        if provider:
            self.provider = provider
        else:
            try:
                from gemini_provider import GeminiProvider
                self.provider = GeminiProvider()
                if not self.provider.api_key:
                    self.provider = MockAIProvider()
            except ImportError:
                self.provider = MockAIProvider()
            except Exception as e:
                print(f"Error initializing AI provider: {e}")
                self.provider = MockAIProvider()

    def analyze_message(self, text):
        """
        Analyzes the message text and returns urgency, importance, and summary.
        Applies PII sanitization and uses caching.
        """
        if not text:
            return {
                "urgency": 0.0,
                "importance": 0.0,
                "summary": "Empty message."
            }
            
        sanitized_text = sanitize_pii(text)
        
        # Cache key based on sanitized text
        cache_key = f"ai_analysis_{hashlib.md5(sanitized_text.encode()).hexdigest()}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
            
        result = self.provider.analyze(sanitized_text)
        
        # Cache the result
        self.cache.set(cache_key, result)
        
        return result

if __name__ == "__main__":
    analyzer = AIAnalyzer()
    
    test_messages = [
        "Hey, can you take a look at the report ASAP? It's a blocker for the release.",
        "Just a heads up, the meeting has been moved to 3 PM today.",
        "FYI: The pantry has been restocked with snacks.",
        "I need the final numbers for the budget by the end of the day."
    ]
    
    for msg in test_messages:
        result = analyzer.analyze_message(msg)
        print(f"Text: {msg}")
        print(f"Result: {json.dumps(result, indent=2)}\n")
