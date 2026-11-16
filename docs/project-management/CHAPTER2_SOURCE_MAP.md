# Chapter 2 source map (Literature Review): what you read, what is missing, how to fill it

*Version 1.0 · 16 Nov 2026 · Companion to `CHAPTER2_LITERATURE_REVIEW.md` (skeleton) and `reference-library/MASTER_REFERENCES.md`. Plan: `knowledge/UNIT7_PLAN.md` section 11.*

**Purpose.** Chapter 2 of the Unit 7 report needs about **1,800 words** (3,000 in the final report) written only from sources you have read and verified. Today the skeleton cites 16 scholarly sources at **abstract level only**, and eight places say `[SOURCE NEEDED]`. This file tells you which sources to read in full, what to look for, which slots are empty, where to search, and how to verify a new source before it is cited.

## 1. O-10 in plain words

**O-10 = "How many sources beyond the course readings may the report use, and how deep should the literature review be?"** Two rules pull in different directions:

- **ADR-020 (your own rule):** course readings first; no new references unless a rubric requires them.
- **The Unit 7 instruction file:** "You may also locate and use additional sources provided you cite them according to APA with a correct and clickable link." The Part C rubric rewards "skillful use of high-quality, credible, relevant sources", and a literature review made only of tooling blogs would score poorly.

**Decision needed from you:** may Chapter 2 cite scholarly sources beyond the course readings? **Recommended answer: yes, up to about 10 additional sources, each verified by you** (link opens, details copied from the publisher record), on top of the 16 scholarly records already in the library. **Approved 16 Nov 2026 by the student** (ADR-050 accepted, O-10 resolved): up to 10 additional verified scholarly sources where needed to close identified gaps; each must be traceable, supported by the publisher record and cited in APA 7. Everything below assumes this.

## 2. Rules (they protect the grade and your integrity, ADR-009)

1. Cite a source only if you have read it (full text, or at least abstract, introduction, results and conclusion) and its record is `Verified` in `MASTER_REFERENCES.md`.
2. A sentence in Chapter 2 may say only what a source says. Keep a reading note for it (section 6). If you cannot point to the note, delete the sentence or mark it `[UNSUPPORTED]`.
3. **Never cite REF-Q01 to REF-Q04.** They are quarantined: the papers could not be found.
4. Say "in the sources reviewed", not "no one has done this".
5. Vendor pages are grey literature: label every claim "vendor-stated" and cite only pages you opened.
6. Copy DOI, volume, pages from the publisher or library record; never type them from memory. Give every reference a clickable link (DOI as `https://doi.org/...`).

## 3. Section-by-section map (Unit 7 word budget: 1,800)

