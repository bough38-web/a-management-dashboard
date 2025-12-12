import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

# -----------------------------------------------------------------------------
# 1. Enterprise Config & Design System
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Enterprise Analytics",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# [CSS] 기업용 대시보드 스타일링
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        /* Global Font & Reset */
        html, body, [class*="css"] {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            color: #1e293b;
        }
        .stApp {
            background-color: #f8fafc; /* Slate-50 */
        }
        
        /* Header Title Visibility Fix */
        .main-title {
            font-size: 2.5rem !important;
            font-weight: 800 !important;
            color: #0f172a !important; /* Dark Slate */
            margin-top: 10px !important;
            margin-bottom: 5px !important;
        }
        .sub-title {
            font-size: 1.2rem !important;
            color: #64748b !important;
            font-weight: 500 !important;
            margin-bottom: 20px !important;
        }
        
        /* Card Container */
        .card-container {
            background-color: #ffffff;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
            margin-bottom: 24px;
        }
        
        /* KPI Metrics Style */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        div[data-testid="stMetric"]:hover {
            border-color: #6366f1;
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        
        /* Pills Button Style */
        div[data-testid="stPills"] { gap: 8px; flex-wrap: wrap; }
        div[data-testid="stPills"] button[aria-selected="true"] {
            background: linear-gradient(135deg, #4338ca 0%, #3730a3 100%) !important;
            color: white !important;
            border: none;
            font-weight: 600;
            padding: 6px 16px;
        }
        div[data-testid="stPills"] button[aria-selected="false"] {
            background-color: #f1f5f9 !important;
            border: 1px solid #cbd5e1 !important;
            color: #475569 !important;
            font-weight: 500;
        }
        
        /* Tab Navigation */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; margin-bottom: 20px; }
        .stTabs [data-baseweb="tab"] {
            height: 44px; background-color: white; border-radius: 8px;
            padding: 0 20px; font-weight: 600; border: 1px solid #e2e8f0; color: #64748b;
        }
        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important; color: white !important; border: none;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Data Loading & Logic (Enhanced)
# -----------------------------------------------------------------------------
@st.cache_data
def load_enterprise_data():
    file_path = "data.csv"
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error("🚨 시스템 에러: 데이터 파일(data.csv)을 찾을 수 없습니다.")
        return pd.DataFrame()

    # [중요] 컬럼명 정리 및 매핑
    # 조회구분을 '정지,설변구분'으로 사용 (사용자 요청 반영)
    if '조회구분' in df.columns:
        df['정지,설변구분'] = df['조회구분']
    
    # KPI 컬럼 자동 탐지 (10월말, 11월말, 12월말 등 유동적 대응)
    kpi_cols = [c for c in df.columns if 'KPI차감' in c]
    if kpi_cols:
        df['KPI_Status'] = df[kpi_cols[0]] # 첫 번째 KPI 컬럼을 대표로 사용
    else:
        df['KPI_Status'] = '-'

    # 날짜 그룹화
    if '이벤트시작일' in df.columns:
        df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
        def categorize_period(dt):
            if pd.isnull(dt): return "기간 미상"
            if dt.year < 2025: return "2024년 이전"
            else: return f"'{str(dt.year)[-2:]}.{dt.month}"
        df['Period'] = df['이벤트시작일'].apply(categorize_period)
        
        def get_sort_key(dt):
            if pd.isnull(dt): return pd.Timestamp.min
            if dt.year < 2025: return pd.Timestamp("2024-12-31")
            return dt
        df['SortKey'] = df['이벤트시작일'].apply(get_sort_key)
    
    # 수치 변환 (쉼표 제거 포함)
    if '월정료(VAT미포함)' in df.columns:
        # 문자열로 변환 -> 쉼표 제거 -> 숫자로 변환
        df['월정료(VAT미포함)'] = df['월정료(VAT미포함)'].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce').fillna(0)
    
    numeric_cols = ['계약번호', '당월말_정지일수']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 결측 처리
    fill_cols = [
        '본부', '지사', '출동/영상', 'L형/i형', '정지,설변구분', 
        '서비스(소)', '부실구분', 'KPI_Status', '체납', 
        '당월말_정지일수_구간', '월정료 구간', '실적채널', '구역담당영업사원'
    ]
    for col in fill_cols:
        if col not in df.columns:
            df[col] = "Unclassified"
        else:
            df[col] = df[col].fillna("미지정")
            
    return df

df = load_enterprise_data()
if df.empty:
    st.stop()

# -----------------------------------------------------------------------------
# 3. Header & Dynamic Filters
# -----------------------------------------------------------------------------
with st.container():
    c_head1, c_head2 = st.columns([3, 1])
    with c_head1:
        st.markdown('<h1 class="main-title">KTT Enterprise Analytics</h1>', unsafe_allow_html=True)
        st.markdown('<div class="sub-title">Strategic Insights & Operational Dashboard</div>', unsafe_allow_html=True)
    with c_head2:
        st.markdown(f"<div style='text-align:right; color:#64748b; padding-top:25px; font-weight:500;'>Data Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}</div>", unsafe_allow_html=True)

# Filter Container
with st.container():
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    
    # 1. 본부 (Pills)
    all_hqs = sorted(df['본부'].unique().tolist())
    st.markdown("##### 🏢 본부 선택")
    if "hq_select" not in st.session_state: st.session_state.hq_select = all_hqs
    
    try:
        selected_hq = st.pills("HQ", all_hqs, selection_mode="multi", default=all_hqs, key="hq_pills", label_visibility="collapsed")
    except AttributeError:
        selected_hq = st.multiselect("HQ", all_hqs, default=all_hqs)
    if not selected_hq: selected_hq = all_hqs

    # 2. 지사 (Pills)
    st.markdown("---")
    valid_branches = sorted(df[df['본부'].isin(selected_hq)]['지사'].unique().tolist())
    st.markdown(f"##### 📍 지사 선택 <span style='color:#64748b; font-size:0.9em'>(총 {len(valid_branches)}개)</span>", unsafe_allow_html=True)
    
    if len(valid_branches) > 30:
        with st.expander(f"🔽 전체 지사 목록 보기 ({len(valid_branches)}개)", expanded=False):
            try:
                selected_branch = st.pills("Branch", valid_branches, selection_mode="multi", default=valid_branches, key="br_pills_full", label_visibility="collapsed")
            except:
                selected_branch = st.multiselect("Branch", valid_branches, default=valid_branches)
    else:
        try:
            selected_branch = st.pills("Branch", valid_branches, selection_mode="multi", default=valid_branches, key="br_pills_lite", label_visibility="collapsed")
        except:
            selected_branch = st.multiselect("Branch", valid_branches, default=valid_branches)
    if not selected_branch: selected_branch = valid_branches

    # 3. 담당자 (Dropdown) & 추가 필터
    st.markdown("---")
    valid_managers = sorted(df[
        (df['본부'].isin(selected_hq)) & 
        (df['지사'].isin(selected_branch))
    ]['구역담당영업사원'].unique().tolist())
    
    if "미지정" in valid_managers:
        valid_managers.remove("미지정")
        valid_managers.append("미지정")

    col_mgr, col_opt = st.columns([2, 1])
    
    with col_mgr:
        st.markdown(f"##### 👤 담당자 선택 <span style='color:#64748b; font-size:0.9em'>({len(valid_managers)}명)</span>", unsafe_allow_html=True)
        selected_managers = st.multiselect(
            "담당자 검색 및 선택", 
            valid_managers, 
            default=valid_managers,
            placeholder="담당자를 선택하세요 (여러 명 가능)"
        )
        if not selected_managers: selected_managers = valid_managers

    with col_opt:
        st.markdown("##### ⚙️ 옵션 필터")
        c_t1, c_t2 = st.columns(2)
        with c_t1: kpi_target = st.toggle("KPI 차감 '대상'만", False)
        with c_t2: arrears_only = st.toggle("체납 건만", False)
        
    st.markdown('</div>', unsafe_allow_html=True)

# Apply Filters
mask = (df['본부'].isin(selected_hq)) & \
       (df['지사'].isin(selected_branch)) & \
       (df['구역담당영업사원'].isin(selected_managers))

if kpi_target: mask = mask & (df['KPI_Status'].str.contains('대상', na=False))
if arrears_only: mask = mask & (df['체납'] != '-') & (df['체납'] != 'Unclassified')

df_filtered = df[mask]

# -----------------------------------------------------------------------------
# 4. KPI Summary
# -----------------------------------------------------------------------------
st.markdown("### 🚀 Executive Summary")
k1, k2, k3, k4 = st.columns(4)

tot_vol = len(df_filtered)
tot_rev = df_filtered['월정료(VAT미포함)'].sum()
avg_susp = df_filtered['당월말_정지일수'].mean() if '당월말_정지일수' in df.columns else 0
risk_cnt = len(df_filtered[df_filtered['정지,설변구분'].str.contains('정지', na=False)])

def fmt_money(val): return f"₩{val/10000:,.0f} 만"

k1.metric("총 계약 건수", f"{tot_vol:,.0f} 건", "Selected Scope")
k2.metric("총 월정료 (예상)", fmt_money(tot_rev), "Monthly Revenue")
k3.metric("평균 정지일수", f"{avg_susp:.1f} 일", "Avg Duration")
k4.metric("Risk Alert (정지)", f"{risk_cnt:,.0f} 건", f"Rate: {risk_cnt/tot_vol*100:.1f}%" if tot_vol>0 else "0%", delta_color="inverse")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. Advanced Analytics Tabs
# -----------------------------------------------------------------------------
tab_strategy, tab_ops, tab_data = st.tabs(["📊 전략 분석 (Strategy)", "🔍 운영 분석 (Operations)", "💾 데이터 그리드 (Data)"])

# [TAB 1] Strategy
with tab_strategy:
    r1_c1, r1_c2 = st.columns([2, 1])
    with r1_c1:
        st.subheader("📅 기간별 실적 성장 추이")
        if 'Period' in df_filtered.columns:
            trend_df = df_filtered.groupby(['Period', 'SortKey']).agg({'계약번호':'count'}).reset_index().sort_values('SortKey')
            fig_trend = px.area(trend_df, x='Period', y='계약번호', markers=True, title="계약 건수 변화 (Timeline)")
            fig_trend.update_traces(line_color='#4f46e5', fillcolor='rgba(79, 70, 229, 0.1)')
            fig_trend.update_layout(template="plotly_white", height=380, xaxis_title=None, yaxis_title="계약 건수")
            st.plotly_chart(fig_trend, use_container_width=True)
    with r1_c2:
        st.subheader("🌐 본부-지사 포트폴리오")
        if not df_filtered.empty:
            fig_sun = px.sunburst(df_filtered, path=['본부', '지사'], values='계약번호', color='계약번호', color_continuous_scale='Purples')
            fig_sun.update_layout(height=380, margin=dict(t=10, l=10, r=10, b=10))
            st.plotly_chart(fig_sun, use_container_width=True)
            
    st.subheader("🏢 본부별 효율성 분석 (Pareto)")
    hq_stats = df_filtered.groupby('본부').agg({'계약번호':'count', '월정료(VAT미포함)':'sum'}).reset_index().sort_values('계약번호', ascending=False)
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(go.Bar(x=hq_stats['본부'], y=hq_stats['계약번호'], name="계약 건수", marker_color='#3b82f6', opacity=0.8, width=0.5), secondary_y=False)
    fig_dual.add_trace(go.Scatter(x=hq_stats['본부'], y=hq_stats['월정료(VAT미포함)'], name="매출(원)", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
    fig_dual.update_layout(template="plotly_white", height=450, hovermode="x unified", legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"))
    st.plotly_chart(fig_dual, use_container_width=True)

# [TAB 2] Operations
with tab_ops:
    # 1. 인터랙티브 분석 존
    st.markdown("### 🚦 다차원 구성비 분석 (Interactive Zone)")
    try:
        analysis_mode = st.pills("분석 모드", ["실적채널", "L형/i형", "출동/영상", "정지,설변구분"], default="정지,설변구분", selection_mode="single")
    except AttributeError:
        analysis_mode = st.radio("분석 모드", ["실적채널", "L형/i형", "출동/영상", "정지,설변구분"], horizontal=True)
    if not analysis_mode: analysis_mode = "정지,설변구분"

    col_dyn1, col_dyn2 = st.columns([1, 2])
    with col_dyn1:
        st.markdown(f"**{analysis_mode} 비중 (Pie)**")
        if analysis_mode in df_filtered.columns:
            mode_cnt = df_filtered[analysis_mode].value_counts().reset_index()
            mode_cnt.columns = ['구분', '건수']
            fig_pie = px.pie(mode_cnt, values='건수', names='구분', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
            fig_pie.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
    with col_dyn2:
        st.markdown(f"**{analysis_mode} 상세 현황 (Bar)**")
        if analysis_mode in df_filtered.columns:
            mode_cnt = df_filtered[analysis_mode].value_counts().reset_index()
            mode_cnt.columns = ['구분', '건수']
            fig_bar = px.bar(mode_cnt, x='구분', y='건수', text='건수', color='구분', title=f"{analysis_mode} 분포")
            fig_bar.update_layout(showlegend=False, template="plotly_white")
            st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown("---")
    
    # 2. 지사별 성과 & 부실
    op_c1, op_c2 = st.columns([1, 1])
    with op_c1:
        st.subheader("📊 지사별 성과 매트릭스")
        br_kpi = df_filtered.groupby(['본부', '지사']).agg({'계약번호':'count', '월정료(VAT미포함)':['mean','sum']}).reset_index()
        br_kpi.columns = ['본부', '지사', '건수', '평균단가', '총매출']
        fig_bub = px.scatter(br_kpi, x='건수', y='평균단가', size='총매출', color='본부', hover_name='지사', template="plotly_white", color_discrete_sequence=px.colors.qualitative.G10)
        st.plotly_chart(fig_bub, use_container_width=True)
    with op_c2:
        st.subheader("⚠️ 부실 사유 분석")
        if '부실구분' in df_filtered.columns:
            bad_cnt = df_filtered['부실구분'].value_counts().reset_index()
            bad_cnt.columns = ['구분', '건수']
            bad_cnt = bad_cnt[~bad_cnt['구분'].isin(['-', 'Unclassified', '미지정'])]
            if not bad_cnt.empty:
                fig_bad = px.pie(bad_cnt, values='건수', names='구분', hole=0.5, color_discrete_sequence=px.colors.qualitative.Bold)
                st.plotly_chart(fig_bad, use_container_width=True)
            else:
                st.info("부실 데이터 없음")

    st.markdown("---")
    
    # 3. 정지/월정료 구간 (스마트 정렬)
    op_c3, op_c4 = st.columns(2)
    def extract_num(s):
        nums = re.findall(r'\d+', str(s))
        return int(nums[0]) if nums else 0

    with op_c3:
        st.subheader("⏱️ 정지일수 구간")
        if '당월말_정지일수_구간' in df_filtered.columns:
            susp_dist = df_filtered['당월말_정지일수_구간'].value_counts().reset_index()
            susp_dist.columns = ['구간', '건수']
            susp_dist['s'] = susp_dist['구간'].apply(extract_num)
            susp_dist = susp_dist.sort_values('s')
            fig_susp = px.bar(susp_dist, x='건수', y='구간', orientation='h', text='건수', color='건수', color_continuous_scale='Reds')
            st.plotly_chart(fig_susp, use_container_width=True)
    with op_c4:
        st.subheader("💰 월정료 가격대")
        if '월정료 구간' in df_filtered.columns:
            prc_dist = df_filtered['월정료 구간'].value_counts().reset_index()
            prc_dist.columns = ['구간', '건수']
            prc_dist['s'] = prc_dist['구간'].apply(extract_num)
            prc_dist = prc_dist.sort_values('s')
            fig_prc = px.bar(prc_dist, x='구간', y='건수', text='건수', color='건수', color_continuous_scale='Blues')
            st.plotly_chart(fig_prc, use_container_width=True)

# [TAB 3] Data Grid
with tab_data:
    st.subheader("💾 Intelligent Data Grid")
    
    d_cols = ['본부', '지사', '구역담당영업사원', 'Period', '고객번호', '상호', '월정료(VAT미포함)', '실적채널', 'L형/i형', '출동/영상', '정지,설변구분', '부실구분', 'KPI_Status']
    v_cols = [c for c in d_cols if c in df_filtered.columns]
    
    def style_row(row):
        st_val = str(row.get('정지,설변구분', ''))
        kpi_val = str(row.get('KPI_Status', ''))
        if '정지' in st_val: return ['background-color: #fee2e2; color: #b91c1c'] * len(row)
        elif '대상' in kpi_val: return ['background-color: #e0e7ff; color: #3730a3; font-weight: bold'] * len(row)
        return [''] * len(row)

    st.dataframe(
        df_filtered[v_cols].style.apply(style_row, axis=1),
        use_container_width=True,
        height=600,
        column_config={"월정료(VAT미포함)": st.column_config.NumberColumn("월정료", format="₩%d")}
    )
    
    st.markdown("---")
    st.markdown("#### 🔒 Secure Download")
    col_p, col_b = st.columns([1, 2])
    pwd = col_p.text_input("비밀번호", type="password", placeholder="****")
    if pwd == "3867":
        col_b.write(""); col_b.write("")
        st.success("인증 완료")
        st.download_button("📥 다운로드 (CSV)", df_filtered.to_csv(index=False).encode('utf-8-sig'), 'data.csv', 'text/csv')
    elif pwd:
        col_b.write(""); col_b.write("")
        st.error("비밀번호 불일치")
