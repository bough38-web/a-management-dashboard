import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

# -----------------------------------------------------------------------------
# 1. Enterprise Config & Style
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Enterprise Analytics",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [CSS] Refined Design System
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        /* Global Font & Reset */
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
            color: #1e293b;
        }
        .stApp {
            background-color: #f8fafc;
        }
        
        /* Custom Header */
        .main-title {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            font-size: 1rem;
            color: #64748b;
            margin-bottom: 2rem;
        }
        
        /* Sidebar Polish */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
        }
        .sidebar-header {
            font-size: 0.9rem;
            font-weight: 700;
            color: #475569;
            margin: 15px 0 8px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .count-badge {
            background-color: #e0e7ff;
            color: #4338ca;
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
        }
        
        /* Metric Cards Enhancement */
        div[data-testid="stMetric"] {
            background-color: white;
            padding: 15px 20px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: box-shadow 0.2s ease;
        }
        div[data-testid="stMetric"]:hover {
            border-color: #6366f1;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Helper Functions (Logic & Charts)
# -----------------------------------------------------------------------------
def format_korean_currency(value):
    """Formats large numbers into Korean currency units."""
    if value == 0: return "0"
    abs_val = abs(value)
    if abs_val >= 100_000_000: return f"{value/100_000_000:,.1f}억"
    elif abs_val >= 1_000_000: return f"{value/1_000_000:,.1f}백만"
    else: return f"{value/1_000:,.0f}천"

def safe_extract_num(s):
    """Safely extracts the first number from a string."""
    try:
        nums = re.findall(r'\d+', str(s))
        return int(nums[0]) if nums else 0
    except:
        return 0

def create_bar_chart(df, x, y, color=None, orientation='v', text=None, title=None, height=400):
    """Factory function for consistent bar charts."""
    fig = px.bar(
        df, x=x, y=y, color=color, text=text, orientation=orientation,
        title=title, color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig.update_layout(
        template="plotly_white", 
        height=height, 
        margin=dict(l=20, r=20, t=40 if title else 20, b=20),
        xaxis_title=None, 
        yaxis_title=None
    )
    return fig

# -----------------------------------------------------------------------------
# 3. Data Loading
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = "data.csv"
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        # Fallback: Create dummy data for demonstration if file is missing
        st.warning("⚠️ 'data.csv' 파일을 찾을 수 없어 데모 데이터를 생성합니다.")
        data = {
            '본부': ['서울본부', '경기본부', '부산본부'] * 50,
            '지사': ['강남지사', '수원지사', '해운대지사'] * 50,
            '구역담당영업사원': [f'매니저{i}' for i in range(150)],
            '이벤트시작일': pd.date_range(start='2024-01-01', periods=150, freq='D'),
            '월정료(VAT미포함)': [x * 10000 for x in range(1, 151)],
            '정지,설변구분': ['정지', '설변', '정지'] * 50,
            '당월말_정지일수': [x % 30 for x in range(150)],
            'KPI차감여부': ['대상', '비대상'] * 75,
            '체납': ['-'] * 140 + ['Y'] * 10,
            '계약번호': range(1000, 1150)
        }
        df = pd.DataFrame(data)

    # 1. Column Standardization
    col_map = {'조회구분': '정지,설변구분'}
    df.rename(columns=col_map, inplace=True)
    
    # 2. Type Conversion
    if '월정료(VAT미포함)' in df.columns and df['월정료(VAT미포함)'].dtype == object:
        df['월정료(VAT미포함)'] = (df['월정료(VAT미포함)'].astype(str)
                                 .str.replace(',', '')
                                 .apply(pd.to_numeric, errors='coerce')
                                 .fillna(0))
    
    num_cols = ['계약번호', '당월말_정지일수']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 3. Date Processing
    if '이벤트시작일' in df.columns:
        df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
        df['Period'] = df['이벤트시작일'].apply(
            lambda x: f"'{str(x.year)[-2:]}.{x.month}" if pd.notnull(x) and x.year >= 2025 else ("2024년 이전" if pd.notnull(x) else "기간 미상")
        )
        df['SortKey'] = df['이벤트시작일'].fillna(pd.Timestamp.min)

    # 4. KPI Status Logic
    kpi_cols = [c for c in df.columns if 'KPI차감' in c]
    df['KPI_Status'] = df[kpi_cols[0]] if kpi_cols else '-'

    # 5. Missing Value Handling
    fill_cols = ['본부', '지사', '출동/영상', 'L형/i형', '서비스(소)', '부실구분', '체납', '실적채널', '구역담당영업사원']
    for col in fill_cols:
        if col not in df.columns: df[col] = "미분류"
        else: df[col] = df[col].fillna("미지정")
            
    return df

df = load_data()

# -----------------------------------------------------------------------------
# 4. Sidebar Controller
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Analytics Controller")
    st.markdown("---")
    
    # 1. HQ Selection
    all_hqs = sorted(df['본부'].unique())
    st.markdown(f'<div class="sidebar-header">🏢 본부 <span class="count-badge">{len(all_hqs)}</span></div>', unsafe_allow_html=True)
    
    # Try using st.pills if available (Streamlit >= 1.40)
    try:
        selected_hq = st.pills("HQ", all_hqs, selection_mode="multi", default=all_hqs, label_visibility="collapsed")
    except AttributeError:
        selected_hq = st.multiselect("HQ", all_hqs, default=all_hqs, label_visibility="collapsed")
    
    if not selected_hq: selected_hq = all_hqs # Fallback to all if none selected

    # 2. Branch Selection (Cascading)
    filtered_hq_df = df[df['본부'].isin(selected_hq)]
    valid_branches = sorted(filtered_hq_df['지사'].unique())
    
    st.markdown(f'<div class="sidebar-header">📍 지사 <span class="count-badge">{len(valid_branches)}</span></div>', unsafe_allow_html=True)
    with st.expander("지사 선택", expanded=True):
        selected_branch = st.multiselect("Branch", valid_branches, default=valid_branches, label_visibility="collapsed")
    if not selected_branch: selected_branch = valid_branches

    # 3. Manager Selection (Cascading)
    filtered_br_df = filtered_hq_df[filtered_hq_df['지사'].isin(selected_branch)]
    valid_managers = sorted(filtered_br_df['구역담당영업사원'].unique())
    
    st.markdown(f'<div class="sidebar-header">👤 담당자 <span class="count-badge">{len(valid_managers)}</span></div>', unsafe_allow_html=True)
    with st.expander("담당자 선택", expanded=False):
        selected_managers = st.multiselect("Manager", valid_managers, default=valid_managers, label_visibility="collapsed", placeholder="검색...")
    if not selected_managers: selected_managers = valid_managers

    st.markdown("---")
    
    # 4. Global Settings
    st.markdown('<div class="sidebar-header">📊 분석 기준</div>', unsafe_allow_html=True)
    metric_mode = st.radio("Metric Mode", ["건수 (Volume)", "금액 (Revenue)"], horizontal=True, label_visibility="collapsed")
    
    st.markdown('<div class="sidebar-header">⚙️ 필터 옵션</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    kpi_target = c1.checkbox("KPI 대상", False)
    arrears_only = c2.checkbox("체납 건", False)

# [Logic] Final Data Filtering
mask = (df['본부'].isin(selected_hq)) & \
       (df['지사'].isin(selected_branch)) & \
       (df['구역담당영업사원'].isin(selected_managers))

if kpi_target: mask &= (df['KPI_Status'].str.contains('대상', na=False))
if arrears_only: mask &= (~df['체납'].isin(['-', '미분류', '미지정']))

df_filtered = df[mask].copy()

# Dynamic Constants
VAL_COL = '계약번호' if metric_mode == "건수 (Volume)" else '월정료(VAT미포함)'
AGG_FUNC = 'count' if metric_mode == "건수 (Volume)" else 'sum'
FMT_FUNC = (lambda x: f"{x:,.0f}건") if metric_mode == "건수 (Volume)" else format_korean_currency
TEXT_TEMPLATE = '%{text:,.0f}' if metric_mode == "건수 (Volume)" else '%{text:.2s}'

# -----------------------------------------------------------------------------
# 5. Main Dashboard
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">KTT Enterprise Analytics</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">Data as of {pd.Timestamp.now().strftime("%Y-%m-%d")} | Total Records: {len(df_filtered):,}</div>', unsafe_allow_html=True)

# KPI Section
with st.container():
    k1, k2, k3, k4 = st.columns(4)
    
    susp_df = df_filtered[df_filtered['정지,설변구분'] == '정지']
    chg_df = df_filtered[df_filtered['정지,설변구분'] == '설변']
    
    val_susp = len(susp_df) if metric_mode == "건수 (Volume)" else susp_df['월정료(VAT미포함)'].sum()
    val_chg = len(chg_df) if metric_mode == "건수 (Volume)" else chg_df['월정료(VAT미포함)'].sum()
    
    avg_dur = df_filtered['당월말_정지일수'].mean() if not df_filtered.empty else 0
    risk_rate = (len(susp_df) / len(df_filtered) * 100) if len(df_filtered) > 0 else 0

    k1.metric("⛔ 정지 (Suspension)", FMT_FUNC(val_susp), help="Total Suspension")
    k2.metric("🔄 설변 (Change)", FMT_FUNC(val_chg), help="Total Change")
    k3.metric("📅 평균 정지일수", f"{avg_dur:.1f} 일")
    k4.metric("⚠️ 정지 리스크율", f"{risk_rate:.1f}%", delta_color="inverse")

st.markdown("---")

# Tabs
tab_strategy, tab_ops, tab_data = st.tabs(["📊 전략 분석", "🔍 운영 분석", "💾 데이터 그리드"])

# [TAB 1] Strategy
with tab_strategy:
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.markdown("##### 📈 실적 트렌드")
        if 'Period' in df_filtered.columns and not df_filtered.empty:
            trend_df = df_filtered.groupby(['Period', 'SortKey'])[VAL_COL].agg(AGG_FUNC).reset_index().sort_values('SortKey')
            fig_trend = px.area(trend_df, x='Period', y=VAL_COL, markers=True)
            fig_trend.update_traces(line_color='#4f46e5', fillcolor='rgba(79, 70, 229, 0.1)')
            fig_trend.update_layout(template="plotly_white", height=380, margin=dict(l=20, r=20, t=10, b=20), xaxis_title=None)
            if metric_mode == "금액 (Revenue)": fig_trend.update_yaxes(tickformat=".2s")
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("데이터가 부족하여 트렌드를 표시할 수 없습니다.")

    with c2:
        st.markdown("##### 🌐 본부/지사 비중")
        if not df_filtered.empty:
            fig_sun = px.sunburst(df_filtered, path=['본부', '지사'], values=VAL_COL, color='본부', color_discrete_sequence=px.colors.qualitative.Prism)
            fig_sun.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_sun, use_container_width=True)

    st.markdown("##### 🏢 본부별 효율성 (Pareto Chart)")
    hq_stats = df_filtered.groupby('본부').agg({'계약번호': 'count', '월정료(VAT미포함)': 'sum'}).reset_index().sort_values('계약번호', ascending=False)
    
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(go.Bar(x=hq_stats['본부'], y=hq_stats['계약번호'], name="건수", marker_color='#3b82f6', opacity=0.8), secondary_y=False)
    fig_dual.add_trace(go.Scatter(x=hq_stats['본부'], y=hq_stats['월정료(VAT미포함)'], name="금액", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
    fig_dual.update_layout(template="plotly_white", height=350, legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_dual, use_container_width=True)

# [TAB 2] Operations
with tab_ops:
    # Controls
    cat_opts = ["정지,설변구분", "실적채널", "L형/i형", "출동/영상"]
    # Check if columns exist
    valid_opts = [c for c in cat_opts if c in df_filtered.columns]
    
    try:
        sub_mode = st.pills("분석 항목 선택", valid_opts, default=valid_opts[0] if valid_opts else None, selection_mode="single")
    except:
        sub_mode = st.selectbox("분석 항목 선택", valid_opts)

    if sub_mode:
        c1, c2 = st.columns([1, 2])
        agg_df = df_filtered.groupby(sub_mode)[VAL_COL].agg(AGG_FUNC).reset_index().rename(columns={VAL_COL: 'Value'})
        
        with c1:
            fig_pie = px.pie(agg_df, values='Value', names=sub_mode, hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
            fig_pie.update_traces(textinfo='percent+label', textposition='inside')
            fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with c2:
            agg_df = agg_df.sort_values('Value')
            fig_bar = create_bar_chart(agg_df, x='Value', y=sub_mode, orientation='h', text='Value', height=300)
            fig_bar.update_traces(texttemplate=TEXT_TEMPLATE, textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    
    # Detailed Breakdowns
    with st.expander("📊 상세 분석 (본부/지사/담당자)", expanded=True):
        t1, t2 = st.tabs(["본부별", "담당자 Top 20"])
        
        with t1:
            hq_brk = df_filtered.groupby(['본부', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
            fig_hq = create_bar_chart(hq_brk, x='본부', y=VAL_COL, color='정지,설변구분', text=VAL_COL, title="본부별 현황")
            fig_hq.update_traces(texttemplate=TEXT_TEMPLATE)
            st.plotly_chart(fig_hq, use_container_width=True)
            
        with t2:
            mgr_brk = df_filtered.groupby(['구역담당영업사원', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
            top_mgrs = mgr_brk.groupby('구역담당영업사원')[VAL_COL].sum().sort_values(ascending=False).head(20).index
            mgr_top = mgr_brk[mgr_brk['구역담당영업사원'].isin(top_mgrs)]
            
            fig_mgr = create_bar_chart(mgr_top, x=VAL_COL, y='구역담당영업사원', color='정지,설변구분', orientation='h', title="상위 담당자 Top 20", height=600)
            fig_mgr.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_mgr, use_container_width=True)

# [TAB 3] Data Grid (Optimized)
with tab_data:
    st.markdown("### 💾 Intelligent Data Grid")
    
    # Secure Download Logic
    c_pw, c_btn = st.columns([1, 4])
    pwd = c_pw.text_input("Access Code", type="password", placeholder="****", label_visibility="collapsed")
    
    if pwd == "3867": # Note: Use st.secrets in production
        csv_data = df_filtered.to_csv(index=False).encode('utf-8-sig')
        c_btn.download_button("📥 Excel/CSV 다운로드", csv_data, 'ktt_analytics_export.csv', 'text/csv', type="primary")
    else:
        c_btn.button("🔒 다운로드 잠김", disabled=True)

    # Performance Optimized Dataframe
    # Warning: Using style.apply on large datasets causes severe lag. 
    # Solution: Use st.column_config for formatting and highlighting.
    
    display_cols = ['본부', '지사', '구역담당영업사원', 'Period', '고객번호', '상호', '월정료(VAT미포함)', '실적채널', '정지,설변구분', 'KPI_Status']
    valid_disp_cols = [c for c in display_cols if c in df_filtered.columns]
    
    st.dataframe(
        df_filtered[valid_disp_cols],
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "월정료(VAT미포함)": st.column_config.NumberColumn(
                "월정료",
                format="₩%d",
            ),
            "KPI_Status": st.column_config.TextColumn(
                "KPI 상태",
                help="대상인 경우 붉은색 표시",
                validate="^대상$" # Highlights if regex matches, but visual cues are limited in basic config
            ),
            "정지,설변구분": st.column_config.Column(
                "구분",
                width="small"
            )
        }
    )
    st.caption("ℹ️ 성능 최적화를 위해 전체 행 스타일링 대신 네이티브 그리드를 사용합니다.")
