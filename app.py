import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. Page & Design Config (High-End UI)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Strategic Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 고급 CSS: Pretendard 폰트, Glassmorphism, Modern Cards
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        /* 기본 폰트 및 배경 설정 */
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
        }
        .stApp {
            background-color: #f8fafc; /* Slate-50 */
        }
        
        /* 헤더 스타일 */
        h1, h2, h3 {
            color: #1e293b;
            font-weight: 800;
            letter-spacing: -0.5px;
        }
        
        /* KPI 카드 디자인 (Neumorphism 느낌) */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: all 0.3s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            border-color: #6366f1; /* Indigo Hover */
        }
        
        /* 필터 컨테이너 스타일 */
        .filter-container {
            background-color: #ffffff;
            padding: 24px;
            border-radius: 20px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }
        
        /* 탭 스타일 고급화 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            background-color: transparent;
            padding-bottom: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 48px;
            background-color: #ffffff;
            border-radius: 12px;
            padding: 0 24px;
            font-weight: 600;
            color: #64748b;
            border: 1px solid #e2e8f0;
            transition: all 0.2s;
        }
        .stTabs [aria-selected="true"] {
            background-color: #4f46e5; /* Indigo-600 */
            color: #ffffff;
            border: none;
            box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.3);
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Data Logic
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = "data.csv"
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error("데이터 파일(data.csv)을 찾을 수 없습니다.")
        return pd.DataFrame()

    if '이벤트시작일' in df.columns:
        df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
        df['년월'] = df['이벤트시작일'].dt.to_period('M').astype(str)
        df['년월_dt'] = df['이벤트시작일'].dt.to_period('M').dt.to_timestamp() # 차트 정렬용
    
    numeric_cols = ['월정료(VAT미포함)', '계약번호', '당월말_정지일수']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    fill_cols = ['본부', '지사', '출동/영상', 'L형/i형', '정지,설변구분', '서비스(소)']
    for col in fill_cols:
        if col not in df.columns:
            df[col] = "미분류"
        else:
            df[col] = df[col].fillna("미분류")
            
    return df

df = load_data()
if df.empty:
    st.stop()

# -----------------------------------------------------------------------------
# 3. Dynamic Filter System (Premium UI)
# -----------------------------------------------------------------------------
st.title("💎 KTT Strategic Insight")
st.markdown("### 🎯 Interactive Control Center")

with st.container():
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    
    # [1] 본부 선택 (Pills UI)
    all_hqs = sorted(df['본부'].unique().tolist())
    st.caption("🏢 Select Headquarters (다중 선택 가능)")
    
    # Session State를 활용한 초기값 설정 방어 로직
    if "hq_select" not in st.session_state:
        st.session_state.hq_select = all_hqs
        
    try:
        selected_hq = st.pills("본부", all_hqs, selection_mode="multi", default=all_hqs, key="hq_pills", label_visibility="collapsed")
    except AttributeError:
        selected_hq = st.multiselect("본부 선택", all_hqs, default=all_hqs)
    
    if not selected_hq: selected_hq = all_hqs

    # [2] 지사 선택 (Chained Dropdown)
    st.markdown("---")
    st.caption(f"📍 Select Branches (Included in {len(selected_hq)} HQs)")
    
    available_branches = sorted(df[df['본부'].isin(selected_hq)]['지사'].unique().tolist())
    
    # 지사가 많을 경우 UI 깨짐 방지
    if len(available_branches) > 20:
        with st.expander(f"📖 지사 전체 목록 열기 ({len(available_branches)}개)", expanded=False):
            try:
                selected_branch = st.pills("지사", available_branches, selection_mode="multi", default=available_branches, key="br_pills_full", label_visibility="collapsed")
            except AttributeError:
                selected_branch = st.multiselect("지사 선택", available_branches, default=available_branches)
    else:
        try:
            selected_branch = st.pills("지사", available_branches, selection_mode="multi", default=available_branches, key="br_pills_lite", label_visibility="collapsed")
        except AttributeError:
            selected_branch = st.multiselect("지사 선택", available_branches, default=available_branches)
            
    if not selected_branch: selected_branch = available_branches
    
    st.markdown('</div>', unsafe_allow_html=True)

# 데이터 필터링
df_filtered = df[
    (df['본부'].isin(selected_hq)) &
    (df['지사'].isin(selected_branch))
]

