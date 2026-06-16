from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime
import sqlite3
import json

# Создаём приложение FastAPI
app = FastAPI(title="Stock Assistant API", description="API для получения данных с MOEX")

# Настраиваем CORS (чтобы фронтенд мог обращаться к нашему API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Работа с БД

def init_db():
    """Создаём таблицу для хранения истории запросов"""
    conn = sqlite3.connect('stock_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            price REAL,
            timestamp TEXT NOT NULL,
            success INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(ticker, price, success=True):
    """Сохраняем запрос в базу данных"""
    conn = sqlite3.connect('stock_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO requests_history (ticker, price, timestamp, success)
        VALUES (?, ?, ?, ?)
    ''', (ticker, price, datetime.now().isoformat(), 1 if success else 0))
    conn.commit()
    conn.close()

# Инициализируем БД при запуске
init_db()

# Функции для работы с MOEX

def get_stock_data(ticker):
    """Получает данные об акции с MOEX"""
    url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Парсим marketdata
        marketdata = data.get("marketdata", {})
        rows = marketdata.get("data", [])
        columns = marketdata.get("columns", [])
        
        if not rows or not columns:
            return None, "Нет данных по тикеру"
        
        # Находим нужные индексы
        result = {}
        try:
            if "LAST" in columns:
                result["price"] = rows[0][columns.index("LAST")]
            if "VOLTODAY" in columns:
                result["volume"] = rows[0][columns.index("VOLTODAY")]
            if "HIGH" in columns:
                result["high"] = rows[0][columns.index("HIGH")]
            if "LOW" in columns:
                result["low"] = rows[0][columns.index("LOW")]
            
            # Также получаем информацию из securities
            securities = data.get("securities", {})
            sec_rows = securities.get("data", [])
            sec_columns = securities.get("columns", [])
            
            if sec_rows and sec_columns:
                if "SHORTNAME" in sec_columns:
                    result["name"] = sec_rows[0][sec_columns.index("SHORTNAME")]
                if "PREVPRICE" in sec_columns:
                    result["prev_price"] = sec_rows[0][sec_columns.index("PREVPRICE")]
            
            return result, None
            
        except (IndexError, ValueError) as e:
            return None, f"Ошибка парсинга данных: {str(e)}"
            
    except requests.RequestException as e:
        return None, f"Ошибка соединения с MOEX: {str(e)}"

def get_candles(ticker, interval=1):
    """
    Получает историю цен (свечи) с MOEX
    interval: 1 - 1 минута, 10 - 10 минут, 60 - 1 час, 24 - день
    """
    url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}/candles.json"
    
    params = {
        "interval": interval,  # интервал свечи
        "from": datetime.now().strftime("%Y-%m-%d"),  # с сегодня
        "till": datetime.now().strftime("%Y-%m-%d"),  # по сегодня
        "limit": 100  # максимум свечей
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Парсим данные
        candles = data.get("candles", {})
        rows = candles.get("data", [])
        columns = candles.get("columns", [])
        
        if not rows or not columns:
            return None, "Нет данных по свечам"
        
        # Находим нужные колонки
        result = []
        begin_idx = columns.index("begin") if "begin" in columns else -1
        close_idx = columns.index("close") if "close" in columns else -1
        
        if begin_idx == -1 or close_idx == -1:
            return None, "Не найдены нужные колонки"
        
        # Собираем данные для графика: время и цена закрытия
        for row in rows:
            result.append({
                "time": row[begin_idx],
                "price": row[close_idx]
            })
        
        return result, None
        
    except requests.RequestException as e:
        return None, f"Ошибка получения свечей: {str(e)}"


# Эндпоинты FastAPI

@app.get("/")
def root():
    """Корневой эндпоинт - проверка работы API"""
    return {
        "message": "Stock Assistant API работает!",
        "endpoints": {
            "/quote/{ticker}": "Получить информацию об акции",
            "/history": "Получить историю запросов",
            "/health": "Проверка здоровья сервера"
        }
    }

@app.get("/health")
def health_check():
    """Проверка, что сервер жив"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/quote/{ticker}")
def get_quote(ticker: str):
    """
    Получить информацию об акции по тикеру
    Пример: /quote/SBER
    """
    # Приводим тикер к верхнему регистру
    ticker = ticker.upper()
    
    # Получаем данные с MOEX
    data, error = get_stock_data(ticker)
    
    if error or not data or "price" not in data:
        save_to_db(ticker, None, success=False)
        raise HTTPException(status_code=404, detail=f"Тикер {ticker} не найден или данные недоступны. Ошибка: {error}")
    
    # Сохраняем успешный запрос в БД
    save_to_db(ticker, data.get("price"))
    
    # Формируем ответ
    response = {
        "ticker": ticker,
        "name": data.get("name", "Неизвестно"),
        "current_price": data.get("price"),
        "prev_price": data.get("prev_price"),
        "change": None,
        "high": data.get("high"),
        "low": data.get("low"),
        "volume": data.get("volume"),
        "timestamp": datetime.now().isoformat()
    }
    
    # Считаем изменение цены
    if response["prev_price"] and response["current_price"]:
        change = response["current_price"] - response["prev_price"]
        change_percent = (change / response["prev_price"]) * 100
        response["change"] = round(change, 2)
        response["change_percent"] = round(change_percent, 2)
    
    return response

@app.get("/candles/{ticker}")
def get_candles_endpoint(ticker: str, interval: int = 1):
    """
    Получить историю цен для графика
    Пример: /candles/SBER?interval=1
    """
    ticker = ticker.upper()
    
    candles, error = get_candles(ticker, interval)
    
    if error or not candles:
        raise HTTPException(status_code=404, detail=f"Нет данных по {ticker}")
    
    return {
        "ticker": ticker,
        "candles": candles,
        "count": len(candles)
    }

@app.get("/history")
def get_history(limit: int = 10):
    """
    Получить историю запросов из БД
    Пример: /history?limit=20
    """
    conn = sqlite3.connect('stock_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ticker, price, timestamp, success 
        FROM requests_history 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "ticker": row[0],
            "price": row[1],
            "timestamp": row[2],
            "success": bool(row[3])
        })
    
    return {"history": history, "count": len(history)}
