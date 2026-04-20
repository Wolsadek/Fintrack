# 💰 financas

Dashboard pessoal de controle financeiro. Importa extratos do Nubank em CSV, categoriza automaticamente e exibe gráficos de gastos, receitas e investimentos.

## Funcionalidades

- Upload de extrato CSV do Nubank (sem duplicatas — pode subir o mesmo arquivo várias vezes)
- Categorização automática por palavras-chave (com regras personalizáveis)
- Totais que batem com o PDF do Nubank (entradas, saídas, saldo)
- Detalhamento: gastos do dia-a-dia vs. investimentos vs. fatura do cartão
- Gráficos: pizza por categoria, gastos por dia, saldo acumulado no mês
- Edição de categoria direto na tabela de transações
- Histórico comparativo entre meses (disponível após importar 2+ meses)
- Exportação CSV com categorias aplicadas
- Banco SQLite local (~2 MB para 3 anos de dados)

## Instalação local

```bash
git clone https://github.com/seu-usuario/financas.git
cd financas
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Abre em: http://localhost:8501

## Como usar

1. No app do Nubank: **Perfil → Extratos → seleciona o mês → exportar CSV**
2. Na sidebar do dashboard: clica em **"Importar extrato Nubank"** e sobe o arquivo
3. O app categoriza automaticamente e salva no banco local (`data/financas.db`)
4. Para ajustar categorias erradas: aba **Transações** → edita na tabela → **Salvar alterações**
5. Para criar regras pra próximos uploads: aba **Transações** → **⚙️ Regras de Categorização Automática**

## Deploy no Oracle Cloud VM

A melhor opção para uso pessoal: privado, gratuito (Always Free tier) e sempre no ar.

### 1. Configurar a VM

```bash
# Conectar na VM
ssh ubuntu@SEU_IP_ORACLE

# Instalar Python e nginx
sudo apt update && sudo apt install -y python3-venv nginx apache2-utils

# Clonar o projeto
git clone https://github.com/seu-usuario/financas.git ~/financas
cd ~/financas
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

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
WorkingDirectory=/home/ubuntu/financas
ExecStart=/home/ubuntu/financas/venv/bin/streamlit run app.py
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

### 3. Configurar nginx com senha (obrigatório — dados financeiros!)

```bash
# Criar senha de acesso
sudo htpasswd -c /etc/nginx/.htpasswd seu_usuario

# Configurar nginx
sudo nano /etc/nginx/sites-available/financas
```

```nginx
server {
    listen 80;
    server_name _;

    auth_basic "Acesso Restrito";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass         http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/financas /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

### 4. Liberar porta no Oracle Cloud

No painel Oracle Cloud:
**Networking → Virtual Cloud Networks → sua VCN → Security Lists → Ingress Rules**
→ Adicionar regra: protocolo TCP, porta 80, source 0.0.0.0/0

Também no firewall da VM:
```bash
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo netfilter-persistent save
```

Acesse em: `http://SEU_IP_ORACLE` (com usuário/senha que você criou)

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
├── .streamlit/
│   └── config.toml         # Tema escuro + configurações do servidor
└── data/
    └── financas.db         # Banco local (criado automaticamente, não vai pro git)
```
