import os
import sys
import logging
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

# ==============================================================================
# 1. CREDENCIAIS E CONFIGURAÇÕES
# ==============================================================================
TOKEN = "8822381506:AAEFA9KscOVs_xIGOV70RJeuLPggQNojYXg"
CHAT_ID = "-1003966783268"

bot = telebot.TeleBot(TOKEN)

# Logging no terminal/Render
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- MOCK DE DADOS (Substitua pela integração da sua corretora/banco de dados) ---
POSICOES_ABERTAS = [
    {"symbol": "BTC/USDT", "side": "LONG", "entry": 64200.0, "pnl": "+4.2%", "qty": 0.05},
    {"symbol": "ETH/USDT", "side": "SHORT", "entry": 3450.0, "pnl": "-1.1%", "qty": 0.5},
]

HISTORICO_HOJE = [
    {"symbol": "SOL/USDT", "side": "LONG", "result": "PROFIT", "pnl": "+12.5%", "lucro_usd": 150.00},
    {"symbol": "BTC/USDT", "side": "SHORT", "result": "PROFIT", "pnl": "+5.2%", "lucro_usd": 80.50},
    {"symbol": "BNB/USDT", "side": "LONG", "result": "LOSS", "pnl": "-2.1%", "lucro_usd": -25.00},
]

# ==============================================================================
# 2. INICIALIZAÇÃO AUTOMÁTICA (Limpa Webhook & Cadastra Menu)
# ==============================================================================
def inicializar_bot():
    try:
        # Elimina o Erro 409 (Conflict) no Render
        bot.remove_webhook()
        logging.info("✅ Webhook antigo removido com sucesso!")
    except Exception as e:
        logging.error(f"⚠️ Erro ao remover webhook: {e}")

    try:
        # Cadastra o menu de comandos direto no aplicativo do Telegram
        bot.set_my_commands([
            BotCommand("start", "🚀 Painel Principal"),
            BotCommand("posicoes", "📊 Posições Abertas"),
            BotCommand("relatorio", "📈 Relatório Diário"),
            BotCommand("sinais", "📡 ÚLTIMOS SINAIS"),
            BotCommand("ajuda", "❓ Instruções e Suporte")
        ])
        logging.info("✅ Menu de comandos cadastrado no Telegram!")
    except Exception as e:
        logging.error(f"⚠️ Erro ao cadastrar comandos: {e}")

# ==============================================================================
# 3. CONSTRUTORES DE MENUS INTERATIVOS (TECLADOS INLINE)
# ==============================================================================
def criar_menu_principal():
    markup = InlineKeyboardMarkup(row_width=2)
    
    btn_posicoes = InlineKeyboardButton("📊 Posições Abertas", callback_data="ver_posicoes")
    btn_sinais = InlineKeyboardButton("📡 ÚLTIMOS SINAIS", callback_data="ver_sinais")
    btn_relatorio = InlineKeyboardButton("📈 Relatório Diário", callback_data="ver_relatorio")
    btn_abrir = InlineKeyboardButton("⚡ Abrir Ordem", callback_data="abrir_ordem")
    btn_fechar = InlineKeyboardButton("❌ Fechar Posição", callback_data="fechar_ordem")
    btn_refresh = InlineKeyboardButton("🔄 Atualizar Painel", callback_data="refresh_painel")
    
    markup.add(btn_posicoes, btn_sinais)
    markup.add(btn_relatorio, btn_abrir)
    markup.add(btn_fechar, btn_refresh)
    return markup

def criar_menu_fechar_posicoes():
    markup = InlineKeyboardMarkup(row_width=1)
    for pos in POSICOES_ABERTAS:
        symbol = pos["symbol"]
        side = pos["side"]
        pnl = pos["pnl"]
        btn_text = f"❌ Fechar {symbol} ({side}) | PnL: {pnl}"
        callback = f"close_pos_{symbol.replace('/', '_')}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=callback))
    
    markup.add(InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="refresh_painel"))
    return markup

# ==============================================================================
# 4. LÓGICA DO RELATÓRIO DIÁRIO
# ==============================================================================
def gerar_texto_relatorio():
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    total_trades = len(HISTORICO_HOJE)
    vitorias = sum(1 for t in HISTORICO_HOJE if t["result"] == "PROFIT")
    derrotas = sum(1 for t in HISTORICO_HOJE if t["result"] == "LOSS")
    winrate = (vitorias / total_trades * 100) if total_trades > 0 else 0
    lucro_total = sum(t["lucro_usd"] for t in HISTORICO_HOJE)
    
    status_emoji = "🟢" if lucro_total >= 0 else "🔴"
    
    texto = (
        f"📈 **RELATÓRIO DIÁRIO DE OPERAÇÕES**\n"
        f"📅 **Data:** `{data_hoje}`\n"
        f"🎯 **Canal/Grupo:** `{CHAT_ID}`\n"
        f"───────────────────────────\n\n"
        f"📊 **RESUMO DA SESSÃO:**\n"
        f"• Total de Operações: `{total_trades}`\n"
        f"• Vitórias (Take Profit): `🟢 {vitorias}`\n"
        f"• Derrotas (Stop Loss): `🔴 {derrotas}`\n"
        f"• Taxa de Assertividade: `{winrate:.1f}%`\n"
        f"• Resultado Financeiro: {status_emoji} **${lucro_total:+.2f} USDT**\n\n"
        f"📝 **DETALHAMENTO DOS TRADES:**\n"
    )
    
    for idx, trade in enumerate(HISTORICO_HOJE, 1):
        icon = "✅" if trade["result"] == "PROFIT" else "❌"
        texto += f"{idx}. {icon} **{trade['symbol']}** ({trade['side']}) → `{trade['pnl']}` (${trade['lucro_usd']:+.2f})\n"
        
    texto += "\n_Relatório gerado automaticamente pelo bot._"
    return texto

