import requests
import json

# Запрос к MOEX для акции Сбербанка
ticker = "SBER"
url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"

print(f"Запрашиваю {url}")
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    
    # Выводим ответ
    print(json.dumps(data, indent=2)[:500])
    
    # Пытаемся найти текущую цену
    marketdata = data.get("marketdata", {})
    rows = marketdata.get("data", [])
    columns = marketdata.get("columns", [])
    
    if rows and columns:
        # Находим индекс колонки с ценой последней сделки
        try:
            last_price_idx = columns.index("LAST")
            last_price = rows[0][last_price_idx]
            print(f"\n Текущая цена {ticker}: {last_price} ₽")
        except ValueError:
            print("Колонка LAST не найдена")
    else:
        print("Нет данных по marketdata")
else:
    print(f"Ошибка: {response.status_code}")