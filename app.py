import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ================================================================
# 1. GLOBAL SETTINGS & DESIGN SYSTEM
# ================================================================
st.set_page_config(
    page_title="KTT Enterprise Insight Hub",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------ CSS Injection --------------------------
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

:root {
    --primary: #4F46E5;
    --secondary: #818CF8;
    --bg: #F8FAFC;
    --card: #FFFFFF;
    --text: #1E293B;
    --sub: #64748B;
}

/* App Reset */
.stApp { background-color: var(--bg); font-family: 'Pretendard'; }

/* Header */
.header { padding: 1.5rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 1.8rem; }
.header-title { font-size: 2.35rem; font-weight: 900;
    background: linear-gradient(135deg,#1E293B,#4F46E5);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.header-sub { color: var(--sub); margin-top: .4rem; }

/* KPI Cards */
.kpi-box { display: grid; grid-template-columns: repeat(4,1fr); gap: 1.3rem; }
.kpi-card {
    background: var(--card); border-radius: 18px;
    padding: 1.4rem; border: 1px solid #E2E8F0;
    box-shadow: 0 4px 8px rgba(0,0,0,0.03);
    transition: .25s ease; position: relative;
}
.kpi-card:hover { transform: translateY(-4px); border-color: var(--secondary);
    box-shadow: 0 10px 16px rgba(79,70,229,0.12);
}
.kpi-label { font-size: .85rem; color: var(--sub); font-weight: 600; }
.kpi-value { font-size: 1.7rem; font-weight: 800; color: var(--text); margin: .45rem 0; }

.delta-pos {
    color: #10B981; background: #ECFDF5;
    padding: 2px 8px; border-radius: 999px; font-size: .8rem; font-weight: 600;
}
.delta-neg {
    color: #EF4444; background: #FEF2F2;
    padding: 2px 8px; border-radius: 999px; font-size: .8rem; font-weight: 600;
}

/* Chart Container */
.chart-box {
    background: var(--card);
    padding: 1.4rem;
    border-radius: 18px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    margin-bottom: 1.4rem;
}
</style>
""", unsafe_allow_html=True)

# ================================================================
# 2. DATA LOADER + PROCESSOR
# ================================================================
@st.cache_data(ttl=1800)
def load_data():
    try:
        try:
            df = pd.read_csv("data.csv", encoding="utf-8")
        except:
            df = pd.read_csv("data.csv", encoding="cp949")
    except FileNotFoundError:
        st.error("❌ data.csv 파일을 찾을 수 없습니다.")
        return pd.DataFrame()

    # Base mappings
    if '조회구분' in df.columns:
        df['정지,설변구분'] = df['조회구분']

    # KPI
    kpi_cols = [c for c in df.columns if 'KPI차감' in c]
    df['KPI_Status'] = df[kpi_cols[0]] if kpi_cols else "-"

    # Dates
    if "이벤트시작일" in df.columns:
        df["이벤트시작일"] = pd.to_datetime(df["이벤트시작일"], errors="coerce")
        df["Period"] = df["이벤트시작일"].dt.strftime("%Y-%m")
        df["Sort"] = df["이벤트시작일"].dt.to_period("M").dt.to_timestamp()

    # Numeric fields
    num_cols = ["월정료(VAT미포함)", "당월말_정지일수"]
    for col in num_cols:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", "")
                .apply(pd.to_numeric, errors="coerce")
                .fillna(0)
            )

    # Defaults
    fill_cols = ['본부','지사','구역담당영업사원','출동/영상','L형/i형','실적채널','체납','부실구분','정지,설변구분']
    for col in fill_cols:
        if col not in df.columns:
            df[col] = "미지정"
        else:
            df[col] = df[col].fillna("미지정")

    return df


# ================================================================
# 3. UTILITIES
# ================================================================
def fmt(x, mode):
    if mode == "건수 (Volume)":
        return f"{x:,.0f} 건"
    return format_currency(x)

def format_currency(value):
    if value >= 100_000_000:
        return f"{value/100_000_000:.1f}억"
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}백만"
    return f"{value/1_000:,.0f}천"


# ================================================================
# 4. MAIN APP
# ================================================================
def main():
    df = load_data()
    if df.empty:
        st.stop()

    # ============================================================
    # Sidebar Filters
    # ============================================================
    with st.sidebar:
        st.markdown("### 📊 Filter Panel")
        all_hq = sorted(df["본부"].unique())
        selected_hq = st.multiselect("본부", all_hq, default=all_hq)

        all_br = sorted(df[df["본부"].isin(selected_hq)]["지사"].unique())
        selected_br = st.multiselect("지사", all_br, default=all_br)

        all_mgr = sorted(df[df["지사"].isin(selected_br)]["구역담당영업사원"].unique())
        selected_mgr = st.multiselect("담당자", all_mgr, default=all_mgr)

        metric_mode = st.radio("분석 기준", ["건수 (Volume)", "금액 (Revenue)"], horizontal=True)

        kpi_only = st.checkbox("KPI 차감 대상만 보기")
        arrears_only = st.checkbox("체납 고객만 보기")

    # Filtering
    mask = (
        df["본부"].isin(selected_hq)
        & df["지사"].isin(selected_br)
        & df["구역담당영업사원"].isin(selected_mgr)
        & (not kpi_only or df["KPI_Status"].str.contains("대상", na=False))
        & (not arrears_only or (df["체납"] != "미지정"))
    )
    d = df[mask]

    # Mode numerical field
    val_col = "계약번호" if metric_mode == "건수 (Volume)" else "월정료(VAT미포함)"
    agg = "count" if metric_mode == "건수 (Volume)" else "sum"

    # ============================================================
    # Header
    # ============================================================
    st.markdown("""
    <div class="header">
        <div class="header-title">KTT Enterprise Insight Hub</div>
        <div class="header-sub">Strategic Operations & KPI Intelligence Dashboard</div>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # KPI Cards
    # ============================================================
    susp = d[d["정지,설변구분"] == "정지"]
    chg  = d[d["정지,설변구분"] == "설변"]

    v_s = susp[val_col].agg(agg)
    v_c = chg[val_col].agg(agg)
    avg_days = d["당월말_정지일수"].mean() if "당월말_정지일수" in d else 0
    risk = (len(susp) / len(d) * 100) if len(d) else 0

    def kpi(title, value, delta):
        cls = "delta-pos" if delta >= 0 else "delta-neg"
        return f"""
        <div class="kpi-card">
            <div class="kpi-label">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="{cls}">{delta:+.1f}%</div>
        </div>
        """

    st.markdown(f"""
    <div class="kpi-box">
        {kpi("정지 총합", fmt(v_s, metric_mode), -2.3)}
        {kpi("설변 총합", fmt(v_c, metric_mode), 1.4)}
        {kpi("평균 정지일수", f"{avg_days:.1f} 일", 0.2)}
        {kpi("정지 비율", f"{risk:.1f}%", -0.7)}
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # TABS
    # ============================================================
    tab1, tab2, tab3 = st.tabs(["📈 Strategic View", "🔍 Operational Analysis", "📄 Data Grid"])

    # ------------------------------------------------------------
    # TAB 1 : Strategic
    # ------------------------------------------------------------
    with tab1:
        col1, col2 = st.columns([2,1])

        # Trend Chart
        with col1:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            if "Period" in d:
                t = d.groupby(["Period","Sort"])[val_col].agg(agg).reset_index().sort_values("Sort")

                fig = px.area(t, x="Period", y=val_col, color_discrete_sequence=["#6366F1"])
                fig.update_traces(line_color="#4F46E5", fillcolor="rgba(79,70,229,0.18)")
                fig.update_layout(title="📅 월별 트렌드 분석", template="plotly_white", height=380)
                fig.update_xaxes(tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Treemap
        with col2:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            if not d.empty:
                fig = px.treemap(
                    d, path=[px.Constant("All"), "본부", "지사"],
                    values=val_col,
                    color="본부",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_layout(title="조직 구조 매핑", height=380)
                st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Pareto
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        hq = d.groupby("본부")[[val_col]].agg(agg).reset_index()
        hq = hq.sort_values(val_col, ascending=False)

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=hq["본부"], y=hq[val_col], marker_color="#3B82F6", name="Volume"))
        fig.add_trace(go.Scatter(x=hq["본부"], y=hq[val_col].cumsum()/hq[val_col].sum()*100,
                                 mode="lines+markers", line=dict(color="#EF4444", width=3), name="Pareto"),
                      secondary_y=True)

        fig.update_layout(title="본부별 효율성 분석 (Pareto)", template="plotly_white", height=400)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # TAB 2 : Operations
    # ------------------------------------------------------------
    with tab2:
        col1, col2 = st.columns([1,2])

        with col1:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            cat_col = st.selectbox("카테고리 선택", ["실적채널","L형/i형","출동/영상","부실구분"])
            grp = d.groupby(cat_col)[val_col].agg(agg).reset_index()

            fig = px.pie(grp, names=cat_col, values=val_col, hole=0.55,
                         color_discrete_sequence=px.colors.qualitative.Safe)
            fig.update_traces(textinfo="percent+label")
            fig.update_layout(title=f"{cat_col} 비중 분석", height=380)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            mgr = d.groupby("구역담당영업사원")[val_col].agg(agg)
            mgr = mgr.sort_values(ascending=True).tail(15).reset_index()

            fig = go.Figure(go.Bar(
                x=mgr[val_col], y=mgr["구역담당영업사원"],
                orientation="h",
                marker=dict(color=mgr[val_col], colorscale="Blues"),
                text=mgr[val_col],
                textposition="auto"
            ))
            fig.update_layout(title="Top 15 담당자 Performance", template="plotly_white", height=380)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # TAB 3 : Data Grid
    # ------------------------------------------------------------
    with tab3:
        st.markdown("### 📄 Data Table View")
        cols = ["본부","지사","구역담당영업사원","이벤트시작일","상호","월정료(VAT미포함)","정지,설변구분","KPI_Status"]
        cols = [c for c in cols if c in d]

        d_show = d[cols]
        st.dataframe(d_show, use_container_width=True, height=550)

        # Download
        if st.text_input("Download Key", type="password") == "3867":
            st.download_button("📥 Download CSV", d.to_csv(index=False).encode("utf-8-sig"),
                               "ktt_export.csv", "text/csv")


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    main()
