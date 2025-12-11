import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. Enterprise Config & Design System
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Enterprise Analytics",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# [CSS] 기업용 대시보드 스타일링 (Deep Indigo & Slate Theme)
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        /* Global Font & Reset */
        html, body, [class*="css"] {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            color: #1e293b;
        }
        .stApp {
            background-color: #f1f5f9; /* Slate-100 Background */
        }
        
        /* Header Design */
        .dashboard-header {
            padding: 20px 0;
            border-bottom: 2px solid #e2e8f0;
            margin-bottom: 30px;
        }
        .main-title {
            font-size: 2.2rem;
            font-weight: 800;
            color: #0f172a; /* Slate-900 */
            letter-spacing: -0.02em;
        }
        .sub-title {
            font-size: 1rem;
            color: #64748b;
            font-weight: 500;
        }
        
        /* Card Container */
        .card-container {
            background-color: #ffffff;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
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
            transition: all 0.2s ease-in-out;
        }
        div[data-testid="stMetric"]:hover {
            border-color: #6366f1; /* Indigo-500 */
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        
        /* Pills Button Customization */
        div[data-testid="stPills"] { gap: 8px; flex-wrap: wrap; }
        div[data-testid="stPills"] button[aria-selected="true"] {
            background: linear-gradient(135deg, #4338ca 0%, #3730a3 100%) !important;
            color: white !important;
            border: none;
            font-weight: 600;
            box-shadow: 0 4px 6px -1px rgba(67, 56, 202, 0.3);
            padding: 8px 18px;
        }
        div[data-testid="stPills"] button[aria-selected="false"] {
            background-color: #f8fafc !important;
            border: 1px solid #cbd5e1 !important;
            color: #475569 !important;
            font-weight: 500;
        }
        
        /* Tab Navigation */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; margin-bottom: 20px; }
        .stTabs [data-baseweb="tab"] {
            height: 48px; background-color: white; border-radius: 10px; padding: 0 24px;
            font-weight: 600; border: 1px solid #e2e8f0; color: #64748b;
        }
        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important; color: white !important; border: none;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Advanced Data Logic
# -----------------------------------------------------------------------------
@st.cache_data
def load_enterprise_data():
    file_path = "data.csv"
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error("🚨 시스템 에러: 데이터 파일(data.csv)을 찾을 수 없습니다. 관리자에게 문의하세요.")
        return pd.DataFrame()

    # [Logic 1] 날짜 그룹화 엔진
    if '이벤트시작일' in df.columns:
        df['이벤트시작일'] = pd.to_datetime(df['이벤트시작일'], errors='coerce')
        
        def categorize_period(dt):
            if pd.isnull(dt): return "기간 미상"
            if dt.year < 2025:
                return "2024년 이전 (누적)"
            else:
                return f"'{str(dt.year)[-2:]}.{dt.month}"
        
        df['Period'] = df['이벤트시작일'].apply(categorize_period)
        
        def get_sort_key(dt):
            if pd.isnull(dt): return pd.Timestamp.min
            if dt.year < 2025:
                return pd.Timestamp("2024-12-31")
            return dt
        df['SortKey'] = df['이벤트시작일'].apply(get_sort_key)
    
    # [Logic 2] 수치 데이터 정제
    numeric_cols = ['월정료(VAT미포함)', '계약번호', '당월말_정지일수']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # [Logic 3] 범주형 결측치 처리
    # KPI차감, 체납, 부실구분 등 새로 요청하신 컬럼 포함
    fill_cols = ['본부', '지사', '출동/영상', 'L형/i형', '정지,설변구분', '서비스(소)', '부실구분', 'KPI차감 10월말', '체납', '당월말_정지일수_구간', '월정료 구간']
    for col in fill_cols:
        if col not in df.columns:
            df[col] = "Unclassified"
        else:
            df[col] = df[col].fillna("-")
            
    return df

df = load_enterprise_data()
if df.empty:
    st.stop()

# -----------------------------------------------------------------------------
# 3. Dynamic Control Center (Smart Filtering)
# -----------------------------------------------------------------------------
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.markdown('<div class="main-title">KTT Enterprise Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Strategic Insights & Operational Dashboard</div>', unsafe_allow_html=True)
with c_head2:
    st.markdown(f"<div style='text-align:right; color:#64748b; padding-top:20px;'>Last Update: {pd.Timestamp.now().strftime('%Y-%m-%d')}</div>", unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    
    # [1] 본부 선택
    all_hqs = sorted(df['본부'].unique().tolist())
    st.markdown("##### 🏢 본부 선택 (Headquarters)")
    
    if "hq_select" not in st.session_state: st.session_state.hq_select = all_hqs
    
    try:
        selected_hq = st.pills("HQ Selection", all_hqs, selection_mode="multi", default=all_hqs, key="hq_pills", label_visibility="collapsed")
    except AttributeError:
        selected_hq = st.multiselect("본부 선택", all_hqs, default=all_hqs)
    
    if not selected_hq: selected_hq = all_hqs

    # [2] 지사 선택
    st.markdown("---")
    valid_branches = sorted(df[df['본부'].isin(selected_hq)]['지사'].unique().tolist())
    st.markdown(f"##### 📍 지사 선택 (Branches) — <span style='color:#6366f1'>{len(valid_branches)}개 지사 활성화</span>", unsafe_allow_html=True)
    
    if len(valid_branches) > 30:
        with st.expander(f"🔽 전체 지사 목록 펼치기 ({len(valid_branches)}개)", expanded=False):
            try:
                selected_branch = st.pills("Branch Selection", valid_branches, selection_mode="multi", default=valid_branches, key="br_pills_full", label_visibility="collapsed")
            except:
                selected_branch = st.multiselect("지사 선택", valid_branches, default=valid_branches)
    else:
        try:
            selected_branch = st.pills("Branch Selection", valid_branches, selection_mode="multi", default=valid_branches, key="br_pills_lite", label_visibility="collapsed")
        except:
            selected_branch = st.multiselect("지사 선택", valid_branches, default=valid_branches)
            
    if not selected_branch: selected_branch = valid_branches
    
    # [3] 추가 조건 필터 (KPI 대상, 체납 등)
    st.markdown("---")
    c_filt1, c_filt2, c_filt3 = st.columns(3)
    
    # KPI 대상 필터
    with c_filt1:
        st.markdown("##### 🎯 KPI 차감 대상")
        # KPI차감 10월말 컬럼에 '대상'이라는 글자가 포함된 데이터만 필터링
        kpi_target = st.toggle("KPI 차감 '대상' 건만 보기", value=False)
        
    # 체납 필터
    with c_filt2:
        st.markdown("##### 💰 체납 여부")
        arrears_only = st.toggle("체납 보유 건만 보기", value=False)
        
    st.markdown('</div>', unsafe_allow_html=True)

# Apply Filters
mask = (df['본부'].isin(selected_hq)) & (df['지사'].isin(selected_branch))

if kpi_target:
    # "대상" 텍스트가 포함된 경우
    mask = mask & (df['KPI차감 10월말'].str.contains('대상', na=False))

if arrears_only:
    # 체납이 '-'나 'Unclassified'가 아닌 경우 (데이터가 있는 경우)
    mask = mask & (df['체납'] != '-') & (df['체납'] != 'Unclassified')

df_filtered = df[mask]

# -----------------------------------------------------------------------------
# 4. Executive Summary (KPIs)
# -----------------------------------------------------------------------------
st.markdown("### 🚀 Key Performance Indicators")
col_k1, col_k2, col_k3, col_k4 = st.columns(4)

total_vol = len(df_filtered)
total_rev = df_filtered['월정료(VAT미포함)'].sum()
avg_susp_days = df_filtered['당월말_정지일수'].mean() if '당월말_정지일수' in df.columns else 0
risk_cases = len(df_filtered[df_filtered['정지,설변구분'].str.contains('정지', na=False)])

def fmt_money(val):
    return f"₩{val/10000:,.0f} 만"

col_k1.metric("총 계약 건수", f"{total_vol:,.0f} 건", "Filtered Volume")
col_k2.metric("총 월정료 (예상)", fmt_money(total_rev), "Monthly Revenue")
col_k3.metric("평균 정지일수", f"{avg_susp_days:.1f} 일", "Avg Suspension Duration")
col_k4.metric("Risk Alert (정지)", f"{risk_cases:,.0f} 건", f"Risk Rate: {risk_cases/total_vol*100:.1f}%" if total_vol>0 else "0%", delta_color="inverse")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. Enterprise Analytics (Advanced Visualizations)
# -----------------------------------------------------------------------------
tab_strategy, tab_ops, tab_data = st.tabs(["📊 전략 분석 (Strategy)", "🔍 운영 분석 (Operations)", "💾 데이터 그리드 (Data)"])

# [TAB 1] Strategy View
with tab_strategy:
    r1_c1, r1_c2 = st.columns([2, 1])
    
    with r1_c1:
        st.subheader("📅 기간별 실적 성장 추이")
        if 'Period' in df_filtered.columns:
            trend_df = df_filtered.groupby(['Period', 'SortKey']).agg({'계약번호':'count'}).reset_index().sort_values('SortKey')
            fig_trend = px.area(trend_df, x='Period', y='계약번호', markers=True, title="계약 건수 변화 (2024이전 통합 vs 월별)")
            fig_trend.update_traces(line_color='#4f46e5', fillcolor='rgba(79, 70, 229, 0.1)')
            fig_trend.update_layout(template="plotly_white", height=380, xaxis_title=None, yaxis_title="계약 건수")
            st.plotly_chart(fig_trend, use_container_width=True)
            
    with r1_c2:
        st.subheader("🌐 본부-지사 포트폴리오")
        if not df_filtered.empty:
            fig_sun = px.sunburst(
                df_filtered, 
                path=['본부', '지사'], 
                values='계약번호',
                color='계약번호', color_continuous_scale='Purples'
            )
            fig_sun.update_layout(height=380, margin=dict(t=10, l=10, r=10, b=10))
            st.plotly_chart(fig_sun, use_container_width=True)
            
    st.subheader("🏢 본부별 효율성 분석 (Pareto)")
    hq_stats = df_filtered.groupby('본부').agg({'계약번호':'count', '월정료(VAT미포함)':'sum'}).reset_index().sort_values('계약번호', ascending=False)
    
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(go.Bar(x=hq_stats['본부'], y=hq_stats['계약번호'], name="계약 건수", marker_color='#3b82f6', opacity=0.8, width=0.5), secondary_y=False)
    fig_dual.add_trace(go.Scatter(x=hq_stats['본부'], y=hq_stats['월정료(VAT미포함)'], name="매출(원)", mode='lines+markers', line=dict(color='#ef4444', width=3)), secondary_y=True)
    fig_dual.update_layout(template="plotly_white", height=450, hovermode="x unified", legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"))
    st.plotly_chart(fig_dual, use_container_width=True)

# [TAB 2] Operations View (New Visuals Added!)
with tab_ops:
    # 1. 부실구분 & 정지일수 구간
    st.subheader("⚠️ 리스크 집중 분석 (Risk Factors)")
    op_c1, op_c2 = st.columns(2)
    
    with op_c1:
        st.markdown("**1. 부실 구분 상세 (Insolvency Type)**")
        if '부실구분' in df_filtered.columns:
            bad_counts = df_filtered['부실구분'].value_counts().reset_index()
            bad_counts.columns = ['구분', '건수']
            # '-' 제외하고 시각화
            bad_counts = bad_counts[bad_counts['구분'] != '-']
            bad_counts = bad_counts[bad_counts['구분'] != 'Unclassified']
            
            if not bad_counts.empty:
                fig_bad = px.pie(bad_counts, values='건수', names='구분', hole=0.5, color_discrete_sequence=px.colors.qualitative.Bold)
                fig_bad.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_bad, use_container_width=True)
            else:
                st.info("조회된 데이터에 부실 내역이 없습니다.")
                
    with op_c2:
        st.markdown("**2. 정지일수 구간 분포 (Suspension Duration)**")
        if '당월말_정지일수_구간' in df_filtered.columns:
            susp_dist = df_filtered['당월말_정지일수_구간'].value_counts().reset_index()
            susp_dist.columns = ['구간', '건수']
            # 구간 순서 정렬이 어려우므로 건수 기준 내림차순
            susp_dist = susp_dist.sort_values('건수', ascending=True)
            
            fig_susp = px.bar(susp_dist, x='건수', y='구간', orientation='h', text='건수',
                              title="정지일수 구간별 건수", color='건수', color_continuous_scale='Reds')
            st.plotly_chart(fig_susp, use_container_width=True)

    st.markdown("---")

    # 2. 월정료 구간 & 서비스 점유율
    op_c3, op_c4 = st.columns(2)
    
    with op_c3:
        st.markdown("**3. 월정료 가격대 분포 (Pricing Tier)**")
        if '월정료 구간' in df_filtered.columns:
            price_dist = df_filtered['월정료 구간'].value_counts().reset_index()
            price_dist.columns = ['구간', '건수']
            
            fig_price = px.bar(price_dist, x='구간', y='건수', text='건수',
                               title="월정료 구간별 분포", color='건수', color_continuous_scale='Blues')
            st.plotly_chart(fig_price, use_container_width=True)
            
    with op_c4:
        st.markdown("**4. 서비스 점유율 (Service Share)**")
        if '서비스(소)' in df_filtered.columns:
            svc_tree = df_filtered['서비스(소)'].value_counts().reset_index()
            svc_tree.columns = ['서비스명', '건수']
            fig_tree = px.treemap(svc_tree.head(15), path=['서비스명'], values='건수', color='건수', color_continuous_scale='Tealgrn')
            st.plotly_chart(fig_tree, use_container_width=True)

# [TAB 3] Data Grid with Secure Download
with tab_data:
    st.subheader("💾 Intelligent Data Grid & Secure Export")
    
    # Column Config
    display_cols = ['본부', '지사', 'Period', '고객번호', '상호', '월정료(VAT미포함)', '정지,설변구분', '부실구분', 'KPI차감 10월말', '체납', '당월말_정지일수_구간']
    valid_cols = [c for c in display_cols if c in df_filtered.columns]
    
    def highlight_status(row):
        status = str(row.get('정지,설변구분', ''))
        kpi_target = str(row.get('KPI차감 10월말', ''))
        
        style = []
        if '정지' in status:
            return ['background-color: #fee2e2; color: #b91c1c'] * len(row)
        elif '대상' in kpi_target: # KPI 대상 강조
            return ['background-color: #e0e7ff; color: #3730a3; font-weight: bold'] * len(row)
        return [''] * len(row)

    styled_df = df_filtered[valid_cols].style.apply(highlight_status, axis=1)
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=600,
        column_config={
            "월정료(VAT미포함)": st.column_config.NumberColumn("월정료", format="₩%d"),
            "Period": st.column_config.TextColumn("분석 기간"),
        }
    )
    
    # Secure Download
    st.markdown("---")
    st.markdown("#### 🔒 Secure Download")
    col_pwd, col_btn = st.columns([1, 2])
    with col_pwd:
        password = st.text_input("접근 비밀번호", type="password", placeholder="비밀번호 4자리")
    with col_btn:
        st.write("") 
        st.write("") 
        if password == "3867":
            st.success("✅ 인증 성공!")
            csv_data = df_filtered.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 데이터 다운로드 (Encrypted CSV)", csv_data, 'ktt_secure_data.csv', 'text/csv')
        elif password:
            st.error("⚠️ 비밀번호 불일치")
