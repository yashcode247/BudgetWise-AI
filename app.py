"""
PIN PLAN - Financial planning MVP.
Streamlit UI: Budget Dashboard, Goal Tracker, Paper Cut Analyzer, AI Assistant (Dedalus).
Keys are loaded via load_dotenv; do not hardcode API keys.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from utils import (
    GOAL_CATEGORIES,
    calculate_monthly_savings,
    goal_eta,
    paper_cut_yearly_impact,
)

# Load .env from the app's directory first, then cwd as fallback (so key is always found).
_app_dir = Path(__file__).resolve().parent
load_dotenv(_app_dir / ".env")
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
# Which dialog is open (None = dashboard only, "income" | "papercut" | "goal")
if "open_dialog" not in st.session_state:
    st.session_state.open_dialog = None


# ---------------------------------------------------------------------------
# Dedalus Runner + tools
# ---------------------------------------------------------------------------
def _get_dedalus_api_key() -> str:
    """Get Dedalus API key: try env, then load .env from app dir and cwd, then parse file directly."""
    from dotenv import dotenv_values
    for env_path in [_app_dir / ".env", Path.cwd() / ".env"]:
        p = env_path.resolve()
        if p.exists():
            load_dotenv(p)
    load_dotenv()
    key = (os.environ.get("DEDALUS_API_KEY") or "").strip()
    if not key:
        for env_path in [_app_dir / ".env", Path.cwd() / ".env"]:
            p = env_path.resolve()
            if p.exists():
                try:
                    vals = dotenv_values(p)
                    key = (vals.get("DEDALUS_API_KEY") or "").strip()
                    if key:
                        os.environ["DEDALUS_API_KEY"] = key
                        break
                except Exception:
                    pass
            if key:
                break
    if not key:
        for env_path in [_app_dir / ".env", Path.cwd() / ".env"]:
            p = env_path.resolve()
            if p.exists():
                try:
                    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                        s = line.strip()
                        if s.startswith("DEDALUS_API_KEY="):
                            key = s.split("=", 1)[1].strip().strip('"').strip("'").split("#")[0].strip()
                            if key:
                                os.environ["DEDALUS_API_KEY"] = key
                                break
                except Exception:
                    pass
            if key:
                break
    if not key or key.lower() in ("your_key_here", "your_actual_key_here"):
        return ""
    return key


def run_ai_assistant(user_message: str, budget_context: str) -> str:
    """
    Run Dedalus Runner with Paper Cut and Goal ETA tools.
    Passes budget context so the AI can call tools with current numbers.
    Uses explicit API key, tries fallback models on 500.
    """
    from dedalus_labs import AsyncDedalus, DedalusRunner
    from dedalus_labs import (
        InternalServerError,
        APIConnectionError,
        RateLimitError,
        APIError,
    )

    api_key = _get_dedalus_api_key()
    if not api_key:
        return "⚠️ DEDALUS_API_KEY is not set or still placeholder. Add your real key to `.env` in the project folder and restart the app."

    # Models to try in order (500 = server error; try Dedalus-docs model first)
    models_to_try = [
        "anthropic/claude-opus-4-6",
        "anthropic/claude-sonnet-4",
        "anthropic/claude-3-5-sonnet-latest",
    ]
    prompt = (
        f"Current user budget context (use these numbers when calling tools):\n{budget_context}\n\n"
        f"User question: {user_message}\n\n"
        "Use the tools when relevant: e.g. for 'how much would I save if I quit Starbucks?' "
        "call paper_cut_yearly_impact; for 'when can I afford X?' call goal_eta. "
        "Reply in a short, helpful way and include the numbers from the tools."
    )
    tools = [paper_cut_yearly_impact, goal_eta, calculate_monthly_savings]

    async def _run(model: str):
        client = AsyncDedalus(api_key=api_key)
        runner = DedalusRunner(client)
        response = await runner.run(input=prompt, model=model, tools=tools)
        return response.final_output or "No response."

    last_error = None
    for model in models_to_try:
        try:
            return asyncio.run(_run(model))
        except InternalServerError as e:
            last_error = e
            continue
        except RateLimitError:
            return "⚠️ Rate limit reached. Please wait a minute and try again."
        except APIConnectionError:
            return "⚠️ Could not reach Dedalus. Check your internet connection and try again."
        except APIError as e:
            return f"⚠️ API error: {getattr(e, 'message', str(e))}. Try again or check your API key."
        except Exception as e:
            return f"⚠️ Something went wrong: {e}. Try again or check the console for details."

    return (
        "⚠️ Dedalus API returned server errors for all models tried. "
        "Please try again in a few minutes or contact support@dedaluslabs.ai."
    )


# ---------------------------------------------------------------------------
# Dialog: Enter your income
# ---------------------------------------------------------------------------
@st.dialog("Enter your income", width="large", dismissible=False)
def dialog_income():
    if st.button("← Back to dashboard", key="back_income"):
        st.session_state.open_dialog = None
        st.rerun()
    st.caption("Set income and expenditure. Money saved = Income − Expenditure.")
    st.session_state.income = st.number_input(
        "Monthly income ($)",
        min_value=0.0,
        value=float(st.session_state.income),
        step=100.0,
        key="dlg_income",
    )
    st.session_state.expenses = st.number_input(
        "Monthly expenses ($)",
        min_value=0.0,
        value=float(st.session_state.expenses),
        step=50.0,
        key="dlg_expenses",
    )
    x, y = st.session_state.income, st.session_state.expenses
    money_saved_display = x - y
    col_x, col_y = st.columns(2)
    with col_x:
        st.metric("Income", f"$ {x:,.2f}")
    with col_y:
        st.metric("Expenditure", f"$ {y:,.2f}")
    st.markdown("**Money saved** = Income − Expenditure")
    if money_saved_display < 0:
        st.warning(f"**Money saved = ${money_saved_display:,.2f}** (negative — expenditure is greater than income)")
    else:
        st.success(f"**Money saved = ${money_saved_display:,.2f}**")


# ---------------------------------------------------------------------------
# Dialog: Paper cut Analyser
# ---------------------------------------------------------------------------
@st.dialog("Paper cut Analyser", width="large", dismissible=False)
def dialog_papercut():
    if st.button("← Back to dashboard", key="back_papercut"):
        st.session_state.open_dialog = None
        st.rerun()
    st.caption("Compare small recurring expenses vs alternatives. Name your habit and see yearly impact.")
    with st.expander("How it works", expanded=False):
        st.markdown(
            "Enter **per occurrence** and how often per week, or use **daily amount**. "
            "Then enter the **alternative** cost. We compute the yearly impact."
        )
    habit_name = st.text_input(
        "Name this habit",
        value="",
        placeholder="e.g. Starbucks coffee, Lunch out",
        key="dlg_pc_habit_name",
    )
    habit_label = habit_name.strip() if habit_name else "Current habit"
    use_daily = st.checkbox("Enter current habit as daily amount ($) instead of per occurrence × times/week", key="dlg_pc_use_daily")
    pc_col1, pc_col2 = st.columns(2)
    with pc_col1:
        st.markdown(f"**{habit_label}**")
        if use_daily:
            daily_amount = st.number_input(
                "Daily amount ($)",
                min_value=0.0,
                value=3.21,
                step=0.25,
                key="dlg_pc_daily",
            )
            yearly_from_daily = daily_amount * 365.0
            current_exp = daily_amount
            freq = 7.0 if daily_amount else 0.0
        else:
            current_exp = st.number_input(
                "Cost per occurrence ($)",
                min_value=0.0,
                value=4.50,
                step=0.5,
                key="dlg_pc_current",
            )
            freq = st.number_input(
                "Times per week",
                min_value=0.0,
                value=5.0,
                step=0.5,
                key="dlg_pc_freq",
            )
            yearly_from_daily = None
    with pc_col2:
        st.markdown("**Alternative**")
        alt_exp = st.number_input(
            "Cost per occurrence ($)",
            min_value=0.0,
            value=0.20,
            step=0.1,
            key="dlg_pc_alt",
        )
        if use_daily:
            alt_freq = st.number_input(
                "Times per week",
                min_value=0.0,
                value=5.0,
                step=0.5,
                key="dlg_pc_alt_freq",
            )
        else:
            alt_freq = freq
        pc_label = st.text_input("Label (optional)", value="", placeholder="e.g. Starbucks → home coffee", key="dlg_pc_label")
    if use_daily and yearly_from_daily is not None:
        yearly_alt = alt_exp * alt_freq * 52.0
        result = {
            "yearly_current": round(yearly_from_daily, 2),
            "yearly_alternative": round(yearly_alt, 2),
            "yearly_savings": round(yearly_from_daily - yearly_alt, 2),
            "description": pc_label or habit_label,
        }
    else:
        result = paper_cut_yearly_impact(current_exp, alt_exp, freq, pc_label or habit_label)
    daily_current = result["yearly_current"] / 365.0
    weekly_current = result["yearly_current"] / 52.0
    weekly_alt = result["yearly_alternative"] / 52.0
    monthly_savings_pc = (result["yearly_savings"] / 12) if result["yearly_savings"] else 0
    st.markdown("---")
    st.markdown("### 📊 Impact")
    comp1, comp2, comp3 = st.columns(3)
    with comp1:
        st.metric(
            f"{habit_label} (year)",
            f"${result['yearly_current']:,.2f}",
            help=f"~${daily_current:,.2f}/day · ~${weekly_current:,.2f}/week",
        )
    with comp2:
        st.metric("With alternative (year)", f"${result['yearly_alternative']:,.2f}", help=f"~${weekly_alt:,.2f}/week")
    with comp3:
        st.metric("You save (year)", f"${result['yearly_savings']:,.2f}", help=f"~${monthly_savings_pc:,.2f}/month")
    st.success(
        f"**Yearly impact:** You spend **${result['yearly_current']:,.2f}** on **{habit_label}** now → "
        f"**${result['yearly_alternative']:,.2f}** with alternative → **Save ${result['yearly_savings']:,.2f}/year**."
    )


# ---------------------------------------------------------------------------
# Dialog: GOAL (Sort by Goals)
# ---------------------------------------------------------------------------
@st.dialog("GOAL — Sort by Goals", width="large", dismissible=False)
def dialog_goal():
    if st.button("← Back to dashboard", key="back_goal"):
        st.session_state.open_dialog = None
        st.rerun()
    st.caption("Set goal amounts below. We compare each goal to your monthly income and show if it’s attainable.")
    monthly_income = st.session_state.income
    monthly_savings_dlg = calculate_monthly_savings(st.session_state.income, st.session_state.expenses)
    current = st.session_state.current_savings

    # Goal amount input boxes (moved from sidebar)
    st.markdown("### 🎯 Goal amounts")
    goal_input_cols = st.columns(len(GOAL_CATEGORIES))
    for i, g in enumerate(GOAL_CATEGORIES):
        with goal_input_cols[i]:
            st.session_state.goals[g] = st.number_input(
                f"{g} ($)",
                min_value=0.0,
                value=float(st.session_state.goals.get(g, 0)),
                step=1000.0,
                key=f"dlg_goal_{g}",
            )
    st.markdown("---")

    # Compare goals to salary (attainability)
    if monthly_income > 0:
        st.markdown("### 📊 Goal vs salary")
        st.caption("How each goal compares to your monthly income; ETAs use your current savings and monthly savings.")
    sort_option = st.selectbox(
        "Sort by",
        ["Default (Home, Car, Vacation, School)", "Soonest ETA first", "Target amount (low → high)", "Target amount (high → low)"],
        key="dlg_goal_sort",
    )
    goals_data = []
    for goal_name in GOAL_CATEGORIES:
        target = st.session_state.goals.get(goal_name, 0)
        eta_result = goal_eta(
            goal_amount=target,
            current_savings=current,
            monthly_savings=monthly_savings_dlg,
            goal_name=goal_name,
        )
        # Compare goal to salary: months of income, and attainability note
        months_of_income = (target / monthly_income) if monthly_income > 0 and target > 0 else None
        goals_data.append((goal_name, target, eta_result, months_of_income))
    if "Soonest ETA first" in sort_option:
        def eta_months(item):
            name, target, eta, _ = item
            m = eta.get("months_needed")
            return m if m is not None else float("inf")
        goals_data.sort(key=eta_months)
    elif "Target amount (low → high)" in sort_option:
        goals_data.sort(key=lambda x: x[1])
    elif "Target amount (high → low)" in sort_option:
        goals_data.sort(key=lambda x: x[1], reverse=True)
    goal_cols = st.columns(len(goals_data))
    for i, (goal_name, target, eta_result, months_of_income) in enumerate(goals_data):
        with goal_cols[i]:
            st.subheader(goal_name)
            st.write(f"Target: **${target:,.0f}**")
            if monthly_income > 0 and target > 0 and months_of_income is not None:
                st.caption(f"= **{months_of_income:.1f}×** your monthly income")
                if months_of_income <= 6:
                    st.success("Within reach (≤ 6 months of income)")
                elif months_of_income <= 24:
                    st.info("Attainable (≤ 2 years of income)")
                else:
                    st.warning("Large goal — save consistently to reach it")
            if target > 0:
                progress_pct = min(100.0, (current / target) * 100.0)
                st.progress(progress_pct / 100.0)
                st.caption(f"{progress_pct:.0f}% of goal · ${max(0, target - current):,.0f} to go")
            st.write(eta_result["message"])
            if eta_result.get("eta_date"):
                st.caption(f"ETA: ~{eta_result['eta_date']}")
            elif not eta_result.get("reachable", True) or eta_result.get("months_needed") is None:
                st.caption("Increase monthly savings to see an ETA.")


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


# Build context string for the AI (so it can call tools with current data)
budget_context = (
    f"Income: ${st.session_state.income:,.2f}, Expenses: ${st.session_state.expenses:,.2f}, "
    f"Monthly savings: ${monthly_savings:,.2f}, Current savings: ${st.session_state.current_savings:,.2f}. "
    f"Goals: " + ", ".join(f"{k} ${v:,.0f}" for k, v in st.session_state.goals.items())
)


# ---------------------------------------------------------------------------
# Home Screen: PIN PLAN + three cards
# ---------------------------------------------------------------------------
st.markdown("# 📌 PIN PLAN")
st.caption("Home Screen — choose an option below.")
st.markdown("---")

# Three cards in a row (like the sketch: enter your income | Paper cut Analyser | GOAL)
card1, card2, card3 = st.columns(3)
with card1:
    with st.container():
        st.markdown("**Enter your income**")
        st.caption("Income, expenditure & money saved")
        if st.button("Open →", key="btn_income"):
            st.session_state.open_dialog = "income"
            st.rerun()
with card2:
    with st.container():
        st.markdown("**Paper cut Analyser**")
        st.caption("Small expenses vs alternatives")
        if st.button("Open →", key="btn_papercut"):
            st.session_state.open_dialog = "papercut"
            st.rerun()
with card3:
    with st.container():
        st.markdown("**GOAL**")
        st.caption("Track goals & ETAs")
        if st.button("Open →", key="btn_goal"):
            st.session_state.open_dialog = "goal"
            st.rerun()

st.markdown("---")

# Open the selected feature in a dialog (modal); each has "Back to dashboard"
if st.session_state.open_dialog == "income":
    dialog_income()
elif st.session_state.open_dialog == "papercut":
    dialog_papercut()
elif st.session_state.open_dialog == "goal":
    dialog_goal()

st.markdown("---")

# ---------------------------------------------------------------------------
# Section: Enter your income (dead code; kept for reference) (Income $x, Expenditure $y, money saved; if y > x → -ve)
# ---------------------------------------------------------------------------
if False:  # moved to dialog_income()
    st.header("Enter your income")
    st.caption("Use the sidebar to set Income and Expenditure. Here’s your result.")
    x = st.session_state.income
    y = st.session_state.expenses
    # Money saved = Income − Expenditure; if expenditure > income, money saved is negative (per sketch).
    money_saved_display = x - y
    col_x, col_y = st.columns(2)
    with col_x:
        st.metric("Income", f"$ {x:,.2f}")
    with col_y:
        st.metric("Expenditure", f"$ {y:,.2f}")
    st.markdown("**Money saved** = Income − Expenditure")
    if money_saved_display < 0:
        st.warning(f"**Money saved = ${money_saved_display:,.2f}** (negative — expenditure is greater than income)")
    else:
        st.success(f"**Money saved = ${money_saved_display:,.2f}**")
    st.divider()

# ---------------------------------------------------------------------------
# Section: Paper cut Analyser
# ---------------------------------------------------------------------------
if False:  # moved to dialog_papercut()
    st.header("Paper cut Analyser")
    st.caption("Compare high-frequency small expenses vs responsible alternatives. Name your habit and see yearly impact.")
    with st.expander("How it works", expanded=False):
        st.markdown(
            "Enter what you spend **per occurrence** (e.g. $4.50 per coffee) and how often per week, or use **daily amount**. "
            "Then enter the **alternative** cost. We compute the yearly impact."
        )
    # Habit name (rename the habit)
    habit_name = st.text_input(
        "Name this habit",
        value="",
        placeholder="e.g. Starbucks coffee, Lunch out",
        key="pc_habit_name",
        help="Give your habit a name so the impact section shows it.",
    )
    habit_label = habit_name.strip() if habit_name else "Current habit"
    # Input mode: per occurrence × frequency (old) OR daily amount
    use_daily = st.checkbox("Enter current habit as daily amount ($) instead of per occurrence × times/week", key="pc_use_daily")
    pc_col1, pc_col2 = st.columns(2)
    with pc_col1:
        st.markdown(f"**{habit_label}**")
        if use_daily:
            daily_amount = st.number_input(
                "Daily amount ($)",
                min_value=0.0,
                value=3.21,
                step=0.25,
                key="pc_daily",
                help="What you spend per day on this habit",
            )
            yearly_from_daily = daily_amount * 365.0
            current_exp = daily_amount
            freq = 7.0 if daily_amount else 0.0
        else:
            current_exp = st.number_input(
                "Cost per occurrence ($)",
                min_value=0.0,
                value=4.50,
                step=0.5,
                key="pc_current",
                help="e.g. price of one coffee",
            )
            freq = st.number_input(
                "Times per week",
                min_value=0.0,
                value=5.0,
                step=0.5,
                key="pc_freq",
            )
            yearly_from_daily = None
    with pc_col2:
        st.markdown("**Alternative**")
        alt_exp = st.number_input(
            "Cost per occurrence ($)",
            min_value=0.0,
            value=0.20,
            step=0.1,
            key="pc_alt",
            help="e.g. home coffee cost",
        )
        if use_daily:
            alt_freq = st.number_input(
                "Times per week",
                min_value=0.0,
                value=5.0,
                step=0.5,
                key="pc_alt_freq",
                help="How often you'd use the alternative per week",
            )
        else:
            alt_freq = freq
        pc_label = st.text_input("Label (optional)", value="", placeholder="e.g. Starbucks → home coffee", key="pc_label")
    if use_daily and yearly_from_daily is not None:
        yearly_alt = alt_exp * alt_freq * 52.0
        result = {
            "yearly_current": round(yearly_from_daily, 2),
            "yearly_alternative": round(yearly_alt, 2),
            "yearly_savings": round(yearly_from_daily - yearly_alt, 2),
            "description": pc_label or habit_label,
        }
    else:
        result = paper_cut_yearly_impact(current_exp, alt_exp, freq, pc_label or habit_label)
    daily_current = result["yearly_current"] / 365.0
    weekly_current = result["yearly_current"] / 52.0
    weekly_alt = result["yearly_alternative"] / 52.0
    monthly_savings_pc = (result["yearly_savings"] / 12) if result["yearly_savings"] else 0
    st.markdown("---")
    st.markdown("### 📊 Impact")
    comp1, comp2, comp3 = st.columns(3)
    with comp1:
        st.metric(
            f"{habit_label} (year)",
            f"${result['yearly_current']:,.2f}",
            help=f"~${daily_current:,.2f}/day · ~${weekly_current:,.2f}/week",
        )
    with comp2:
        st.metric("With alternative (year)", f"${result['yearly_alternative']:,.2f}", help=f"~${weekly_alt:,.2f}/week")
    with comp3:
        st.metric("You save (year)", f"${result['yearly_savings']:,.2f}", help=f"~${monthly_savings_pc:,.2f}/month")
    st.success(
        f"**Yearly impact:** You spend **${result['yearly_current']:,.2f}** on **{habit_label}** now → "
        f"**${result['yearly_alternative']:,.2f}** with alternative → **Save ${result['yearly_savings']:,.2f}/year**."
    )
    st.divider()

# ---------------------------------------------------------------------------
# Section: GOAL (Sort by Goals)
# ---------------------------------------------------------------------------
if False:  # moved to dialog_goal()
    st.header("GOAL")
    st.caption("Sort by goals. Set target amounts in the sidebar. ETAs use your current savings and monthly savings.")
    # Sort by Goals: dropdown to order goals (by ETA soonest, by target amount, or default order)
    sort_option = st.selectbox(
        "Sort by",
        ["Default (Home, Car, Vacation, School)", "Soonest ETA first", "Target amount (low → high)", "Target amount (high → low)"],
        key="goal_sort",
    )
    # Build list of (goal_name, target, eta_result) and sort if needed
    current = st.session_state.current_savings
    goals_data = []
    for goal_name in GOAL_CATEGORIES:
        target = st.session_state.goals.get(goal_name, 0)
        eta_result = goal_eta(
            goal_amount=target,
            current_savings=current,
            monthly_savings=monthly_savings,
            goal_name=goal_name,
        )
        goals_data.append((goal_name, target, eta_result))
    if "Soonest ETA first" in sort_option:
        def eta_months(item):
            name, target, eta = item
            m = eta.get("months_needed")
            return m if m is not None else float("inf")
        goals_data.sort(key=eta_months)
    elif "Target amount (low → high)" in sort_option:
        goals_data.sort(key=lambda x: x[1])
    elif "Target amount (high → low)" in sort_option:
        goals_data.sort(key=lambda x: x[1], reverse=True)
    # Render goal cards with progress bars
    goal_cols = st.columns(len(goals_data))
    for i, (goal_name, target, eta_result) in enumerate(goals_data):
        with goal_cols[i]:
            st.subheader(goal_name)
            st.write(f"Target: **${target:,.0f}**")
            if target > 0:
                progress_pct = min(100.0, (current / target) * 100.0)
                st.progress(progress_pct / 100.0)
                st.caption(f"{progress_pct:.0f}% of goal · ${max(0, target - current):,.0f} to go")
            st.write(eta_result["message"])
            if eta_result.get("eta_date"):
                st.caption(f"ETA: ~{eta_result['eta_date']}")
            elif not eta_result.get("reachable", True) or eta_result.get("months_needed") is None:
                st.caption("Increase monthly savings to see an ETA.")
    st.divider()


# ---------------------------------------------------------------------------
# AI Assistant (Dedalus Tool Calling) — always visible at bottom
# ---------------------------------------------------------------------------
st.header("AI Assistant")
api_key = _get_dedalus_api_key()
dedalus_key_set = bool(api_key)
if dedalus_key_set:
    st.caption("Dedalus: API key set. Ask about savings or goals (Tool Calling: Paper Cut & Goal ETA).")
else:
    st.warning("Dedalus: API key not set. Add `DEDALUS_API_KEY` to your `.env` in the project folder and restart the app.")
    with st.expander("Where the app looks for .env"):
        st.code(f"1. {_app_dir / '.env'}\n2. {Path.cwd() / '.env'}", language="text")
        st.caption("Ensure .env is in the same folder as app.py and contains: DEDALUS_API_KEY=your_key")
if st.button("Verify Dedalus key", key="verify_dedalus"):
    key = _get_dedalus_api_key()
    if not key:
        st.error("Key not found. Check that .env exists next to app.py and has DEDALUS_API_KEY=... (no quotes)")
    else:
        from dedalus_labs import AsyncDedalus, DedalusRunner
        from dedalus_labs import InternalServerError
        models = ["anthropic/claude-opus-4-6", "anthropic/claude-sonnet-4", "anthropic/claude-3-5-sonnet-latest"]
        worked = False
        for model in models:
            with st.spinner(f"Trying {model}..."):
                try:
                    async def _test(m):
                        client = AsyncDedalus(api_key=key)
                        runner = DedalusRunner(client)
                        r = await runner.run(input="Reply with exactly: OK", model=m)
                        return r.final_output or ""
                    out = asyncio.run(_test(model))
                    st.success(f"Dedalus is working (model: {model}). Response: {out[:200]}")
                    worked = True
                    break
                except InternalServerError:
                    continue
                except Exception as e:
                    st.error(f"Dedalus test failed: {e}")
                    worked = True
                    break
        if not worked:
            st.error(
                "Dedalus returned 500 for all models. This is a server-side issue. "
                "Try again in a few minutes or contact support@dedaluslabs.ai."
            )
st.caption(
    'e.g. "How much would I save if I quit Starbucks?" or "When can I afford a car?"'
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
