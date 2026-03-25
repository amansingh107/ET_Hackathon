# LLM Integration

All AI inference runs locally via Ollama. No API keys. No cost. No data leaves your machine.

---

## Ollama Setup

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
# Windows: download installer from https://ollama.com/download

# 2. Pull models
ollama pull llama3.1:8b         # Primary model (~4.7 GB)
ollama pull mistral:7b           # Fallback if RAM < 16 GB (~4.1 GB)
ollama pull nomic-embed-text     # Embeddings (~274 MB)

# 3. Start Ollama server (runs on port 11434)
ollama serve

# 4. Verify
curl http://localhost:11434/api/tags
```

### Model Selection Guide

| RAM Available | Recommended Model | Notes |
|---|---|---|
| 8 GB | mistral:7b | Works, slightly less coherent on complex filings |
| 16 GB | llama3.1:8b | Recommended — best balance |
| 32 GB+ | llama3.1:70b | Excellent, slow on CPU |
| NVIDIA GPU 8GB+ | llama3.1:8b | 5-10x faster inference |

---

## Ollama Client

### File: `backend/app/llm/ollama_client.py`

```python
"""
Wrapper around Ollama HTTP API for all LLM tasks.
"""
import httpx
import json
import logging
from typing import Optional

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = httpx.Client(
            base_url=OLLAMA_BASE_URL,
            timeout=120.0  # LLM inference can take up to 2 min on CPU
        )

    def generate(self, prompt: str, system: str = "", temperature: float = 0.1) -> str:
        """
        Call Ollama generate API.
        temperature=0.1 for factual extraction tasks, 0.7 for explanations.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 1000,  # Max output tokens
            }
        }
        try:
            resp = self.client.post("/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json()["response"]
        except Exception as e:
            logger.error(f"Ollama generate failed: {e}")
            return ""

    def extract_signals(self, filing_text: str, filing_type: str, symbol: str) -> list[dict]:
        """
        Extract structured signals from filing text.
        Returns list of signal dicts with type, title, summary, confidence.
        """
        from app.llm.filing_prompts import FILING_SIGNAL_EXTRACTION_PROMPT

        prompt = FILING_SIGNAL_EXTRACTION_PROMPT.format(
            filing_type=filing_type,
            symbol=symbol,
            text=filing_text[:8000]  # Context window management
        )

        raw = self.generate(prompt, temperature=0.1)

        try:
            # Strip any markdown code fences
            cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
            signals = json.loads(cleaned)
            return signals if isinstance(signals, list) else []
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM JSON for {symbol} filing")
            return []

    def explain_pattern(self, pattern, stats) -> str:
        """
        Generate plain-English explanation for a detected chart pattern.
        """
        from app.llm.pattern_prompts import PATTERN_EXPLANATION_PROMPT

        prompt = PATTERN_EXPLANATION_PROMPT.format(
            symbol=pattern.symbol,
            pattern_name=pattern.pattern_name.replace("_", " ").title(),
            timeframe=pattern.timeframe,
            entry_price=pattern.entry_price,
            target_price=pattern.target_price or "Not calculated",
            stop_loss=pattern.stop_loss or "Not calculated",
            volume_confirmation="Yes" if pattern.volume_confirmation else "No",
            win_rate=stats.win_rate if stats else "Insufficient data",
            sample_size=stats.sample_size if stats else 0
        )

        return self.generate(prompt, temperature=0.6)

    def summarize_bulk_deal_context(self, symbol: str, deal_summary: str) -> str:
        """
        Generate context about why a bulk deal matters for this specific stock.
        """
        prompt = f"""
A bulk/block deal happened in {symbol} today:
{deal_summary}

In 2-3 sentences, explain what this deal likely signals to a retail investor.
Consider: institutional conviction, possible information advantage, market impact.
Be direct. No disclaimers.
"""
        return self.generate(prompt, temperature=0.5)

    def analyze_management_commentary(self, symbol: str, transcript: str) -> dict:
        """
        Analyze management commentary for tone shifts and forward guidance.
        Returns structured dict.
        """
        prompt = f"""
Analyze this earnings call excerpt from {symbol}:

{transcript[:3000]}

Return a JSON object with:
- "tone": "positive" | "neutral" | "negative"
- "guidance_direction": "upgrade" | "maintained" | "downgrade" | "none"
- "key_statements": [list of 3 most material statements, each under 100 chars]
- "risks_mentioned": [list of risks explicitly mentioned]
- "confidence": integer 1-10

