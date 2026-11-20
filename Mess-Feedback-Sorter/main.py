"""
Mess Feedback Sorter - Main Application
========================================
A console-based Python application that classifies hostel mess feedback
using the Groq API (e.g., llama-3.3-70b-versatile or llama-3.1-8b-instant).

It reads feedback from a CSV file, classifies each comment into a category,
sentiment, urgency flag and short summary, then generates reports.

The AI only flags and sorts. The hostel warden makes the final decision.
"""

import csv
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# ============================================================
# CONFIGURATION
# ============================================================

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
API_KEY = os.getenv("GROQ_API_KEY")

# Model to use on Groq
# Note: 'qwen/qwen3.8-27b' or 'openai/gpt-oss-120b' are active on your Groq endpoint
MODEL_NAME = "qwen/qwen3.8-27b"

# The Groq client is created only when needed (lazy initialization)
_client = None


def get_client():
    """
    Create and return the Groq API client.
    The client is created once and reused for all API calls.
    Raises an error if the API key is not set.
    """
    global _client
    if _client is None:
        if not API_KEY:
            raise ValueError(
                "GROQ_API_KEY not found! "
                "Create a .env file with: GROQ_API_KEY=your-key-here"
            )
        _client = Groq(api_key=API_KEY)
    return _client


# File paths (relative to this script's directory)
BASE_DIR = Path(__file__).parent
FEEDBACK_FILE = BASE_DIR / "feedback.csv"
SYSTEM_PROMPT_FILE = BASE_DIR / "system_prompt.txt"
RESULTS_FILE = BASE_DIR / "results.csv"
URGENT_FILE = BASE_DIR / "urgent.csv"
SUMMARY_FILE = BASE_DIR / "summary.txt"

# Allowed values for validation
ALLOWED_CATEGORIES = {"taste", "hygiene", "quantity", "timing", "other"}
ALLOWED_SENTIMENTS = {"positive", "negative", "neutral"}

# ============================================================
# Health-risk keywords for the safety net.
# Includes English, Tamil script and Tanglish variants.
# ============================================================

HEALTH_RISK_REGEX_PATTERNS = [
    # --- English ---
    r"\binsect\b", r"\binsects\b",
    r"\bcockroach\b", r"\bcockroaches\b",
    r"\bhair\b", r"\bhairs\b",
    r"\bexpired\b",
    r"\bstale\b",
    r"\bspoiled\b",
    r"\brotten\b",
    r"\bfood\s+poisoning\b",
    r"\bfell\s+sick\b",
    r"\bsick\b",
    r"\bworm\b", r"\bworms\b",
    r"\bmaggot\b", r"\bmaggots\b",
    r"\bfungus\b",
    r"\bvomit\b", r"\bvomited\b", r"\bvomiting\b",
    # --- Tanglish ---
    r"\bpoochi\b", r"\bpuchi\b",       # insect
    r"\bkarappan\b",                    # cockroach
    r"\bmudi\b",                        # hair
    r"\bkalavadhi\b",                   # expired
    r"\bpazhaya\b",                     # stale / old
    r"\bketta\b", r"\bkettu\b",         # spoiled
    r"\bazhugiya\b",                    # rotten
    r"\bpuzhu\b", r"\bpuzhoo\b",        # worm
    r"\bpoonjai\b",                     # fungus
    r"\bvaandhi\b",                     # vomit
]

HEALTH_RISK_TAMIL_KEYWORDS = [
    "பூச்சி",          # poochi  – insect
    "கரப்பான்",        # karappan – cockroach
    "முடி",            # mudi    – hair
    "காலாவதி",         # kalavadhi – expired
    "பழைய",           # pazhaya – stale / old
    "கெட்ட",           # ketta   – spoiled
    "கெட்டு",          # kettu   – spoiled (variant)
    "அழுகிய",          # azhugiya – rotten
    "புழு",            # puzhu   – worm
    "பூஞ்சை",          # poonjai – fungus
    "வாந்தி",          # vaandhi – vomit
    "உணவு நச்சு",      # food poisoning
    "உடம்பு சரியில்லை",  # feeling unwell / sick
]