| Section | Words | Sources already in the library (abstract-level use) | Empty slot or work needed |
|---|---|---|---|
| 2.1.1 Test automation and its maintenance burden | 180 | REF-107 Garousi and Mäntylä (2016): multivocal review on when and what to automate; REF-108 Rafi et al. (2012): systematic review plus practitioner survey, benefits and limits; REF-112 Nass et al. (2021): 49 publications, 24 GUI-automation challenges, four lasting about two decades. Course: REF-017 Rana, REF-018 AWS, REF-026 Hrupa, REF-027 BrowserStack (definitions of test cases, unit and system testing) | Read REF-107 and REF-112 in full; add one sentence connecting maintenance burden to locator fragility |
| 2.1.2 Web UI automation frameworks | 120 | REF-207 Playwright, REF-208 Selenium, REF-209 pytest (official documentation, URLs to test) | **Slot S1** official-documentation comparison; optional empirical study (S2). No performance claims without a source |
| 2.1.3 AI and LLMs in software testing | 260 | REF-101 Wang et al. (2024): survey of 102 studies, test case preparation and program repair most representative (preprint); REF-102 Hou et al. (2024): 395 articles on LLMs in software engineering; REF-103 Schäfer et al. (2023): LLM unit-test generator, 70.2% statement and 52.8% branch coverage on 25 npm packages (preprint); REF-104 Fontes and Gay (2023); REF-105 Durelli et al. (2019); REF-106 Trudova et al. (2020): 34 studies, nine activities | Read REF-101 in full; skim REF-102 and REF-103; state that two of these are preprints |
| 2.1.4 From requirements to tests | 180 | Course: REF-008 Letaw (2024), REF-006 Summers (2020) on requirements | **Slot S3** a verified requirements-to-test generation study (search terms below) |
| 2.1.5 Locator fragility and self-healing | 230 | REF-109 Leotta et al. (2015): multi-locators for robustness; REF-110 Hammoudi et al. (2016): why record/replay tests break (**DOI pending**); REF-111 Stocco et al. (2018): visual web test repair | Read REF-109 and REF-111 in full (core to the project); **Slot S4** vendor documentation for commercial self-healing, vendor-stated only |
| 2.1.6 Failure analysis and intelligent reporting | 170 | REF-113 Luo et al. (2014): causes of flaky tests; REF-114 Parry et al. (2022): survey of 76 papers on flaky tests | Read REF-114 in full; **Slot S5** a failure-triage or log-analysis study |
| 2.1.7 Enterprise QA context | 150 | REF-115 Shahin et al. (2017): 69 papers on CI, delivery and deployment, 30 approaches. Course: REF-001 Oguz, REF-011 Parzych, REF-012 Narasimhan et al., REF-013 Red Hat | Skim REF-115; tie to the project's CI/CD in Chapter 3 |
| 2.1.8 Trust, security and governance of AI-assisted testing | 160 | REF-201 NIST AI RMF (2023), REF-202 NIST CSF 2.0 (2024), REF-203 OWASP Top 10 for LLM applications (**edition to be chosen**), REF-204 OWASP Top 10, REF-205 GDPR, REF-206 ISO/IEC 27001 | **Slot S6** pick the OWASP edition, test every URL, describe them as guidance, not compliance |
| 2.2 Comparative analysis (Table 2 plus paragraph) | 200 | Table 2 columns from the skeleton | Fill each cell only with a cited statement; otherwise "not assessed"; **Slot S4** for the commercial row; write the 150 to 200 word paragraph |
| 2.3 Research gap | 150 | Provisional gaps G1 to G4 in the skeleton | Confirm each gap against what you read; keep "in the sources reviewed" |
| **Total** | **1,800** | | |

Not for Chapter 2: REF-116 Hevner et al. (2004), design science (use in the Chapter 3 method section if at all); REF-028 Miller and the maintenance readings REF-029 and REF-030 belong to Chapter 5.3 and Part B.

## 4. Reading list and what each full text must tell you

**A. Read in full (about 4 to 5 hours).** Answer the questions in your reading note (section 6).

| ID | Source | Questions to answer from the text |
|---|---|---|
| REF-101 | Wang et al. (2024), software testing with LLMs, survey | Which testing tasks were studied and how often? Which prompt or fine-tuning approaches? Which challenges and gaps do the authors state? Does any study cover a full requirements-to-report pipeline? |
| REF-107 | Garousi and Mäntylä (2016), when and what to automate | Which factors favour or oppose automation? What do practitioners report about maintenance cost? |
| REF-109 | Leotta et al. (2015), multi-locators | What locator strategies were compared? How was robustness measured? What did they not address (generation, failure analysis)? |
| REF-111 | Stocco et al. (2018), visual web test repair | What kinds of breakage does the approach repair? How were results measured? Limits the authors state? |
| REF-114 | Parry et al. (2022), flaky test survey | How are flaky tests defined and classified? Which causes and detection methods? What is said about distinguishing flaky from real failures? |
| REF-112 | Nass et al. (2021), GUI test automation challenges | Which of the 24 challenges relate to maintenance and locators? Which ones persisted? |

