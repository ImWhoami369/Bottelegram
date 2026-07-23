import os
import sys
import logging
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from http.server import HTTPServer, BaseHTTPRequestHandler

# ======================================================
# 1. SERVIDOR DUMMY PARA O RENDER (FIX PORT SCAN)
# ======================================================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Scalper M1 (15 Ativos) Ativo!")

    def log_message(self, format, *args):
        return

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"--> Servidor HTTP iniciado na porta {port}.")
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ==============================================================================
# 1. CREDENCIAIS E CONFIGURAÇÕES
# ==============================================================================
TOKEN = "8822381506:AAEFA9KscOVs_xIGOV70RJeuLPggQNojYXg"
CHAT_ID = "-1003966783268"

bot = telebot.TeleBot(TOKEN)

# Logging no terminal/Render
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 15 ATIVOS FIXOS EM POSIÇÕES ABERTAS ---
POSICOES_ABERTAS = [
    {"symbol": "BTC/USDT", "side": "LONG", "entry": 64200.0, "pnl": "+4.2%", "qty": 0.05},
    {"symbol": "ETH/USDT", "side": "SHORT", "entry": 3450.0, "pnl": "-1.1%", "qty": 0.5},
    {"symbol": "SOL/USDT", "side": "LONG", "entry": 145.0, "pnl": "+8.5%", "qty": 10.0},
    {"symbol": "BNB/USDT", "side": "LONG", "entry": 580.0, "pnl": "+2.1%", "qty": 1.5},
    {"symbol": "XRP/USDT", "side": "SHORT", "entry": 0.55, "pnl": "-0.5%", "qty": 1000.0},
    {"symbol": "ADA/USDT", "side": "LONG", "entry": 0.42, "pnl": "+1.8%", "qty": 500.0},
    {"symbol": "DOGE/USDT", "side": "LONG", "entry": 0.12, "pnl": "+15.4%", "qty": 2500.0},
    {"symbol": "AVAX/USDT", "side": "SHORT", "entry": 28.5, "pnl": "+3.0%", "qty": 15.0},
    {"symbol": "LINK/USDT", "side": "LONG", "entry": 14.2, "pnl": "-2.4%", "qty": 30.0},
    {"symbol": "DOT/USDT", "side": "LONG", "entry": 6.8, "pnl": "+0.9%", "qty": 80.0},
    {"symbol": "NEAR/USDT", "side": "LONG", "entry": 5.1, "pnl": "+6.3%", "qty": 100.0},
    {"symbol": "MATIC/USDT", "side": "SHORT", "entry": 0.58, "pnl": "-1.8%", "qty": 400.0},
    {"symbol": "ATOM/USDT", "side": "LONG", "entry": 6.5, "pnl": "+1.2%", "qty": 50.0},
    {"symbol": "SUI/USDT", "side": "LONG", "entry": 1.15, "pnl": "+11.0%", "qty": 300.0},
    {"symbol": "CHZ/USDT", "side": "LONG", "entry": 0.08, "pnl": "+4.7%", "qty": 5000.0},
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
    global POSICOES_ABERTAS  # Correção do escopo global no topo do handler
    
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

    texto = f"📊 **POSIÇÕES ABERTAS ({len(POSICOES_ABERTAS)}):**\n\n"
    for idx, pos in enumerate(POSICOES_ABERTAS, 1):
        emoji = "🟢" if pos["side"] == "LONG" else "🔴"
        texto += (
            f"{idx}. {emoji} **{pos['symbol']}** ({pos['side']})\n"
            f"   • Entrada: `${pos['entry']}` | Qtd: `{pos['qty']}`\n"
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
