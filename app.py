import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

# -----------------------------------------------------------------------------
# 1. Enterprise Config & Design System (Premium Theme)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Enterprise Analytics",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [CSS] HTML 스타일 이식 (카드, 배지, 그림자 등)
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        :root {
            --primary: #2563eb;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg-body: #f1f5f9;
            --bg-card: #ffffff;
            --text-main: #0f172a;
            --text-sub: #64748b;
        }

        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
            color: var(--text-main);
            background-color: var(--bg-body);
        }

        /* KPI Card Style */
        .kpi-card {
            background-color: var(--bg-card);
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.05);
            border: 1px solid #e2e8f0;
            border-left: 5px solid #cbd5e1; /* Default Color */
            transition: transform 0.2s;
            height: 100%;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }
        .kpi-title {
            font-size: 0.85rem;
            color: var(--text-sub);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .kpi-value {
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--text-main);
            line-height: 1.2;
        }
        .kpi-sub {
            font-size: 0.8rem;
            color: var(--text-sub);
            margin-top: 4px;
        }

        /* Chart Card Style */
        .chart-card {
            background-color: var(--bg-card);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            border: 1px solid #e2e8f0;
            margin-bottom: 24px;
        }
        .chart-header {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--text-main);
        }
        .badge {
            font-size: 0.75rem;
            padding: 4px 8px;
            border-radius: 4px;
            background: #f1f5f9;
            color: var(--text-sub);
            font-weight: 600;
        }

        /* Sidebar Header */
        .sidebar-header {
            font-size: 0.9rem;
            font-weight: 700;
            color: #475569;
            margin: 20px 0 10px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        /* Main Title */
        .main-title {
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-main);
            margin-bottom: 4px;
        }
        .main-subtitle {
            font-size: 1rem;
            color: var(--text-sub);
            margin-bottom: 30px;
        }
        
        /* Remove default streamlit padding */
        .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Logic: Data Loading & Processing
# -----------------------------------------------------------------------------
def format_korean_currency(value):
    if value == 0: return "0"
    elif abs(value) >= 100_000_000: return f"{value/100_000_000:,.1f}억"
    elif abs(value) >= 1_000_000: return f"{value/1_000_000:,.1f}백만"
    else: return f"{value/1_000:,.0f}천"

def get_custom_rank(branch_name):
    target_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
    branch_str = str(branch_name)
    for idx, keyword in enumerate(target_order):
        if keyword in branch_str:
            return idx
    return 999

@st.cache_data
def load_enterprise_data():
    file_path = "data.csv"
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        # Dummy Data Generation
        data = {
            '본부': ['강북/강원본부']*40 + ['서울본부']*20,
            '지사': ['중앙지사', '원주지사', '강북지사', '고양지사', '의정부지사', '강릉지사', '서대문지사', '남양주지사']*5 + ['강남지사']*20,
            '구역담당영업사원': [f'담당자{i}' for i in range(60)],
            '월정료(VAT미포함)': [20000] * 60,
            '정지,설변구분': ['정지', '설변'] * 30,
            'KPI_Status': ['대상', '비대상'] * 30,
            '체납': ['-'] * 60,
            '당월말_정지일수': [10] * 60,
            '계약번호': range(60),
            '이벤트시작일': pd.date_range('2025-01-01', periods=60)
        }
        df = pd.DataFrame(data)

    if '조회구분' in df.columns: df['정지,설변구분'] = df['조회구분']
    kpi_cols = [c for c in df.columns if 'KPI차감' in c]
    df['KPI_Status'] = df[kpi_cols[0]] if kpi_cols else '-'

    if '월정료(VAT미포함)' in df.columns:
        df['월정료(VAT미포함)'] = df['월정료(VAT미포함)'].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce').fillna(0)
    for col in ['계약번호', '당월말_정지일수']:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if '이벤트시작일' in df.columns:
        df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
        df['Period'] = df['이벤트시작일'].apply(lambda x: f"'{str(x.year)[-2:]}.{x.month}" if pd.notnull(x) and x.year >= 2025 else "2024년 이전")
        df['SortKey'] = df['이벤트시작일'].fillna(pd.Timestamp.min)

    target_cols = ['본부', '지사', '구역담당영업사원', '정지,설변구분', '체납']
    for col in target_cols:
        if col not in df.columns: df[col] = "Unclassified"
        else: df[col] = df[col].fillna("미지정")
    
    # [Optimized] Categorical Sorting
    custom_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
    # 지사명 정제 (지사 글자 포함 여부 등) - 여기서는 단순 포함 여부로 매핑
    # 실제로는 데이터에 맞게 정교화 필요. 우선 Rank 컬럼 유지.
    df['Branch_Rank'] = df['지사'].apply(get_custom_rank)
    
    return df

