import os
import logging
import gspread
import matplotlib.pyplot as plt
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configuração do logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações do Google Sheets
CREDS_FILE = os.getenv('GOOGLE_CREDS_FILE', 'credenciais.json')
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_NAME = 'botgastos'

def get_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPES)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).sheet1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Olá! Use /add <valor> <descrição> para adicionar uma despesa.')

async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        valor = float(context.args[0])
        descricao = ' '.join(context.args[1:])
        if valor <= 0:
            await update.message.reply_text('O valor deve ser positivo.')
            return
        if not descricao.strip():
            await update.message.reply_text('A descrição não pode estar vazia.')
            return
        sheet = get_sheet()
        sheet.append_row([valor, descricao])
        await update.message.reply_text(f'Despesa de R${valor:.2f} para "{descricao}" adicionada.')
    except (IndexError, ValueError):
        await update.message.reply_text('Uso: /add <valor> <descrição>')
    except Exception as e:
        logger.error(f"Erro ao adicionar despesa: {e}")
        await update.message.reply_text('Erro ao adicionar despesa.')

async def list_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        sheet = get_sheet()
        records = sheet.get_all_values()
        if not records or len(records) <= 1:
            await update.message.reply_text('Nenhuma despesa registrada.')
        else:
            response = "Despesas registradas:\n"
            for row in records[1:]:
                valor = row[0].replace(',', '.')
                descricao = row[1]
                response += f"R${float(valor):.2f} - {descricao}\n"
            await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Erro ao listar despesas: {e}")
        await update.message.reply_text('Erro ao listar despesas.')

def generate_chart():
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        if not records:
            raise ValueError("A planilha está vazia. Adicione dados para gerar o gráfico.")
        df = pd.DataFrame(records)
        df.columns = df.columns.str.strip().str.lower()
        if 'valor' not in df.columns or 'descrição' not in df.columns:
            raise ValueError("A planilha deve conter as colunas 'Valor' e 'Descrição'.")
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
        df.dropna(subset=['valor'], inplace=True)
        if df.empty:
            raise ValueError("Nenhum dado válido encontrado para gerar o gráfico.")
        plt.figure(figsize=(8, 8))
        plt.pie(df['valor'], labels=df['descrição'], autopct='%1.1f%%', startangle=140)
        plt.title('Distribuição de Gastos')
        plt.savefig('expenses_pie_chart.png')
        plt.close()
    except Exception as e:
        logger.error(f"Erro ao gerar gráfico: {e}")
        raise e

async def send_chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        generate_chart()
        await update.message.reply_photo(photo=open('expenses_pie_chart.png', 'rb'))
        os.remove('expenses_pie_chart.png')
    except Exception as e:
        logger.error(f"Erro ao gerar gráfico: {e}")
        await update.message.reply_text('Erro ao gerar gráfico.')

def main() -> None:
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        raise ValueError("O token do bot não foi definido. Configure a variável de ambiente TELEGRAM_BOT_TOKEN.")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_expense))
    application.add_handler(CommandHandler("list", list_expenses))
    application.add_handler(CommandHandler("chart", send_chart))
    application.run_polling()

if __name__ == '__main__':
    main()
