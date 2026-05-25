import streamlit as st
import pandas as pd
import plotly.express as px
from duckduckgo_search import DDGS

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
        idx_start = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains('Classe', case=False).any(), axis=1)].index[0] + 1
        idx_end = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains('Cofrinho', case=False).any(), axis=1)].index[0]
        
        df = df_raw.iloc[idx_start:idx_end, [0, 1, 3]].copy()
        df.columns = ['Ativo', 'Valor_Atual', 'Meta']
        df['Valor_Atual'] = pd.to_numeric(df['Valor_Atual'].str.replace(',', '.'), errors='coerce')
        df['Meta'] = pd.to_numeric(df['Meta'].str.replace('%', '').str.replace(',', '.'), errors='coerce')
        
        aporte_idx = df_raw[df_raw.apply(lambda row: row.astype(str).str.contains('Aporte Mensal', case=False).any(), axis=1)].index[0]
        aporte = float(df_raw.iloc[aporte_idx, 1].replace(',', '.'))
        return df.dropna(), aporte
    except:
        return pd.DataFrame(), 0

# --- INTERFACE ---
st.title("⚖️ Smart Balance Pro")
df, aporte_base = carregar_dados()

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

    st.subheader("🚀 Destaques: InfoMoney & Status Invest")
    
    @st.cache_data(ttl=600) # Reduzi o cache para 10 minutos para garantir atualização rápida
    def buscar_noticias_financeiras():
        try:
         with DDGS() as ddgs:
            # Query mais ampla para garantir resultados
            query = "mercado financeiro ações dividendos FIIs"
            # Buscamos mais resultados para filtrar apenas os que vêm dos domínios desejados
            resultados = list(ddgs.text(query, max_results=10))
            
            # Filtro inteligente: garante que apenas links dos sites escolhidos passem
            filtrados = [n for n in resultados if "infomoney.com.br" in n['href'] or "statusinvest.com.br" in n['href']]
            
            # Se não achar nada específico nos sites, retorna os 3 mais relevantes gerais
            return filtrados[:5] if filtrados else resultados[:3]
        except:
            return []
else:
    st.error("Erro ao carregar dados.")