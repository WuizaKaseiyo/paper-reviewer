# Paper Review Template

> **Usage**: This template is organized into two main parts: a **Desk Rejection Assessment** screening pass, followed by the **Formal Review**. Fill in each section in order.

---

# Part I. Desk Rejection Assessment

> Before proceeding to substantive review, complete the four screening checks below. Failing any one of them is grounds for desk rejection.

## 1. Paper Length
- [ ] Pass ✅ / Fail ❌
- Notes:

## 2. Topic Compatibility
- [ ] Pass ✅ / Fail ❌
- Is the paper within the venue's scope (indicate the relevant track/area):

## 3. Minimum Quality
Does the paper contain the expected scientific components:
- [ ] Abstract
- [ ] Introduction
- [ ] Related Work
- [ ] Methodology
- [ ] Experiments
- [ ] Quantitative Results
- [ ] Conclusion / Limitations

Verdict: - [ ] Pass ✅ / Fail ❌
Notes:

## 4. Prompt Injection and Hidden Manipulation Detection
- [ ] No hidden instructions, reviewer-targeting text, or other manipulation attempts found
- [ ] Suspicious content found (describe):

Verdict: - [ ] Pass ✅ / Fail ❌

---

# Part II. Formal Review (Expected Review Outcome)

## 1. Confidence in Your Evaluation
> 1 = Unfamiliar; 2 = Somewhat familiar; 3 = Confident, topic close to expertise; 4 = Expert-level; 5 = Absolute authority

- Score: ___ / 5
- Justification:

## 2. Importance / Relevance
> 1 = Marginal; 2 = Locally relevant; 3 = Mainstream relevance; 4 = Of broad interest; 5 = Critical problem

- Score: ___ / 5
- Justification:

## 3. Novelty / Originality
> 1 = Restates known work; 2 = Minor improvement; 3 = Moderately original; 4 = Substantially original; 5 = Groundbreaking

- Score: ___ / 5
- Justification:

## 4. Technical Correctness
> 1 = Clearly wrong; 2 = Multiple concerns; 3 = Probably correct; 4 = Largely correct; 5 = Rigorously correct

- Score: ___ / 5
- Justification (flag key derivations, assumptions, and potential inconsistencies):

## 5. Experimental Validation and Reproducibility
> 1 = Missing; 2 = Insufficient; 3 = Limited but convincing; 4 = Sufficient; 5 = Complete and fully reproducible

- Score: ___ / 5
- Justification (coverage of benchmarks, baselines, ablations, disclosure of details):

## 6. Clarity of Presentation
> 1 = Hard to read; 2 = Multiple confusions; 3 = Clear enough; 4 = Clear and fluent; 5 = Exceptional

- Score: ___ / 5
- Justification (figures/tables, notation, theory-to-implementation bridge):

## 7. Reference to Prior Work
> 1 = Severely missing; 2 = Missing key references; 3 = Mostly complete; 4 = Fairly comprehensive; 5 = Comprehensive

- Score: ___ / 5
- Justification:

---

# Part III. Potentially Missing Related Work

> List works identified during review that are directly relevant but not cited or discussed. Use the structure below for each entry.

### 1. **[Authors], "[Paper Title]," [Year]**
- **Relevance**: Why is this work relevant to the paper under review?
- **Suggested Placement**: Which section / paragraph should discuss it?
- **How to Use**: Background citation / Baseline comparison / Future-work extension?

### 2. **[Authors], "[Paper Title]," [Year]**
- **Relevance**:
- **Suggested Placement**:
- **How to Use**:

*(Add more entries as needed)*

---

# Part IV. Overall Evaluation

> 1 = Strong Reject; 2 = Reject; 3 = Weak Reject; 4 = Weak Accept; 5 = Accept; 6 = Strong Accept

- **Score**: ___ / 6
- **One-line summary**:

---

# Part V. Strengths, Weaknesses, and Justification

## Strengths

> Aim for 3–5 items. Each should follow the structure: **bolded headline** + concrete evidence (cite specific Figures / Tables / Equations / numbers).

1. **[Strength headline]**
   Concrete explanation, citing specific Figure X / Table Y / Eq. (Z) / experimental numbers as evidence.

2. **[Strength headline]**

3. **[Strength headline]**

4. **[Strength headline]**

## Weaknesses

> Aim for 3–6 items. Cite specific locations; distinguish between **fatal flaws** and **fixable issues**.

1. **[Weakness headline]**
   Concrete explanation + specific location + impact on the paper's main claims.

2. **[Weakness headline]**

3. **[Weakness headline]**

4. **[Weakness headline]**

5. **[Weakness headline]**

6. **[Weakness headline]**

## Justification

> Synthesize Strengths and Weaknesses to justify the Overall Evaluation score above. Aim for 2–3 paragraphs.

- Paragraph 1: Positive assessment (problem importance, contribution, empirical support)
- Paragraph 2: Reservations (theory-to-practice gap, literature coverage, experimental scope, etc.)
- Paragraph 3: Final balanced judgment

---

# Part VI. Additional Comments to Authors (Optional)

> For specific suggestions that do not affect the score but would improve the paper. Examples:

- [ ] Formatting issues (e.g., leftover headers from other venues, layout errors)
- [ ] Missing variance or confidence intervals in main tables/figures
- [ ] Suggest including pseudocode in the main paper rather than only the appendix
- [ ] Suggest a worked end-to-end example (with actual prompts / outputs)
- [ ] Notation consistency suggestions
- [ ] Disclosure of key hyperparameters / implementation details needed for reproduction
- [ ] Other:

---

# Reviewer Self-Check

Before submitting, confirm the following:

- [ ] Read the full paper (including appendix sections directly supporting the main claims)
- [ ] Verified key equation derivations
- [ ] Cross-checked numbers in main tables against the narrative
- [ ] Verified that each figure actually supports the conclusion it claims
- [ ] Identified core assumptions and assessed their plausibility
- [ ] Examined the gap between the theoretical framework and the actual implementation
- [ ] Searched for potentially missing related work
- [ ] Scores, Strengths, Weaknesses, and Justification are internally consistent
- [ ] Comments are objective, specific, and actionable (avoid vague criticism)
