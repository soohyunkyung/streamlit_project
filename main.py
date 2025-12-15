#-------------------------------------AI helped---------------------------
import streamlit as st
import pandas as pd
import requests
import re
from konlpy.tag import Okt
from collections import Counter
from itertools import combinations
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from wordcloud import WordCloud
import seaborn as sns
import plotly.express as px
import ast

st.set_page_config(
    page_title="네이버 블로그 분석",
    page_icon="📊",
    layout="wide"
)

plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

st.title("네이버 블로그 키워드 분석")
st.markdown("---")

st.sidebar.header("설정")

if 'df' not in st.session_state:
    st.session_state.df = None
if 'word_counts' not in st.session_state:
    st.session_state.word_counts = None

tab1, tab2, tab3, tab4 = st.tabs(["데이터 수집", "전처리", "시각화", "네트워크"])

# 데이터 수집
with tab1:
    st.header("데이터 수집")
    
    col1, col2 = st.columns(2)
    
    with col1:
        client_id = st.text_input("Client ID", value="8ARlBk0ZI4GdhNsfG4Jq", type="password")
        search_keyword = st.text_input("검색어", value="케이팝 데몬 헌터스")
        max_results = st.number_input("수집 개수", min_value=100, max_value=25000, value=1000, step=100)
    
    with col2:
        client_secret = st.text_input("Client Secret", value="j8Q1PLyChH", type="password")
        sort_option = st.selectbox("정렬", ["sim (정확도)", "date (최신순)"])
    
    if st.button("수집 시작"):
        with st.spinner("데이터 수집 중"):
            url = "https://openapi.naver.com/v1/search/blog.json"
            headers = {
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret
            }
            
            all_items = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_iterations = max_results // 100
            
            for idx, start_index in enumerate(range(1, max_results + 1, 100)):
                params = {
                    "query": search_keyword,
                    "display": 100,
                    "start": start_index,
                    "sort": sort_option.split()[0]
                }
                
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    all_items.extend(data['items'])
                    progress = (idx + 1) / total_iterations
                    progress_bar.progress(progress)
                    status_text.text(f"{len(all_items)}개 수집됨")
                else:
                    st.error(f"오류: {response.status_code}")
                    break
            
            df = pd.DataFrame(all_items)
            df['title'] = df['title'].str.replace('<b>', '').str.replace('</b>', '')
            df['description'] = df['description'].str.replace('<b>', '').str.replace('</b>', '')
            df.drop(['bloggername', 'bloggerlink'], axis=1, inplace=True)
            
            st.session_state.df = df
            
            st.success(f"{len(df)}개 수집 완료")
            st.dataframe(df.head(10), use_container_width=True)

# 전처리
with tab2:
    st.header("전처리")
    
    if st.session_state.df is None:
        st.warning("먼저 데이터를 수집하세요")
    else:
        df = st.session_state.df.copy()
        
        st.subheader("불용어 설정")
        default_stopwords = ['케이팝', '데몬', '헌터스', '하다', '케데헌', '보다', '애니메이션', 
                            '영화', '되다', '이다', '이', '인기', '트릭', '스', '가다',
                            '있다', '요즘', '나오다', '이번', '공개', '않다', '바로', 
                            '되어다', '아니다', '안녕하다', '넷플릭스']
        
        stopwords_text = st.text_area(
            "불용어 목록 (쉼표 구분)", 
            value=", ".join(default_stopwords),
            height=100
        )
        
        custom_stopwords = [word.strip() for word in stopwords_text.split(',')]
        
        if st.button("전처리 실행"):
            with st.spinner("처리 중"):
                okt = Okt()
                
                stop_str = '에 가 이은 을 를 의 도 또한 더 를 위해 에게 에게서 에게로 부터 어 우선 이후 하는 입니다 이거 이건'
                stop_words = set(stop_str.split(' '))
                stop_set = set(custom_stopwords)
                
                def preprocess_text(text):
                    if not isinstance(text, str):
                        return []
                    
                    text = re.sub(r'[a-zA-Z0-9_\-\.]+@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,6})', ' ', text)
                    text = re.sub(r'<[^>]*>', ' ', text)
                    text = re.sub(r'[ㄱ-ㅎㅏ-ㅣ]+', ' ', text)
                    text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', text)
                    
                    pos_results = okt.pos(text, stem=True)
                    
                    final_words = []
                    for word, pos in pos_results:
                        if pos in ['Noun', 'Verb', 'Adjective']:
                            if word not in stop_words and word not in stop_set and len(word) > 1:
                                final_words.append(word)
                    
                    return final_words
                
                progress_bar = st.progress(0)
                
                df['title_cleaned'] = df['title'].apply(preprocess_text)
                progress_bar.progress(0.5)
                
                df['description_cleaned'] = df['description'].apply(preprocess_text)
                progress_bar.progress(1.0)
                
                all_words = [word for sublist in df['description_cleaned'] for word in sublist]
                word_counts = Counter(all_words)
                
                st.session_state.df = df
                st.session_state.word_counts = word_counts
                
                st.success("전처리 완료")
                
                st.subheader("상위 50개 단어")
                top_50 = word_counts.most_common(50)
                top_df = pd.DataFrame(top_50, columns=['단어', '빈도'])
                st.dataframe(top_df, use_container_width=True)