df = load_enterprise_data()
if df.empty: st.stop()

# -----------------------------------------------------------------------------
# 3. Sidebar Control Center
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Control Panel")
    
    # 1. 파일 업로드 (HTML 스타일)
    with st.container():
        st.caption("📁 데이터 파일 업로드 (.csv)")
        uploaded_file = st.file_uploader("Upload CSV", type="csv", label_visibility="collapsed")
        if uploaded_file:
            st.success("File Uploaded!")
            # 실제로는 여기서 df를 다시 로드하는 로직 필요
            
    st.markdown("---")
    
    # 2. Cascading Filters (Button Style using pills)
    all_hqs = sorted(df['본부'].unique().tolist())
    all_branches = sorted(df['지사'].unique().tolist(), key=lambda x: (get_custom_rank(x), x))
    all_managers = sorted(df['구역담당영업사원'].unique().tolist())

    # [State Management]
    if "hq_selection" not in st.session_state: st.session_state.hq_selection = []
    if "br_selection" not in st.session_state: st.session_state.br_selection = []
    
    # A. 본부
    st.markdown('<div class="sidebar-header">🏢 본부 선택</div>', unsafe_allow_html=True)
    sel_hq = st.pills("HQ", all_hqs, selection_mode="multi", key="hq_selection", label_visibility="collapsed")
    final_hq = sel_hq if sel_hq else all_hqs

    # B. 지사 (Cascading)
    subset_hq = df[df['본부'].isin(final_hq)]
    valid_branches = sorted(subset_hq['지사'].unique().tolist(), key=lambda x: (get_custom_rank(x), x))
    
    st.markdown(f'<div class="sidebar-header">📍 지사 선택 <span style="font-size:0.7em; color:#2563eb">({len(valid_branches)})</span></div>', unsafe_allow_html=True)
    # Filter valid selection
    st.session_state.br_selection = [b for b in st.session_state.br_selection if b in valid_branches]
    sel_branch = st.pills("Branch", valid_branches, selection_mode="multi", key="br_selection", label_visibility="collapsed")
    final_branch = sel_branch if sel_branch else valid_branches

    # C. 담당자 (Cascading)
    subset_br = subset_hq[subset_hq['지사'].isin(final_branch)]
    valid_managers = sorted(subset_br['구역담당영업사원'].unique().tolist())
    
    st.markdown(f'<div class="sidebar-header">👤 담당자 선택 <span style="font-size:0.7em; color:#2563eb">({len(valid_managers)})</span></div>', unsafe_allow_html=True)
    if len(valid_managers) > 50:
        sel_mgr = st.multiselect("Manager", valid_managers, label_visibility="collapsed", placeholder="담당자 검색")
    else:
        sel_mgr = st.pills("Manager", valid_managers, selection_mode="multi", label_visibility="collapsed")
    final_managers = sel_mgr if sel_mgr else valid_managers

    st.markdown("---")
    st.markdown('<div class="sidebar-header">⚙️ 보기 설정</div>', unsafe_allow_html=True)
    metric_mode = st.radio("집계 기준", ["건수 (Volume)", "금액 (Revenue)"], horizontal=True, label_visibility="collapsed")
    kpi_target = st.toggle("KPI 차감 대상만 보기", False)
    arrears_only = st.toggle("체납 건만 보기", False)

