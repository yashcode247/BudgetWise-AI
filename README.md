# 📌 PIN PLAN — Financial Planning MVP

**CMU Hackathon · BudgetWise-AI**

An AI-assisted budget planner with a **Dedalus SDK**–powered assistant that uses **Tool Calling** for real financial logic (Paper Cut analyzer, Goal ETA), and a PR-ready setup for **CodeRabbit** reviews.

---

## Prize angles

- **Dedalus Tool Calling:** The AI assistant doesn’t just chat — it **calls tools**. Ask *“How much would I save if I quit Starbucks?”* and it uses `paper_cut_yearly_impact`. Ask *“When can I afford a car?”* and it uses `goal_eta` with your budget context.
- **CodeRabbit:** Open a Pull Request (e.g. from `feature/ai-integration`) to trigger CodeRabbit review. The repo has a clean structure and `.github/workflows/coderabbit.yml` for PR checks.

---

## Tech stack

| Layer            | Choice              |
|-----------------|---------------------|
| Frontend/Backend | **Streamlit** (Python) |
| AI orchestration | **Dedalus SDK** (Runner + Tool Calling) |
| Debug/Review     | **CodeRabbit** (PR reviews) |

---

## Quick start

1. **Clone and install**
   ```bash
   pip install -r requirements.txt
   ```

2. **API key (required for AI assistant)**  
   Create a `.env` file (do **not** commit it; use `load_dotenv`, never hardcode keys):
   ```bash
   DEDALUS_API_KEY=your_key_here
   ```
   Copy from `.env.example` if needed.

3. **Run the app**
   ```bash
   streamlit run app.py
   ```

---

## Features

1. **Budget Dashboard** — Income and expense inputs; **Monthly Savings** updates dynamically.
2. **Goal Tracker** — “Sort by Goals” (Home, Car, Vacation, School) with **ETA** to reach each goal from current savings.
3. **Paper Cut Analyzer** — Compare small recurring expenses (e.g. $4.50 Starbucks) vs alternatives (e.g. $0.20 home coffee); **yearly impact**.
4. **AI Assistant (Dedalus)** — Chat interface using Dedalus `Runner` with tools:
   - `paper_cut_yearly_impact` — yearly savings from switching an expense
   - `goal_eta` — months/date to reach a goal
   - `calculate_monthly_savings` — income minus expenses

---

## Project structure

```
BudgetWise-AI/
├── app.py              # Streamlit UI + Dedalus chat logic
├── utils.py            # Math + Dedalus tools (paper cut, goal ETA, savings)
├── requirements.txt    # streamlit, dedalus-labs, python-dotenv
├── .env.example        # Template for DEDALUS_API_KEY
├── .github/
│   └── workflows/
│       └── coderabbit.yml   # PR checks; CodeRabbit runs on PR when app installed
└── README.md
```

---

## Pushing for CodeRabbit

```bash
git checkout -b feature/ai-integration
git add .
git commit -m "feat: implement dedalus tool calling for financial analysis"
git push origin feature/ai-integration
```

Open a **Pull Request** on GitHub to trigger CodeRabbit.

---

## Notes

- **Keys:** Use `load_dotenv` and a `.env` file only; never hardcode `DEDALUS_API_KEY` in code.
- **Dedalus:** Official Python package is `dedalus-labs` (see [Dedalus SDK](https://docs.dedaluslabs.ai/sdk/quickstart)).
- **Modular:** Logic lives in `utils.py`; `app.py` handles UI and calling the Runner with those tools.