# ============================================================
# HELPER: Load the system prompt from file
# ============================================================

def load_system_prompt():
    """
    Read the system prompt from system_prompt.txt.
    """
    with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


# ============================================================
# HELPER: Read feedback CSV
# ============================================================

def read_feedback():
    """
    Read feedback.csv and return a list of dictionaries.
    """
    rows = []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except FileNotFoundError:
        print(f"[ERROR] Feedback file not found: {FEEDBACK_FILE}")
    except csv.Error as e:
        print(f"[ERROR] CSV error: {e}")
    return rows


# ============================================================
# FUNCTION A: classify(comment)
# ============================================================

def classify(comment):
    """
    Send a single feedback comment to the Groq API for classification.

    - Never sends empty comments to the API.
    - Includes the system prompt to guide the LLM.
    - Enforces JSON response format via response_format={"type": "json_object"}.
    - Returns the raw JSON string from the LLM.
    - Returns None if the comment is empty or if an API error occurs.
    """
    if not comment or not comment.strip():
        return None

    try:
        system_prompt = load_system_prompt()
        client = get_client()

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": comment
                }
            ],
            model=MODEL_NAME,
            temperature=0.1,  # Low temperature for deterministic classification
            response_format={"type": "json_object"}  # Groq native JSON enforcement
        )

        return chat_completion.choices[0].message.content

    except Exception as e:
        print(f"  [!] API error: {e}")
        return None


# ============================================================
# FUNCTION B: parse_reply(reply)
# ============================================================

def parse_reply(reply):
    """
    Parse the LLM's response text into a Python dictionary.

    - Uses json.loads() to convert the JSON string.
    - Handles markdown code fences if present.
    - Returns None if parsing fails.
    """
    if reply is None:
        return None

    try:
        cleaned = reply.strip()

        # Remove ```json ... ``` or ``` ... ``` wrapping
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines
                     if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)

        data = json.loads(cleaned)
        return data

    except (json.JSONDecodeError, AttributeError) as e:
        print(f"  [!] JSON parsing failed: {e}")
        return None


# ============================================================
# FUNCTION C: is_valid(data)
# ============================================================

def is_valid(data):
    """
    Validate the parsed JSON dictionary against all required rules.

    Checks:
    1. data is a dictionary
    2. Exactly 4 fields: category, sentiment, urgent, summary
    3. category is one of the allowed values
    4. sentiment is one of the allowed values
    5. urgent is a real boolean (True/False), not a string
    6. summary is a string with no more than 12 words
    """
    if not isinstance(data, dict):
        return False

    required_fields = {"category", "sentiment", "urgent", "summary"}

    if set(data.keys()) != required_fields:
        return False

    if data["category"] not in ALLOWED_CATEGORIES:
        return False

    if data["sentiment"] not in ALLOWED_SENTIMENTS:
        return False

    if not isinstance(data["urgent"], bool):
        return False

    if not isinstance(data["summary"], str):
        return False

    if len(data["summary"].split()) > 12:
        return False

    return True


# ============================================================
# FUNCTION D: apply_safety_net(comment, result)
# ============================================================

def apply_safety_net(comment, result):
    """
    Independently scan the original comment for health-risk keywords.
    This is a BACKUP check that runs AFTER the LLM classification.

    Rules:
    - If a health-risk keyword is found, set urgent = True.
    - Can ONLY RAISE urgency (False -> True).
    - Can NEVER REDUCE urgency (True stays True).
    - Does not change category, sentiment or summary.

    Returns the (possibly modified) result dictionary.
    """
    if result is None or not comment:
        return result

    comment_lower = comment.lower()

    # Check English and Tanglish patterns
    for pattern in HEALTH_RISK_REGEX_PATTERNS:
        if re.search(pattern, comment_lower):
            if not result["urgent"]:
                print(f"  [SAFETY NET] Keyword matched: {pattern} → urgent = True")
            result["urgent"] = True
            return result

    # Check Tamil script keywords
    for keyword in HEALTH_RISK_TAMIL_KEYWORDS:
        if keyword in comment:
            if not result["urgent"]:
                print(f"  [SAFETY NET] Tamil keyword matched: {keyword} → urgent = True")
            result["urgent"] = True
            return result

    return result


