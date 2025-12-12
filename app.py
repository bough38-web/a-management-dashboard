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
        
        /* Header Title Visibility */
        .main-title {
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            color: #0f172a !important;
            margin-top: 10px !important;
            margin-bottom: 5px !important;
        }
        .sub-title {
            font-size: 1.1rem !important;
            color: #64748b !important;
            font-weight: 500 !important;
            margin-bottom: 20px !important;
        }
        
        /* Card Container */
        .card-container {
            background-color: #ffffff;
            border-radius: 16px;
            padding: 25px;
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
        
        /* Filter Label */
        .filter-label {
            font-size: 0.95rem;
            font-weight: 700;
            color: #334155;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
        }
        .count-badge {
            background-color: #e0e7ff;
            color: #4338ca;
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
            margin-left: 6px;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Data Loading & Logic
# -----------------------------------------------------------------------------
def format_korean_currency(value):
    if value == 0: return "0"
    elif abs(value) >= 100_000_000: return f"{value/100_000_000:,.1f}억"
    elif abs(value) >= 1_000_000: return f"{value/1_000_000:,.1f}백만"
    else: return f"{value/1_000:,.0f}천"

@st.cache_data
def load_enterprise_data():
    file_path = "data.csv"
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error("🚨 시스템 에러: 데이터 파일(data.csv)을 찾을 수 없습니다.")
        return pd.DataFrame()

    # 컬럼 매핑
    if '조회구분' in df.columns:
        df['정지,설변구분'] = df['조회구분']
    
    # KPI 컬럼
    kpi_cols = [c for c in df.columns if 'KPI차감' in c]
    df['KPI_Status'] = df[kpi_cols[0]] if kpi_cols else '-'

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
    
    # 수치 변환
    if '월정료(VAT미포함)' in df.columns:
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
    
    # 1. 본부 선택 (Pills - 항상 펼침)
    all_hqs = sorted(df['본부'].unique().tolist())
    st.markdown(f'<div class="filter-label">🏢 본부 선택 <span class="count-badge">{len(all_hqs)}</span></div>', unsafe_allow_html=True)
    
    if "hq_select" not in st.session_state: st.session_state.hq_select = all_hqs
    
    try:
        selected_hq = st.pills("HQ", all_hqs, selection_mode="multi", default=all_hqs, key="hq_pills", label_visibility="collapsed")
    except AttributeError:
        selected_hq = st.multiselect("HQ", all_hqs, default=all_hqs)
    if not selected_hq: selected_hq = all_hqs

    st.markdown("---")

    # 2. 지사 선택 (Expander - 깔끔하게 접기)
    valid_branches = sorted(df[df['본부'].isin(selected_hq)]['지사'].unique().tolist())
    st.markdown(f'<div class="filter-label">📍 지사 선택 <span class="count-badge">{len(valid_branches)}개소</span></div>', unsafe_allow_html=True)
    
    with st.expander(f"🔽 지사 전체 목록 펼치기 ({len(valid_branches)}개)", expanded=False):
        try:
            selected_branch = st.pills("Branch", valid_branches, selection_mode="multi", default=valid_branches, key="br_pills", label_visibility="collapsed")
        except:
            selected_branch = st.multiselect("Branch", valid_branches, default=valid_branches)
    if not selected_branch: selected_branch = valid_branches

    st.markdown("---")

    # 3. 담당자 선택 (Expander - 지사와 동일한 스타일 적용)
    valid_managers = sorted(df[
        (df['본부'].isin(selected_hq)) & 
        (df['지사'].isin(selected_branch))
    ]['구역담당영업사원'].unique().tolist())
    if "미지정" in valid_managers:
        valid_managers.remove("미지정")
        valid_managers.append("미지정")

    st.markdown(f'<div class="filter-label">👤 담당자 선택 <span class="count-badge">{len(valid_managers)}명</span></div>', unsafe_allow_html=True)
    
    # [IMPROVED] 담당자 선택 UI (지사와 동일한 Expander + Pills/Multiselect 구조)
    with st.expander(f"🔽 담당자 전체 목록 펼치기 ({len(valid_managers)}명)", expanded=False):
        if len(valid_managers) > 50:
             selected_managers = st.multiselect("Manager", valid_managers, default=valid_managers, label_visibility="collapsed", placeholder="담당자를 검색하거나 선택하세요")
        else:
            try:
                selected_managers = st.pills("Manager", valid_managers, selection_mode="multi", default=valid_managers, key="mgr_pills", label_visibility="collapsed")
            except AttributeError:
                selected_managers = st.multiselect("Manager", valid_managers, default=valid_managers)
    
    if not selected_managers: selected_managers = valid_managers

    st.markdown("---")

    # 4. 분석 기준 및 옵션 (가로 배치)
    c_met, c_opt = st.columns([1, 2])
    
    with c_met:
        st.markdown('<div class="filter-label">📊 분석 기준 (Metric)</div>', unsafe_allow_html=True)
        try:
            metric_mode = st.pills("Metric", ["건수 (Volume)", "금액 (Revenue)"], default="건수 (Volume)", selection_mode="single", label_visibility="collapsed")
        except:
            metric_mode = st.radio("Metric", ["건수 (Volume)", "금액 (Revenue)"], horizontal=True)
            
    with c_opt:
        st.markdown('<div class="filter-label">⚙️ 고급 필터 (Filter Options)</div>', unsafe_allow_html=True)
        c_t1, c_t2 = st.columns(2)
        with c_t1: kpi_target = st.toggle("🎯 KPI 차감 대상만 보기", False)
        with c_t2: arrears_only = st.toggle("💰 체납 건만 보기", False)
        
    st.markdown('</div>', unsafe_allow_html=True)

# [CORE LOGIC] Apply Filters Dynamically
mask = (df['본부'].isin(selected_hq)) & \
       (df['지사'].isin(selected_branch)) & \
       (df['구역담당영업사원'].isin(selected_managers))

if kpi_target: mask = mask & (df['KPI_Status'].str.contains('대상', na=False))
if arrears_only: mask = mask & (df['체납'] != '-') & (df['체납'] != 'Unclassified') & (df['체납'] != '미지정')

df_filtered = df[mask]

# Global Config
VAL_COL = '계약번호' if metric_mode == "건수 (Volume)" else '월정료(VAT미포함)'
AGG_FUNC = 'count' if metric_mode == "건수 (Volume)" else 'sum'
FMT_FUNC = (lambda x: f"{x:,.0f}건") if metric_mode == "건수 (Volume)" else format_korean_currency

# -----------------------------------------------------------------------------
# 4. KPI Summary (Split View)
# -----------------------------------------------------------------------------
st.markdown("### 🚀 Executive Summary")
k1, k2, k3, k4 = st.columns(4)

susp_df = df_filtered[df_filtered['정지,설변구분'] == '정지']
chg_df = df_filtered[df_filtered['정지,설변구분'] == '설변']

if metric_mode == "건수 (Volume)":
    v1, v2 = len(susp_df), len(chg_df)
    l1, l2 = "정지 건수", "설변 건수"
else:
    v1, v2 = susp_df['월정료(VAT미포함)'].sum(), chg_df['월정료(VAT미포함)'].sum()
    l1, l2 = "정지 금액", "설변 금액"

k1.metric(f"⛔ {l1}", FMT_FUNC(v1), "Suspension Total")
k2.metric(f"🔄 {l2}", FMT_FUNC(v2), "Change Total")
k3.metric("📅 평균 정지일수", f"{df_filtered['당월말_정지일수'].mean():.1f} 일", "Avg Duration")
risk_rate = (len(susp_df) / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
k4.metric("⚠️ 정지 비율", f"{risk_rate:.1f}%", "Suspension Rate", delta_color="inverse")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. Advanced Analytics (Stylish Charts)
# -----------------------------------------------------------------------------
tab_strategy, tab_ops, tab_data = st.tabs(["📊 전략 분석", "🔍 운영 분석", "💾 데이터 그리드"])

# [TAB 1] Strategy
with tab_strategy:
    r1_c1, r1_c2 = st.columns([2, 1])
    with r1_c1:
        st.markdown("##### 📅 실적 트렌드")
        if 'Period' in df_filtered.columns:
            trend_df = df_filtered.groupby(['Period', 'SortKey'])[VAL_COL].agg(AGG_FUNC).reset_index().sort_values('SortKey')
            fig_trend = px.area(trend_df, x='Period', y=VAL_COL, markers=True)
            fig_trend.update_traces(line_color='#4f46e5', fillcolor='rgba(79, 70, 229, 0.1)')
            fig_trend.update_layout(template="plotly_white", height=380, xaxis_title=None, margin=dict(l=20, r=20, t=20, b=20))
            if metric_mode == "금액 (Revenue)": fig_trend.update_yaxes(tickformat=".2s")
            st.plotly_chart(fig_trend, use_container_width=True)
            
    with r1_c2:
        st.markdown("##### 🌐 본부 포트폴리오")
        if not df_filtered.empty:
            fig_sun = px.sunburst(df_filtered, path=['본부', '지사'], values=VAL_COL, color='본부', color_discrete_sequence=px.colors.qualitative.Prism)
            fig_sun.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=20))
            st.plotly_chart(fig_sun, use_container_width=True)
            
    st.markdown("##### 🏢 본부별 효율성 (Pareto)")
    hq_stats = df_filtered.groupby('본부').agg({'계약번호': 'count', '월정료(VAT미포함)': 'sum'}).reset_index().sort_values('계약번호', ascending=False)
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(go.Bar(x=hq_stats['본부'], y=hq_stats['계약번호'], name="건수", marker_color='#3b82f6', opacity=0.8, marker_line_width=0), secondary_y=False)
    fig_dual.add_trace(go.Scatter(x=hq_stats['본부'], y=hq_stats['월정료(VAT미포함)'], name="금액", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
    fig_dual.update_layout(template="plotly_white", height=400, hovermode="x unified", legend=dict(orientation="h", y=1.1), margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_dual, use_container_width=True)

# [TAB 2] Operations (Fixed KeyError)
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
            fig_pie = px.pie(mode_data, values='값', names='구분', hole=0.6, color_discrete_sequence=px.colors.qualitative.Safe)
            fig_pie.update_traces(textinfo='percent+label', textposition='inside')
            fig_pie.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_pie, use_container_width=True)
    with c_dyn2:
        if sub_mode in df_filtered.columns:
            # [FIXED] Split aggregation and sorting to avoid KeyError
            mode_data = df_filtered.groupby(sub_mode)[VAL_COL].agg(AGG_FUNC).reset_index()
            mode_data.columns = ['구분', '값'] # Rename first
            mode_data = mode_data.sort_values('값', ascending=True) # Then sort
            
            # Stylish Bar Chart
            fig_bar = px.bar(mode_data, x='값', y='구분', orientation='h', text='값', color='구분', title=f"{sub_mode}별 현황")
            fig_bar.update_layout(showlegend=False, template="plotly_white", xaxis_visible=False, margin=dict(l=10, r=10, t=40, b=10))
            fig_bar.update_traces(texttemplate='%{text:,.0f}' if metric_mode=="건수 (Volume)" else '%{text:.2s}', textposition='outside', marker_line_width=0)
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    
    # 2. Hierarchy Drill-down
    st.markdown("#### 🔍 계층별 상세 (Drill-down)")
    
    with st.expander("🏢 본부별 현황 (Click to Expand)", expanded=True):
        hq_brk = df_filtered.groupby(['본부', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
        hq_brk.columns = ['본부', '구분', '값']
        fig_hq = px.bar(hq_brk, x='본부', y='값', color='구분', barmode='group', text='값', color_discrete_sequence=['#ef4444', '#3b82f6'])
        fig_hq.update_layout(template="plotly_white", margin=dict(t=20, b=20), legend=dict(orientation="h", y=1.1))
        fig_hq.update_traces(texttemplate='%{text:,.0f}' if metric_mode=="건수 (Volume)" else '%{text:.2s}', textposition='outside')
        st.plotly_chart(fig_hq, use_container_width=True)

    with st.expander("📍 지사별 현황 (Click to Expand)", expanded=False):
        br_brk = df_filtered.groupby(['지사', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
        br_brk.columns = ['지사', '구분', '값']
        fig_br = px.bar(br_brk, x='지사', y='값', color='구분', barmode='stack')
        fig_br.update_layout(template="plotly_white", margin=dict(t=20, b=20))
        st.plotly_chart(fig_br, use_container_width=True)

    with st.expander("👤 담당자별 Top 20 (Click to Expand)", expanded=False):
        mgr_brk = df_filtered.groupby(['구역담당영업사원', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
        mgr_brk.columns = ['담당자', '구분', '값']
        top_list = mgr_brk.groupby('담당자')['값'].sum().sort_values(ascending=False).head(20).index
        mgr_top = mgr_brk[mgr_brk['담당자'].isin(top_list)]
        fig_mgr = px.bar(mgr_top, x='값', y='담당자', color='구분', orientation='h')
        fig_mgr.update_layout(yaxis={'categoryorder':'total ascending'}, template="plotly_white", margin=dict(t=20, b=20))
        st.plotly_chart(fig_mgr, use_container_width=True)

    st.markdown("---")
    
    # 3. Misc Charts
    c_m1, c_m2 = st.columns(2)
    def extract_num(s):
        nums = re.findall(r'\d+', str(s))
        return int(nums[0]) if nums else 0

    with c_m1:
        st.markdown("##### ⏱️ 정지일수 구간")
        if '당월말_정지일수_구간' in df_filtered.columns:
            s_data = df_filtered.groupby('당월말_정지일수_구간')[VAL_COL].agg(AGG_FUNC).reset_index()
            s_data.columns = ['구간', '값']
            s_data['sort'] = s_data['구간'].apply(extract_num)
            s_data = s_data.sort_values('sort')
            fig_s = px.bar(s_data, x='값', y='구간', orientation='h', text='값', color='값', color_continuous_scale='Reds')
            fig_s.update_layout(template="plotly_white", xaxis_visible=False)
            fig_s.update_traces(texttemplate='%{text:,.0f}' if metric_mode=="건수 (Volume)" else '%{text:.2s}', textposition='outside')
            st.plotly_chart(fig_s, use_container_width=True)

    with c_m2:
        st.markdown("##### 💰 월정료 가격대")
        if '월정료 구간' in df_filtered.columns:
            p_data = df_filtered.groupby('월정료 구간')[VAL_COL].agg(AGG_FUNC).reset_index()
            p_data.columns = ['구간', '값']
            p_data['sort'] = p_data['구간'].apply(extract_num)
            p_data = p_data.sort_values('sort')
            fig_p = px.bar(p_data, x='구간', y='값', text='값', color='값', color_continuous_scale='Blues')
            fig_p.update_layout(template="plotly_white", yaxis_visible=False)
            fig_p.update_traces(texttemplate='%{text:,.0f}' if metric_mode=="건수 (Volume)" else '%{text:.2s}', textposition='outside')
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
