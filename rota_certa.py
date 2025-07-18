from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from waitress import serve
import requests, json, asyncio, threading, uuid

# 🔐 Tokens
ACCESS_TOKEN = "APP_USR-264234346131232-071723-2b11d40f943d9721d869863410833122-777482543"
BOT_TOKEN = "8095673432:AAG8YrbG1J9zUmoz3-u_J1kV6yA9M1Vt8ec"  # Substitua pelo seu token do Telegram
WEBHOOK_URL = "https://rota-zd11.onrender.com/telegram"  # Substitua pela sua URL pública

# 🧠 Dados locais
usuarios = {}
creditos = {}
pagamentos_pendentes = {}

# 💳 Opções de crédito
opcoes_credito = {
    "1": {"quantidade": 30, "valor": 19.90},
    "2": {"quantidade": 60, "valor": 36.90},
    "3": {"quantidade": 90, "valor": 51.90},
    "4": {"quantidade": 120, "valor": 62.90},
}

# 🚀 Flask app
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

@app.route("/", methods=["GET"])
def home():
    return "<h1>Rota Certa Bot está online com Webhook 🚀</h1>"

@app.route("/webhook/pix", methods=["POST"])
def webhook_pix():
    try:
        dados = request.get_json(force=True)
        print("🔔 Webhook recebido:", dados)
        threading.Thread(target=processar_pagamento, args=(dados,)).start()
        return "OK", 200
    except Exception as e:
        print(f"❌ Erro interno no webhook: {e}")
        return "Erro interno", 500

def processar_pagamento(dados):
    try:
        payment_id = str(dados.get("data", {}).get("id"))
        chat_id = pagamentos_pendentes.get(payment_id)
        if not chat_id:
            print(f"⚠️ Pagamento não reconhecido: {payment_id}")
            return

        url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"❌ Erro ao consultar pagamento: {response.text}")
            return

        pagamento = response.json()
        print("📄 Detalhes do pagamento:", pagamento)

        if pagamento.get("status") == "approved":
            quantidade = int(pagamento.get("transaction_amount", 0) // 0.66)
            creditos[str(chat_id)] = creditos.get(str(chat_id), 0) + quantidade
            nome = usuarios.get(str(chat_id), {}).get("nome", "entregador")
            mensagem = (
                f"🎉 Olá {nome}!\n"
                f"Recebemos seu pagamento e liberamos {quantidade} créditos para você.\n"
                f"Envie /ajuda para começar a usar o corretor de romaneio!"
            )
            asyncio.run(bot.send_message(chat_id=chat_id, text=mensagem))

    except Exception as e:
        print(f"❌ Erro ao processar pagamento: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    nome = update.effective_user.first_name
    usuarios[str(chat_id)] = {"nome": nome}
    creditos[str(chat_id)] = creditos.get(str(chat_id), 0) + 1

    await update.message.reply_text(
        f"Cadastro concluído, {nome}! 🎉\nVocê ganhou 1 crédito para experimentar nosso corretor de romaneio.\n"
        "Envie /adquirir para comprar créditos ou /ajuda caso você não saiba por onde começar."
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 Envie seu romaneio e eu corrijo pra você!\nUse /adquirir para comprar mais créditos.")

async def adquirir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("30 créditos – R$ 19,90", callback_data="1")],
        [InlineKeyboardButton("60 créditos – R$ 36,90", callback_data="2")],
        [InlineKeyboardButton("90 créditos – R$ 51,90", callback_data="3")],
        [InlineKeyboardButton("120 créditos – R$ 62,90", callback_data="4")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Ótimo! Você escolheu adquirir créditos. 🌟\n\n"
        "Escolha uma das opções abaixo e clique para gerar o pagamento via PIX:",
        reply_markup=reply_markup
    )

async def processar_escolha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(text="Gerando pagamento via PIX...")

    chat_id = query.message.chat.id
    escolha = query.data
    threading.Thread(target=gerar_pagamento_pix, args=(chat_id, escolha)).start()

    await query.edit_message_text("⏳ Processando sua solicitação...")

def gerar_pagamento_pix(chat_id, escolha):
    if escolha not in opcoes_credito:
        bot.send_message(chat_id=chat_id, text="❌ Opção inválida. Tente novamente.")
        return

    dados = opcoes_credito[escolha]
    quantidade = dados["quantidade"]
    valor = dados["valor"]

    url = "https://api.mercadopago.com/v1/payments"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "X-Idempotency-Key": str(uuid.uuid4())
    }
    payload = {
        "transaction_amount": valor,
        "description": f"{quantidade} créditos Rota Certa",
        "payment_method_id": "pix",
        "payer": {
            "email": "usuario@email.com",
            "first_name": "Usuário",
            "last_name": "Teste",
            "identification": {
                "type": "CPF",
                "number": "12345678909"
            }
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    print("🔍 Resposta Mercado Pago:", data)

    link = (
        data.get("point_of_interaction", {}).get("transaction_data", {}).get("ticket_url")
        or data.get("transaction_details", {}).get("external_resource_url")
        or "⚠️ Link de pagamento não disponível. Tente novamente mais tarde."
    )

    payment_id = str(data.get("id"))
    pagamentos_pendentes[payment_id] = chat_id

    bot.send_message(
        chat_id=chat_id,
        text=f"💳 Para adquirir {quantidade} créditos, pague via PIX usando o link abaixo:\n{link}\n\n"
             "Assim que o pagamento for aprovado, seus créditos serão liberados automaticamente."
    )

# 🔧 Inicializa o bot com webhook
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ajuda", ajuda))
application.add_handler(CommandHandler("adquirir", adquirir))
application.add_handler(CallbackQueryHandler(processar_escolha))

if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=5000,
        webhook_url=WEBHOOK_URL
    )
