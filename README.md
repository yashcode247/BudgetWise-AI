# 📌 PIN PLAN

**CMU Hackathon · BudgetWise-AI** — Financial planning MVP with an AI assistant that **calls tools** (Dedalus SDK), not just chat.

---

## For judges

- **Dedalus Tool Calling:** Ask *"How much would I save if I quit Starbucks?"* → the assistant calls `paper_cut_yearly_impact`. *"When can I afford a car?"* → it calls `goal_eta`. Real functions, real numbers.
- **CodeRabbit:** PR-ready repo; `.github/workflows/coderabbit.yml` runs on PRs. Open a PR to trigger CodeRabbit review.
- **Stack:** Streamlit (UI) · Dedalus SDK (Runner + tools) · `utils.py` (paper cut, goal ETA, savings math).

---

## Run it

```bash
pip install -r requirements.txt
```

Add a `.env` with `DEDALUS_API_KEY=<your_key>` (copy from `.env.example`). Then:

```bash
py -m streamlit run app.py
```

---

## What’s in the app

| Feature | What it does |
|--------|----------------|
| **Dashboard** | Income & expenses → monthly savings (incl. negative when spending > income). |
| **Enter your income** | Dialog: set income/expenditure, see money saved. |
| **Paper cut Analyser** | Dialog: current habit vs alternative → yearly impact; name your habit, optional daily amount. |
| **GOAL** | Dialog: goal amounts (Home, Car, Vacation, School), sort by ETA or target, progress bars, goal vs salary. |
| **AI Assistant** | Dedalus Runner with tools above; uses your budget context. "Verify Dedalus key" tests the connection. |

---

## Repo layout

```
├── app.py           # Streamlit UI, dialogs, Dedalus chat
├── utils.py         # paper_cut_yearly_impact, goal_eta, calculate_monthly_savings (Dedalus tools)
├── requirements.txt
├── .env.example
├── .github/workflows/coderabbit.yml
└── docs/
```

Keys live in `.env` only (load_dotenv); never hardcoded.
