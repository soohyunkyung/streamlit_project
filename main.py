# ==================== main.py ====================
import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import altair as alt
from wordcloud import WordCloud
import os
import ast

# 페이지 설정
st.set_page_config(
    page_title="블로그 데이터 시각화",
    page_icon="📊",
    layout="wide"
)

# 폰트 설정 (Streamlit Cloud 환경)
def setup_font():
    """한글 폰트 설정"""
    font_paths = [
        '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf',
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        '/System/Library/Fonts/AppleGothic.ttf',
        'C:/Windows/Fonts/malgun.ttf'
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                import matplotlib.font_manager as fm
                fm.fontManager.addfont(font_path)
                font_name = fm.FontProperties(fname=font_path).get_name()
                plt.rcParams['font.family'] = font_name
                plt.rcParams['axes.unicode_minus'] = False
                return font_path
            except:
                continue
    
    # 폰트를 찾지 못한 경우 기본 설정
    plt.rcParams['axes.unicode_minus'] = False
    return None

font_path = setup_font()

# 데이터 로드
@st.cache_data
def load_data():
    """CSV 파일 로드"""
    try:
        df_wc = pd.read_csv('df_kdh.csv')
        df_visu = pd.read_csv('df_kdh_visu.csv')
        df_net = pd.read_csv('network_edge_list.csv')
        return df_wc, df_visu, df_net, None
    except FileNotFoundError as e:
        return None, None, None, str(e)
    except Exception as e:
        return None, None, None, str(e)

# 타이틀
st.title("📊 블로그 데이터 시각화 분석")
st.markdown("---")

# 데이터 로드
df_kdh, df_kdh_visu, df_network, error = load_data()

if error:
    st.error(f"⚠️ 데이터 로드 오류: {error}")
    st.info("""
    필요한 파일:
    - df_kdh.csv (워드클라우드용)
    - df_kdh_visu.csv (차트용)
    - network_edge_list.csv (네트워크용)
    
    파일들을 GitHub 저장소 루트에 업로드해주세요.
    """)
    st.stop()

# 사이드바
with st.sidebar:
    st.header("데이터 정보")
    st.success("✅ 데이터 로드 완료")
    st.metric("워드클라우드 데이터", f"{len(df_kdh)}행")
    st.metric("차트 데이터", f"{len(df_kdh_visu)}행")
    st.metric("네트워크 데이터", f"{len(df_network)}행")

# 탭 구성
tab1, tab2, tab3 = st.tabs(["워드클라우드", "통계 차트", "네트워크"])

# 탭 1: 워드클라우드
with tab1:
    st.header("워드클라우드")
    
    try:
        if 'description_cleaned' in df_kdh.columns:
            col_name = 'description_cleaned'
        else:
            col_name = df_kdh.columns[0]
        
        all_words = []
        sample = df_kdh[col_name].iloc[0]
        
        # 리스트 문자열 파싱
        if isinstance(sample, str) and sample.startswith('['):
            df_kdh[col_name] = df_kdh[col_name].apply(ast.literal_eval)
            for words in df_kdh[col_name]:
                if isinstance(words, list):
                    all_words.extend(words)
        else:
            text = " ".join(df_kdh[col_name].astype(str))
            all_words = text.split()
        
        if not all_words:
            st.warning("추출된 단어가 없습니다")
        else:
            word_freq = pd.Series(all_words).value_counts()
            
            wc = WordCloud(
                font_path=font_path,
                background_color='white',
                width=1200,
                height=600,
                max_words=100
            ).generate_from_frequencies(word_freq)
            
            fig, ax = plt.subplots(figsize=(14, 7))
            ax.imshow(wc, interpolation='bilinear')
            ax.axis('off')
            st.pyplot(fig)
            
            # 상위 단어 표
            st.subheader("상위 20개 단어")
            top_words = word_freq.head(20).reset_index()
            top_words.columns = ['단어', '빈도']
            st.dataframe(top_words, use_container_width=True)
            
    except Exception as e:
        st.error(f"워드클라우드 생성 오류: {e}")
        st.write("데이터 샘플:", df_kdh.head())

# 탭 2: 차트
with tab2:
    st.header("키워드 빈도 분석")
    
    try:
        # 컬럼명 확인
        if len(df_kdh_visu.columns) < 2:
            st.error("데이터에 최소 2개 컬럼이 필요합니다")
        else:
            word_col = df_kdh_visu.columns[0]
            freq_col = df_kdh_visu.columns[1]
            
            # 상위 30개
            top_n = st.slider("표시할 단어 수", 10, 50, 30)
            df_chart = df_kdh_visu.sort_values(by=freq_col, ascending=False).head(top_n)
            
            # Seaborn
            st.subheader("1. Seaborn")
            fig_sb, ax_sb = plt.subplots(figsize=(10, max(8, top_n * 0.3)))
            sns.barplot(data=df_chart, x=freq_col, y=word_col, palette='viridis', ax=ax_sb)
            ax_sb.set_title(f'상위 {top_n}개 키워드')
            ax_sb.set_xlabel('빈도')
            ax_sb.set_ylabel('단어')
            st.pyplot(fig_sb)
            
            st.markdown("---")
            
            # Altair
            st.subheader("2. Altair")
            chart_alt = alt.Chart(df_chart).mark_bar().encode(
                x=alt.X(f'{freq_col}:Q', title='빈도'),
                y=alt.Y(f'{word_col}:N', sort='-x', title='단어'),
                color=alt.Color(f'{freq_col}:Q', scale=alt.Scale(scheme='viridis')),
                tooltip=[word_col, freq_col]
            ).properties(
                height=max(400, top_n * 15),
                title=f'상위 {top_n}개 키워드'
            )
            st.altair_chart(chart_alt, use_container_width=True)
            
            st.markdown("---")
            
            # Plotly
            st.subheader("3. Plotly")
            fig_px = px.bar(
                df_chart,
                x=freq_col,
                y=word_col,
                orientation='h',
                title=f'상위 {top_n}개 키워드',
                color=freq_col,
                color_continuous_scale='Viridis',
                height=max(500, top_n * 20)
            )
            fig_px.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                xaxis_title='빈도',
                yaxis_title='단어'
            )
            st.plotly_chart(fig_px, use_container_width=True)
            
    except Exception as e:
        st.error(f"차트 생성 오류: {e}")
        st.write("데이터 샘플:", df_kdh_visu.head())

