# classification-core.md — GRI Methodology & Classification Opinion Format
## DServe Legal | Customs Classification — Core Reference (Small-Model Edition)

> **Scope:** This file contains only what is needed to produce a Classification Opinion:
> GRI 1–6 methodology, the Indian duty formula, and the output template.
> For SCN replies, CAAR applications, appeals, FTA rules, and practice notes
> see `skills/custom-classification.md`.

---

## STEP 1 — ROUTE TO THE RIGHT CHAPTER

Before reading any chapter file, read `chapter_routing.md`.
Find the product keyword → note the 1–2 chapter numbers listed → read only those chapter files.
Do **not** load chapter files speculatively.

---

## STEP 2 — ALWAYS READ GIR FIRST

Read `chapters/chapter_00_GIR.md` before any heading analysis.
The General Rules of Interpretation (GRI) govern every classification.

---

## THE GRI SEQUENCE — APPLY IN ORDER, NEVER SKIP

### GRI 1 — Section Notes, Chapter Notes, Heading Text
*Resolves the majority of classifications.*

1. Read the **Section Notes** — legally binding; define scope, inclusions, exclusions.
2. Read the **Chapter Notes** — narrow scope within the Section; check definition notes, exclusion notes, subheading notes.
3. Read the **Heading Text** (4-digit) — does the product answer to the heading by name, function, composition, or end-use?

**GRI 1 checklist:**
- [ ] Section Notes read and applied
- [ ] Chapter Notes read and applied; exclusions checked
- [ ] Heading text matches the goods — state *how*
- [ ] No Note expressly excludes the goods from this heading
- If GRI 1 resolves → state this clearly and proceed to GRI 6 (subheading). Stop.

### GRI 2 — Incomplete / Unfinished / Mixed Goods
Apply only if GRI 1 does not resolve.
- **GRI 2(a):** Incomplete or unassembled article → classifies as complete if it has the essential character of the finished article.
- **GRI 2(b):** Mixture or combination of materials → heading for the material also covers it mixed with another, if the mixture retains the essential character. Opens multiple headings → go to GRI 3.

### GRI 3 — Two or More Headings in Contention
Apply only if GRI 1 and 2 leave two or more headings unresolved.
- **GRI 3(a):** Most specific description prevails over a general description.
- **GRI 3(b):** If equally specific → classify by the component that gives the goods their **essential character** (consider: nature, bulk, weight, value, role in use).
- **GRI 3(c):** If 3(a) and 3(b) both fail → heading that occurs **last in numerical order**.

### GRI 4 — Classification by Analogy (rare)
If no heading covers the goods → classify under the heading for goods **most akin** to the goods. Document thoroughly. Rarely used in practice.

### GRI 5 — Packing and Containers
- **GRI 5(a):** Specially shaped containers presented with the article → classify with the article.
- **GRI 5(b):** Packing materials presented with goods → classify with goods, unless clearly suitable for repetitive use.

### GRI 6 — Subheading Classification
After determining the 4-digit heading, apply GRI 1–5 *mutatis mutandis* to select the correct 6-digit subheading. Compare subheadings at the **same level only** (one-dash first, then two-dash). Indian CTH goes to **8 digits**.

---

## VERBATIM QUOTE RULE

- **Always** quote Chapter Notes and Explanatory Note text verbatim from the chapter file.
- If you cannot locate the exact text in the chapter file, write:
  `[TEXT NOT LOCATED IN CHAPTER FILE — manual verification required]`
- **Never** paraphrase or reconstruct legal text from memory.

---

## INDIAN DUTY COMPUTATION

```
Assessable Value (AV)  = CIF value converted to INR at CBIC rate of exchange
BCD                    = AV × BCD rate (check Notification 50/2017-Cus for exemptions)
SWS                    = BCD × 10%  (if BCD > NIL and SWS not exempt)
IGST Base              = AV + BCD + SWS + other duties
IGST                   = IGST Base × IGST rate
Total Duty             = BCD + SWS + IGST + Cess + ADD/CVD (if any)
Effective Duty %       = (Total Duty / AV) × 100
```

Key flags:
- BCD and IGST rates are **indicative** — verify against current notifications and Finance Act in force.
- CBIC exchange rate applies on the date of Bill of Entry presentation — not the inter-bank rate.
- IGST paid on imports is generally ITC-eligible for registered importers.
- Check Notification 50/2017-Customs for serial-number-based BCD exemptions.
- Chapter 99 special provisions may apply (project imports, specific end-use).

---

## CLASSIFICATION OPINION — OUTPUT TEMPLATE

```
# CUSTOMS CLASSIFICATION OPINION

**Product:** [name of goods]
**Ref:** DSL/CC/[Year]/[Number]

---

**A. PRODUCT DESCRIPTION**

[Technical description — material, form, function, end use, mode of presentation]

---

**B. QUERY**

[Classification question in one sentence]

---

**C. APPLICABLE LEGAL FRAMEWORK**

GRI rules applied: [e.g. GRI 1, GRI 6]
Chapter Notes consulted: [e.g. Chapter 68 Note 1]
WCO Explanatory Notes consulted: [e.g. heading 68.14]

---

**D. GRI ANALYSIS**

**D.1 — GRI 1**

Chapter [XX] Notes state (verbatim): "[exact quote from chapter file]"

Heading [XX.XX] — [heading text] — [does it cover the goods? why or why not, quoting verbatim]

Heading [XX.XX] — [heading text] — [competing heading eliminated with reason]

GRI 1 conclusion: [Heading XX.XX applies / does not resolve — continue to D.2]

**D.2–D.5** [Include only if GRI 1 does not resolve]

**D.6 — Subheading Analysis (GRI 6)**

Subheading [XXXX.XX] — [text] — [why it applies]

**Final CTH: [XXXX.XX.XX]**

---

**E. COMPETING HEADINGS ELIMINATED**

| Heading | Why eliminated |
|---------|---------------|
| [XX.XX] | [reason from chapter notes or EN] |

---

**F. DUTY IMPLICATIONS**

| Component | Rate |
|-----------|------|
| BCD | [X]% |
| SWS (10% of BCD) | [X]% |
| IGST | [X]% |
| Estimated effective duty | ~[X]% of CIF |

---

**G. OPINION**

The goods are classifiable under **CTH [XXXX.XX.XX]** — "[description]" of the First Schedule
to the Customs Tariff Act, 1975. Classification is resolved by **GRI [X]**.

---

**H. RECOMMENDATIONS**

1. [Advance ruling / documentation / notification advice]
2. [Any other recommendation]

---

**I. CAVEAT**

This opinion is a draft based on the product information provided and the WCO Explanatory
Notes (7th Edition, 2022). Duty rates are indicative and subject to notifications.
Only a CAAR Advance Ruling provides a legally binding classification.

**DRAFT — FOR REVIEW BY CUSTOMS CONSULTANT BEFORE ADVICE TO CLIENT**
```
