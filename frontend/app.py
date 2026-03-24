import streamlit as st
import requests
import pandas as pd
import os

st.set_page_config(
    page_title="SEC Financial Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0a0a0f;
    color: #e2e2e8;
}

#MainMenu, footer, header { visibility: hidden; }
.stApp { background: #0a0a0f; }

[data-testid="stSidebar"] {
    background: #0f0f17 !important;
    border-right: 1px solid #1e1e2e;
}

.page-header {
    padding: 2rem 0 1.5rem 0;
    border-bottom: 1px solid #1e1e2e;
    margin-bottom: 2rem;
}

.page-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #f0f0f6;
    letter-spacing: -0.02em;
    margin: 0;
}

.page-desc {
    font-size: 0.875rem;
    color: #6b6b80;
    margin-top: 0.3rem;
}

.metric-card {
    background: #0f0f17;
    border: 1px solid #1e1e2e;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    text-align: center;
}

.metric-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #7c6ff7;
    font-variant-numeric: tabular-nums;
}

.metric-label {
    font-size: 0.7rem;
    color: #555570;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 0.2rem;
}

.section-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #555570;
    margin-bottom: 0.5rem;
}

.card-title {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #7c6ff7;
    margin-bottom: 1rem;
}

.pill {
    display: inline-block;
    background: rgba(124, 111, 247, 0.1);
    color: #7c6ff7;
    border: 1px solid rgba(124, 111, 247, 0.2);
    border-radius: 100px;
    padding: 0.2rem 0.75rem;
    font-size: 0.72rem;
    font-weight: 500;
}

.pill-green {
    background: rgba(52, 211, 153, 0.1);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.2);
}

.stButton > button {
    background: #7c6ff7 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 0.55rem 1.5rem !important;
}

.stButton > button:hover {
    background: #6a5ee0 !important;
    box-shadow: 0 4px 20px rgba(124, 111, 247, 0.3) !important;
}

.stSelectbox > div > div,
.stTextInput > div > div > input {
    background: #0a0a0f !important;
    border: 1px solid #1e1e2e !important;
    border-radius: 8px !important;
    color: #e2e2e8 !important;
    font-family: 'Inter', sans-serif !important;
}

.stDataFrame {
    border: 1px solid #1e1e2e;
    border-radius: 10px;
    overflow: hidden;
}