# 시각화
with tab3:
    st.header("시각화")
    
    if st.session_state.word_counts is None:
        st.warning("먼저 전처리를 완료하세요")
    else:
        word_counts = st.session_state.word_counts
        
        viz_type = st.selectbox(
            "차트 종류",
            ["워드클라우드", "막대 그래프", "인터랙티브 차트"]
        )
        
        top_n = st.slider("단어 개수", min_value=10, max_value=100, value=30, step=5)
        
        if viz_type == "워드클라우드":
            st.subheader("워드클라우드")
            
            with st.spinner("생성 중"):
                fig, ax = plt.subplots(figsize=(12, 8))
                
                wc = WordCloud(
                    font_path='/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf',
                    background_color='white',
                    width=1200,
                    height=800,
                    max_words=top_n
                )
                
                wc.generate_from_frequencies(word_counts)
                
                ax.imshow(wc, interpolation='bilinear')
                ax.axis('off')
                
                st.pyplot(fig)
        
        elif viz_type == "막대 그래프":
            st.subheader("막대 그래프")
            
            top_words = word_counts.most_common(top_n)
            viz_df = pd.DataFrame(top_words, columns=['단어', '빈도'])
            
            fig, ax = plt.subplots(figsize=(12, max(8, top_n * 0.3)))
            sns.barplot(data=viz_df, x='빈도', y='단어', palette='viridis', ax=ax)
            ax.set_title(f'상위 {top_n}개 단어', fontsize=16)
            ax.set_xlabel('빈도', fontsize=12)
            ax.set_ylabel('단어', fontsize=12)
            plt.tight_layout()
            
            st.pyplot(fig)
        
        elif viz_type == "인터랙티브 차트":
            st.subheader("인터랙티브 차트")
            
            top_words = word_counts.most_common(top_n)
            viz_df = pd.DataFrame(top_words, columns=['단어', '빈도'])
            
            fig = px.bar(
                viz_df,
                x='빈도',
                y='단어',
                orientation='h',
                title=f'상위 {top_n}개 단어',
                color='빈도',
                color_continuous_scale='Viridis',
                hover_data=['단어', '빈도'],
                height=max(600, top_n * 20)
            )
            
            fig.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                xaxis_title='빈도',
                yaxis_title='단어'
            )
            
            st.plotly_chart(fig, use_container_width=True)

# 네트워크 분석
with tab4:
    st.header("네트워크 분석")
    
    if st.session_state.df is None or 'description_cleaned' not in st.session_state.df.columns:
        st.warning("먼저 전처리를 완료하세요")
    else:
        df = st.session_state.df
        
        col1, col2 = st.columns(2)
        
        with col1:
            min_edge_count = st.slider("최소 연결 빈도", min_value=5, max_value=100, value=20, step=5)
            k_value = st.slider("간격 조절", min_value=0.05, max_value=2.0, value=0.15, step=0.05)
        
        with col2:
            iterations = st.slider("반복 횟수", min_value=100, max_value=500, value=300, step=50)
            scale_value = st.slider("크기 조절", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
        
        if st.button("네트워크 생성"):
            with st.spinner("생성 중"):
                edge_list = []
                
                for nouns in df['description_cleaned']:
                    unique_nouns = sorted(set(nouns))
                    if len(unique_nouns) > 1:
                        edge_list.extend(combinations(unique_nouns, 2))
                
                edge_counts = Counter(edge_list)
                filtered_edges = {edge: weight for edge, weight in edge_counts.items() 
                                if weight >= min_edge_count}
                
                st.info(f"엣지 개수: {len(filtered_edges)}개")
                
                G = nx.Graph()
                weighted_edges = [
                    (node1, node2, weight)
                    for (node1, node2), weight in filtered_edges.items()
                ]
                G.add_weighted_edges_from(weighted_edges)
                
                pos_spring = nx.spring_layout(
                    G,
                    k=k_value,
                    iterations=iterations,
                    seed=42,
                    scale=scale_value
                )
                
                fig, ax = plt.subplots(figsize=(18, 18), dpi=100)
                
                node_sizes = [min(G.degree(node) * 50, 1000) for node in G.nodes()]
                edge_widths = [min(G[u][v]['weight'] * 0.02, 5) for u, v in G.edges()]
                
                nx.draw_networkx(
                    G,
                    pos_spring,
                    with_labels=True,
                    node_size=node_sizes,
                    width=edge_widths,
                    font_size=10,
                    font_family='NanumGothic',
                    node_color='lightblue',
                    edge_color='gray',
                    alpha=0.8,
                    linewidths=2,
                    edgecolors='navy',
                    ax=ax
                )
                
                ax.set_title("키워드 네트워크",
                           fontsize=22,
                           fontfamily='NanumGothic',
                           pad=20)
                ax.axis('off')
                plt.tight_layout()
                
                st.pyplot(fig)
                
                st.subheader("통계")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("노드", G.number_of_nodes())
                with col2:
                    st.metric("엣지", G.number_of_edges())
                with col3:
                    avg_degree = sum(dict(G.degree()).values()) / G.number_of_nodes()
                    st.metric("평균 연결도", f"{avg_degree:.2f}")

st.sidebar.markdown("---")
st.sidebar.header("다운로드")

if st.session_state.df is not None:
    csv = st.session_state.df.to_csv(index=False, encoding='utf-8-sig')
    st.sidebar.download_button(
        label="CSV 다운로드",
        data=csv,
        file_name="result.csv",
        mime="text/csv"
    )

st.sidebar.markdown("---")
st.sidebar.info("""
목차:
1. 데이터 수집
2. 전처리
3. 시각화
4. 네트워크 분석
""")
