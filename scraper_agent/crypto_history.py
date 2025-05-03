import os
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import datetime as dt
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("CMC_API_KEY")
if not API_KEY:
    raise RuntimeError("Set your CoinMarketCap API key in the CMC_API_KEY environment variable")

DB_NAME = os.getenv("DB_NAME", "your_db")
DB_USER = os.getenv("DB_USER", "your_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_pass")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

BASE_URL = "https://pro-api.coinmarketcap.com/v1"
HEADERS = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": API_KEY
}

SYMBOLS = ["BTC", "ETH", "ADA", "DOT", "SOL"]
CONVERT = "USD"


def fetch(endpoint, params=None):
    """Helper to perform GET on CoinMarketCap API and return .json()['data']."""
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()["data"]


def setup_tables(cur):
    """Create tables designed to store both current and historical data."""
    # Drop existing tables to avoid column mismatch
    cur.execute("""
    DROP TABLE IF EXISTS crypto_quotes CASCADE;
    DROP TABLE IF EXISTS crypto_listings CASCADE;
    DROP TABLE IF EXISTS global_metrics CASCADE;
    DROP TABLE IF EXISTS price_conversions CASCADE;
    """)
    
    cur.execute("""
    -- Quotes table with timestamp column for historical data
    CREATE TABLE IF NOT EXISTS crypto_quotes (
      id SERIAL,
      symbol TEXT NOT NULL,
      price_usd DOUBLE PRECISION,
      market_cap DOUBLE PRECISION,
      volume_24h DOUBLE PRECISION,
      pct_change_1h DOUBLE PRECISION,
      pct_change_24h DOUBLE PRECISION,
      pct_change_7d DOUBLE PRECISION,
      timestamp TIMESTAMP NOT NULL,
      PRIMARY KEY (id)
    );
    
    -- Listings table with timestamp column for historical data
    CREATE TABLE IF NOT EXISTS crypto_listings (
      id SERIAL,
      symbol TEXT NOT NULL,
      rank INTEGER,
      circulating_supply DOUBLE PRECISION,
      total_supply DOUBLE PRECISION,
      max_supply DOUBLE PRECISION,
      num_market_pairs INTEGER,
      volume_24h DOUBLE PRECISION,
      timestamp TIMESTAMP NOT NULL,
      PRIMARY KEY (id)
    );
    
    -- Global metrics with timestamp column for historical data
    CREATE TABLE IF NOT EXISTS global_metrics (
      id SERIAL,
      metric TEXT NOT NULL,
      value DOUBLE PRECISION,
      timestamp TIMESTAMP NOT NULL,
      PRIMARY KEY (id)
    );
    
    -- Price conversions with timestamp column for historical data
    CREATE TABLE IF NOT EXISTS price_conversions (
      id SERIAL,
      base_symbol TEXT NOT NULL,
      target_symbol TEXT NOT NULL,
      rate DOUBLE PRECISION,
      timestamp TIMESTAMP NOT NULL,
      PRIMARY KEY (id)
    );
    
    -- Tables without historical data
    CREATE TABLE IF NOT EXISTS id_map (
      symbol TEXT PRIMARY KEY,
      cmc_id INTEGER
    );
    
    CREATE TABLE IF NOT EXISTS metadata_info (
      symbol TEXT PRIMARY KEY,
      name TEXT,
      logo_url TEXT,
      description TEXT,
      tags TEXT[],
      date_added DATE
    );
    
    -- Create indexes for efficient historical queries
    CREATE INDEX IF NOT EXISTS crypto_quotes_symbol_timestamp_idx ON crypto_quotes(symbol, timestamp);
    CREATE INDEX IF NOT EXISTS crypto_listings_symbol_timestamp_idx ON crypto_listings(symbol, timestamp);
    CREATE INDEX IF NOT EXISTS global_metrics_metric_timestamp_idx ON global_metrics(metric, timestamp);
    CREATE INDEX IF NOT EXISTS price_conversions_symbols_timestamp_idx ON price_conversions(base_symbol, target_symbol, timestamp);
    """)


