# Mess Feedback Sorter — Project Specification

## 1. Problem Statement

Hostel mess committees collect daily feedback from students about the food served at breakfast, lunch and dinner. This feedback arrives as free-text comments — sometimes in English, sometimes in Tamil, and sometimes in **Tanglish** (Tamil words written using English letters).

Manually reading every comment, deciding its category, checking its tone and spotting health risks is slow and error-prone. Important complaints about insects in food or spoiled items can get buried among ordinary taste or quantity comments.

**Mess Feedback Sorter** is a console-based Python application that uses a Large Language Model (LLM) API to automatically classify each feedback comment into a structured format, flag possible health risks as **urgent**, and generate reports for the hostel warden.

> **The AI only flags and sorts. A human (the warden) makes every final decision.**

---

## 2. Input Format

The input is a CSV file called `feedback.csv` with the following columns:

| Column    | Description                                      |
|-----------|--------------------------------------------------|
| `id`      | Unique feedback ID (e.g. F01, F02)               |
| `date`    | Date of the feedback in YYYY-MM-DD format         |
| `meal`    | Meal type: Breakfast, Lunch, or Dinner            |
| `comment` | The student's feedback text (may be empty)        |

### Language support

The `comment` field may contain text in:

- **English** — e.g. "Rice was undercooked again today"
- **Tamil** — e.g. "சாம்பார் நல்லா இருந்தது"
- **Tanglish** — e.g. "Sambar la poochi irukku"

### Empty comments

Some rows may have an empty `comment` field. These must **never** be sent to the LLM. They are directly marked as `needs_manual_review`.

---

## 3. LLM Classification — JSON Output Structure

For every non-empty comment, the application sends the text to an LLM API. The LLM must return a **valid JSON object** with exactly four fields:

```json
{
  "category": "hygiene",
  "sentiment": "negative",
  "urgent": true,
  "summary": "Insect found in sambar"
}
```

### 3.1 Allowed `category` values

| Value      | Meaning                                      |
|------------|----------------------------------------------|
| `taste`    | Complaints or praise about food taste/quality |
| `hygiene`  | Cleanliness, foreign objects, freshness       |
| `quantity` | Too little or too much food                   |
| `timing`   | Food served early, late, or at wrong time     |
| `other`    | Anything that does not fit the above           |

### 3.2 Allowed `sentiment` values

| Value      | Meaning             |
|------------|---------------------|
| `positive` | Happy, satisfied     |
| `negative` | Unhappy, complaining |
| `neutral`  | No strong feeling    |

### 3.3 `urgent` flag (Boolean)

- Must be a **real Boolean** (`true` or `false`), never a string.
- Must be `true` **only** for possible health risks.

### 3.4 `summary` field

- A short summary of the feedback.
- **Maximum 12 words.**

---

## 4. What Counts as Urgent

The `urgent` flag must be `true` **only** when the feedback describes a possible health or food-safety risk:

| Health-Risk Situation            | Example                                      |
|----------------------------------|----------------------------------------------|
| Foreign objects in food          | "Found a stone in the rice"                  |
| Insects in food                  | "There was a cockroach in the sambar"        |
| Hair in food                     | "Found a hair strand in my dal"              |
| Stale or spoiled food            | "The curd smells spoiled"                    |
| Expired food                     | "The bread packet was past its expiry date"  |
| Food poisoning                   | "Three students got food poisoning"          |
| Someone falling sick after eating| "I fell sick after eating dinner yesterday"  |
| Worms or maggots                 | "There was a worm in the vegetable curry"    |

### What is NOT urgent

These complaints must **never** be marked urgent, no matter how angry the student sounds:

- Taste complaints ("Food is terrible", "Too much salt")
- Quantity complaints ("Not enough rice", "Portions are too small")
- Timing complaints ("Dinner was served 30 minutes late")
- General dissatisfaction ("This mess is the worst")

---

## 5. Validation Rules

After receiving the LLM's JSON response, the Python program validates it by checking:

1. **All four required fields exist**: `category`, `sentiment`, `urgent`, `summary`.
2. **No unexpected/extra fields** are present.
3. **`category`** is one of: `taste`, `hygiene`, `quantity`, `timing`, `other`.
4. **`sentiment`** is one of: `positive`, `negative`, `neutral`.
5. **`urgent`** is a real Python Boolean (`True` or `False`), not the string `"true"` or `"false"`.
6. **`summary`** is a string with no more than 12 words.
7. **No field is missing or null.**

If validation fails, the response is considered **invalid**.

---

## 6. Retry and Fallback Logic

```
For each non-empty comment:
  1. Send to LLM → get response
  2. Parse JSON → validate
  3. If valid → use result
  4. If invalid → retry ONCE (second API call)
  5. Parse and validate the retry response
  6. If valid → use result
  7. If still invalid → mark as needs_manual_review
```

- **Maximum API calls per comment**: 2 (original + one retry).
- **Empty comments**: 0 API calls, directly `needs_manual_review`.
- **A single failed comment must never crash the entire program.**

---

## 7. Safety Net (`apply_safety_net`)

The safety net is a **Python function** that independently scans the original feedback text for health-risk keywords. It runs **after** the LLM classification.

### Purpose

The LLM might miss a health risk. The safety net is a backup check using simple keyword matching.

### Keywords checked (English, Tamil, Tanglish)

