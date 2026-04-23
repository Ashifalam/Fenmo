import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st

from app.database import SessionLocal, create_tables
from app.service import ExpenseService

# --- Initialization ---
create_tables()
service = ExpenseService(SessionLocal)

PRESET_CATEGORIES = [
    "Groceries",
    "Transport",
    "Dining",
    "Entertainment",
    "Utilities",
    "Healthcare",
    "Shopping",
    "Other",
]

CATEGORY_ICONS = {
    "Groceries": "🛒",
    "Transport": "🚗",
    "Dining": "🍽️",
    "Entertainment": "🎬",
    "Utilities": "💡",
    "Healthcare": "🏥",
    "Shopping": "🛍️",
    "Other": "📦",
}

st.set_page_config(page_title="Fenmo - Expense Tracker", page_icon="💸", layout="wide")

# --- Custom CSS ---
st.markdown("""
<style>
    /* Main header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: rgba(255,255,255,0.85);
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
    }

    /* Section cards */
    .section-card {
        background: white;
        border: 1px solid #e8ecf1;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .section-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1a1a2e;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Total banner */
    .total-banner {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    .total-banner .amount {
        color: white;
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }
    .total-banner .label {
        color: rgba(255,255,255,0.85);
        font-size: 0.9rem;
        margin: 0;
    }

    /* Summary cards */
    .summary-card {
        background: #f8f9fc;
        border: 1px solid #e8ecf1;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .summary-card .cat-name {
        font-size: 0.85rem;
        color: #6b7280;
        margin-bottom: 0.25rem;
    }
    .summary-card .cat-amount {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1a1a2e;
    }
    .summary-card .cat-count {
        font-size: 0.75rem;
        color: #9ca3af;
    }

    /* Better form styling */
    .stForm {
        border: 1px solid #e8ecf1 !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        background: #fafbff !important;
    }

    /* Submit button */
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: opacity 0.2s !important;
    }
    .stFormSubmitButton > button:hover {
        opacity: 0.9 !important;
    }

    /* Dataframe styling */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 3rem 1rem;
        color: #9ca3af;
    }
    .empty-state .icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .empty-state p {
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<div class="main-header">
    <h1>💸 Fenmo</h1>
    <p>Track your expenses, understand your spending</p>
</div>
""", unsafe_allow_html=True)

# --- Session state defaults ---
if "pending_idempotency_key" not in st.session_state:
    st.session_state.pending_idempotency_key = str(uuid.uuid4())

# =============================
# Layout: Two columns — Form (left) + Summary (right)
# =============================
left_col, right_col = st.columns([3, 2], gap="large")

with left_col:
    st.markdown('<div class="section-title">➕ Add New Expense</div>', unsafe_allow_html=True)

    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            amount_input = st.text_input("Amount (₹)", placeholder="e.g. 150.00")
            category_select = st.selectbox("Category", PRESET_CATEGORIES)

        with col2:
            expense_date = st.date_input("Date", value=date.today())
            description = st.text_input("Description", placeholder="e.g. Weekly groceries")

        if category_select == "Other":
            custom_category = st.text_input("Custom category name")
        else:
            custom_category = ""

        submitted = st.form_submit_button("💾  Save Expense", use_container_width=True)

    if submitted:
        error = ""
        amount = Decimal("0")
        category = category_select if category_select != "Other" else custom_category.strip()

        if not amount_input.strip():
            error = "Amount is required."
        else:
            try:
                amount = Decimal(amount_input.strip())
                if amount <= 0:
                    error = "Amount must be positive."
                elif amount.as_tuple().exponent < -2:  # type: ignore[operator]
                    error = "Amount cannot have more than 2 decimal places."
            except InvalidOperation:
                error = "Invalid amount. Enter a number like 150.00"

        if not category:
            error = "Category is required."

        if error:
            st.error(error)
        else:
            try:
                from app.schemas import ExpenseCreate

                data = ExpenseCreate(
                    idempotency_key=st.session_state.pending_idempotency_key,
                    amount=amount,
                    category=category,
                    description=description.strip(),
                    date=expense_date,
                )
                expense, was_created = service.create_expense(data)

                if was_created:
                    st.success(f"Expense of ₹{expense.amount:,.2f} added successfully!")
                else:
                    st.info("This expense was already recorded (duplicate submission detected).")

                st.session_state.pending_idempotency_key = str(uuid.uuid4())

            except Exception as e:
                st.error(f"Failed to save expense. Please try again. ({e})")

