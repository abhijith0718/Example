# Reflection

## What I Learned

Building the Mess Feedback Sorter taught me that using AI in a real project is not just about calling an API and trusting whatever comes back. The most important lesson was that AI output must always be validated and checked before it is used for any real decision. I learned how to structure a Python project properly, with separate functions for each task, proper error handling, and clear separation between what the AI does and what Python code handles.

I also learned about prompt engineering — writing a clear system prompt using the five-role framework (Authority, Exemplar, Constraint, Rubric, Metadata) made a significant difference in the quality of the LLM responses. Without a good prompt, the LLM would return inconsistent formats, wrong categories, or overly long summaries.

## How I Used an LLM

I used the Google Gemini API to classify each feedback comment into a category (taste, hygiene, quantity, timing, other), a sentiment (positive, negative, neutral), an urgency flag, and a short summary. The LLM was given a detailed system prompt with examples of correct JSON output. I set the temperature to a low value (0.2) so the responses would be more consistent and predictable. The LLM handled English, Tamil, and Tanglish comments, which would have been extremely difficult to do with simple keyword matching alone.

## What Problems I Faced

The biggest challenge was handling unreliable API responses. Sometimes the LLM would wrap its JSON in markdown code fences, return extra fields, or use string values instead of booleans. I had to write a validation function that checks every response against strict rules. Another problem was Tanglish — Tamil words written in English letters have no standard spelling, so "poochi" (insect) could be spelled in multiple ways. I addressed this by building a safety net with multiple keyword variants.

## Why AI Outputs Need Validation

An LLM is a probabilistic model, not a database lookup. It can produce different outputs for the same input, hallucinate information, or be tricked by prompt injection attacks. In a system where health safety is involved, we cannot afford to blindly trust the AI. The validation function and the retry logic ensure that only properly formatted, rule-compliant results make it into the final reports.

## Why the Safety Net Matters

The safety net is a simple keyword scanner that runs after the LLM classification. It exists because the LLM might miss a health-risk keyword, especially in Tanglish or Tamil. For example, "poochi" (insect) in a Tanglish sentence might not be recognized by the LLM. The safety net catches these cases and raises the urgency flag. It can only raise urgency, never lower it — this design ensures we never accidentally dismiss a real health risk.

## What I Learned About Human Responsibility

The most important design decision in this project is that the AI never takes action. The hostel warden reads every urgent comment and decides what to do. This taught me that in real-world applications, especially those involving health and safety, AI should assist humans, not replace them. The warden has context that the AI does not — they know the kitchen staff, the suppliers, and the history of past complaints.

## How This Project Can Help a Hostel Mess Committee

A hostel serving hundreds of students can receive dozens of feedback comments every day. Reading and sorting them manually is slow and tiring. This tool saves time by automatically categorizing complaints, highlighting the urgent ones, and generating a summary report. The mess committee can quickly see which areas need improvement (taste, hygiene, quantity, timing) and the warden gets an immediate alert about potential health risks. It supports comments in multiple languages, which is essential in a diverse Indian college setting.
