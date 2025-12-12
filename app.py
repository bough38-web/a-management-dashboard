import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. Page Config & CSS Design System (HTML 스타일 이식)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KTT Retention Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# HTML의 CSS 변수와 스타일을 Streamlit에 적용
st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        /* Global Reset */
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
            color: #0f172a;
        }
        .stApp {
            background-color: #f1f5f9; /* --bg-body */
        }
        
        /* Card Style */
        .kpi-card {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.05);
            border: 1px solid #e2e8f0;
            border-left-width: 5px;
            transition: transform 0.2s;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }
        .kpi-title {
            font-size: 0.85rem;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .kpi-value {
            font-size: 1.8rem;
            font-weight: 800;
            color: #0f172a;
        }
        
        /* Chart Container */
        .chart-container {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            border: 1px solid #e2e8f0;
            margin-bottom: 20px;
        }
        .chart-header {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
        }
        
        /* Custom Badges for Dataframe */
        div[data-testid="stDataFrame"] {
            font-size: 0.9rem;
        }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Data Generation (Mock Data 생성 - CSV 대체)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    # 시드 고정
    np.random.seed(42)
    
    # 공통 데이터
    n_rows = 300
    hqs = ['강북/강원'] * 200 + ['서울'] * 100
    branches_kangbuk = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
    branches_seoul = ['강남', '서초', '송파', '강동']
    managers = [f'매니저{i}' for i in range(1, 21)]
    
    # 1. Pipeline Data (해지방어)
    pipeline_data = []
    for i in range(n_rows):
        hq = np.random.choice(hqs)
        br = np.random.choice(branches_kangbuk if hq == '강북/강원' else branches_seoul)
        stage = np.random.choice(['방어성공', '방어실패', '진행중'], p=[0.4, 0.2, 0.4])
        risk = np.random.randint(10, 99)
        revenue = np.random.randint(20, 500) * 1000 # 2만원 ~ 50만원
        
        reason = np.random.choice(
            ['비용 부담', '타사 이전', '폐업/이전', '서비스 불만', '단순 변심', '약정 만료'], 
            p=[0.3, 0.2, 0.2, 0.1, 0.1, 0.1]
        ) if stage != '방어성공' else '-'
        
        date = datetime(2025, 1, 1) + timedelta(days=np.random.randint(0, 90))
        
        pipeline_data.append({
            '관리본부': hq,
            '관리지사': br,
            '담당자': np.random.choice(managers),
            '계약번호': 10000000 + i,
            '상호': f'고객사_{i}',
            '채널': np.random.choice(['SP', 'SC', 'AM']),
            '월정료': revenue,
            '방어진행단계': stage,
            '해지위험도': risk,
            '해지사유': reason,
            '등록일자': date
        })
    
    # 2. VOC Data (고객관리)
    voc_data = []
    for i in range(n_rows):
        hq = np.random.choice(hqs)
        br = np.random.choice(branches_kangbuk if hq == '강북/강원' else branches_seoul)
        status = np.random.choice(['처리완료', '접수', '미접수'], p=[0.5, 0.3, 0.2])
        voc_type = np.random.choice(['요금문의', '기술지원', '설치변경', '해지상담'], p=[0.2, 0.4, 0.2, 0.2])
        
        voc_data.append({
            '관리본부': hq,
            '관리지사': br,
            '담당자': np.random.choice(managers),
            '계약번호': 20000000 + i,
            '상호': f'고객사_{i}',
            '상태': status,
            'VOC유형': voc_type,
            '합산월정료': np.random.randint(20, 300) * 1000,
            '등록일자': datetime(2025, 1, 1) + timedelta(days=np.random.randint(0, 90))
        })
        
    return pd.DataFrame(voc_data), pd.DataFrame(pipeline_data)

df_voc_raw, df_pipeline_raw = load_data()

# -----------------------------------------------------------------------------
# 3. Sidebar & Filtering Logic
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🏢 KTT 통합 대시보드")
    
    # 3.1 View Switcher (VOC vs Pipeline)
    view_mode = st.radio(
        "분석 모드 선택",
        ["VOC 활동 현황", "해지 파이프라인"],
        index=0,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 3.2 Cascading Filters (공통 로직)
    target_df = df_voc_raw if view_mode == "VOC 활동 현황" else df_pipeline_raw
    
    # A. 본부 선택
    all_hqs = sorted(target_df['관리본부'].unique())
    sel_hq = st.multiselect("관리본부", all_hqs, default=all_hqs)
    
    # B. 지사 선택 (본부에 종속)
    filtered_by_hq = target_df[target_df['관리본부'].isin(sel_hq)]
    
    # 지사 정렬 (중앙, 강북... 순서 유지 로직)
    custom_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
    avail_branches = filtered_by_hq['관리지사'].unique().tolist()
    # 순서가 있는 것과 없는 것 분리하여 정렬
    sorted_branches = sorted([b for b in avail_branches if b in custom_order], key=lambda x: custom_order.index(x)) + \
                      sorted([b for b in avail_branches if b not in custom_order])
    
    sel_branch = st.multiselect("관리지사", sorted_branches, default=sorted_branches)
    
    # C. 담당자 선택 (지사에 종속)
    filtered_by_br = filtered_by_hq[filtered_by_hq['관리지사'].isin(sel_branch)]
    avail_mgrs = sorted(filtered_by_br['담당자'].unique())
    sel_mgr = st.multiselect("담당자", avail_mgrs, default=avail_mgrs, placeholder="담당자 검색...")
    
    # 3.3 Mode-Specific Filters
    if view_mode == "해지 파이프라인":
        st.markdown("---")
        st.markdown("#### ⚙️ 추가 필터")
        sel_channel = st.selectbox("영업 채널", ["ALL", "SP", "SC", "AM"])
        min_risk = st.slider("최소 해지 위험도 (%)", 0, 100, 50)
    else:
        st.markdown("---")
        st.markdown("#### ⚙️ 추가 필터")
        sel_voc_status = st.multiselect("VOC 상태", ["처리완료", "접수", "미접수"], default=["처리완료", "접수", "미접수"])

# Apply Filters
final_df = filtered_by_br[filtered_by_br['담당자'].isin(sel_mgr)]

if view_mode == "해지 파이프라인":
    if sel_channel != "ALL":
        final_df = final_df[final_df['채널'] == sel_channel]
    final_df = final_df[final_df['해지위험도'] >= min_risk]
else:
    final_df = final_df[final_df['상태'].isin(sel_voc_status)]


# -----------------------------------------------------------------------------
# 4. KPI Card Component (HTML Style)
# -----------------------------------------------------------------------------
def render_kpi_card(title, value, sub_text, color_code):
    st.markdown(f"""
        <div class="kpi-card" style="border-left-color: {color_code};">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 5px;">{sub_text}</div>
        </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Dashboard Views
# -----------------------------------------------------------------------------

# ==========================================
# VIEW A: VOC 활동 현황
# ==========================================
if view_mode == "VOC 활동 현황":
    st.markdown("### 📞 관리고객(VOC) 활동 현황")
    
    # 1. KPI Section
    k1, k2, k3, k4 = st.columns(4)
    total_voc = len(final_df)
    done_voc = len(final_df[final_df['상태'] == '처리완료'])
    pending_voc = len(final_df[final_df['상태'] == '미접수'])
    rate = (done_voc / total_voc * 100) if total_voc > 0 else 0
    
    with k1: render_kpi_card("총 VOC 접수", f"{total_voc:,}", "전체 접수 건수", "#3b82f6")
    with k2: render_kpi_card("처리 완료", f"{done_voc:,}", "조치 완료 건수", "#10b981")
    with k3: render_kpi_card("처리율", f"{rate:.1f}%", "전체 대비 완료율", "#f59e0b")
    with k4: render_kpi_card("미접수 건", f"{pending_voc:,}", "즉시 조치 필요", "#ef4444")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. Charts Section
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown('<div class="chart-header">📉 담당자별 미접수 현황 (Top 10)</div>', unsafe_allow_html=True)
        # Data Prep
        ag_data = final_df[final_df['상태'].isin(['미접수', '접수'])].groupby(['담당자', '상태']).size().reset_index(name='건수')
        # Sort by total
        ag_order = final_df[final_df['상태']=='미접수'].groupby('담당자').size().sort_values(ascending=False).head(10).index.tolist()
        ag_data = ag_data[ag_data['담당자'].isin(ag_order)]
        
        fig_ag = px.bar(ag_data, x='건수', y='담당자', color='상태', orientation='h', 
                        color_discrete_map={'미접수': '#ef4444', '접수': '#f59e0b'},
                        category_orders={'담당자': ag_order})
        fig_ag.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_ag, use_container_width=True)
        
    with c2:
        st.markdown('<div class="chart-header">🏢 지사별 처리 현황</div>', unsafe_allow_html=True)
        br_data = final_df.groupby(['관리지사', '상태']).size().reset_index(name='건수')
        fig_br = px.bar(br_data, x='관리지사', y='건수', color='상태',
                        color_discrete_map={'처리완료': '#3b82f6', '접수': '#f59e0b', '미접수': '#ef4444'},
                        category_orders={'관리지사': sorted_branches})
        fig_br.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_br, use_container_width=True)

    # 3. Data Grid
    st.markdown('<div class="chart-header">📋 상세 데이터 리스트</div>', unsafe_allow_html=True)
    st.dataframe(
        final_df[['관리지사', '담당자', '계약번호', '상호', '상태', 'VOC유형', '합산월정료', '등록일자']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "합산월정료": st.column_config.NumberColumn(format="₩%d"),
            "등록일자": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "상태": st.column_config.TextColumn()
        }
    )

# ==========================================
# VIEW B: 해지 파이프라인
# ==========================================
elif view_mode == "해지 파이프라인":
    st.markdown("### 🛡️ 해지 파이프라인 분석")
    
    # 1. KPI Section
    p1, p2, p3, p4 = st.columns(4)
    tot_amt = final_df['월정료'].sum()
    high_risk = len(final_df[final_df['해지위험도'] >= 80])
    success_cnt = len(final_df[final_df['방어진행단계'] == '방어성공'])
    fail_cnt = len(final_df[final_df['방어진행단계'] == '방어실패'])
    succ_rate = (success_cnt / (success_cnt + fail_cnt) * 100) if (success_cnt + fail_cnt) > 0 else 0
    
    with p1: render_kpi_card("관리 대상 금액", f"{tot_amt/100000000:.1f}억", "월정료 합계", "#2563eb")
    with p2: render_kpi_card("고위험군 (80%↑)", f"{high_risk:,}", "집중 관리 필요", "#ef4444")
    with p3: render_kpi_card("방어 성공", f"{success_cnt:,}", "해지 방어 완료", "#10b981")
    with p4: render_kpi_card("방어 성공률", f"{succ_rate:.1f}%", "성공 / (성공+실패)", "#f59e0b")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. Main Charts (Bubble & Trend)
    row2_1, row2_2 = st.columns([2, 1])
    
    with row2_1:
        st.markdown('<div class="chart-header">🎯 위험도 vs 월정료 (4분면 분석)</div>', unsafe_allow_html=True)
        # Bubble Chart with Quadrants
        fig_bubble = px.scatter(
            final_df, x="해지위험도", y="월정료", 
            size="월정료", color="방어진행단계",
            hover_name="상호", text="관리지사",
            color_discrete_map={'방어성공': '#10b981', '진행중': '#f59e0b', '방어실패': '#ef4444'},
            size_max=40
        )
        
        # Add Quadrant Lines
        avg_risk = final_df['해지위험도'].mean()
        avg_rev = final_df['월정료'].mean()
        fig_bubble.add_hline(y=avg_rev, line_dash="dash", line_color="gray", annotation_text="평균 월정료")
        fig_bubble.add_vline(x=avg_risk, line_dash="dash", line_color="gray", annotation_text="평균 위험도")
        
        fig_bubble.update_layout(height=400, margin=dict(l=0,r=0,t=20,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(240,240,240,0.5)')
        st.plotly_chart(fig_bubble, use_container_width=True)
        
    with row2_2:
        st.markdown('<div class="chart-header">🍩 해지 사유 분석</div>', unsafe_allow_html=True)
        reason_data = final_df[final_df['해지사유'] != '-'].groupby('해지사유').size().reset_index(name='건수')
        fig_donut = px.pie(reason_data, values='건수', names='해지사유', hole=0.6,
                           color_discrete_sequence=px.colors.qualitative.Prism)
        fig_donut.update_layout(height=400, margin=dict(l=0,r=0,t=20,b=0), showlegend=True, legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig_donut, use_container_width=True)
        
    # 3. Trend & Stage
    st.markdown('<div class="chart-header">📊 월별 방어 현황 및 성공률</div>', unsafe_allow_html=True)
    # Group by Month
    final_df['Month'] = final_df['등록일자'].dt.strftime('%Y-%m')
    trend = final_df.groupby(['Month', '방어진행단계']).size().reset_index(name='건수')
    
    fig_trend = px.bar(trend, x='Month', y='건수', color='방어진행단계',
                       color_discrete_map={'방어성공': '#10b981', '진행중': '#f59e0b', '방어실패': '#ef4444'})
    fig_trend.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # 4. Data Grid
    st.markdown('<div class="chart-header">📋 상세 파이프라인 리스트</div>', unsafe_allow_html=True)
    
    # Apply styling to dataframe
    st.dataframe(
        final_df[['관리지사', '담당자', '계약번호', '상호', '채널', '월정료', '방어진행단계', '해지위험도', '해지사유', '등록일자']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "월정료": st.column_config.NumberColumn(format="₩%d"),
            "해지위험도": st.column_config.ProgressColumn(
                format="%d%%",
                min_value=0,
                max_value=100,
            ),
            "방어진행단계": st.column_config.TextColumn(),
            "등록일자": st.column_config.DateColumn(format="YYYY-MM-DD")
        }
    )

# -----------------------------------------------------------------------------
# 6. Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption("© 2025 KTT Enterprise Analytics Team. Optimized for Chrome.")
