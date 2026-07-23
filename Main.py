import ccxt
import pandas as pd
import requests
import time
from datetime import datetime

# ==========================================
# CONFIGURAÇÕES DO TELEGRAM
# ==========================================
TOKEN = '8822381506:AAEFA9KscOVs_xIGOV70RJeuLPggQNojYXg'
CHAT_ID = '-1003966783268'

# ==========================================
# CONFIGURAÇÕES DO BOT E MERCADO PERPÉTUO
# ==========================================
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
TIMEFRAME = '1m'
TS_PCT = 1.5

exchange = ccxt.binanceusdm()

posicoes = {
    symbol: {
        'ativa': False,
        'tipo': None,
        'entrada': 0.0,
        'ts_price': 0.0
    } for symbol in SYMBOLS
}

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem ao Telegram: {e}")

def calcular_indicadores(df):
    df['ema_fast'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=21, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    ema_gain = gain.ewm(com=13, adjust=False).mean()
    ema_loss = loss.ewm(com=13, adjust=False).mean()
    rs = ema_gain / ema_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def analisar_e_executar():
    for symbol in SYMBOLS:
        try:
            bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            df = calcular_indicadores(df)

            ultima_fechada = df.iloc[-2]
            penultima = df.iloc[-3]
            preco_atual = df.iloc[-1]['close']
            high_atual = df.iloc[-1]['high']
            low_atual = df.iloc[-1]['low']

            pos = posicoes[symbol]
            hashtag = symbol.replace('/', '').replace(':USDT', '')

            if pos['ativa']:
                if pos['tipo'] == 'BUY':
                    novo_ts = high_atual * (1 - (TS_PCT / 100))
                    pos['ts_price'] = max(pos['ts_price'], novo_ts)

                    if low_atual <= pos['ts_price']:
                        pnl = ((pos['ts_price'] - pos['entrada']) / pos['entrada']) * 100
                        resultado_str = "<b>WIN</b> 🎯" if pnl > 0 else "<b>LOSS</b> ❌"
                        cor_emoji = "🟢" if pnl > 0 else "🔴"

                        msg_resultado = f"""
{cor_emoji} <b>OPERAÇÃO FINALIZADA</b> | #{hashtag}

📌 <b>Direção:</b> LONG (CALL)
🏁 <b>Resultado:</b> {resultado_str} ({pnl:+.2f}%)
📥 <b>Preço Entrada:</b> ${pos['entrada']:.4f}
📤 <b>Saída (TS):</b> ${pos['ts_price']:.4f}

⏱ <i>Scalper M1 Perpétuo</i>
"""
                        enviar_telegram(msg_resultado)
                        pos['ativa'] = False

                elif pos['tipo'] == 'SELL':
                    novo_ts = low_atual * (1 + (TS_PCT / 100))
                    pos['ts_price'] = min(pos['ts_price'], novo_ts)

                    if high_atual >= pos['ts_price']:
                        pnl = ((pos['entrada'] - pos['ts_price']) / pos['entrada']) * 100
                        resultado_str = "<b>WIN</b> 🎯" if pnl > 0 else "<b>LOSS</b> ❌"
                        cor_emoji = "🟢" if pnl > 0 else "🔴"

                        msg_resultado = f"""
{cor_emoji} <b>OPERAÇÃO FINALIZADA</b> | #{hashtag}

📌 <b>Direção:</b> SHORT (PUT)
🏁 <b>Resultado:</b> {resultado_str} ({pnl:+.2f}%)
📥 <b>Preço Entrada:</b> ${pos['entrada']:.4f}
📤 <b>Saída (TS):</b> ${pos['ts_price']:.4f}

⏱ <i>Scalper M1 Perpétuo</i>
"""
                        enviar_telegram(msg_resultado)
                        pos['ativa'] = False

            else:
                cruzou_alta = (penultima['ema_fast'] <= penultima['ema_slow']) and (ultima_fechada['ema_fast'] > ultima_fechada['ema_slow'])
                cruzou_baixa = (penultima['ema_fast'] >= penultima['ema_slow']) and (ultima_fechada['ema_fast'] < ultima_fechada['ema_slow'])

                if cruzou_alta and ultima_fechada['rsi'] > 55:
                    pos['ativa'] = True
                    pos['tipo'] = 'BUY'
                    pos['entrada'] = preco_atual
                    pos['ts_price'] = preco_atual * (1 - (TS_PCT / 100))

                    msg_sinal = f"""
⚡ <b>SINAL DE TRADING</b> | #{hashtag}

📊 <b>Direção:</b> 🟢 <b>LONG (CALL)</b>
💵 <b>Entrada:</b> ${preco_atual:.4f}
🛡 <b>Trailing Stop:</b> ${pos['ts_price']:.4f} (1.5%)

📈 <b>Análise Técnica:</b>
• EMA 9x21: Cruzamento de Alta
• RSI (14): {ultima_fechada['rsi']:.1f} (Força Compradora)
• Tempo Gráfico: M1 Perpétuo
"""
                    enviar_telegram(msg_sinal)

                elif cruzou_baixa and ultima_fechada['rsi'] < 45:
                    pos['ativa'] = True
                    pos['tipo'] = 'SELL'
                    pos['entrada'] = preco_atual
                    pos['ts_price'] = preco_atual * (1 + (TS_PCT / 100))

                    msg_sinal = f"""
⚡ <b>SINAL DE TRADING</b> | #{hashtag}

📊 <b>Direção:</b> 🔴 <b>SHORT (PUT)</b>
💵 <b>Entrada:</b> ${preco_atual:.4f}
🛡 <b>Trailing Stop:</b> ${pos['ts_price']:.4f} (1.5%)

📉 <b>Análise Técnica:</b>
• EMA 9x21: Cruzamento de Baixa
• RSI (14): {ultima_fechada['rsi']:.1f} (Força Vendedora)
• Tempo Gráfico: M1 Perpétuo
"""
                    enviar_telegram(msg_sinal)

        except Exception as e:
            print(f"Erro ao processar {symbol}: {e}")

print("==========================================")
print("Bot Scalper M1 Perpétuo Iniciado!")
print("==========================================")

enviar_telegram("🚀 <b>SISTEMA DE SINAIS M1 PERPÉTUO CONECTADO</b>\n\nMonitorando BTC, ETH e SOL em tempo real...")

while True:
    analisar_e_executar()
    time.sleep(10)
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem ao Telegram: {e}")

def calcular_indicadores(df):
    # Cálculo das EMAs (9 e 21) usando Pandas nativo
    df['ema_fast'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # Cálculo do RSI (14) usando Pandas nativo
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    ema_gain = gain.ewm(com=13, adjust=False).mean()
    ema_loss = loss.ewm(com=13, adjust=False).mean()
    rs = ema_gain / ema_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def analisar_e_executar():
    for symbol in SYMBOLS:
        try:
            bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            df = calcular_indicadores(df)

            ultima_fechada = df.iloc[-2]
            penultima = df.iloc[-3]
            preco_atual = df.iloc[-1]['close']
            high_atual = df.iloc[-1]['high']
            low_atual = df.iloc[-1]['low']

            pos = posicoes[symbol]
            hashtag = symbol.replace('/', '').replace(':USDT', '')

            # Gerenciamento de Posições (Win / Loss)
            if pos['ativa']:
                if pos['tipo'] == 'BUY':
                    novo_ts = high_atual * (1 - (TS_PCT / 100))
                    pos['ts_price'] = max(pos['ts_price'], novo_ts)

                    if low_atual <= pos['ts_price']:
                        pnl = ((pos['ts_price'] - pos['entrada']) / pos['entrada']) * 100
                        resultado_str = "<b>WIN</b> 🎯" if pnl > 0 else "<b>LOSS</b> ❌"
                        cor_emoji = "🟢" if pnl > 0 else "🔴"

                        msg_resultado = f"""
{cor_emoji} <b>OPERAÇÃO FINALIZADA</b> | #{hashtag}

📌 <b>Direção:</b> LONG (CALL)
🏁 <b>Resultado:</b> {resultado_str} ({pnl:+.2f}%)
📥 <b>Preço Entrada:</b> ${pos['entrada']:.4f}
📤 <b>Saída (TS):</b> ${pos['ts_price']:.4f}

⏱ <i>Scalper M1 Perpétuo</i>
"""
                        enviar_telegram(msg_resultado)
                        pos['ativa'] = False

                elif pos['tipo'] == 'SELL':
                    novo_ts = low_atual * (1 + (TS_PCT / 100))
                    pos['ts_price'] = min(pos['ts_price'], novo_ts)

                    if high_atual >= pos['ts_price']:
                        pnl = ((pos['entrada'] - pos['ts_price']) / pos['entrada']) * 100
                        resultado_str = "<b>WIN</b> 🎯" if pnl > 0 else "<b>LOSS</b> ❌"
                        cor_emoji = "🟢" if pnl > 0 else "🔴"

                        msg_resultado = f"""
{cor_emoji} <b>OPERAÇÃO FINALIZADA</b> | #{hashtag}

📌 <b>Direção:</b> SHORT (PUT)
🏁 <b>Resultado:</b> {resultado_str} ({pnl:+.2f}%)
📥 <b>Preço Entrada:</b> ${pos['entrada']:.4f}
📤 <b>Saída (TS):</b> ${pos['ts_price']:.4f}

⏱ <i>Scalper M1 Perpétuo</i>
"""
                        enviar_telegram(msg_resultado)
                        pos['ativa'] = False

            else:
                cruzou_alta = (penultima['ema_fast'] <= penultima['ema_slow']) and (ultima_fechada['ema_fast'] > ultima_fechada['ema_slow'])
                cruzou_baixa = (penultima['ema_fast'] >= penultima['ema_slow']) and (ultima_fechada['ema_fast'] < ultima_fechada['ema_slow'])

                if cruzou_alta and ultima_fechada['rsi'] > 55:
                    pos['ativa'] = True
                    pos['tipo'] = 'BUY'
                    pos['entrada'] = preco_atual
                    pos['ts_price'] = preco_atual * (1 - (TS_PCT / 100))

                    msg_sinal = f"""
⚡ <b>SINAL DE TRADING</b> | #{hashtag}

📊 <b>Direção:</b> 🟢 <b>LONG (CALL)</b>
💵 <b>Entrada:</b> ${preco_atual:.4f}
🛡 <b>Trailing Stop:</b> ${pos['ts_price']:.4f} (1.5%)

📈 <b>Análise Técnica:</b>
• EMA 9x21: Cruzamento de Alta
• RSI (14): {ultima_fechada['rsi']:.1f} (Força Compradora)
• Tempo Gráfico: M1 Perpétuo
"""
                    enviar_telegram(msg_sinal)

                elif cruzou_baixa and ultima_fechada['rsi'] < 45:
                    pos['ativa'] = True
                    pos['tipo'] = 'SELL'
                    pos['entrada'] = preco_atual
                    pos['ts_price'] = preco_atual * (1 + (TS_PCT / 100))

                    msg_sinal = f"""
⚡ <b>SINAL DE TRADING</b> | #{hashtag}

📊 <b>Direção:</b> 🔴 <b>SHORT (PUT)</b>
💵 <b>Entrada:</b> ${preco_atual:.4f}
🛡 <b>Trailing Stop:</b> ${pos['ts_price']:.4f} (1.5%)

📉 <b>Análise Técnica:</b>
• EMA 9x21: Cruzamento de Baixa
• RSI (14): {ultima_fechada['rsi']:.1f} (Força Vendedora)
• Tempo Gráfico: M1 Perpétuo
"""
                    enviar_telegram(msg_sinal)

        except Exception as e:
            print(f"Erro ao processar {symbol}: {e}")

print("==========================================")
print("Bot Scalper M1 Perpétuo Iniciado!")
print("==========================================")

enviar_telegram("🚀 <b>SISTEMA DE SINAIS M1 PERPÉTUO CONECTADO</b>\n\nMonitorando BTC, ETH e SOL em tempo real...")

while True:
    analisar_e_executar()
    time.sleep(10)
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erro ao enviar mensagem ao Telegram: {e}")

def analisar_e_executar():
    for symbol in SYMBOLS:
        try:
            # Busca as últimas velas do gráfico de 1 minuto
            bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            # Indicadores técnicos
            df['ema_fast'] = ta.ema(df['close'], length=9)
            df['ema_slow'] = ta.ema(df['close'], length=21)
            df['rsi'] = ta.rsi(df['close'], length=14)

            ultima_fechada = df.iloc[-2]
            penultima = df.iloc[-3]
            preco_atual = df.iloc[-1]['close']
            high_atual = df.iloc[-1]['high']
            low_atual = df.iloc[-1]['low']

            pos = posicoes[symbol]
            hashtag = symbol.replace('/', '').replace(':USDT', '')

            # ==========================================
            # 1. GERENCIAMENTO DE POSIÇÃO ABERTA (WIN / LOSS)
            # ==========================================
            if pos['ativa']:
                # Se for COMPRA (LONG)
                if pos['tipo'] == 'BUY':
                    novo_ts = high_atual * (1 - (TS_PCT / 100))
                    pos['ts_price'] = max(pos['ts_price'], novo_ts)

                    # Saída atingida
                    if low_atual <= pos['ts_price']:
                        pnl = ((pos['ts_price'] - pos['entrada']) / pos['entrada']) * 100
                        resultado_str = "<b>WIN</b> 🎯" if pnl > 0 else "<b>LOSS</b> ❌"
                        cor_emoji = "🟢" if pnl > 0 else "🔴"

                        msg_resultado = f"""
{cor_emoji} <b>OPERAÇÃO FINALIZADA</b> | #{hashtag}

📌 <b>Direção:</b> LONG (CALL)
🏁 <b>Resultado:</b> {resultado_str} ({pnl:+.2f}%)
📥 <b>Preço Entrada:</b> ${pos['entrada']:.4f}
📤 <b>Saída (TS):</b> ${pos['ts_price']:.4f}

⏱ <i>Scalper M1 Perpétuo</i>
"""
                        enviar_telegram(msg_resultado)
                        pos['ativa'] = False

                # Se for VENDA (SHORT)
                elif pos['tipo'] == 'SELL':
                    novo_ts = low_atual * (1 + (TS_PCT / 100))
                    pos['ts_price'] = min(pos['ts_price'], novo_ts)

                    # Saída atingida
                    if high_atual >= pos['ts_price']:
                        pnl = ((pos['entrada'] - pos['ts_price']) / pos['entrada']) * 100
                        resultado_str = "<b>WIN</b> 🎯" if pnl > 0 else "<b>LOSS</b> ❌"
                        cor_emoji = "🟢" if pnl > 0 else "🔴"

                        msg_resultado = f"""
{cor_emoji} <b>OPERAÇÃO FINALIZADA</b> | #{hashtag}

📌 <b>Direção:</b> SHORT (PUT)
🏁 <b>Resultado:</b> {resultado_str} ({pnl:+.2f}%)
📥 <b>Preço Entrada:</b> ${pos['entrada']:.4f}
📤 <b>Saída (TS):</b> ${pos['ts_price']:.4f}

⏱ <i>Scalper M1 Perpétuo</i>
"""
                        enviar_telegram(msg_resultado)
                        pos['ativa'] = False

            # ==========================================
            # 2. IDENTIFICAÇÃO DE NOVOS SINAIS
            # ==========================================
            else:
                cruzou_alta = (penultima['ema_fast'] <= penultima['ema_slow']) and (ultima_fechada['ema_fast'] > ultima_fechada['ema_slow'])
                cruzou_baixa = (penultima['ema_fast'] >= penultima['ema_slow']) and (ultima_fechada['ema_fast'] < ultima_fechada['ema_slow'])

                # Sinal de Compra (LONG)
                if cruzou_alta and ultima_fechada['rsi'] > 55:
                    pos['ativa'] = True
                    pos['tipo'] = 'BUY'
                    pos['entrada'] = preco_atual
                    pos['ts_price'] = preco_atual * (1 - (TS_PCT / 100))

                    msg_sinal = f"""
⚡ <b>SINAL DE TRADING</b> | #{hashtag}

📊 <b>Direção:</b> 🟢 <b>LONG (CALL)</b>
💵 <b>Entrada:</b> ${preco_atual:.4f}
🛡 <b>Trailing Stop:</b> ${pos['ts_price']:.4f} (1.5%)

📈 <b>Análise Técnica:</b>
• EMA 9x21: Cruzamento de Alta
• RSI (14): {ultima_fechada['rsi']:.1f} (Força Compradora)
• Tempo Gráfico: M1 Perpétuo
"""
                    enviar_telegram(msg_sinal)

                # Sinal de Venda (SHORT)
                elif cruzou_baixa and ultima_fechada['rsi'] < 45:
                    pos['ativa'] = True
                    pos['tipo'] = 'SELL'
                    pos['entrada'] = preco_atual
                    pos['ts_price'] = preco_atual * (1 + (TS_PCT / 100))

                    msg_sinal = f"""
⚡ <b>SINAL DE TRADING</b> | #{hashtag}

📊 <b>Direção:</b> 🔴 <b>SHORT (PUT)</b>
💵 <b>Entrada:</b> ${preco_atual:.4f}
🛡 <b>Trailing Stop:</b> ${pos['ts_price']:.4f} (1.5%)

📉 <b>Análise Técnica:</b>
• EMA 9x21: Cruzamento de Baixa
• RSI (14): {ultima_fechada['rsi']:.1f} (Força Vendedora)
• Tempo Gráfico: M1 Perpétuo
"""
                    enviar_telegram(msg_sinal)

        except Exception as e:
            print(f"Erro ao processar {symbol}: {e}")

# ==========================================
# EXECUÇÃO CONTÍNUA
# ==========================================
print("==========================================")
print("Bot Scalper M1 Perpétuo Iniciado!")
print("==========================================")

enviar_telegram("🚀 <b>SISTEMA DE SINAIS M1 PERPÉTUO CONECTADO</b>\n\nMonitorando BTC, ETH e SOL em tempo real...")

while True:
    analisar_e_executar()
    time.sleep(10)  # Checa a cada 10 segundos para responder rápido no M1