# ==============================================================================
# 5. HANDLERS DOS COMANDOS (/start, /posicoes, /relatorio, /sinais, /ajuda)
# ==============================================================================
@bot.message_handler(commands=['start'])
def command_start(message):
    texto = (
        "🤖 **PAINEL DE TRADING PROFISSIONAL**\n\n"
        "Sistema operacional ativo e conectado!\n"
        "Selecione uma ação no menu abaixo:"
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown", reply_markup=criar_menu_principal())

@bot.message_handler(commands=['posicoes'])
def command_posicoes(message):
    exibir_posicoes(message.chat.id)

@bot.message_handler(commands=['relatorio'])
def command_relatorio(message):
    texto = gerar_texto_relatorio()
    bot.send_message(message.chat.id, texto, parse_mode="Markdown", reply_markup=criar_menu_principal())

@bot.message_handler(commands=['sinais'])
def command_sinais(message):
    exibir_sinais(message.chat.id)

@bot.message_handler(commands=['ajuda'])
def command_ajuda(message):
    texto = (
        "❓ **AJUDA & COMANDOS**\n\n"
        "• `/start` - Abre o painel interativo\n"
        "• `/posicoes` - Consulta operações abertas\n"
        "• `/relatorio` - Exibe o relatório de performance do dia\n"
        "• `/sinais` - Mostra os últimos alertas do sistema"
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

# ==============================================================================
# 6. HANDLER DE BOTÕES (CALLBACK QUERIES)
# ==============================================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data == "ver_posicoes":
        exibir_posicoes(chat_id)
        bot.answer_callback_query(call.id, "Posições carregadas!")

    elif call.data == "ver_relatorio":
        texto = gerar_texto_relatorio()
        bot.send_message(chat_id, texto, parse_mode="Markdown", reply_markup=criar_menu_principal())
        bot.answer_callback_query(call.id, "Relatório Diário Gerado!")

    elif call.data == "ver_sinais":
        exibir_sinais(chat_id)
        bot.answer_callback_query(call.id, "Sinais carregados!")

    elif call.data == "abrir_ordem":
        bot.send_message(chat_id, "⚡ **ORDEM RÁPIDA**\n\nEnvie o comando no formato:\n`COMPRA BTCUSDT 0.01` ou `VENDA ETHUSDT 0.1`", parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    elif call.data == "fechar_ordem":
        if not POSICOES_ABERTAS:
            bot.send_message(chat_id, "ℹ️ Nenhuma posição aberta para fechar no momento.")
        else:
            bot.send_message(chat_id, "🎯 **Selecione qual posição deseja fechar:**", reply_markup=criar_menu_fechar_posicoes())
        bot.answer_callback_query(call.id)

    elif call.data == "refresh_painel":
        texto = "🔄 **Painel Atualizado com Sucesso!**\nEscolha uma opção abaixo:"
        try:
            bot.edit_message_text(texto, chat_id, message_id, parse_mode="Markdown", reply_markup=criar_menu_principal())
        except Exception:
            bot.send_message(chat_id, texto, parse_mode="Markdown", reply_markup=criar_menu_principal())
        bot.answer_callback_query(call.id)

    elif call.data.startswith("close_pos_"):
        symbol_raw = call.data.replace("close_pos_", "").replace("_", "/")
        global POSICOES_ABERTAS
        POSICOES_ABERTAS = [p for p in POSICOES_ABERTAS if p["symbol"] != symbol_raw]
        
        bot.send_message(chat_id, f"✅ **Posição em {symbol_raw} encerrada com sucesso!**", parse_mode="Markdown")
        bot.answer_callback_query(call.id, f"{symbol_raw} Fechado!")

# ==============================================================================
# 7. FUNÇÕES AUXILIARES DE EXIBIÇÃO
# ==============================================================================
def exibir_posicoes(chat_id):
    if not POSICOES_ABERTAS:
        bot.send_message(chat_id, "📊 **POSIÇÕES:**\nNenhuma ordem aberta no momento.")
        return

    texto = "📊 **POSIÇÕES ABERTAS EM TEMPO REAL:**\n\n"
    for idx, pos in enumerate(POSICOES_ABERTAS, 1):
        emoji = "🟢" if pos["side"] == "LONG" else "🔴"
        texto += (
            f"{idx}. {emoji} **{pos['symbol']}** ({pos['side']})\n"
            f"   • Entrada: `${pos['entry']}`\n"
            f"   • Qtd: `{pos['qty']}`\n"
            f"   • PnL Atual: **{pos['pnl']}**\n\n"
        )
    bot.send_message(chat_id, texto, parse_mode="Markdown", reply_markup=criar_menu_principal())

def exibir_sinais(chat_id):
    texto = (
        "📡 **ÚLTIMO SINAL DETECTADO**\n\n"
        "🎯 **Ativo:** BTC/USDT\n"
        "📈 **Direção:** LONG (Compra)\n"
        "💵 **Entrada:** 64,150.00\n"
        "🎯 **Alvo 1:** 65,200.00\n"
        "🎯 **Alvo 2:** 66,500.00\n"
        "🛑 **Stop Loss:** 63,200.00\n\n"
        "_Status: Sinal ativo e monitorado._"
    )
    bot.send_message(chat_id, texto, parse_mode="Markdown", reply_markup=criar_menu_principal())

# ==============================================================================
# 8. EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    print("🤖 Iniciando Bot de Trading no Render...")
    inicializar_bot()
    print(f"🚀 Bot Ativo no Chat ID: {CHAT_ID}")
    
    # Executa o polling descartando requisições pendentes antigas
    bot.infinity_polling(skip_pending=True)
