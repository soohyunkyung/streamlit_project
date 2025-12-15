import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import altair as alt
from wordcloud import WordCloud
import os
import platform
import ast

# 1. 페이지 설정
st.set_page_config(
    page_title="블로그 데이터 시각화 대시보드",
    page_icon="📊",
    layout="wide"
)

# 2. 폰트 설정 (한글 깨짐 방지)
def get_font_family():
    system_name = platform.system()
    if system_name == "Windows":
        return "Malgun Gothic"
    elif system_name == "Darwin":
        return "AppleGothic"
    else:
        # 리눅스/스트림릿 클라우드 환경
        if os.path.exists('/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf'):
            return "NanumBarunGothic"
        return "sans-serif"

font_family = get_font_family()
plt.rcParams['font.family'] = font_family
plt.rcParams['axes.unicode_minus'] = False

# 3. 데이터 로드 함수
@st.cache_data
def load_csv_data():
    try:
        # 파일 경로 설정 (같은 폴더에 있다고 가정)
        df_wc = pd.read_csv('df_kdh.csv')           # 워드클라우드용
        df_visu = pd.read_csv('df_kdh_visu.csv')    # 차트용 (Seaborn, Altair, Plotly)
        df_net = pd.read_csv('network_edge_list.csv') # 네트워크용
        return df_wc, df_visu, df_net
    except FileNotFoundError as e:
        return None, None, None

st.title("📂 CSV 데이터 기반 시각화 분석")
st.markdown("---")

# 데이터 불러오기
df_kdh, df_kdh_visu, df_network = load_csv_data()

# 파일이 없을 경우 경고 메시지
if df_kdh is None:
    st.error("⚠️ CSV 파일을 찾을 수 없습니다. (df_kdh.csv, df_kdh_visu.csv, network_edge_list.csv 파일이 필요합니다.)")
