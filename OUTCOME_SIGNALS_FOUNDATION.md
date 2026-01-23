# Outcome Signal Detection - Foundation Document

## STEP 2: Outcome Signal Detection (v1)

**Date:** 2025-01-22  
**Status:** Conceptual Foundation + Seed File Created  
**Purpose:** Detect how researchers describe outcomes (not biological truth)

---

## What Is an Outcome Signal?

**An outcome signal is NOT:**
- A claim about biological truth
- A determination of efficacy
- A conclusion about what works
- A recommendation

**An outcome signal IS:**
- How authors describe their results
- Language patterns in scientific writing
- A directional indicator of reported progress/struggle
- Descriptive, not interpretive

**Key Insight:** We track language patterns, not biological facts.

---

## The 4 Outcome Signal Classes (Final)

These are intentionally simple and conservative.

---

### 🟢 POSITIVE Signal

**What it means:**  
Language indicating reported improvement or success.

**Examples:**
- "significant improvement"
- "significantly improved"
- "robust effect"
- "effective"
- "enhanced"
- "outperformed"
- "increased significantly"
- "demonstrated efficacy"
- "strong response"
- "beneficial effect"

**What we are allowed to say:**  
"Authors used positive outcome language in X% of events."

**What we are NOT saying:**
- That the approach works
- That it is effective
- That it should be used

---

### 🟡 NEUTRAL Signal

**What it means:**  
Exploratory, descriptive, or setup-focused language.

**Examples:**
- "investigated"
- "examined"
- "evaluated"
- "characterized"
- "assessed"
- "analyzed"
- "measured"
- "explored"
- "observed"

**What we are allowed to say:**  
"Research remains exploratory and descriptive."

**What we are NOT saying:**
- That no progress is being made
- That the field is confused
- That results are inconclusive

---

### 🔴 NEGATIVE Signal

**What it means:**  
Language indicating limitations, lack of effect, or failure.

**Examples:**
- "no significant effect"
- "did not improve"
- "failed to"
- "limited effect"
- "inconsistent results"
- "no difference"
- "poor stability"
- "low efficacy"
- "unable to"

**What we are allowed to say:**  
"Negative outcome language appears frequently in studies involving X."

**What we are NOT saying:**
- That the approach doesn't work
- That it should be abandoned
- That it is a dead end

**Why this matters:**  
This is how you responsibly describe friction without claiming failure.

---

### 🔁 REPLICATION Signal

**What it means:**  
Language indicating validation, confirmation, or follow-up.

**Examples:**
- "replicated"
- "reproduced"
- "validated"
- "confirmed"
- "consistent with previous studies"
- "in agreement with"
- "corroborated"

**What we are allowed to say:**  
"Replication language is present/absent in this research area."

**What we are NOT saying:**
- That the results are proven
- That the approach is validated
- That it is ready for clinical use

---

## Why This Step Is Powerful But Safe

### What this enables:

✅ "Negative outcome language appears frequently in studies involving X"  
✅ "Positive signals cluster around Y approach"  
✅ "Replication language is scarce in this area"  
✅ "Research shows mostly exploratory (neutral) language"

### What this does NOT claim:

❌ That X doesn't work  
❌ That Y is the best approach  
❌ That lack of replication means failure  
❌ That exploratory research is bad

**Researchers respect this distinction.**

---

## How This Connects to Pattern Types (Step 1)

Later, you'll combine:
- **Pattern Type** (Step 1: Convergence, Escalation, Stagnation, Abandonment, Fragmentation)
- **Outcome Signals** (Step 2: Positive, Neutral, Negative, Replication)

### Example Combinations:

| Pattern Type | Outcome Signals | Interpretation |
|--------------|----------------|----------------|
| **Convergence** | Mostly Positive | → Promising (high effort + positive language) |
| **Convergence** | Mixed | → Actively contested |
| **Stagnation** | Mostly Negative | → Persistent barrier |
| **Fragmentation** | Mostly Neutral | → Exploratory phase |
| **Escalation** | Replication present | → Validation phase |
| **Abandonment** | Mostly Negative | → Deprioritized after challenges |

**This is how you responsibly approach "what works vs what doesn't" without lying.**

---

## Seed File Created

**File:** `seeds/outcome_signals.json`

```json
{
  "version": "v1",
  "positive": [20 phrases],
  "neutral": [18 phrases],
  "negative": [20 phrases],
  "replication": [13 phrases]
}
```

**These terms are:**
- Conservative
- Common in scientific writing
- Low-risk for overclaiming
- Tunable later

---

## Where This Plugs Into Your Pipeline

### Detection happens AFTER:
1. ✅ Text extraction
2. ✅ Entity extraction
3. ✅ Normalization

### Detection looks at:
- Abstract
- Results section
- Discussion section
- Conclusion

**NOT methods section** (methods are neutral by definition)

---

## Implementation Logic (Pseudocode)

**You do NOT need ML. Simple deterministic matching.**

