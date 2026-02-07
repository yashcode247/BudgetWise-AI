"""
PIN PLAN - Financial planning utilities and Dedalus tools.
All functions are designed for use in the Streamlit UI and as Dedalus Runner tools.
"""

from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Core budget math (used by dashboard and by AI via tools)
# ---------------------------------------------------------------------------

def calculate_monthly_savings(income: float, expenses: float) -> float:
    """
    Compute monthly savings from income and total expenses.
    Used by the budget dashboard and by the AI when answering savings questions.
    """
    return max(0.0, float(income) - float(expenses))


def paper_cut_yearly_impact(
    current_expense: float,
    alternative_expense: float,
    frequency_per_week: float,
    description: str = "",
) -> dict:
    """
    Compare a high-frequency small expense (e.g. $4.50 Starbucks) vs a responsible
    alternative (e.g. $0.20 home coffee) and return the yearly financial impact.

    Use this when the user asks things like "How much would I save if I quit Starbucks?"
    or "What's the yearly impact of switching to home coffee?"

    Returns a dict with: yearly_current, yearly_alternative, yearly_savings, description.
    """
    current = float(current_expense)
    alternative = float(alternative_expense)
    freq = max(0.0, float(frequency_per_week))
    weeks_per_year = 52.0
    yearly_current = current * freq * weeks_per_year
    yearly_alternative = alternative * freq * weeks_per_year
    yearly_savings = yearly_current - yearly_alternative
    return {
        "yearly_current": round(yearly_current, 2),
        "yearly_alternative": round(yearly_alternative, 2),
        "yearly_savings": round(yearly_savings, 2),
        "description": description or "Paper cut expense vs alternative",
    }


def goal_eta(
    goal_amount: float,
    current_savings: float,
    monthly_savings: float,
    goal_name: str = "Goal",
) -> dict:
    """
    Calculate how many months until a savings goal is reached, and optional ETA date.
    Use when the user asks "When can I afford X?" or "How long until my goal?"

    Returns a dict with: months_needed, reachable, message, eta_date (if reachable).
    """
    goal = max(0.0, float(goal_amount))
    current = max(0.0, float(current_savings))
    monthly = float(monthly_savings)
    remaining = goal - current
    if remaining <= 0:
        return {
            "months_needed": 0,
            "reachable": True,
            "message": f"You have already reached or exceeded the {goal_name} target.",
            "eta_date": None,
        }
    if monthly <= 0:
        return {
            "months_needed": None,
            "reachable": False,
            "message": f"Cannot reach {goal_name} with current monthly savings (${monthly:,.2f}). Increase income or reduce expenses.",
            "eta_date": None,
        }
    months_needed = remaining / monthly
    today = datetime.now().date()
    eta_date = (today + timedelta(days=int(months_needed * 30.44))).isoformat()
    return {
        "months_needed": round(months_needed, 1),
        "reachable": True,
        "message": f"At ${monthly:,.2f}/month savings, you'll reach {goal_name} in ~{months_needed:.1f} months.",
        "eta_date": eta_date,
    }


# ---------------------------------------------------------------------------
# Goal categories for the Goal Tracker (Sort by Goals)
# ---------------------------------------------------------------------------
GOAL_CATEGORIES = ["Home", "Car", "Vacation", "School"]
