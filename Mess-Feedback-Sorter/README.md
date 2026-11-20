# Mess Feedback Sorter

A console-based Python application that classifies hostel mess feedback using the Google Gemini API. Built as a capstone project for the CIT AI-Native Engineering Programme (Semester 1, Assessment 5).

## Project Overview

Hostel mess committees collect daily feedback from students about food quality. This tool:

1. **Reads** feedback from a CSV file (supports English, Tamil and Tanglish)
2. **Classifies** each comment using an LLM into category, sentiment, urgency and summary
3. **Validates** every LLM response with strict Python checks
4. **Applies a safety net** that scans for health-risk keywords the LLM might miss
5. **Generates reports** (results.csv, urgent.csv, summary.txt) for the hostel warden

> **The AI only flags and sorts. The hostel warden makes every final decision.**

## Features

- **Multilingual support**: English, Tamil script, and Tanglish (Tamil in English letters)
- **LLM classification**: Category (taste/hygiene/quantity/timing/other), sentiment (positive/negative/neutral), urgency flag, short summary
- **Strict validation**: Checks JSON structure, field values, data types and summary length
- **Retry logic**: Invalid responses are retried once; persistent failures go to manual review
- **Safety net**: Python keyword scanner catches health risks the LLM might miss (insects, spoiled food, food poisoning, etc.)
- **Prompt injection defence**: System prompt treats feedback as untrusted data; safety net provides a second line of defence
- **Three output reports**: Complete results, urgent-only report, and statistical summary

## Folder Structure

```
Mess-Feedback-Sorter/
│
├── main.py                  # Main Python application
├── feedback.csv             # Input: 30 student feedback comments
├── system_prompt.txt        # LLM system prompt (5-role framework)
├── results.csv              # Output: all classified feedback
├── urgent.csv               # Output: urgent/health-risk feedback only
├── summary.txt              # Output: statistics report
├── requirements.txt         # Python dependencies
├── .env.example             # Placeholder for API key
├── .gitignore               # Files excluded from Git
├── README.md                # This file
│
├── tests/
│   ├── __init__.py          # Makes tests a Python package
│   ├── eval_harness.py      # 6 evaluation tests (mocked LLM)
│   └── red_team_tests.py    # 4 red-team / adversarial tests
│
└── documentation/
    ├── specification.md     # Full project specification
    ├── judgment_framework.md # AI vs Python vs Human decisions
    ├── cost_latency.md      # API cost and timing estimates
    ├── ai_decision_journal.md # Design decision log
    └── reflection.md        # 400-word reflection
```

## Installation

### 1. Prerequisites

- Python 3.10 or later
- A Google Gemini API key (free tier)

### 2. Install dependencies

```bash
cd Mess-Feedback-Sorter
pip install -r requirements.txt
```

This installs:
- `google-genai` — Google Gemini API SDK
- `python-dotenv` — Loads API key from `.env` file
- `pytest` — Test framework

## API Key Setup

### 1. Get a free Gemini API key

1. Go to [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Click **"Create API Key"**
3. Copy the key

### 2. Create the `.env` file

In the project root, create a file called `.env`:

```
GEMINI_API_KEY=your-actual-api-key-here
```

> **Never share or commit your `.env` file.** It is listed in `.gitignore`.

## How to Run the Project

```bash
cd Mess-Feedback-Sorter
python main.py
```

The program will:
1. Read `feedback.csv`
2. Classify each comment via the Gemini API
3. Validate every response
4. Apply the safety net
5. Generate `results.csv`, `urgent.csv` and `summary.txt`

## How to Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run evaluation harness only
python -m pytest tests/eval_harness.py -v

# Run red-team tests only
python -m pytest tests/red_team_tests.py -v
```

All tests use **mocked LLM responses** so they run without an API key and produce deterministic results.

## Input and Output Files

| File | Type | Description |
|------|------|-------------|
| `feedback.csv` | Input | 30 student feedback comments (English, Tamil, Tanglish) |
| `results.csv` | Output | Every comment with its classification and review status |
| `urgent.csv` | Output | Only urgent (health-risk) comments for the warden |
| `summary.txt` | Output | Category counts, sentiment stats, urgent list |

## Safety Net

The safety net is a Python function (`apply_safety_net`) that scans the **original comment** for health-risk keywords in three languages:

- **English**: insect, hair, stale, spoiled, expired, food poisoning, worm, vomit, sick, etc.
- **Tamil script**: பூச்சி, கெட்ட, முடி, புழு, வாந்தி, etc.
- **Tanglish**: poochi, mudi, pazhaya, ketta, puzhu, vaandhi, etc.

**Rules:**
- The safety net can only **raise** urgency (False → True)
- It can **never reduce** urgency (True stays True)
- It runs after every LLM classification as a backup

## Human Checkpoint

> **THE WARDEN READS EVERY COMMENT IN `urgent.csv`.**

The AI only flags possible health risks. The hostel warden decides whether to:
- Inspect the kitchen
- Contact the food supplier
- Dispose of a food batch
- Call a doctor for affected students

**No action is ever automated. The human is always in the loop.**

## Git Commit Messages

1. `Initial project structure and specification`
2. `Implement LLM classification and safety validation`
3. `Add testing, reports and documentation`
