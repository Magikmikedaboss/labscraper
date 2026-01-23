# Research Pattern Types - Foundation Document

## STEP 1: Formalize Research Pattern Types

**Date:** 2026-01-22
**Status:** Conceptual Foundation (No Implementation Yet)  
**Purpose:** Define honest, domain-agnostic pattern language for research intelligence

---

## What Is a Research Pattern?

**A research pattern is NOT:**
- A paper
- An entity
- A claim about efficacy
- A biological truth

**A research pattern IS:**
- A recurring configuration over time
- Observable across multiple events
- Describable through:
  - **Entities** (what)
  - **Methods** (how)
  - **Models** (where)
  - **Frequency** (how often)
  - **Trajectory** (what happens next)

**Key Insight:** Patterns only emerge when you look across events. Your engine already has the data to detect them.

---

## The 5 Pattern Types (Final, Stable Set)

These 5 are sufficient to support any research field.  
They describe **behavior**, not **truth**.

---

### 🟢 1. Convergence Pattern

**What it means:**  
Research effort is repeatedly clustering around the same entities + methods.

**Signals:**
- Same primary entities appear across many events
- Same assays reused
- Similar models used
- Frequency increases or remains steady

**Allowed interpretation:**  
"Research effort is converging around this approach."

**NOT allowed to say:**
- That it works
- That it is effective
- That it is the "right" approach

**Why this matters:**  
Convergence is the strongest early indicator of perceived promise in science.

**Example from current data:**
- LC-MS appears in 85 events (convergence on this assay)
- SEMAGLUTIDE appears in 10 events (convergence on this compound)

---

### 🔵 2. Escalation Pattern

**What it means:**  
Research effort is moving toward higher-validation contexts.

**Signals:**
- in vitro → in vivo → human samples
- qualitative → quantitative assays
- simple metrics → PK/PD, durability, stability
- Increasing methodological rigor

**Allowed interpretation:**  
"This line of research shows increasing validation effort."

**NOT allowed to say:**
- That it is succeeding
- That it will reach clinical trials
- That it is safe or effective

**Why this matters:**  
Escalation is how ideas survive contact with reality.

**Example from current data:**
- Events showing progression from cell culture → animal models → human samples
- Events showing progression from qualitative → quantitative assays

---

### 🟠 3. Stagnation Pattern

**What it means:**  
The same problems are being studied repeatedly without structural change.

**Signals:**
- Same limitation terms recur (aggregation, instability, degradation)
- Same assays repeated
- Same models repeated
- No new entities or methods introduced
- Frequency remains constant but no progression

**Allowed interpretation:**  
"Research effort appears to be encountering persistent technical barriers."

**NOT allowed to say:**
- That the approach "doesn't work"
- That it should be abandoned
- That it is a dead end

**Why this matters:**  
This is how you responsibly talk about "what doesn't work yet" without making claims.

**Example from current data:**
- AGGREGATION appears in 24 events (recurring problem)
- PEPTIDE DEGRADATION appears in 9 events (persistent challenge)

---

### 🔴 4. Abandonment Pattern

**What it means:**  
Research interest appears to drop after initial exploration.

**Signals:**
- Entity appears briefly, then disappears
- No follow-up events
- No diversification
- Frequency declines sharply
- Time gap increases

**Allowed interpretation:**  
"Research attention appears to have decreased."

**NOT allowed to say:**
- That it failed
- That it was proven ineffective
- Why it was abandoned

**Why this matters:**  
Quiet abandonment is common and rarely surfaced. This makes it visible.

**Example from current data:**
- Entities that appear in 1-2 events only, with no recent activity

---

### 🟣 5. Fragmentation Pattern

**What it means:**  
The field lacks agreement on methods or direction.

**Signals:**
- Many assays, no dominant method
- Many models, no consensus
- Low recurrence across entities
- Low confidence throughout
- High diversity, low convergence

**Allowed interpretation:**  
"The research area remains exploratory and methodologically diverse."

**NOT allowed to say:**
- That the field is "confused"
- That there is no progress
- That one method is better than another

**Why this matters:**  
Fragmentation often precedes either breakthroughs or abandonment. It's a neutral observation.

**Example from current data:**
- 24 different assay types with varying frequencies
- 12 different pathway targets with low individual recurrence

---

## How These Patterns Stay Honest

### What these patterns describe:
✅ **Effort** - Where researchers are focusing  
✅ **Behavior** - What actions are being taken  
✅ **Attention** - What is being studied  
✅ **Trajectory** - How research is evolving  

### What these patterns do NOT describe:
❌ **Outcomes** - Whether approaches work  
❌ **Efficacy** - Whether treatments are effective  
❌ **Safety** - Whether approaches are safe  
❌ **Biological truth** - What is scientifically correct  

