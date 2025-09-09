import sqlite3
from pathlib import Path
from typing import Iterable

DB_PATH = Path('trading.db')

SCHEMA = [
    '''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY,
        symbol TEXT,
        side TEXT,
        qty REAL,
        price REAL,
        ts INTEGER
    );''',
    '''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        binance_order_id TEXT,
        symbol TEXT,
        side TEXT,
        type TEXT,
        price REAL,
        qty REAL,
        status TEXT,
        ts INTEGER
    );'''
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        for stmt in SCHEMA:
            cur.execute(stmt)
        conn.commit()
    finally:
        conn.close()


def save_order(order: dict):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (binance_order_id, symbol, side, type, price, qty, status, ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(order.get('orderId')),
                order.get('symbol'),
                order.get('side'),
                order.get('type'),
                float(order.get('price') or order.get('stopPrice') or 0),
                float(order.get('origQty') or order.get('executedQty') or 0),
                order.get('status'),
                int(order.get('transactTime') or order.get('time') or 0),
            ),
        )
        conn.commit()
    finally:
        conn.close()