hr { border: none; border-top: 1px solid #1e1e2e; margin: 1.5rem 0; }

.sidebar-title {
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #7c6ff7;
    padding-bottom: 1rem;
    border-bottom: 1px solid #1e1e2e;
    margin-bottom: 0.5rem;
}

.sidebar-sub {
    font-size: 0.68rem;
    color: #555570;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #2e2e4e; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">◈ SEC Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">Financial Data Platform</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Navigation</div>', unsafe_allow_html=True)
    page = st.radio("", [
        "Dashboard",
        "Balance Sheet",
        "Income Statement",
        "Cash Flow",
        "Company Search",
        "Storage Explorer"
    ], label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<div class="section-label">Backend Status</div>', unsafe_allow_html=True)
    try:
        r = requests.get(f"{BACKEND}/health", timeout=3)
        if r.status_code == 200:
            st.markdown('<span class="pill pill-green">Connected</span>', unsafe_allow_html=True)
    except:
        st.markdown('<span style="color:#f87171;font-size:0.8rem;">Offline</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.7rem;color:#333350;line-height:1.6;">'
        'SEC Financial Intelligence<br>v1.0.0 · Snowflake + FastAPI<br>Q4 2024 Dataset'
        '</div>',
        unsafe_allow_html=True
    )


def fmt_number(val):
    if val is None:
        return "—"
    try:
        v = float(val)
        if abs(v) >= 1e9:
            return f"${v/1e9:.2f}B"
        elif abs(v) >= 1e6:
            return f"${v/1e6:.2f}M"
        elif abs(v) >= 1e3:
            return f"${v/1e3:.2f}K"
        return f"${v:.2f}"
    except:
        return str(val)


# ── Dashboard ──────────────────────────────────────────────────
if page == "Dashboard":
    st.markdown("""
    <div class="page-header">
        <div class="page-title">Financial Intelligence Dashboard</div>
        <div class="page-desc">Overview of SEC Q4 2024 financial statement data</div>
    </div>
    """, unsafe_allow_html=True)

    try:
        stats = requests.get(f"{BACKEND}/financial/raw/stats", timeout=10).json()
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{stats.get("RAW_SUB", 0):,}</div><div class="metric-label">Total Filings</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{stats.get("RAW_NUM", 0)/1e6:.1f}M</div><div class="metric-label">Numeric Facts</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{stats.get("RAW_TAG", 0):,}</div><div class="metric-label">XBRL Tags</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{stats.get("RAW_PRE", 0)/1e3:.0f}K</div><div class="metric-label">Presentation Rows</div></div>', unsafe_allow_html=True)
    except:
        st.error("Could not connect to backend")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown('<div class="card-title">Top Companies by Total Assets</div>', unsafe_allow_html=True)
        try:
            data = requests.get(f"{BACKEND}/financial/facts/top-companies?metric=assets_total&limit=10", timeout=10).json()
            df = pd.DataFrame(data)
            if not df.empty:
                df["assets_total"] = df["assets_total"].apply(fmt_number)
                df.columns = ["Company", "CIK", "Year", "Total Assets"]
                st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(str(e))

    with col2:
        st.markdown('<div class="card-title">Top Companies by Revenue</div>', unsafe_allow_html=True)
        try:
            data = requests.get(f"{BACKEND}/financial/facts/income-statement?form_type=10-K&limit=10", timeout=10).json()
            df = pd.DataFrame(data)
            if not df.empty:
                df = df[["company_name", "fiscal_year", "revenues", "net_income"]].head(10)
                df["revenues"] = df["revenues"].apply(fmt_number)
                df["net_income"] = df["net_income"].apply(fmt_number)
                df.columns = ["Company", "Year", "Revenue", "Net Income"]
                st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(str(e))


# ── Balance Sheet ──────────────────────────────────────────────
elif page == "Balance Sheet":
    st.markdown("""
    <div class="page-header">
        <div class="page-title">Balance Sheet</div>
        <div class="page-desc">Assets, liabilities, and equity across all filings</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        form_type = st.selectbox("Form Type", ["All", "10-K", "10-Q", "20-F"])
    with col2:
        fiscal_year = st.selectbox("Fiscal Year", ["All", "2024", "2023", "2022"])
    with col3:
        limit = st.selectbox("Rows", [50, 100, 200, 500])

    params = {"limit": limit}
    if form_type != "All":
        params["form_type"] = form_type
    if fiscal_year != "All":
        params["fiscal_year"] = fiscal_year

    try:
        data = requests.get(f"{BACKEND}/financial/facts/balance-sheet", params=params, timeout=15).json()
        df = pd.DataFrame(data)
        if not df.empty:
            st.markdown(f'<span class="pill">{len(df):,} records</span>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            for col in ["assets_total", "assets_current", "liabilities_total", "equity_total", "cash_and_equivalents", "long_term_debt"]:
                if col in df.columns:
                    df[col] = df[col].apply(fmt_number)
            st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(str(e))


# ── Income Statement ───────────────────────────────────────────
elif page == "Income Statement":
    st.markdown("""
    <div class="page-header">
        <div class="page-title">Income Statement</div>
        <div class="page-desc">Revenue, profit, and earnings data across all filings</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        form_type = st.selectbox("Form Type", ["All", "10-K", "10-Q", "20-F"])
    with col2:
        fiscal_year = st.selectbox("Fiscal Year", ["All", "2024", "2023", "2022"])
    with col3:
        limit = st.selectbox("Rows", [50, 100, 200, 500])

    params = {"limit": limit}
    if form_type != "All":
        params["form_type"] = form_type
    if fiscal_year != "All":
        params["fiscal_year"] = fiscal_year

    try:
        data = requests.get(f"{BACKEND}/financial/facts/income-statement", params=params, timeout=15).json()
        df = pd.DataFrame(data)
        if not df.empty:
            st.markdown(f'<span class="pill">{len(df):,} records</span>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            for col in ["revenues", "gross_profit", "operating_income", "net_income"]:
                if col in df.columns:
                    df[col] = df[col].apply(fmt_number)
            st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(str(e))


# ── Cash Flow ──────────────────────────────────────────────────
elif page == "Cash Flow":
    st.markdown("""
    <div class="page-header">
        <div class="page-title">Cash Flow Statement</div>
        <div class="page-desc">Operating, investing, and financing cash flows</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        form_type = st.selectbox("Form Type", ["All", "10-K", "10-Q"])
    with col2:
        limit = st.selectbox("Rows", [50, 100, 200, 500])

    params = {"limit": limit}
    if form_type != "All":
        params["form_type"] = form_type

    try:
        data = requests.get(f"{BACKEND}/financial/facts/cash-flow", params=params, timeout=15).json()
        df = pd.DataFrame(data)
        if not df.empty:
            st.markdown(f'<span class="pill">{len(df):,} records</span>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            for col in ["cfo", "cfi", "cff", "free_cash_flow", "capex"]:
                if col in df.columns:
                    df[col] = df[col].apply(fmt_number)
            st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(str(e))


# ── Company Search ─────────────────────────────────────────────
elif page == "Company Search":
    st.markdown("""
    <div class="page-header">
        <div class="page-title">Company Search</div>
        <div class="page-desc">Search for any US public company and view their financials</div>
    </div>
    """, unsafe_allow_html=True)

    search_query = st.text_input("", placeholder="Search by company name e.g. Apple, Microsoft, Tesla", label_visibility="collapsed")

    if search_query:
        try:
            results = requests.get(f"{BACKEND}/search/company", params={"name": search_query}, timeout=10).json()
            if results:
                st.markdown(f'<span class="pill">{len(results)} companies found</span><br><br>', unsafe_allow_html=True)
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown('<div class="section-label">View Detailed Financials</div>', unsafe_allow_html=True)
                cik_options = {f"{r['company_name']} (CIK: {r['cik']})": r['cik'] for r in results}
                selected = st.selectbox("Select company", list(cik_options.keys()), label_visibility="collapsed")

                if st.button("Load Financials"):
                    cik = cik_options[selected]
                    fin = requests.get(f"{BACKEND}/search/company/{cik}/financials", timeout=15).json()

                    tab1, tab2, tab3 = st.tabs(["Balance Sheet", "Income Statement", "Cash Flow"])

                    with tab1:
                        bs = pd.DataFrame(fin["balance_sheet"])
                        if not bs.empty:
                            for col in ["assets_total", "liabilities_total", "equity_total", "cash_and_equivalents"]:
                                if col in bs.columns:
                                    bs[col] = bs[col].apply(fmt_number)
                            st.dataframe(bs, use_container_width=True, hide_index=True)
                        else:
                            st.info("No balance sheet data available")

                    with tab2:
                        inc = pd.DataFrame(fin["income_statement"])
                        if not inc.empty:
                            for col in ["revenues", "gross_profit", "net_income", "eps_diluted"]:
                                if col in inc.columns:
                                    inc[col] = inc[col].apply(fmt_number)
                            st.dataframe(inc, use_container_width=True, hide_index=True)
                        else:
                            st.info("No income statement data available")

                    with tab3:
                        cf = pd.DataFrame(fin["cash_flow"])
                        if not cf.empty:
                            for col in ["cfo", "cfi", "cff", "free_cash_flow"]:
                                if col in cf.columns:
                                    cf[col] = cf[col].apply(fmt_number)
                            st.dataframe(cf, use_container_width=True, hide_index=True)
                        else:
                            st.info("No cash flow data available")
            else:
                st.info("No companies found matching your search")
        except Exception as e:
            st.error(str(e))


# ── Storage Explorer ───────────────────────────────────────────
elif page == "Storage Explorer":
    st.markdown("""
    <div class="page-header">
        <div class="page-title">Storage Explorer</div>
        <div class="page-desc">Compare Raw, JSON, and Fact Table storage approaches</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Raw Staging", "JSON Transform", "Fact Tables"])

    with tab1:
        st.markdown('<div class="card-title">Raw Staging — Latest Filings</div>', unsafe_allow_html=True)
        try:
            data = requests.get(f"{BACKEND}/financial/raw/companies?limit=50", timeout=10).json()
            df = pd.DataFrame(data)
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(str(e))

    with tab2:
        st.markdown('<div class="card-title">JSON Transform — Latest Filings</div>', unsafe_allow_html=True)
        form_filter = st.selectbox("Filter by form", ["All", "10-K", "10-Q"], key="json_form")
        try:
            params = {"limit": 50}
            if form_filter != "All":
                params["form"] = form_filter
            data = requests.get(f"{BACKEND}/financial/json/filings", params=params, timeout=10).json()
            df = pd.DataFrame(data)
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(str(e))

    with tab3:
        st.markdown('<div class="card-title">Fact Tables — Balance Sheet Preview</div>', unsafe_allow_html=True)
        try:
            data = requests.get(f"{BACKEND}/financial/facts/balance-sheet?limit=50&form_type=10-K", timeout=10).json()
            df = pd.DataFrame(data)
            if not df.empty:
                for col in ["assets_total", "liabilities_total", "equity_total"]:
                    if col in df.columns:
                        df[col] = df[col].apply(fmt_number)
                st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(str(e))