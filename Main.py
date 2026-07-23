import os
import sys
import logging
import random
import time
import threading
from datetime import datetime
from threading import Thread
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

# ==============================================================================
# 1. SERVIDOR FLASK PARA KEEP-ALIVE (RENDER)
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot de Trading Automático 1M ativo!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ==============================================================================
# 2. CREDENCIAIS E BANCO DE DADOS EM MEMÓRIA
# ==============================================================================
TOKEN = "8822381506:AAEFA9KscOVs_xIGOV70RJeuLPggQNojYXg"
CHAT_ID = "-1003966783268"

bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- POSIÇÕES ABERTAS E HISTÓRICO ---
POSICOES_ABERTAS = []

HISTORICO_HOJE = [
    {"symbol": "SOL/USDT", "side": "LONG", "result": "PROFIT", "pnl": "+12.5%", "lucro_usd": 150.00},
    {"symbol": "BTC/USDT", "side": "SHORT", "result": "PROFIT", "pnl": "+5.2%", "lucro_usd": 80.50},
]

# ==============================================================================
# 3. MOTORES DE AUTOMAÇÃO (1 MINUTO TEMPORIZADOR)
# ==============================================================================
def processar_sinal_automatico(symbol, side, entry_price, target_chat_id):
    """Abre a posição automaticamente e inicia a contagem de 1 minuto (60s)."""
    global POSICOES_ABERTAS
    
    # 1. Adiciona a nova posição às posições abertas
    nova_posicao = {
        "symbol": symbol,
        "side": side,
        "entry": entry_price,
        "pnl": "0.0%",
        "qty": 1.0
    }
    POSICOES_ABERTAS.append(nova_posicao)
    
    # 2. Envia notificação imediata
    emoji_direcao = "🟢 LONG (Compra)" if side == "LONG" else "🔴 SHORT (Venda)"
    texto_abertura = (
        f"⚡ **SINAL DETECTADO & ORDEM ABERTA AUTOMATICAMENTE!**\n\n"
        f"🎯 **Ativo:** `{symbol}`\n"
        f"📊 **Direção:** {emoji_direcao}\n"
        f"💵 **Preço de Entrada:** `${entry_price}`\n"
        f"⏱️ **Tempo da Operação:** `1 Minuto`\n\n"
        f"_A ordem foi executada. Aguardando resultado da operação..._"
    )
    bot.send_message(target_chat_id, texto_abertura, parse_mode="Markdown")
    
    # 3. Dispara temporizador de 1 minuto (60 segundos) em segundo plano
    threading.Timer(60.0, finalizar_sinal_automatico, args=[symbol, side, entry_price, target_chat_id]).start()

def finalizar_sinal_automatico(symbol, side, entry_price, target_chat_id):
    """Executado automaticamente após 1 minuto para fechar e exibir o resultado."""
    global POSICOES_ABERTAS, HISTORICO_HOJE
    
    # Simula o resultado do mercado após 1m (70% de chance de Profit)
    is_profit = random.random() < 0.70
    pnl_percent = round(random.uniform(1.2, 5.5), 2) if is_profit else -round(random.uniform(1.0, 3.5), 2)
    lucro_usd = round((entry_price * (pnl_percent / 100)), 2)
    result_str = "PROFIT" if is_profit else "LOSS"
    
    # 1. Remove da lista de Posições Abertas
    POSICOES_ABERTAS = [p for p in POSICOES_ABERTAS if p["symbol"] != symbol]
    
    # 2. Registra no Histórico
    HISTORICO_HOJE.append({
        "symbol": symbol,
        "side": side,
        "result": result_str,
        "pnl": f"{pnl_percent:+.1f}%",
        "lucro_usd": lucro_usd
    })
    
    # 3. Envia o anúncio de resultado no chat
    status_emoji = "🟢 TAKEN PROFIT (Vitória!)" if is_profit else "🔴 STOP LOSS (Derrota)"
    texto_resultado = (
        f"🎯 **RESULTADO DO SINAL (Após 1m)**\n\n"
        f"💎 **Ativo:** `{symbol}` ({side})\n"
        f"📊 **Resultado:** {status_emoji}\n"
        f"📈 **PnL:** `{pnl_percent:+.2f}%`\n"
        f"💵 **Lucro/Prejuízo:** `${lucro_usd:+.2f} USDT`\n\n"
        f"_Operação encerrada e computada no relatório diário!_"
    )
    bot.send_message(target_chat_id, texto_resultado, parse_mode="Markdown", reply_markup=criar_menu_principal())

