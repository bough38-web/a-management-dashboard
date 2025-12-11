import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. Expert Config & CSS (전문가급 디자인 설정)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Premium Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 고급 CSS: Glassmorphism, Custom Font, Card UI
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        /* 전체 폰트 및 배경 */
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
        }
        .stApp {
            background-color: #f0f2f6;
            background-image: linear-gradient(315deg, #f0f2f6 0%, #eef1f5 74%);
        }
        
        /* Glassmorphism Card Style */
        .glass-card {
            background: rgba(255, 255, 255, 0.7);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.05);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.18);
            padding: 20px;
            margin-bottom: 20px;
        }
        
        /* Metric Styling */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            padding: 15px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.04);
            border-left: 5px solid #4f46e5; /* Indigo accent */
            transition: transform 0.2s ease-in-out;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        }
        
        /* 탭 디자인 커스텀 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            background-color: #ffffff;
            border-radius: 30px;
            padding: 0px 24px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
            font-weight: 600;
            border: 1px solid #e5e7eb;
        }
        .stTabs [aria-selected="true"] {
            background-color: #4f46e5;
            color: white;
            border: none;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Data Logic (캐싱 및 전처리)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = "data.csv"
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error("데이터 파일(data.csv)이 없습니다.")
        return pd.DataFrame()

    # 날짜 처리
    if '이벤트시작일' in df.columns:
        df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
        df['년월'] = df['이벤트시작일'].dt.to_period('M').astype(str)
    
    # 숫자 처리
    numeric_cols = ['월정료(VAT미포함)', '계약번호', '당월말_정지일수']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # 결측 처리
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
# 3. Dynamic Filters (Expert Technique: Session State & Interactivity)
# -----------------------------------------------------------------------------
st.title("💎 KTT Executive Dashboard")
st.markdown("### 🎯 Smart Filtering System")

# 컨테이너로 감싸서 깔끔하게 배치
with st.container():
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    # [Step 1] 본부 선택 (Pills)
    all_hqs = sorted(df['본부'].unique().tolist())
    st.markdown("**1. 본부 선택 (Headquarters)**")
    
    # st.pills 사용 (Streamlit >= 1.40.0)
    try:
        selected_hq = st.pills("본부를 선택하세요", all_hqs, selection_mode="multi", default=all_hqs, key="hq_pills")
    except AttributeError:
        selected_hq = st.multiselect("본부 선택", all_hqs, default=all_hqs)
    
    if not selected_hq:
        selected_hq = all_hqs

    # [Step 2] 지사 선택 (Dynamic Button Generation based on HQ)
    st.markdown("---")
    st.markdown(f"**2. 지사 선택 (Branches) - {', '.join(selected_hq) if len(selected_hq)<3 else '다수 본부'} 소속**")
    
    # 본부에 해당하는 지사만 필터링
    available_branches = sorted(df[df['본부'].isin(selected_hq)]['지사'].unique().tolist())
    
    # 지사가 너무 많으면 Expandable 영역에 넣어서 UI 깔끔하게 유지
    if len(available_branches) > 15:
        with st.expander(f"📍 지사 목록 전체 보기 (총 {len(available_branches)}개) - 클릭하여 확장", expanded=True):
            try:
                selected_branch = st.pills("지사를 선택하세요", available_branches, selection_mode="multi", default=available_branches, key="branch_pills")
            except AttributeError:
                selected_branch = st.multiselect("지사 선택", available_branches, default=available_branches)
    else:
        try:
            selected_branch = st.pills("지사를 선택하세요", available_branches, selection_mode="multi", default=available_branches, key="branch_pills_small")
        except AttributeError:
            selected_branch = st.multiselect("지사 선택", available_branches, default=available_branches)

    if not selected_branch:
        selected_branch = available_branches

    st.markdown('</div>', unsafe_allow_html=True)

# 데이터 필터링 적용
df_filtered = df[
    (df['본부'].isin(selected_hq)) &
    (df['지사'].isin(selected_branch))
]

# -----------------------------------------------------------------------------
# 4. KPI & Metrics (Expert Contextual Display)
# -----------------------------------------------------------------------------
total_cnt = len(df_filtered)
total_amt = df_filtered['월정료(VAT미포함)'].sum()
suspension_cnt = len(df_filtered[df_filtered['정지,설변구분'].str.contains('정지', na=False)])
insolvency_cnt = len(df_filtered[df_filtered['부실구분'].notnull() & (df_filtered['부실구분'] != 'None')]) if '부실구분' in df_filtered.columns else 0

st.markdown("### 🚀 Performance Overview")
k1, k2, k3, k4 = st.columns(4)

# 고급 포맷팅 함수
def format_currency(val):
    return f"₩{val/10000:,.0f} 만"

k1.metric("Total Contracts", f"{total_cnt:,.0f} 건", "활성 계약 기준")
k2.metric("Total Revenue", format_currency(total_amt), "VAT 별도 (예상)")
k3.metric("Suspension Cases", f"{suspension_cnt:,.0f} 건", f"전체 대비 {suspension_cnt/total_cnt*100:.1f}%", delta_color="inverse")
k4.metric("Risk Alert", f"{insolvency_cnt:,.0f} 건", "부실 의심", delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Advanced Visualizations (Tabs)
# -----------------------------------------------------------------------------
tab_trend, tab_detail, tab_grid = st.tabs(["📊 종합 트렌드 & 구조", "🔍 유형별 심층 분석", "💾 스마트 데이터 그리드"])

# TAB 1: 종합 트렌드 (Sunburst & Dual Axis)
with tab_trend:
    col_dual, col_sun = st.columns([2, 1])
    
    with col_dual:
        st.subheader("📈 본부별 실적 이중축 분석")
        hq_agg = df_filtered.groupby('본부').agg({'계약번호':'count', '월정료(VAT미포함)':'sum'}).reset_index()
        
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dual.add_trace(
            go.Bar(x=hq_agg['본부'], y=hq_agg['계약번호'], name="계약 건수", 
                   marker_color='#4f46e5', opacity=0.8, radius=5),
            secondary_y=False
        )
        fig_dual.add_trace(
            go.Scatter(x=hq_agg['본부'], y=hq_agg['월정료(VAT미포함)'], name="매출(원)", 
                       mode='lines+markers', line=dict(color='#f43f5e', width=3)),
            secondary_y=True
        )
        fig_dual.update_layout(template="plotly_white", hovermode="x unified", height=400,
                               legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_dual, use_container_width=True)
        
    with col_sun:
        st.subheader("🌐 조직 계층 시각화")
        # Sunburst: 본부 -> 지사 계층 구조
        if not df_filtered.empty:
            fig_sun = px.sunburst(df_filtered, path=['본부', '지사'], values='계약번호',
                                  color='계약번호', color_continuous_scale='Blues')
            fig_sun.update_layout(height=400, margin=dict(t=10, l=10, r=10, b=10))
            st.plotly_chart(fig_sun, use_container_width=True)

# TAB 2: 심층 분석 (Funnel & Donut)
with tab_detail:
    st.markdown("#### 🔍 다각도 비중 분석")
    
    r1_c1, r1_c2, r1_c3 = st.columns(3)
    
    with r1_c1:
        st.markdown("**1. 출동 vs 영상 서비스**")
        fig_pie1 = px.pie(df_filtered, names='출동/영상', hole=0.6, 
                          color_discrete_sequence=px.colors.qualitative.Pastel1)
        fig_pie1.update_traces(textinfo='percent+label')
        fig_pie1.update_layout(showlegend=False, margin=dict(t=20, b=20))
        st.plotly_chart(fig_pie1, use_container_width=True)
        
    with r1_c2:
        st.markdown("**2. L형 vs i형 구분**")
        fig_pie2 = px.pie(df_filtered, names='L형/i형', hole=0.6, 
                          color_discrete_sequence=px.colors.qualitative.Pastel2)
        fig_pie2.update_traces(textinfo='percent+label')
        fig_pie2.update_layout(showlegend=False, margin=dict(t=20, b=20))
        st.plotly_chart(fig_pie2, use_container_width=True)
        
    with r1_c3:
        st.markdown("**3. 정지 및 설변 유형**")
        fig_pie3 = px.pie(df_filtered, names='정지,설변구분', hole=0.6, 
                          color_discrete_sequence=px.colors.qualitative.Safe)
        fig_pie3.update_traces(textinfo='percent+label')
        fig_pie3.update_layout(showlegend=False, margin=dict(t=20, b=20))
        st.plotly_chart(fig_pie3, use_container_width=True)
        
    st.markdown("---")
    
    # 강북/강원 데이터가 있을 경우 Funnel Chart
    gb_df = df[df['본부'].astype(str).str.contains("강북|강원")]
    if not gb_df.empty:
        st.markdown("#### 🌲 강북/강원본부 지사별 Funnel Chart")
        gb_agg = gb_df.groupby('지사')['계약번호'].count().reset_index().sort_values('계약번호', ascending=False)
        fig_funnel = px.funnel(gb_agg, x='계약번호', y='지사', title="지사별 계약 규모 깔때기 분석")
        fig_funnel.update_layout(template="simple_white")
        st.plotly_chart(fig_funnel, use_container_width=True)

# TAB 3: 스마트 데이터 그리드 (Conditional Formatting)
with tab_grid:
    st.markdown("### 💾 Intelligent Data Grid")
    
    # 주요 컬럼만 선택해서 보여주기
    display_cols = ['본부', '지사', '고객번호', '상호', '월정료(VAT미포함)', '정지,설변구분', '이벤트시작일', '부실구분']
    valid_cols = [c for c in display_cols if c in df_filtered.columns]
    
    # 스타일링된 데이터프레임 (조건부 서식)
    # 정지나 설변인 경우 배경색을 살짝 붉게 표시하는 로직
    def highlight_risk(row):
        val = str(row.get('정지,설변구분', ''))
        if '정지' in val:
            return ['background-color: #ffe4e6'] * len(row)
        elif '설변' in val:
            return ['background-color: #fff1f2'] * len(row)
        else:
            return [''] * len(row)

    styled_df = df_filtered[valid_cols].style.apply(highlight_risk, axis=1)
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=600,
        column_config={
            "월정료(VAT미포함)": st.column_config.NumberColumn("월정료", format="₩%d"),
            "이벤트시작일": st.column_config.DateColumn("이벤트 날짜", format="YYYY-MM-DD"),
        }
    )
    
    # CSV 다운로드
    csv_data = df_filtered.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 전체 데이터 다운로드 (Excel 호환 CSV)",
        data=csv_data,
        file_name="ktt_premium_data.csv",
        mime="text/csv"
    )
