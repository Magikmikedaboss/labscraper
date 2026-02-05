# Pattern Scoring v1 - Foundation Document

## STEP 3: Pattern Scoring (Turning Patterns + Signals into Usable Insight)

**Date:** 2025-01-22  
**Status:** Conceptual Foundation (No Implementation Yet)  
**Purpose:** Compute Pattern Health Score reflecting research momentum, not truth

---

## What This Step Does (Precisely)

**We are NOT scoring:**
- Truth
- Effectiveness
- Safety
- Biological validity

**We ARE computing:**
- A **Pattern Health Score** (0-100)
- Reflecting how research effort behaves around a topic over time
- Enabling responsible talk about promising directions, blocked areas, exploratory zones, deprioritized topics

**Across any domain.**

---

## Inputs to Pattern Scoring (Already Built)

Pattern Scoring uses only things you already have:

1. ✅ **Pattern Type** (Step 1)
   - Convergence, Escalation, Stagnation, Abandonment, Fragmentation

2. ✅ **Outcome Signals** (Step 2)
   - Positive, Neutral, Negative, Replication

3. ✅ **Time / Frequency** (already in your data)
   - Event counts over time
   - Trajectory (increasing/stable/decreasing)

4. ✅ **Confidence** (already present)
   - High, Med, Low confidence per event

**No new scraping. No ML.**

---

## The Pattern Health Score (v1)

**A single score from 0–100 that represents research momentum, not success.**

### Why a single score?

✅ Makes dashboards usable  
✅ Allows comparisons  
✅ Lets users sort/filter  
✅ Stays abstract enough to avoid overclaiming  

---

## Scoring Components (Transparent & Additive)

### 1️⃣ Pattern Type Base Score

Each pattern starts with a baseline reflecting research behavior, not quality.

| Pattern Type | Base Score | Rationale |
|--------------|-----------|-----------|
| **Convergence** | +40 | High effort clustering |
| **Escalation** | +45 | Increasing validation |
| **Fragmentation** | +20 | Early exploration |
| **Stagnation** | +10 | Persistent challenges |
| **Abandonment** | 0 | Declining attention |

**This reflects research behavior, not quality.**

---

### 2️⃣ Outcome Signal Adjustment

Outcome language nudges the score.

| Signal Type | Adjustment | Rationale |
|-------------|-----------|-----------|
| **Positive** | +5 per signal | Reported progress |
| **Negative** | -5 per signal | Reported challenges |
| **Replication** | +3 per signal | Validation effort |
| **Neutral** | +1 per signal (capped at 5) | Exploratory activity |

**Neutral signals are capped** so exploratory work doesn't inflate scores.

---

### 3️⃣ Time Momentum Adjustment

Based on change since last run (or over time window).

| Trajectory | Adjustment | Rationale |
|-----------|-----------|-----------|
| **Increasing frequency** | +10 | Growing attention |
| **Stable frequency** | +5 | Sustained effort |
| **Decreasing frequency** | -10 | Declining interest |

**Momentum matters more than raw count.**

---

### 4️⃣ Confidence Modifier

We scale the score slightly based on event confidence.

| Confidence Level | Multiplier | Rationale |
|-----------------|-----------|-----------|
| **High** | ×1.1 | Strong signal quality |
| **Medium** | ×1.0 | Standard quality |
| **Low** | ×0.9 | Weak signal quality |

**This avoids garbage inflation.**

---

## Final Score Calculation (Pseudocode)

```python
def calculate_pattern_health_score(
    pattern_type: str,
    outcome_signals: dict,
    time_momentum: str,
    confidence_level: str
) -> int:
    """
    Calculate Pattern Health Score (0-100).
    Represents research momentum, not effectiveness.
    """
    
    # 1. Pattern Type Base Score
    pattern_base = {
        "convergence": 40,
        "escalation": 45,
        "fragmentation": 20,
        "stagnation": 10,
        "abandonment": 0
    }
    score = pattern_base.get(pattern_type, 0)
    
    # 2. Outcome Signal Adjustment
    score += (outcome_signals.get("positive", 0) * 5)
    score -= (outcome_signals.get("negative", 0) * 5)
    score += (outcome_signals.get("replication", 0) * 3)
    score += min(outcome_signals.get("neutral", 0), 5) * 1  # capped
    
    # 3. Time Momentum Adjustment
    momentum_bonus = {
        "increasing": 10,
        "stable": 5,
        "decreasing": -10
    }
    score += momentum_bonus.get(time_momentum, 0)
    
    # 4. Confidence Modifier
    confidence_multiplier = {
        "high": 1.1,
        "med": 1.0,
        "low": 0.9
    }
    score = score * confidence_multiplier.get(confidence_level, 1.0)
    
    # 5. Clamp to 0-100
    score = max(0, min(int(score), 100))
    
    return score
```

**That's it. Simple. Explainable. Defensible.**

---

## What the Score Means (Critical)

### Score Interpretation Ranges

