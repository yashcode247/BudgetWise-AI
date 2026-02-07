"""
PIN PLAN - Financial planning MVP.
Streamlit UI: Budget Dashboard, Goal Tracker, Paper Cut Analyzer, AI Assistant (Dedalus).
Keys are loaded via load_dotenv; do not hardcode API keys.
"""

import asyncio
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from utils import (
    GOAL_CATEGORIES,
    calculate_monthly_savings,
    goal_eta,
    paper_cut_yearly_impact,
)

# Load environment variables (DEDALUS_API_KEY); never hardcode keys.
load_dotenv()


# ---------------------------------------------------------------------------
# Page config and session state
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PIN PLAN | Financial Planning",
    page_icon="📌",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "income" not in st.session_state:
    st.session_state.income = 0.0
if "expenses" not in st.session_state:
    st.session_state.expenses = 0.0
if "goals" not in st.session_state:
    st.session_state.goals = {g: 0.0 for g in GOAL_CATEGORIES}
if "current_savings" not in st.session_state:
    st.session_state.current_savings = 0.0


# ---------------------------------------------------------------------------
# Dedalus Runner + tools
# ---------------------------------------------------------------------------
def run_ai_assistant(user_message: str, budget_context: str) -> str:
    """
    Run Dedalus Runner with Paper Cut and Goal ETA tools.
    Passes budget context so the AI can call tools with current numbers.
    """
    from dedalus_labs import AsyncDedalus, DedalusRunner
    import os

    api_key = os.environ.get("DEDALUS_API_KEY")
    if not api_key:
        return "⚠️ DEDALUS_API_KEY is not set. Add it to your `.env` file and restart the app."

    async def _run():
        client = AsyncDedalus()
        runner = DedalusRunner(client)
        prompt = (
            f"Current user budget context (use these numbers when calling tools):\n{budget_context}\n\n"
            f"User question: {user_message}\n\n"
            "Use the tools when relevant: e.g. for 'how much would I save if I quit Starbucks?' "
            "call paper_cut_yearly_impact; for 'when can I afford X?' call goal_eta. "
            "Reply in a short, helpful way and include the numbers from the tools."
        )
        response = await runner.run(
            input=prompt,
            model="anthropic/claude-sonnet-4-20250514",
            tools=[paper_cut_yearly_impact, goal_eta, calculate_monthly_savings],
        )
        return response.final_output or "No response."

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# Sidebar: Budget inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📌 Budget inputs")
    st.session_state.income = st.number_input(
        "Monthly income ($)",
        min_value=0.0,
        value=float(st.session_state.income),
        step=100.0,
        key="income_input",
    )
    st.session_state.expenses = st.number_input(
        "Monthly expenses ($)",
        min_value=0.0,
        value=float(st.session_state.expenses),
        step=50.0,
        key="expenses_input",
    )
    monthly_savings = calculate_monthly_savings(
        st.session_state.income, st.session_state.expenses
    )
    st.metric("Monthly savings", f"${monthly_savings:,.2f}")
    st.session_state.current_savings = st.number_input(
        "Current total savings ($)",
        min_value=0.0,
        value=float(st.session_state.current_savings),
        step=500.0,
        key="savings_input",
    )
    st.divider()
    st.markdown("### 🎯 Goal amounts")
    for g in GOAL_CATEGORIES:
        st.session_state.goals[g] = st.number_input(
            f"{g} ($)",
            min_value=0.0,
            value=float(st.session_state.goals.get(g, 0)),
            step=1000.0,
            key=f"goal_{g}",
        )


# ---------------------------------------------------------------------------
# Main: Title and layout
# ---------------------------------------------------------------------------
st.title("📌 PIN PLAN")
st.caption("Financial planning MVP — Budget, goals, paper cuts, and AI assistant.")

# Build context string for the AI (so it can call tools with current data)
budget_context = (
    f"Income: ${st.session_state.income:,.2f}, Expenses: ${st.session_state.expenses:,.2f}, "
    f"Monthly savings: ${monthly_savings:,.2f}, Current savings: ${st.session_state.current_savings:,.2f}. "
    f"Goals: " + ", ".join(f"{k} ${v:,.0f}" for k, v in st.session_state.goals.items())
)


# ---------------------------------------------------------------------------
# Section 1: Budget Dashboard
# ---------------------------------------------------------------------------
st.header("Budget Dashboard")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Monthly income", f"${st.session_state.income:,.2f}")
with col2:
    st.metric("Monthly expenses", f"${st.session_state.expenses:,.2f}")
with col3:
    st.metric("Monthly savings", f"${monthly_savings:,.2f}")
st.divider()


# ---------------------------------------------------------------------------
# Section 2: Goal Tracker (Sort by Goals)
# ---------------------------------------------------------------------------
st.header("Sort by Goals")
st.caption("ETAs based on current savings and monthly savings.")

goal_cols = st.columns(len(GOAL_CATEGORIES))
for i, goal_name in enumerate(GOAL_CATEGORIES):
    target = st.session_state.goals.get(goal_name, 0)
    eta_result = goal_eta(
        goal_amount=target,
        current_savings=st.session_state.current_savings,
        monthly_savings=monthly_savings,
        goal_name=goal_name,
    )
    with goal_cols[i]:
        st.subheader(goal_name)
        st.write(f"Target: ${target:,.0f}")
        st.write(eta_result["message"])
        if eta_result.get("eta_date"):
            st.caption(f"ETA: ~{eta_result['eta_date']}")
st.divider()


# ---------------------------------------------------------------------------
# Section 3: Paper Cut Analyzer
# ---------------------------------------------------------------------------
st.header("Paper Cut Analyzer")
st.caption("Compare small recurring expenses vs alternatives — yearly impact.")

pc_col1, pc_col2 = st.columns(2)
with pc_col1:
    current_exp = st.number_input(
        "Current expense per occurrence ($)",
        min_value=0.0,
        value=4.50,
        step=0.5,
        key="pc_current",
    )
    freq = st.number_input(
        "Times per week",
        min_value=0.0,
        value=5.0,
        step=0.5,
        key="pc_freq",
    )
with pc_col2:
    alt_exp = st.number_input(
        "Alternative expense per occurrence ($)",
        min_value=0.0,
        value=0.20,
        step=0.1,
        key="pc_alt",
    )
    pc_label = st.text_input("Label (e.g. Starbucks → home coffee)", value="")

result = paper_cut_yearly_impact(current_exp, alt_exp, freq, pc_label)
st.success(
    f"**Yearly impact:** You spend **${result['yearly_current']:,.2f}** now → "
    f"**${result['yearly_alternative']:,.2f}** with alternative → "
    f"**Save ${result['yearly_savings']:,.2f}/year**."
)
st.divider()


# ---------------------------------------------------------------------------
# Section 4: AI Assistant (Dedalus Tool Calling)
# ---------------------------------------------------------------------------
st.header("AI Assistant")
st.caption(
    "Ask about savings or goals. The AI uses Tool Calling (Paper Cut & Goal ETA) — e.g. "
    '"How much would I save if I quit Starbucks?" or "When can I afford a car?"'
)

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about your budget, goals, or paper cuts..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = run_ai_assistant(prompt, budget_context)
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
