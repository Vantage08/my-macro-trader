import os
from flask import Flask, request, jsonify
import ccxt

app = Flask(__name__)

# --- CONFIGURATION (Edit your default trading parameters here) ---
SYMBOL = "BTC/USDT:USDT"  # Trading target
POSITION_SIZE = 0.01      # Trade size in BTC (Adjust to your leverage/risk)
TP_PERCENT = 0.03         # 3.0% Take Profit
SL_PERCENT = 0.015        # 1.5% Stop Loss
SECRET_TOKEN = "your_super_secret_macro_password_123" # Keep this safe!

# Authenticate with the exchange using your secure environment variables
exchange = ccxt.bybit({
    'apiKey': os.getenv('EXCHANGE_API_KEY'),
    'secret': os.getenv('EXCHANGE_SECRET'),
    'options': {'defaultType': 'future'}
})

@app.route('/trade', methods=['POST'])
def execute_trade():
    data = request.json
    
    # Authenticate the incoming ping from MacroDroid
    if not data or data.get("token") != SECRET_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    
    direction = data.get("direction", "").upper()
    if direction not in ["LONG", "SHORT"]:
        return jsonify({"error": "Invalid direction"}), 400

    try:
        # 1. Fetch the latest market price to base our TP/SL math on
        ticker = exchange.fetch_ticker(SYMBOL)
        current_price = ticker['last']
        
        # 2. Place trades based on the signal
        if direction == "LONG":
            # Open market long
            order = exchange.create_market_buy_order(SYMBOL, POSITION_SIZE)
            
            # Calculate target exits
            tp_price = current_price * (1 + TP_PERCENT)
            sl_price = current_price * (1 - SL_PERCENT)
            
            # Send Limit TP and Stop Market SL orders
            exchange.create_order(SYMBOL, 'limit', 'sell', POSITION_SIZE, tp_price, {'reduceOnly': True})
            exchange.create_order(SYMBOL, 'stop', 'sell', POSITION_SIZE, None, {'stopPrice': sl_price, 'reduceOnly': True})
            
        elif direction == "SHORT":
            # Open market short
            order = exchange.create_market_sell_order(SYMBOL, POSITION_SIZE)
            
            # Calculate target exits
            tp_price = current_price * (1 - TP_PERCENT)
            sl_price = current_price * (1 + SL_PERCENT)
            
            # Send Limit TP and Stop Market SL orders
            exchange.create_order(SYMBOL, 'limit', 'buy', POSITION_SIZE, tp_price, {'reduceOnly': True})
            exchange.create_order(SYMBOL, 'stop', 'buy', POSITION_SIZE, None, {'stopPrice': sl_price, 'reduceOnly': True})

        return jsonify({
            "status": "success",
            "direction": direction,
            "entry": current_price,
            "tp": tp_price,
            "sl": sl_price
        }), 200

    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
