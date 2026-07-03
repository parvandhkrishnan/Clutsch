import os
import json
import google.generativeai as genai
from ai_analyzer import AIProvider

class GeminiProvider(AIProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use gemini-1.5-flash for speed and cost-effectiveness
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def analyze(self, text):
        if not self.model:
            raise ValueError("Gemini API key not provided.")

        prompt = f"""
        Analyze the following communication and provide a priority assessment.
        Return the result ONLY as a JSON object with the following fields:
        - urgency (float between 0.0 and 1.0): How time-sensitive is this?
        - importance (float between 0.0 and 1.0): How critical is this to the user's goals?
        - summary (string): A one-sentence explanation of WHY it scored this way.
        - action_suggested (string): Optional suggested action (reply, review, ignore, etc.).

        Communication:
        "{text}"
        """

        response = self.model.generate_content(prompt)
        
        try:
            text_response = response.text.strip()
            # Handle markdown blocks if present
            if text_response.startswith("```json"):
                text_response = text_response.split("```json")[1].split("```")[0].strip()
            elif text_response.startswith("```"):
                text_response = text_response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(text_response)
            return {
                "urgency": float(result.get("urgency", 0.5)),
                "importance": float(result.get("importance", 0.5)),
                "summary": result.get("summary", "AI analysis complete."),
                "action_suggested": result.get("action_suggested", "None")
            }
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            print(f"Raw response: {response.text}")
            raise e