# ============================================================
# HELPER: Process a single comment (with retry)
# ============================================================

def process_comment(comment):
    """
    Classify a single comment through the full pipeline:
      1. Send to LLM
      2. Parse JSON
      3. Validate
      4. If invalid → retry ONCE
      5. If still invalid → return None (needs manual review)
      6. Apply safety net
    """
    if not comment or not comment.strip():
        return None

    # --- Attempt 1 ---
    raw_reply = classify(comment)
    parsed = parse_reply(raw_reply)

    if parsed is not None and is_valid(parsed):
        return apply_safety_net(comment, parsed)

    # --- Attempt 2 (retry once) ---
    print("  [RETRY] First response invalid. Retrying...")
    raw_reply = classify(comment)
    parsed = parse_reply(raw_reply)

    if parsed is not None and is_valid(parsed):
        return apply_safety_net(comment, parsed)

    print("  [FAIL] Both attempts failed. Marking needs_manual_review.")
    return None


# ============================================================
# HELPER: Process all feedback comments
# ============================================================

def process_all_feedback():
    """
    Read feedback.csv, classify every comment, and return a list
    of result dictionaries ready for report generation.
    """
    rows = read_feedback()
    results = []

    print(f"\nProcessing {len(rows)} feedback comments...\n")

    for i, row in enumerate(rows, start=1):
        feedback_id = row.get("id", "")
        date = row.get("date", "")
        meal = row.get("meal", "")
        comment = row.get("comment", "").strip()

        print(f"[{i}/{len(rows)}] {feedback_id}: ", end="")

        if not comment:
            print("(empty) → needs_manual_review")
            results.append({
                "id": feedback_id,
                "date": date,
                "meal": meal,
                "comment": "",
                "category": "",
                "sentiment": "",
                "urgent": "",
                "summary": "",
                "review_status": "needs_manual_review",
            })
            continue

        preview = comment[:50] + "..." if len(comment) > 50 else comment
        print(f"{preview}")

        try:
            classification = process_comment(comment)
        except Exception as e:
            print(f"  [ERROR] Unexpected error: {e}")
            classification = None

        if classification is not None:
            results.append({
                "id": feedback_id,
                "date": date,
                "meal": meal,
                "comment": comment,
                "category": classification["category"],
                "sentiment": classification["sentiment"],
                "urgent": classification["urgent"],
                "summary": classification["summary"],
                "review_status": "classified",
            })
            print(f"  → {classification['category']} | "
                  f"{classification['sentiment']} | "
                  f"urgent={classification['urgent']} | "
                  f"{classification['summary']}")
        else:
            results.append({
                "id": feedback_id,
                "date": date,
                "meal": meal,
                "comment": comment,
                "category": "",
                "sentiment": "",
                "urgent": "",
                "summary": "",
                "review_status": "needs_manual_review",
            })
            print("  → needs_manual_review")

    return results


# ============================================================
# HELPER: Statistics functions
# ============================================================

def calculate_category_counts(results):
    counts = {cat: 0 for cat in ALLOWED_CATEGORIES}
    for r in results:
        if r["review_status"] == "classified" and r["category"] in counts:
            counts[r["category"]] += 1
    return counts


def calculate_sentiment_counts(results):
    counts = {sent: 0 for sent in ALLOWED_SENTIMENTS}
    for r in results:
        if r["review_status"] == "classified" and r["sentiment"] in counts:
            counts[r["sentiment"]] += 1
    return counts


def calculate_negative_percentage(sentiment_counts, total_classified):
    if total_classified == 0:
        return 0.0
    return round(sentiment_counts["negative"] / total_classified * 100, 1)


