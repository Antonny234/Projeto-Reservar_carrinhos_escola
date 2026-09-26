# Reserva de Carrinhos Escolares

Sistema Django para gestão de carrinhos de notebooks/tablets, reservas por horário, controle de inventário, fichas de uso e administração por escola.

## Stack

- Python 3.12+
- Django 6.1.1
- PostgreSQL em produção / SQLite para desenvolvimento local
- WhiteNoise para arquivos estáticos
- django-select2 para pesquisas nos formulários
- Pandas + OpenPyXL para importação/exportação
- Resend para e-mail de confirmação e recuperação de senha

Django 6.1.1 é a versão estável indicada atualmente pelo projeto Django e suporta Python 3.12–3.14.

## Instalação local

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/macOS
# Para desenvolvimento local, use DJANGO_DEBUG=True no .env.
python manage.py migrate
python manage.py check
python manage.py runserver
```

## Variáveis de ambiente

Em produção, `DJANGO_SECRET_KEY`, `DATABASE_URL` e os hosts/origens autorizados devem ser configurados no provedor. Nunca coloque `.env`, backups de banco ou credenciais no Git.

## Deploy

O projeto já possui `Procfile`, `railway.json` e `nixpacks.toml`. O processo de build executa `check --deploy` e `collectstatic`; o processo de inicialização aplica migrações antes do Gunicorn.

## Segurança aplicada

- Superadmin separado da administração por escola.
- Alterações de estado somente via POST + CSRF.
- Isolamento de consultas pela escola ativa.
- PIN do tablet armazenado com hash.
- Restrições de banco para horários inválidos, quantidade inválida e reserva duplicada de carrinho inteiro.
- Índices para as consultas de disponibilidade e reservas.
- Configuração de produção sem segredos hard-coded.

## Testes

```bash
python manage.py test reservas
```

Os testes devem ser executados no ambiente com as dependências instaladas e acesso ao banco de teste.


## Telegram por escola

Cada escola pode ter seu próprio bot Telegram e vários chats de destino. O token do bot é armazenado cifrado usando `TELEGRAM_ENCRYPTION_KEY`.

1. Gere uma chave Fernet para o ambiente:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

2. Cadastre `TELEGRAM_ENCRYPTION_KEY` no ambiente da aplicação.
3. No painel da escola, abra **Notificações Telegram**.
4. Crie o bot pelo `@BotFather`, cole o token e salve.
5. Gere o link de conexão e abra-o no Telegram.
6. Use o botão de teste para conferir o recebimento.

Em produção, o webhook precisa estar publicado em HTTPS. O projeto usa `setWebhook` e `secret_token` para autenticar os callbacks recebidos do Telegram.
