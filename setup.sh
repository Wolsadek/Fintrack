#!/bin/bash
set -e

echo "🔧 Configurando ambiente..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtualenv criado"
else
    echo "ℹ️  Virtualenv já existe"
fi

echo "📦 Instalando dependências..."
venv/bin/pip install -r requirements.txt -q

mkdir -p data

echo ""
echo "✅ Setup completo!"
echo ""
echo "Para rodar localmente:"
echo "  venv/bin/streamlit run app.py"
echo ""
echo "Para rodar como serviço (servidor):"
echo "  sudo systemctl start financas"