| Score Range | Interpretation | Allowed Language |
|-------------|---------------|------------------|
| **80–100** | Strong research momentum | "Shows strong research momentum" |
| **60–79** | Promising / active | "Appears promising and active" |
| **40–59** | Exploratory | "Remains exploratory" |
| **20–39** | Stalled / uncertain | "Appears stalled or uncertain" |
| **0–19** | Deprioritized | "Shows declining attention" |

### You NEVER say:

❌ "effective"  
❌ "works"  
❌ "fails"  
❌ "proven"  
❌ "safe"  

### You ALWAYS say:

✅ "shows strong momentum"  
✅ "appears stalled"  
✅ "remains exploratory"  
✅ "exhibits declining attention"  
✅ "demonstrates increasing validation effort"  

---

## Example Calculation (Realistic)

### Topic: Peptide stability in plasma

**Inputs:**
- **Pattern:** Stagnation (+10)
- **Outcome signals:** 
  - Negative: 3 (-15)
  - Neutral: 1 (+1)
- **Time:** Stable (+5)
- **Confidence:** Medium (×1.0)

**Calculation:**
```
score = 10           # Stagnation base
score += 0           # No positive signals
score -= 15          # 3 negative signals × 5
score += 1           # 1 neutral signal × 1
score += 5           # Stable momentum
score = 1 × 1.0      # Medium confidence
score = 1            # Final score
```

**Score:** 1 (Deprioritized range: 0-19)

**Honest Interpretation:**  
"This area shows repeated technical barriers with limited momentum."

**NOT allowed to say:**  
"This approach doesn't work" or "This should be abandoned"

---

## Why This Is Powerful (And Rare)

### Most tools:
❌ Summarize papers  
❌ Rank popularity  
❌ Hallucinate conclusions  

### Your tool:
✅ Scores behavior  
✅ Tracks effort  
✅ Exposes friction  
✅ Respects uncertainty  

**Researchers understand this language immediately.**

---

## How This Answers Your Original Goal

**Original question:**  
"What research patterns work or don't work in biohacking?"

**Your honest answer:**  
"Patterns showing convergence, escalation, and replication signals exhibit stronger research momentum, while stagnation and abandonment patterns indicate persistent barriers or declining interest."

**That is a real answer, not hype.**

---

## Example Patterns with Scores

### Example 1: SEMAGLUTIDE (Compound)

**Pattern Analysis:**
- **Pattern Type:** Convergence (appears in 10 events, consistent methods)
- **Outcome Signals:** 
  - Positive: 6 ("effective", "improved", "robust")
  - Negative: 1 ("limited stability")
  - Neutral: 8 ("investigated", "evaluated")
  - Replication: 2 ("validated", "confirmed")
- **Time Momentum:** Increasing (growing from 2 → 10 events)
- **Confidence:** High (most events high confidence)

**Score Calculation:**
```
score = 40           # Convergence base
score += 30          # 6 positive × 5
score -= 5           # 1 negative × 5
score += 5           # 5 neutral × 1 (capped)
score += 6           # 2 replication × 3
score += 10          # Increasing momentum
score = 86 × 1.1     # High confidence
score = 95           # Final score
```

**Score:** 95 (Strong research momentum)

**Honest Interpretation:**  
"SEMAGLUTIDE shows strong research momentum with convergence around consistent methods, predominantly positive outcome language, and increasing validation efforts."

---

### Example 2: AGGREGATION (Pathway/Challenge)

**Pattern Analysis:**
- **Pattern Type:** Stagnation (appears in 24 events, same problem recurring)
- **Outcome Signals:**
  - Positive: 1 ("reduced aggregation")
  - Negative: 18 ("aggregated", "unstable", "poor stability")
  - Neutral: 12 ("characterized", "observed")
  - Replication: 0
- **Time Momentum:** Stable (consistent problem across time)
- **Confidence:** Medium

**Score Calculation:**
```
score = 10           # Stagnation base
score += 5           # 1 positive × 5
score -= 90          # 18 negative × 5
score += 5           # 5 neutral × 1 (capped)
score += 0           # 0 replication
score += 5           # Stable momentum
score = -65 × 1.0    # Medium confidence
score = 0            # Clamped to 0
```

**Score:** 0 (Deprioritized)

**Honest Interpretation:**  
"Aggregation appears as a persistent technical barrier with predominantly negative outcome language and limited reported progress."

---

### Example 3: LC-MS (Assay)

**Pattern Analysis:**
- **Pattern Type:** Convergence (appears in 85 events, dominant method)
- **Outcome Signals:**
  - Positive: 12 ("robust", "sensitive", "accurate")
  - Negative: 2 ("limited sensitivity")
  - Neutral: 45 ("analyzed", "measured", "quantified")
  - Replication: 8 ("validated", "consistent with")
- **Time Momentum:** Stable (established method)
- **Confidence:** High

