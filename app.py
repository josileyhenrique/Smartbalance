import streamlit as st
import pandas as pd
import plotly.express as px
from duckduckgo_search import DDGS

st.set_page_config(page_title="Rebalanceador Inteligente", layout="wide")

st.title("⚖️ Rebalanceador Automático")
st.write("Insira quanto você já tem em cada área e o seu aporte mensal. Eu calcularei a melhor distribuição para você.")

# 1. Inputs
with st.sidebar:
    st.header("Dados de Entrada")
    aporte_mensal = st.number_input("Quanto vai investir este mês? (R$)", value=1000.0)
    
    ativos = ['Ações Brasil', 'Ações EUA', 'Renda Fixa', 'FIIs']
    carteira_atual = {}
    for ativo in ativos:
        carteira_atual[ativo] = st.number_input(f"Quanto já tenho em {ativo} (R$):", value=0.0)

# 2. Lógica de Inteligência (Simulada via Notícias)
# Analisamos se o setor está em evidência (notícias positivas) para sugerir um peso maior
def obter_fator_mercado(ativo):
    try:
        with DDGS() as ddgs:
            noticias = list(ddgs.text(f"notícias cenário {ativo} Brasil", max_results=2))
            texto = " ".join([n['body'] for n in noticias]).lower()
            # Lógica simples de "sentimento": se aparecer 'alta', 'crescimento' ou 'oportunidade', peso aumenta
            if any(palavra in texto for palavra in ['alta', 'oportunidade', 'crescimento', 'lucro']):
                return 1.3 # Bônus de 30% no aporte para este setor
            return 1.0
    except:
        return 1.0

# 3. Cálculo
total_ja_investido = sum(carteira_atual.values())
if total_ja_investido == 0: total_ja_investido = 1 # Evitar divisão por zero

# Cálculo de peso: Prioriza o que está "menor" na carteira e o que as notícias indicam
df = pd.DataFrame(list(carteira_atual.items()), columns=['Ativo', 'Valor Atual'])
df['Peso Mercado'] = [obter_fator_mercado(a) for a in df['Ativo']]

# Lógica: Inversamente proporcional ao valor já investido (rebalanceamento) + Fator notícia
df['Score'] = (1 / (df['Valor Atual'] + 100)) * df['Peso Mercado']
total_score = df['Score'].sum()
df['Aporte Sugerido'] = (df['Score'] / total_score) * aporte_mensal

# 4. Exibição
col1, col2 = st.columns(2)

with col1:
    fig = px.pie(df, values='Aporte Sugerido', names='Ativo', title="Distribuição Sugerida do Aporte Mensal")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.write("### 📝 Justificativa do Rebalanceamento")
    for index, row in df.iterrows():
        st.write(f"- **{row['Ativo']}**: R$ {row['Aporte Sugerido']:.2f}")
    
    st.info("""
    **Por que este balanceamento?**
    O sistema priorizou ativos onde você tinha menos exposição e, ao mesmo tempo, 
    aplicou um peso maior em setores onde as notícias recentes indicam cenários favoráveis.
    """)