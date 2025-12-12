import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

# -----------------------------------------------------------------------------
# 1. Enterprise Config & Expert Design System
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Enterprise Analytics",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# [CSS] Top-tier Dashboard Styling
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        /* 1. Typography & Reset */
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
            color: #334155;
        }
        .stApp {
            background-color: #f8fafc; /* Slate-50 */
        }
        
        /* 2. Header Gradient Typography */
        .main-title {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-top: 10px;
        }
        .sub-title {
            font-size: 1.05rem;
            color: #64748b;
            font-weight: 500;
            margin-bottom: 25px;
        }
        
        /* 3. Glassmorphism Filter Container */
        .filter-container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
        }
        
        /* 4. KPI Cards (Hover Effect) */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            padding: 24px;
            border-radius: 16px;
            border: 1px solid #f1f5f9;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.1);
            border-color: #6366f1;
        }
        
        /* 5. Modern Pills Buttons */
        div[data-testid="stPills"] { gap: 8px; flex-wrap: wrap; }
        div[data-testid="stPills"] button[aria-selected="true"] {
            background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%) !important;
            color: white !important;
            border: none;
            box-shadow: 0 4px 10px rgba(79, 70, 229, 0.3);
            font-weight: 600;
            padding: 6px 18px;
            transition: all 0.2s;
        }
        div[data-testid="stPills"] button[aria-selected="false"] {
            background-color: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            color: #64748b !important;
            font-weight: 500;
        }
        div[data-testid="stPills"] button:hover {
            background-color: #eef2ff !important;
            border-color: #4f46e5 !important;
            color: #4f46e5 !important;
        }
        
        /* 6. Custom Tab Style */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; border-bottom: none; }
        .stTabs [data-baseweb="tab"] {
            height: 46px; background-color: white; border-radius: 10px;
            padding: 0 24px; font-weight: 600; border: 1px solid #e2e8f0; color: #64748b;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important; color: white !important; border: none;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }
        
        /* 7. Section Titles */
        .section-header {
            font-size: 1.1rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Expert Helper Functions
# -----------------------------------------------------------------------------
def format_korean_currency(value):
    """
    전문가 기법: 금액 크기에 따른 스마트 포맷팅
    - 100만 이상: '1.2백만'
    - 100만 미만: '850천'
    """
    if value == 0:
        return "0"
    elif abs(value) >= 1_000_000:
        return f"{value/1_000_000:,.1f}백만"
    else:
        return f"{value/1_000:,.0f}천"

@st.cache_data
def load_enterprise_data():
    file_path = "data.csv"
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error("🚨 데이터 파일을 찾을 수 없습니다.")
        return pd.DataFrame()

    # [전처리] 컬럼 매핑 및 정제
    if '조회구분' in df.columns:
        df['정지,설변구분'] = df['조회구분']
    
    kpi_cols = [c for c in df.columns if 'KPI차감' in c]
    df['KPI_Status'] = df[kpi_cols[0]] if kpi_cols else '-'

    # 날짜 및 기간 그룹화
    if '이벤트시작일' in df.columns:
        df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
        def categorize_period(dt):
            if pd.isnull(dt): return "기간 미상"
            if dt.year < 2025: return "2024년 이전"
            return f"'{str(dt.year)[-2:]}.{dt.month}"
        df['Period'] = df['이벤트시작일'].apply(categorize_period)
        
        def get_sort_key(dt):
            if pd.isnull(dt): return pd.Timestamp.min
            if dt.year < 2025: return pd.Timestamp("2024-12-31")
            return dt
        df['SortKey'] = df['이벤트시작일'].apply(get_sort_key)
    
    # 수치 변환 (쉼표 제거 안전 로직)
    if '월정료(VAT미포함)' in df.columns:
        df['월정료(VAT미포함)'] = df['월정료(VAT미포함)'].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce').fillna(0)
    
    for col in ['계약번호', '당월말_정지일수']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # 결측 처리
    target_cols = ['본부', '지사', '출동/영상', 'L형/i형', '정지,설변구분', '서비스(소)', '부실구분', '체납', '실적채널', '구역담당영업사원']
    for col in target_cols:
        if col not in df.columns: df[col] = "Unclassified"
        else: df[col] = df[col].fillna("미지정")
            
    return df

df = load_enterprise_data()
if df.empty: st.stop()

# -----------------------------------------------------------------------------
# 3. Control Center (Smart Layout)
# -----------------------------------------------------------------------------
# Header
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown('<div class="main-title">KTT Enterprise Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Strategic Insights & Operational Dashboard</div>', unsafe_allow_html=True)
with c2:
    st.markdown(f"<div style='text-align:right; color:#64748b; padding-top:25px; font-size:0.9rem;'>Updates: {pd.Timestamp.now().strftime('%Y-%m-%d')}</div>", unsafe_allow_html=True)

# Filter Logic (Progressive Disclosure)
with st.container():
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    
    # [1] 본부 (Always Visible)
    all_hqs = sorted(df['본부'].unique().tolist())
    st.markdown('<div class="section-header">🏢 본부 선택</div>', unsafe_allow_html=True)
    if "hq_select" not in st.session_state: st.session_state.hq_select = all_hqs
    
    try:
        selected_hq = st.pills("HQ", all_hqs, selection_mode="multi", default=all_hqs, key="hq_pills", label_visibility="collapsed")
    except AttributeError:
        selected_hq = st.multiselect("HQ", all_hqs, default=all_hqs)
    if not selected_hq: selected_hq = all_hqs

    # [2] 지사 (Smart Collapsible)
    st.markdown("---")
    valid_branches = sorted(df[df['본부'].isin(selected_hq)]['지사'].unique().tolist())
    st.markdown(f'<div class="section-header">📍 지사 선택 <span style="font-weight:400; font-size:0.9em; color:#64748b; margin-left:5px">({len(valid_branches)}개소)</span></div>', unsafe_allow_html=True)
    
    if len(valid_branches) > 15:
        with st.expander(f"🔽 지사 전체 목록 펼치기 ({len(valid_branches)}개)", expanded=False):
            try:
                selected_branch = st.pills("Branch", valid_branches, selection_mode="multi", default=valid_branches, key="br_pills_full", label_visibility="collapsed")
            except:
                selected_branch = st.multiselect("지사", valid_branches, default=valid_branches)
    else:
        try:
            selected_branch = st.pills("Branch", valid_branches, selection_mode="multi", default=valid_branches, key="br_pills_lite", label_visibility="collapsed")
        except:
            selected_branch = st.multiselect("지사", valid_branches, default=valid_branches)
    if not selected_branch: selected_branch = valid_branches

    # [3] 담당자 (Smart Collapsible - Same as Branch)
    st.markdown("---")
    valid_managers = sorted(df[
        (df['본부'].isin(selected_hq)) & 
        (df['지사'].isin(selected_branch))
    ]['구역담당영업사원'].unique().tolist())
    if "미지정" in valid_managers:
        valid_managers.remove("미지정")
        valid_managers.append("미지정")

    c_mgr, c_opt = st.columns([3, 1])
    
    with c_mgr:
        st.markdown(f'<div class="section-header">👤 담당자 선택 <span style="font-weight:400; font-size:0.9em; color:#64748b; margin-left:5px">({len(valid_managers)}명)</span></div>', unsafe_allow_html=True)
        
        # [NEW] 담당자 선택도 지사처럼 Pills + Expander 적용
        if len(valid_managers) > 20:
            with st.expander(f"🔽 담당자 전체 목록 펼치기 ({len(valid_managers)}명)", expanded=False):
                try:
                    selected_managers = st.pills("Manager", valid_managers, selection_mode="multi", default=valid_managers, key="mgr_pills_full", label_visibility="collapsed")
                except AttributeError:
                    selected_managers = st.multiselect("담당자", valid_managers, default=valid_managers)
        else:
            try:
                selected_managers = st.pills("Manager", valid_managers, selection_mode="multi", default=valid_managers, key="mgr_pills_lite", label_visibility="collapsed")
            except AttributeError:
                selected_managers = st.multiselect("담당자", valid_managers, default=valid_managers)
        
        if not selected_managers: selected_managers = valid_managers

    with c_opt:
        st.markdown('<div class="section-header">⚙️ 옵션 필터</div>', unsafe_allow_html=True)
        c_t1, c_t2 = st.columns(2)
        with c_t1: kpi_target = st.toggle("KPI 대상만", False)
        with c_t2: arrears_only = st.toggle("체납 건만", False)
        
    st.markdown('</div>', unsafe_allow_html=True)

# [CORE] Apply Filters
mask = (df['본부'].isin(selected_hq)) & \
       (df['지사'].isin(selected_branch)) & \
       (df['구역담당영업사원'].isin(selected_managers))

if kpi_target: mask = mask & (df['KPI_Status'].str.contains('대상', na=False))
if arrears_only: mask = mask & (df['체납'] != '-') & (df['체납'] != 'Unclassified') & (df['체납'] != '미지정')

df_filtered = df[mask]

# -----------------------------------------------------------------------------
# 4. Global Analysis Mode (Volume vs Revenue)
# -----------------------------------------------------------------------------
st.markdown("### 🚦 분석 모드 설정 (Analysis Context)")
col_mode, col_space = st.columns([1, 2])
with col_mode:
    try:
        # 건수/금액 전환 버튼 (중앙 관제)
        metric_mode = st.pills("분석 기준", ["건수 (Volume)", "금액 (Revenue)"], default="건수 (Volume)", selection_mode="single", key="global_metric")
    except:
        metric_mode = st.radio("분석 기준", ["건수 (Volume)", "금액 (Revenue)"], horizontal=True)

# 설정값 전역 변수화
VAL_COL = '계약번호' if metric_mode == "건수 (Volume)" else '월정료(VAT미포함)'
AGG_FUNC = 'count' if metric_mode == "건수 (Volume)" else 'sum'
FMT_FUNC = (lambda x: f"{x:,.0f}건") if metric_mode == "건수 (Volume)" else format_korean_currency

# -----------------------------------------------------------------------------
# 5. Executive Summary (Dynamic & Smart Formatted)
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🚀 Executive Summary")
k1, k2, k3, k4 = st.columns(4)

# Data Segmentation
susp_df = df_filtered[df_filtered['정지,설변구분'] == '정지']
chg_df = df_filtered[df_filtered['정지,설변구분'] == '설변']

# Calculate Metrics based on Mode
if metric_mode == "건수 (Volume)":
    v1, v2 = len(susp_df), len(chg_df)
    l1, l2 = "정지 건수", "설변 건수"
else:
    v1, v2 = susp_df['월정료(VAT미포함)'].sum(), chg_df['월정료(VAT미포함)'].sum()
    l1, l2 = "정지 금액", "설변 금액"

k1.metric(f"⛔ {l1}", FMT_FUNC(v1), "Suspension")
k2.metric(f"🔄 {l2}", FMT_FUNC(v2), "Change")
k3.metric("📅 평균 정지일수", f"{df_filtered['당월말_정지일수'].mean():.1f} 일", "Avg Duration")
# Risk Rate is always count based
risk_cnt = len(df_filtered[df_filtered['정지,설변구분'] == '정지'])
total_cnt = len(df_filtered)
k4.metric("⚠️ 정지 비율 (Rate)", f"{risk_cnt/total_cnt*100:.1f}%" if total_cnt>0 else "0%", "Suspension Rate", delta_color="inverse")

st.markdown("---")

# -----------------------------------------------------------------------------
# 6. Advanced Analytics Tabs
# -----------------------------------------------------------------------------
tab_strategy, tab_ops, tab_data = st.tabs(["📊 전략 분석 (Strategy)", "🔍 운영 분석 (Operations)", "💾 데이터 그리드 (Data)"])

# [TAB 1] Strategy View
with tab_strategy:
    r1_c1, r1_c2 = st.columns([2, 1])
    
    with r1_c1:
        st.subheader("📅 실적 트렌드 (Trend)")
        if 'Period' in df_filtered.columns:
            trend_df = df_filtered.groupby(['Period', 'SortKey'])[VAL_COL].agg(AGG_FUNC).reset_index().sort_values('SortKey')
            fig_trend = px.area(trend_df, x='Period', y=VAL_COL, markers=True, title=f"기간별 {metric_mode} 변화")
            fig_trend.update_traces(line_color='#4f46e5', fillcolor='rgba(79, 70, 229, 0.1)')
            fig_trend.update_layout(template="plotly_white", height=380, xaxis_title=None)
            if metric_mode == "금액 (Revenue)": fig_trend.update_yaxes(tickformat=".2s") # Simplify large numbers
            st.plotly_chart(fig_trend, use_container_width=True)
            
    with r1_c2:
        st.subheader("🌐 본부-지사 포트폴리오")
        if not df_filtered.empty:
            fig_sun = px.sunburst(df_filtered, path=['본부', '지사'], values=VAL_COL, color='본부', color_discrete_sequence=px.colors.qualitative.Prism)
            fig_sun.update_layout(height=380, margin=dict(t=10, l=10, r=10, b=10))
            st.plotly_chart(fig_sun, use_container_width=True)
            
    st.subheader("🏢 본부별 효율성 (Pareto)")
    hq_stats = df_filtered.groupby('본부').agg({
        '계약번호': 'count', 
        '월정료(VAT미포함)': 'sum'
    }).reset_index().sort_values('계약번호', ascending=False)
    
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    # 건수 (Bar)
    fig_dual.add_trace(go.Bar(x=hq_stats['본부'], y=hq_stats['계약번호'], name="건수", marker_color='#3b82f6', opacity=0.8), secondary_y=False)
    # 금액 (Line)
    fig_dual.add_trace(go.Scatter(x=hq_stats['본부'], y=hq_stats['월정료(VAT미포함)'], name="금액", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
    
    fig_dual.update_layout(template="plotly_white", height=450, hovermode="x unified", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_dual, use_container_width=True)

# [TAB 2] Operations View
with tab_ops:
    # 1. Interactive Analysis
    st.markdown("#### 🚦 다차원 상세 분석")
    try:
        sub_mode = st.pills("상세 항목", ["실적채널", "L형/i형", "출동/영상", "정지,설변구분"], default="정지,설변구분", selection_mode="single")
    except:
        sub_mode = st.radio("상세 항목", ["실적채널", "L형/i형", "출동/영상", "정지,설변구분"], horizontal=True)
    if not sub_mode: sub_mode = "정지,설변구분"

    c_dyn1, c_dyn2 = st.columns([1, 2])
    with c_dyn1:
        if sub_mode in df_filtered.columns:
            mode_data = df_filtered.groupby(sub_mode)[VAL_COL].agg(AGG_FUNC).reset_index()
            mode_data.columns = ['구분', '값']
            fig_pie = px.pie(mode_data, values='값', names='구분', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
            fig_pie.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
    with c_dyn2:
        if sub_mode in df_filtered.columns:
            mode_data = df_filtered.groupby(sub_mode)[VAL_COL].agg(AGG_FUNC).reset_index()
            mode_data.columns = ['구분', '값']
            fig_bar = px.bar(mode_data, x='구분', y='값', text='값', color='구분', title=f"{sub_mode}별 {metric_mode}")
            fig_bar.update_layout(showlegend=False, template="plotly_white")
            if metric_mode == "금액 (Revenue)": fig_bar.update_traces(texttemplate='%{text:.2s}')
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    
    # 2. Hierarchy Drill-down (Collapsible)
    st.subheader(f"🔍 계층별 {metric_mode} 상세")
    
    with st.expander("🏢 본부별 현황 (Click to Expand)", expanded=True):
        hq_brk = df_filtered.groupby(['본부', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
        hq_brk.columns = ['본부', '구분', '값']
        fig_hq = px.bar(hq_brk, x='본부', y='값', color='구분', barmode='group', text='값')
        if metric_mode == "금액 (Revenue)": fig_hq.update_traces(texttemplate='%{text:.2s}')
        st.plotly_chart(fig_hq, use_container_width=True)

    with st.expander("📍 지사별 현황 (Click to Expand)", expanded=False):
        br_brk = df_filtered.groupby(['지사', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
        br_brk.columns = ['지사', '구분', '값']
        fig_br = px.bar(br_brk, x='지사', y='값', color='구분', barmode='stack', title="지사별 누적 현황")
        st.plotly_chart(fig_br, use_container_width=True)

    with st.expander("👤 담당자별 Top 20 (Click to Expand)", expanded=False):
        mgr_brk = df_filtered.groupby(['구역담당영업사원', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
        mgr_brk.columns = ['담당자', '구분', '값']
        top_list = mgr_brk.groupby('담당자')['값'].sum().sort_values(ascending=False).head(20).index
        mgr_top = mgr_brk[mgr_brk['담당자'].isin(top_list)]
        fig_mgr = px.bar(mgr_top, x='값', y='담당자', color='구분', orientation='h')
        fig_mgr.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_mgr, use_container_width=True)

    st.markdown("---")
    
    # 3. Misc Charts (Sorted Smartly)
    c_m1, c_m2 = st.columns(2)
    def extract_num(s):
        nums = re.findall(r'\d+', str(s))
        return int(nums[0]) if nums else 0

    with c_m1:
        st.subheader("⏱️ 정지일수 구간")
        if '당월말_정지일수_구간' in df_filtered.columns:
            s_data = df_filtered.groupby('당월말_정지일수_구간')[VAL_COL].agg(AGG_FUNC).reset_index()
            s_data.columns = ['구간', '값']
            s_data['sort'] = s_data['구간'].apply(extract_num)
            s_data = s_data.sort_values('sort')
            fig_s = px.bar(s_data, x='값', y='구간', orientation='h', text='값', color='값', color_continuous_scale='Reds')
            st.plotly_chart(fig_s, use_container_width=True)

    with c_m2:
        st.subheader("💰 월정료 가격대")
        if '월정료 구간' in df_filtered.columns:
            p_data = df_filtered.groupby('월정료 구간')[VAL_COL].agg(AGG_FUNC).reset_index()
            p_data.columns = ['구간', '값']
            p_data['sort'] = p_data['구간'].apply(extract_num)
            p_data = p_data.sort_values('sort')
            fig_p = px.bar(p_data, x='구간', y='값', text='값', color='값', color_continuous_scale='Blues')
            if metric_mode == "금액 (Revenue)": fig_p.update_traces(texttemplate='%{text:.2s}')
            st.plotly_chart(fig_p, use_container_width=True)

# [TAB 3] Data Grid
with tab_data:
    st.subheader("💾 Intelligent Data Grid")
    
    # Secure Download
    c_pw, c_btn = st.columns([1, 3])
    pwd = c_pw.text_input("다운로드 비밀번호", type="password", placeholder="****")
    if pwd == "3867":
        c_btn.success("✅ 인증 완료")
        c_btn.download_button("📥 전체 데이터 다운로드 (CSV)", df_filtered.to_csv(index=False).encode('utf-8-sig'), 'ktt_data.csv', 'text/csv')
    
    st.markdown("---")
    
    # Table
    d_cols = ['본부', '지사', '구역담당영업사원', 'Period', '고객번호', '상호', '월정료(VAT미포함)', '실적채널', '정지,설변구분', '부실구분', 'KPI_Status']
    v_cols = [c for c in d_cols if c in df_filtered.columns]
    
    def style_row(row):
        status = str(row.get('정지,설변구분', ''))
        kpi = str(row.get('KPI_Status', ''))
        if '정지' in status: return ['background-color: #fee2e2; color: #b91c1c'] * len(row)
        elif '대상' in kpi: return ['background-color: #e0e7ff; color: #3730a3; font-weight: bold'] * len(row)
        return [''] * len(row)

    st.dataframe(
        df_filtered[v_cols].style.apply(style_row, axis=1),
        use_container_width=True,
        height=600,
        column_config={"월정료(VAT미포함)": st.column_config.NumberColumn("월정료", format="₩%d")}
    )
