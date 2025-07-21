import logging
import openpyxl
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import io
from datetime import datetime
from collections import defaultdict

# === CONFIGURAÇÕES ===
TOKEN = "8095673432:AAGa19vnVQDqxLDz_OSr0wFPQUzH2mh03sA"

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

# === COMANDO /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Envie seu arquivo de romaneio (.xlsx) para começar o processamento."
    )

# === FUNÇÃO PRINCIPAL DE PROCESSAMENTO ===
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        document = update.message.document
        if not document.file_name.endswith(".xlsx"):
            await update.message.reply_text("❌ O arquivo enviado não é uma planilha .xlsx. Envie o romaneio correto.")
            return

        # Baixa o arquivo
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        wb = openpyxl.load_workbook(filename=io.BytesIO(file_content))
        ws = wb.active

        # === EXEMPLO DE AGRUPAMENTO POR ENDEREÇO ===
        end_col = None
        seq_col = None

        for idx, cell in enumerate(ws[1]):
            if cell.value == "Destination Address":
                end_col = idx
            elif cell.value == "Sequence":
                seq_col = idx

        if end_col is None or seq_col is None:
            await update.message.reply_text("❌ A planilha precisa conter as colunas 'Destination Address' e 'Sequence'.")
            return

        agrupamentos = defaultdict(list)

        for row in ws.iter_rows(min_row=2):
            endereco = row[end_col].value
            sequencia = row[0].value  # Supondo que a coluna A seja o número do pacote
            if endereco:
                chave = endereco.strip().lower()
                agrupamentos[chave].append(sequencia)

        for row in ws.iter_rows(min_row=2):
            endereco = row[end_col].value
            if endereco:
                chave = endereco.strip().lower()
                seqs = agrupamentos[chave]
                row[seq_col].value = ",".join(map(str, sorted(seqs)))

        # === SALVANDO E ENVIANDO ===
        output = io.BytesIO()
        data = datetime.now().strftime("%d-%m-%Y")
        nome_saida = f"ROTA-ATUALIZADA-{data}.xlsx"
        wb.save(output)
        output.seek(0)

        await update.message.reply_document(
            document=InputFile(output, filename=nome_saida),
            caption="✅ Arquivo processado com sucesso!\n\n📩 Para iniciar novamente, envie seu romaneio."
        )

    except Exception as e:
        logging.exception("Erro ao processar o arquivo:")
        await update.message.reply_text("⚠️ Ocorreu um erro durante o processamento. Verifique se o arquivo está correto e tente novamente.")

# === MAIN ===
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    app.run_polling()
