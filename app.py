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
    [data-testid="stSidebar"] {
        background-color: #0f0f23;
    }
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px 20px;
    }
    div[data-testid="metric-container"] label {
        color: #aaa !important;
        font-size: 13px !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 6px 18px;
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
    "Alimentação":   "#FF6B6B",
    "Transporte":    "#4ECDC4",
    "Saúde":         "#45B7D1",
    "Educação":      "#96CEB4",
    "Esporte":       "#FFEAA7",
    "Assinaturas":   "#C3A6FF",
    "Investimentos": "#66BB6A",
    "Fatura Cartão": "#FFA726",
    "Lazer":         "#FF8A65",
    "Receita":       "#26A69A",
    "Estorno":       "#90A4AE",
    "Outros":        "#78909C",
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

    st.markdown("---")
    st.caption(f"Total de meses importados: **{len(meses)}**")

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

tab_resumo, tab_transacoes, tab_historico = st.tabs(
    ["📊 Resumo", "📋 Transações", "📈 Histórico"]
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
            st.caption("Configure suas metas no final desta página.")

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

    # ── Gerenciar Metas ──
    st.markdown("---")
    with st.expander("⚙️ Gerenciar Metas por Categoria"):
        st.caption("Define o limite máximo de gasto mensal por categoria.")
        col_mc, col_mv, col_mb = st.columns([2, 2, 1])
        with col_mc:
            meta_cat = st.selectbox("Categoria", CATEGORIAS_META, key="meta_cat")
        with col_mv:
            metas_atuais = db.get_metas()
            valor_existente = metas_atuais.get(meta_cat, 0.0)
            meta_val = st.number_input(
                "Limite mensal (R$)",
                min_value=0.0,
                value=valor_existente,
                step=50.0,
                key="meta_val",
            )
        with col_mb:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Salvar", type="primary") and meta_val > 0:
                db.salvar_meta(meta_cat, meta_val)
                st.success(f"Meta salva!")
                st.rerun()

        if metas_atuais:
            st.markdown("**Metas ativas:**")
            for cat, limite in sorted(metas_atuais.items()):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"**{cat}**")
                c2.write(fmt_brl(limite) + " / mês")
                if c3.button("🗑️", key=f"del_meta_{cat}"):
                    db.deletar_meta(cat)
                    st.rerun()

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
#  TAB 3 — HISTÓRICO
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
