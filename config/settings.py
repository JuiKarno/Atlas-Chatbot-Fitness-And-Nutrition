import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # OpenRouter API Configuration (loaded from .env)
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    AI_MODEL = os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-4b:free')
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Legacy Groq key (kept for reference)
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    FIREBASE_CREDENTIALS = "serviceAccountKey.json"

    # Recommendation Weights (Moved from app.py for easy tuning)
    WEIGHTS = {
        'beginner': {'difficulty': 0.1, 'safety': 0.9},
        'advanced': {'difficulty': 0.9, 'safety': 0.4}
    }