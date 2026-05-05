# 💰 financas

Dashboard pessoal de controle financeiro. Importa extratos do Nubank em CSV, categoriza automaticamente e exibe gráficos de gastos, receitas e investimentos.

## Funcionalidades

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
- Aba Planejamento: regra 50/30/20, projeção de poupança, custo em dias de trabalho
- Assistente de IA (Groq) com histórico persistente
- Histórico comparativo entre meses
- Exportação CSV com categorias aplicadas
- Banco SQLite local (~2 MB para 3 anos de dados)

## Instalação local

```bash
git clone https://github.com/seu-usuario/financas.git
cd financas
bash setup.sh
venv/bin/streamlit run app.py
```

Abre em: http://localhost:8501

## Como usar

1. No app do Nubank: **Perfil → Extratos → seleciona o mês → exportar CSV**
2. Na sidebar do dashboard: clica em **"Importar extrato Nubank"** e sobe o arquivo
3. O app categoriza automaticamente e salva no banco local (`data/financas.db`)
4. Para ajustar categorias erradas: aba **Transações** → edita na tabela → **Salvar alterações**
5. Para criar regras para próximos uploads: aba **Transações** → **⚙️ Regras de Categorização Automática**
6. Para categorizar transações "Outros" com IA: aba **Transações** → **🤖 Categorizar 'Outros' com IA**

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
git pull
bash setup.sh          # reinstala dependências se necessário
sudo systemctl restart financas
```

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