with right_col:
    st.markdown('<div class="section-title">📊 Category Breakdown</div>', unsafe_allow_html=True)

    try:
        summary = service.get_summary()
        if summary.by_category:
            # Grand total banner
            st.markdown(f"""
            <div class="total-banner">
                <p class="label">Total Spending</p>
                <p class="amount">₹{summary.grand_total:,.2f}</p>
            </div>
            """, unsafe_allow_html=True)

            # Category cards in a grid
            num_cats = len(summary.by_category)
            cols_per_row = 2
            for i in range(0, num_cats, cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    idx = i + j
                    if idx < num_cats:
                        cat = summary.by_category[idx]
                        icon = CATEGORY_ICONS.get(cat.category, "📦")
                        with col:
                            st.markdown(f"""
                            <div class="summary-card">
                                <div style="font-size:1.5rem">{icon}</div>
                                <div class="cat-name">{cat.category}</div>
                                <div class="cat-amount">₹{cat.total:,.2f}</div>
                                <div class="cat-count">{cat.count} expense{'s' if cat.count != 1 else ''}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.write("")  # spacing
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="icon">📊</div>
                <p>No data yet. Add your first expense!</p>
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        st.error("Failed to load summary.")

st.markdown("---")

# =============================
# Expense List
# =============================
st.markdown('<div class="section-title">📋 Expense History</div>', unsafe_allow_html=True)

filter_col, sort_col, spacer = st.columns([2, 2, 4])

with filter_col:
    existing_categories = service.get_categories()
    all_categories = ["All Categories"] + existing_categories
    selected_category = st.selectbox(
        "Filter", all_categories, key="filter_cat", label_visibility="collapsed"
    )

with sort_col:
    sort_option = st.selectbox(
        "Sort",
        ["📅 Newest first", "📅 Oldest first"],
        key="sort_date",
        label_visibility="collapsed",
    )

category_filter = None if selected_category == "All Categories" else selected_category
sort_value = "date_desc" if "Newest" in sort_option else "date_asc"

try:
    result = service.list_expenses(category=category_filter, sort=sort_value)

    # Total bar
    filter_label = f" in {selected_category}" if selected_category != "All Categories" else ""
    st.markdown(f"""
    <div style="background:#f0f4ff; border-left:4px solid #667eea; padding:0.8rem 1.2rem; border-radius:0 8px 8px 0; margin-bottom:1rem;">
        <span style="color:#6b7280; font-size:0.9rem;">Showing {result.count} expense{'s' if result.count != 1 else ''}{filter_label}</span>
        <span style="float:right; font-size:1.2rem; font-weight:700; color:#1a1a2e;">Total: ₹{result.total:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

    if result.expenses:
        table_data = []
        for e in result.expenses:
            icon = CATEGORY_ICONS.get(e.category, "📦")
            table_data.append({
                "Date": e.date.strftime("%d %b %Y"),
                "Category": f"{icon} {e.category}",
                "Description": e.description or "—",
                "Amount (₹)": f"{e.amount:,.2f}",
            })

        df = pd.DataFrame(table_data)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Amount (₹)": st.column_config.TextColumn("Amount (₹)", width="medium"),
                "Date": st.column_config.TextColumn("Date", width="small"),
            },
        )
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">🔍</div>
            <p>No expenses found matching your filter.</p>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Failed to load expenses. Please refresh the page. ({e})")

# Footer
st.markdown("""
<div style="text-align:center; padding:2rem 0 1rem; color:#9ca3af; font-size:0.8rem;">
    Built with Fenmo — Your personal expense companion
</div>
""", unsafe_allow_html=True)
