"""
Sri Lanka validation utilities.
Ensures all data is properly scoped to Sri Lanka.
"""

import re
from urllib.parse import urlparse
from typing import Optional
import json
import os


# Sri Lanka identification keywords
SL_KEYWORDS = [
    "sri lanka", "srilanka", "colombo", "kandy", "galle", "negombo",
    "jaffna", "matara", "kurunegala", "anuradhapura", "trincomalee",
    "batticaloa", "ratnapura", "badulla", "moratuwa", "dehiwala",
    "maharagama", "kotte", "nugegoda", "rajagiriya", "battaramulla",
    "lkr", "rs.", "rupees", "Gampaha"
    # Sinhala
    "ශ්‍රී ලංකා", "කොළඹ", "ලංකා", "රු",
    # Tamil
    "இலங்கை", "கொழும்பு",
]

SL_DOMAIN_SUFFIX = ".lk"

# Sri Lankan regulatory bodies
SL_REGULATORY_BODIES = [
    "cbsl", "central bank of sri lanka",
    "sec", "securities and exchange commission",
    "consumer affairs authority", "caa",
    "board of investment", "boi",
    "inland revenue", "ird",
]

# Load company aliases
_ALIASES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "company_aliases.json"
)


def _load_aliases() -> dict:
    """Load company alias mappings."""
    try:
        with open(_ALIASES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


COMPANY_ALIASES = _load_aliases()


def is_sri_lankan_result(text: str, url: str = "") -> bool:
    """
    Validate whether a result is related to Sri Lanka.

    Args:
        text: The text content of the result.
        url: The source URL.

    Returns:
        True if the result is confirmed as Sri Lanka-related.
    """
    # Check URL domain
    if url:
        try:
            domain = urlparse(url).netloc.lower()
            if domain.endswith(SL_DOMAIN_SUFFIX):
                return True
        except Exception:
            pass

    # Check text for SL keywords
    text_lower = text.lower()
    for keyword in SL_KEYWORDS:
        if keyword in text_lower:
            return True

    return False


def normalize_company_name(name: str) -> str:
    """
    Normalize a company name: strip whitespace, title-case,
    and resolve known aliases.

    Args:
        name: Raw company name input.

    Returns:
        Normalized company name.
    """
    name = name.strip()
    name = re.sub(r"\s+", " ", name)

    # Check aliases (case-insensitive)
    for alias, full_name in COMPANY_ALIASES.items():
        if name.lower() == alias.lower():
            return full_name

    return name.title()


def mentions_company(text: str, company: str) -> bool:
    """Check if text mentions the company or its known aliases to prevent irrelevant fallback results."""
    text_lower = text.lower()
    if company.lower() in text_lower:
        return True
        
    # Check aliases
    for alias, full_name in COMPANY_ALIASES.items():
        if full_name.lower() == company.lower() and alias.lower() in text_lower:
            return True
            
    return False


def enrich_query(company: str, platform: str = "general") -> str:
    """
    Append Sri Lanka geo-restriction strings to a query
    based on the target platform.

    Args:
        company: The normalized company name.
        platform: Target platform identifier.

    Returns:
        Enriched search query string.
    """
    platform = platform.lower()

    if platform == "reddit":
        return f"{company} Sri Lanka"

    elif platform == "google_maps":
        return f"{company} Sri Lanka"

    elif platform in ("glassdoor", "indeed"):
        return f"{company}"  # Glassdoor uses country filter param

    elif platform in ("topjobs", "ikman", "jobsnet"):
        return company  # SL-native sites, no geo needed

    elif platform == "linkedin":
        return f"{company}"  # LinkedIn uses location filter

    elif platform == "facebook":
        return f"{company} Sri Lanka"

    elif platform == "news":
        return f'"{company}" site:.lk'

    elif platform == "web":
        return f'"{company}" "Sri Lanka" review OR complaint OR feedback'

    else:
        return f'{company} site:.lk OR "Sri Lanka" OR "Colombo"'


def detect_regulatory_mention(text: str) -> list[str]:
    """
    Detect mentions of Sri Lankan regulatory bodies in text.

    Args:
        text: Text to scan.

    Returns:
        List of detected regulatory body references.
    """
    text_lower = text.lower()
    found = []
    for body in SL_REGULATORY_BODIES:
        if body in text_lower:
            found.append(body.upper() if len(body) <= 4 else body.title())
    return found


def detect_crisis_signals(text: str) -> list[str]:
    """
    Detect crisis signals in text content.

    Args:
        text: Text to scan for crisis indicators.

    Returns:
        List of detected crisis signal descriptions.
    """
    text_lower = text.lower()
    signals = []

    crisis_patterns = {
        "Mass layoffs or retrenchment": [
            "layoff", "lay off", "retrenchment", "mass firing",
            "downsizing", "workforce reduction", "let go",
        ],
        "Legal case or court proceeding": [
            "court case", "lawsuit", "legal action", "sued",
            "tribunal", "litigation", "court order",
        ],
        "Financial distress": [
            "unpaid salaries", "salary delay", "salary not paid",
            "financial trouble", "bankruptcy", "liquidation",
            "debt default", "insolvent",
        ],
        "Product safety complaints": [
            "product recall", "safety hazard", "dangerous product",
            "health risk", "contamination",
        ],
        "Regulatory action": [
            "cbsl action", "sec investigation", "regulatory penalty",
            "fined by", "license revoked", "compliance violation",
        ],
    }

    for signal_type, patterns in crisis_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                signals.append(signal_type)
                break

    # Also check regulatory mentions
    reg_mentions = detect_regulatory_mention(text)
    if reg_mentions:
        signals.append(f"Regulatory body mentioned: {', '.join(reg_mentions)}")

    return list(set(signals))
