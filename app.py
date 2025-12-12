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
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Data Loading & Logic
# -----------------------------------------------------------------------------
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

    # 3. 담당자 (Dropdown Expander)
    st.markdown("---")
    valid_managers = sorted(df[
        (df['본부'].isin(selected_hq)) & 
        (df['지사'].isin(selected_branch))
    ]['구역담당영업사원'].unique().tolist())
    if "미지정" in valid_managers:
        valid_managers.remove("미지정")
        valid_managers.append("미지정")

    c_mgr, c_opt = st.columns([2, 1])
    with c_mgr:
        st.markdown(f"##### 👤 담당자 선택 <span style='color:#64748b; font-size:0.9em'>({len(valid_managers)}명)</span>", unsafe_allow_html=True)
        # 담당자 드롭다운을 Expander 안에 넣거나 바로 노출
        selected_managers = st.multiselect(
            "담당자 검색 및 선택", 
            valid_managers, 
            default=valid_managers,
            placeholder="담당자를 선택하세요 (여러 명 가능)"
        )
        if not selected_managers: selected_managers = valid_managers

    with c_opt:
        st.markdown("##### ⚙️ 옵션 필터 (전체 적용)")
        c_t1, c_t2 = st.columns(2)
        with c_t1: kpi_target = st.toggle("KPI 대상만", False)
        with c_t2: arrears_only = st.toggle("체납 건만", False)
        
    st.markdown('</div>', unsafe_allow_html=True)

# [CORE LOGIC] Apply Filters Dynamically
mask = (df['본부'].isin(selected_hq)) & \
       (df['지사'].isin(selected_branch)) & \
       (df['구역담당영업사원'].isin(selected_managers))

if kpi_target: mask = mask & (df['KPI_Status'].str.contains('대상', na=False))
if arrears_only: mask = mask & (df['체납'] != '-') & (df['체납'] != 'Unclassified') & (df['체납'] != '미지정')

df_filtered = df[mask]

# -----------------------------------------------------------------------------
# 4. KPI Summary
# -----------------------------------------------------------------------------
st.markdown("### 🚀 Executive Summary")
k1, k2, k3, k4 = st.columns(4)

def fmt_money(val): return f"₩{val/10000:,.0f} 만"

susp_df = df_filtered[df_filtered['정지,설변구분'] == '정지']
chg_df = df_filtered[df_filtered['정지,설변구분'] == '설변']

k1.metric("⛔ 정지 건수", f"{len(susp_df):,.0f} 건", "Suspension Count")
k2.metric("⛔ 정지 월정료", fmt_money(susp_df['월정료(VAT미포함)'].sum()), "Suspension Revenue", delta_color="inverse")
k3.metric("🔄 설변 건수", f"{len(chg_df):,.0f} 건", "Change Count")
k4.metric("🔄 설변 월정료", fmt_money(chg_df['월정료(VAT미포함)'].sum()), "Change Revenue")

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