**That's why researchers won't dismiss this.**

---

## How This Fits Your Current Data

Your current exports already support pattern detection:

| Pattern Type | Current Data Support |
|--------------|---------------------|
| **Convergence** | ✅ Recurrence counts, entity frequencies |
| **Escalation** | ✅ Model context (in vitro/in vivo), assay types |
| **Stagnation** | ✅ Recurring limitation terms, repeated assays |
| **Abandonment** | ✅ Time gaps, frequency decline |
| **Fragmentation** | ✅ Assay diversity, low recurrence, confidence distribution |

**You do not need new scraping to define patterns.**  
**We are naming what already exists.**

---

## Minimal Schema Addition (Conceptual Only)

```python
Pattern {
  pattern_id: str           # Unique identifier
  pattern_type: str         # convergence | escalation | stagnation | abandonment | fragmentation
  primary_entities: list    # Entities involved
  methods: list             # Assays/techniques used
  models: list              # Experimental contexts
  time_window: tuple        # (start_date, end_date)
  supporting_events: list   # Event IDs that support this pattern
  confidence: float         # 0.0-1.0 confidence in pattern detection
  frequency: int            # Number of occurrences
  trajectory: str           # increasing | stable | decreasing
}
```

**This is conceptual for now. No implementation yet.**

---

## How This Answers Your Original Goal

When you later ask:  
**"What research patterns appear to work or not work?"**

You will translate that to defensible science language:

| Pattern Combination | Interpretation |
|--------------------|----------------|
| **Convergence + Escalation** | → Promising (high effort + increasing validation) |
| **Stagnation** | → Blocked (persistent barriers) |
| **Abandonment** | → Deprioritized (declining attention) |
| **Fragmentation** | → Uncertain (exploratory phase) |
| **Convergence + Stagnation** | → Active but challenged |

**This is defensible science language.**

---

## Current Data Examples

### Convergence Pattern Example:
- **Entity:** LC-MS (assay)
- **Frequency:** 85 events
- **Interpretation:** "Research effort is converging around LC-MS as a primary analytical method."

### Stagnation Pattern Example:
- **Entity:** AGGREGATION (pathway)
- **Frequency:** 24 events
- **Interpretation:** "Research effort appears to be encountering persistent aggregation challenges."

### Fragmentation Pattern Example:
- **Observation:** 24 different assay types with varying frequencies
- **Interpretation:** "The analytical methodology remains exploratory and diverse."

---

## STOP POINT

**Do not implement anything yet.**

### Questions to consider:

1. ✅ Do these 5 patterns feel sufficient?
2. ✅ Do they feel honest?
3. ✅ Can you imagine a researcher recognizing themselves in them?
4. ✅ Is there a pattern type that feels missing or confusing?

---

## Next Steps (When Ready)

**STEP 2 (Later):**  
Add Outcome Signal detection to support pattern scoring  
(not conclusions, just language signals).

**But we do not do that yet.**

---

## Assessment

### Do these five pattern types feel like the right foundation?

**My assessment:**

✅ **Convergence** - Clear, measurable, honest. Captures "where effort is going."

✅ **Escalation** - Clear progression signal. Captures "increasing validation."

✅ **Stagnation** - Honest way to describe persistent challenges without claiming failure.

✅ **Abandonment** - Important signal that's rarely surfaced. Captures "declining attention."

✅ **Fragmentation** - Captures early-stage exploration without judgment.

### Potential considerations:

1. **Are these 5 sufficient?** 
   - Yes. They cover the full lifecycle: exploration → convergence → validation → persistence/abandonment
   - Any research trajectory can be described by one or more of these patterns

2. **Are they honest?**
   - Yes. They describe observable behavior, not outcomes
   - They avoid claims about efficacy, safety, or biological truth
   - Researchers would recognize these patterns in their own work

3. **Is anything missing?**
   - Possibly: **Diversification Pattern** (when research branches into new directions)
   - But this might be captured by "Fragmentation" or inverse "Convergence"
   - Question: Should we add a 6th pattern for "Diversification" or is it covered?

4. **Is anything confusing?**
   - The distinction between "Stagnation" and "Abandonment" is clear
   - The distinction between "Fragmentation" and early "Convergence" is clear
   - All 5 feel distinct and non-overlapping

### My recommendation:

**These 5 patterns feel solid as the foundation.**

The only question is whether we need a 6th pattern for **"Diversification"** (research branching into new methods/entities after initial convergence), or if that's already captured by the existing 5.

**What do you think?** Should we proceed with these 5, or add Diversification as a 6th pattern?
