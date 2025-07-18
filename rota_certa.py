from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from waitress import serve
import requests, json, asyncio, threading

# 🔐 Tokens
ACCESS_TOKEN = "APP_USR-264234346131232-071723-2b11d40f943d9721d869863410833122-777482543"
BOT_TOKEN = "7544200568:AAErpB0bVwAcp_YSr_uOGlCVZugQ7O9LTQQ"
# 🧠 Dados locais
usuarios = {}
creditos = {}
pagamentos_pendentes = {}

# 🚀 Flask app
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

# ✅ Rota principal
@app.route("/", methods=["GET"])
def home():
    return "<h1>Rota Certa Bot está online 🚀</h1>"

# 📩 Webhook do Mercado Pago
@app.route("/webhook/pix", methods=["POST"])
def webhook_pix():
    dados = request.json
    payment_id = str(dados.get("data", {}).get("id"))
    chat_id = pagamentos_pendentes.get(payment_id)

    if not chat_id:
        return "Pagamento não reconhecido", 400

    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return "Erro ao consultar pagamento", 500

    pagamento = response.json()
    if pagamento.get("status") == "approved":
        creditos[str(chat_id)] = creditos.get(str(chat_id), 0) + 1
        nome = usuarios.get(str(chat_id), {}).get("nome", "entregador")
        mensagem = (
            f"🎉 Olá {nome}!\n"
            f"Recebemos seu pagamento e liberamos 1 crédito para você.\n"
            f"Envie /ajuda para começar a usar o corretor de romaneio!"
        )
        asyncio.run(bot.send_message(chat_id=chat_id, text=mensagem))

    return "OK", 200

# 🤖 Comandos do bot
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
    chat_id = update.effective_chat.id
    url = "https://api.mercadopago.com/v1/payments"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    payload = {
        "transaction_amount": 9.90,
        "description": "Crédito Rota Certa",
        "payment_method_id": "pix",
        "payer": {"email": "teste@email.com"}
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    link = data.get("point_of_interaction", {}).get("transaction_data", {}).get("ticket_url")
    payment_id = str(data.get("id"))

    pagamentos_pendentes[payment_id] = chat_id

    await update.message.reply_text(
        f"💳 Para adquirir 1 crédito, pague via PIX usando o link abaixo:\n{link}\n"
        "Assim que o pagamento for aprovado, seu crédito será liberado automaticamente."
    )

# 🧵 Rodar Flask e Bot juntos com asyncio na thread
def iniciar_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("ajuda", ajuda))
    app_telegram.add_handler(CommandHandler("adquirir", adquirir))

    loop.run_until_complete(app_telegram.initialize())
    loop.run_until_complete(app_telegram.start())
    loop.run_until_complete(app_telegram.updater.start_polling())
    loop.run_forever()

# 🚀 Iniciar tudo com Waitress
if __name__ == "__main__":
    threading.Thread(target=iniciar_bot).start()
    serve(app, host="0.0.0.0", port=5000)
