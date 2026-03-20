"""
Centralized configuration for Company Career Scout.
All settings in one place for easy updates.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LLM PROVIDER SETTINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Default models per provider — update here when models change
DEFAULT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "google": "gemini-2.5-flash",
    "anthropic": "claude-haiku-4-5-20250315",
    "openai": "gpt-4o-mini",
}

# LangChain class mappings (module_name, class_name)
PROVIDER_CLASSES = {
    "groq": ("langchain_groq", "ChatGroq"),
    "google": ("langchain_google_genai", "ChatGoogleGenerativeAI"),
    "anthropic": ("langchain_anthropic", "ChatAnthropic"),
    "openai": ("langchain_openai", "ChatOpenAI"),
}

# Providers with free tiers
FREE_TIER_PROVIDERS = {"groq", "google"}

# Display labels for the frontend dropdown
MODEL_DISPLAY_NAMES = {
    "groq": "Groq — Llama 3.3 70B (free, default)",
    "google": "Google Gemini — gemini-2.5-flash (free)",
    "anthropic": "Anthropic Claude — claude-haiku-4-5 (free credits)",
    "openai": "OpenAI — gpt-4o-mini (paid, fallback)",
}

# LLM temperature
DEFAULT_TEMPERATURE = 0.1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API KEYS — loaded from .env, overridable via frontend
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Maps provider name → env var name
API_KEY_ENV_VARS = {
    "groq": "GROQ_API_KEY",
    "google": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "tavily": "TAVILY_API_KEY",
    "serpapi": "SERPAPI_KEY",
    "reddit": "REDDIT_CLIENT_ID",  # not used anymore, kept for reference
}

# Frontend display labels and help text for API key inputs
API_KEY_UI = {
    "groq": {
        "label": "Groq API Key",
        "help": "Get free key at console.groq.com",
        "required": False,
    },
    "google": {
        "label": "Google AI Studio Key",
        "help": "Get free key at aistudio.google.com",
        "required": False,
    },
    "anthropic": {
        "label": "Anthropic API Key",
        "help": "Get key at console.anthropic.com",
        "required": False,
    },
    "openai": {
        "label": "OpenAI API Key",
        "help": "Get key at platform.openai.com",
        "required": False,
    },
    "tavily": {
        "label": "Tavily Search API Key",
        "help": "Get free key at app.tavily.com",
        "required": False,
    },
    "serpapi": {
        "label": "SerpAPI Key",
        "help": "Get key at serpapi.com",
        "required": False,
    },
}


def get_api_key(provider: str) -> str:
    """
    Get API key for a provider from environment variables.

    Args:
        provider: Provider name (e.g. 'groq', 'google').

    Returns:
        API key string, or empty string if not found.
    """
    env_var = API_KEY_ENV_VARS.get(provider, "")
    return os.environ.get(env_var, "")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CRAWLER SETTINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Reddit (uses public JSON API, no auth needed)
REDDIT_SUBREDDITS = ["srilanka", "colombo", "askSriLanka"]
REDDIT_MAX_POSTS = 30
REDDIT_MAX_COMMENTS_PER_POST = 5
REDDIT_MAX_AGE_YEARS = 2
REDDIT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Google Maps
GOOGLE_MAPS_MAX_RESULTS = 20

# Glassdoor / Indeed
GLASSDOOR_MAX_RESULTS = 40

# SL Job Boards
TOPJOBS_MAX_RESULTS = 30

# LinkedIn
LINKEDIN_MAX_RESULTS = 10

# Facebook
FACEBOOK_MAX_RESULTS = 15

# SL News
NEWS_MAX_RESULTS = 20
SL_NEWS_SITES = [
    "dailymirror.lk",
    "sundaytimes.lk",
    "lankabusinessonline.com",
    "adaderana.lk",
    "colombogazette.com",
    "ft.lk",
    "island.lk",
    "newsfirst.lk",
    "economynext.com",
]

# General Web
WEB_MAX_RESULTS = 10


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CACHE SETTINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CACHE_TTL_HOURS = 48
CACHE_DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "cache.db")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SRI LANKA VALIDATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SL_KEYWORDS = [
    "sri lanka", "srilanka", "colombo", "kandy", "galle", "negombo",
    "jaffna", "matara", "kurunegala", "anuradhapura", "trincomalee",
    "batticaloa", "ratnapura", "badulla", "moratuwa", "dehiwala",
    "maharagama", "kotte", "nugegoda", "rajagiriya", "battaramulla",
    "lkr", "rs.", "rupees", "gampaha",
    # Sinhala
    "ශ්‍රී ලංකා", "කොළඹ", "ලංකා", "රු",
    # Tamil
    "இலங்கை", "கொழும்பு",
]

SL_DOMAIN_SUFFIX = ".lk"

SL_REGULATORY_BODIES = [
    "cbsl", "central bank of sri lanka",
    "sec", "securities and exchange commission",
    "consumer affairs authority", "caa",
    "board of investment", "boi",
    "inland revenue", "ird",
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DEDUPLICATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEDUP_MODEL = "all-MiniLM-L6-v2"
DEDUP_SIMILARITY_THRESHOLD = 0.85


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATA PATHS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DATA_DIR = str(Path(__file__).resolve().parent.parent / "data")
COMPANY_ALIASES_PATH = str(Path(DATA_DIR) / "company_aliases.json")
DEMO_COMPANIES_PATH = str(Path(DATA_DIR) / "demo_companies.json")
