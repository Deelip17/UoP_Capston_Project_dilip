# Developer Setup (Windows)

Covers a clean machine to a working environment. Related: NFR-26 (Windows and Linux, Python 3.12), NFR-27 (install in 15 minutes or less), NFR-09 (API key from the environment only).

## 1. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.12 | `python --version` |
| Git | recent | `git --version` |
| Google Chrome | current (for Selenium) | installed in `Program Files` |
| VS Code with the Python extension | current | optional |

## 2. Create the environment (inside the repository, never in OneDrive)

```text
cd C:\Users\dchennap\repos\UoP_Capston_Project_dilip
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
playwright install chromium
```

`.venv` is git-ignored. In VS Code choose **Python: Select Interpreter** and pick `.venv\Scripts\python.exe` of this repository.

## 3. Verify

```text
python --version
pytest --version
python -c "import playwright, selenium, openai, pandas, sqlite3; print('imports ok')"
```

## 4. OpenAI API key (live LLM calls only; tests and CI use the mock provider)

1. Create or sign in to an account at the OpenAI platform and open the API keys page.
2. Open **Billing**, add a small prepaid credit, and set a **monthly budget limit of $5** with an email alert at a lower threshold (project budget policy ADR-026). Turn automatic top-up off.
3. Create a project-scoped key named `capstone-demo` (restricted permissions if offered, only the model endpoints needed). Copy it once.
4. Store it as a **user environment variable**, not in any file: PowerShell `setx OPENAI_API_KEY "paste-key-here"`, then **close and reopen** VS Code and every terminal so the variable loads.
5. Check without printing the key: `python -c "import os; print('key set' if os.environ.get('OPENAI_API_KEY') else 'key missing')"`.
6. Never paste the key into chat, code, `.env` files committed to Git, screenshots, logs or reports. If it leaks, delete it on the API keys page and create a new one.

## 5. Playwright and Selenium notes

- Playwright stores browsers per user, outside the repository; `playwright install chromium` downloads only what the installed Playwright version expects.
- Selenium 4 downloads a matching driver automatically (Selenium Manager); Chrome must be installed.
- Test only against public demonstration applications.

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| `python` points to another environment | Activate `.venv`, or run `.venv\Scripts\python.exe` directly |
| `playwright` browser missing | `playwright install chromium` |
| Key not found after `setx` | Restart VS Code and terminals; `setx` affects new processes only |
| Long path or sync errors | Keep the repository and `.venv` outside OneDrive |
