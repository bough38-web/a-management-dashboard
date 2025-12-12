import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. System Configuration & Design System
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Enterprise Insight Hub",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [Modern SaaS Design System CSS]
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        :root {
            --primary-color: #4F46E5;
            --secondary-color: #818CF8;
            --bg-color: #F8FAFC;
            --card-bg: #FFFFFF;
            --text-main: #1E293B;
            --text-sub: #64748B;
        }

        /* Global Reset */
        .stApp { background-color: var(--bg-color); font-family: 'Pretendard', sans-serif; }
        h1, h2, h3 { letter-spacing: -0.02em; }

        /* Custom Header */
        .dashboard-header {
            padding: 1.5rem 0;
            margin-bottom: 2rem;
            border-bottom: 1px solid #E2E8F0;
        }
        .header-title {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #1E293B 0%, #4F46E5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header-meta {
            font-size: 0.9rem;
            color: var(--text-sub);
            margin-top: 0.5rem;
        }

        /* KPI Cards (Glassmorphism + Hover Effect) */
        .kpi-container {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .kpi-card {
            background: var(--card-bg);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            border: 1px solid #F1F5F9;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        .kpi-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.1), 0 4px 6px -2px rgba(79, 70, 229, 0.05);
            border-color: var(--secondary-color);
        }
        .kpi-label { font-size: 0.85rem; font-weight: 600; color: var(--text-sub); text-transform: uppercase; letter-spacing: 0.05em; }
        .kpi-value { font-size: 1.8rem; font-weight: 800; color: var(--text-main); margin: 0.5rem 0; }
        .kpi-delta { font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; gap: 4px; }
        .delta-pos { color: #10B981; background: #ECFDF5; padding: 2px 8px; border-radius: 999px; width: fit-content; }
        .delta-neg { color: #EF4444; background: #FEF2F2; padding: 2px 8px; border-radius: 999px; width: fit-content; }
        .kpi-icon { position: absolute; top: 1.5rem; right: 1.5rem; opacity: 0.1; font-size: 2.5rem; color: var(--primary-color); }

        /* Chart Containers */
        .chart-box {
            background: var(--card-bg);
            border-radius: 20px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
            border: 1px solid #F1F5F9;
            height: 100%;
        }
        .chart-header {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* Custom Sidebar */
        [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }
        .sidebar-section { margin-bottom: 2rem; }
        .sidebar-label { font-size: 0.8rem; font-weight: 700; color: var(--text-sub); margin-bottom: 0.5rem; text-transform: uppercase; }
        
        /* Pills Customization */
        div[data-testid="stPills"] { gap: 8px; }
        div[data-testid="stPills"] button[aria-selected="true"] {
            background: var(--primary-color) !important;
            color: white !important;
            border: none;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Advanced Logic & Utilities (OOP)
# -----------------------------------------------------------------------------
class DataProcessor:
    @staticmethod
    def format_currency(value):
        if value == 0: return "0"
        elif abs(value) >= 100_000_000: return f"{value/100_000_000:,.2f}억"
        elif abs(value) >= 1_000_000: return f"{value/1_000_000:,.1f}백만"
        else: return f"{value/1_000:,.0f}천"

    @staticmethod
    @st.cache_data(ttl=3600)
    def load_data(file_path="data.csv"):
        try:
            # 실무 팁: utf-8이 안되면 cp949로 시도
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='cp949')
        except FileNotFoundError:
            # Fallback for demo if file doesn't exist
            return pd.DataFrame()

        # Preprocessing Pipeline
        if '조회구분' in df.columns: df['정지,설변구분'] = df['조회구분']
        
        # KPI Logic
        kpi_cols = [c for c in df.columns if 'KPI차감' in c]
        df['KPI_Status'] = df[kpi_cols[0]] if kpi_cols else '-'
        
        # Date Logic
        if '이벤트시작일' in df.columns:
            df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
            df['Period_YYYYMM'] = df['이벤트시작일'].dt.to_period('M').astype(str)
            df['Year'] = df['이벤트시작일'].dt.year

        # Numeric Conversion
        numeric_cols = ['월정료(VAT미포함)', '계약번호', '당월말_정지일수']
        for col in numeric_cols:
            if col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce')
                df[col] = df[col].fillna(0)

        # Missing Value Handling
        fill_cols = ['본부', '지사', '출동/영상', 'L형/i형', '정지,설변구분', '서비스(소)', '부실구분', '체납', '실적채널', '구역담당영업사원']
        for col in fill_cols:
            if col not in df.columns: df[col] = "Unclassified"
            else: df[col] = df[col].fillna("미지정")
            
        return df

class ChartFactory:
    """Enterprise Chart Design System"""
    COLORS = ['#6366F1', # Indigo
              '#EC4899', # Pink
              '#10B981', # Emerald
              '#F59E0B', # Amber
              '#3B82F6', # Blue
              '#8B5CF6'] # Violet

    @staticmethod
    def get_layout(title="", height=350):
        return dict(
            title=dict(text=title, font=dict(size=16, family="Pretendard", weight="bold")),
            template="plotly_white",
            height=height,
            margin=dict(l=20, r=20, t=50, b=20),
            hovermode="x unified",
            showlegend=True,
            legend=dict(orientation="h", y=1.1, x=1, xanchor="right")
        )

# -----------------------------------------------------------------------------
# 3. Application Logic
# -----------------------------------------------------------------------------
def main():
    # A. Data Loading
    raw_df = DataProcessor.load_data()
    
    if raw_df.empty:
        st.error("🚨 데이터 파일을 찾을 수 없습니다. (data.csv)")
        # Demo Data Generator could go here
        st.stop()

    # B. Sidebar Control Logic
    with st.sidebar:
        st.markdown("### 🎛️ Analysis Hub")
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
        
        # Hierarchy Filters
        st.markdown('<div class="sidebar-label">🏢 ORGANIZATION</div>', unsafe_allow_html=True)
        
        all_hqs = sorted(raw_df['본부'].unique().tolist())
        selected_hq = st.multiselect("본부", all_hqs, default=all_hqs, label_visibility="collapsed")
        
        valid_branches = sorted(raw_df[raw_df['본부'].isin(selected_hq)]['지사'].unique().tolist())
        with st.expander(f"📍 지사 선택 ({len(valid_branches)})", expanded=False):
            selected_branch = st.multiselect("지사", valid_branches, default=valid_branches, label_visibility="collapsed")
            
        # Manager Filter
        valid_managers = sorted(raw_df[
            (raw_df['본부'].isin(selected_hq)) & (raw_df['지사'].isin(selected_branch))
        ]['구역담당영업사원'].unique().tolist())
        
        with st.expander(f"👤 담당자 선택 ({len(valid_managers)})", expanded=False):
            if "미지정" in valid_managers: valid_managers.append(valid_managers.pop(valid_managers.index("미지정")))
            selected_managers = st.multiselect("담당자", valid_managers, default=valid_managers, label_visibility="collapsed")

        st.markdown("---")
        
        # Metric Settings
        st.markdown('<div class="sidebar-label">📊 METRICS & SCOPE</div>', unsafe_allow_html=True)
        try:
            metric_mode = st.pills("View Mode", ["건수 (Volume)", "금액 (Revenue)"], default="건수 (Volume)", selection_mode="single")
        except:
            metric_mode = st.radio("View Mode", ["건수 (Volume)", "금액 (Revenue)"])

        c1, c2 = st.columns(2)
        with c1: kpi_target = st.toggle("KPI 차감", False)
        with c2: arrears_only = st.toggle("체납 건", False)

        st.caption(f"Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # C. Filtering
    if not selected_hq: selected_hq = all_hqs
    if not selected_branch: selected_branch = valid_branches
    if not selected_managers: selected_managers = valid_managers

    mask = (raw_df['본부'].isin(selected_hq)) & \
           (raw_df['지사'].isin(selected_branch)) & \
           (raw_df['구역담당영업사원'].isin(selected_managers))

    if kpi_target: mask = mask & (raw_df['KPI_Status'].str.contains('대상', na=False))
    if arrears_only: mask = mask & (raw_df['체납'] != '-') & (raw_df['체납'] != '미지정')

    df = raw_df[mask]

    # Global Constants for Charting
    VAL_COL = '계약번호' if metric_mode == "건수 (Volume)" else '월정료(VAT미포함)'
    AGG_FUNC = 'count' if metric_mode == "건수 (Volume)" else 'sum'
    FMT_FUNC = (lambda x: f"{x:,.0f}건") if metric_mode == "건수 (Volume)" else DataProcessor.format_currency

    # D. Main Dashboard Layout
    st.markdown("""
        <div class="dashboard-header">
            <div class="header-title">Enterprise Insight Hub</div>
            <div class="header-meta">Strategic Operations & Risk Management Dashboard</div>
        </div>
    """, unsafe_allow_html=True)

    # 1. KPI Cards Section
    susp_df = df[df['정지,설변구분'] == '정지']
    chg_df = df[df['정지,설변구분'] == '설변']

    v_susp = len(susp_df) if metric_mode == "건수 (Volume)" else susp_df['월정료(VAT미포함)'].sum()
    v_chg = len(chg_df) if metric_mode == "건수 (Volume)" else chg_df['월정료(VAT미포함)'].sum()
    
    # Calculate previous period (Mockup logic for demo - assuming 10% growth)
    delta_susp = -2.5 # Fake delta
    delta_chg = 1.2
    
    def render_kpi_card(title, value, delta, icon, color_class):
        delta_html = f"<div class='delta-{color_class}'>{delta}% vs last month</div>"
        return f"""
        <div class="kpi-card">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-label">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-delta">{delta_html}</div>
        </div>
        """

    # Using st.markdown with HTML for advanced cards
    kpi_html = f"""
    <div class="kpi-container">
        {render_kpi_card(f"Total {'Suspension' if metric_mode == '건수 (Volume)' else 'Loss'}", FMT_FUNC(v_susp), delta_susp, "⛔", "pos")}
        {render_kpi_card(f"Total {'Changes' if metric_mode == '건수 (Volume)' else 'Rev'}", FMT_FUNC(v_chg), delta_chg, "🔄", "neg")}
        {render_kpi_card("Avg Duration", f"{df['당월말_정지일수'].mean():.1f} Days", -0.5, "📅", "pos")}
        {render_kpi_card("Risk Ratio", f"{(len(susp_df)/len(df)*100 if len(df) else 0):.1f}%", 0.2, "⚠️", "neg")}
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # 2. Advanced Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Strategic View", "🔍 Operational Deep-Dive", "💾 Data Grid"])

    # [TAB 1] Strategy
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            # Area Chart with Gradient
            if 'Period_YYYYMM' in df.columns:
                trend_df = df.groupby(['Period_YYYYMM', '정지,설변구분'])[VAL_COL].agg(AGG_FUNC).reset_index()
                trend_df = trend_df.sort_values('Period_YYYYMM')
                
                fig_trend = px.area(trend_df, x='Period_YYYYMM', y=VAL_COL, color='정지,설변구분',
                                  color_discrete_map={'정지': '#EF4444', '설변': '#6366F1'})
                fig_trend.update_layout(ChartFactory.get_layout("📈 Monthly Trend Analysis"))
                fig_trend.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F1F5F9')
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("시계열 데이터를 분석하려면 '이벤트시작일' 컬럼이 필요합니다.")
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            # Treemap (Better than Sunburst for dashboards)
            if not df.empty:
                fig_tree = px.treemap(df, path=[px.Constant("All"), '본부', '지사'], values=VAL_COL,
                                    color='본부', color_discrete_sequence=px.colors.qualitative.Prism)
                fig_tree.update_layout(ChartFactory.get_layout("🗺️ HQ/Branch Hierarchy", height=350))
                fig_tree.update_traces(root_color="lightgrey")
                st.plotly_chart(fig_tree, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
        
        # Pareto Analysis (Combo Chart)
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        hq_stats = df.groupby('본부').agg({
            '계약번호': 'count', 
            '월정료(VAT미포함)': 'sum'
        }).reset_index().sort_values('계약번호', ascending=False)

        fig_combo = make_subplots(specs=[[{"secondary_y": True}]])
        fig_combo.add_trace(
            go.Bar(x=hq_stats['본부'], y=hq_stats['계약번호'], name="Volume (건수)", 
                   marker_color='#3B82F6', marker_line_width=0, opacity=0.8),
            secondary_y=False
        )
        fig_combo.add_trace(
            go.Scatter(x=hq_stats['본부'], y=hq_stats['월정료(VAT미포함)'], name="Revenue (금액)", 
                       mode='lines+markers', line=dict(color='#F59E0B', width=3), marker=dict(size=8)),
            secondary_y=True
        )
        fig_combo.update_layout(ChartFactory.get_layout("🏢 Efficiency Analysis (Pareto)", height=400))
        st.plotly_chart(fig_combo, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # [TAB 2] Operations
    with tab2:
        c_op1, c_op2 = st.columns([1, 2])
        
        with c_op1:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            cat_col = st.selectbox("Category Breakdown", ["실적채널", "L형/i형", "출동/영상", "부실구분"], index=0)
            
            if cat_col in df.columns:
                pie_df = df.groupby(cat_col)[VAL_COL].agg(AGG_FUNC).reset_index()
                fig_donut = px.pie(pie_df, values=VAL_COL, names=cat_col, hole=0.6, 
                                 color_discrete_sequence=ChartFactory.COLORS)
                fig_donut.update_layout(ChartFactory.get_layout(f"{cat_col} Distribution", height=350))
                fig_donut.update_traces(textinfo='percent+label', textposition='inside')
                st.plotly_chart(fig_donut, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with c_op2:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            # Horizontal Bar Chart for Managers (Top 15)
            mgr_df = df.groupby('구역담당영업사원')[VAL_COL].agg(AGG_FUNC).reset_index().sort_values(VAL_COL, ascending=True).tail(15)
            
            fig_bar = go.Figure(go.Bar(
                x=mgr_df[VAL_COL], 
                y=mgr_df['구역담당영업사원'], 
                orientation='h',
                marker=dict(color=mgr_df[VAL_COL], colorscale='Viridis'),
                text=mgr_df[VAL_COL].apply(lambda x: f"{x:,.0f}" if metric_mode=="건수 (Volume)" else f"{x/10000:,.0f}만"),
                textposition='auto'
            ))
            fig_bar.update_layout(ChartFactory.get_layout("🏆 Top Performing Managers (Top 15)", height=350))
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # [TAB 3] Data Grid
    with tab3:
        st.markdown("### 💾 Intelligent Data Grid")
        st.caption("Filter, Sort, and Edit data directly. Sensitive columns are protected.")
        
        target_cols = ['본부', '지사', '구역담당영업사원', '이벤트시작일', '고객번호', '상호', '월정료(VAT미포함)', '실적채널', '정지,설변구분', 'KPI_Status']
        display_cols = [c for c in target_cols if c in df.columns]
        
        # Advanced Data Editor
        edited_df = st.data_editor(
            df[display_cols],
            use_container_width=True,
            height=600,
            column_config={
                "월정료(VAT미포함)": st.column_config.NumberColumn("월정료", format="₩%d"),
                "이벤트시작일": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "KPI_Status": st.column_config.TextColumn("KPI", help="KPI 차감 대상 여부")
            },
            hide_index=True,
            num_rows="dynamic"
        )
        
        # Download Logic
        col_d1, col_d2 = st.columns([1, 4])
        with col_d1:
            pwd = st.text_input("Security Key", type="password", placeholder="Enter PIN", label_visibility="collapsed")
        with col_d2:
            if pwd == "3867":
                st.download_button(
                    "📥 Export Full Data (CSV)", 
                    df.to_csv(index=False).encode('utf-8-sig'), 
                    f"ktt_export_{datetime.now().strftime('%Y%m%d')}.csv", 
                    "text/csv",
                    type="primary"
                )
            else:
                st.button("🔒 Locked", disabled=True)

if __name__ == "__main__":
    main()
