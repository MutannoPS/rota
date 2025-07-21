import pandas as pd
import requests, re, io, os
from datetime import datetime
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

TOKEN = "8095673432:AAHy4SwjFRyWnjpHeydQJ9eUMiu_fH9DIi8"
app_telegram = Application.builder().token(TOKEN).build()
app_web = Flask(__name__)

def consultar_logradouro(cep):
    cep = str(cep).replace("-", "").strip()
    url = f"https://opencep.com/v1/{cep}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("logradouro")
    return None

def extrair_numero_complemento(endereco):
    match = re.search(r"\d.*", endereco)
    return match.group(0) if match else ""

def corrigir_endereco(endereco, logradouro_api):
    numero_complemento = extrair_numero_complemento(endereco)
    if logradouro_api:
        return f"{logradouro_api}, {numero_complemento}".strip(", ")
    return endereco

def normalizar_endereco(endereco):
    match = re.match(r"(.+?),\s*(\d+)", endereco)
    if match:
        rua, numero = match.group(1).strip(), match.group(2).strip()
        return f"{rua}, {numero}"
    return endereco.strip()

def formatar_sequence(lista):
    itens = sorted(set(lista))
    texto = ", ".join(itens)
    if len(itens) > 1:
        return f"{texto}; Total: {len(itens)} pacotes."
    return texto

async def tratar_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hora = datetime.now().hour
    saudacao = "Bom dia ☀️" if hora < 12 else "Boa tarde 🌤️" if hora < 18 else "Boa noite 🌙"
    await update.message.reply_text(f"{saudacao}\n📥 Aprimorando sua planilha, aguarde ⏳")

    file_info = await update.message.document.get_file()
    file_bytes = await file_info.download_as_bytearray()
    nome_arquivo = update.message.document.file_name
    match = re.search(r"(\d{2}-\d{2}-\d{4})", nome_arquivo)
    data_str = match.group(1) if match else "data"
    nome_final = f"RotaAtualizada-{data_str}.xlsx"

    df = pd.read_excel(io.BytesIO(file_bytes))
    for i, row in df.iterrows():
        cep, endereco = row.get("Zipcode/Postal code"), row.get("Destination Address")
        if pd.notna(cep) and pd.notna(endereco):
            df.at[i, "Destination Address"] = corrigir_endereco(endereco, consultar_logradouro(cep))

    df["Endereco Corrigido"] = df["Destination Address"].apply(normalizar_endereco)
    df["Sequence"] = df["Sequence"].astype(str)
    agrupado = df.groupby("Endereco Corrigido", as_index=False).agg({
        "Sequence": formatar_sequence,
        "Destination Address": "first",
        "Bairro": "first",
        "City": "first",
        "Zipcode/Postal code": "first"
    }).drop(columns=["Endereco Corrigido"])
    buffer = io.BytesIO()
    agrupado.to_excel(buffer, index=False)
    buffer.seek(0)
    await update.message.reply_document(document=buffer, filename=nome_final)
    await update.message.reply_text("✅ Planilha atualizada! Boa rota! 🎉")

app_telegram.add_handler(MessageHandler(filters.Document.ALL, tratar_arquivo))

@app_web.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_telegram.bot)
    app_telegram.update.update(update)
    return "OK", 200

if __name__ == "__main__":
    app_telegram.bot.set_webhook(f"https://SEU-DOMINIO.onrender.com/{TOKEN}")
    app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
