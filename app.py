# ------------------------------------------------------------------------------------
# KTT ENTERPRISE ANALYTICS — FULL ENTERPRISE VERSION
# Theme System + Header Branding + AgGrid + SQL Loader + AI Risk Prediction
# ------------------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from sqlalchemy import create_engine
from datetime import datetime
import joblib

# ====================================================================================
# PAGE CONFIG
# ====================================================================================
st.set_page_config(
    page_title="KTT Enterprise Dashboard",
    page_icon="📊",
    layout="wide",
)

# ====================================================================================
# THEME CSS (Three Modes)
# ====================================================================================
def apply_theme(theme):
    if theme == "Neumorphic":
        st.markdown("""
        <style>
        body { background: #e0e5ec; }
        .stApp { background: #e0e5ec; }
        .card {
            background: #e0e5ec;
            border-radius: 18px;
            padding: 28px;
            box-shadow: 9px 9px 16px #b8b9be,
                        -9px -9px 16px #ffffff;
        }
        </style>
        """, unsafe_allow_html=True)

    elif theme == "Material (Google)":
        st.markdown("""
        <style>
            .stApp { background: #fafafa; }
            .card {
                background: white;
                padding: 26px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            }
        </style>
        """, unsafe_allow_html=True)

    elif theme == "Enterprise Blue":
        st.markdown("""
        <style>
            .stApp { background: #f0f4ff; }
            .card {
                background: white;
                padding: 26px;
                border-radius: 12px;
                border: 1px solid #d0d8ff;
                box-shadow: 0 4px 8px rgba(0,0,0,0.05);
            }
        </style>
        """, unsafe_allow_html=True)


# ====================================================================================
# THEME SELECTOR (Sidebar)
# ====================================================================================
theme = st.sidebar.selectbox(
    "🎨 Theme",
    ["Enterprise Blue", "Neumorphic", "Material (Google)"],
    index=0
)
apply_theme(theme)

# ====================================================================================
# SQL CONNECTOR (Optional)
# ====================================================================================
st.sidebar.markdown("## 🔌 SQL Connection")
use_sql = st.sidebar.checkbox("DB에서 불러오기")

sql_df = None
if use_sql:
    db_url = st.sidebar.text_input("SQLAlchemy URL", "mysql+pymysql://user:pass@host/db")

    if st.sidebar.button("Load DB"):
        try:
            engine = create_engine(db_url)
            sql_df = pd.read_sql("SELECT * FROM your_table", engine)
            st.success(f"{len(sql_df):,} rows loaded from DB")
        except Exception as e:
            st.error(f"SQL Load Error: {e}")

# ====================================================================================
# LOAD CSV or SQL
# ====================================================================================
@st.cache_data
def load_csv():
    df = pd.read_csv("data.csv")
    df["이벤트시작일"] = pd.to_datetime(df["이벤트시작일"], errors="coerce")
    df["Period"] = df["이벤트시작일"].dt.strftime("%Y-%m")
    df = df.fillna("-")
    return df

df = sql_df if use_sql else load_csv()


# ====================================================================================
# BRANDED HEADER UI
# ====================================================================================
st.markdown(f"""
<style>
.header-container {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 28px;
    background: linear-gradient(90deg, #1e3a8a, #3b82f6);
    border-radius: 12px;
    margin-bottom: 18px;
    color: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}}
.header-left {{
    display: flex;
    align-items: center;
    gap: 16px;
}}
.header-logo {{
    width: 48px;
    height: 48px;
    border-radius: 12px;
    background: white;
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 26px;
    color: #1e3a8a;
    font-weight: 900;
}}
.header-title {{
    font-size: 1.8rem;
    font-weight: 800;
    margin: 0;
}}
.header-sub {{
    font-size: 0.9rem;
    margin-top: -4px;
    opacity: 0.9;
}}
.header-right {{
    font-size: 0.9rem;
    opacity: 0.9;
    text-align: right;
}}
</style>

<div class="header-container">
    <div class="header-left">
        <div class="header-logo">K</div>
        <div>
            <div class="header-title">KTT Enterprise Dashboard</div>
            <div class="header-sub">Strategic Business Intelligence Platform</div>
        </div>
    </div>
    <div class="header-right">
        Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
    </div>
</div>
""", unsafe_allow_html=True)