```python
def detect_outcome_signals(text: str, signal_seeds: dict) -> dict:
    """
    Detect outcome signals in text.
    Returns counts of each signal type.
    """
    text_l = text.lower()
    signals = {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
        "replication": 0
    }
    
    for signal_type, phrases in signal_seeds.items():
        for phrase in phrases:
            if phrase in text_l:
                signals[signal_type] += 1
    
    return signals
```

### Store per event as:

```json
{
  "event_id": "abc123",
  "outcome_signals": {
    "positive": 2,
    "neutral": 5,
    "negative": 1,
    "replication": 0
  }
}
```

---

## How This Stays Honest

### You are NOT scoring success.

### You ARE recording:
"Authors used X amount of positive / negative / neutral language."

**That's descriptive, not interpretive.**

---

## What This Unlocks Immediately

You can now answer questions like:

1. **"Which research areas show repeated negative outcome language?"**
   - Answer: Areas with high negative signal counts
   - Interpretation: "Research appears to encounter persistent challenges"

2. **"Which patterns show increasing replication language?"**
   - Answer: Patterns with growing replication signal counts
   - Interpretation: "Validation efforts are increasing"

3. **"Are biohacking-adjacent studies mostly exploratory or outcome-driven?"**
   - Answer: Compare neutral vs positive/negative ratios
   - Interpretation: "Research remains exploratory" or "Research shows outcome focus"

4. **"Where is effort happening but progress language is scarce?"**
   - Answer: High event count + low positive signals
   - Interpretation: "High effort, limited reported progress"

**This is real insight without overclaiming.**

---

## What We Do NOT Do Next

To be explicit:

❌ No conclusions  
❌ No ranking "best" biohacks  
❌ No recommendations  
❌ No advice  
❌ No ML models  
❌ No sentiment analysis hype  

**Just deterministic signal detection.**

---

## Important Notes

### A single paper can contain multiple signal types.

**Example:**
- "We investigated (neutral) the effect of X and found significant improvement (positive), though stability remained limited (negative)."
- Signals: neutral=1, positive=1, negative=1

### This is expected and honest.

Research is complex. Mixed signals are normal.

---

## Current Data Compatibility

Your existing pipeline already extracts:
- ✅ Evidence snippets (where signals will be detected)
- ✅ Event types (decision_point, stability_issue, etc.)
- ✅ Confidence levels

**Outcome signals will add one more dimension:**
- Event type (what kind of event)
- Confidence (how certain we are it's an event)
- **Outcome signals (how authors describe results)** ← NEW

---

## Assessment: Does This Feel Honest?

### My Analysis:

✅ **Fair:** We're tracking language, not making claims  
✅ **Honest:** We distinguish between "reported" and "true"  
✅ **Defensible:** Researchers use this language themselves  
✅ **Useful:** Enables pattern-based insights without hype  

### Potential Concerns:

1. **"What if positive language is just hype?"**
   - Answer: We're tracking hype vs friction, not truth vs lies
   - That's still useful information

2. **"What if negative language is just caution?"**
   - Answer: We're tracking reported challenges, not failures
   - Caution is a signal worth tracking

3. **"What if neutral language hides important results?"**
   - Answer: Neutral language indicates exploratory phase
   - That's valuable to know

### My Recommendation:

**This feels like a fair and honest way to approach "what works / what doesn't" without lying.**

The key is we're always clear:
- We track **reported signals**, not **biological truth**
- We describe **language patterns**, not **outcomes**
- We enable **pattern detection**, not **conclusions**

---

## Next Steps (When Ready)

**STEP 3 (Later):**
- Pattern Scoring v1
- Combining:
  - Pattern type (Step 1)
  - Outcome signals (Step 2)
  - Time
  - Frequency

**This is where "works vs doesn't" becomes pattern-based, not hype-based.**

**But we only do that once Step 2 feels solid.**

---

## STOP POINT

Before moving on, check yourself:

1. ✅ Does this still feel honest?
2. ✅ Does it still feel defensible?
3. ✅ Does it feel like something a researcher wouldn't laugh at?

**If yes, we proceed to Step 3.**

---

## Status

✅ **STEP 1 COMPLETE:** Research Pattern Types formalized  
✅ **STEP 2 COMPLETE:** Outcome Signal Detection defined  
✅ **Seed file created:** `seeds/outcome_signals.json`  
⏸️ **STEP 3 PENDING:** Pattern Scoring (awaiting approval)  
❌ **No implementation yet:** This is conceptual foundation only  

**Foundation documents:**
- `RESEARCH_PATTERNS_FOUNDATION.md` (Step 1)
- `OUTCOME_SIGNALS_FOUNDATION.md` (Step 2)
- `seeds/outcome_signals.json` (Step 2 seed file)

---

## Ready for Step 3?

Say **"ready for Step 3"** when you want to move on to Pattern Scoring.

Or ask questions if anything feels unclear or dishonest.

**We're doing the hard, boring, correct part — and that's why this has legs.**