# -----------------------------------------------------------------------------
# 4. KPI Section (Expert Context)
# -----------------------------------------------------------------------------
st.markdown("### 🚀 Executive Summary")

k1, k2, k3, k4 = st.columns(4)

tot_cnt = len(df_filtered)
tot_rev = df_filtered['월정료(VAT미포함)'].sum()
avg_susp = df_filtered['당월말_정지일수'].mean() if '당월말_정지일수' in df.columns else 0
risk_cnt = len(df_filtered[df_filtered['정지,설변구분'].str.contains('정지', na=False)])

# KPI Design with Helper Text
k1.metric("총 계약 건수", f"{tot_cnt:,.0f}", "Active Contracts")
k2.metric("총 월정료 (Revenue)", f"₩{tot_rev/10000:,.0f} 만", "Monthly Recurring")
k3.metric("평균 정지일수", f"{avg_susp:.1f} 일", "Suspension Avg", delta_color="off")
k4.metric("Risk Alert (정지)", f"{risk_cnt:,.0f} 건", f"Risk Ratio: {risk_cnt/tot_cnt*100:.1f}%", delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Visualizations (Top 10 Techniques)
# -----------------------------------------------------------------------------
tab_overview, tab_analysis, tab_grid = st.tabs(["📊 Performance & Structure", "📈 Deep Dive Analysis", "💾 Smart Data Grid"])

# [TAB 1] 종합 현황 (Dual Axis & Sunburst)
with tab_overview:
    row1_c1, row1_c2 = st.columns([2, 1])
    
    with row1_c1:
        st.subheader("🏢 본부별 효율성 분석 (Pareto Chart)")
        hq_agg = df_filtered.groupby('본부').agg({'계약번호':'count', '월정료(VAT미포함)':'sum'}).reset_index()
        hq_agg = hq_agg.sort_values('계약번호', ascending=False)
        
        # Dual Axis: Bar(건수) + Line(매출)
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig_dual.add_trace(
            go.Bar(x=hq_agg['본부'], y=hq_agg['계약번호'], name="계약 건수",
                   marker_color='#6366f1', opacity=0.8, width=0.5), # Indigo
            secondary_y=False
        )
        fig_dual.add_trace(
            go.Scatter(x=hq_agg['본부'], y=hq_agg['월정료(VAT미포함)'], name="매출 규모",
                       mode='lines+markers', line=dict(color='#f43f5e', width=3), marker=dict(size=8)), # Rose
            secondary_y=True
        )
        
        fig_dual.update_layout(
            template="plotly_white", 
            hovermode="x unified",
            height=450,
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center'),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        fig_dual.update_yaxes(title_text="계약 건수", secondary_y=False, showgrid=False)
        fig_dual.update_yaxes(title_text="매출 (원)", secondary_y=True, showgrid=True, gridcolor='#f1f5f9')
        
        st.plotly_chart(fig_dual, use_container_width=True)
        
    with row1_c2:
        st.subheader("🌐 조직 계층 구조 (Sunburst)")
        # Hierarchy: 본부 -> 지사
        if not df_filtered.empty:
            fig_sun = px.sunburst(
                df_filtered, 
                path=['본부', '지사'], 
                values='계약번호',
                color='계약번호',
                color_continuous_scale='Indigo',
                hover_data=['월정료(VAT미포함)']
            )
            fig_sun.update_layout(height=450, margin=dict(t=10, l=10, r=10, b=10))
            st.plotly_chart(fig_sun, use_container_width=True)

    # [Trend] 월별 추이 (Area Chart)
    st.subheader("📅 월별 실적 추이 (Trend Analysis)")
    if '년월_dt' in df_filtered.columns:
        trend_df = df_filtered.groupby('년월_dt').agg({'계약번호':'count', '월정료(VAT미포함)':'sum'}).reset_index()
        fig_trend = px.area(trend_df, x='년월_dt', y='계약번호', title="월별 계약 건수 변화", markers=True)
        fig_trend.update_traces(line_color='#0ea5e9', fill_color='rgba(14, 165, 233, 0.3)')
        fig_trend.update_layout(template="plotly_white", height=350, xaxis_title="기간", yaxis_title="건수")
        st.plotly_chart(fig_trend, use_container_width=True)

# [TAB 2] 심층 분석 (Bubble, Treemap, Ranking)
with tab_analysis:
    row2_c1, row2_c2 = st.columns([1, 1])
    
    with row2_c1:
        st.subheader("📊 지사별 성과 매트릭스 (Bubble)")
        # X: 건수, Y: 평균단가, Size: 총매출, Color: 본부
        branch_stats = df_filtered.groupby(['본부', '지사']).agg({
            '계약번호':'count', 
            '월정료(VAT미포함)':['mean', 'sum']
        }).reset_index()
        branch_stats.columns = ['본부', '지사', '건수', '평균단가', '총매출']
        
        fig_bub = px.scatter(
            branch_stats, x='건수', y='평균단가', 
            size='총매출', color='본부',
            hover_name='지사',
            title="건수 vs 단가 상관관계 (크기: 총매출)",
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_bub.update_layout(height=400)
        st.plotly_chart(fig_bub, use_container_width=True)
        
    with row2_c2:
        st.subheader("🧩 서비스 상품 구성 (Treemap)")
        # Treemap: 서비스(소) 비중
        if '서비스(소)' in df_filtered.columns:
            svc_cnt = df_filtered['서비스(소)'].value_counts().reset_index()
            svc_cnt.columns = ['서비스명', '건수']
            # Top 15만 표시
            fig_tree = px.treemap(
                svc_cnt.head(15), 
                path=['서비스명'], 
                values='건수',
                color='건수',
                color_continuous_scale='Teal'
            )
            fig_tree.update_layout(height=400, margin=dict(t=30, l=10, r=10, b=10))
            st.plotly_chart(fig_tree, use_container_width=True)

    st.markdown("---")
    
    # [Donut Charts] 비중 분석
    st.subheader("🍩 주요 카테고리별 점유율 (Market Share)")
    c_pie1, c_pie2, c_pie3 = st.columns(3)
    
    with c_pie1:
        fig1 = px.pie(df_filtered, names='출동/영상', hole=0.6, title="출동/영상 비중", color_discrete_sequence=px.colors.qualitative.Pastel1)
        fig1.update_traces(textinfo='percent+label')
        st.plotly_chart(fig1, use_container_width=True)
    with c_pie2:
        fig2 = px.pie(df_filtered, names='L형/i형', hole=0.6, title="L형/i형 비중", color_discrete_sequence=px.colors.qualitative.Pastel2)
        fig2.update_traces(textinfo='percent+label')
        st.plotly_chart(fig2, use_container_width=True)
    with c_pie3:
        fig3 = px.pie(df_filtered, names='정지,설변구분', hole=0.6, title="정지/설변 유형", color_discrete_sequence=px.colors.qualitative.Safe)
        fig3.update_traces(textinfo='percent+label')
        st.plotly_chart(fig3, use_container_width=True)

# [TAB 3] 데이터 그리드 (Styled Table)
with tab_grid:
    st.markdown("### 💾 Intelligent Data Grid")
    st.caption("조건부 서식이 적용된 데이터 테이블입니다. 컬럼 헤더를 클릭하여 정렬할 수 있습니다.")
    
    cols_to_show = ['본부', '지사', '고객번호', '상호', '월정료(VAT미포함)', '정지,설변구분', '이벤트시작일', '부실구분']
    valid_cols = [c for c in cols_to_show if c in df_filtered.columns]
    
    # [Condition] 정지는 붉은색 배경, 설변은 노란색 배경
    def color_coding(row):
        val = str(row.get('정지,설변구분', ''))
        if '정지' in val:
            return ['background-color: #fee2e2; color: #991b1b'] * len(row) # Light Red
        elif '설변' in val:
            return ['background-color: #fef9c3; color: #854d0e'] * len(row) # Light Yellow
        return [''] * len(row)

    styled_df = df_filtered[valid_cols].style.apply(color_coding, axis=1)
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=600,
        column_config={
            "월정료(VAT미포함)": st.column_config.NumberColumn("월정료", format="₩%d"),
            "이벤트시작일": st.column_config.DateColumn("이벤트 일자", format="YYYY-MM-DD"),
        }
    )
    
    # CSV Download
    csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 엑셀 호환 CSV 다운로드",
        data=csv,
        file_name='ktt_premium_export.csv',
        mime='text/csv'
    )