# 탭 3: 네트워크
with tab3:
    st.header("키워드 네트워크")
    
    try:
        # 컬럼 확인
        required_cols = {'Source', 'Target', 'Weight'}
        if not required_cols.issubset(df_network.columns):
            st.error(f"필요한 컬럼: {required_cols}")
            st.write("현재 컬럼:", list(df_network.columns))
        else:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                layout = st.selectbox("레이아웃", ["spring", "kamada_kawai", "circular"])
            with col2:
                node_size = st.slider("노드 크기", 10, 150, 50)
            with col3:
                min_weight = st.slider("최소 가중치", 1, 20, 1)
            
            # 필터링
            df_filtered = df_network[df_network['Weight'] >= min_weight]
            
            if len(df_filtered) == 0:
                st.warning("필터 조건에 맞는 데이터가 없습니다")
            else:
                # 그래프 생성
                G = nx.from_pandas_edgelist(
                    df_filtered,
                    source='Source',
                    target='Target',
                    edge_attr='Weight'
                )
                
                # 레이아웃
                if layout == 'spring':
                    pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
                elif layout == 'kamada_kawai':
                    pos = nx.kamada_kawai_layout(G)
                else:
                    pos = nx.circular_layout(G)
                
                # 시각화
                fig, ax = plt.subplots(figsize=(16, 16))
                
                # 노드 크기
                degrees = dict(G.degree())
                node_sizes = [degrees[n] * node_size for n in G.nodes()]
                
                # 엣지 두께
                weights = [G[u][v]['Weight'] for u, v in G.edges()]
                max_w = max(weights) if weights else 1
                edge_widths = [(w / max_w) * 3 for w in weights]
                
                nx.draw_networkx_nodes(
                    G, pos,
                    node_size=node_sizes,
                    node_color='lightblue',
                    alpha=0.8,
                    ax=ax
                )
                nx.draw_networkx_edges(
                    G, pos,
                    width=edge_widths,
                    alpha=0.3,
                    edge_color='gray',
                    ax=ax
                )
                nx.draw_networkx_labels(
                    G, pos,
                    font_size=9,
                    ax=ax
                )
                
                ax.set_title(f'네트워크 (노드: {len(G.nodes)}, 엣지: {len(G.edges)})')
                ax.axis('off')
                st.pyplot(fig)
                
                # 통계
                st.subheader("통계")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("노드", len(G.nodes()))
                with col_b:
                    st.metric("엣지", len(G.edges()))
                with col_c:
                    avg_degree = sum(degrees.values()) / len(degrees) if degrees else 0
                    st.metric("평균 연결도", f"{avg_degree:.2f}")
                    
    except Exception as e:
        st.error(f"네트워크 생성 오류: {e}")
        st.write("데이터 샘플:", df_network.head())
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
