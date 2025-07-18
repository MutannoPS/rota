from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from waitress import serve
import requests, json, asyncio, threading

# 🔐 Tokens
ACCESS_TOKEN = "APP_USR-264234346131232-071723-2b11d40f943d9721d869863410833122-777482543"  # Substitua pelo seu token do Mercado Pago
BOT_TOKEN = "8095673432:AAEOd6Sceqa7ClwP36bg7kPlu64fPWSvN2w"  # Substitua pelo seu token do Telegram

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
    return "<h1>Rota Certa Bot está online 🚀</h1>"

@app.route("/webhook/pix", methods=["POST"])
def webhook_pix():
    try:
        dados = request.get_json(force=True)
        print("🔔 Webhook recebido:", dados)

        payment_id = str(dados.get("data", {}).get("id"))
        if not payment_id:
            print("❌ ID de pagamento ausente na requisição.")
            return "ID de pagamento ausente", 400

        chat_id = pagamentos_pendentes.get(payment_id)
        if not chat_id:
            print(f"⚠️ Pagamento não reconhecido: {payment_id}")
            return "Pagamento não reconhecido", 400

        url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"❌ Erro ao consultar pagamento: {response.text}")
            return "Erro ao consultar pagamento", 500

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

        return "OK", 200

    except Exception as e:
        print(f"❌ Erro interno no webhook: {e}")
        return "Erro interno", 500

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
    await query.answer()

    chat_id = query.message.chat.id
    escolha = query.data

    if escolha not in opcoes_credito:
        await query.edit_message_text("❌ Opção inválida. Tente novamente.")
        return

    dados = opcoes_credito[escolha]
    quantidade = dados["quantidade"]
    valor = dados["valor"]

    url = "https://api.mercadopago.com/v1/payments"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
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
    print(f"🧾 Pagamento gerado: {payment_id}")
    pagamentos_pendentes[payment_id] = chat_id

    await query.edit_message_text(
        f"💳 Para adquirir {quantidade} créditos, pague via PIX usando o link abaixo:\n{link}\n\n"
        "Assim que o pagamento for aprovado, seus créditos serão liberados automaticamente."
    )

def iniciar_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("ajuda", ajuda))
    app_telegram.add_handler(CommandHandler("adquirir", adquirir))
    app_telegram.add_handler(CallbackQueryHandler(processar_escolha))

    loop.run_until_complete(app_telegram.initialize())
    loop.run_until_complete(app_telegram.start())
    loop.run_until_complete(app_telegram.updater.start_polling())
    loop.run_forever()

if __name__ == "__main__":
    threading.Thread(target=iniciar_bot).start()
    serve(app, host="0.0.0.0", port=5000)
