import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. Page & Design Config (Premium & Luxury UI)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Premium Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 고급 CSS: 버튼 색상, 카드 디자인, 폰트
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        /* 1. 전체 폰트 및 배경 */
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
        }
        .stApp {
            background-color: #f8fafc; /* 밝은 회색 배경 */
        }
        
        /* 2. 고급스러운 버튼 스타일 (st.pills 타겟팅) */
        /* 선택된 알약 버튼 색상 변경 (기본 붉은색 -> 고급 인디고 그라데이션) */
        div[data-testid="stPills"] button[aria-selected="true"] {
            background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%) !important;
            color: white !important;
            border: none;
            box-shadow: 0 4px 6px rgba(79, 70, 229, 0.3);
            font-weight: 600;
        }
        div[data-testid="stPills"] button:hover {
            border-color: #4f46e5 !important;
            color: #4f46e5 !important;
        }
        
        /* 3. KPI 카드 디자인 (Shadow & Border) */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            border-left: 5px solid #4f46e5; /* 포인트 컬러 */
        }
        
        /* 4. 필터 컨테이너 (Glassmorphism 느낌) */
        .filter-box {
            background-color: #ffffff;
            padding: 25px;
            border-radius: 20px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
            border: 1px solid #f1f5f9;
            margin-bottom: 20px;
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
        df['년월_dt'] = df['이벤트시작일'].dt.to_period('M').dt.to_timestamp()
    
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
# 3. Dynamic Filter System (Luxury Button UI)
# -----------------------------------------------------------------------------
st.title("💎 KTT Strategic Insight")
st.markdown("### 🎯 Control Center")

with st.container():
    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    
    # [1] 본부 선택 (Pills UI)
    all_hqs = sorted(df['본부'].unique().tolist())
    st.markdown("**🏢 본부 선택 (Headquarters)** - `다중 선택 가능`")
    
    try:
        # key를 설정하여 상태 유지
        selected_hq = st.pills("본부", all_hqs, selection_mode="multi", default=all_hqs, key="hq_pills", label_visibility="collapsed")
    except AttributeError:
        selected_hq = st.multiselect("본부 선택", all_hqs, default=all_hqs)
    
    if not selected_hq: selected_hq = all_hqs

    # [2] 지사 선택 (Chained Interaction)
    st.markdown("---")
    # 선택된 본부에 속한 지사만 필터링
    available_branches = sorted(df[df['본부'].isin(selected_hq)]['지사'].unique().tolist())
    
    st.markdown(f"**📍 지사 선택 (Branches)** - `총 {len(available_branches)}개 지사 활성화`")
    
    # 지사 개수에 따라 UI 자동 최적화
    if len(available_branches) > 20:
        with st.expander(f"🔽 지사 전체 목록 펼치기 ({len(available_branches)}개)", expanded=False):
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

# 실제 데이터 필터링 (여기가 핵심: 선택한 버튼에 따라 데이터가 바뀜)
df_filtered = df[
    (df['본부'].isin(selected_hq)) &
    (df['지사'].isin(selected_branch))
]

# -----------------------------------------------------------------------------
# 4. KPI Section
# -----------------------------------------------------------------------------
st.markdown("### 🚀 Performance Overview")

k1, k2, k3, k4 = st.columns(4)

tot_cnt = len(df_filtered)
tot_rev = df_filtered['월정료(VAT미포함)'].sum()
avg_susp = df_filtered['당월말_정지일수'].mean() if '당월말_정지일수' in df.columns else 0
risk_cnt = len(df_filtered[df_filtered['정지,설변구분'].str.contains('정지', na=False)])

k1.metric("총 계약 건수", f"{tot_cnt:,.0f}", "Active Contracts")
k2.metric("총 월정료 (Revenue)", f"₩{tot_rev/10000:,.0f} 만", "VAT 별도")
k3.metric("평균 정지일수", f"{avg_susp:.1f} 일", "Suspension Avg", delta_color="off")
k4.metric("Risk Alert (정지)", f"{risk_cnt:,.0f} 건", f"Ratio: {risk_cnt/tot_cnt*100:.1f}%" if tot_cnt>0 else "0%", delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Visualizations (Fixed Errors)
# -----------------------------------------------------------------------------
tab_overview, tab_analysis, tab_grid = st.tabs(["📊 Performance & Structure", "📈 Deep Dive Analysis", "💾 Smart Data Grid"])

# [TAB 1] 종합 현황
with tab_overview:
    row1_c1, row1_c2 = st.columns([2, 1])
    
    with row1_c1:
        st.subheader("🏢 본부별 효율성 분석 (Pareto Chart)")
        hq_agg = df_filtered.groupby('본부').agg({'계약번호':'count', '월정료(VAT미포함)':'sum'}).reset_index()
        hq_agg = hq_agg.sort_values('계약번호', ascending=False)
        
        # Dual Axis Chart
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig_dual.add_trace(
            go.Bar(x=hq_agg['본부'], y=hq_agg['계약번호'], name="계약 건수",
                   marker_color='#4f46e5', opacity=0.8), # 고급 인디고 색상
            secondary_y=False
        )
        fig_dual.add_trace(
            go.Scatter(x=hq_agg['본부'], y=hq_agg['월정료(VAT미포함)'], name="매출 규모",
                       mode='lines+markers', line=dict(color='#f43f5e', width=3), marker=dict(size=8)),
            secondary_y=True
        )
        
        fig_dual.update_layout(template="plotly_white", hovermode="x unified", height=450, legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_dual, use_container_width=True)
        
    with row1_c2:
        st.subheader("🌐 조직 계층 구조")
        if not df_filtered.empty:
            fig_sun = px.sunburst(
                df_filtered, 
                path=['본부', '지사'], 
                values='계약번호',
                color='계약번호',
                color_continuous_scale='Purples', # Indigo 대신 Purples 사용 (에러 방지)
                hover_data=['월정료(VAT미포함)']
            )
            fig_sun.update_layout(height=450, margin=dict(t=10, l=10, r=10, b=10))
            st.plotly_chart(fig_sun, use_container_width=True)

    # Trend Chart
    st.subheader("📅 월별 실적 추이")
    if '년월_dt' in df_filtered.columns:
        trend_df = df_filtered.groupby('년월_dt').agg({'계약번호':'count', '월정료(VAT미포함)':'sum'}).reset_index()
        fig_trend = px.area(trend_df, x='년월_dt', y='계약번호', markers=True)
        # [수정됨] fill_color -> fillcolor 로 수정
        fig_trend.update_traces(line_color='#4f46e5', fillcolor='rgba(79, 70, 229, 0.2)')
        fig_trend.update_layout(template="plotly_white", height=300)
        st.plotly_chart(fig_trend, use_container_width=True)

# [TAB 2] 심층 분석
with tab_analysis:
    row2_c1, row2_c2 = st.columns([1, 1])
    
    with row2_c1:
        st.subheader("📊 지사별 성과 매트릭스")
        branch_stats = df_filtered.groupby(['본부', '지사']).agg({
            '계약번호':'count', 
            '월정료(VAT미포함)':['mean', 'sum']
        }).reset_index()
        branch_stats.columns = ['본부', '지사', '건수', '평균단가', '총매출']
        
        fig_bub = px.scatter(
            branch_stats, x='건수', y='평균단가', 
            size='총매출', color='본부',
            hover_name='지사',
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_bub.update_layout(height=400)
        st.plotly_chart(fig_bub, use_container_width=True)
        
    with row2_c2:
        st.subheader("🧩 서비스 상품 구성")
        if '서비스(소)' in df_filtered.columns:
            svc_cnt = df_filtered['서비스(소)'].value_counts().reset_index()
            svc_cnt.columns = ['서비스명', '건수']
            fig_tree = px.treemap(
                svc_cnt.head(15), 
                path=['서비스명'], 
                values='건수',
                color='건수',
                color_continuous_scale='Teal'
            )
            fig_tree.update_layout(height=400, margin=dict(t=10, l=10, r=10, b=10))
            st.plotly_chart(fig_tree, use_container_width=True)

    st.markdown("---")
    
    # Donut Charts
    st.subheader("🍩 카테고리별 비중")
    c_pie1, c_pie2, c_pie3 = st.columns(3)
    
    with c_pie1:
        fig1 = px.pie(df_filtered, names='출동/영상', hole=0.6, title="출동/영상 비중", color_discrete_sequence=px.colors.qualitative.Pastel1)
        st.plotly_chart(fig1, use_container_width=True)
    with c_pie2:
        fig2 = px.pie(df_filtered, names='L형/i형', hole=0.6, title="L형/i형 비중", color_discrete_sequence=px.colors.qualitative.Pastel2)
        st.plotly_chart(fig2, use_container_width=True)
    with c_pie3:
        fig3 = px.pie(df_filtered, names='정지,설변구분', hole=0.6, title="정지/설변 유형", color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig3, use_container_width=True)

# [TAB 3] 데이터 그리드
with tab_grid:
    st.markdown("### 💾 Intelligent Data Grid")
    
    cols_to_show = ['본부', '지사', '고객번호', '상호', '월정료(VAT미포함)', '정지,설변구분', '이벤트시작일', '부실구분']
    valid_cols = [c for c in cols_to_show if c in df_filtered.columns]
    
    def color_coding(row):
        val = str(row.get('정지,설변구분', ''))
        if '정지' in val:
            return ['background-color: #fee2e2; color: #991b1b'] * len(row)
        elif '설변' in val:
            return ['background-color: #fef9c3; color: #854d0e'] * len(row)
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
    
    csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 데이터 다운로드 (CSV)", csv, "ktt_data.csv", "text/csv")
