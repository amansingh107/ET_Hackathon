# Signal Scoring Engine

All signals are scored 0–100. Scores below 40 are discarded. Scores above 70 trigger alerts.

---

## Scoring Philosophy

- A score represents **conviction**, not just presence of an event
- Multiple weak signals on the same stock on the same day compound each other
- Signals are directional: buys and sells are both signals (different types)
- Historical context matters: a stock near 52W high getting insider buys scores higher

---

## Score Ranges

| Score | Meaning | Action |
|---|---|---|
| 0–39 | Noise | Discarded, not stored |
| 40–59 | Noteworthy | Stored, shown in feed, no alert |
| 60–74 | Strong signal | Stored, shown prominently, optional alert |
| 75–89 | Very strong signal | Alert sent immediately |
| 90–100 | Exceptional signal | High-priority alert, digest headline |

---

## Signal Type Scorers

### 1. Bulk/Block Deal Scorer

```
base_score = f(volume_ratio)
    volume_ratio >= 5.0x  →  50 pts
    volume_ratio 2.0–5.0x →  35 pts
    volume_ratio 1.0–2.0x →  20 pts
    volume_ratio < 1.0x   →   5 pts

direction_bonus
    BUY  → +20 pts
    SELL → +10 pts

institution_bonus
    Known institution identified → +15 pts

deal_type_bonus
    BLOCK deal → +10 pts
    BULK deal  →  +0 pts

max_score = 100
```

**Example**: HDFC MF buys ₹500Cr of a stock at 7x avg daily volume = 50 + 20 + 15 + 10 = **95**

---

### 2. Insider Trade Scorer

```
Single insider buy:
    Promoter buy         → base 65
    Director/KMP buy     → base 50
    Relative/associate   → base 35

Cluster multiplier (buys in 7-day window):
    2 insiders → base × 1.3
    3 insiders → base × 1.5
    4+ insiders → base × 1.7 (cap 100)

Value bonus:
    > ₹10 Cr  → +15 pts
    > ₹50 Cr  → +25 pts
    > ₹100 Cr → +35 pts

Stake change bonus:
    Promoter stake increased > 1% → +10 pts
    Promoter stake increased > 2% → +20 pts
```

---

### 3. Quarterly Results Scorer

```
Revenue beat:
    Beat by > 10% → +30 pts
    Beat by 5–10% → +20 pts
    Beat by 1–5%  → +10 pts
    Miss by 1–5%  → -10 pts (creates RESULTS_MISS signal)
    Miss by > 10% → -25 pts

PAT beat:
    Same scale as Revenue, weight × 1.3

PAT growth YoY:
    > 50% YoY growth → +20 pts
    20–50% YoY       → +10 pts
    0–20% YoY        →  +5 pts
    Negative          → -15 pts

Guidance:
    Explicit upgrade → +25 pts
    Vague positivity → +10 pts
    No guidance      →  +0 pts

Management sentiment (FinBERT):
    Strong positive  → +15 pts
    Mild positive    →  +5 pts
    Negative         → -10 pts
```

---

### 4. Filing Anomaly Scorer

Triggered when Ollama extracts a non-routine event from a filing.

```
Signal type weights:
    ORDER_WIN                → base 70
    CAPACITY_EXPANSION       → base 65
    ACQUISITION              → base 75
    MANAGEMENT_TONE_POSITIVE → base 50
    MANAGEMENT_TONE_NEGATIVE → base 55
    REGULATORY_ACTION        → base 80
    EXCEPTIONAL_ITEM         → base 60
    DEBT_REDUCTION           → base 55
    CREDIT_RATING_UPGRADE    → base 65
    CREDIT_RATING_DOWNGRADE  → base 70

Ollama confidence adjustment:
    confidence 8–10 → score × 1.0
    confidence 5–7  → score × 0.85
    confidence 1–4  → score × 0.65
```

---

## Signal Compounding

When multiple signals hit the same stock within 48 hours, compound them:

```python
def compound_signals(signals: list[Signal]) -> int:
    """
    Compound multiple signals on same stock.
    Each additional signal adds diminishing value.
    """
    if not signals:
        return 0

    scores = sorted([s.score for s in signals], reverse=True)
    compound = scores[0]

    for s in scores[1:]:
        # Each additional signal adds 30% of its remaining room to max
        remaining = 100 - compound
        compound += int(0.30 * remaining * (s / 100))

    return min(compound, 100)
```

**Example**:
- Bulk deal signal: 75
- Insider buy same week: 65
- Results beat announced same day: 70

Compounded: 75 → 75 + 0.3×25×0.65 = 80 → 80 + 0.3×20×0.70 = **84**

---

## Daily Signal Digest

At 8 PM IST each day, compile:

```python
def build_daily_digest():
    """
    Top 10 signals of the day, grouped by sector.
    Format for email/push notification.
    """
    today_signals = get_today_signals(min_score=60)
    top_10 = sorted(today_signals, key=lambda s: s.score, reverse=True)[:10]

    digest = {
        "date": date.today().isoformat(),
        "top_signals": top_10,
        "total_signals_today": len(today_signals),
        "sectors_with_activity": group_by_sector(today_signals),
    }
    return digest
```

---

## Anti-Noise Filters

Apply before scoring to avoid garbage signals:

1. **Circuit filter**: Stock hit upper/lower circuit today → skip (price discovery incomplete)
2. **Illiquidity filter**: Avg daily volume < 10,000 → skip (manipulation risk)
3. **Penny stock filter**: Price < ₹10 → skip
4. **Suspended filter**: Stock is suspended → skip
5. **Duplicate filter**: Same signal type for same stock in last 24 hours → skip