else:
    # 사이드바: 데이터 미리보기
    with st.sidebar:
        st.header("데이터 상태")
        st.success("✅ 데이터 로드 성공")
        with st.expander("데이터 미리보기"):
            st.write("WordCloud용 데이터:", df_kdh.shape)
            st.write("Chart용 데이터:", df_kdh_visu.shape)
            st.write("Network용 데이터:", df_network.shape)

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["☁️ 워드클라우드", "📊 통계 차트 (3종)", "🕸️ 네트워크 분석"])

    # --- 1. WordCloud (df_kdh.csv) ---
    with tab1:
        st.header("WordCloud Analysis")
        
        # 텍스트 데이터 추출 및 전처리
        # 'description_cleaned' 컬럼이 리스트 문자열("['단어', '단어']")로 되어있을 경우 처리
        if 'description_cleaned' in df_kdh.columns:
            target_col = 'description_cleaned'
        else:
            target_col = df_kdh.columns[0] # 첫번째 컬럼 사용

        all_words = []
        sample_data = df_kdh[target_col].iloc[0]

        try:
            # 문자열 형태의 리스트인지 확인하고 파싱
            if isinstance(sample_data, str) and sample_data.startswith('['):
                df_kdh[target_col] = df_kdh[target_col].apply(ast.literal_eval)
                for row in df_kdh[target_col]:
                    all_words.extend(row)
            else:
                # 일반 텍스트인 경우
                text_blob = " ".join(df_kdh[target_col].astype(str))
                all_words = text_blob.split()
            
            # 워드클라우드 그리기
            wc_font_path = '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf'
            if not os.path.exists(wc_font_path): wc_font_path = font_family

            wc = WordCloud(
                font_path=wc_font_path,
                background_color='white',
                width=1000, height=500,
                max_words=100
            ).generate_from_frequencies(pd.Series(all_words).value_counts())

            fig, ax = plt.subplots(figsize=(12, 6))
            ax.imshow(wc, interpolation='bilinear')
            ax.axis('off')
            st.pyplot(fig)
            
        except Exception as e:
            st.error(f"워드클라우드 생성 중 오류 발생: {e}")

    # --- 2. Charts: Seaborn, Altair, Plotly (df_kdh_visu.csv) ---
    with tab2:
        st.header("Keyword Frequency Visualization")
        
        # 컬럼명 자동 감지 (첫번째: 단어, 두번째: 빈도라고 가정)
        x_col_name = df_kdh_visu.columns[1] # 빈도 (숫자)
        y_col_name = df_kdh_visu.columns[0] # 단어 (문자)
        
        # 상위 20개만 필터링
        df_chart = df_kdh_visu.sort_values(by=x_col_name, ascending=False).head(20)

        col_a, col_b = st.columns(2)
        
        # 2-1. Seaborn
        with col_a:
            st.markdown("### 1. Seaborn (Static)")
            fig_sb, ax_sb = plt.subplots(figsize=(8, 10))
            sns.barplot(data=df_chart, x=x_col_name, y=y_col_name, palette='viridis', ax=ax_sb)
            ax_sb.set_title("Seaborn Bar Plot")
            st.pyplot(fig_sb)

        # 2-2. Altair
        with col_b:
            st.markdown("### 2. Altair (Declarative)")
            chart_alt = alt.Chart(df_chart).mark_bar().encode(
                x=alt.X(f'{x_col_name}:Q', title='Frequency'),
                y=alt.Y(f'{y_col_name}:N', sort='-x', title='Keyword'),
                color=alt.Color(f'{x_col_name}:Q', scale=alt.Scale(scheme='tealblues')),
                tooltip=[y_col_name, x_col_name]
            ).properties(height=600, title="Altair Bar Chart")
            st.altair_chart(chart_alt, use_container_width=True)

        st.markdown("---")

        # 2-3. Plotly
        st.markdown("### 3. Plotly (Interactive)")
        fig_px = px.bar(
            df_chart, 
            x=x_col_name, 
            y=y_col_name, 
            orientation='h',
            title="Plotly Interactive Chart",
            color=x_col_name,
            color_continuous_scale='Viridis',
            height=600
        )
        fig_px.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_px, use_container_width=True)

    # --- 3. NetworkX (network_edge_list.csv) ---
    with tab3:
        st.header("Keyword Network Analysis")
        
        # 엣지 리스트 불러오기 (컬럼: Source, Target, Weight)
        if {'Source', 'Target', 'Weight'}.issubset(df_network.columns):
            
            # 사용자 옵션
            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                layout_mode = st.selectbox("레이아웃 알고리즘", ["spring", "kamada_kawai", "circular"])
            with col_opt2:
                node_scale = st.slider("노드 크기 배율", 10, 100, 50)

            # 그래프 생성
            G = nx.from_pandas_edgelist(df_network, source='Source', target='Target', edge_attr='Weight')
            
            # 레이아웃 계산
            if layout_mode == 'spring':
                pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
            elif layout_mode == 'kamada_kawai':
                pos = nx.kamada_kawai_layout(G)
            else:
                pos = nx.circular_layout(G)

            # 시각화
            fig_net, ax_net = plt.subplots(figsize=(14, 14))
            
            # 노드 크기 (Degree Centrality 기반)
            d = dict(G.degree)
            node_sizes = [v * node_scale for v in d.values()]
            
            # 엣지 두께 (Weight 기반)
            weights = [G[u][v]['Weight'] for u,v in G.edges()]
            max_weight = max(weights) if weights else 1
            edge_widths = [(w / max_weight) * 3 for w in weights] # 최대 두께 3

            nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color="skyblue", alpha=0.9, ax=ax_net)
            nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.4, edge_color="gray", ax=ax_net)
            nx.draw_networkx_labels(G, pos, font_family=font_family, font_size=10, ax=ax_net)
            
            ax_net.set_title(f"Network Graph (Nodes: {len(G.nodes)}, Edges: {len(G.edges)})")
            ax_net.axis('off')
            st.pyplot(fig_net)
            
        else:
            st.error("CSV 파일 컬럼명이 맞지 않습니다. (Source, Target, Weight가 필요합니다)")
            st.write("현재 컬럼:", df_network.columns)
