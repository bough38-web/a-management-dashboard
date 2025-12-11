import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =============================================================================

# 0. Global Config (Page & Constants)

# =============================================================================

PAGE_TITLE = "KTT Strategic Dashboard"
PAGE_ICON = "💎"
DATA_PATH = "data.csv"

# 공통 컬러 팔레트 (재사용 가능)

COLOR_PRIMARY = "#4f46e5"   # Indigo
COLOR_PRIMARY_SOFT = "rgba(79, 70, 229, 0.15)"
COLOR_ACCENT = "#f43f5e"    # Rose
COLOR_BG = "#f8fafc"        # Slate-50

st.set_page_config(
page_title=PAGE_TITLE,
page_icon=PAGE_ICON,
layout="wide",
initial_sidebar_state="collapsed"
)

# =============================================================================

# 1. Global Style (CSS)

# =============================================================================

def inject_global_css() -> None:
    """Pretendard 폰트 + 공통 UI 스타일 주입."""
    st.markdown(
        f"""
        <style>
            @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

            html, body, [class*="css"] {{
                font-family: 'Pretendard', sans-serif;
            }}
            .stApp {{
                background-color: {COLOR_BG};
            }}

            .header-title {{
                font-size: 28px;
                font-weight: 800;
                color: #1e293b;
                margin-bottom: 5px;
            }}
            .header-subtitle {{
                font-size: 15px;
                color: #64748b;
                margin-bottom: 20px;
            }}

            .filter-box {{
                background-color: #ffffff;
                padding: 26px;
                border-radius: 24px;
                box-shadow: 0 1px 3px rgba(15,23,42,0.12);
                border: 1px solid #e2e8f0;
                margin-bottom: 24px;
            }}

            div[data-testid="stPills"] {{
                gap: 8px;
            }}
            div[data-testid="stPills"] button[aria-selected="true"] {{
                background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%) !important;
                color: white !important;
                border-radius: 999px;
                border: none;
            }}
            div[data-testid="stPills"] button[aria-selected="false"] {{
                background-color: white !important;
                border-radius: 999px;
                border: 1px solid #e2e8f0 !important;
            }}

            div[data-testid="stMetric"] {{
                background-color: white;
                border: 1px solid #e2e8f0;
                padding: 22px;
                border-radius: 18px;
                box-shadow: 0 4px 6px rgba(15,23,42,0.08);
                transition: .15s;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )



inject_global_css()

# =============================================================================

# 2. Data Load & Preprocessing

# =============================================================================

@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
# """CSV 로드 + 기본 전처리."""
try:
df = pd.read_csv(path)
except FileNotFoundError:
st.error(f"데이터 파일({path})을 찾을 수 없습니다. 파일 경로를 확인해주세요.")
return pd.DataFrame()
except Exception as e:
st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
return pd.DataFrame()


# --- 날짜 처리 ---
if "이벤트시작일" in df.columns:
    df["이벤트시작일"] = pd.to_datetime(df["이벤트시작일"], errors="coerce")

    # 분석기간 라벨링
    def get_period_label(dt):
        if pd.isnull(dt):
            return "미분류"
        if dt.year < 2025:
            return "2024년 이전"
        return f"'{str(dt.year)[-2:]}.{dt.month}"

    df["분석기간"] = df["이벤트시작일"].apply(get_period_label)

    def get_sort_key(dt):
        if pd.isnull(dt):
            return pd.Timestamp.min
        if dt.year < 2025:
            # 2024년 이전은 가장 먼저 나오도록, 2024-01-01 이전 기준 부여
            return pd.Timestamp("2024-01-01")
        return dt

    df["sort_key"] = df["이벤트시작일"].apply(get_sort_key)
else:
    df["분석기간"] = "미분류"
    df["sort_key"] = pd.Timestamp.min

# --- 숫자 컬럼 처리 ---
numeric_cols = ["월정료(VAT미포함)", "계약번호", "당월말_정지일수"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# --- 범주형 결측 처리 ---
fill_cols = ["본부", "지사", "출동/영상", "L형/i형", "정지,설변구분", "서비스(소)"]
for col in fill_cols:
    if col not in df.columns:
        df[col] = "미분류"
    else:
        df[col] = df[col].fillna("미분류")

return df


df = load_data(DATA_PATH)
if df.empty:
st.stop()

# =============================================================================

# 3. Header & Filters

# =============================================================================

# 상단 헤더

st.markdown(
""" <div class="header-title">💎 KTT Strategic Insight</div> <div class="header-subtitle">조직·상품·기간별 실적을 한 번에 조망할 수 있는 인터랙티브 대시보드</div>
""",
unsafe_allow_html=True,
)

def render_filters(data: pd.DataFrame) -> pd.DataFrame:
"""본부 / 지사 멀티 필터 UI 및 필터링된 데이터 리턴."""
with st.container():
st.markdown('<div class="filter-box">', unsafe_allow_html=True)


    # ---------------------------
    # [1] 본부 선택
    # ---------------------------
    all_hqs = sorted(data["본부"].unique().tolist())
    st.markdown("**🏢 본부 선택 (Headquarters)**")

    # Session State 기본값
    if "hq_select" not in st.session_state:
        st.session_state.hq_select = all_hqs

    # st.pills 지원 여부에 따라 fallback
    try:
        selected_hq = st.pills(
            "본부 목록",
            all_hqs,
            selection_mode="multi",
            default=all_hqs,
            key="hq_pills",
            label_visibility="collapsed",
        )
    except AttributeError:
        selected_hq = st.multiselect("본부 선택", all_hqs, default=all_hqs)

    if not selected_hq:
        selected_hq = all_hqs

    # ---------------------------
    # [2] 지사 선택 (선택 본부 기준)
    # ---------------------------
    st.markdown("---")

    branch_candidates = data[data["본부"].isin(selected_hq)]
    available_branches = sorted(branch_candidates["지사"].unique().tolist())

    st.markdown(
        f"**📍 지사 선택 (Branches)**  &nbsp;&nbsp;<span style='color:#94a3b8; font-size:13px'>(활성 지사 {len(available_branches)}개)</span>",
        unsafe_allow_html=True,
    )

    if len(available_branches) > 24:
        with st.expander(f"🔽 전체 지사 목록 보기 ({len(available_branches)}개)", expanded=False):
            try:
                selected_branch = st.pills(
                    "지사 목록",
                    available_branches,
                    selection_mode="multi",
                    default=available_branches,
                    key="br_pills_full",
                    label_visibility="collapsed",
                )
            except AttributeError:
                selected_branch = st.multiselect(
                    "지사 선택", available_branches, default=available_branches
                )
    else:
        try:
            selected_branch = st.pills(
                "지사 목록",
                available_branches,
                selection_mode="multi",
                default=available_branches,
                key="br_pills_lite",
                label_visibility="collapsed",
            )
        except AttributeError:
            selected_branch = st.multiselect(
                "지사 선택", available_branches, default=available_branches
            )

    if not selected_branch:
        selected_branch = available_branches

    st.markdown("</div>", unsafe_allow_html=True)

# 실제 필터링 적용
filtered = data[
    (data["본부"].isin(selected_hq)) & (data["지사"].isin(selected_branch))
].copy()

return filtered


df_filtered = render_filters(df)

# =============================================================================

# 4. KPI Section

# =============================================================================

st.markdown("### 🚀 Executive Summary")

k1, k2, k3, k4 = st.columns(4)

tot_cnt = len(df_filtered)
tot_rev = float(df_filtered["월정료(VAT미포함)"].sum())
avg_susp = (
float(df_filtered["당월말_정지일수"].mean())
if "당월말_정지일수" in df_filtered.columns
else 0
)
risk_cnt = len(df_filtered[df_filtered["정지,설변구분"].str.contains("정지", na=False)])

ratio_text = (
f"Ratio: {risk_cnt / tot_cnt * 100:.1f}%"
if tot_cnt > 0
else "Ratio: 0.0%"
)

k1.metric("총 계약 건수", f"{tot_cnt:,.0f} 건", "Active Contracts")
k2.metric("총 월정료 (Revenue)", f"₩{tot_rev/10000:,.0f} 만", "VAT 별도")
k3.metric("평균 정지일수", f"{avg_susp:.1f} 일", "Suspension Avg", delta_color="off")
k4.metric("Risk Alert (정지)", f"{risk_cnt:,.0f} 건", ratio_text, delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True)

# =============================================================================

# 5. Visualization Tabs

# =============================================================================

tab_overview, tab_analysis, tab_grid = st.tabs(
["📊 Performance & Trend", "📈 Deep Dive Analysis", "💾 Data Grid"]
)

# -----------------------------------------------------------------------------

# [TAB 1] Performance & Trend

# -----------------------------------------------------------------------------

with tab_overview:
row1_c1, row1_c2 = st.columns([2, 1])

```
# 5-1. 본부별 Pareto / Dual Axis
with row1_c1:
    st.subheader("🏢 본부별 효율성 (Pareto Chart)")
    hq_agg = (
        df_filtered.groupby("본부")
        .agg({"계약번호": "count", "월정료(VAT미포함)": "sum"})
        .reset_index()
    )
    hq_agg = hq_agg.sort_values("계약번호", ascending=False)

    if hq_agg.empty:
        st.info("선택된 조건에 해당하는 본부 데이터가 없습니다.")
    else:
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])

        fig_dual.add_trace(
            go.Bar(
                x=hq_agg["본부"],
                y=hq_agg["계약번호"],
                name="계약 건수",
                marker_color=COLOR_PRIMARY,
                opacity=0.9,
                width=0.5,
            ),
            secondary_y=False,
        )

        fig_dual.add_trace(
            go.Scatter(
                x=hq_agg["본부"],
                y=hq_agg["월정료(VAT미포함)"],
                name="매출 규모",
                mode="lines+markers",
                line=dict(color=COLOR_ACCENT, width=3),
                marker=dict(size=8),
            ),
            secondary_y=True,
        )

        fig_dual.update_layout(
            template="plotly_white",
            hovermode="x unified",
            height=420,
            legend=dict(orientation="h", y=1.12),
            margin=dict(t=40, b=0, l=0, r=0),
        )
        fig_dual.update_yaxes(
            title_text="건수", secondary_y=False, showgrid=False
        )
        fig_dual.update_yaxes(
            title_text="매출(원)",
            secondary_y=True,
            showgrid=True,
            gridcolor="#f1f5f9",
        )

        st.plotly_chart(fig_dual, use_container_width=True)

# 5-2. 조직 분포 Sunburst
with row1_c2:
    st.subheader("🌐 조직 분포 (Sunburst)")
    if df_filtered.empty:
        st.info("표시할 조직 분포 데이터가 없습니다.")
    else:
        fig_sun = px.sunburst(
            df_filtered,
            path=["본부", "지사"],
            values="계약번호",
            color="계약번호",
            color_continuous_scale="Purples",
            hover_data=["월정료(VAT미포함)"],
        )
        fig_sun.update_layout(
            height=420, margin=dict(t=10, l=10, r=10, b=10)
        )
        st.plotly_chart(fig_sun, use_container_width=True)

# 5-3. 기간별 실적 추이
st.subheader("📅 기간별 실적 추이 (2024 이전 통합)")
if "분석기간" in df_filtered.columns and not df_filtered.empty:
    trend_df = (
        df_filtered.groupby(["분석기간", "sort_key"])
        .agg({"계약번호": "count"})
        .reset_index()
        .sort_values("sort_key")
    )

    fig_trend = px.area(
        trend_df,
        x="분석기간",
        y="계약번호",
        markers=True,
        title="기간별 계약 건수 변화",
    )
    fig_trend.update_traces(
        line_color=COLOR_PRIMARY,
        line_width=3,
        fill="tozeroy",
        fillcolor=COLOR_PRIMARY_SOFT,
    )
    fig_trend.update_layout(
        template="plotly_white",
        height=350,
        xaxis_title="기간 (Period)",
        yaxis_title="계약 건수",
        margin=dict(t=60, b=0, l=0, r=0),
    )
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("기간별 추이를 계산할 수 있는 데이터가 없습니다.")


# -----------------------------------------------------------------------------

# [TAB 2] Deep Dive Analysis

# -----------------------------------------------------------------------------

with tab_analysis:
row2_c1, row2_c2 = st.columns(2)

```
# 5-4. 지사별 성과 매트릭스 (버블 차트)
with row2_c1:
    st.subheader("📊 지사별 성과 매트릭스")

    branch_stats = (
        df_filtered.groupby(["본부", "지사"])
        .agg(
            {
                "계약번호": "count",
                "월정료(VAT미포함)": ["mean", "sum"],
            }
        )
        .reset_index()
    )

    branch_stats.columns = ["본부", "지사", "건수", "평균단가", "총매출"]

    if branch_stats.empty:
        st.info("지사별 성과를 표시할 데이터가 없습니다.")
    else:
        fig_bub = px.scatter(
            branch_stats,
            x="건수",
            y="평균단가",
            size="총매출",
            color="본부",
            hover_name="지사",
            template="plotly_white",
            size_max=40,
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
        fig_bub.update_layout(
            height=400,
            xaxis_title="계약 건수",
            yaxis_title="평균 단가 (원)",
            margin=dict(t=40, b=0, l=0, r=0),
        )
        st.plotly_chart(fig_bub, use_container_width=True)

# 5-5. 서비스 상품 구성 (Treemap)
with row2_c2:
    st.subheader("🧩 서비스 상품 구성")
    if "서비스(소)" in df_filtered.columns and not df_filtered.empty:
        svc_cnt = (
            df_filtered["서비스(소)"]
            .value_counts()
            .reset_index()
            .rename(columns={"index": "서비스명", "서비스(소)": "건수"})
        )

        fig_tree = px.treemap(
            svc_cnt.head(15),
            path=["서비스명"],
            values="건수",
            color="건수",
            color_continuous_scale="Teal",
        )
        fig_tree.update_layout(
            height=400, margin=dict(t=10, l=10, r=10, b=10)
        )
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("서비스(소) 기준으로 분석 가능한 데이터가 없습니다.")

st.markdown("---")

# 5-6. Donut 차트 3종
st.subheader("🍩 카테고리별 비중")
c_pie1, c_pie2, c_pie3 = st.columns(3)

with c_pie1:
    if not df_filtered.empty:
        fig1 = px.pie(
            df_filtered,
            names="출동/영상",
            hole=0.6,
            title="출동/영상 비중",
            color_discrete_sequence=px.colors.qualitative.Pastel1,
        )
        fig1.update_layout(margin=dict(t=40, b=0, l=0, r=0), height=320)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("출동/영상 데이터 없음")

with c_pie2:
    if not df_filtered.empty:
        fig2 = px.pie(
            df_filtered,
            names="L형/i형",
            hole=0.6,
            title="L형/i형 비중",
            color_discrete_sequence=px.colors.qualitative.Pastel2,
        )
        fig2.update_layout(margin=dict(t=40, b=0, l=0, r=0), height=320)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("L형/i형 데이터 없음")

with c_pie3:
    if not df_filtered.empty:
        fig3 = px.pie(
            df_filtered,
            names="정지,설변구분",
            hole=0.6,
            title="정지/설변 유형",
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig3.update_layout(margin=dict(t=40, b=0, l=0, r=0), height=320)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("정지/설변 데이터 없음")
```

# -----------------------------------------------------------------------------

# [TAB 3] Data Grid

# -----------------------------------------------------------------------------

with tab_grid:
st.markdown("### 💾 Intelligent Data Grid")

```
cols_to_show = [
    "본부",
    "지사",
    "분석기간",
    "고객번호",
    "상호",
    "월정료(VAT미포함)",
    "정지,설변구분",
    "이벤트시작일",
]
valid_cols = [c for c in cols_to_show if c in df_filtered.columns]

def color_coding(row):
    """정지/설변 상태에 따른 행 배경색 지정."""
    val = str(row.get("정지,설변구분", ""))
    base_style = [""] * len(row)

    if "정지" in val:
        return [
            "background-color: #fee2e2; color: #991b1b; font-weight: 500;"
        ] * len(row)
    if "설변" in val:
        return [
            "background-color: #fef9c3; color: #854d0e; font-weight: 500;"
        ] * len(row)
    return base_style

if not df_filtered.empty and valid_cols:
    styled_df = df_filtered[valid_cols].style.apply(
        color_coding, axis=1
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        height=600,
        column_config={
            "월정료(VAT미포함)": st.column_config.NumberColumn(
                "월정료", format="₩%d"
            ),
            "이벤트시작일": st.column_config.DateColumn(
                "이벤트 일자", format="YYYY-MM-DD"
            ),
        },
    )
else:
    st.info("표시할 데이터가 없습니다. 상단 필터 조건을 확인해주세요.")

# 다운로드 버튼
if not df_filtered.empty:
    csv = df_filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 데이터 다운로드 (CSV)",
        csv,
        "ktt_data.csv",
        "text/csv",
    )
```