# [CORE] Apply Filters
mask = (df['본부'].isin(final_hq)) & (df['지사'].isin(final_branch)) & (df['구역담당영업사원'].isin(final_managers))
if kpi_target: mask = mask & (df['KPI_Status'].str.contains('대상', na=False))
if arrears_only: mask = mask & (df['체납'] != '-') & (df['체납'] != 'Unclassified') & (df['체납'] != '미지정')

df_filtered = df[mask].copy().sort_values(by=['Branch_Rank', '지사'])

# Config Vars
VAL_COL = '계약번호' if metric_mode == "건수 (Volume)" else '월정료(VAT미포함)'
AGG_FUNC = 'count' if metric_mode == "건수 (Volume)" else 'sum'
FMT_FUNC = (lambda x: f"{x:,.0f}건") if metric_mode == "건수 (Volume)" else format_korean_currency

# -----------------------------------------------------------------------------
# 4. View Switcher & KPI Cards
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">KTT Enterprise Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Strategic Insights & Operational Dashboard</div>', unsafe_allow_html=True)

# [UI] Button-style View Switcher (HTML의 상단 탭 구현)
view_mode = st.pills("View Mode", ["전략 분석 (Strategy)", "운영 분석 (Operations)", "데이터 그리드 (Data)"], 
                     default="전략 분석 (Strategy)", selection_mode="single", label_visibility="collapsed")

st.markdown("---")