def insert_data(conn):
    """Fetch from CMC and insert into Postgres tables (preserving historical data)."""
    cur = conn.cursor()
    # Use timezone-aware datetime to avoid deprecation warning
    now = datetime.now(dt.UTC)

    # 1. Quotes
    quotes = fetch("cryptocurrency/quotes/latest", {"symbol": ",".join(SYMBOLS), "convert": CONVERT})
    quote_rows = [
        (
            sym,
            data["quote"][CONVERT]["price"],
            data["quote"][CONVERT]["market_cap"],
            data["quote"][CONVERT]["volume_24h"],
            data["quote"][CONVERT]["percent_change_1h"],
            data["quote"][CONVERT]["percent_change_24h"],
            data["quote"][CONVERT]["percent_change_7d"],
            now
        )
        for sym, data in quotes.items()
    ]
    
    # Insert into quotes table (historical approach)
    execute_values(cur, """
        INSERT INTO crypto_quotes
        (symbol, price_usd, market_cap, volume_24h, pct_change_1h, pct_change_24h, pct_change_7d, timestamp)
        VALUES %s
    """, quote_rows)

    # 2. Listings
    listings = fetch("cryptocurrency/listings/latest", {"start": 1, "limit": 5, "convert": CONVERT})
    listing_rows = [
        (
            c["symbol"],
            c["cmc_rank"],
            c["circulating_supply"],
            c["total_supply"],
            c.get("max_supply"),
            c["num_market_pairs"],
            c["quote"][CONVERT]["volume_24h"],
            now
        )
        for c in listings
    ]
    
    # Insert into listings table (historical approach)
    execute_values(cur, """
        INSERT INTO crypto_listings
        (symbol, rank, circulating_supply, total_supply, max_supply, num_market_pairs, volume_24h, timestamp)
        VALUES %s
    """, listing_rows)

    # 3. Global Metrics
    globals_ = fetch("global-metrics/quotes/latest")
    # Iterate through the items in the CONVERT (e.g., "USD") dictionary, excluding the "last_updated" key
    global_rows = [(key, val, now) for key, val in globals_["quote"][CONVERT].items() if key != "last_updated"]
    
    # Insert into global metrics table (historical approach)
    execute_values(cur, """
        INSERT INTO global_metrics
        (metric, value, timestamp)
        VALUES %s
    """, global_rows)

    # 4. Price Conversion (1 BTC to USD)
    conv = fetch("tools/price-conversion", {"amount": 1, "symbol": "BTC", "convert": CONVERT})
    # Extract the actual price value from the quote dictionary
    conv_row = [("BTC", CONVERT, conv["quote"][CONVERT]["price"], now)]
    
    # Insert into price conversions table (historical approach)
    execute_values(cur, """
        INSERT INTO price_conversions
        (base_symbol, target_symbol, rate, timestamp)
        VALUES %s
    """, conv_row)

    # 5. ID Map (no historical data needed)
    id_map = fetch("cryptocurrency/map", {"symbol": ",".join(SYMBOLS)})
    map_rows = [(c["symbol"], c["id"]) for c in id_map]
    execute_values(cur, """
        INSERT INTO id_map (symbol, cmc_id) VALUES %s
        ON CONFLICT (symbol) DO NOTHING;
    """, map_rows)

    # 6. Metadata Info (no historical data needed)
    info = fetch("cryptocurrency/info", {"symbol": ",".join(SYMBOLS)})
    meta_rows = [
        (
            sym,
            info[sym]["name"],
            info[sym]["logo"],
            info[sym].get("description", ""),
            info[sym].get("tags", []),
            info[sym].get("date_added", None)
        )
        for sym in SYMBOLS
    ]
    execute_values(cur, """
        INSERT INTO metadata_info
        (symbol, name, logo_url, description, tags, date_added)
        VALUES %s
        ON CONFLICT (symbol) DO UPDATE SET
          name = EXCLUDED.name,
          logo_url = EXCLUDED.logo_url,
          description = EXCLUDED.description,
          tags = EXCLUDED.tags,
          date_added = EXCLUDED.date_added;
    """, meta_rows)

    conn.commit()
    cur.close()