def motor_loop_estrategia():
    """Gera um sinal automático rápido a cada 60 a 120 segundos."""
    pares = ["CHZ/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT", "NEAR/USDT", "PEPE/USDT"]
    while True:
        # Aguarda entre 60 e 120 segundos (1 a 2 minutos) para o próximo sinal
        tempo_espera = random.randint(60, 120)
        time.sleep(tempo_espera)
        
        par = random.choice(pares)
        lado = random.choice(["LONG", "SHORT"])
        preco = round(random.uniform(0.08, 65000.0), 2)
        
        logging.info(f"🤖 Motor Rápido 1M gerou novo sinal para {par}")
        processar_sinal_automatico(par, lado, preco, CHAT_ID)

# ==============================================================================
# 4. INICIALIZAÇÃO DO BOT
# ==============================================================================
def inicializar_bot():
    try:
        bot.remove_webhook(drop_pending_updates=True)
        logging.info("✅ Webhook antigo limpo com sucesso!")
    except Exception as e:
        logging.error(f"⚠️ Erro ao remover webhook: {e}")

    try:
        bot.set_my_commands([
            BotCommand("start", "🚀 Painel Principal"),
            BotCommand("testar_sinal", "⚡ Simular Entrada Automática (1m)"),
            BotCommand("posicoes", "📊 Posições Abertas"),
            BotCommand("relatorio", "📈 Relatório Diário"),
            BotCommand("sinais", "📡 ÚLTIMOS SINAIS"),
            BotCommand("ajuda", "❓ Instruções e Suporte")
        ])
        logging.info("✅ Menu de comandos cadastrado!")
    except Exception as e:
        logging.error(f"⚠️ Erro ao cadastrar comandos: {e}")

# ==============================================================================
# 5. MENUS E TECLADOS INLINE
# ==============================================================================
def criar_menu_principal():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 Posições Abertas", callback_data="ver_posicoes"),
        InlineKeyboardButton("📡 ÚLTIMOS SINAIS", callback_data="ver_sinais")
    )
    markup.add(
        InlineKeyboardButton("📈 Relatório Diário", callback_data="ver_relatorio"),
        InlineKeyboardButton("⚡ Simular Sinal (1m)", callback_data="disparar_sinal_teste")
    )
    markup.add(
        InlineKeyboardButton("❌ Fechar Posição", callback_data="fechar_ordem"),
        InlineKeyboardButton("🔄 Atualizar Painel", callback_data="refresh_painel")
    )
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

