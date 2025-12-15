#-----------------AI helped-------------------
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

# 1. 페이지 및 폰트 설정
st.set_page_config(page_title="CSV 데이터 시각화 대시보드", layout="wide")

def get_font_family():
    system_name = platform.system()
    if system_name == "Windows": return "Malgun Gothic"
    elif system_name == "Darwin": return "AppleGothic"
    else:
        if os.path.exists('/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf'):
            return "NanumBarunGothic"
        return "sans-serif"

font_family = get_font_family()
plt.rcParams['font.family'] = font_family
plt.rcParams['axes.unicode_minus'] = False

st.title("📊 블로그 데이터 분석 시각화")
st.markdown("---")

# 2. 데이터 로드 함수
@st.cache_data
def load_data():
    try:
        # 파일이 존재하는지 확인하고 로드
        df_wc = pd.read_csv('df_kdh.csv')           # 워드클라우드용 (원본 텍스트 추정)
        df_visu = pd.read_csv('df_kdh_visu.csv')    # 차트용 (빈도수 데이터 추정)
        df_net = pd.read_csv('network_edge_list.csv') # 네트워크용 (엣지 리스트)
        return df_wc, df_visu, df_net
    except FileNotFoundError as e:
        st.error(f"파일을 찾을 수 없습니다: {e}")
        return None, None, None

# 데이터 불러오기
df_kdh, df_kdh_visu, df_network = load_data()

# 데이터가 잘 로드되었을 때만 실행
if df_kdh is not None:
    
    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["☁️ 워드클라우드", "📊 통계 차트", "🕸️ 네트워크"])

    # --- Tab 1: WordCloud (df_kdh.csv) ---
    with tab1:
        st.header("WordCloud Analysis")
        
        # 텍스트 데이터 전처리 (리스트가 문자열로 저장된 경우 변환)
        # 'description_cleaned' 컬럼이 있다고 가정 (없으면 텍스트 컬럼 자동 탐색)
        text_col = 'description_cleaned' if 'description_cleaned' in df_kdh.columns else df_kdh.columns[0]
        
        all_words = []
        # 데이터가 이미 전처리된 리스트 형태인지, 일반 문장인지 확인
        sample = df_kdh[text_col].iloc[0] if not df_kdh.empty else ""
        
        try:
            if isinstance(sample, str) and sample.startswith('['):
                # 문자열로 된 리스트 "['단어', '단어']" -> 실제 리스트 변환
                df_kdh[text_col] = df_kdh[text_col].apply(ast.literal_eval)
                for row in df_kdh[text_col]:
                    all_words.extend(row)
            else:
                # 일반 텍스트인 경우
                text_data = " ".join(df_kdh[text_col].astype(str))
                all_words = text_data.split()
        except:
            st.warning("데이터 형식을 변환하는 중 오류가 발생했습니다. 텍스트 컬럼을 확인해주세요.")

        # 워드클라우드 생성
        if all_words:
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
        else:
            st.error("워드클라우드를 생성할 텍스트 데이터가 없습니다.")

    # --- Tab 2: Charts (df_kdh_visu.csv) -> Seaborn, Plotly, Altair ---
    with tab2:
        st.header("Keyword Frequency Charts")
        
        # 컬럼 이름 확인 (보통 '단어', '빈도' 혹은 'Word', 'Count' 등일 것임)
        cols = df_kdh_visu.columns
        x_col = cols[1] # 빈도 (숫자)
        y_col = cols[0] # 단어 (문자)
        
        # 데이터 정렬 (빈도 내림차순)
        df_chart = df_kdh_visu.sort_values(by=x_col, ascending=False).head(20)

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1. Seaborn (Static)")
            fig_sb, ax_sb = plt.subplots(figsize=(8, 10))
            sns.barplot(data=df_chart, x=x_col, y=y_col, palette='viridis', ax=ax_sb)
            ax_sb.set_title("Top 20 Keywords")
            st.pyplot(fig_sb)

        with col2:
            st.subheader("2. Altair (Declarative)")
            chart = alt.Chart(df_chart).mark_bar().encode(
                x=alt.X(f'{x_col}:Q', title='Frequency'),
                y=alt.Y(f'{y_col}:N', sort='-x', title='Keyword'),
                color=f'{x_col}:Q',
                tooltip=[y_col, x_col]
            ).properties(height=600)
            st.altair_chart(chart, use_container_width=True)
            
        st.markdown("---")
        st.subheader("3. Plotly (Interactive)")
        fig_px = px.bar(
            df_chart, x=x_col, y=y_col, 
            orientation='h', 
            color=x_col,
            title="Interactive Keyword Frequency",
            height=600
        )
        fig_px.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_px, use_container_width=True)

    # --- Tab 3: Network (network_edge_list.csv) -> NetworkX ---
    with tab3:
        st.header("Keyword Network Analysis")
        
        # 컬럼 확인 (Source, Target, Weight 가정)
        if {'Source', 'Target', 'Weight'}.issubset(df_network.columns):
            G = nx.from_pandas_edgelist(
                df_network, 
                source='Source', 
                target='Target', 
                edge_attr='Weight'
            )
            
            # 시각화 옵션
            layout_opt = st.radio("레이아웃 선택", ["kamada_kawai", "spring"])
            
            fig_net, ax_net = plt.subplots(figsize=(15, 15))
            
            # 레이아웃 계산
            if layout_opt == "kamada_kawai":
                pos = nx.kamada_kawai_layout(G)
            else:
                pos = nx.spring_layout(G, k=0.5, iterations=50)
            
            # 노드 크기 (차수 기반)
            d = dict(G.degree)
            node_sizes = [v * 100 for v in d.values()]
            
            # 그리기
            nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color="skyblue", alpha=0.9, ax=ax_net)
            nx.draw_networkx_edges(G, pos, width=[d['Weight']*0.1 for u,v,d in G.edges(data=True)], alpha=0.4, edge_color="gray", ax=ax_net)
            nx.draw_networkx_labels(G, pos, font_family=font_family, font_size=10, ax=ax_net)
            
            ax_net.axis('off')
            ax_net.set_title(f"Network Graph (Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()})")
            st.pyplot(fig_net)
            
        else:
            st.error("CSV 파일 형식이 맞지 않습니다. (Source, Target, Weight 컬럼이 필요합니다.)")
            st.write("현재 컬럼:", df_network.columns)

else:
    st.info("CSV 파일들을 프로젝트 폴더에 넣어주세요 (df_kdh.csv, df_kdh_visu.csv, network_edge_list.csv)")