**B. Skim (about 1.5 hours): abstract, introduction, results, conclusion.**
REF-102 Hou, REF-103 Schäfer, REF-108 Rafi, REF-110 Hammoudi, REF-113 Luo, REF-115 Shahin, REF-104 Fontes and Gay, REF-105 Durelli, REF-106 Trudova.

**C. Documents, not papers:** REF-201 to REF-215. You need the page open, the edition or version, and an access date; you do not need to read them fully.

## 5. Empty slots (S1 to S8): what to find, where, how to verify

| Slot | Needed | Search terms to try | Where |
|---|---|---|---|
| S1 | Selenium and Playwright from official documentation (architecture, browser support, auto-waiting) | the two documentation sites (REF-208 and REF-207) | official sites; record the access date |
| S2 | Optional: an empirical comparison of web UI automation tools | "empirical comparison Selenium Playwright Cypress", "web test automation tools comparison study" | Google Scholar, ACM DL, IEEE Xplore |
| S3 | A study on generating test cases from requirements or user stories, ideally with LLMs | "LLM generate test cases from natural language requirements", "requirements-based test generation large language model", "test generation from user stories" | UoP library, Google Scholar, arXiv (flag preprints) |
| S4 | Vendor documentation for self-healing in commercial or open-source tools (examples of names to look up: Healenium, mabl, Testim, Katalon, Applitools; use whichever has a public page that opens) | "self-healing tests documentation", the vendor's own docs | vendor sites; label vendor-stated; no performance claims |
| S5 | A study on automatic triage or classification of test failures from logs | "automated test failure triage", "test failure classification root cause continuous integration", "log analysis test failures machine learning" | UoP library, Google Scholar, ACM, IEEE |
| S6 | OWASP Top 10 for LLM applications (choose the edition), NIST AI RMF, NIST CSF 2.0 | the official project pages (REF-203, REF-201, REF-202) | official sites; record edition and access date |
| S7 | Numbers reported in the literature that you can compare with your results in Chapter 5.2 (for example repair or robustness results from Leotta and Stocco, coverage from Schäfer) | taken from sources you already read | your reading notes; state that studies differ in setting, so the numbers are context, not a ranking |
| S8 | Confirm the five Unit 7 course readings (REF-026 to REF-030) say what the notes claim | read them | course materials |

**Selection criteria for a new source:** relevant to one of the gaps G1 to G4; peer-reviewed, or a widely cited preprint clearly labelled; 2018 to 2025 unless it is foundational; English; you can open the full text.

**Verification checklist (do all six before a source is cited):**
1. Open the link or DOI; it must load.
2. Copy the citation details from the publisher or library record (authors, year, title, venue, volume, pages, DOI); do not retype from memory.
3. Check that title, authors and year match what you read.
4. Note whether it is peer-reviewed or a preprint.
5. Add it to `MASTER_REFERENCES.md` as the next number (REF-117 onward) with status `Verified – Record checked` and the date; tell me and I will add it.
6. Add its reading note.

**To-do on existing records:** REF-110 (copy the DOI), REF-203 and REF-204 (choose the edition), REF-201, REF-202, REF-205 to REF-215 (test each URL and write the access date), REF-207 (confirm the Playwright Python page or the main documentation site).

## 6. Reading note template (one per source; keep them in `final-report/CHAPTER2_READING_NOTES.md`)

```text
REF-nnn  Author (year). Short title.
Read: full text / skim.   Date read: ...   Peer-reviewed or preprint: ...
Question the authors ask:
Method and data (with size or scope):
Key findings (with section or page): 1) ...  2) ...
Limits the authors state:
Relevance to my project (gap G1 / G2 / G3 / G4, or 2.1.x):
One sentence I may write, and the section or page that supports it:
Anything I could NOT confirm:
```

## 7. Chapter 5.2 link

Chapter 5.2 compares your results with the literature. Collect, while you read, two or three numbers or statements that your results can sit next to (slot S7). Write each as "Study X reported ...; my evaluation found ...; the settings differ in ...". Never rank your system against a study.