# [UI] Premium KPI Cards Helper
def render_kpi(title, value, sub_text, color="#2563eb", icon="📊"):
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color: {color};">
            <div class="kpi-title"><span>{icon}</span> {title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub_text}</div>
        </div>
    """, unsafe_allow_html=True)

# Summary Metrics Calculation
susp_df = df_filtered[df_filtered['정지,설변구분'] == '정지']
chg_df = df_filtered[df_filtered['정지,설변구분'] == '설변']

if metric_mode == "건수 (Volume)":
    v1, v2 = len(susp_df), len(chg_df)
    l1, l2 = "정지 건수", "설변 건수"
else:
    v1, v2 = susp_df['월정료(VAT미포함)'].sum(), chg_df['월정료(VAT미포함)'].sum()
    l1, l2 = "정지 금액", "설변 금액"

risk_rate = (len(susp_df) / len(df_filtered) * 100) if len(df_filtered) > 0 else 0

# KPI Section (Always Visible)
k1, k2, k3, k4 = st.columns(4)
with k1: render_kpi(l1, FMT_FUNC(v1), "전월 대비 추이", "#ef4444", "⛔")
with k2: render_kpi(l2, FMT_FUNC(v2), "활성 변경 건", "#3b82f6", "🔄")
with k3: render_kpi("평균 정지일수", f"{df_filtered['당월말_정지일수'].mean():.1f} 일", "리스크 모니터링", "#f59e0b", "📅")
with k4: render_kpi("정지 비율", f"{risk_rate:.1f}%", "전체 모수 대비", "#10b981", "⚠️")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Dynamic Content (Based on View Switcher)
# -----------------------------------------------------------------------------

# [VIEW 1] 전략 분석
if "전략" in view_mode:
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.markdown('<div class="chart-card"><div class="chart-header">📅 실적 트렌드 <span class="badge">Monthly</span></div>', unsafe_allow_html=True)
        if 'Period' in df_filtered.columns and not df_filtered.empty:
            trend_df = df_filtered.groupby(['Period', 'SortKey'])[VAL_COL].agg(AGG_FUNC).reset_index().sort_values('SortKey')
            fig_trend = px.area(trend_df, x='Period', y=VAL_COL, markers=True)
            fig_trend.update_traces(line_color='#2563eb', fillcolor='rgba(37, 99, 235, 0.1)')
            fig_trend.update_layout(template="plotly_white", height=320, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None)
            if metric_mode == "금액 (Revenue)": fig_trend.update_yaxes(tickformat=".2s")
            st.plotly_chart(fig_trend, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="chart-card"><div class="chart-header">🌐 본부 포트폴리오</div>', unsafe_allow_html=True)
        if not df_filtered.empty:
            fig_sun = px.sunburst(df_filtered, path=['본부', '지사'], values=VAL_COL, color='본부', color_discrete_sequence=px.colors.qualitative.Prism)
            fig_sun.update_layout(height=320, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_sun, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="chart-card"><div class="chart-header">🏢 본부별 효율성 (Pareto Analysis)</div>', unsafe_allow_html=True)
    hq_stats = df_filtered.groupby('본부').agg({'계약번호': 'count', '월정료(VAT미포함)': 'sum'}).reset_index().sort_values('계약번호', ascending=False)
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(go.Bar(x=hq_stats['본부'], y=hq_stats['계약번호'], name="건수", marker_color='#3b82f6', opacity=0.8), secondary_y=False)
    fig_dual.add_trace(go.Scatter(x=hq_stats['본부'], y=hq_stats['월정료(VAT미포함)'], name="금액", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
    fig_dual.update_layout(template="plotly_white", height=350, margin=dict(t=10), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_dual, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# [VIEW 2] 운영 분석
elif "운영" in view_mode:
    # 상세 항목 필터 (버튼식)
    sub_mode = st.pills("분석 차원", ["실적채널", "L형/i형", "출동/영상", "정지,설변구분"], default="정지,설변구분", selection_mode="single")
    if not sub_mode: sub_mode = "정지,설변구분"
    
    col_op1, col_op2 = st.columns([1, 2])
    
    with col_op1:
        st.markdown(f'<div class="chart-card"><div class="chart-header">🍩 {sub_mode} 비중</div>', unsafe_allow_html=True)
        if sub_mode in df_filtered.columns:
            mode_data = df_filtered.groupby(sub_mode)[VAL_COL].agg(AGG_FUNC).reset_index()
            mode_data.columns = ['구분', '값']
            fig_pie = px.pie(mode_data, values='값', names='구분', hole=0.6, color_discrete_sequence=px.colors.qualitative.Safe)
            fig_pie.update_traces(textinfo='percent+label', textposition='inside')
            fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_op2:
        st.markdown(f'<div class="chart-card"><div class="chart-header">📊 {sub_mode}별 상세 현황</div>', unsafe_allow_html=True)
        if sub_mode in df_filtered.columns:
            mode_data = df_filtered.groupby(sub_mode)[VAL_COL].agg(AGG_FUNC).reset_index()
            mode_data.columns = ['구분', '값']
            mode_data = mode_data.sort_values('값')
            fig_bar = px.bar(mode_data, x='값', y='구분', orientation='h', text='값', color='구분')
            fig_bar.update_layout(showlegend=False, template="plotly_white", xaxis_visible=False, height=300, margin=dict(t=0,b=0))
            fig_bar.update_traces(texttemplate='%{text:,.0f}' if metric_mode=="건수 (Volume)" else '%{text:.2s}', textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="chart-card"><div class="chart-header">📍 지사별 현황 (Stacked)</div>', unsafe_allow_html=True)
    br_brk = df_filtered.groupby(['지사', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
    br_brk.columns = ['지사', '구분', '값']
    br_brk['Rank'] = br_brk['지사'].apply(get_custom_rank)
    sorted_branches = sorted(br_brk['지사'].unique(), key=lambda x: (get_custom_rank(x), x))
    
    fig_br = px.bar(br_brk, x='지사', y='값', color='구분', barmode='stack')
    fig_br.update_layout(
        template="plotly_white", height=350, margin=dict(t=10, b=20),
        xaxis={'categoryorder':'array', 'categoryarray': sorted_branches},
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig_br, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 하단 분석
    c_m1, c_m2 = st.columns(2)
    def extract_num(s):
        nums = re.findall(r'\d+', str(s))
        return int(nums[0]) if nums else 0

    with c_m1:
        st.markdown('<div class="chart-card"><div class="chart-header">⏱️ 정지일수 구간</div>', unsafe_allow_html=True)
        if '당월말_정지일수_구간' in df_filtered.columns:
            s_data = df_filtered.groupby('당월말_정지일수_구간')[VAL_COL].agg(AGG_FUNC).reset_index()
            s_data.columns = ['당월말_정지일수_구간', '값']
            s_data['sort'] = s_data['당월말_정지일수_구간'].apply(extract_num)
            s_data = s_data.sort_values('sort')
            fig_s = px.bar(s_data, x='값', y='당월말_정지일수_구간', orientation='h', text='값', color='값', color_continuous_scale='Reds')
            fig_s.update_layout(template="plotly_white", xaxis_visible=False, height=300, margin=dict(t=0,b=0))
            fig_s.update_traces(texttemplate='%{text:,.0f}' if metric_mode=="건수 (Volume)" else '%{text:.2s}', textposition='outside')
            st.plotly_chart(fig_s, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
            
    with c_m2:
        st.markdown('<div class="chart-card"><div class="chart-header">💰 월정료 가격대</div>', unsafe_allow_html=True)
        if '월정료 구간' in df_filtered.columns:
            p_data = df_filtered.groupby('월정료 구간')[VAL_COL].agg(AGG_FUNC).reset_index()
            p_data.columns = ['월정료 구간', '값']
            p_data['sort'] = p_data['월정료 구간'].apply(extract_num)
            p_data = p_data.sort_values('sort')
            fig_p = px.bar(p_data, x='월정료 구간', y='값', text='값', color='값', color_continuous_scale='Blues')
            fig_p.update_layout(template="plotly_white", yaxis_visible=False, height=300, margin=dict(t=0,b=0))
            fig_p.update_traces(texttemplate='%{text:,.0f}' if metric_mode=="건수 (Volume)" else '%{text:.2s}', textposition='outside')
            st.plotly_chart(fig_p, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# [VIEW 3] 데이터 그리드
elif "데이터" in view_mode:
    st.markdown('<div class="chart-card"><div class="chart-header">💾 Intelligent Data Grid</div>', unsafe_allow_html=True)
    
    c_pw, c_btn = st.columns([1, 4])
    with c_pw:
        pwd = st.text_input("다운로드 비밀번호", type="password", placeholder="****", label_visibility="collapsed")
    with c_btn:
        if pwd == "3867":
            st.download_button("📥 Excel/CSV 다운로드", df_filtered.to_csv(index=False).encode('utf-8-sig'), 'ktt_data.csv', 'text/csv')
        else:
            st.button("🔒 다운로드 잠금", disabled=True)
    
    st.markdown("---")
    d_cols = ['본부', '지사', '구역담당영업사원', 'Period', '고객번호', '상호', '월정료(VAT미포함)', '실적채널', '정지,설변구분', '부실구분', 'KPI_Status']
    v_cols = [c for c in d_cols if c in df_filtered.columns]
    
    st.dataframe(
        df_filtered[v_cols],
        use_container_width=True,
        height=600,
        column_config={
            "월정료(VAT미포함)": st.column_config.NumberColumn("월정료", format="₩%d"),
            "KPI_Status": st.column_config.TextColumn("KPI 상태", validate="^대상$"),
            "지사": st.column_config.Column("지사", help="지정된 순서로 정렬됨")
        }
    )
    st.markdown('</div>', unsafe_allow_html=True)