**Score Calculation:**
```
score = 40           # Convergence base
score += 60          # 12 positive × 5
score -= 10          # 2 negative × 5
score += 5           # 5 neutral × 1 (capped)
score += 24          # 8 replication × 3
score += 5           # Stable momentum
score = 124 × 1.1    # High confidence
score = 100          # Clamped to 100
```

**Score:** 100 (Strong research momentum)

**Honest Interpretation:**  
"LC-MS shows strong research momentum as a dominant analytical method with extensive validation and predominantly positive outcome language."

---

## What We Do NOT Do Yet

❌ No domain overlays  
❌ No UI polishing  
❌ No automation  
❌ No claims about effectiveness  
❌ No implementation yet  

**We freeze this logic first.**

---

## Assessment: Do These Feel Right?

### Pattern Base Scores

| Pattern | Score | Assessment |
|---------|-------|------------|
| Escalation | 45 | ✅ Highest (increasing validation) |
| Convergence | 40 | ✅ High (focused effort) |
| Fragmentation | 20 | ✅ Low-mid (early exploration) |
| Stagnation | 10 | ✅ Low (persistent barriers) |
| Abandonment | 0 | ✅ Lowest (declining attention) |

**My assessment:** These feel right. Escalation slightly higher than Convergence makes sense (validation > clustering).

### Signal Weights

| Signal | Weight | Assessment |
|--------|--------|------------|
| Positive | +5 | ✅ Balanced |
| Negative | -5 | ✅ Symmetric with positive |
| Replication | +3 | ✅ Lower than positive (validation ≠ success) |
| Neutral | +1 (capped) | ✅ Prevents exploratory inflation |

**My assessment:** These feel balanced and honest.

### Momentum Adjustments

| Momentum | Adjustment | Assessment |
|----------|-----------|------------|
| Increasing | +10 | ✅ Significant boost |
| Stable | +5 | ✅ Modest boost |
| Decreasing | -10 | ✅ Significant penalty |

**My assessment:** Momentum matters. These weights feel appropriate.

### Confidence Multipliers

| Confidence | Multiplier | Assessment |
|-----------|-----------|------------|
| High | ×1.1 | ✅ Modest boost (10%) |
| Medium | ×1.0 | ✅ Baseline |
| Low | ×0.9 | ✅ Modest penalty (10%) |

**My assessment:** Conservative multipliers prevent garbage inflation. Good.

---

## Potential Tweaks to Consider

### Option 1: Adjust Escalation Base Score
- Current: 45
- Alternative: 50 (to emphasize validation more)
- **Recommendation:** Keep at 45. It's already highest.

### Option 2: Increase Replication Weight
- Current: +3
- Alternative: +5 (equal to positive)
- **Recommendation:** Keep at +3. Replication ≠ success, just validation.

### Option 3: Cap Negative Signals
- Current: No cap
- Alternative: Cap at -25 (prevent extreme penalties)
- **Recommendation:** Consider capping. Prevents single-issue domination.

### Option 4: Add Diversity Bonus
- Current: Not present
- Alternative: +5 if multiple entity types present
- **Recommendation:** Not needed yet. Keep simple.

---

## My Recommendation

**These scoring components feel solid:**

✅ Pattern base scores reflect behavior honestly  
✅ Signal weights are balanced and symmetric  
✅ Momentum adjustments emphasize trajectory  
✅ Confidence multipliers are conservative  
✅ Language interpretations are defensible  

**Potential refinement:**
- Consider capping negative signals at -25 to prevent extreme penalties
- Otherwise, proceed with current weights

---

## Next Steps (When Ready)

**STEP 4 (Later):**
- Implement pattern detection logic
- Add outcome signal detection to scraper
- Calculate scores for existing data
- Generate pattern health reports

**But we only do that once Step 3 feels solid.**

---

## STOP POINT

Before moving on, confirm these feel right:

1. ✅ Pattern base scores (Escalation 45, Convergence 40, etc.)
2. ✅ Signal weights (+5/-5 for positive/negative, +3 for replication)
3. ✅ Language used in interpretations ("momentum" not "effectiveness")
4. ✅ Score ranges and their meanings (80-100 = strong momentum, etc.)

**If you want to tweak numbers, now is the time.**

---

## Status

✅ **STEP 1 COMPLETE:** Research Pattern Types (5 types)  
✅ **STEP 2 COMPLETE:** Outcome Signal Detection (4 classes)  
✅ **STEP 3 COMPLETE:** Pattern Scoring (0-100 health score)  
⏸️ **STEP 4 PENDING:** Implementation (awaiting approval)  
❌ **No code yet:** Conceptual foundation only  

**Foundation documents:**
1. `RESEARCH_PATTERNS_FOUNDATION.md` - Step 1
2. `OUTCOME_SIGNALS_FOUNDATION.md` - Step 2
3. `PATTERN_SCORING_FOUNDATION.md` - Step 3

---

## Ready to Implement?

**Say "ready to implement"** when you want to build this into the scraper.

Or suggest tweaks to the scoring weights if anything feels off.

**We're doing the hard, boring, correct part — and that's why this has legs.** 🎯
