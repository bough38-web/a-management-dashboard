import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. 디자인 및 페이지 설정 (Modern UI/UX)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Advanced Dashboard",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed" # 모바일 친화적으로 사이드바 기본 닫힘
)

# 고급 CSS (Glassmorphism & Card UI)
st.markdown("""
    <style>
        /* 배경 및 폰트 설정 */
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        .stApp {
            background-color: #f8f9fa;
            font-family: 'Pretendard', sans-serif;
        }
        
        /* 카드 스타일 (그림자 효과) */
        .metric-card {
            background-color: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-5px);
        }
        
        /* 헤더 스타일 */
        h1, h2, h3 { color: #1e3a8a; font-weight: 800; }
        
        /* 탭 스타일 업그레이드 */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #ffffff;
            border-radius: 20px;
            padding: 8px 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: #3b82f6;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 캐싱
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("data.csv")
    except FileNotFoundError:
        st.error("데이터 파일(data.csv)이 없습니다.")
        return pd.DataFrame()

    # 날짜 및 숫자 변환
    if '이벤트시작일' in df.columns:
        df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
        df['년월'] = df['이벤트시작일'].dt.to_period('M').astype(str)
    
    numeric_cols = ['월정료(VAT미포함)', '계약번호', '당월말_정지일수']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # 결측치 채우기
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
# 3. 상단 필터 영역 (Button/Pills Style) - 동적 필터링
# -----------------------------------------------------------------------------
st.title("💠 KTT Service Intelligence")
st.markdown("### 🎯 데이터 필터링 (Interactive Filters)")

# 상단에 배치하여 접근성 강화 (Expandable Container)
with st.container():
    c_filter1, c_filter2 = st.columns([1, 1])
    
    # 3.1 본부 선택 (Pills UI - 최신 Streamlit 기능)
    all_hqs = sorted(df['본부'].unique().tolist())
    with c_filter1:
        st.write("**🏢 본부 선택 (Headquarters)**")
        # st.pills가 없으면 multiselect로 fallback하는 안전장치
        try:
            selected_hq = st.pills("본부를 선택하세요", all_hqs, selection_mode="multi", default=all_hqs)
        except AttributeError:
            selected_hq = st.multiselect("본부 선택", all_hqs, default=all_hqs)
            
    if not selected_hq:
        selected_hq = all_hqs

    # 3.2 지사 선택 (동적 필터링)
    filtered_branches = sorted(df[df['본부'].isin(selected_hq)]['지사'].unique().tolist())
    with c_filter2:
        st.write(f"**📍 지사 선택 (Branch) - {len(filtered_branches)}개 지사**")
        # 지사는 개수가 많으므로 Multiselect 유지하되 Pills 느낌 내기
        selected_branch = st.multiselect("지사를 선택하세요", filtered_branches, default=filtered_branches)

    # 데이터 필터링 적용
    df_filtered = df[
        (df['본부'].isin(selected_hq)) &
        (df['지사'].isin(selected_branch))
    ]

st.markdown("---")

# -----------------------------------------------------------------------------
# 4. KPI 대시보드 (Gauge Chart & Metrics)
# -----------------------------------------------------------------------------
st.markdown("### 🚀 핵심 성과 지표 (KPIs)")

k1, k2, k3, k4 = st.columns(4)

# KPI 계산
total_vol = len(df_filtered)
total_rev = df_filtered['월정료(VAT미포함)'].sum()
avg_susp = df_filtered['당월말_정지일수'].mean()
risk_rate = (len(df_filtered[df_filtered['정지,설변구분'].str.contains('정지')]) / total_vol * 100) if total_vol > 0 else 0

# 게이지 차트 생성 함수 (속도계 모양)
def create_gauge(value, title, max_val, suffix=""):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title, 'font': {'size': 14}},
        number = {'suffix': suffix},
        gauge = {
            'axis': {'range': [None, max_val]},
            'bar': {'color': "#3b82f6"},
            'steps': [
                {'range': [0, max_val*0.3], 'color': "#e0f2fe"},
                {'range': [max_val*0.3, max_val*0.7], 'color': "#bae6fd"},
                {'range': [max_val*0.7, max_val], 'color': "#7dd3fc"}],
        }
    ))
    fig.update_layout(height=130, margin=dict(l=20,r=20,t=30,b=20), paper_bgcolor="rgba(0,0,0,0)")
    return fig

with k1:
    st.metric("총 계약 건수", f"{total_vol:,.0f} 건", "Target: 100%")
with k2:
    st.metric("총 월정료", f"₩{total_rev/10000:,.0f} 만", "VAT 별도")
with k3:
    # 평균 정지일수 게이지 (Max 180일 가정)
    st.plotly_chart(create_gauge(avg_susp, "평균 정지일수", 180, "일"), use_container_width=True)
with k4:
    # 정지 비율 게이지 (Max 50% 가정)
    fig_risk = create_gauge(risk_rate, "정지/부실 비율", 50, "%")
    fig_risk.update_traces(gauge_bar_color="#ef4444") # 빨간색 경고
    st.plotly_chart(fig_risk, use_container_width=True)

# -----------------------------------------------------------------------------
# 5. 메인 시각화 (Tabs)
# -----------------------------------------------------------------------------
tab_main, tab_motion, tab_detail = st.tabs(["📊 종합 분석", "🎬 트렌드 모션", "🔍 심층 리포트"])

# TAB 1: 종합 분석 (Dual Axis & Sunburst)
with tab_main:
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("🏢 본부별 실적 현황 (Dual-Axis)")
        hq_stats = df_filtered.groupby('본부').agg({'계약번호':'count', '월정료(VAT미포함)':'sum'}).reset_index()
        
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dual.add_trace(go.Bar(x=hq_stats['본부'], y=hq_stats['계약번호'], name="건수", marker_color='#3b82f6', opacity=0.7), secondary_y=False)
        fig_dual.add_trace(go.Scatter(x=hq_stats['본부'], y=hq_stats['월정료(VAT미포함)'], name="매출(원)", line=dict(color='#ef4444', width=3)), secondary_y=True)
        fig_dual.update_layout(template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_dual, use_container_width=True)
        
    with col_right:
        st.subheader("🌐 조직 분포 (Sunburst)")
        if not df_filtered.empty:
            fig_sun = px.sunburst(df_filtered, path=['본부', '지사'], values='계약번호', color='본부', color_discrete_sequence=px.colors.qualitative.Prism)
            fig_sun.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=350)
            st.plotly_chart(fig_sun, use_container_width=True)

# TAB 2: 트렌드 모션 (Animation)
with tab_motion:
    st.subheader("📅 시간 흐름에 따른 변화 (Animation Chart)")
    st.info("💡 하단의 **재생(Play)** 버튼을 누르면 월별 데이터 변화를 애니메이션으로 볼 수 있습니다.")
    
    if '년월' in df_filtered.columns:
        # 애니메이션을 위한 데이터 집계
        motion_df = df_filtered.groupby(['년월', '본부']).agg({'계약번호':'count', '월정료(VAT미포함)':'mean'}).reset_index()
        motion_df = motion_df.sort_values('년월')
        
        fig_ani = px.scatter(
            motion_df, 
            x="계약번호", 
            y="월정료(VAT미포함)", 
            animation_frame="년월", 
            animation_group="본부",
            size="계약번호", 
            color="본부", 
            hover_name="본부",
            range_x=[0, motion_df['계약번호'].max()*1.1],
            range_y=[0, motion_df['월정료(VAT미포함)'].max()*1.1],
            title="월별 본부 실적 변화 (Bubble Size: 계약건수)"
        )
        fig_ani.update_layout(height=500, template="plotly_white")
        st.plotly_chart(fig_ani, use_container_width=True)
    else:
        st.warning("날짜 데이터(년월)가 없어 애니메이션을 생성할 수 없습니다.")

# TAB 3: 심층 리포트 (Specific Analysis)
with tab_detail:
    st.markdown("### 🔍 다차원 상세 분석")
    
    # 강북/강원 분석
    gb_df = df[df['본부'].astype(str).str.contains("강북|강원")]
    if not gb_df.empty:
        st.markdown(f"#### 🌲 강북/강원본부 지사별 현황 ({len(gb_df)}건)")
        gb_stats = gb_df.groupby('지사')['계약번호'].count().reset_index().sort_values('계약번호', ascending=False)
        fig_gb = px.bar(gb_stats, x='지사', y='계약번호', color='계약번호', color_continuous_scale='Teal')
        st.plotly_chart(fig_gb, use_container_width=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**출동/영상 비중**")
        fig1 = px.pie(df_filtered, names='출동/영상', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        st.markdown("**L형/i형 비중**")
        fig2 = px.pie(df_filtered, names='L형/i형', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig2, use_container_width=True)
    with c3:
        st.markdown("**정지/설변 비중**")
        fig3 = px.pie(df_filtered, names='정지,설변구분', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig3, use_container_width=True)

# 데이터 다운로드
with st.expander("💾 원본 데이터 다운로드"):
    st.dataframe(df_filtered.head(100), use_container_width=True)
    st.download_button("CSV 다운로드", df_filtered.to_csv().encode('utf-8-sig'), "ktt_data.csv", "text/csv")