def analyze_price_history(conn, symbol, days=30):
    """Analyze historical price data for a cryptocurrency."""
    cur = conn.cursor()
    
    # Calculate date range
    end_date = datetime.now(dt.UTC)
    start_date = end_date - dt.timedelta(days=days)
    
    # Query historical data
    cur.execute("""
        SELECT timestamp, price_usd, market_cap, volume_24h, 
               pct_change_1h, pct_change_24h, pct_change_7d
        FROM crypto_quotes
        WHERE symbol = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp
    """, (symbol, start_date, end_date))
    
    rows = cur.fetchall()
    cur.close()
    
    if not rows:
        print(f"No historical data available for {symbol}")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=[
        'timestamp', 'price', 'market_cap', 'volume_24h', 
        'pct_change_1h', 'pct_change_24h', 'pct_change_7d'
    ])
    
    # Calculate moving averages if we have enough data
    if len(df) >= 7:
        df['ma_7d'] = df['price'].rolling(window=7).mean()
        
    if len(df) >= 14:
        df['ma_14d'] = df['price'].rolling(window=14).mean()
    
    if len(df) >= 30:
        df['ma_30d'] = df['price'].rolling(window=30).mean()
    
    # Calculate daily returns and volatility
    if len(df) > 1:
        df['daily_return'] = df['price'].pct_change()
        # 7-day rolling volatility (annualized)
        if len(df) >= 7:
            df['volatility'] = df['daily_return'].rolling(window=7).std() * (252 ** 0.5)
    
    # Print summary
    print(f"\n{symbol} Summary:")
    print(f"Current Price: ${df['price'].iloc[-1]:.2f}")
    print(f"Price Range: ${df['price'].min():.2f} - ${df['price'].max():.2f}")
    
    if 'volatility' in df.columns and not pd.isna(df['volatility'].iloc[-1]):
        print(f"Current Volatility: {df['volatility'].iloc[-1]:.2%}")
    
    # Generate price chart
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 1, 1)
    plt.plot(df['timestamp'], df['price'], label=f'{symbol} Price')
    
    if 'ma_7d' in df.columns:
        plt.plot(df['timestamp'], df['ma_7d'], label='7-Day MA')
    if 'ma_30d' in df.columns:
        plt.plot(df['timestamp'], df['ma_30d'], label='30-Day MA')
    
    plt.title(f'{symbol} Price History')
    plt.ylabel('Price (USD)')
    plt.legend()
    plt.grid(True)
    
    plt.subplot(2, 1, 2)
    plt.bar(df['timestamp'], df['volume_24h'], color='gray', alpha=0.5)
    plt.title(f'{symbol} Trading Volume')
    plt.ylabel('Volume (24h)')
    plt.grid(True)
    
    plt.tight_layout()
    
    # Save the chart
    filename = f'{symbol}_price_chart.png'
    plt.savefig(filename)
    print(f"Chart saved as {filename}")
    plt.close()
    
    return df


def main():
    # Get command line arguments
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'collect'
    
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    
    try:
        if mode == 'setup':
            # Create tables
            cur = conn.cursor()
            setup_tables(cur)
            conn.commit()
            print("✅ Database tables created successfully")
            
        elif mode == 'collect':
            # Just collect data
            insert_data(conn)
            print("✅ Cryptocurrency data collected successfully")
            
        elif mode == 'analyze':
            # Analyze historical data
            for symbol in SYMBOLS:
                print(f"Analyzing {symbol} data...")
                analyze_price_history(conn, symbol, days=30)
                
        elif mode == 'all':
            # Setup, collect and analyze
            cur = conn.cursor()
            setup_tables(cur)
            conn.commit()
            insert_data(conn)
            for symbol in SYMBOLS:
                analyze_price_history(conn, symbol, days=30)
            print("✅ Setup, data collection, and analysis completed")
            
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python crypto_history.py [mode]")
            print("Modes: setup, collect, analyze, all")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main() 

