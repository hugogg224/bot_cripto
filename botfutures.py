import os
import time
import datetime
from pybit.unified_trading import HTTP
import math

# === CONFIGURACIÓN GENERAL ===
API_KEY = os.getenv("BYBIT_API_KEY_REAL")
API_SECRET = os.getenv("BYBIT_API_SECRET_REAL")

symbol = os.getenv("SYMBOL", "BTCUSDT")
leverage_limit = float(os.getenv("LEVERAGE_LIMIT", 25))
cooldown_minutes = float(os.getenv("COOLDOWN_MINUTES", 7))

# === PARÁMETROS DE CAPITAL ===
capital_total = float(os.getenv("CAPITAL_TOTAL", 40))  # Capital total
target_price = float(os.getenv("PRICE_TARGET", 80000))  # Precio objetivo BTC

# === CÁLCULOS DE CAPITAL ===
capital_dual = capital_total * 0.8
capital_bot = capital_total * 0.2

# Cálculo de apalancamiento necesario para cubrir el 80 % del capital total
leverage = round(capital_dual / capital_bot, 2)
if leverage > leverage_limit:
    leverage = leverage_limit

# === CONEXIÓN CON BYBIT ===
session = HTTP(
    testnet=False,  # cambia a True si quieres probar en testnet
    api_key=API_KEY,
    api_secret=API_SECRET
)

print("\n=== BOT FUTURES AUTO (Bybit v5 + Railway Ready) ===")
print(f"Capital total: ${capital_total}")
print(f"Dual Assets: ${capital_dual}")
print(f"Capital Bot: ${capital_bot}")
print(f"Apalancamiento calculado: {leverage}x")
print(f"Target Price: {target_price}\n")

# === FUNCIONES ===
def get_price():
    try:
        data = session.get_tickers(category="linear", symbol=symbol)
        return float(data['result']['list'][0]['lastPrice'])
    except Exception as e:
        print("⚠️ Error al obtener precio:", e)
        return None

def open_short(qty):
    try:
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Sell",
            orderType="Market",
            qty=qty,
            timeInForce="GoodTillCancel",
            reduceOnly=False
        )
        print("✅ SHORT abierto.")
        return order
    except Exception as e:
        print("⚠️ Error al abrir SHORT:", e)

def close_short(qty):
    try:
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            orderType="Market",
            qty=qty,
            timeInForce="GoodTillCancel",
            reduceOnly=True
        )
        print("🛑 SHORT cerrado.")
        return order
    except Exception as e:
        print("⚠️ Error al cerrar SHORT:", e)

# === ESTABLECER APALANCAMIENTO ===
try:
    session.set_leverage(category="linear", symbol=symbol,
                         buyLeverage=leverage, sellLeverage=leverage)
    print(f"🎯 Apalancamiento {leverage}x establecido para {symbol}\n")
except Exception as e:
    print("⚠️ Error al establecer apalancamiento:", e)

# === LOOP PRINCIPAL ===
position_open = False
entry_price = None
last_trade_time = datetime.datetime.now() - datetime.timedelta(minutes=cooldown_minutes)

while True:
    try:
        price = get_price()
        if not price:
            time.sleep(10)
            continue

        now = datetime.datetime.now()
        time_since_last = (now - last_trade_time).total_seconds() / 60

        print(f"{now.strftime('%H:%M:%S')} | Precio {symbol}: {price:.2f} USD", end="\r")

        # Abrir SHORT
        if not position_open and price <= target_price and time_since_last >= cooldown_minutes:
            qty = round((capital_bot * leverage) / price, 4)
            print(f"\n🚨 Precio <= {target_price}. Abriendo SHORT...")
            open_short(qty)
            entry_price = price
            position_open = True
            last_trade_time = now

        # Cerrar SHORT
        elif position_open and price >= entry_price:
            print(f"\n🛑 Precio volvió a la entrada ({entry_price}). Cerrando SHORT...")
            close_short(qty)
            position_open = False
            last_trade_time = now

        time.sleep(10)

    except KeyboardInterrupt:
        print("\n🧩 Bot detenido manualmente.")
        break
    except Exception as e:
        print(f"\n⚠️ Error en ciclo principal: {e}")
        time.sleep(10)
