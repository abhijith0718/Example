# Judgment Framework

This table shows **who decides what** in the Mess Feedback Sorter system.

| System Component | What does AI (LLM) decide? | What does Python check/decide? | What must a Human decide? |
|---|---|---|---|
| **Category Classification** | The LLM reads the comment and picks one of: taste, hygiene, quantity, timing, other | Python validates that the category is one of the 5 allowed values. Rejects anything else. | The warden can override a wrong category after reading the original comment. |
| **Sentiment Classification** | The LLM judges the tone as positive, negative or neutral | Python validates the sentiment is one of the 3 allowed values | The warden interprets context the AI may miss (sarcasm, cultural tone) |
| **Urgent Flag** | The LLM decides if the comment describes a health risk (True/False) | Python validates urgent is a real boolean. The safety net independently scans for health-risk keywords and can RAISE urgency to True. Python never lowers urgency. | **THE WARDEN READS EVERY COMMENT IN urgent.csv.** The warden decides the actual action: inspect the kitchen, call a doctor, discard food, etc. |
| **Summary Generation** | The LLM writes a short summary (max 12 words) | Python checks the summary has ≤ 12 words | The warden reads the original comment, not just the summary, before acting |
| **Validation** | N/A | Python checks all 4 fields exist, no extra fields, correct types, allowed values. Invalid responses are retried once, then marked needs_manual_review | The warden or committee reviews needs_manual_review items manually |
| **Safety Net** | N/A | Python scans the original comment for health-risk keywords in English, Tamil and Tanglish. Can only raise urgency, never lower it | The warden uses the safety net flags as an extra alert, but still reads the original text |
| **Statistics** | N/A – the LLM never calculates any numbers | Python counts categories, sentiments, percentages and totals. All math is done in Python | The mess committee and warden interpret the statistics and decide on improvements |
| **Final Action** | N/A – the AI never takes action | N/A – the program never takes action | **The hostel warden decides all actions.** The AI is an assistant, not a decision maker |

## Most Important Human Checkpoint

> **THE WARDEN READS EVERY COMMENT IN `urgent.csv`.**
>
> The AI only flags possible health risks. The warden decides whether to:
> - Inspect the kitchen
> - Contact the food supplier
> - Dispose of a food batch
> - Call a doctor for affected students
> - Issue a warning to mess staff
>
> No action is ever automated. The human is always in the loop.
