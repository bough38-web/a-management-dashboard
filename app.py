import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import random

# -----------------------------------------------------------------------------
# 1. System Config & Design System
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Enterprise Insight Hub",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [CSS] Integrated Design System (Glassmorphism + V2 KPI + Modern Tables)
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        :root {
            --primary: #4F46E5;     /* Indigo 600 */
            --primary-light: #818CF8;
            --danger: #E11D48;      /* Rose 600 */
            --success: #059669;     /* Emerald 600 */
            --bg-color: #F8FAFC;    /* Slate 50 */
            --card-bg: #FFFFFF;
            --text-main: #1E293B;   /* Slate 800 */
            --text-sub: #64748B;    /* Slate 500 */
            --border: #E2E8F0;
        }

        /* 1. Global Reset */
        .stApp { background-color: var(--bg-color); font-family: 'Pretendard', sans-serif; }
        
        /* 2. Header Style */
        .dashboard-header {
            padding: 1rem 0 2rem 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2rem;
        }
        .header-title {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #0F172A 0%, #4F46E5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        }
        .header-meta { font-size: 1rem; color: var(--text-sub); margin-top: 0.5rem; }

        /* 3. KPI Cards V2 (Ultimate) */
        .kpi-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .kpi-card {
            background: var(--card-bg);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
            position: relative;
            transition: all 0.3s ease;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .kpi-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            border-color: #CBD5E1;
        }
        .kpi-card::before {
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--primary-light));
            opacity: 0; transition: opacity 0.3s;
        }
        .kpi-card:hover::before { opacity: 1; }
        
        .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
        .kpi-label { font-size: 0.85rem; color: var(--text-sub); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
        .kpi-icon-box {
            width: 40px; height: 40px; border-radius: 10px;
            background: #F1F5F9; display: flex; align-items: center; justify-content: center;
            font-size: 1.25rem; color: #475569;
        }
        .kpi-value {
            font-size: 2.2rem; font-weight: 800; color: var(--text-main);
            margin-bottom: 0.5rem; letter-spacing: -0.03em; font-feature-settings: "tnum";
        }
        .delta-badge {
            display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px;
            border-radius: 999px; font-size: 0.85rem; font-weight: 600;
        }
        .delta-pos { background-color: #ECFDF5; color: #059669; }
        .delta-neg { background-color: #FFF1F2; color: #E11D48; }

        /* 4. Sidebar & Widgets */
        [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid var(--border); }
        div[data-testid="stExpander"] { border: none; box-shadow: none; background: transparent; }
        
        /* 5. Chart Containers */
        .chart-box {
            background: #FFFFFF; border-radius: 20px; padding: 1.5rem;
            border: 1px solid var(--border); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
            height: 100%;
        }
        
        /* 6. Tabs Customization */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            height: 40px; white-space: pre-wrap; background-color: transparent; border-radius: 6px;
            color: #64748B; font-weight: 600; padding: 0 16px;
        }
        .stTabs [aria-selected="true"] { background-color: #EEF2FF; color: #4F46E5; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Advanced Data Logic (Mock Generator + Loader)
# -----------------------------------------------------------------------------
class DataEngine:
    @staticmethod
    def generate_mock_data(rows=1000):
        """실행을 위한 고품질 가상 데이터 생성 (파일 없어도 실행 가능)"""
        hqs = ['수도권본부', '부산경남본부', '대구경북본부', '호남본부', '충청본부']
        branches = {
            '수도권본부': ['강남지사', '강북지사', '인천지사', '경기지사'],
            '부산경남본부': ['부산지사', '울산지사', '창원지사'],
            '대구경북본부': ['대구지사', '포항지사', '구미지사'],
            '호남본부': ['광주지사', '전주지사', '제주지사'],
            '충청본부': ['대전지사', '천안지사', '청주지사']
        }
        managers = [f"매니저{i}" for i in range(1, 50)]
        types = ['정지', '설변']
        channels = ['대리점', '직판', '법인영업', '온라인']
        
        data = []
        base_date = datetime(2025, 1, 1)
        
        for i in range(rows):
            hq = random.choice(hqs)
            branch = random.choice(branches[hq])
            mgr = random.choice(managers)
            # 날짜 분포 (최근 데이터가 더 많게)
            days_offset = random.choices(range(365), weights=[i**2 for i in range(365)], k=1)[0]
            evt_date = base_date - timedelta(days=days_offset)
            
            # 수치 생성
            status = random.choices(types, weights=[0.3, 0.7], k=1)[0] # 정지 30%, 설변 70%
            fee = random.randint(30000, 500000)
            duration = random.randint(1, 365) if status == '정지' else 0
            is_kpi = "대상" if random.random() > 0.8 else "비대상"
            is_arrears = "Y" if random.random() > 0.9 else "N"
            
            data.append([
                hq, branch, mgr, evt_date, 
                status, fee, duration, 
                random.choice(channels), is_kpi, is_arrears
            ])
            
        df = pd.DataFrame(data, columns=[
            '본부', '지사', '구역담당영업사원', '이벤트시작일', 
            '정지,설변구분', '월정료(VAT미포함)', '당월말_정지일수', 
            '실적채널', 'KPI_Status', '체납'
        ])
        return df

    @staticmethod
    @st.cache_data(ttl=3600)
    def load_data():
        """CSV 로드 시도 후 실패 시 Mock Data 반환"""
        try:
            df = pd.read_csv("data.csv", encoding='utf-8')
        except:
            try:
                df = pd.read_csv("data.csv", encoding='cp949')
            except FileNotFoundError:
                # 파일이 없으면 가상 데이터 생성 (데모 모드)
                return DataEngine.generate_mock_data(2000)

        # 전처리
        if '이벤트시작일' in df.columns:
            df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
            df['YearMonth'] = df['이벤트시작일'].dt.to_period('M').astype(str)
        
        # 숫자형 변환
        cols_to_numeric = ['월정료(VAT미포함)', '당월말_정지일수']
        for col in cols_to_numeric:
            if col in df.columns and df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce')
            df[col] = df[col].fillna(0)
            
        return df

class ChartHelper:
    """Enterprise Chart Design System"""
    # 시맨틱 컬러: 정지(위험)=Rose, 설변(일반)=Indigo
    COLOR_MAP = {'정지': '#E11D48', '설변': '#4F46E5'} 
    
    @staticmethod
    def get_layout(title="", height=350):
        return dict(
            title=dict(text=title, font=dict(size=17, family="Pretendard", weight="bold")),
            template="plotly_white",
            height=height,
            margin=dict(l=20, r=20, t=50, b=20),
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1, x=1, xanchor="right")
        )

# -----------------------------------------------------------------------------
# 3. Main Dashboard Application
# -----------------------------------------------------------------------------
def main():
    # A. Data Loading
    df_raw = DataEngine.load_data()
    
    # B. Sidebar Controls (Chained Filtering)
    with st.sidebar:
        st.markdown("### 🎛️ Analysis Hub")
        
        # 1. Organization Filters
        st.markdown("<br><span style='font-size:0.8rem; font-weight:700; color:#64748B;'>ORGANIZATION</span>", unsafe_allow_html=True)
        
        all_hqs = sorted(df_raw['본부'].unique().tolist())
        sel_hq = st.multiselect("본부", all_hqs, default=all_hqs, label_visibility="collapsed", placeholder="본부 선택")
        
        # Filter branches based on HQ selection
        filtered_branches = sorted(df_raw[df_raw['본부'].isin(sel_hq)]['지사'].unique().tolist())
        
        with st.expander(f"📍 지사 선택 ({len(filtered_branches)})", expanded=False):
            sel_branch = st.multiselect("지사", filtered_branches, default=filtered_branches, label_visibility="collapsed")
            
        # Filter managers based on Branch selection
        filtered_mgrs = sorted(df_raw[
            (df_raw['본부'].isin(sel_hq)) & (df_raw['지사'].isin(sel_branch))
        ]['구역담당영업사원'].unique().tolist())
        
        with st.expander(f"👤 담당자 선택 ({len(filtered_mgrs)})", expanded=False):
            sel_mgr = st.multiselect("담당자", filtered_mgrs, default=filtered_mgrs, label_visibility="collapsed")

        # 2. Metric Options
        st.markdown("<br><span style='font-size:0.8rem; font-weight:700; color:#64748B;'>METRICS</span>", unsafe_allow_html=True)
        try:
            metric_type = st.pills("View Mode", ["건수 (Volume)", "금액 (Revenue)"], default="건수 (Volume)", selection_mode="single")
        except:
            metric_type = st.radio("View Mode", ["건수 (Volume)", "금액 (Revenue)"])
        
        # 3. Advanced Toggles
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: filter_kpi = st.toggle("KPI 대상", False)
        with c2: filter_arrears = st.toggle("체납 건", False)
        
        st.divider()
        st.caption(f"Source: {'Mock Data (Demo)' if 'data.csv' not in str(DataEngine.load_data) else 'Live CSV'}")

    # C. Apply Filters
    if not sel_hq: sel_hq = all_hqs
    if not sel_branch: sel_branch = filtered_branches
    if not sel_mgr: sel_mgr = filtered_mgrs
    
    mask = (df_raw['본부'].isin(sel_hq)) & \
           (df_raw['지사'].isin(sel_branch)) & \
           (df_raw['구역담당영업사원'].isin(sel_mgr))
           
    if filter_kpi: mask &= df_raw['KPI_Status'].str.contains("대상", na=False)
    if filter_arrears: mask &= (df_raw['체납'] == 'Y')
    
    df = df_raw[mask]
    
    # Constants
    VAL_COL = '월정료(VAT미포함)' if metric_type == "금액 (Revenue)" else 'KPI_Status' # KPI_Status is just a dummy for count
    AGG = 'sum' if metric_type == "금액 (Revenue)" else 'count'
    FMT = (lambda x: f"₩{x/10000:,.0f}만") if metric_type == "금액 (Revenue)" else (lambda x: f"{x:,.0f}건")

    # D. Dashboard Layout
    st.markdown("""
        <div class="dashboard-header">
            <div class="header-title">Enterprise Insight Hub</div>
            <div class="header-meta">Strategic Operations & Risk Management Dashboard</div>
        </div>
    """, unsafe_allow_html=True)

    # 1. KPI Section (V2 Ultimate Design)
    susp_df = df[df['정지,설변구분'] == '정지']
    chg_df = df[df['정지,설변구분'] == '설변']
    
    v_susp = susp_df['월정료(VAT미포함)'].sum() if metric_type == "금액 (Revenue)" else len(susp_df)
    v_chg = chg_df['월정료(VAT미포함)'].sum() if metric_type == "금액 (Revenue)" else len(chg_df)
    
    # Logic for trend arrows (Comparison mockup)
    delta_susp = -2.5 
    delta_chg = 1.2
    
    def kpi_card(title, val, delta, icon, is_good_trend_up=True):
        # Trend Logic: For "Suspension", Decrease is Good (Green). For "Revenue", Increase is Good (Green).
        is_pos = (delta > 0) == is_good_trend_up
        # Exception: For suspension/risk, negative delta is actually 'positive' outcome (Green)
        if "Suspension" in title or "Risk" in title:
            cls = "delta-pos" if delta < 0 else "delta-neg"
        else:
            cls = "delta-pos" if delta > 0 else "delta-neg"
            
        arrow = "▲" if delta > 0 else "▼"
        
        return f"""
        <div class="kpi-card">
            <div class="card-header">
                <span class="kpi-label">{title}</span>
                <div class="kpi-icon-box">{icon}</div>
            </div>
            <div class="kpi-value">{val}</div>
            <div><span class="delta-badge {cls}">{arrow} {abs(delta)}% vs last month</span></div>
        </div>
        """
        
    st.markdown(f"""
    <div class="kpi-container">
        {kpi_card(f"Total {'Suspension' if metric_type == '건수 (Volume)' else 'Loss'}", FMT(v_susp), delta_susp, "⛔", False)}
        {kpi_card(f"Total {'Change' if metric_type == '건수 (Volume)' else 'Revenue'}", FMT(v_chg), delta_chg, "🔄", True)}
        {kpi_card("Avg Suspension Days", f"{df['당월말_정지일수'].mean():.1f} Days", -0.8, "📅", False)}
        {kpi_card("Risk Ratio", f"{(len(susp_df)/len(df)*100 if len(df) else 0):.1f}%", 0.4, "⚠️", False)}
    </div>
    """, unsafe_allow_html=True)

    # 2. Main Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Strategic View", "🔍 Operational Deep-Dive", "💾 Data Grid"])

    # [Tab 1] Strategy
    with tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            if 'YearMonth' in df.columns:
                trend = df.groupby(['YearMonth', '정지,설변구분'])[VAL_COL].agg(AGG).reset_index().sort_values('YearMonth')
                # Area Chart with Custom Colors
                fig_trend = px.area(trend, x='YearMonth', y=VAL_COL, color='정지,설변구분',
                                  color_discrete_map=ChartHelper.COLOR_MAP)
                fig_trend.update_layout(ChartHelper.get_layout("📈 Monthly Trend Analysis"))
                st.plotly_chart(fig_trend, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            # Treemap (Better than Sunburst for standard dashboards)
            fig_tree = px.treemap(df, path=[px.Constant("All"), '본부', '지사'], values='월정료(VAT미포함)', 
                                color='본부', color_discrete_sequence=px.colors.qualitative.Prism)
            fig_tree.update_layout(ChartHelper.get_layout("🗺️ Region Hierarchy", height=350))
            fig_tree.update_traces(root_color="#F1F5F9")
            st.plotly_chart(fig_tree, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        # Pareto (Combo Chart - Advanced)
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        
        pareto = df.groupby('본부').agg({'KPI_Status':'count', '월정료(VAT미포함)':'sum'}).reset_index().sort_values('KPI_Status', ascending=False)
        
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        # Bar: Volume
        fig_dual.add_trace(go.Bar(x=pareto['본부'], y=pareto['KPI_Status'], name="Volume (건수)", 
                                marker_color='#818CF8', opacity=0.8, marker_line_width=0), secondary_y=False)
        # Line: Revenue
        fig_dual.add_trace(go.Scatter(x=pareto['본부'], y=pareto['월정료(VAT미포함)'], name="Revenue (금액)", 
                                    mode='lines+markers', line=dict(color='#F59E0B', width=3)), secondary_y=True)
        
        fig_dual.update_layout(ChartHelper.get_layout("🏢 Efficiency Analysis (Volume vs Revenue)", height=400))
        st.plotly_chart(fig_dual, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # [Tab 2] Operations
    with tab2:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            cat_dim = st.selectbox("분석 차원", ["실적채널", "체납", "KPI_Status"])
            pie_data = df.groupby(cat_dim)[VAL_COL].agg(AGG).reset_index()
            # Donut Chart
            fig_pie = px.pie(pie_data, values=VAL_COL, names=cat_dim, hole=0.6, color_discrete_sequence=px.colors.qualitative.Bold)
            fig_pie.update_layout(ChartHelper.get_layout(f"{cat_dim} Distribution"))
            fig_pie.update_traces(textinfo='percent+label', textposition='inside')
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with c2:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            # Top Managers Bar Chart
            top_mgr = df.groupby('구역담당영업사원')[VAL_COL].agg(AGG).reset_index().sort_values(VAL_COL).tail(15)
            fig_bar = px.bar(top_mgr, x=VAL_COL, y='구역담당영업사원', orientation='h', text=VAL_COL, color=VAL_COL, color_continuous_scale='Indigo')
            fig_bar.update_layout(ChartHelper.get_layout("🏆 Top 15 Managers Performance"))
            fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # [Tab 3] Data Grid
    with tab3:
        st.subheader("💾 Intelligent Data Grid")
        st.caption("Double-click cells to edit. Filter and sort directly in the table.")
        
        # Interactive Editor (Replaces static dataframe)
        edited_df = st.data_editor(
            df[['본부','지사','구역담당영업사원','이벤트시작일','정지,설변구분','월정료(VAT미포함)','KPI_Status']],
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
        
        st.download_button(
            "📥 Download Filtered Data (CSV)",
            edited_df.to_csv(index=False).encode('utf-8-sig'),
            f"ktt_export_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            type="primary"
        )

if __name__ == "__main__":
    main()
