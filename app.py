import streamlit as st
import pandas as pd
import plotly.express as px
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import feedparser

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Smart Balance Pro", layout="centered")

st.markdown("""
    <style>
    .stApp { background: #0e1117; color: #ffffff; }
    div[data-testid="stExpander"] { background: #1e1e1e; border: 1px solid #333; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
@st.cache_data(ttl=3600)
def buscar_noticias_financeiras():
    try:
        with DDGS() as ddgs:
            query = "site:infomoney.com.br OR site:statusinvest.com.br notícias mercado ações fiis maio 2026"
            return list(ddgs.text(query, max_results=5))
    except:
        return []

@st.cache_data(ttl=60)
def carregar_dados():
    try:
        # [Sua lógica de extração mantida]
        SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSvID5Q3Tp7biTamvnU-rsDwVRWPRqJbIcrKRJd4GTrJE05smWhM4eU4TA0MtGqBbfpijtQapRNE6pd/pub?gid=123758560&single=true&output=csv"
    
        df_raw = pd.read_csv(SHEET_URL, header=None, dtype=str)
            
       # 1. Extrair DF Principal (O que contém a coluna 'Meta')
        idx_start = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains('Classe', case=False).any(), axis=1)].index[0] + 1
        idx_end = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains('Cofrinho', case=False).any(), axis=1)].index[0]
        df_main = df_raw.iloc[idx_start:idx_end, [0, 1, 3]].copy()
        df_main.columns = ['Classe', 'Valor_Atual', 'Meta'] # Garante o nome 'Meta'
        df_main['Valor_Atual'] = pd.to_numeric(df_main['Valor_Atual'].str.replace(',', '.'), errors='coerce')
        df_main['Meta'] = pd.to_numeric(df_main['Meta'].str.replace('%', '').str.replace(',', '.'), errors='coerce')
        
        # 2. Extrair Blocos (Ações e FIIs)
        def extrair_bloco(termo_inicio, termo_fim):
            idx_s = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains(termo_inicio, case=False).any(), axis=1)].index[0] + 1
            idx_e = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains(termo_fim, case=False).any(), axis=1)].index[0]
            df = df_raw.iloc[idx_s:idx_e, [0, 1, 2]].copy()
            df.columns = ['Nome', 'Valor_Atual', 'Meta_Perc']
            for col in ['Valor_Atual', 'Meta_Perc']:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace('%', '').str.replace(',', '.'), errors='coerce')
            df['Diferença'] = (df['Meta_Perc'] - (df['Valor_Atual'] / df['Valor_Atual'].sum() * 100))
            return df.dropna()

        df_acoes = extrair_bloco('Segmento de Ações', 'Total atual dos FIIS')
        df_fiis = extrair_bloco('Tipo de FII', 'Segmento de Tijolo')
        
        aporte_idx = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains('Aporte Mensal', case=False).any(), axis=1)].index[0]
        aporte = float(str(df_raw.iloc[aporte_idx, 1]).replace(',', '.'))
        
        return df_main, df_acoes, df_fiis, aporte
    except Exception as e:
        st.error(f"Erro no carregamento: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 0.0

# --- INTERFACE ---
st.title("⚖️ Smart Balance Pro")
# Chamada no App
df, df_acoes,df_fiis, aporte_base = carregar_dados()
df = df.rename(columns={'Classe': 'Ativo'})

if not df.empty:
    st.sidebar.header("⚙️ Configurações")
    novo_aporte = st.sidebar.number_input("Valor do Aporte (R$)", value=float(aporte_base))
    risco = st.sidebar.slider("Fator de Agressividade", 0.5, 1.5, 1.0)

    # Cálculos
    df['Valor_Alvo'] = (df['Meta'] / 100) * (df['Valor_Atual'].sum() + novo_aporte)
    df['Sugestao'] = ((df['Valor_Alvo'] - df['Valor_Atual']) * risco).clip(lower=0)
    df['Final'] = (df['Sugestao'] / df['Sugestao'].sum()) * novo_aporte

    # Gráficos
    col1, col2 = st.columns(2)
    config = {"template": "plotly_dark", "font_color": "white", "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)"}
    
    with col1:
        fig1 = px.pie(df, values='Valor_Atual', names='Ativo', title="Carteira Atual").update_layout(**config).update_traces(textfont_color="white")
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = px.pie(df, values='Final', names='Ativo', title="Sugestão Aporte", hole=0.4).update_layout(**config).update_traces(textfont_color="white")
        st.plotly_chart(fig2, use_container_width=True)
    
    

    # --- NOVA LÓGICA DE REBALANCEAMENTO DIRETO ---
    st.subheader("🎯 Plano de Aporte Sugerido")
    st.write("Abaixo, o plano de ação para alinhar sua carteira à estratégia definida:")

    # Criar um DataFrame focado na ação
    df_acao = df[df['Final'] > 1.0].copy()
    df['Progresso'] = (df['Valor_Atual'] / (df['Valor_Alvo'] / (df['Meta']/100)) * 100).fillna(0)
    
    
    # Filtrar apenas ativos relevantes
    df_acao = df[df['Final'] > 1.0].copy()
    
    for _, row in df_acao.iterrows():
        # Lógica de cálculo de progresso
        progresso = min(row['Progresso'], 100)
        
        # Criação de um card moderno
        with st.container():
            col_a, col_b = st.columns([2, 1])
            
            with col_a:
                st.markdown(f"#### 💰 {row['Ativo']}")
                st.caption(f"Meta Alvo: {row['Meta']}%")
                    
                with col_b:
                    st.markdown(f"""
                <div style="text-align: right;">
                    <span style="color:#00ff00; font-size: 15px; font-weight: bold;">
                        R$ {row['Final']:.2f}
                    </span>
                </div>
            """, unsafe_allow_html=True)
                    
            # Barra de progresso nativa do Streamlit (Muito mais elegante que texto)
            st.progress(progresso / 100)
            
            # Texto explicativo minimalista
            st.write(f"*Insight: Reforço necessário para atingir {row['Meta']}% de alocação.*")
            st.divider()

    def exibir_painel_saude(df_acoes,df_fiis):
        # Definindo um estilo para diminuir o tamanho dos números do metric
        st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 18px !important; }
        </style>
        """, unsafe_allow_html=True)
        
        # Criamos dois expanders, um para cada classe
        for titulo, df in [("🏥 Saúde das Ações", df_acoes), ("🏠 Saúde dos FIIs", df_fiis)]:
            with st.expander(titulo):
                total_segmento = df['Valor_Atual'].sum()
                
                for _, row in df.iterrows():
                    # Lógica de status e cores
                    diff = row['Diferença']
                    if abs(diff) < 2:
                        status, cor = "🟢 OK", "#00FF00"
                    elif diff > 0:
                        status, cor = "🔴 Abaixo", "#FF4B4B"
                    else:
                        status, cor = "🟡 Acima", "#FFD700"
                        
                    valor_ideal = total_segmento * (row['Meta_Perc'] / 100)
                    progresso = min(row['Valor_Atual'] / valor_ideal, 1.0) if valor_ideal > 0 else 0
                    
                    # Card do segmento
                    st.markdown(f"**{row['Nome']}** <span style='color:{cor}'>({status})</span>", unsafe_allow_html=True)
                    st.progress(float(progresso))
                    
                    # Métricas menores
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Atual", f"R${row['Valor_Atual']:.2f}")
                    m2.metric("Meta", f"R${valor_ideal:.2f}")
                    m3.metric("Desvio", f"{diff:.1f}%")
                    
                    # Ação recomendada (só se precisar)
                    if status != "🟢 OK":
                        valor_ajuste = abs(row['Valor_Atual'] - valor_ideal)
                        acao = "Aportar" if status == "🔴 Abaixo" else "Rebalancear"
                        st.caption(f"💡 Sugestão: {acao} R${valor_ajuste:.2f}")
                    
                    st.divider()

        # Chamada no App
    exibir_painel_saude(df_acoes, df_fiis)
    
    @st.cache_data(ttl=600) # Reduzi o cache para 10 minutos para garantir atualização rápida
    def buscar_noticias_financeiras():
        feed = feedparser.parse("https://www.infomoney.com.br/feed/")
        noticias = []
        
        for entry in feed.entries[:5]:
            # Extrai apenas o texto limpo da descrição (remove HTML)
            soup = BeautifulSoup(entry.description, "html.parser")
            texto_limpo = soup.get_text(separator=' ', strip=True)
            
            # Remove a parte final padrão do WordPress "The post ... appeared first on ..."
            if "The post" in texto_limpo:
                texto_limpo = texto_limpo.split("The post")[0].strip()
                
            noticias.append({
                'title': entry.title,
                'href': entry.link,
                'body': texto_limpo
            })
            return noticias
    st.subheader("🚀 Destaques do Mercado")
    noticias = buscar_noticias_financeiras()
    if noticias:
        for n in noticias:
            with st.expander("Ver Notícias Financeiras (Clique para ocultar)", expanded=True):
                
                if noticias:
                    for n in noticias:
                        st.markdown(f"**{n['title']}**")
                    st.link_button("Ler", n['href'])
        else:
            st.write("Sem notícias no momento.")
else:
    st.error("Erro ao carregar dados.")