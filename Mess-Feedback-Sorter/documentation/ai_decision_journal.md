# AI Decision Journal

A beginner-friendly record of the design decisions made while building the Mess Feedback Sorter.

---

## 1. Why was an LLM selected for classification?

Hostel mess feedback comes in free-text form — students write in English, Tamil and Tanglish. A simple keyword-based approach cannot reliably understand the meaning of sentences like "Dosa was cold by the time I reached the counter" (timing, not taste) or "Meals romba nalla irukku" (positive Tanglish feedback).

An LLM can understand natural language across multiple languages, extract the category and sentiment, and generate a short summary — all in one API call. This is far more flexible than writing hundreds of if-else rules.

**Decision:** Use Google Gemini API (free tier, `gemini-2.5-flash` model) for its multilingual capability, structured JSON output support and zero cost for small-scale use.

---

## 2. Why does Python handle all counting?

LLMs can make arithmetic mistakes. If you ask an LLM "how many negative comments are there?", it might miscounted or hallucinate a number.

Counting is a simple, deterministic operation that Python does perfectly every time. There is no reason to involve an expensive, probabilistic AI for basic addition.

**Decision:** Python calculates all statistics — category counts, sentiment counts, negative percentage and urgent totals. The LLM is never asked to count anything.

---

## 3. Why is validation required?

LLMs are not perfectly reliable. Even with a clear system prompt, the LLM might:

- Return extra fields (like `"confidence": 0.9`)
- Use wrong category names (like `"flavor"` instead of `"taste"`)
- Return `"true"` as a string instead of the boolean `true`
- Write a summary that is too long
- Wrap the JSON in markdown code fences

Without validation, these errors would silently corrupt our output reports.

**Decision:** The `is_valid()` function checks every response against strict rules. Any response that fails validation is retried or sent to manual review.

---

## 4. Why is a retry implemented?

API calls can fail for temporary reasons:

- Network timeout
- Server overload (429 rate limit)
- The LLM producing slightly malformed JSON on one attempt

A single retry gives the system a second chance before giving up. More than one retry would waste API calls and slow down processing.

**Decision:** Retry exactly once. If both attempts fail, mark the comment as `needs_manual_review` instead of crashing the program.

---

## 5. Why is the safety net necessary?

The LLM might miss a health-risk keyword, especially in Tanglish. For example:

- "Sambar la poochi irukku" — the LLM might not know "poochi" means insect
- A prompt injection attack might trick the LLM into ignoring the health risk

The safety net is a simple Python function that scans the original comment for known health-risk keywords in English, Tamil and Tanglish. It acts as a backup — it can only **raise** urgency, never lower it.

**Decision:** Always run the safety net after the LLM classification. The safety net is a "catch-all" that covers cases the LLM misses.

---

## 6. Why does the warden remain responsible?

AI classification is not 100% accurate. The LLM might:

- Misunderstand sarcasm
- Over-flag a non-urgent comment
- Miss a health risk described in unusual wording

A human (the hostel warden) must read `urgent.csv` and decide what action to take. The AI is a tool that saves time by sorting and flagging — it does not replace human judgment.

**Decision:** The system generates reports but never takes action. The warden reads the urgent report and decides whether to inspect the kitchen, contact suppliers or take other steps.

---

## 7. What limitations were discovered?

- **Tanglish variability:** Tamil words written in English letters have no standard spelling. "Poochi" might also be written as "puchi", "poochee", etc. The safety net covers common variants but cannot catch every possible spelling.
- **Tamil script support:** The LLM handles Tamil script reasonably well, but very colloquial or slang Tamil may be misclassified.
- **Rate limits:** The free tier has request-per-minute limits. Processing a large batch of feedback requires pacing.
- **Summary length:** Occasionally the LLM produces summaries slightly over 12 words, requiring validation and retry.
- **Sarcasm:** Comments like "Great job making inedible food!" may be misclassified as positive.

---

## 8. What changes were made during development?

1. **Lazy client initialization:** Originally the Gemini client was created at module load time, which crashed the program if no API key was set (breaking unit tests). Changed to lazy initialization with `get_client()`.
2. **Markdown fence stripping:** Added logic in `parse_reply()` to strip ` ```json ... ``` ` wrappers, since some LLM responses include them despite the system prompt saying not to.
3. **Safety net keyword list expansion:** Added Tanglish variants like "kettu" (spoiled variant) and "puzhu"/"puzhoo" (worm) after realizing the initial list was too narrow.
4. **Low temperature setting:** Set `temperature=0.2` for more consistent, deterministic classifications instead of the default higher value.
