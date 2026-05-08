import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import database as db

st.set_page_config(
    page_title="Finanças Pessoais",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #0a0a0a;
        border-right: 1px solid rgba(255,255,255,0.06);
    }

    /* ── Metric cards ── */
    div[data-testid="metric-container"] {
        background: #16181a;
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 20px;
        padding: 20px 24px;
        transition: border-color 0.18s ease;
    }
    div[data-testid="metric-container"]:hover {
        border-color: rgba(255,255,255,0.24);
    }
    div[data-testid="metric-container"] label {
        color: rgba(255,255,255,0.6) !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        letter-spacing: 0.6px !important;
        text-transform: uppercase !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 600 !important;
        letter-spacing: -0.4px !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-size: 13px !important;
    }

    /* ── Tabs — pill nav ── */
    .stTabs [data-baseweb="tab-list"] {
        background: #16181a;
        border-radius: 9999px;
        padding: 4px 6px;
        gap: 2px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9999px;
        padding: 8px 20px;
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 0.2px;
        color: rgba(255,255,255,0.55);
        transition: color 0.15s ease;
    }
    .stTabs [aria-selected="true"] {
        background: #494fdf !important;
        color: #ffffff !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }

    /* ── Buttons — pill shape ── */
    .stButton > button {
        border-radius: 9999px !important;
        font-weight: 600 !important;
        letter-spacing: 0.2px !important;
        transition: opacity 0.15s ease !important;
    }
    .stButton > button:hover { opacity: 0.88 !important; }
    .stButton > button[kind="primary"] {
        background: #494fdf !important;
        border: none !important;
        color: #ffffff !important;
    }
    .stButton > button[kind="secondary"] {
        border: 1px solid rgba(255,255,255,0.18) !important;
    }

    /* ── Expanders ── */
    [data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 16px !important;
        background: #16181a !important;
    }

    /* ── Dividers ── */
    hr {
        border-color: rgba(255,255,255,0.06) !important;
        margin: 1.2rem 0 !important;
    }

    /* ── Progress bars ── */
    [data-testid="stProgressBar"] > div > div {
        border-radius: 9999px;
    }
    [data-testid="stProgressBar"] > div {
        border-radius: 9999px;
        background: rgba(255,255,255,0.08);
    }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {
        border-radius: 16px !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        background: #16181a !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────── CATEGORIAS ───────────────────

CATEGORIAS_LISTA = [
    "Alimentação",
    "Transporte",
    "Saúde",
    "Educação",
    "Esporte",
    "Assinaturas",
    "Investimentos",
    "Fatura Cartão",
    "Lazer",
    "Receita",
    "Estorno",
    "Outros",
]

CORES = {
    "Alimentação":   "#e61e49",   # accent-pink
    "Transporte":    "#007bc2",   # accent-light-blue
    "Saúde":         "#494fdf",   # primary cobalt
    "Educação":      "#376cd5",   # accent-blue-link
    "Esporte":       "#00a87e",   # accent-teal
    "Assinaturas":   "#b09000",   # accent-yellow
    "Investimentos": "#00a87e",   # accent-teal — crescimento
    "Fatura Cartão": "#ec7e00",   # accent-warning
    "Lazer":         "#e61e49",   # accent-pink
    "Receita":       "#428619",   # accent-light-green
    "Estorno":       "#5c5e60",   # ash
    "Outros":        "#505a63",   # mute
}

# Regras em ordem de prioridade — mais específicas primeiro
REGRAS_BUILTIN: list[tuple[str, list[str]]] = [
    ("Estorno",        ["estorno"]),
    ("Receita",        ["transferência recebida", "transferencia recebida"]),
    ("Investimentos",  ["aplicação rdb", "aplicacao rdb", "resgate rdb", "nomad fintech"]),
    ("Fatura Cartão",  ["pagamento de fatura"]),
    ("Transporte",     ["99 tecnologia", "uber do brasil", "uber eats", "combustiv", "gasolina", "posto "]),
    ("Alimentação",    ["zaffari", "big bem", "padaria", "mercado", "supermercado",
                        "restaurante", "restaurant", "sorveteria", "expresso do xis",
                        "ponto certo", "carrefour", "walmart", "atacadao", "ifood", "rappi"]),
    ("Saúde",          ["psicolog", "plinio vieira", "farmacia", "drogaria",
                        "consulta", "clinica", "medic", "odonto", "hospital", "unimed"]),
    ("Educação",       ["universidade federal", "ufrgs", "senac", "curso", "escola", "faculdade"]),
    ("Esporte",        ["sesc", "academia", "gym ", "fitness", "natacao", "crossfit", "smartfit"]),
    ("Assinaturas",    ["netflix", "spotify", "youtube", "prime video", "disney",
                        "apple ", "google one", "microsoft", "adobe", "hbo"]),
    ("Lazer",          ["cinema", "show", "teatro", "ingresso", "balada"]),
]

# Categorias excluídas da análise de gastos reais
NAO_SAO_GASTOS = {"Receita", "Estorno", "Investimentos", "Fatura Cartão"}


def categorizar(descricao: str, regras_custom: dict[str, str] | None = None) -> str:
    desc = descricao.lower()
    if regras_custom:
        for padrao, cat in regras_custom.items():
            if padrao in desc:
                return cat
    for cat, palavras in REGRAS_BUILTIN:
        if any(p in desc for p in palavras):
            return cat
    return "Outros"


def processar_csv(arquivo, regras_custom: dict[str, str] | None = None) -> pd.DataFrame:
    df = pd.read_csv(arquivo, encoding="utf-8")
    df.columns = ["data", "valor", "identificador", "descricao"]
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["categoria"] = df["descricao"].apply(lambda d: categorizar(d, regras_custom))
    return df


def fmt_brl(valor: float) -> str:
    formatted = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def fmt_mes(mes_ano: str) -> str:
    ano, mes = mes_ano.split("-")
    nomes = {
        "01": "Janeiro", "02": "Fevereiro", "03": "Março",
        "04": "Abril",   "05": "Maio",      "06": "Junho",
        "07": "Julho",   "08": "Agosto",    "09": "Setembro",
        "10": "Outubro", "11": "Novembro",  "12": "Dezembro",
    }
    return f"{nomes[mes]} {ano}"


# Categorias que fazem sentido ter meta (gastos reais do dia-a-dia)
CATEGORIAS_META = [
    c for c in CATEGORIAS_LISTA
    if c not in {"Receita", "Estorno", "Investimentos", "Fatura Cartão"}
]

# Agrupamentos para regra 50/30/20
CATS_NECESSIDADES = {"Alimentação", "Transporte", "Saúde", "Educação", "Esporte"}
CATS_DESEJOS      = {"Lazer", "Assinaturas", "Outros"}
CATS_INVESTIMENTOS = {"Investimentos"}


def calcular_alertas(gastos_atual_df: pd.DataFrame, mes_atual: str) -> dict:
    """Retorna categorias com gasto acima de 20% da média dos meses anteriores."""
    todos_meses = db.get_meses_disponiveis()
    meses_anteriores = [m for m in todos_meses if m != mes_atual]

    if len(meses_anteriores) < 2:
        return {}

    historico = []
    for m in meses_anteriores:
        df_m = db.get_transacoes(m)
        if df_m.empty:
            continue
        g = df_m[(df_m["valor"] < 0) & (~df_m["categoria"].isin(NAO_SAO_GASTOS))]
        for cat, grp in g.groupby("categoria"):
            historico.append({"categoria": cat, "valor": abs(grp["valor"].sum())})

    if not historico:
        return {}

    media_por_cat = pd.DataFrame(historico).groupby("categoria")["valor"].mean()
    gastos_cat_atual = gastos_atual_df.groupby("categoria")["valor"].sum().abs()

    alertas = {}
    for cat, valor_atual in gastos_cat_atual.items():
        if cat in media_por_cat.index:
            media = media_por_cat[cat]
            if media > 0 and valor_atual > media * 1.2:
                alertas[cat] = {
                    "atual": valor_atual,
                    "media": media,
                    "pct_acima": ((valor_atual / media) - 1) * 100,
                }
    return alertas


# ─────────────────── INICIALIZAÇÃO ───────────────────

db.init_db()

# ─────────────────── SIDEBAR ───────────────────

with st.sidebar:
    st.markdown("## 💰 Finanças Pessoais")
    st.markdown("---")

    arquivo = st.file_uploader(
        "Importar extrato Nubank",
        type=["csv"],
        help="Exporte o extrato em CSV no app do Nubank: Perfil → Extratos → CSV",
    )

    if arquivo is not None:
        regras_atuais = db.get_regras()
        df_novo = processar_csv(arquivo, regras_atuais)
        inseridos, duplicatas = db.salvar_transacoes(df_novo)
        if inseridos > 0:
            st.success(f"✅ {inseridos} transações importadas!")
        if duplicatas > 0:
            st.info(f"ℹ️ {duplicatas} já existiam no banco")
        if inseridos == 0 and duplicatas == 0:
            st.warning("Nenhuma transação encontrada no arquivo.")

    st.markdown("---")

    meses = db.get_meses_disponiveis()

    if not meses:
        st.warning("Nenhum dado ainda.\nFaça o upload de um extrato acima.")
        st.stop()

    mes_sel = st.selectbox("Mês", meses, format_func=fmt_mes)
    st.caption(f"Total de meses importados: **{len(meses)}**")

    # ── Bloco de Notas ──
    st.markdown("---")
    st.markdown("##### 📝 Anotações")
    notas_salvas_sb = db.get_config("notas_planejamento", "")
    notas_input_sb = st.text_area(
        "notas",
        value=notas_salvas_sb,
        height=180,
        placeholder="Metas, lembretes, ideias...",
        label_visibility="collapsed",
        key="notas_sidebar",
    )
    if st.button("💾 Salvar", key="btn_notas_sb"):
        db.set_config("notas_planejamento", notas_input_sb)
        st.success("Salvo!")

# ─────────────────── DADOS DO MÊS ───────────────────

df = db.get_transacoes(mes_sel)

if df.empty:
    st.warning("Sem transações para o mês selecionado.")
    st.stop()

gastos_df = df[(df["valor"] < 0) & (~df["categoria"].isin(NAO_SAO_GASTOS))]

# Totais brutos — batem com o PDF do Nubank
total_entradas = df[df["valor"] > 0]["valor"].sum()
total_saidas   = df[df["valor"] < 0]["valor"].abs().sum()
saldo_mes      = df["valor"].sum()

# Detalhamento
total_gastos_reais = gastos_df["valor"].abs().sum()
invest_aplicado    = df[(df["categoria"] == "Investimentos") & (df["valor"] < 0)]["valor"].abs().sum()
invest_resgatado   = df[(df["categoria"] == "Investimentos") & (df["valor"] > 0)]["valor"].sum()
invest_liquido     = invest_aplicado - invest_resgatado
fatura_paga        = df[df["categoria"] == "Fatura Cartão"]["valor"].abs().sum()

# ─────────────────── TABS ───────────────────

tab_resumo, tab_transacoes, tab_plan, tab_ia, tab_historico = st.tabs(
    ["📊 Resumo", "📋 Transações", "💡 Planejamento", "🤖 IA", "📈 Histórico"]
)

# ═══════════════════════════════════════════
#  TAB 1 — RESUMO
# ═══════════════════════════════════════════

with tab_resumo:
    st.markdown(f"### {fmt_mes(mes_sel)}")

    # Linha 1 — bate exatamente com o PDF do Nubank
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💚 Entradas", fmt_brl(total_entradas))
    with col2:
        st.metric("🔴 Saídas", fmt_brl(total_saidas))
    with col3:
        sinal = "+" if saldo_mes >= 0 else ""
        st.metric("💰 Saldo do Mês", f"{sinal}{fmt_brl(saldo_mes)}")

    # Linha 2 — detalhamento das saídas
    st.markdown("**Detalhamento das saídas:**")
    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("🛒 Gastos do dia-a-dia", fmt_brl(total_gastos_reais),
                  help="Exclui investimentos e fatura do cartão")
    with col5:
        st.metric("📈 Investido (líquido)", fmt_brl(invest_liquido),
                  help=f"Aplicado: {fmt_brl(invest_aplicado)} | Resgatado: {fmt_brl(invest_resgatado)}")
    with col6:
        st.metric("💳 Fatura paga", fmt_brl(fatura_paga),
                  help="Pagamento da fatura do cartão de crédito")

    # ── Alertas de gasto alto ──
    alertas = calcular_alertas(gastos_df, mes_sel)
    if alertas:
        st.markdown("---")
        st.markdown("#### 🚨 Alertas")
        for cat, info in alertas.items():
            st.warning(
                f"**{cat}**: {fmt_brl(info['atual'])} gastos — "
                f"**{info['pct_acima']:.0f}% acima** da sua média histórica ({fmt_brl(info['media'])})"
            )

    st.markdown("---")

    # ── Top 5 + Metas ──
    col_top5, col_metas = st.columns(2)

    with col_top5:
        st.markdown("#### 🔝 Top 5 Maiores Gastos")
        if not gastos_df.empty:
            top5 = gastos_df.nsmallest(5, "valor")[
                ["data", "descricao", "categoria", "valor"]
            ].copy()
            top5["data"] = top5["data"].dt.strftime("%d/%m")
            top5["valor"] = top5["valor"].abs().apply(fmt_brl)
            st.dataframe(
                top5.rename(columns={
                    "data": "Data", "descricao": "Descrição",
                    "categoria": "Categoria", "valor": "Valor",
                }),
                hide_index=True,
                use_container_width=True,
            )

    with col_metas:
        st.markdown("#### 🎯 Metas do Mês")
        metas = db.get_metas()
        if metas:
            gastos_por_cat = gastos_df.groupby("categoria")["valor"].sum().abs()
            for cat, limite in sorted(metas.items()):
                gasto = gastos_por_cat.get(cat, 0.0)
                pct = gasto / limite
                pct_bar = min(pct, 1.0)
                icon = "🟢" if pct < 0.75 else ("🟡" if pct < 1.0 else "🔴")
                st.markdown(
                    f"{icon} **{cat}** — {fmt_brl(gasto)} / {fmt_brl(limite)} "
                    f"({pct * 100:.0f}%)"
                )
                st.progress(pct_bar)
        else:
            st.caption("Nenhuma meta definida ainda.")
            st.caption("Configure em 💡 Planejamento →")

    st.markdown("---")

    # ── Gráficos linha 1: pizza + barras por dia ──
    col_pizza, col_diario = st.columns(2)

    with col_pizza:
        if not gastos_df.empty:
            gastos_cat = (
                gastos_df.groupby("categoria")["valor"]
                .sum()
                .abs()
                .reset_index()
                .sort_values("valor", ascending=False)
            )
            fig_pizza = px.pie(
                gastos_cat,
                values="valor",
                names="categoria",
                title="Gastos por Categoria",
                color="categoria",
                color_discrete_map=CORES,
                hole=0.4,
            )
            fig_pizza.update_traces(
                textposition="inside",
                textinfo="percent+label",
                textfont_size=11,
            )
            fig_pizza.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.info("Sem gastos registrados neste mês.")

    with col_diario:
        gastos_dia = (
            gastos_df.groupby(gastos_df["data"].dt.day)["valor"]
            .sum()
            .abs()
        )
        fig_bar = go.Figure(
            go.Bar(
                x=gastos_dia.index,
                y=gastos_dia.values,
                marker_color="#FF6B6B",
                hovertemplate="Dia %{x}: R$ %{y:,.2f}<extra></extra>",
            )
        )
        fig_bar.update_layout(
            title="Gastos por Dia",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis=dict(title="Dia", gridcolor="rgba(255,255,255,0.08)"),
            yaxis=dict(title="R$", gridcolor="rgba(255,255,255,0.08)"),
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── Saldo acumulado ──
    df_sorted = df.sort_values(["data", "id"]).copy()
    df_sorted["saldo_acum"] = df_sorted["valor"].cumsum()

    fig_linha = go.Figure()
    fig_linha.add_trace(
        go.Scatter(
            x=df_sorted["data"],
            y=df_sorted["saldo_acum"],
            mode="lines+markers",
            line=dict(color="#4ECDC4", width=2),
            fill="tozeroy",
            fillcolor="rgba(78,205,196,0.1)",
            hovertemplate="%{x|%d/%m}: R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig_linha.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.25)")
    fig_linha.update_layout(
        title="Saldo Acumulado no Mês",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        yaxis=dict(title="R$", gridcolor="rgba(255,255,255,0.08)"),
        showlegend=False,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_linha, use_container_width=True)

    # ── Movimentações de investimento ──
    invest_df = df[df["categoria"] == "Investimentos"].copy()
    if not invest_df.empty:
        st.markdown("---")
        st.markdown("#### 📈 Investimentos no Mês")
        col_inv1, col_inv2 = st.columns([2, 1])

        with col_inv1:
            inv_exibir = invest_df[["data", "descricao", "valor"]].copy()
            inv_exibir["data"] = inv_exibir["data"].dt.strftime("%d/%m/%Y")
            inv_exibir["valor_fmt"] = inv_exibir["valor"].apply(
                lambda v: f"{'▲' if v > 0 else '▼'} {fmt_brl(v)}"
            )
            st.dataframe(
                inv_exibir[["data", "descricao", "valor_fmt"]].rename(
                    columns={"data": "Data", "descricao": "Descrição", "valor_fmt": "Valor"}
                ),
                hide_index=True,
                use_container_width=True,
            )

        with col_inv2:
            st.metric("Aplicado", fmt_brl(invest_aplicado))
            st.metric("Resgatado", fmt_brl(invest_resgatado))
            st.metric("Líquido investido", fmt_brl(invest_liquido))

# ═══════════════════════════════════════════
#  TAB 2 — TRANSAÇÕES
# ═══════════════════════════════════════════

with tab_transacoes:
    st.markdown("### Transações")

    col_busca, col_cat_filter = st.columns([2, 1])
    with col_busca:
        busca = st.text_input("🔍 Buscar na descrição", placeholder="Ex: Zaffari, Uber...")
    with col_cat_filter:
        cat_filtro = st.multiselect("Filtrar por categoria", options=CATEGORIAS_LISTA)

    df_exibir = df.copy()
    if busca:
        df_exibir = df_exibir[
            df_exibir["descricao"].str.contains(busca, case=False, na=False)
        ]
    if cat_filtro:
        df_exibir = df_exibir[df_exibir["categoria"].isin(cat_filtro)]

    df_exibir = df_exibir.sort_values("data")
    df_exibir["data_fmt"] = df_exibir["data"].dt.strftime("%d/%m/%Y")
    df_exibir["valor_fmt"] = df_exibir["valor"].apply(
        lambda v: f"{'▲' if v > 0 else '▼'} {fmt_brl(v)}"
    )

    edited_df = st.data_editor(
        df_exibir[["id", "data_fmt", "valor_fmt", "descricao", "categoria"]],
        column_config={
            "id":        st.column_config.NumberColumn("ID",        disabled=True, width="small"),
            "data_fmt":  st.column_config.TextColumn("Data",       disabled=True, width="small"),
            "valor_fmt": st.column_config.TextColumn("Valor",      disabled=True, width="medium"),
            "descricao": st.column_config.TextColumn("Descrição",  disabled=True),
            "categoria": st.column_config.SelectboxColumn(
                "Categoria", options=CATEGORIAS_LISTA, width="medium"
            ),
        },
        hide_index=True,
        use_container_width=True,
        key="tabela_transacoes",
    )

    if st.button("💾 Salvar alterações", type="primary"):
        original_cats = dict(zip(df_exibir["id"], df_exibir["categoria"]))
        alteracoes = 0
        for _, row in edited_df.iterrows():
            id_ = int(row["id"])
            nova = row["categoria"]
            if original_cats.get(id_) != nova:
                db.update_categoria(id_, nova)
                alteracoes += 1
        if alteracoes:
            st.success(f"✅ {alteracoes} categoria(s) atualizada(s)!")
            st.rerun()
        else:
            st.info("Nenhuma alteração detectada.")

    # ── Exportar CSV ──
    csv_export = df_exibir[["data_fmt", "descricao", "valor", "categoria"]].copy()
    csv_export.columns = ["Data", "Descrição", "Valor", "Categoria"]
    st.download_button(
        label="⬇️ Exportar CSV com categorias",
        data=csv_export.to_csv(index=False).encode("utf-8"),
        file_name=f"financas_{mes_sel}.csv",
        mime="text/csv",
    )

    # ── Categorização com IA ──
    st.markdown("---")
    with st.expander("🤖 Categorizar 'Outros' com IA"):
        outros_df = df[df["categoria"] == "Outros"].copy()
        api_key_cat = db.get_config("ia_api_key", "")

        if outros_df.empty:
            st.success("Nenhuma transação em 'Outros' neste mês!")
        elif not api_key_cat:
            st.warning("Configure a API Key na aba 🤖 IA para usar esta função.")
        else:
            st.caption(f"{len(outros_df)} transação(ões) em 'Outros' neste mês.")

            if st.button("🔍 Analisar com IA", type="primary", key="btn_cat_ia"):
                # Monta lista com frequência
                freq = outros_df.groupby("descricao").agg(
                    vezes=("valor", "count"),
                    valor_medio=("valor", "mean")
                ).reset_index()

                lista_txt = "\n".join([
                    f'- ID_DESC "{row.descricao}" | R${abs(row.valor_medio):.2f} | '
                    f'{row.vezes}x no mês'
                    for _, row in freq.iterrows()
                ])

                prompt_cat = f"""Analise estas transações brasileiras na categoria "Outros" e sugira a categoria mais provável para cada uma.

Categorias disponíveis: Alimentação, Transporte, Saúde, Educação, Esporte, Assinaturas, Lazer, Outros

Retorne SOMENTE um JSON válido, sem texto adicional, no formato:
[{{"descricao": "...", "categoria": "...", "motivo": "..."}}]

Transações:
{lista_txt}"""

                try:
                    from groq import Groq
                    import json
                    client = Groq(api_key=api_key_cat)
                    with st.spinner("Analisando transações..."):
                        resp = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt_cat}],
                            max_tokens=1500,
                            temperature=0.1,
                        )
                    raw = resp.choices[0].message.content.strip()
                    # Extrai JSON mesmo se vier com texto em volta
                    inicio = raw.find("[")
                    fim    = raw.rfind("]") + 1
                    sugestoes = json.loads(raw[inicio:fim])
                    st.session_state["sugestoes_ia"] = sugestoes
                except Exception as e:
                    st.error(f"Erro: {e}")

            if "sugestoes_ia" in st.session_state and st.session_state["sugestoes_ia"]:
                sugestoes = st.session_state["sugestoes_ia"]
                st.markdown("**Sugestões da IA — revise e aplique:**")

                selecionadas = {}
                for i, s in enumerate(sugestoes):
                    desc  = s.get("descricao", "")
                    cat   = s.get("categoria", "Outros")
                    motivo = s.get("motivo", "")
                    col_d, col_c, col_m, col_chk = st.columns([3, 2, 3, 1])
                    col_d.markdown(f"`{desc[:45]}`")
                    nova_cat_sug = col_c.selectbox(
                        "", CATEGORIAS_LISTA,
                        index=CATEGORIAS_LISTA.index(cat) if cat in CATEGORIAS_LISTA else 0,
                        key=f"sug_{i}",
                        label_visibility="collapsed",
                    )
                    col_m.caption(motivo)
                    aplicar = col_chk.checkbox("", value=True, key=f"chk_{i}")
                    if aplicar:
                        selecionadas[desc] = nova_cat_sug

                col_aplicar, col_regra = st.columns(2)
                with col_aplicar:
                    if st.button("✅ Aplicar selecionadas", type="primary"):
                        atualizados = 0
                        for desc, cat_nova in selecionadas.items():
                            ids = df[df["descricao"] == desc]["id"].tolist()
                            for id_ in ids:
                                db.update_categoria(id_, cat_nova)
                                atualizados += 1
                        st.success(f"{atualizados} transação(ões) atualizadas!")
                        del st.session_state["sugestoes_ia"]
                        st.rerun()
                with col_regra:
                    if st.button("✅ Aplicar + salvar como regras"):
                        atualizados = 0
                        for desc, cat_nova in selecionadas.items():
                            ids = df[df["descricao"] == desc]["id"].tolist()
                            for id_ in ids:
                                db.update_categoria(id_, cat_nova)
                                atualizados += 1
                            # Salva a palavra-chave mais curta identificável
                            palavras = desc.lower().split(" - ")
                            chave = palavras[-1].strip()[:30] if len(palavras) > 1 else desc.lower()[:30]
                            db.salvar_regra(chave, cat_nova)
                        st.success(f"{atualizados} transações atualizadas e regras salvas!")
                        del st.session_state["sugestoes_ia"]
                        st.rerun()

    # ── Regras personalizadas ──
    st.markdown("---")
    with st.expander("⚙️ Regras de Categorização Automática"):
        st.caption(
            "Palavras-chave que serão aplicadas automaticamente em novos uploads. "
            "Têm prioridade sobre as regras padrão."
        )

        col_p, col_c, col_btn = st.columns([2, 1, 1])
        with col_p:
            novo_padrao = st.text_input("Palavra-chave", key="novo_padrao",
                                        placeholder="Ex: carlosalberto")
        with col_c:
            nova_cat = st.selectbox("Categoria", CATEGORIAS_LISTA, key="nova_cat")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Adicionar") and novo_padrao.strip():
                db.salvar_regra(novo_padrao.strip(), nova_cat)
                st.success(f"Regra salva: '{novo_padrao}' → {nova_cat}")
                st.rerun()

        regras = db.get_regras()
        if regras:
            st.markdown("**Regras ativas:**")
            for padrao, cat in regras.items():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.code(padrao)
                c2.write(cat)
                if c3.button("🗑️", key=f"del_{padrao}"):
                    db.deletar_regra(padrao)
                    st.rerun()

# ═══════════════════════════════════════════
#  TAB 3 — PLANEJAMENTO
# ═══════════════════════════════════════════

with tab_plan:
    st.markdown("### 💡 Planejamento Financeiro")

    # ── Configuração de salário ──
    salario_salvo  = db.get_config("salario_mensal")
    dias_u_salvo   = db.get_config("dias_uteis", "22")
    salario_atual  = float(salario_salvo) if salario_salvo else 0.0
    dias_uteis     = int(dias_u_salvo)

    tblm_mes = df[df["descricao"].str.contains("TBLM", case=False, na=False)]["valor"].sum()
    hint = f"TBLM neste mês: {fmt_brl(tblm_mes)}" if tblm_mes > 0 else "Informe sua renda mensal total"

    col_sal, col_dias, col_btn = st.columns([3, 1, 1])
    with col_sal:
        novo_salario = st.number_input(
            "Salário / renda mensal (R$)",
            min_value=0.0, value=salario_atual, step=100.0,
            help=hint,
        )
    with col_dias:
        novos_dias = st.number_input(
            "Dias úteis/mês", min_value=1, max_value=31,
            value=dias_uteis, help="Padrão: 22 dias",
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Salvar", type="primary", key="salvar_salario"):
            db.set_config("salario_mensal", str(novo_salario))
            db.set_config("dias_uteis", str(novos_dias))
            salario_atual = novo_salario
            dias_uteis    = novos_dias
            st.success("Salvo!")
            st.rerun()

    if salario_atual <= 0:
        st.info("Configure seu salário acima para ver as análises de planejamento.")
    else:
        valor_dia  = salario_atual / dias_uteis
        valor_hora = valor_dia / 8

        st.markdown("---")

        # ── Métricas como % da renda ──
        pct_gastos    = (total_gastos_reais / salario_atual) * 100
        pct_econ      = (max(saldo_mes, 0) / salario_atual) * 100
        pct_inv       = (invest_liquido / salario_atual) * 100 if invest_liquido > 0 else 0.0
        dias_p_gastos = total_gastos_reais / valor_dia

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("🛒 Gastos / renda",   f"{pct_gastos:.1f}%")
        col_b.metric("💰 Economizado",       f"{pct_econ:.1f}%")
        col_c.metric("📈 Investido",          f"{pct_inv:.1f}%")
        col_d.metric("⏰ Dias p/ pagar gastos", f"{dias_p_gastos:.1f} dias")

        st.markdown("---")

        # ── Regra 50/30/20 ──
        st.markdown("#### Regra 50 / 30 / 20")
        st.caption("Necessidades 50% · Desejos 30% · Investimentos 20% — valores ideais para saúde financeira")

        g_nec  = gastos_df[gastos_df["categoria"].isin(CATS_NECESSIDADES)]["valor"].abs().sum()
        g_des  = gastos_df[gastos_df["categoria"].isin(CATS_DESEJOS)]["valor"].abs().sum()
        g_inv  = invest_liquido

        pct_nec = (g_nec / salario_atual) * 100
        pct_des = (g_des / salario_atual) * 100
        pct_inv_r = (g_inv / salario_atual) * 100

        blocos = [
            ("🏠 Necessidades", pct_nec, 50, g_nec, "#45B7D1"),
            ("🎉 Desejos",      pct_des, 30, g_des, "#C3A6FF"),
            ("📈 Investimentos", pct_inv_r, 20, g_inv, "#66BB6A"),
        ]
        for label, pct_real, pct_ideal, valor, cor in blocos:
            diff = pct_real - pct_ideal
            sinal = f"+{diff:.1f}pp" if diff > 0 else f"{diff:.1f}pp"
            status = "🔴" if diff > 5 else ("🟡" if diff > 0 else "🟢")
            col_l, col_v, col_s = st.columns([3, 2, 1])
            col_l.markdown(f"**{label}** — ideal {pct_ideal}%")
            col_v.markdown(f"{fmt_brl(valor)} ({pct_real:.1f}%)")
            col_s.markdown(f"{status} {sinal}")
            st.progress(min(pct_real / 100, 1.0))

        fig_5030 = go.Figure()
        labels  = ["Necessidades", "Desejos", "Investimentos"]
        ideais  = [50, 30, 20]
        reais   = [pct_nec, pct_des, pct_inv_r]
        cores   = ["#45B7D1", "#C3A6FF", "#66BB6A"]
        fig_5030.add_trace(go.Bar(
            name="Ideal", x=labels, y=ideais,
            marker_color="rgba(255,255,255,0.12)",
            marker_line_color="rgba(255,255,255,0.3)", marker_line_width=1,
        ))
        fig_5030.add_trace(go.Bar(
            name="Atual", x=labels, y=reais,
            marker_color=[c if r <= i else "#FF6B6B" for c, r, i in zip(cores, reais, ideais)],
        ))
        fig_5030.update_layout(
            barmode="overlay", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", font_color="white",
            yaxis=dict(title="%", gridcolor="rgba(255,255,255,0.08)"),
            legend=dict(orientation="h", y=1.1),
            margin=dict(l=0, r=0, t=20, b=0), height=280,
        )
        st.plotly_chart(fig_5030, use_container_width=True)

        st.markdown("---")

        # ── Custo em dias de trabalho por categoria ──
        st.markdown("#### ⏰ Custo em Dias de Trabalho")
        if not gastos_df.empty:
            custo_cat = (
                gastos_df.groupby("categoria")["valor"].sum().abs()
                .reset_index()
                .sort_values("valor", ascending=False)
            )
            custo_cat["% Salário"]       = (custo_cat["valor"] / salario_atual * 100).round(1)
            custo_cat["Dias trabalhados"] = (custo_cat["valor"] / valor_dia).round(1)
            custo_cat["Horas trabalhadas"]= (custo_cat["valor"] / valor_hora).round(0).astype(int)
            custo_cat["Gasto"]           = custo_cat["valor"].apply(fmt_brl)
            st.dataframe(
                custo_cat[["categoria", "Gasto", "% Salário", "Dias trabalhados", "Horas trabalhadas"]]
                .rename(columns={"categoria": "Categoria"}),
                hide_index=True, use_container_width=True,
            )

        st.markdown("---")

        # ── Projeção anual ──
        st.markdown("#### 📅 Projeção")
        economia_mensal = max(saldo_mes, 0)
        col_p1, col_p2, col_p3 = st.columns(3)
        col_p1.metric("Economia projetada em 1 ano",  fmt_brl(economia_mensal * 12))
        col_p2.metric("Economia projetada em 2 anos", fmt_brl(economia_mensal * 24))
        col_p3.metric("Economia projetada em 5 anos", fmt_brl(economia_mensal * 60))

        if economia_mensal > 0:
            meses_range = list(range(1, 61))
            proj_vals   = [economia_mensal * m for m in meses_range]
            fig_proj = go.Figure(go.Scatter(
                x=meses_range, y=proj_vals,
                mode="lines", fill="tozeroy",
                line=dict(color="#66BB6A", width=2),
                fillcolor="rgba(102,187,106,0.1)",
                hovertemplate="Mês %{x}: R$ %{y:,.2f}<extra></extra>",
            ))
            fig_proj.update_layout(
                title="Acúmulo projetado (5 anos, sem juros)",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                xaxis=dict(title="Meses", gridcolor="rgba(255,255,255,0.08)"),
                yaxis=dict(title="R$",    gridcolor="rgba(255,255,255,0.08)"),
                margin=dict(l=0, r=0, t=40, b=0), showlegend=False,
            )
            st.plotly_chart(fig_proj, use_container_width=True)

        st.markdown("---")

        # ── Gerenciar Metas ──
        st.markdown("#### 🎯 Metas por Categoria")
        col_mc, col_mv, col_mb = st.columns([2, 2, 1])
        with col_mc:
            meta_cat = st.selectbox("Categoria", CATEGORIAS_META, key="meta_cat")
        with col_mv:
            metas_atuais = db.get_metas()
            meta_val = st.number_input(
                "Limite mensal (R$)", min_value=0.0,
                value=metas_atuais.get(meta_cat, 0.0),
                step=50.0, key="meta_val",
            )
        with col_mb:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Salvar meta", type="primary") and meta_val > 0:
                db.salvar_meta(meta_cat, meta_val)
                st.success("Meta salva!")
                st.rerun()

        if metas_atuais:
            for cat, limite in sorted(metas_atuais.items()):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"**{cat}**")
                c2.write(fmt_brl(limite) + " / mês")
                if c3.button("🗑️", key=f"del_meta_{cat}"):
                    db.deletar_meta(cat)
                    st.rerun()

# ═══════════════════════════════════════════
#  TAB 4 — IA
# ═══════════════════════════════════════════

with tab_ia:
    st.markdown("### 🤖 Assistente Financeiro IA")

    # ── Configuração ──
    with st.expander("⚙️ Configurar API"):
        st.markdown(
            "O assistente usa o **Groq** (gratuito, rápido). "
            "Crie conta em [console.groq.com](https://console.groq.com), gere uma API Key e cole abaixo."
        )
        provedores = ["Groq (grátis — recomendado)", "Google Gemini (grátis)", "OpenAI"]
        prov_salvo = db.get_config("ia_provedor", provedores[0])
        prov_idx   = provedores.index(prov_salvo) if prov_salvo in provedores else 0

        col_prov, col_key = st.columns([1, 2])
        with col_prov:
            provedor = st.selectbox("Provedor", provedores, index=prov_idx)
        with col_key:
            api_key = st.text_input(
                "API Key", value=db.get_config("ia_api_key", ""),
                type="password", placeholder="gsk_..."
            )
        if st.button("💾 Salvar configuração de IA"):
            db.set_config("ia_provedor", provedor)
            db.set_config("ia_api_key",  api_key)
            st.success("Configuração salva!")
            st.rerun()

        # Stats do histórico
        stats = db.get_stats_historico()
        if stats["total"] > 0:
            st.caption(
                f"Histórico: **{stats['total']}** mensagens ativas "
                f"(desde {stats['primeira'][:10] if stats['primeira'] else '—'}) · "
                f"{stats['arquivadas']} arquivadas"
            )

    api_key_ativa = db.get_config("ia_api_key", "")

    # ── Contexto financeiro ──
    def montar_contexto() -> str:
        linhas = [
            f"Mês analisado: {fmt_mes(mes_sel)}",
            f"Entradas: {fmt_brl(total_entradas)}",
            f"Saídas totais: {fmt_brl(total_saidas)}",
            f"Gastos do dia-a-dia: {fmt_brl(total_gastos_reais)}",
            f"Investido (líquido): {fmt_brl(invest_liquido)}",
            f"Saldo do mês: {fmt_brl(saldo_mes)}",
            "", "Gastos por categoria:",
        ]
        if not gastos_df.empty:
            for cat, val in gastos_df.groupby("categoria")["valor"].sum().abs().sort_values(ascending=False).items():
                linhas.append(f"  - {cat}: {fmt_brl(val)}")
        sal = db.get_config("salario_mensal")
        if sal:
            linhas += ["", f"Salário mensal: {fmt_brl(float(sal))}"]
        metas = db.get_metas()
        if metas:
            linhas.append("\nMetas:")
            for cat, lim in metas.items():
                gasto = gastos_df[gastos_df["categoria"] == cat]["valor"].abs().sum()
                linhas.append(f"  - {cat}: {fmt_brl(gasto)} / {fmt_brl(lim)}")
        return "\n".join(linhas)

    # ── Perguntas rápidas ──
    st.markdown("**Perguntas rápidas:**")
    perguntas_rapidas = [
        "Onde estou gastando mais este mês?",
        "Estou dentro da regra 50/30/20?",
        "Qual categoria devo cortar para economizar mais?",
        "Como posso reduzir meus gastos em R$200?",
        "Estou indo bem financeiramente?",
        "Que metas de gasto você me recomenda?",
    ]
    cols_p = st.columns(3)
    pergunta_selecionada = None
    for i, p in enumerate(perguntas_rapidas):
        if cols_p[i % 3].button(p, key=f"pq_{i}", use_container_width=True):
            pergunta_selecionada = p

    st.markdown("---")

    # ── Histórico persistido ──
    historico_db = db.get_historico(limite=60)  # exibe últimas 60 mensagens
    for msg in historico_db:
        with st.chat_message(msg["role"]):
            st.caption(msg["data"])
            st.markdown(msg["conteudo"])

    # ── Input ──
    prompt_input = st.chat_input("Pergunte sobre seus gastos...")
    prompt = pergunta_selecionada or prompt_input

    if prompt:
        db.salvar_mensagem("user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if not api_key_ativa:
                resposta = (
                    "Configure sua API Key no painel **⚙️ Configurar API** acima para "
                    "ativar o assistente. O Groq é gratuito e leva menos de 2 minutos pra configurar."
                )
                st.markdown(resposta)
            else:
                contexto = montar_contexto()
                # Injeta histórico recente no prompt (últimas 40 msgs = 20 trocas)
                historico_contexto = db.get_historico(limite=40)
                msgs_api = [
                    {
                        "role": "system",
                        "content": (
                            "Você é um assistente financeiro pessoal. Responda de forma direta e prática em português. "
                            "Use os dados financeiros abaixo para embasar suas respostas. "
                            "Quando o usuário mencionar algo de conversas anteriores, use o histórico fornecido.\n\n"
                            f"DADOS FINANCEIROS:\n{contexto}"
                        ),
                    }
                ]
                # Inclui histórico como mensagens reais (não só texto)
                for m in historico_contexto:
                    msgs_api.append({"role": m["role"], "content": m["conteudo"]})
                msgs_api.append({"role": "user", "content": prompt})

                try:
                    from groq import Groq
                    client = Groq(api_key=api_key_ativa)
                    with st.spinner("Pensando..."):
                        completion = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=msgs_api,
                            max_tokens=1024,
                        )
                    resposta = completion.choices[0].message.content
                except ImportError:
                    resposta = "⚠️ Instale a dependência: `pip install groq` e reinicie o app."
                except Exception as e:
                    resposta = f"⚠️ Erro: {e}"
                st.markdown(resposta)

        db.salvar_mensagem("assistant", resposta)
        st.rerun()

    # ── Controles do histórico ──
    if historico_db:
        col_arq, col_del = st.columns([1, 1])
        with col_arq:
            if st.button("📦 Arquivar conversa", help="Move para arquivo, não apaga"):
                db.arquivar_historico()
                st.success("Conversa arquivada! Novo chat iniciado.")
                st.rerun()
        with col_del:
            with st.expander("⚠️ Apagar histórico ativo"):
                st.caption("Isso remove permanentemente as mensagens ativas.")
                if st.button("🗑️ Confirmar exclusão", type="primary"):
                    conn_tmp = __import__("sqlite3").connect(str(db.DB_PATH))
                    conn_tmp.execute("DELETE FROM ia_historico WHERE arquivado = 0")
                    conn_tmp.commit()
                    conn_tmp.close()
                    st.success("Histórico apagado.")
                    st.rerun()

# ═══════════════════════════════════════════
#  TAB 5 — HISTÓRICO
# ═══════════════════════════════════════════

with tab_historico:
    st.markdown("### Histórico Mensal")

    todos_meses = db.get_meses_disponiveis()

    if len(todos_meses) < 2:
        st.info(
            "📅 Importe pelo menos **2 meses** de extratos para ver a comparação histórica.\n\n"
            f"Você tem **{len(todos_meses)}** mês importado até agora."
        )
    else:
        historico = []
        for m in todos_meses:
            df_m = db.get_transacoes(m)
            if df_m.empty:
                continue
            g = df_m[(df_m["valor"] < 0) & (~df_m["categoria"].isin(NAO_SAO_GASTOS))]
            r = df_m[(df_m["valor"] > 0) & (~df_m["categoria"].isin({"Estorno", "Investimentos"}))]
            historico.append({
                "mes":      m,
                "mes_fmt":  fmt_mes(m),
                "gastos":   abs(g["valor"].sum()),
                "receitas": r["valor"].sum(),
                "saldo":    r["valor"].sum() + g["valor"].sum(),
            })

        df_hist = pd.DataFrame(historico).sort_values("mes")

        # ── Barras comparativas ──
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Bar(
            x=df_hist["mes_fmt"], y=df_hist["receitas"],
            name="Receitas", marker_color="#26A69A",
        ))
        fig_hist.add_trace(go.Bar(
            x=df_hist["mes_fmt"], y=df_hist["gastos"],
            name="Gastos", marker_color="#FF6B6B",
        ))
        fig_hist.add_trace(go.Scatter(
            x=df_hist["mes_fmt"], y=df_hist["saldo"],
            name="Saldo", mode="lines+markers",
            line=dict(color="#FFEAA7", width=2),
        ))
        fig_hist.update_layout(
            title="Comparativo Mensal",
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            yaxis=dict(title="R$", gridcolor="rgba(255,255,255,0.08)"),
            legend=dict(orientation="h", y=1.12),
            margin=dict(l=0, r=0, t=60, b=0),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        # ── Gastos por categoria no histórico ──
        hist_cat = []
        for m in todos_meses:
            df_m = db.get_transacoes(m)
            if df_m.empty:
                continue
            g = df_m[(df_m["valor"] < 0) & (~df_m["categoria"].isin(NAO_SAO_GASTOS))]
            for cat, grp in g.groupby("categoria"):
                hist_cat.append({
                    "mes_fmt":  fmt_mes(m),
                    "mes":      m,
                    "categoria": cat,
                    "valor":    abs(grp["valor"].sum()),
                })

        if hist_cat:
            df_hist_cat = pd.DataFrame(hist_cat).sort_values("mes")
            fig_cat = px.bar(
                df_hist_cat,
                x="mes_fmt",
                y="valor",
                color="categoria",
                color_discrete_map=CORES,
                title="Gastos por Categoria (Histórico)",
                barmode="stack",
                labels={"mes_fmt": "Mês", "valor": "R$", "categoria": "Categoria"},
            )
            fig_cat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                yaxis=dict(title="R$", gridcolor="rgba(255,255,255,0.08)"),
                legend=dict(orientation="h", y=-0.25),
                margin=dict(l=0, r=0, t=40, b=80),
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        # ── Tabela resumo ──
        st.markdown("#### Resumo por Mês")
        df_resumo = df_hist[["mes_fmt", "receitas", "gastos", "saldo"]].copy()
        df_resumo.columns = ["Mês", "Entradas (R$)", "Gastos (R$)", "Saldo (R$)"]
        for col in ["Entradas (R$)", "Gastos (R$)", "Saldo (R$)"]:
            df_resumo[col] = df_resumo[col].apply(lambda v: fmt_brl(v))
        st.dataframe(df_resumo, hide_index=True, use_container_width=True)
