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
import ccxt

# ==============================================================================
# 1. SERVIDOR FLASK PARA KEEP-ALIVE (RENDER)
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot de Trading Automático 1M (Binance Real) ativo!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ==============================================================================
# 2. CREDENCIAIS E API PÚBLICA DA BINANCE
# ==============================================================================
TOKEN = "8822381506:AAEFA9KscOVs_xIGOV70RJeuLPggQNojYXg"
CHAT_ID = "-1003966783268"

bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Conexão PÚBLICA com a Binance (não exige chave nem login)
binance = ccxt.binance({'enableRateLimit': True})

# --- POSIÇÕES ABERTAS E HISTÓRICO ---
POSICOES_ABERTAS = []
HISTORICO_HOJE = []

def obter_preco_real_binance(symbol):
    """Busca o preço exato e atualizado diretamente na API pública da Binance."""
    try:
        ticker = binance.fetch_ticker(symbol)
        return float(ticker['last'])
    except Exception as e:
        logging.error(f"⚠️ Erro ao puxar preço público da Binance para {symbol}: {e}")
        return None

def formatar_preco(valor):
    """Formata números para o padrão R$/USDT (ex: 64.000,00 ou 0,0854)."""
    if valor is None:
        return "0,00"
    if valor >= 1.0:
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        return f"{valor:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ==============================================================================
# 3. MOTORES DE AUTOMAÇÃO (1 MINUTO COM DADOS REAIS)
# ==============================================================================
def processar_sinal_automatico(symbol, side, target_chat_id):
    """Obtém preço real da Binance, abre a ordem e programa fechamento em 60s."""
    global POSICOES_ABERTAS
    
    entry_price = obter_preco_real_binance(symbol)
    if not entry_price:
        logging.error(f"Falha ao buscar cotação para {symbol}. Cancelando sinal.")
        return

    symbol_par = symbol.replace("/", "-")
    preco_formatado = formatar_preco(entry_price)
    
    # 1. Adiciona a nova posição às posições abertas
    nova_posicao = {
        "symbol": symbol,
        "side": side,
        "entry": entry_price,
        "pnl": "0.0%",
        "qty": 1.0
    }
    POSICOES_ABERTAS.append(nova_posicao)
    
    # 2. Envia notificação no Telegram
    emoji_direcao = "🟢 LONG (Compra)" if side == "LONG" else "🔴 SHORT (Venda)"
    texto_abertura = (
        f"⚡ **SINAL DETECTADO & ORDEM ABERTA AUTOMATICAMENTE!**\n\n"
        f"📌 **{symbol_par} Entrada:** `${preco_formatado}`\n"
        f"🎯 **Ativo:** `{symbol}`\n"
        f"📊 **Direção:** {emoji_direcao}\n"
        f"⏱️ **Tempo da Operação:** `1 Minuto`\n\n"
        f"_Preço em tempo real puxado diretamente da Binance._"
    )
    bot.send_message(target_chat_id, texto_abertura, parse_mode="Markdown")
    
    # 3. Temporizador exato de 60 segundos em segundo plano
    threading.Timer(60.0, finalizar_sinal_automatico, args=[symbol, side, entry_price, target_chat_id]).start()

def finalizar_sinal_automatico(symbol, side, entry_price, target_chat_id):
    """Executado após 60s: Puxa o preço real atualizado da Binance e calcula o PnL real."""
    global POSICOES_ABERTAS, HISTORICO_HOJE
    
    exit_price = obter_preco_real_binance(symbol)
    if not exit_price:
        exit_price = entry_price # Fallback caso haja oscilação de conexão
        
    symbol_par = symbol.replace("/", "-")
    preco_entrada_fmt = formatar_preco(entry_price)
    preco_saida_fmt = formatar_preco(exit_price)
    
    # Calcula variação percentual real do mercado
    if side == "LONG":
        pnl_percent = ((exit_price - entry_price) / entry_price) * 100
    else:
        pnl_percent = ((entry_price - exit_price) / entry_price) * 100
        
    is_profit = pnl_percent > 0
    lucro_usd = round(pnl_percent * 10, 2) # Simulação de $100 de margem a 10x
    result_str = "PROFIT" if is_profit else "LOSS"
    
    # 1. Remove da lista de Posições Abertas
    POSICOES_ABERTAS = [p for p in POSICOES_ABERTAS if p["symbol"] != symbol]
    
    # 2. Registra no Histórico
    HISTORICO_HOJE.append({
        "symbol": symbol,
        "side": side,
        "result": result_str,
        "pnl": f"{pnl_percent:+.2f}%",
        "lucro_usd": lucro_usd
    })
    
    # 3. Envia mensagem de encerramento no Telegram
    status_emoji = "🟢 TAKEN PROFIT (Vitória!)" if is_profit else "🔴 STOP LOSS (Derrota)"
    texto_resultado = (
        f"🎯 **RESULTADO DO SINAL (Após 1m)**\n\n"
        f"📌 **{symbol_par} Entrada:** `${preco_entrada_fmt}`\n"
        f"🏁 **{symbol_par} Saída:** `${preco_saida_fmt}`\n"
        f"💎 **Ativo:** `{symbol}` ({side})\n"
        f"📊 **Resultado:** {status_emoji}\n"
        f"📈 **PnL Real:** `{pnl_percent:+.2f}%`\n"
        f"💵 **Resultado Estimado:** `${lucro_usd:+.2f} USDT`\n\n"
        f"_Operação encerrada e computada no relatório diário!_"
    )
    bot.send_message(target_chat_id, texto_resultado, parse_mode="Markdown", reply_markup=criar_menu_principal())

