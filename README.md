# 💰 financas

Dashboard pessoal de controle financeiro. Importa extratos do Nubank em CSV, categoriza automaticamente e exibe gráficos de gastos, receitas e investimentos — tudo rodando local, sem depender de nenhum serviço externo além das cotações do Yahoo Finance.

## Funcionalidades

**Extratos e gastos**
- Upload de extrato CSV do Nubank (sem duplicatas — pode subir o mesmo arquivo várias vezes)
- Categorização automática por palavras-chave (com regras personalizáveis)
- **Categorização com IA** — analisa transações em "Outros" e sugere categorias automaticamente
- Totais que batem com o PDF do Nubank (entradas, saídas, saldo)
- Detalhamento: gastos do dia-a-dia vs. investimentos vs. fatura do cartão
- Gráficos: pizza por categoria, gastos por dia, saldo acumulado no mês
- Edição de categoria direto na tabela de transações
- Metas por categoria com barra de progresso
- Alertas de gasto alto (comparado com média histórica)
- Top 5 maiores gastos do mês
- Exportação CSV com categorias aplicadas

**Planejamento**
- Regra 50/30/20, projeção de poupança, custo em dias de trabalho
- Bloco de anotações pessoais na sidebar

**Carteira de Investimentos** *(inspirado no Investidor10)*
- Cadastro manual de posições: ações, ETFs, criptos, FIIs — qualquer ativo do Yahoo Finance
- Cotações em tempo real via Yahoo Finance
- Multi-moeda: visualize o patrimônio em BRL, USD, EUR, GBP, JPY, ARS e mais
- Cards de resumo: Patrimônio Total, Lucro/Prejuízo, Variação %, câmbio atual
- Gráfico de evolução do patrimônio (mensal) com seletor de período
- Gráfico de alocação por tipo de ativo (donut)
- Tabela de posições com P. Médio, P. Atual, Custo Total, Variação por ativo
- Busca de ativos por nome ou ticker com sugestão automática (search-as-you-type)
- Preço médio pode ser informado em USD ou BRL, com conversão automática

**IA e histórico**
- Assistente de IA (Groq / Claude / Gemini) com histórico persistente
- A IA tem acesso ao resumo do portfólio e ao histórico de gastos para dar conselhos contextualizados
- Histórico comparativo entre meses

**Geral**
- Banco SQLite local (~2 MB para 3 anos de dados)
- Design escuro inspirado no Revolut

## Instalação local

```bash
git clone https://github.com/seu-usuario/financas.git
cd financas
bash setup.sh
venv/bin/streamlit run app.py
```

Abre em: http://localhost:8501

## Como usar

**Extratos**
1. Exporte o extrato do seu banco em CSV
   - Nubank: **Perfil → Extratos → seleciona o mês → exportar CSV**
2. Na sidebar: clica em **"Importar extrato"** e sobe o arquivo
3. O app categoriza automaticamente e salva no banco local (`data/financas.db`)
4. Para ajustar categorias erradas: aba **Transações** → edita na tabela → **Salvar alterações**
5. Para criar regras automáticas: aba **Transações** → **⚙️ Regras de Categorização**
6. Para categorizar "Outros" com IA: aba **Transações** → **🤖 Categorizar com IA**
7. Para excluir um extrato importado por engano: sidebar → **🗑️ Excluir extrato**

> **Bancos suportados atualmente:** Nubank. O formato esperado é o CSV padrão do Nubank (colunas `date`, `title`, `amount`). Suporte a outros bancos está planejado — veja abaixo.

### Suporte a outros bancos (roadmap)

O app foi pensado para ser universal. O plano de expansão:

- **Curto prazo:** mapeamento manual de colunas para bancos como Inter, C6, Itaú
- **Médio prazo:** detecção automática do formato ao importar — o app tenta identificar as colunas automaticamente
- **Longo prazo:** se o formato for desconhecido e a API de IA estiver configurada, o assistente analisa o CSV e pergunta ao usuário quais colunas correspondem a data, valor e descrição — sem precisar codar nada

