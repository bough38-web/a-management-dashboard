import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 (Page Configuration)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="전사 부실/정지 현황 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 커스터마이징 (CSS)
st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        div[data-testid="stMetricValue"] {font-size: 1.8rem;}
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 (Data Loading & Preprocessing)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    # 파일 경로 설정 (실제 배포 시에는 경로를 상대 경로로 맞춰주세요)
    file_path = "a_전사부실일일.xlsx - 정지_부실_통합_설변포함.csv"
    
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다: {file_path}")
        return pd.DataFrame()

    # 날짜 컬럼 변환
    if '이벤트시작일' in df.columns:
        df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
    
    # 숫자 컬럼 결측치 처리 (0으로 대체)
    cols_to_fill = ['월정료(VAT미포함)', '당월말_정지일수', '익월말_정지일수']
    for col in cols_to_fill:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 필터링을 위한 년/월 컬럼 생성
    df['년월'] = df['이벤트시작일'].dt.to_period('M').astype(str)
    
    return df

df = load_data()

if df.empty:
    st.stop()

# -----------------------------------------------------------------------------
# 3. 사이드바 - 필터링 (Sidebar Filters)
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 검색 필터")

# 3.1 본부 선택
all_headquarters = sorted(df['본부'].dropna().unique().tolist())
selected_hq = st.sidebar.multiselect("본부 선택", all_headquarters, default=all_headquarters)

# 3.2 지사 선택 (본부 선택에 따라 동적으로 변경)
if selected_hq:
    filtered_branches = df[df['본부'].isin(selected_hq)]['지사'].dropna().unique().tolist()
else:
    filtered_branches = []
    
selected_branch = st.sidebar.multiselect("지사 선택", sorted(filtered_branches), default=sorted(filtered_branches))

# 3.3 정지/설변 구분
all_types = sorted(df['정지,설변구분'].dropna().unique().tolist())
selected_type = st.sidebar.multiselect("유형 선택 (정지/설변)", all_types, default=all_types)

# 데이터 필터링 적용
df_filtered = df[
    (df['본부'].isin(selected_hq)) &
    (df['지사'].isin(selected_branch)) &
    (df['정지,설변구분'].isin(selected_type))
]

# -----------------------------------------------------------------------------
# 4. 메인 대시보드 (Main Dashboard)
# -----------------------------------------------------------------------------

st.title("📊 전사 부실/정지 현황 대시보드")
st.markdown("---")

# 4.1 KPI 지표 (Top Row Metrics)
total_contracts = len(df_filtered)
total_revenue = df_filtered['월정료(VAT미포함)'].sum()
avg_suspension_days = df_filtered['당월말_정지일수'].mean()
insolvency_count = df_filtered[df_filtered['부실구분'].notnull() & (df_filtered['부실구분'] != 'None')].shape[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("총 계약 건수", f"{total_contracts:,.0f} 건")
col2.metric("총 월정료 (예상)", f"₩{total_revenue:,.0f}")
col3.metric("평균 정지일수 (당월)", f"{avg_suspension_days:.1f} 일")
col4.metric("부실 의심 건수", f"{insolvency_count:,.0f} 건", delta_color="inverse")

st.markdown("---")

# 4.2 차트 영역 1 (Chart Row 1)
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("📅 월별 이벤트 발생 추이")
    # 월별 집계
    monthly_trend = df_filtered.groupby('년월').size().reset_index(name='건수')
    fig_trend = px.line(monthly_trend, x='년월', y='건수', markers=True, 
                        title='월별 발생 건수 추이', template="plotly_white")
    fig_trend.update_xaxes(type='category') # x축을 카테고리로 설정하여 간격 일정하게
    st.plotly_chart(fig_trend, use_container_width=True)

with c2:
    st.subheader("🏢 본부별 매출 현황")
    hq_revenue = df_filtered.groupby('본부')['월정료(VAT미포함)'].sum().reset_index()
    fig_bar = px.bar(hq_revenue, x='본부', y='월정료(VAT미포함)', 
                     text_auto='.2s', title='본부별 월정료 합계',
                     color='월정료(VAT미포함)', color_continuous_scale='Blues')
    st.plotly_chart(fig_bar, use_container_width=True)

# 4.3 차트 영역 2 (Chart Row 2)
c3, c4 = st.columns(2)

with c3:
    st.subheader("🧩 서비스 유형 분포")
    # 상위 10개 서비스만 표시, 나머지는 기타
    service_counts = df_filtered['서비스(소)'].value_counts()
    top_n = 7
    if len(service_counts) > top_n:
        top_services = service_counts[:top_n]
        other_count = service_counts[top_n:].sum()
        top_services['기타'] = other_count
        service_df = top_services.reset_index()
        service_df.columns = ['서비스명', '건수']
    else:
        service_df = service_counts.reset_index()
        service_df.columns = ['서비스명', '건수']
        
    fig_donut = px.pie(service_df, values='건수', names='서비스명', hole=0.4,
                       title='주요 서비스 상품 비율')
    st.plotly_chart(fig_donut, use_container_width=True)

with c4:
    st.subheader("⚠️ 유형별(정지/설변) 비중")
    type_counts = df_filtered['정지,설변구분'].value_counts().reset_index()
    type_counts.columns = ['구분', '건수']
    fig_pie = px.bar(type_counts, x='건수', y='구분', orientation='h',
                     title='정지 및 설변 유형 건수', color='건수', color_continuous_scale='Reds')
    st.plotly_chart(fig_pie, use_container_width=True)

# -----------------------------------------------------------------------------
# 5. 상세 데이터 보기 (Raw Data Expander)
# -----------------------------------------------------------------------------
with st.expander("📄 상세 데이터 목록 보기 (클릭하여 펼치기)"):
    st.dataframe(df_filtered.sort_values(by='이벤트시작일', ascending=False), use_container_width=True)
    
    # CSV 다운로드 버튼
    csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="필터링된 데이터 다운로드 (CSV)",
        data=csv,
        file_name='filtered_dashboard_data.csv',
        mime='text/csv',
    )