## 8. After you finish reading

1. Send me the reading notes file and the new source details; I add the references to the library and update the skeleton.
2. Cowork writes the 1,800-word Chapter 2 from the notes only, with an "unsupported sentences" list.
3. You trace each citation to a note line and sign off (about 1.5 hours), then commit Chapter 2 as v2.0.

## 9. Decision of 16 Nov 2026: only two new sources for now (one per gap)

**Scope for the Unit 7 version:** one new scholarly source for S3 (requirements to tests) and one for S5 (failure triage). S2 (empirical tool comparison) and S4 (vendor pages) are skipped for now: Table 2 says "not assessed" in the commercial row and 2.1.2 relies on the official documentation (S1). The 1,800-word budget does not need more. Add more only if the author wants a deeper Chapter 2 for Unit 8.

**Suggested sources that were checked and rejected (do not use for these slots):**
- Leotta, Clerissi, Ricca and Spadaro, "Capture-replay vs. programmable web testing", ICST 2015, pp. 1-10: **the details are wrong.** The paper found is Leotta, Clerissi, Ricca and Tonella (2013), *Capture-Replay vs. Programmable Web Testing: An Empirical Assessment during Test Case Evolution*, 20th Working Conference on Reverse Engineering (WCRE 2013), pp. 272-281. It compares the cost of capture-replay and programmable web tests over releases; it is **not** about requirements-to-test generation or AI-assisted creation. It could support 2.1.1 or 2.1.5 (maintenance cost) if wanted, with the corrected citation, but it does not fill S3.
- Garousi and Mäntylä (2016): **already REF-107.** It is a review of when and what to automate; the recorded abstract does not mention defect triage, so it does not fill S5.

**Candidates found by web search (snippets only, NOT yet verified: open each page, read the paper, copy the record, then tell me):**

| Slot | Candidate | Why it fits | Check before citing |
|---|---|---|---|
| S3 (recommended) | Korraprolu et al. (2025), *Test Case Generation for Requirements in Natural Language: An LLM Comparison Study*, ISEC 2025 (peer-reviewed conference). https://conf.researchr.org/details/isec-2025/isec-2025-papers/7/Test-Case-Generation-for-Requirements-in-Natural-Language-An-LLM-Comparison-Study | Compares six general-purpose LLMs generating tests from natural-language requirements, validated with coverage | Full author list, DOI and pages from the ACM record; its domain is technical requirements checked on a Simulink model, so say it is not web UI testing |
| S3 alternative | arXiv 2412.03693, ChatGPT-4o test case design from SRS documents across five projects (preprint). https://arxiv.org/abs/2412.03693v1 | Reports that about 15% of valid generated tests had not been considered by the developers | Peer-review status; exact title and authors |
| S5 (recommended) | Zhang et al. (2022), *BuildSheriff: Change-aware test failure triage for continuous-integration builds*, ICSE 2022 (peer-reviewed). https://chenbihuan.github.io/paper/icse22-zhang-buildsheriff.pdf | Empirical study of 163,371 broken builds from 1,337 GitHub Java projects; groups test failures that share a root cause, which parallels the project's failure clustering (FR-29) | Exact title, authors, DOI and pages from the ACM or IEEE record; it targets Java CI builds, not UI tests, so say so |
| S5 alternative | arXiv 2111.03382, Discerning legitimate failures from false alerts: Chromium's CI (preprint). https://arxiv.org/pdf/2111.03382 | Classifier over more than 1 million test failures | Whether it was peer-reviewed; exact record |
| S5 alternative | arXiv 2601.22264, FlaXifyer, few-shot fine-tuned language models on job logs (FSE 2026 industry track). https://arxiv.org/abs/2601.22264v1 | Failure-category prediction from logs with language models | Peer-review status; very recent |

Choose one per slot, read it, fill the reading note, then give me the verified record and I add REF-117 and REF-118.