**Carteira de Investimentos**
1. Acesse a aba **💼 Investimentos**
2. Clique em **➕ Adicionar / Gerenciar Posições**
3. Na busca, digite o nome ou ticker do ativo (ex: `Bitcoin`, `QQQ`, `Petrobras`)
4. Selecione o ativo na lista de sugestões
5. Informe a quantidade e o preço médio de compra (em USD ou BRL)
6. Clique em **➕ Salvar** — as cotações são buscadas automaticamente do Yahoo Finance
7. Para editar ou excluir: use os campos abaixo de cada posição cadastrada

> **Nota:** ativos da B3 (ações brasileiras) usam o sufixo `.SA` — ex: `PETR4.SA`. Criptos usam `-USD` — ex: `BTC-USD`. A busca já formata automaticamente.

## Deploy no Oracle Cloud VM

A melhor opção para uso pessoal: privado, gratuito (Always Free tier) e sempre no ar.

> Para um guia completo de como configurar a VM do zero (firewall, Docker, Nginx Proxy Manager, DuckDNS, SSL), veja: **[oracle-free-server-guide](https://github.com/Wolsadek/oracle-free-server-guide)**

### 1. Clonar e configurar o projeto

```bash
ssh ubuntu@SEU_IP_ORACLE
git clone https://github.com/seu-usuario/financas.git ~/github/financas
cd ~/github/financas
bash setup.sh
```

O `setup.sh` cria o `venv` e instala todas as dependências automaticamente.

### 2. Criar serviço systemd (mantém o app rodando)

```bash
sudo nano /etc/systemd/system/financas.service
```

```ini
[Unit]
Description=Financas Dashboard
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/github/financas
ExecStart=/home/ubuntu/github/financas/venv/bin/streamlit run app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable financas
sudo systemctl start financas
```

### 3. Nginx Proxy Manager (já instalado via Docker)

No painel do NPM (`http://SEU_IP:81`):

1. **Proxy Hosts → Add Proxy Host**
   - Domain: `seu-dominio.duckdns.org`
   - Forward Hostname: `172.18.0.1` (gateway do Docker)
   - Forward Port: `8501`
   - Marcar: **Websockets Support**
2. **SSL** → Request Let's Encrypt → marcar **Force SSL**
3. **Access** → criar Access List com autenticação básica (usuário/senha) + regra Allow `0.0.0.0/0`

### 4. Liberar portas no Oracle Cloud

No painel Oracle Cloud:
**Networking → Virtual Cloud Networks → sua VCN → Security Lists → Ingress Rules**
→ Adicionar regras TCP para as portas: **80**, **443**, **8501**

Firewall na VM:
```bash
sudo iptables -I INPUT -s 172.16.0.0/12 -p tcp --dport 8501 -j ACCEPT
```

Acesse em: `https://seu-dominio.duckdns.org`

### Atualizar o app no servidor

Sempre que houver mudanças no código:

```bash
cd ~/github/financas
git stash              # guarda alterações locais temporariamente
git pull
git stash drop         # descarta versão antiga (opcional)
bash setup.sh          # instala dependências novas (ex: yfinance, anthropic)
sudo systemctl restart financas
```

> Se aparecer erro de dependência no app (ex: "pip install yfinance"), sempre rode `bash setup.sh` — ele garante que tudo do `requirements.txt` está instalado no `venv`.

---

> **Por que não Vercel?**
> Vercel é para sites estáticos e funções serverless (Next.js, React, etc.).
> Streamlit precisa de um processo persistente com WebSocket, e o SQLite precisa de
> filesystem permanente — ambos incompatíveis com o modelo serverless do Vercel.
> O Oracle VM é a opção certa aqui.

## Estrutura

```
financas/
├── app.py                  # Interface Streamlit + lógica de categorização
├── database.py             # Operações SQLite
├── requirements.txt
├── setup.sh                # Script de instalação/atualização
├── .streamlit/
│   └── config.toml         # Tema escuro + configurações do servidor
└── data/
    └── financas.db         # Banco local (criado automaticamente, não vai pro git)
```
