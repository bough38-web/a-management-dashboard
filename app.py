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
    initial_sidebar_state="expanded"
)

# [CSS] Styling
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; color: #1e293b; }
        .stApp { background-color: #f8fafc; }
        [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
        
        .main-title {
            font-size: 2.2rem; font-weight: 800;
            background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 5px;
        }
        
        div[data-testid="stMetric"] {
            background-color: white; padding: 20px; border-radius: 16px;
            border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        
        .sidebar-header {
            font-size: 0.9rem; font-weight: 700; color: #475569;
            margin: 15px 0 8px 0; display: flex; align-items: center; justify-content: space-between;
        }
        .count-badge {
            background-color: #e0e7ff; color: #4338ca;
            font-size: 0.7rem; padding: 2px 6px; border-radius: 10px; font-weight: 600;
        }
        
        div.stButton > button { width: 100%; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Logic: Sorting & Data Loading
# -----------------------------------------------------------------------------
def format_korean_currency(value):
    if value == 0: return "0"
    elif abs(value) >= 100_000_000: return f"{value/100_000_000:,.1f}억"
    elif abs(value) >= 1_000_000: return f"{value/1_000_000:,.1f}백만"
    else: return f"{value/1_000:,.0f}천"

def get_custom_rank(branch_name):
    """지사 정렬 우선순위 부여"""
    target_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
    branch_str = str(branch_name)
    for idx, keyword in enumerate(target_order):
        if keyword in branch_str:
            return idx
    return 999  # 지정 목록 외에는 뒤로 배치

@st.cache_data
def load_enterprise_data():
    file_path = "data.csv"
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        # Dummy Data for Demo
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

    # 1. Column Standardization
    if '조회구분' in df.columns: df['정지,설변구분'] = df['조회구분']
    
    # 2. KPI Status
    kpi_cols = [c for c in df.columns if 'KPI차감' in c]
    df['KPI_Status'] = df[kpi_cols[0]] if kpi_cols else '-'

    # 3. Numeric Conversion
    if '월정료(VAT미포함)' in df.columns:
        df['월정료(VAT미포함)'] = df['월정료(VAT미포함)'].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce').fillna(0)
    for col in ['계약번호', '당월말_정지일수']:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 4. Period & SortKey
    if '이벤트시작일' in df.columns:
        df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
        df['Period'] = df['이벤트시작일'].apply(lambda x: f"'{str(x.year)[-2:]}.{x.month}" if pd.notnull(x) and x.year >= 2025 else "2024년 이전")
        df['SortKey'] = df['이벤트시작일'].fillna(pd.Timestamp.min)

    # 5. Missing Values
    target_cols = ['본부', '지사', '구역담당영업사원', '정지,설변구분', '체납']
    for col in target_cols:
        if col not in df.columns: df[col] = "Unclassified"
        else: df[col] = df[col].fillna("미지정")
    
    # [CORE] Apply Global Rank Column (Sorting Logic)
    df['Branch_Rank'] = df['지사'].apply(get_custom_rank)
    
    return df

df = load_enterprise_data()
if df.empty: st.stop()

# -----------------------------------------------------------------------------
# 3. Sidebar Control Center (Global Actions)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Control Panel")
    
    col_g1, col_g2 = st.columns(2)
    
    # 필요한 전체 목록 미리 계산
    all_hqs = sorted(df['본부'].unique().tolist())
    all_branches = sorted(df['지사'].unique().tolist(), key=lambda x: (get_custom_rank(x), x))
    all_managers = sorted(df['구역담당영업사원'].unique().tolist())
    if "미지정" in all_managers:
        all_managers.remove("미지정")
        all_managers.append("미지정")

    def on_global_select_all():
        st.session_state.hq_selection = all_hqs
        st.session_state.br_selection = all_branches
        st.session_state.mgr_selection = all_managers

    def on_global_reset():
        st.session_state.hq_selection = []
        st.session_state.br_selection = []
        st.session_state.mgr_selection = []

    col_g1.button("✅ 전체 선택", on_click=on_global_select_all, use_container_width=True)
    col_g2.button("🧹 초기화", on_click=on_global_reset, use_container_width=True)
    
    st.markdown("---")

    # --- 1. 본부 필터 ---
    st.markdown(f'<div class="sidebar-header">🏢 본부 선택 <span class="count-badge">{len(all_hqs)}</span></div>', unsafe_allow_html=True)
    if "hq_selection" not in st.session_state: st.session_state.hq_selection = all_hqs
    
    try:
        selected_hq = st.pills("HQ", all_hqs, selection_mode="multi", key="hq_selection", label_visibility="collapsed")
    except:
        selected_hq = st.multiselect("HQ", all_hqs, key="hq_selection", label_visibility="collapsed")
    
    # Fallback
    final_hq = selected_hq if selected_hq else all_hqs

    # --- 2. 지사 필터 ---
    subset_hq = df[df['본부'].isin(final_hq)]
    valid_branches = sorted(subset_hq['지사'].unique().tolist(), key=lambda x: (get_custom_rank(x), x))
    
    st.markdown(f'<div class="sidebar-header">📍 지사 선택 <span class="count-badge">{len(valid_branches)}</span></div>', unsafe_allow_html=True)
    
    if "br_selection" not in st.session_state: st.session_state.br_selection = all_branches
    else:
        st.session_state.br_selection = [b for b in st.session_state.br_selection if b in valid_branches]

    with st.expander(f"지사 목록 ({len(valid_branches)}개)", expanded=True):
        try:
            selected_branch = st.pills("Branch", valid_branches, selection_mode="multi", key="br_selection", label_visibility="collapsed")
        except:
            selected_branch = st.multiselect("Branch", valid_branches, key="br_selection", label_visibility="collapsed")
            
    final_branch = selected_branch if selected_branch else valid_branches

    # --- 3. 담당자 필터 ---
    subset_br = subset_hq[subset_hq['지사'].isin(final_branch)]
    valid_managers = sorted(subset_br['구역담당영업사원'].unique().tolist())
    if "미지정" in valid_managers:
        valid_managers.remove("미지정")
        valid_managers.append("미지정")

    st.markdown(f'<div class="sidebar-header">👤 담당자 선택 <span class="count-badge">{len(valid_managers)}</span></div>', unsafe_allow_html=True)
    
    if "mgr_selection" not in st.session_state: st.session_state.mgr_selection = all_managers
    else:
         st.session_state.mgr_selection = [m for m in st.session_state.mgr_selection if m in valid_managers]

    with st.expander(f"담당자 목록 ({len(valid_managers)}명)", expanded=False):
        if len(valid_managers) > 50:
            selected_managers = st.multiselect("Manager", valid_managers, key="mgr_selection", label_visibility="collapsed", placeholder="담당자 검색")
        else:
            try:
                selected_managers = st.pills("Manager", valid_managers, selection_mode="multi", key="mgr_selection", label_visibility="collapsed")
            except:
                selected_managers = st.multiselect("Manager", valid_managers, key="mgr_selection", label_visibility="collapsed")
    
    final_managers = selected_managers if selected_managers else valid_managers

    st.markdown("---")
    
    # --- Options ---
    st.markdown('<div class="sidebar-header">📊 분석 기준</div>', unsafe_allow_html=True)
    try: metric_mode = st.pills("Metric", ["건수 (Volume)", "금액 (Revenue)"], default="건수 (Volume)", selection_mode="single", label_visibility="collapsed")
    except: metric_mode = st.radio("Metric", ["건수 (Volume)", "금액 (Revenue)"], horizontal=True)
    
    st.markdown('<div class="sidebar-header">⚙️ 고급 필터</div>', unsafe_allow_html=True)
    kpi_target = st.toggle("🎯 KPI 차감 대상만 보기", False)
    arrears_only = st.toggle("💰 체납 건만 보기", False)
    st.caption(f"Update: {pd.Timestamp.now().strftime('%Y-%m-%d')}")

# [CORE] Apply Filters
mask = (df['본부'].isin(final_hq)) & \
       (df['지사'].isin(final_branch)) & \
       (df['구역담당영업사원'].isin(final_managers))

if kpi_target: mask = mask & (df['KPI_Status'].str.contains('대상', na=False))
if arrears_only: mask = mask & (df['체납'] != '-') & (df['체납'] != 'Unclassified') & (df['체납'] != '미지정')

df_filtered = df[mask].copy()
df_filtered = df_filtered.sort_values(by=['Branch_Rank', '지사'])

# Global Config
VAL_COL = '계약번호' if metric_mode == "건수 (Volume)" else '월정료(VAT미포함)'
AGG_FUNC = 'count' if metric_mode == "건수 (Volume)" else 'sum'
FMT_FUNC = (lambda x: f"{x:,.0f}건") if metric_mode == "건수 (Volume)" else format_korean_currency

# -----------------------------------------------------------------------------
# 4. Dashboard Main
# -----------------------------------------------------------------------------
st.markdown('<div class="main-title">KTT Enterprise Analytics</div>', unsafe_allow_html=True)
st.caption("Strategic Insights & Operational Dashboard")

# Summary Metrics
k1, k2, k3, k4 = st.columns(4)
susp_df = df_filtered[df_filtered['정지,설변구분'] == '정지']
chg_df = df_filtered[df_filtered['정지,설변구분'] == '설변']

if metric_mode == "건수 (Volume)":
    v1, v2 = len(susp_df), len(chg_df)
    l1, l2 = "정지 건수", "설변 건수"
else:
    v1, v2 = susp_df['월정료(VAT미포함)'].sum(), chg_df['월정료(VAT미포함)'].sum()
    l1, l2 = "정지 금액", "설변 금액"

k1.metric(f"⛔ {l1}", FMT_FUNC(v1))
k2.metric(f"🔄 {l2}", FMT_FUNC(v2))
k3.metric("📅 평균 정지일수", f"{df_filtered['당월말_정지일수'].mean():.1f} 일")
risk_rate = (len(susp_df) / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
k4.metric("⚠️ 정지 비율", f"{risk_rate:.1f}%", delta_color="inverse")

st.markdown("---")

# Tabs
tab_strategy, tab_ops, tab_data = st.tabs(["📊 전략 분석", "🔍 운영 분석", "💾 데이터 그리드"])

# [TAB 1] Strategy
with tab_strategy:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("##### 📅 실적 트렌드")
        if 'Period' in df_filtered.columns and not df_filtered.empty:
            trend_df = df_filtered.groupby(['Period', 'SortKey'])[VAL_COL].agg(AGG_FUNC).reset_index().sort_values('SortKey')
            fig_trend = px.area(trend_df, x='Period', y=VAL_COL, markers=True)
            fig_trend.update_traces(line_color='#4f46e5', fillcolor='rgba(79, 70, 229, 0.1)')
            fig_trend.update_layout(template="plotly_white", height=380, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None)
            if metric_mode == "금액 (Revenue)": fig_trend.update_yaxes(tickformat=".2s")
            st.plotly_chart(fig_trend, use_container_width=True)
            
    with c2:
        st.markdown("##### 🌐 본부 포트폴리오")
        if not df_filtered.empty:
            fig_sun = px.sunburst(df_filtered, path=['본부', '지사'], values=VAL_COL, color='본부', color_discrete_sequence=px.colors.qualitative.Prism)
            fig_sun.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_sun, use_container_width=True)

    st.markdown("##### 🏢 본부별 효율성 (Pareto)")
    hq_stats = df_filtered.groupby('본부').agg({'계약번호': 'count', '월정료(VAT미포함)': 'sum'}).reset_index().sort_values('계약번호', ascending=False)
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(go.Bar(x=hq_stats['본부'], y=hq_stats['계약번호'], name="건수", marker_color='#3b82f6', opacity=0.8), secondary_y=False)
    fig_dual.add_trace(go.Scatter(x=hq_stats['본부'], y=hq_stats['월정료(VAT미포함)'], name="금액", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
    fig_dual.update_layout(template="plotly_white", height=400, legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_dual, use_container_width=True)

# [TAB 2] Operations (FIXED KeyError)
with tab_ops:
    st.markdown("#### 🚦 다차원 상세 분석")
    try: sub_mode = st.pills("상세 항목", ["실적채널", "L형/i형", "출동/영상", "정지,설변구분"], default="정지,설변구분", selection_mode="single")
    except: sub_mode = st.radio("상세 항목", ["실적채널", "L형/i형", "출동/영상", "정지,설변구분"], horizontal=True)
    if not sub_mode: sub_mode = "정지,설변구분"

    c1, c2 = st.columns([1, 2])
    with c1:
        if sub_mode in df_filtered.columns:
            mode_data = df_filtered.groupby(sub_mode)[VAL_COL].agg(AGG_FUNC).reset_index()
            mode_data.columns = ['구분', '값'] # Rename
            fig_pie = px.pie(mode_data, values='값', names='구분', hole=0.6, color_discrete_sequence=px.colors.qualitative.Safe)
            fig_pie.update_traces(textinfo='percent+label', textposition='inside')
            fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        if sub_mode in df_filtered.columns:
            # [FIXED] Rename columns BEFORE sorting
            mode_data = df_filtered.groupby(sub_mode)[VAL_COL].agg(AGG_FUNC).reset_index()
            mode_data.columns = ['구분', '값'] 
            mode_data = mode_data.sort_values('값') 
            
            fig_bar = px.bar(mode_data, x='값', y='구분', orientation='h', text='값', color='구분', title=f"{sub_mode}별 현황")
            fig_bar.update_layout(showlegend=False, template="plotly_white", xaxis_visible=False)
            fig_bar.update_traces(texttemplate='%{text:,.0f}' if metric_mode=="건수 (Volume)" else '%{text:.2s}', textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    
    with st.expander("🏢 본부별 현황", expanded=True):
        hq_brk = df_filtered.groupby(['본부', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
        hq_brk.columns = ['본부', '구분', '값'] # Explicit Renaming
        fig_hq = px.bar(hq_brk, x='본부', y='값', color='구분', barmode='group', text='값', color_discrete_sequence=['#ef4444', '#3b82f6'])
        fig_hq.update_layout(template="plotly_white", margin=dict(t=20, b=20), legend=dict(orientation="h", y=1.1))
        fig_hq.update_traces(texttemplate='%{text:,.0f}' if metric_mode=="건수 (Volume)" else '%{text:.2s}', textposition='outside')
        st.plotly_chart(fig_hq, use_container_width=True)

    with st.expander("📍 지사별 현황 (Sorted)", expanded=True):
        br_brk = df_filtered.groupby(['지사', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
        br_brk.columns = ['지사', '구분', '값']
        
        # 순서 강제 적용
        br_brk['Rank'] = br_brk['지사'].apply(get_custom_rank)
        sorted_branches = sorted(br_brk['지사'].unique(), key=lambda x: (get_custom_rank(x), x))
        
        fig_br = px.bar(br_brk, x='지사', y='값', color='구분', barmode='stack')
        fig_br.update_layout(
            template="plotly_white", 
            margin=dict(t=20, b=20),
            xaxis={'categoryorder':'array', 'categoryarray': sorted_branches}
        )
        st.plotly_chart(fig_br, use_container_width=True)

    with st.expander("👤 담당자별 Top 20", expanded=False):
        mgr_brk = df_filtered.groupby(['구역담당영업사원', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
        mgr_brk.columns = ['구역담당영업사원', '정지,설변구분', VAL_COL] # Keep original names or rename for clarity
        
        top_list = mgr_brk.groupby('구역담당영업사원')[VAL_COL].sum().sort_values(ascending=False).head(20).index
        mgr_top = mgr_brk[mgr_brk['구역담당영업사원'].isin(top_list)]
        
        fig_mgr = px.bar(mgr_top, x=VAL_COL, y='구역담당영업사원', color='정지,설변구분', orientation='h')
        fig_mgr.update_layout(yaxis={'categoryorder':'total ascending'}, template="plotly_white", margin=dict(t=20, b=20))
        st.plotly_chart(fig_mgr, use_container_width=True)

    st.markdown("---")
    
    # Bottom Charts
    c_m1, c_m2 = st.columns(2)
    def extract_num(s):
        nums = re.findall(r'\d+', str(s))
        return int(nums[0]) if nums else 0

    with c_m1:
        st.markdown("##### ⏱️ 정지일수 구간")
        if '당월말_정지일수_구간' in df_filtered.columns:
            s_data = df_filtered.groupby('당월말_정지일수_구간')[VAL_COL].agg(AGG_FUNC).reset_index()
            s_data.columns = ['당월말_정지일수_구간', '값']
            s_data['sort'] = s_data['당월말_정지일수_구간'].apply(extract_num)
            s_data = s_data.sort_values('sort')
            
            fig_s = px.bar(s_data, x='값', y='당월말_정지일수_구간', orientation='h', text='값', color='값', color_continuous_scale='Reds')
            fig_s.update_layout(template="plotly_white", xaxis_visible=False)
            fig_s.update_traces(texttemplate='%{text:,.0f}' if metric_mode=="건수 (Volume)" else '%{text:.2s}', textposition='outside')
            st.plotly_chart(fig_s, use_container_width=True)

    with c_m2:
        st.markdown("##### 💰 월정료 가격대")
        if '월정료 구간' in df_filtered.columns:
            p_data = df_filtered.groupby('월정료 구간')[VAL_COL].agg(AGG_FUNC).reset_index()
            p_data.columns = ['월정료 구간', '값']
            p_data['sort'] = p_data['월정료 구간'].apply(extract_num)
            p_data = p_data.sort_values('sort')
            
            fig_p = px.bar(p_data, x='월정료 구간', y='값', text='값', color='값', color_continuous_scale='Blues')
            fig_p.update_layout(template="plotly_white", yaxis_visible=False)
            fig_p.update_traces(texttemplate='%{text:,.0f}' if metric_mode=="건수 (Volume)" else '%{text:.2s}', textposition='outside')
            st.plotly_chart(fig_p, use_container_width=True)

# [TAB 3] Data Grid
with tab_data:
    st.subheader("💾 Intelligent Data Grid")
    c_pw, c_btn = st.columns([1, 3])
    pwd = c_pw.text_input("다운로드 비밀번호", type="password", placeholder="****", label_visibility="collapsed")
    if pwd == "3867":
        c_btn.download_button("📥 Excel/CSV 다운로드", df_filtered.to_csv(index=False).encode('utf-8-sig'), 'ktt_data.csv', 'text/csv')
    
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
            "지사": st.column_config.Column("지사", help="지정된 순서(중앙, 강북...)로 정렬됨")
        }
    )
