import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import ccxt
import pandas as pd
import requests

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

# ======================================================
# 2. CONFIGURAÇÕES DO TELEGRAM E LISTA DE 15 ATIVOS
# ======================================================
TOKEN = '8822381506:AAEFA9KscOVs_xIGOV70RJeuLPggQNojYXg'
CHAT_ID = '-1003966783268'

# 15 Ativos de Alta Volatilidade para Chuva de Sinais em M1
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'DOGE/USDT', 'XRP/USDT',
    'ADA/USDT', 'AVAX/USDT', 'LINK/USDT', 'NEAR/USDT', 'PEPE/USDT',
    'SHIB/USDT', 'SUI/USDT', 'BNB/USDT', 'OP/USDT', 'ARB/USDT'
]

TIMEFRAME = '1m'
TS_PCT = 1.0  # Trailing Stop de 1.0% para Scalper rápido

# Conexão Binance USD-M Futures
exchange = ccxt.binanceusdm({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

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
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

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
            bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=60)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df = calcular_indicadores(df)

            ultima_fechada = df.iloc[-2]
            penultima = df.iloc[-3]
            preco_atual = df.iloc[-1]['close']
            high_atual = df.iloc[-1]['high']
            low_atual = df.iloc[-1]['low']

            pos = posicoes[symbol]
            hashtag = symbol.replace('/', '').replace(':USDT', '')

            # GERENCIAMENTO DE POSIÇÃO (TRAILING STOP)
            if pos['ativa']:
                if pos['tipo'] == 'BUY':
                    novo_ts = high_atual * (1 - (TS_PCT / 100))
                    pos['ts_price'] = max(pos['ts_price'], novo_ts)

                    if low_atual <= pos['ts_price']:
                        pnl = ((pos['ts_price'] - pos['entrada']) / pos['entrada']) * 100
                        resultado_str = "<b>WIN</b> 🎯" if pnl > 0 else "<b>LOSS</b> ❌"
                        cor_emoji = "🟢" if pnl > 0 else "🔴"

                        msg_resultado = (
                            f"{cor_emoji} <b>OPERAÇÃO ENCERRADA M1</b> | #{hashtag}\n\n"
                            f"📌 <b>Tipo:</b> LONG\n"
                            f"🏁 <b>Resultado:</b> {resultado_str} ({pnl:+.2f}%)\n"
                            f"📥 <b>Entrada:</b> ${pos['entrada']:.6f}\n"
                            f"📤 <b>Saída:</b> ${pos['ts_price']:.6f}"
                        )
                        enviar_telegram(msg_resultado)
                        pos['ativa'] = False

                elif pos['tipo'] == 'SELL':
                    novo_ts = low_atual * (1 + (TS_PCT / 100))
                    pos['ts_price'] = min(pos['ts_price'], novo_ts)

                    if high_atual >= pos['ts_price']:
                        pnl = ((pos['entrada'] - pos['ts_price']) / pos['entrada']) * 100
                        resultado_str = "<b>WIN</b> 🎯" if pnl > 0 else "<b>LOSS</b> ❌"
                        cor_emoji = "🟢" if pnl > 0 else "🔴"

                        msg_resultado = (
                            f"{cor_emoji} <b>OPERAÇÃO ENCERRADA M1</b> | #{hashtag}\n\n"
                            f"📌 <b>Tipo:</b> SHORT\n"
                            f"🏁 <b>Resultado:</b> {resultado_str} ({pnl:+.2f}%)\n"
                            f"📥 <b>Entrada:</b> ${pos['entrada']:.6f}\n"
                            f"📤 <b>Saída:</b> ${pos['ts_price']:.6f}"
                        )
                        enviar_telegram(msg_resultado)
                        pos['ativa'] = False

            # GERAÇÃO DE NOVOS SINAIS (M1 SCALPER)
            else:
                cruzou_alta = (penultima['ema_fast'] <= penultima['ema_slow']) and (ultima_fechada['ema_fast'] > ultima_fechada['ema_slow'])
                cruzou_baixa = (penultima['ema_fast'] >= penultima['ema_slow']) and (ultima_fechada['ema_fast'] < ultima_fechada['ema_slow'])

                if cruzou_alta and ultima_fechada['rsi'] > 50:
                    pos['ativa'] = True
                    pos['tipo'] = 'BUY'
                    pos['entrada'] = preco_atual
                    pos['ts_price'] = preco_atual * (1 - (TS_PCT / 100))

                    msg_sinal = (
                        f"⚡ <b>SINAL M1 ULTRA SCALPER</b> | #{hashtag}\n\n"
                        f"📊 <b>Direção:</b> 🟢 <b>LONG (COMPRA)</b>\n"
                        f"💵 <b>Entrada:</b> ${preco_atual:.6f}\n"
                        f"🛡 <b>Trailing Stop:</b> ${pos['ts_price']:.6f} ({TS_PCT}%)\n\n"
                        f"🔥 <i>EMA 9x21 Cruzou para CIMA | RSI: {ultima_fechada['rsi']:.1f}</i>"
                    )
                    enviar_telegram(msg_sinal)

                elif cruzou_baixa and ultima_fechada['rsi'] < 50:
                    pos['ativa'] = True
                    pos['tipo'] = 'SELL'
                    pos['entrada'] = preco_atual
                    pos['ts_price'] = preco_atual * (1 + (TS_PCT / 100))

                    msg_sinal = (
                        f"⚡ <b>SINAL M1 ULTRA SCALPER</b> | #{hashtag}\n\n"
                        f"📊 <b>Direção:</b> 🔴 <b>SHORT (VENDA)</b>\n"
                        f"💵 <b>Entrada:</b> ${preco_atual:.6f}\n"
                        f"🛡 <b>Trailing Stop:</b> ${pos['ts_price']:.6f} ({TS_PCT}%)\n\n"
                        f"🔥 <i>EMA 9x21 Cruzou para BAIXO | RSI: {ultima_fechada['rsi']:.1f}</i>"
                    )
                    enviar_telegram(msg_sinal)

        except Exception as e:
            print(f"Erro em {symbol}: {e}")

print("==========================================")
print("BOT M1 SCALPER (15 ATIVOS) INICIADO!")
print("==========================================")

enviar_telegram("⚡ <b>SISTEMA M1 SCALPER CONECTADO (15 ATIVOS)</b>\n\nMonitorando BTC, ETH, SOL, DOGE, XRP, ADA, AVAX, LINK, NEAR, PEPE, SHIB, SUI, BNB, OP e ARB...")

while True:
    analisar_e_executar()
    time.sleep(3)  # Pausa de 3s entre varreduras completas