def get_urgent_comments(results):
    return [r for r in results
            if r["review_status"] == "classified" and r["urgent"] is True]


def count_manual_review(results):
    return sum(1 for r in results if r["review_status"] == "needs_manual_review")


def generate_summary_text(results):
    total = len(results)
    total_classified = sum(1 for r in results
                          if r["review_status"] == "classified")
    cat_counts = calculate_category_counts(results)
    sent_counts = calculate_sentiment_counts(results)
    neg_pct = calculate_negative_percentage(sent_counts, total_classified)
    urgent_comments = get_urgent_comments(results)
    manual_review_count = count_manual_review(results)

    lines = []
    lines.append("=" * 50)
    lines.append("  MESS FEEDBACK SORTER – SUMMARY REPORT")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Total comments processed: {total}")
    lines.append("")
    lines.append("--- Category Breakdown ---")
    for cat in ["taste", "hygiene", "quantity", "timing", "other"]:
        lines.append(f"  {cat.capitalize():10s}: {cat_counts[cat]}")
    lines.append("")
    lines.append("--- Sentiment Breakdown ---")
    lines.append(f"  Positive : {sent_counts['positive']}")
    lines.append(f"  Negative : {sent_counts['negative']}")
    lines.append(f"  Neutral  : {sent_counts['neutral']}")
    lines.append(f"  Negative %: {neg_pct}%")
    lines.append("")
    lines.append(f"--- Urgent Comments: {len(urgent_comments)} ---")
    if urgent_comments:
        for u in urgent_comments:
            lines.append(f"  [{u['id']}] {u['comment']}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append(f"Comments needing manual review: {manual_review_count}")
    lines.append("")
    lines.append("=" * 50)
    lines.append("NOTE: The warden must read urgent.csv and decide")
    lines.append("what action to take. The AI only flags risks.")
    lines.append("=" * 50)

    return "\n".join(lines)


# ============================================================
# FUNCTION E: write_reports(results)
# ============================================================

def write_reports(results):
    """
    Generate results.csv, urgent.csv, and summary.txt.
    """
    try:
        with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["id", "date", "meal", "comment", "category",
                          "sentiment", "urgent", "summary", "review_status"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"\n[OK] results.csv written ({len(results)} rows)")
    except IOError as e:
        print(f"[ERROR] Could not write results.csv: {e}")

    try:
        urgent_comments = get_urgent_comments(results)
        with open(URGENT_FILE, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["id", "date", "meal", "comment", "summary"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for u in urgent_comments:
                writer.writerow({
                    "id": u["id"],
                    "date": u["date"],
                    "meal": u["meal"],
                    "comment": u["comment"],
                    "summary": u["summary"],
                })
        print(f"[OK] urgent.csv written ({len(urgent_comments)} urgent rows)")
    except IOError as e:
        print(f"[ERROR] Could not write urgent.csv: {e}")

    try:
        summary_text = generate_summary_text(results)
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            f.write(summary_text)
        print(f"[OK] summary.txt written")
        print("\n" + summary_text)
    except IOError as e:
        print(f"[ERROR] Could not write summary.txt: {e}")


# ============================================================
# MAIN: Entry point
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  MESS FEEDBACK SORTER")
    print("  AI-assisted feedback classification for hostel mess (Groq API)")
    print("=" * 60)

    if not API_KEY:
        print("\n[ERROR] GROQ_API_KEY not found!")
        print("Please create a .env file with your Groq API key:")
        print("  GROQ_API_KEY=gsk_your-actual-groq-key-here")
        print("\nGet a free API key at: https://console.groq.com/keys")
        print("See .env.example for the template.")
        exit(1)

    print(f"\n[OK] Groq API key loaded")
    print(f"[OK] Using Groq Model: {MODEL_NAME}")
    print(f"[OK] Reading from: {FEEDBACK_FILE}")

    results = process_all_feedback()
    write_reports(results)

    print("\n[DONE] All reports generated.")
    print("       The warden should review urgent.csv for action.")
