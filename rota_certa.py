import pandas as pd
import requests
import re
import io
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = "8095673432:AAHy4SwjFRyWnjpHeydQJ9eUMiu_fH9DIi8"

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
        rua = match.group(1).strip()
        numero = match.group(2).strip()
        return f"{rua}, {numero}"
    return endereco.strip()

def formatar_sequence(lista):
    itens = sorted(set(lista))
    texto = ", ".join(itens)
    if len(itens) > 1:
        return f"{texto}; Total: {len(itens)} pacotes."
    return texto

async def tratar_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Saudação personalizada
    hora = datetime.now().hour
    if 5 <= hora < 12:
        saudacao = "Bom dia ☀️"
    elif 12 <= hora < 18:
        saudacao = "Boa tarde 🌤️"
    else:
        saudacao = "Boa noite 🌙"

    await update.message.reply_text(
        f"{saudacao}\n\n📥 Estou Aprimorando Sua Planilha, obrigado por aguardar. ⏳🚚"
    )

    arquivo = update.message.document
    nome_original = arquivo.file_name
    match = re.search(r"(\d{2}-\d{2}-\d{4})", nome_original)
    data_str = match.group(1) if match else "data"
    nome_final = f"RotaAtualizada-{data_str}.xlsx"

    file = await arquivo.get_file()
    file_bytes = await file.download_as_bytearray()

    df = pd.read_excel(io.BytesIO(file_bytes))

    for i, row in df.iterrows():
        cep = row.get("Zipcode/Postal code")
        endereco_original = row.get("Destination Address")
        if pd.notna(cep) and pd.notna(endereco_original):
            logradouro_api = consultar_logradouro(cep)
            endereco_corrigido = corrigir_endereco(endereco_original, logradouro_api)
            df.at[i, "Destination Address"] = endereco_corrigido

    df["Endereco Corrigido"] = df["Destination Address"].apply(normalizar_endereco)
    df["Sequence"] = df["Sequence"].astype(str)

    agrupado = (
        df.groupby("Endereco Corrigido", as_index=False)
        .agg({
            "Sequence": lambda x: formatar_sequence(x),
            "Destination Address": "first",
            "Bairro": "first",
            "City": "first",
            "Zipcode/Postal code": "first"
        })
    )

    agrupado.drop(columns=["Endereco Corrigido"], inplace=True)
    colunas_finais = ["Sequence", "Destination Address", "Bairro", "City", "Zipcode/Postal code"]
    agrupado = agrupado[colunas_finais]

    buffer = io.BytesIO()
    agrupado.to_excel(buffer, index=False)
    buffer.seek(0)

    await update.message.reply_document(document=buffer, filename=nome_final)
    await update.message.reply_text("✅ Sua Planilha Foi Atualizada Com Sucesso! Tenha uma ótimo Rota! 🎉")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.Document.ALL, tratar_arquivo))
app.run_polling()
