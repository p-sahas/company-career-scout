"""
Multi-provider LLM router using LangChain.
Supports Groq, Google Gemini, Anthropic Claude, and OpenAI.
All model/provider config imported from config.settings.
"""

import time
from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

# Import from centralized config
try:
    from config.settings import (
        DEFAULT_MODELS,
        PROVIDER_CLASSES as _PROVIDER_CLASSES,
        FREE_TIER_PROVIDERS,
        DEFAULT_TEMPERATURE,
    )
except ImportError:
    # Fallback if config not available
    DEFAULT_MODELS = {
        "groq": "llama-3.3-70b-versatile",
        "google": "gemini-2.5-flash",
        "anthropic": "claude-haiku-4-5-20250315",
        "openai": "gpt-4o-mini",
    }
    _PROVIDER_CLASSES = {
        "groq": ("langchain_groq", "ChatGroq"),
        "google": ("langchain_google_genai", "ChatGoogleGenerativeAI"),
        "anthropic": ("langchain_anthropic", "ChatAnthropic"),
        "openai": ("langchain_openai", "ChatOpenAI"),
    }
    FREE_TIER_PROVIDERS = {"groq", "google"}
    DEFAULT_TEMPERATURE = 0.1


# Classification prompt template
CLASSIFY_SYSTEM_PROMPT = """You are an expert analyst classifying company reviews and mentions from Sri Lanka.
For the given text, extract the following as a JSON object. Return ONLY valid JSON, no markdown fences:
{
  "sentiment": "positive" | "negative" | "neutral",
  "confidence": 0.0-1.0,
  "reviewer_type": "employee" | "customer" | "job_seeker" | "press" | "general",
  "themes": [list from: "salary_benefits", "work_life_balance", "management_culture",
             "product_quality", "customer_service", "pricing", "delivery",
             "job_security", "office_environment", "career_growth",
             "ethical_practices", "layoffs_restructuring"],
  "severity": "low" | "medium" | "high" | "critical",
  "language_detected": "en" | "si" | "ta" | "mixed"
}"""

SUMMARIZE_SYSTEM_PROMPT = """You are an expert analyst creating a comprehensive reputation summary for a Sri Lankan company.
Based on the provided classified reviews and data, generate a detailed summary.
Return a JSON object with these fields. Return ONLY valid JSON, no markdown fences:
{
  "what_employees_say": "summary string",
  "what_customers_say": "summary string",
  "what_press_says": "summary string",
  "top_5_pros": ["pro1", "pro2", "pro3", "pro4", "pro5"],
  "top_5_cons": ["con1", "con2", "con3", "con4", "con5"],
  "crisis_flags": ["flag1"] or [],
  "recommendation": "overall recommendation string",
  "overall_score": 0-100
}"""


class ModelRouter:
    """
    Unified LLM router that abstracts across multiple providers.
    Uses LangChain's unified .invoke() interface.
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        model_name: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model_name = model_name or DEFAULT_MODELS.get(self.provider, "")
        self.temperature = temperature
        self.total_tokens_used = 0
        self.total_calls = 0
        self._llm: Optional[BaseChatModel] = None

        if self.provider not in _PROVIDER_CLASSES:
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Supported: {list(_PROVIDER_CLASSES.keys())}"
            )

    def _get_llm(self) -> BaseChatModel:
        """Lazy-initialize the LLM instance."""
        if self._llm is None:
            module_name, class_name = _PROVIDER_CLASSES[self.provider]
            module = __import__(module_name, fromlist=[class_name])
            llm_class = getattr(module, class_name)

            kwargs = {
                "model": self.model_name,
                "temperature": self.temperature,
            }

            if self.provider == "groq":
                kwargs["groq_api_key"] = self.api_key
            elif self.provider == "google":
                kwargs["google_api_key"] = self.api_key
            elif self.provider == "anthropic":
                kwargs["anthropic_api_key"] = self.api_key
            elif self.provider == "openai":
                kwargs["openai_api_key"] = self.api_key

            self._llm = llm_class(**kwargs)

        return self._llm

    def _invoke(self, system_prompt: str, user_prompt: str) -> str:
        llm = self._get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        start_time = time.time()
        response = llm.invoke(messages)
        elapsed = time.time() - start_time

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
            tokens = getattr(usage, "total_tokens", 0) or 0
            self.total_tokens_used += tokens

        self.total_calls += 1
        return response.content

    def classify(self, text: str) -> dict:
        import json

        user_prompt = f"Classify this text:\n\n{text[:2000]}"

        try:
            result = self._invoke(CLASSIFY_SYSTEM_PROMPT, user_prompt)
            result = result.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[1] if "\n" in result else result
                if result.endswith("```"):
                    result = result[:-3]
                result = result.strip()

            return json.loads(result)
        except (json.JSONDecodeError, Exception) as e:
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "reviewer_type": "general",
                "themes": [],
                "severity": "low",
                "language_detected": "en",
                "error": str(e),
            }

    def summarize(self, reviews_data: list) -> dict:
        import json

        condensed = []
        for i, review in enumerate(reviews_data[:100]):
            condensed.append(
                f"[{i+1}] Source: {review.get('source_platform', 'unknown')} | "
                f"Sentiment: {review.get('sentiment', 'unknown')} | "
                f"Type: {review.get('reviewer_type', 'unknown')} | "
                f"Themes: {', '.join(review.get('themes', []))} | "
                f"Text: {review.get('raw_text', '')[:200]}"
            )

        user_prompt = (
            f"Summarize these {len(condensed)} classified reviews:\n\n"
            + "\n".join(condensed)
        )

        try:
            result = self._invoke(SUMMARIZE_SYSTEM_PROMPT, user_prompt)
            result = result.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[1] if "\n" in result else result
                if result.endswith("```"):
                    result = result[:-3]
                result = result.strip()

            return json.loads(result)
        except (json.JSONDecodeError, Exception) as e:
            return {
                "what_employees_say": "Analysis could not be completed.",
                "what_customers_say": "Analysis could not be completed.",
                "what_press_says": "Analysis could not be completed.",
                "top_5_pros": [],
                "top_5_cons": [],
                "crisis_flags": [],
                "recommendation": "Insufficient data for recommendation.",
                "overall_score": 50,
                "error": str(e),
            }

    def supports_free_tier(self) -> bool:
        return self.provider in FREE_TIER_PROVIDERS

    def get_usage_stats(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model_name,
            "total_tokens": self.total_tokens_used,
            "total_calls": self.total_calls,
            "is_free_tier": self.supports_free_tier(),
        }

    def get_display_name(self) -> str:
        provider_names = {
            "groq": "Groq",
            "google": "Google Gemini",
            "anthropic": "Anthropic Claude",
            "openai": "OpenAI",
        }
        provider_display = provider_names.get(self.provider, self.provider)
        return f"{provider_display} — {self.model_name}"