def motor_loop_estrategia():
    """Gera sinais automáticos em M1 consultando a Binance."""
    pares = ["CHZ/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT", "DOGE/USDT, "OP/USDT", "BNB/USDT"]    
    # Aguarda 10 segundos ao ligar o bot
    time.sleep(10)
    
    while True:
        par = random.choice(pares)
        lado = random.choice(["LONG", "SHORT"])
        
        logging.info(f"🤖 Motor 1M gerou novo sinal real da Binance para {par}")
        processar_sinal_automatico(par, lado, CHAT_ID)
        
        # Aguarda de 60 a 90 segundos para o próximo sinal
        tempo_espera = random.randint(60, 90)
        time.sleep(tempo_espera)

# ==============================================================================
# 4. INICIALIZAÇÃO DO BOT
# ==============================================================================
def inicializar_bot():
    try:
        bot.delete_webhook(drop_pending_updates=True)
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
        
        bot.send_message(CHAT_ID, "🚀 **BOT CONECTADO À BINANCE (M1) E OPERANDO!**\n\n_O motor autônomo está ativo e buscando preços públicos da Binance em tempo real._", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"⚠️ Erro ao inicializar bot: {e}")

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
        f"📈 **RELATÓRIO DIÁRIO DE OPERAÇÕES (1M BINANCE)**\n"
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
    texto += "\n_Relatório gerado com cotações reais da Binance._"
    return texto

# ==============================================================================
# 6. HANDLERS DOS COMANDOS
# ==============================================================================
@bot.message_handler(commands=['start'])
def command_start(message):
    bot.send_message(message.chat.id, "🤖 **PAINEL DE TRADING AUTOMÁTICO (1M BINANCE)**\n\nConectado e obtendo cotações em tempo real!", parse_mode="Markdown", reply_markup=criar_menu_principal())

@bot.message_handler(commands=['testar_sinal'])
def command_testar_sinal(message):
    pares = ["CHZ/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT"]
    par = random.choice(pares)
    lado = random.choice(["LONG", "SHORT"])
    
    processar_sinal_automatico(par, lado, message.chat.id)

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
    texto = "❓ **COMANDOS DISPONÍVEIS:**\n\n• `/start` - Painel Principal\n• `/testar_sinal` - Abre um sinal automático com preço real Binance\n• `/posicoes` - Consulta posições abertas\n• `/relatorio` - Performance do dia"
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
        
        bot.answer_callback_query(call.id, "Buscando preço Binance e enviando...")
        processar_sinal_automatico(par, lado, chat_id)

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
        preco_fmt = formatar_preco(pos['entry'])
        texto += f"{idx}. {emoji} **{pos['symbol']}** ({pos['side']})\n   • Entrada: `${preco_fmt}` | Qtd: `{pos['qty']}`\n   • PnL: **{pos['pnl']}**\n\n"
    bot.send_message(chat_id, texto, parse_mode="Markdown", reply_markup=criar_menu_principal())

def exibir_sinais(chat_id):
    texto = "📡 **MONITORAMENTO DE SINAIS BINANCE M1 ATIVO**\n\nOs preços de entrada e saída são consultados diretamente na Binance!"
    bot.send_message(chat_id, texto, parse_mode="Markdown", reply_markup=criar_menu_principal())

# ==============================================================================
# 8. EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    print("🤖 Iniciando Servidor Keep-Alive (Flask)...")
    keep_alive()
    
    print("🤖 Iniciando Bot de Trading Automático 1M Binance no Render...")
    inicializar_bot()
    
    # Inicia o motor autônomo em segundo plano
    t_motor = Thread(target=motor_loop_estrategia)
    t_motor.daemon = True
    t_motor.start()
    
    # Inicia o polling no Telegram
    bot.infinity_polling(skip_pending=True)