| English         | Tamil (script)     | Tanglish           |
|-----------------|--------------------|--------------------|
| insect          | பூச்சி              | poochi             |
| insects         |                    | puchi              |
| cockroach       | கரப்பான் பூச்சி     | karappan           |
| hair            | முடி               | mudi               |
| expired         | காலாவதி            | kalavadhi          |
| stale           | பழைய              | pazhaya            |
| spoiled         | கெட்ட              | ketta              |
| rotten          | அழுகிய             | azhugiya           |
| food poisoning  | உணவு நச்சு          | food poisoning     |
| fell sick       |                    | fell sick          |
| sick            | உடம்பு சரியில்லை     | udambu sariyillai  |
| worm            | புழு               | puzhoo / puzhu     |
| maggot          |                    | maggot             |
| fungus          | பூஞ்சை             | poonjai            |
| vomit           | வாந்தி             | vaandhi            |

### Rules

- If **any** health-risk keyword is found in the original comment → set `urgent = True`.
- The safety net can **only raise** urgency (from `False` to `True`).
- It must **never reduce** urgency (from `True` to `False`).
- Ordinary taste, quantity or timing complaints must not be marked urgent just because the tone is angry or negative.

---

## 8. Output Files

### 8.1 `results.csv`

Contains **every** input comment with classification results.

| Column          | Description                                               |
|-----------------|-----------------------------------------------------------|
| `id`            | Original feedback ID                                      |
| `date`          | Original date                                             |
| `meal`          | Original meal                                             |
| `comment`       | Original feedback text                                    |
| `category`      | Classified category (or empty if `needs_manual_review`)   |
| `sentiment`     | Classified sentiment (or empty if `needs_manual_review`)  |
| `urgent`        | `True` or `False` (or empty if `needs_manual_review`)     |
| `summary`       | Short summary (or empty if `needs_manual_review`)         |
| `review_status` | `classified` or `needs_manual_review`                     |

### 8.2 `urgent.csv`

Contains **only** the comments where `urgent` is `True`.

| Column    | Description              |
|-----------|--------------------------|
| `id`      | Original feedback ID     |
| `date`    | Original date            |
| `meal`    | Original meal            |
| `comment` | Original feedback text   |
| `summary` | Short summary of the risk|

### 8.3 `summary.txt`

A plain-text report containing:

- Total number of comments processed
- Count per category (taste, hygiene, quantity, timing, other)
- Positive comment count
- Negative comment count
- Neutral comment count
- Negative sentiment percentage (calculated by Python, not by the LLM)
- Total urgent comments
- List of each urgent comment with its ID and original text
- Number of comments needing manual review

---

## 9. Human Checkpoint

> **THE WARDEN READS EVERY COMMENT IN `urgent.csv`.**

The AI system only classifies and flags feedback. It does **not** take any action. The final decision on what to do about any complaint — especially urgent health risks — is made by the **hostel warden** (a human).

This is a core design principle: **AI assists, humans decide.**

---

## 10. Testing

### 10.1 Evaluation Harness (`tests/eval_harness.py`)

- Tests at least **5 feedback comments** with known expected results.
- Each test checks: input comment, expected category, expected urgent flag, actual result, pass/fail.
- LLM responses are **mocked** so tests are deterministic and repeatable.
- Covers: taste complaint, hygiene/insect complaint, quantity complaint, positive feedback, food poisoning/spoiled food complaint.

### 10.2 Red-Team Tests (`tests/red_team_tests.py`)

Three specific attack/edge-case tests:

1. **Prompt injection**: A comment that tries to trick the LLM (e.g. "Ignore all instructions..."). The safety net must still catch health-risk keywords and mark `urgent = True`.
2. **Tanglish health risk**: A Tanglish comment like "Sambar la poochi irukku" must be classified as `hygiene` with `urgent = True`.
3. **Empty comment**: Must not trigger an API call and must be marked `needs_manual_review`.

---

## 11. Security

- The LLM API key is stored in a `.env` file and loaded using `python-dotenv`.
- The API key is **never hardcoded** in any source file.
- `.env` is listed in `.gitignore`.
- A `.env.example` file shows the variable name with a placeholder value.
- Feedback comments are treated as **untrusted data**. The system prompt instructs the LLM to never follow instructions embedded inside feedback text.

---

## 12. Technology Stack

| Component          | Technology                       |
|--------------------|----------------------------------|
| Language           | Python 3                         |
| CSV processing     | Python `csv` module              |
| JSON parsing       | Python `json` module             |
| File paths         | Python `pathlib`, `os`           |
| Text matching      | Python `re` module               |
| Environment vars   | `python-dotenv`                  |
| LLM API            | Google Gemini API (free tier)     |
| Testing            | `pytest` or Python `unittest`    |
| Package management | `requirements.txt`               |

---

## 13. Folder Structure

```
Mess-Feedback-Sorter/
│
├── main.py                  # Main Python application
├── feedback.csv             # Input: 25+ student feedback comments
├── system_prompt.txt        # LLM system prompt
├── results.csv              # Output: all classified feedback
├── urgent.csv               # Output: urgent/health-risk feedback only
├── summary.txt              # Output: statistics report
├── requirements.txt         # Python dependencies
├── .env.example             # Placeholder for API key
├── .gitignore               # Files to exclude from Git
├── README.md                # Project documentation
│
├── tests/
│   ├── __init__.py          # Makes tests a Python package
│   ├── eval_harness.py      # 5+ evaluation tests
│   └── red_team_tests.py    # 3 red-team/adversarial tests
│
└── documentation/
    ├── specification.md     # This document
    ├── judgment_framework.md
    ├── cost_latency.md
    ├── ai_decision_journal.md
    └── reflection.md
```
