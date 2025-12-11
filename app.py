import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 커스텀 스타일 (UI/UX)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT 서비스 현황 대시보드 Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 전문가 느낌의 커스텀 CSS (카드 디자인, 폰트, 여백 조정)
st.markdown("""
    <style>
        /* 전체 배경 및 폰트 */
        .main { background-color: #f8f9fa; }
        h1, h2, h3 { font-family: 'Suit', sans-serif; font-weight: 700; color: #333; }
        
        /* KPI 카드 스타일 */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        div[data-testid="stMetricLabel"] { font-size: 0.9rem; color: #666; }
        div[data-testid="stMetricValue"] { font-size: 1.6rem; color: #000; font-weight: bold; }
        
        /* 탭 스타일 */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            height: 50px; white-space: pre-wrap; background-color: #fff;
            border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .stTabs [aria-selected="true"] { background-color: #e3f2fd; color: #1976d2; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 데이터 로드 (Caching)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = "data.csv" # 파일명 고정
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error("데이터 파일(data.csv)을 찾을 수 없습니다.")
        return pd.DataFrame()

    # 전처리
    if '이벤트시작일' in df.columns:
        df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
        df['년월'] = df['이벤트시작일'].dt.to_period('M').astype(str)
    
    cols_numeric = ['월정료(VAT미포함)', '계약번호', '당월말_정지일수']
    for col in cols_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # 누락된 컬럼에 대한 방어 코드 (데이터가 없을 경우를 대비)
    required_cols = ['본부', '지사', '출동/영상', 'L형/i형', '정지,설변구분']
    for col in required_cols:
        if col not in df.columns:
            df[col] = "정보없음"
            
    return df

df = load_data()
if df.empty:
    st.stop()

# -----------------------------------------------------------------------------
# 3. 사이드바 - 글로벌 필터 (Button Style 느낌의 Radio/Select)
# -----------------------------------------------------------------------------
st.sidebar.title("🎛️ Control Panel")
st.sidebar.markdown("---")

# 날짜 필터 (데이터에 있는 기간 자동 추출)
if '년월' in df.columns:
    all_months = sorted(df['년월'].dropna().unique().tolist(), reverse=True)
    selected_month = st.sidebar.selectbox("📅 조회 년월 선택", ["전체"] + all_months)
else:
    selected_month = "전체"

# 본부 필터
all_hqs = sorted(df['본부'].unique().tolist())
st.sidebar.subheader("🏢 본부 필터")
# 직관적인 선택을 위해 multiselect 사용 (공간 효율성)
selected_hq = st.sidebar.multiselect("본부 선택 (다중 선택 가능)", all_hqs, default=all_hqs)

# 필터링 로직
df_filtered = df.copy()
if selected_month != "전체":
    df_filtered = df_filtered[df_filtered['년월'] == selected_month]
if selected_hq:
    df_filtered = df_filtered[df_filtered['본부'].isin(selected_hq)]

# -----------------------------------------------------------------------------
# 4. 메인 대시보드 레이아웃
# -----------------------------------------------------------------------------

st.title("📊 KTT 서비스 인사이트 대시보드")
st.markdown(f"**조회 기준:** {selected_month} | **데이터 건수:** {len(df_filtered):,.0f} 건")

# 탭 구성: 종합 현황 | 상세 분석 | 데이터 리스트
tab1, tab2, tab3 = st.tabs(["📋 종합 현황 (Overview)", "🔍 심층 분석 (Deep Dive)", "💾 원본 데이터"])

# =============================================================================
# TAB 1: 종합 현황 (핵심 시각화)
# =============================================================================
with tab1:
    # 1. KPI Cards Row
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    total_cnt = len(df_filtered)
    total_amt = df_filtered['월정료(VAT미포함)'].sum()
    suspension_cnt = len(df_filtered[df_filtered['정지,설변구분'].str.contains('정지', na=False)])
    change_cnt = len(df_filtered[df_filtered['정지,설변구분'].str.contains('설변', na=False)])

    kpi1.metric("총 계약 건수", f"{total_cnt:,.0f} 건", delta="전체 대상")
    kpi2.metric("총 월정료 (Revenue)", f"{total_amt/10000:,.0f} 만원", "VAT 별도")
    kpi3.metric("정지 발생", f"{suspension_cnt:,.0f} 건", delta_color="inverse")
    kpi4.metric("설비 변경", f"{change_cnt:,.0f} 건", delta_color="normal")

    st.markdown("---")

    # 2. 본부별 건수 & 매출 시각화 (Dual Axis Chart)
    st.subheader("🏢 본부별 실적 현황 (계약건수 vs 월정료)")
    
    hq_agg = df_filtered.groupby('본부').agg({
        '계약번호': 'count', 
        '월정료(VAT미포함)': 'sum'
    }).reset_index().rename(columns={'계약번호': '건수', '월정료(VAT미포함)': '금액'})
    
    # 이중축 차트 생성 (Expert Plotly Skill)
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Bar: 건수
    fig_dual.add_trace(
        go.Bar(x=hq_agg['본부'], y=hq_agg['건수'], name="계약 건수", marker_color='#5D9CEC', opacity=0.8),
        secondary_y=False
    )
    # Line: 금액
    fig_dual.add_trace(
        go.Scatter(x=hq_agg['본부'], y=hq_agg['금액'], name="월정료 합계", mode='lines+markers', 
                   line=dict(color='#FF6B6B', width=3), marker=dict(size=8)),
        secondary_y=True
    )
    
    fig_dual.update_layout(title_text="본부별 계약 건수 및 매출 규모", template="plotly_white", hovermode="x unified")
    fig_dual.update_yaxes(title_text="계약 건수", secondary_y=False)
    fig_dual.update_yaxes(title_text="월정료 (원)", secondary_y=True, tickformat=",")
    st.plotly_chart(fig_dual, use_container_width=True)

    # 3. 정지 vs 설변 (건수/금액) 비교
    st.subheader("⚖️ 정지 vs 설변 상세 비교")
    col_l, col_r = st.columns(2)
    
    type_agg = df_filtered.groupby('정지,설변구분').agg({'계약번호': 'count', '월정료(VAT미포함)': 'sum'}).reset_index()
    
    with col_l:
        # 건수 비교 (Pie)
        fig_type_cnt = px.pie(type_agg, values='계약번호', names='정지,설변구분', 
                              title='유형별 발생 건수 비중', hole=0.4,
                              color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_type_cnt.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_type_cnt, use_container_width=True)
        
    with col_r:
        # 금액 비교 (Bar)
        fig_type_amt = px.bar(type_agg, x='정지,설변구분', y='월정료(VAT미포함)',
                              title='유형별 금액(Revenue) 규모', text_auto='.2s',
                              color='정지,설변구분', color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_type_amt, use_container_width=True)

# =============================================================================
# TAB 2: 심층 분석 (Deep Dive)
# =============================================================================
with tab2:
    # 1. 강북/강원 본부 특화 시각화
    st.markdown("### 🌲 강북/강원본부 집중 분석")
    
    target_hq = "강북/강원본부"
    # 본부 이름에 '강북' 또는 '강원'이 들어가는 데이터 필터링 (정확한 명칭 매칭 필요)
    # 데이터 상의 정확한 명칭을 찾기 위해 str.contains 사용
    gangbuk_df = df[df['본부'].astype(str).str.contains("강북|강원")]
    
    if not gangbuk_df.empty:
        gb_agg = gangbuk_df.groupby('지사')['계약번호'].count().reset_index().sort_values(by='계약번호', ascending=False)
        
        # 컬러 그라데이션 Bar Chart
        fig_gb = px.bar(gb_agg, x='지사', y='계약번호',
                        title=f"{target_hq} 지사별 발생 현황",
                        text_auto=True,
                        color='계약번호', color_continuous_scale='Teal')
        st.plotly_chart(fig_gb, use_container_width=True)
    else:
        st.info("강북/강원 본부 데이터가 없습니다.")

    st.markdown("---")
    
    # 2. 서비스 유형별 비중 (도넛 차트 2개 병렬 배치)
    st.markdown("### 🧩 서비스 구성비 (Service Mix)")
    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        # 출동/영상 비중
        if '출동/영상' in df_filtered.columns:
            fig_svc1 = px.pie(df_filtered, names='출동/영상', title='출동 vs 영상 서비스 비중', 
                              color_discrete_sequence=px.colors.sequential.RdBu, hole=0.5)
            fig_svc1.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_svc1, use_container_width=True)

    with row2_col2:
        # L형/i형 비중
        if 'L형/i형' in df_filtered.columns:
            fig_svc2 = px.pie(df_filtered, names='L형/i형', title='L형 vs i형 서비스 비중', 
                              color_discrete_sequence=px.colors.sequential.Emrld, hole=0.5)
            fig_svc2.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_svc2, use_container_width=True)

# =============================================================================
# TAB 3: 원본 데이터 (Data Grid)
# =============================================================================
with tab3:
    st.subheader("💾 데이터 상세 조회 및 다운로드")
    
    # 컬럼 선택 옵션
    all_cols = df_filtered.columns.tolist()
    selected_cols = st.multiselect("표시할 컬럼 선택", all_cols, default=all_cols[:10])
    
    # 데이터프레임 표시
    st.dataframe(df_filtered[selected_cols], use_container_width=True, height=600)
    
    # CSV 다운로드
    csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 CSV로 다운로드",
        data=csv,
        file_name='ktt_dashboard_data.csv',
        mime='text/csv',
    )
