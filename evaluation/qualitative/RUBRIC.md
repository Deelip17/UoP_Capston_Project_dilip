# Qualitative review: clarity, completeness, actionability (ADR-040)

Purpose: one qualitative metric for Unit 6 Part B. A reviewer reads the framework's output (the HTML report of a run, and later the Dashboard) and rates it against three questions. No personal data and no client content is collected (ADR-005).

## What the reviewer is given

1. The report of the evaluation run (`report.html`, open it in a browser; no installation needed).
2. This sheet. About 15 minutes.

## The questions (score 1 to 5; 1 = poor, 3 = acceptable, 5 = very good; write a comment for every score of 2 or less)

| Id | Criterion | Question |
|---|---|---|
| Q1 | Clarity | Can you tell within one minute how many tests passed and failed, and what the main problem was? |
| Q2 | Completeness | Does the report give what you need to understand a failure (cause, evidence, screenshot, log) without asking someone? |
| Q3 | Actionability | For each failure, does the report say what to do next, and would you do it? |
| Q4 | Trust | Are the figures labelled clearly enough (mock or live, how each was computed) that you would trust them? |
| Q5 | Accessibility | Can you read it without colour alone, at a larger text size, and with the keyboard? (optional) |

## How to record

Fill in `ratings.csv`: one row per reviewer and question. Use a short reviewer code (R1, R2, ...), not a name. If you are the only reviewer, the result is a **self-review** and must be reported as one; a second reviewer makes it stronger. Reviewers must agree to take part (a verbal yes is recorded in the `consent` column as `yes`).

## How it is reported

Median and range per question, the number of reviewers, and every comment that explains a low score. The paper states who reviewed and what that means for validity.