# [TAB 2] Operations (Enhanced with Metric Toggle & Collapsibles)
with tab_ops:
    st.markdown("### 🚦 다차원 구성비 분석 (Interactive Zone)")
    
    # [NEW] Metric Switcher (건수 vs 금액)
    c_sw1, c_sw2 = st.columns([1, 3])
    with c_sw1:
        try:
            metric_type = st.pills("📊 분석 기준", ["건수(Volume)", "금액(Revenue)"], default="건수(Volume)", selection_mode="single")
        except AttributeError:
            metric_type = st.radio("분석 기준", ["건수(Volume)", "금액(Revenue)"], horizontal=True)
    
    # Define value column based on selection
    val_col = '계약번호' if metric_type == "건수(Volume)" else '월정료(VAT미포함)'
    agg_func = 'count' if metric_type == "건수(Volume)" else 'sum'

    # Interactive Charts
    try:
        analysis_mode = st.pills("분석 항목", ["실적채널", "L형/i형", "출동/영상", "정지,설변구분"], default="정지,설변구분", selection_mode="single")
    except AttributeError:
        analysis_mode = st.radio("분석 항목", ["실적채널", "L형/i형", "출동/영상", "정지,설변구분"], horizontal=True)
    if not analysis_mode: analysis_mode = "정지,설변구분"

    col_dyn1, col_dyn2 = st.columns([1, 2])
    with col_dyn1:
        st.markdown(f"**{analysis_mode} 비중 (Pie)**")
        if analysis_mode in df_filtered.columns:
            mode_cnt = df_filtered.groupby(analysis_mode)[val_col].agg(agg_func).reset_index()
            mode_cnt.columns = ['구분', '값']
            fig_pie = px.pie(mode_cnt, values='값', names='구분', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
            fig_pie.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
    with col_dyn2:
        st.markdown(f"**{analysis_mode} 상세 ({metric_type})**")
        if analysis_mode in df_filtered.columns:
            mode_cnt = df_filtered.groupby(analysis_mode)[val_col].agg(agg_func).reset_index()
            mode_cnt.columns = ['구분', '값']
            fig_bar = px.bar(mode_cnt, x='구분', y='값', text='값', color='구분', title=f"{analysis_mode} 분포")
            fig_bar.update_layout(showlegend=False, template="plotly_white")
            if metric_type == "금액(Revenue)": fig_bar.update_traces(texttemplate='%{text:,.0f}')
            st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown("---")
    
    # [NEW] Suspension vs Change Breakdown by Hierarchy (Collapsible)
    st.subheader("🔍 정지 vs 설변 계층별 상세 분석")
    
    # 1. 본부별
    with st.expander("🏢 본부별 정지/설변 현황 (펼치기/접기)", expanded=True):
        hq_brk = df_filtered.groupby(['본부', '정지,설변구분'])[val_col].agg(agg_func).reset_index()
        hq_brk.columns = ['본부', '구분', '값']
        fig_hq_grp = px.bar(hq_brk, x='본부', y='값', color='구분', barmode='group', text='값', title=f"본부별 {metric_type}")
        if metric_type == "금액(Revenue)": fig_hq_grp.update_traces(texttemplate='%{text:,.0f}')
        st.plotly_chart(fig_hq_grp, use_container_width=True)

    # 2. 지사별
    with st.expander("📍 지사별 정지/설변 현황 (펼치기/접기)", expanded=False):
        br_brk = df_filtered.groupby(['지사', '정지,설변구분'])[val_col].agg(agg_func).reset_index()
        br_brk.columns = ['지사', '구분', '값']
        fig_br_grp = px.bar(br_brk, x='지사', y='값', color='구분', title=f"지사별 {metric_type} (Stacked)")
        st.plotly_chart(fig_br_grp, use_container_width=True)

    # 3. 담당자별 (Top 20)
    with st.expander("👤 담당자별 정지/설변 Top 20 (펼치기/접기)", expanded=False):
        mgr_brk = df_filtered.groupby(['구역담당영업사원', '정지,설변구분'])[val_col].agg(agg_func).reset_index()
        mgr_brk.columns = ['담당자', '구분', '값']
        # Sort by value to get Top 20
        top_mgrs = mgr_brk.groupby('담당자')['값'].sum().sort_values(ascending=False).head(20).index
        mgr_brk_top = mgr_brk[mgr_brk['담당자'].isin(top_mgrs)]
        
        fig_mgr_grp = px.bar(mgr_brk_top, x='값', y='담당자', color='구분', orientation='h', title=f"상위 담당자 {metric_type}")
        fig_mgr_grp.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_mgr_grp, use_container_width=True)

    st.markdown("---")
    
    # 정지일수 & 월정료 & 부실
    c_misc1, c_misc2 = st.columns(2)
    def extract_num(s):
        nums = re.findall(r'\d+', str(s))
        return int(nums[0]) if nums else 0

    with c_misc1:
        st.subheader("⏱️ 정지일수 구간")
        if '당월말_정지일수_구간' in df_filtered.columns:
            susp_dist = df_filtered['당월말_정지일수_구간'].value_counts().reset_index()
            susp_dist.columns = ['구간', '건수']
            susp_dist['s'] = susp_dist['구간'].apply(extract_num)
            susp_dist = susp_dist.sort_values('s')
            fig_susp = px.bar(susp_dist, x='건수', y='구간', orientation='h', text='건수', color='건수', color_continuous_scale='Reds')
            st.plotly_chart(fig_susp, use_container_width=True)
    with c_misc2:
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
