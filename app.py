import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. 디자인 및 페이지 설정 (Design System)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Enterprise Dashboard",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 고급 CSS 스타일링 (SaaS 대시보드 느낌)
st.markdown("""
    <style>
        /* 전체 배경색 - 연한 회색으로 차분하게 */
        .stApp {
            background-color: #f4f6f9;
        }
        
        /* 사이드바 스타일 */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e0e0e0;
        }
        
        /* 컨테이너(카드) 스타일 정의 */
        .css-card {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            margin-bottom: 20px;
        }
        
        /* 헤더 폰트 스타일 */
        h1, h2, h3 {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
            color: #2c3e50;
            font-weight: 700;
        }
        
        /* KPI Metric 스타일 커스텀 */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #3b82f6; /* 포인트 컬러 */
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        div[data-testid="stMetricLabel"] { font-size: 0.85rem; color: #64748b; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #1e293b; font-weight: 800; }
        
        /* 탭 스타일 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 10px 20px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            border: 1px solid #e2e8f0;
        }
        .stTabs [aria-selected="true"] {
            background-color: #3b82f6;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = "data.csv"
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error("데이터 파일(data.csv)을 찾을 수 없습니다.")
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
            
    # 결측 문자열 처리
    text_cols = ['본부', '지사', '출동/영상', 'L형/i형', '정지,설변구분', '서비스(소)']
    for col in text_cols:
        if col not in df.columns:
            df[col] = "미분류"
        else:
            df[col] = df[col].fillna("미분류")
            
    return df

df = load_data()
if df.empty:
    st.stop()

# -----------------------------------------------------------------------------
# 3. 사이드바 (Control Panel)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🎛️ Control Panel")
    st.caption("KTT Management System")
    st.markdown("---")
    
    # 3.1 기간 필터
    if '년월' in df.columns:
        month_list = ["전체"] + sorted(df['년월'].unique().tolist(), reverse=True)
        selected_month = st.selectbox("📅 분석 기간 (Period)", month_list)
    else:
        selected_month = "전체"
        
    # 3.2 본부 필터
    hq_list = sorted(df['본부'].unique().tolist())
    selected_hq = st.multiselect("🏢 본부 선택 (Headquarters)", hq_list, default=hq_list)
    
    st.markdown("---")
    st.info("💡 **Tip**: 차트의 범례를 클릭하면 해당 항목을 숨길 수 있습니다.")

# 데이터 필터링
df_filtered = df.copy()
if selected_month != "전체":
    df_filtered = df_filtered[df_filtered['년월'] == selected_month]
if selected_hq:
    df_filtered = df_filtered[df_filtered['본부'].isin(selected_hq)]

# -----------------------------------------------------------------------------
# 4. 메인 대시보드
# -----------------------------------------------------------------------------

# 헤더 영역
c_hd1, c_hd2 = st.columns([3, 1])
with c_hd1:
    st.title("KTT Service Insights")
    st.markdown(f"**DATA DATE**: {pd.Timestamp.now().strftime('%Y-%m-%d')} | **TARGET**: {', '.join(selected_hq) if len(selected_hq) < 4 else 'Multiple HQs'}")

# KPI 요약 (Card UI)
st.markdown("### 🚀 Key Performance Indicators")
k1, k2, k3, k4 = st.columns(4)

total_vol = len(df_filtered)
total_rev = df_filtered['월정료(VAT미포함)'].sum()
avg_susp = df_filtered['당월말_정지일수'].mean()
risk_cnt = len(df_filtered[df_filtered['정지,설변구분'].str.contains('정지', na=False)])

k1.metric("총 계약 건수", f"{total_vol:,.0f}", "Total Contracts")
k2.metric("총 예상 매출", f"₩{total_rev/10000:,.0f} 만", "Monthly Revenue")
k3.metric("평균 정지일수", f"{avg_susp:.1f} 일", "Avg Suspension")
k4.metric("정지 리스크", f"{risk_cnt:,.0f} 건", "Risk Alerts", delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True)

# 탭 메뉴
tab_main, tab_detail, tab_data = st.tabs(["📊 대시보드 (Dashboard)", "🔍 심층 분석 (Analytics)", "💾 데이터 그리드 (Data)"])

# =============================================================================
# TAB 1: 대시보드 (Visual Impact)
# =============================================================================
with tab_main:
    # Row 1: 본부별 실적 (이중축 차트)
    st.subheader("🏢 본부별 매출 및 계약 규모")
    
    hq_stats = df_filtered.groupby('본부').agg({'계약번호':'count', '월정료(VAT미포함)':'sum'}).reset_index()
    
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Bar Chart (계약건수)
    fig_dual.add_trace(
        go.Bar(x=hq_stats['본부'], y=hq_stats['계약번호'], name="계약 건수", 
               marker_color='#3b82f6', opacity=0.8, text=hq_stats['계약번호'], textposition='auto'),
        secondary_y=False
    )
    # Line Chart (매출)
    fig_dual.add_trace(
        go.Scatter(x=hq_stats['본부'], y=hq_stats['월정료(VAT미포함)'], name="월정료(원)", 
                   mode='lines+markers+text', text=[f"{v/10000:.0f}만" for v in hq_stats['월정료(VAT미포함)']],
                   textposition="top center",
                   line=dict(color='#ef4444', width=3), marker=dict(size=8, color='#ef4444')),
        secondary_y=True
    )
    
    fig_dual.update_layout(
        template="plotly_white", 
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified"
    )
    fig_dual.update_yaxes(title_text="계약 건수 (건)", showgrid=False, secondary_y=False)
    fig_dual.update_yaxes(title_text="월정료 (원)", showgrid=True, gridcolor='#f1f5f9', secondary_y=True)
    
    st.plotly_chart(fig_dual, use_container_width=True)
    
    # Row 2: Sunburst & Treemap (Expert Visuals)
    col_sun, col_tree = st.columns(2)
    
    with col_sun:
        st.subheader("🌐 조직 계층 구조 (Sunburst)")
        st.caption("본부(Inner) → 지사(Outer) 순으로 데이터 비중을 시각화합니다.")
        # 데이터 집계
        sun_df = df_filtered.groupby(['본부', '지사']).size().reset_index(name='건수')
        fig_sun = px.sunburst(sun_df, path=['본부', '지사'], values='건수',
                              color='건수', color_continuous_scale='Blues')
        fig_sun.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=400)
        st.plotly_chart(fig_sun, use_container_width=True)
        
    with col_tree:
        st.subheader("🧩 서비스 유형 분포 (Treemap)")
        st.caption("사각형의 크기가 해당 서비스의 비중을 나타냅니다.")
        # 서비스 유형 집계
        tree_df = df_filtered['서비스(소)'].value_counts().reset_index()
        tree_df.columns = ['서비스명', '건수']
        # 상위 15개만 표현 (가독성)
        tree_df = tree_df.head(15)
        
        fig_tree = px.treemap(tree_df, path=['서비스명'], values='건수',
                              color='건수', color_continuous_scale='Tealgrn')
        fig_tree.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=400)
        st.plotly_chart(fig_tree, use_container_width=True)

# =============================================================================
# TAB 2: 심층 분석 (Deep Dive)
# =============================================================================
with tab_detail:
    # 1. 강북/강원 Special Zone
    st.markdown("### 🌲 강북/강원본부 집중 분석")
    
    gb_df = df[df['본부'].astype(str).str.contains("강북|강원")]
    
    if not gb_df.empty:
        gb_stats = gb_df.groupby('지사').agg({'계약번호':'count', '월정료(VAT미포함)':'mean'}).reset_index()
        
        # Bubble Chart for Multi-dimensional analysis
        fig_bub = px.scatter(gb_stats, x='지사', y='계약번호', 
                             size='월정료(VAT미포함)', color='지사',
                             title="지사별 건수(Y축) vs 평균단가(크기)",
                             labels={'계약번호':'계약 건수', '월정료(VAT미포함)':'평균 월정료'},
                             template='plotly_white')
        fig_bub.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_bub, use_container_width=True)
    else:
        st.info("선택된 필터 내에 강북/강원 본부 데이터가 없습니다.")
        
    st.markdown("---")
    
    # 2. 비중 분석 (Donut Charts)
    st.subheader("⚖️ 서비스 및 계약 유형 상세 비중")
    r2_c1, r2_c2, r2_c3 = st.columns(3)
    
    with r2_c1:
        st.markdown("**1. 출동 vs 영상**")
        fig1 = px.pie(df_filtered, names='출동/영상', hole=0.6, color_discrete_sequence=px.colors.sequential.RdBu)
        fig1.update_layout(showlegend=False, margin=dict(t=20, b=20))
        fig1.update_traces(textinfo='label+percent')
        st.plotly_chart(fig1, use_container_width=True)
        
    with r2_c2:
        st.markdown("**2. L형 vs i형**")
        fig2 = px.pie(df_filtered, names='L형/i형', hole=0.6, color_discrete_sequence=px.colors.sequential.Teal)
        fig2.update_layout(showlegend=False, margin=dict(t=20, b=20))
        fig2.update_traces(textinfo='label+percent')
        st.plotly_chart(fig2, use_container_width=True)
        
    with r2_c3:
        st.markdown("**3. 정지 vs 설변**")
        fig3 = px.pie(df_filtered, names='정지,설변구분', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig3.update_layout(showlegend=False, margin=dict(t=20, b=20))
        fig3.update_traces(textinfo='label+percent')
        st.plotly_chart(fig3, use_container_width=True)

# =============================================================================
# TAB 3: 데이터 그리드
# =============================================================================
with tab_data:
    st.markdown("### 💾 Raw Data Grid")
    
    with st.expander("🛠️ 컬럼 설정 및 필터링"):
        all_cols = df.columns.tolist()
        show_cols = st.multiselect("표시할 컬럼 선택", all_cols, default=all_cols[:8])
    
    st.dataframe(
        df_filtered[show_cols],
        use_container_width=True,
        height=600,
        column_config={
            "월정료(VAT미포함)": st.column_config.NumberColumn("월정료", format="₩%d"),
            "이벤트시작일": st.column_config.DateColumn("이벤트 일자", format="YYYY-MM-DD"),
        }
    )
    
    csv_data = df_filtered.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        "📥 CSV 다운로드 (Excel 호환)",
        csv_data,
        "ktt_dashboard_export.csv",
        "text/csv",
        key='download-csv'
    )