Return only JSON, no other text.
"""
        raw = self.generate(prompt, temperature=0.1)
        try:
            return json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        except:
            return {"tone": "neutral", "guidance_direction": "none", "key_statements": [], "risks_mentioned": [], "confidence": 1}

    def embed(self, text: str) -> list[float]:
        """Get text embedding using nomic-embed-text for semantic search."""
        resp = self.client.post("/api/embeddings", json={
            "model": "nomic-embed-text",
            "prompt": text
        })
        return resp.json()["embedding"]
```

---

## FinBERT Integration

### File: `backend/app/llm/finbert_client.py`

```python
"""
FinBERT: pre-trained BERT model fine-tuned on financial texts.
Classifies sentiment as positive, negative, or neutral.
Model: ProsusAI/finbert (~440 MB, downloaded once on first use)
"""
from transformers import pipeline
import logging

logger = logging.getLogger(__name__)

# Singleton — load once, reuse
_pipeline = None

def get_finbert():
    global _pipeline
    if _pipeline is None:
        logger.info("Loading FinBERT model (first time may download ~440MB)...")
        _pipeline = pipeline(
            task="text-classification",
            model="ProsusAI/finbert",
            top_k=None,  # Return all labels with scores
            truncation=True,
            max_length=512
        )
    return _pipeline


def analyze_sentiment(text: str) -> dict:
    """
    Returns:
        {
            "label": "positive" | "negative" | "neutral",
            "score": 0.0–1.0,
            "all_scores": {"positive": 0.x, "negative": 0.x, "neutral": 0.x}
        }
    """
    finbert = get_finbert()
    results = finbert(text[:2000])  # BERT max 512 tokens (~2000 chars)

    all_scores = {r["label"]: round(r["score"], 4) for r in results[0]}
    dominant = max(results[0], key=lambda x: x["score"])

    return {
        "label": dominant["label"],
        "score": round(dominant["score"], 4),
        "all_scores": all_scores
    }


def batch_analyze_sentiment(texts: list[str]) -> list[dict]:
    """Process multiple texts efficiently in a single batch."""
    finbert = get_finbert()
    truncated = [t[:2000] for t in texts]
    batch_results = finbert(truncated)

    output = []
    for results in batch_results:
        all_scores = {r["label"]: round(r["score"], 4) for r in results}
        dominant = max(results, key=lambda x: x["score"])
        output.append({
            "label": dominant["label"],
            "score": round(dominant["score"], 4),
            "all_scores": all_scores
        })
    return output
```

---

## Context Window Management

NSE filings can be very long. Strategies to fit within Ollama's context:

```python
def prepare_filing_for_llm(text: str, max_chars: int = 8000) -> str:
    """
    Smart truncation: keep first 2000 chars (header/intro) +
    last 3000 chars (conclusion/guidance) +
    middle sample 3000 chars.
    """
    if len(text) <= max_chars:
        return text

    head = text[:2000]
    tail = text[-3000:]
    mid_start = len(text) // 2 - 1500
    middle = text[mid_start:mid_start + 3000]

    return f"{head}\n\n[...]\n\n{middle}\n\n[...]\n\n{tail}"
```

---

## LLM Task Queue

LLM inference is slow on CPU (~15–60 seconds per call). Route all LLM tasks through a dedicated Celery queue:

```python
# celery config
CELERY_TASK_ROUTES = {
    "app.workers.nlp_analyzer.*": {"queue": "llm"},       # Slow queue
    "app.workers.filing_crawler.*": {"queue": "fast"},    # Fast queue
    "app.workers.ohlcv_fetcher.*": {"queue": "fast"},
    "app.patterns.*": {"queue": "default"},
}

# Start separate worker for LLM queue with concurrency=1 (Ollama is single-threaded)
# celery -A app.celery worker -Q llm --concurrency=1
# celery -A app.celery worker -Q fast,default --concurrency=4
```

---

## Caching LLM Results

LLM explanations for patterns are expensive to regenerate. Cache in Redis:

```python
import hashlib
import json
import redis

r = redis.Redis(host="localhost", port=6379, db=1)

def get_pattern_explanation(pattern_key: str) -> str | None:
    """Check Redis cache before calling Ollama."""
    cached = r.get(f"pattern_explain:{pattern_key}")
    return cached.decode() if cached else None

def cache_pattern_explanation(pattern_key: str, explanation: str, ttl_hours: int = 24):
    r.setex(f"pattern_explain:{pattern_key}", ttl_hours * 3600, explanation)

# Usage
key = f"{symbol}:{pattern_name}:{timeframe}:{detected_date}"
explanation = get_pattern_explanation(key)
if not explanation:
    explanation = ollama.explain_pattern(pattern, stats)
    cache_pattern_explanation(key, explanation)
```
