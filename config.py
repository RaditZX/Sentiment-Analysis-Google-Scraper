import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

# GitHub Models Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_ENDPOINT = os.getenv("GITHUB_ENDPOINT", "https://models.github.ai/inference")
GITHUB_MODEL = os.getenv("GITHUB_MODEL", "gpt-4o-mini")

# MySQL Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'sentiment_db'),
    'user': os.getenv('DB_USER', 'lucid'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

# Apify
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