# ====================================================================================
# FILTER PANEL
# ====================================================================================
with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        hqs = sorted(df["본부"].unique())
        selected_hq = st.multiselect("본부", hqs, default=hqs)

    with c2:
        branches = sorted(df[df["본부"].isin(selected_hq)]["지사"].unique())
        selected_branch = st.multiselect("지사", branches, default=branches)

    with c3:
        stores = sorted(df[df["지사"].isin(selected_branch)]["상호"].unique())
        selected_store = st.multiselect("상호", stores, default=stores)

    st.markdown("</div>", unsafe_allow_html=True)

mask = (
    df["본부"].isin(selected_hq)
    & df["지사"].isin(selected_branch)
    & df["상호"].isin(selected_store)
)
df_filtered = df[mask]


# ====================================================================================
# KPI SUMMARY
# ====================================================================================
st.markdown("## 📌 Executive Summary")

k1, k2, k3, k4 = st.columns(4)

k1.metric("총 계약 건수", f"{len(df_filtered):,}")
k2.metric("기간 수", df_filtered["Period"].nunique())
k3.metric("지사 수", df_filtered["지사"].nunique())
k4.metric("부실 건수", (df_filtered["부실여부(체납제외)"] != "-").sum())


# ====================================================================================
# CHART — Timeline
# ====================================================================================
st.subheader("📅 기간별 계약 추이")

trend = df_filtered.groupby("Period").size().reset_index(name="count")
fig = px.line(trend, x="Period", y="count", markers=True)
st.plotly_chart(fig, use_container_width=True)


# ====================================================================================
# CHART — HQ / Branch Structure
# ====================================================================================
st.subheader("🏢 본부 / 지사 분포도")

fig2 = px.sunburst(df_filtered, path=["본부", "지사"])
st.plotly_chart(fig2, use_container_width=True)


# ====================================================================================
# 부실 / 체납 분석
# ====================================================================================
st.subheader("⚠️ 부실·체납 분포")

colA, colB = st.columns(2)

with colA:
    debt = df_filtered["체납"].value_counts().reset_index()
    debt.columns = ["구분", "건수"]
    st.plotly_chart(px.pie(debt, names="구분", values="건수", hole=0.45), use_container_width=True)

with colB:
    if "부실여부(체납제외)" in df.columns:
        bad = df_filtered["부실여부(체납제외)"].value_counts().reset_index()
        bad.columns = ["구분", "건수"]
        st.plotly_chart(px.pie(bad, names="구분", values="건수", hole=0.45), use_container_width=True)


# ====================================================================================
# AI RISK PREDICTION
# ====================================================================================
st.subheader("🤖 AI 기반 부실 위험 예측")

try:
    model = joblib.load("model.pkl")

    df_pred = df_filtered.copy()
    df_pred["month"] = df_pred["이벤트시작일"].dt.month
    df_pred["year"] = df_pred["이벤트시작일"].dt.year
    df_pred = df_pred.fillna(0)

    X = df_pred[["month", "year"]]
    df_pred["부실예측확률(%)"] = (model.predict_proba(X)[:, 1] * 100).round(1)

    st.plotly_chart(
        px.histogram(df_pred, x="부실예측확률(%)", nbins=20),
        use_container_width=True
    )

    st.dataframe(df_pred[["상호", "본부", "지사", "부실예측확률(%)"]])

except Exception as e:
    st.warning("예측 모델(model.pkl)이 존재하지 않아 예측 기능을 비활성화합니다.")


# ====================================================================================
# GRID — AgGrid
# ====================================================================================
st.subheader("📄 Smart Data Grid")

gb = GridOptionsBuilder.from_dataframe(df_filtered)
gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=20)
gb.configure_side_bar()
gb.configure_selection("multiple", use_checkbox=True)
grid_options = gb.build()

AgGrid(
    df_filtered,
    gridOptions=grid_options,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    theme="material",
)

st.download_button(
    "CSV 다운로드",
    df_filtered.to_csv(index=False).encode("utf-8-sig"),
    "filtered_data.csv",
    "text/csv"
)