def gerar_texto_relatorio():
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    total_trades = len(HISTORICO_HOJE)
    vitorias = sum(1 for t in HISTORICO_HOJE if t["result"] == "PROFIT")
    derrotas = sum(1 for t in HISTORICO_HOJE if t["result"] == "LOSS")
    winrate = (vitorias / total_trades * 100) if total_trades > 0 else 0
    lucro_total = sum(t["lucro_usd"] for t in HISTORICO_HOJE)
    status_emoji = "🟢" if lucro_total >= 0 else "🔴"
    
    texto = (
        f"📈 **RELATÓRIO DIÁRIO DE OPERAÇÕES (1M)**\n"
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
# 6. HANDLERS DOS COMANDOS
# ==============================================================================
@bot.message_handler(commands=['start'])
def command_start(message):
    bot.send_message(message.chat.id, "🤖 **PAINEL DE TRADING AUTOMÁTICO (1M)**\n\nSistema conectado e rodando em M1!", parse_mode="Markdown", reply_markup=criar_menu_principal())

@bot.message_handler(commands=['testar_sinal'])
def command_testar_sinal(message):
    pares = ["CHZ/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT"]
    par = random.choice(pares)
    lado = random.choice(["LONG", "SHORT"])
    preco = round(random.uniform(0.1, 3500.0), 2)
    
    processar_sinal_automatico(par, lado, preco, message.chat.id)

@bot.message_handler(commands=['posicoes'])
def command_posicoes(message):
    exibir_posicoes(message.chat.id)

@bot.message_handler(commands=['relatorio'])
def command_relatorio(message):
    bot.send_message(message.chat.id, gerar_texto_relatorio(), parse_mode="Markdown", reply_markup=criar_menu_principal())

@bot.message_handler(commands=['sinais'])
def command_sinais(message):
    exibir_sinais(message.chat.id)

@bot.message_handler(commands=['ajuda'])
def command_ajuda(message):
    texto = "❓ **COMANDOS DISPONÍVEIS:**\n\n• `/start` - Painel Principal\n• `/testar_sinal` - Abre um sinal automático de 1 min\n• `/posicoes` - Consulta posições abertas\n• `/relatorio` - Mostra a performance do dia"
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

# ==============================================================================
# 7. HANDLER DE BOTÕES
# ==============================================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    global POSICOES_ABERTAS
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data == "ver_posicoes":
        exibir_posicoes(chat_id)
        bot.answer_callback_query(call.id)

    elif call.data == "ver_relatorio":
        bot.send_message(chat_id, gerar_texto_relatorio(), parse_mode="Markdown", reply_markup=criar_menu_principal())
        bot.answer_callback_query(call.id)

    elif call.data == "disparar_sinal_teste":
        pares = ["CHZ/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT"]
        par = random.choice(pares)
        lado = random.choice(["LONG", "SHORT"])
        preco = round(random.uniform(0.1, 3500.0), 2)
        
        bot.answer_callback_query(call.id, "Sinal M1 gerado!")
        processar_sinal_automatico(par, lado, preco, chat_id)

    elif call.data == "ver_sinais":
        exibir_sinais(chat_id)
        bot.answer_callback_query(call.id)

    elif call.data == "fechar_ordem":
        if not POSICOES_ABERTAS:
            bot.send_message(chat_id, "ℹ️ Nenhuma posição aberta para fechar.")
        else:
            bot.send_message(chat_id, "🎯 **Selecione a posição que deseja encerrar:**", reply_markup=criar_menu_fechar_posicoes())
        bot.answer_callback_query(call.id)

    elif call.data == "refresh_painel":
        try:
            bot.edit_message_text("🔄 **Painel Atualizado!**", chat_id, message_id, parse_mode="Markdown", reply_markup=criar_menu_principal())
        except Exception:
            bot.send_message(chat_id, "🔄 **Painel Atualizado!**", parse_mode="Markdown", reply_markup=criar_menu_principal())
        bot.answer_callback_query(call.id)

    elif call.data.startswith("close_pos_"):
        symbol_raw = call.data.replace("close_pos_", "").replace("_", "/")
        POSICOES_ABERTAS = [p for p in POSICOES_ABERTAS if p["symbol"] != symbol_raw]
        bot.send_message(chat_id, f"✅ **Posição em {symbol_raw} encerrada manualmente!**", parse_mode="Markdown")
        bot.answer_callback_query(call.id)

def exibir_posicoes(chat_id):
    if not POSICOES_ABERTAS:
        bot.send_message(chat_id, "📊 **POSIÇÕES:**\nNenhuma ordem aberta no momento.")
        return
    texto = f"📊 **POSIÇÕES ABERTAS ({len(POSICOES_ABERTAS)}):**\n\n"
    for idx, pos in enumerate(POSICOES_ABERTAS, 1):
        emoji = "🟢" if pos["side"] == "LONG" else "🔴"
        texto += f"{idx}. {emoji} **{pos['symbol']}** ({pos['side']})\n   • Entrada: `${pos['entry']}` | Qtd: `{pos['qty']}`\n   • PnL: **{pos['pnl']}**\n\n"
    bot.send_message(chat_id, texto, parse_mode="Markdown", reply_markup=criar_menu_principal())

def exibir_sinais(chat_id):
    texto = "📡 **SISTEMA DE MONITORAMENTO DE SINAIS M1 ATIVO**\n\nO bot está gerando sinais automáticos em tempo real ou você pode clicar em **⚡ Simular Sinal (1m)** no menu!"
    bot.send_message(chat_id, texto, parse_mode="Markdown", reply_markup=criar_menu_principal())

# ==============================================================================
# 8. EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    print("🤖 Iniciando Servidor Keep-Alive (Flask)...")
    keep_alive()
    
    print("🤖 Iniciando Bot de Trading Automático 1M no Render...")
    inicializar_bot()
    
    # Inicia o motor autônomo de alta frequência
    t_motor = Thread(target=motor_loop_estrategia)
    t_motor.daemon = True
    t_motor.start()
    
    # Inicia o bot no Telegram
    bot.infinity_polling(skip_pending=True)
