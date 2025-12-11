import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import io

#Configuração da Página
st.set_page_config(page_title="Controle de Frota & Equipamentos", layout="wide")

# --- LISTAS DE DADOS (CONFIGURAÇÃO) ---
CIDADES = [
    "Água Clara", "Bataguassu", "Nova Porto XV", "Brasilândia", "Debrasa",
    "Novo Porto João André", "Ribas do Rio Pardo", "Santa Rita do Pardo",
    "Selvíria", "Três Lagoas", "Arapuá"
]

CATEGORIAS = [
    "Veículo Leve", "Caminhão", "Roçadeira", "Bomba Seca Vala",
    "Compactador de Solo", "Placa Vibratória", "Soprador", "Cortadora de Piso"
]

# --- SIMULAÇÃO DE BANCO DE DADOS (SESSION STATE) ---
# Em produção, você substituiria isso pela conexão com Google Sheets
if 'dados_frota' not in st.session_state:
    # Criando alguns dados fictícios para exemplo
    data = {
        'ID': [101, 102, 103],
        'Tipo': ['Roçadeira', 'Caminhão', 'Bomba Seca Vala'],
        'Modelo': ['Stihl FS 220', 'VW Constellation', 'Honda WB30'],
        'Cidade': ['Três Lagoas', 'Brasilândia', 'Água Clara'],
        'Horimetro_KM_Atual': [150, 50000, 40],
        'Ultima_Revisao': ['2023-10-01', '2023-09-15', '2023-11-01'],
        'Proxima_Revisao_Sugerida': [200, 60000, 100], # Em horas ou KM
        'Status': ['Operacional', 'Em Manutenção', 'Operacional']
    }
    st.session_state['dados_frota'] = pd.DataFrame(data)

# --- SISTEMA DE LOGIN SIMPLES ---
def check_password():
    """Retorna o usuário e cargo se o login for sucesso"""
    st.sidebar.title("🔐 Login do Sistema")
    usuario = st.sidebar.text_input("Usuário")
    senha = st.sidebar.text_input("Senha", type="password")
    
    if st.sidebar.button("Entrar"):
        # USERS HARDCODED PARA EXEMPLO (No real use um banco seguro)
        if usuario == "adm" and senha == "adm123":
            st.session_state['user'] = {"role": "ADM", "city": "Global", "name": "Administrador Geral"}
        elif usuario == "super_tl" and senha == "123":
            st.session_state['user'] = {"role": "Supervisão", "city": "Três Lagoas", "name": "Supervisor TL"}
        elif usuario == "op_geral" and senha == "123":
            st.session_state['user'] = {"role": "Operação", "city": "Global", "name": "Operador"}
        else:
            st.sidebar.error("Senha incorreta")

if 'user' not in st.session_state:
    check_password()
    st.stop() # Para a execução se não estiver logado

# Recupera dados do usuário logado
user_role = st.session_state['user']['role']
user_city = st.session_state['user']['city']
st.sidebar.success(f"Logado como: {user_role} ({user_city})")

if st.sidebar.button("Sair"):
    del st.session_state['user']
    st.rerun()

# --- LÓGICA DE DADOS ---
df = st.session_state['dados_frota']

# Filtragem de segurança baseada no cargo
if user_role == "Supervisão":
    df_visible = df[df['Cidade'] == user_city]
else:
    df_visible = df # ADM e Operação veem tudo (Operação só insere, mas pode ver lista simples)

# --- INTERFACE PRINCIPAL ---

st.title("🚜 Gestão de Frota e Equipamentos")
st.markdown("---")

# ABA DE OPERAÇÃO (INSERIR DADOS)
if user_role in ["ADM", "Supervisão", "Operação"]:
    with st.expander("📝 Nova Entrada / Cadastro (Disponível para Operação)", expanded=(user_role=="Operação")):
        c1, c2, c3 = st.columns(3)
        with c1:
            novo_tipo = st.selectbox("Equipamento/Veículo", CATEGORIAS)
            novo_modelo = st.text_input("Modelo/Placa")
        with c2:
            nova_cidade = st.selectbox("Cidade", [user_city] if user_role == "Supervisão" else CIDADES)
            novo_km = st.number_input("Horímetro ou KM Atual", min_value=0)
        with c3:
            nova_revisao = st.date_input("Data Última Revisão")
            novo_status = st.selectbox("Status", ["Operacional", "Em Manutenção", "Baixado"])
        
        if st.button("Salvar Registro"):
            novo_id = df['ID'].max() + 1 if not df.empty else 1
            novo_dado = {
                'ID': novo_id,
                'Tipo': novo_tipo,
                'Modelo': novo_modelo,
                'Cidade': nova_cidade,
                'Horimetro_KM_Atual': novo_km,
                'Ultima_Revisao': str(nova_revisao),
                'Proxima_Revisao_Sugerida': novo_km + 1000 if novo_tipo == "Caminhão" else novo_km + 50, # Lógica simples de alerta
                'Status': novo_status
            }
            st.session_state['dados_frota'] = pd.concat([df, pd.DataFrame([novo_dado])], ignore_index=True)
            st.success("Equipamento adicionado com sucesso!")
            st.rerun()

# --- ÁREA ADMINISTRATIVA E SUPERVISÃO (RELATÓRIOS) ---
if user_role in ["ADM", "Supervisão"]:
    st.subheader(f"📊 Painel de Controle - Visão: {user_city if user_role == 'Supervisão' else 'Global'}")
    
    # KPIs
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Ativos", len(df_visible))
    kpi2.metric("Em Manutenção", len(df_visible[df_visible['Status'] == 'Em Manutenção']))
    
    # Alerta de Revisão (Lógica: se atual >= proxima sugerida)
    manutencao_critica = df_visible[df_visible['Horimetro_KM_Atual'] >= df_visible['Proxima_Revisao_Sugerida']]
    kpi3.metric("⚠️ Alerta Revisão", len(manutencao_critica))

    if not manutencao_critica.empty:
        st.error(f"Atenção: {len(manutencao_critica)} equipamentos precisam de revisão urgente!")
        st.dataframe(manutencao_critica[['Cidade', 'Tipo', 'Modelo', 'Horimetro_KM_Atual', 'Proxima_Revisao_Sugerida']])

    # Gráficos
    g1, g2 = st.columns(2)
    with g1:
        fig_status = px.pie(df_visible, names='Status', title='Distribuição por Status')
        st.plotly_chart(fig_status, use_container_width=True)
    
    with g2:
        # Se for ADM mostra por cidade, se for Supervisor mostra por Tipo
        if user_role == "ADM":
            fig_bar = px.bar(df_visible, x='Cidade', color='Status', title='Equipamentos por Cidade')
        else:
            fig_bar = px.bar(df_visible, x='Tipo', color='Status', title='Meus Equipamentos por Tipo')
        st.plotly_chart(fig_bar, use_container_width=True)

    # Tabela Completa e Exportação
    st.markdown("### 📋 Inventário Completo")
    st.dataframe(df_visible, use_container_width=True)
    
    # Botão de Exportar para Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_visible.to_excel(writer, sheet_name='Frota', index=False)
    
    st.download_button(
        label="📥 Baixar Relatório em Excel",
        data=buffer,
        file_name="relatorio_frota.xlsx",
        mime="application/vnd.ms-excel"
    )

elif user_role == "Operação":
    st.info("Perfil de Operação: Acesso restrito apenas ao cadastro de informações.")
