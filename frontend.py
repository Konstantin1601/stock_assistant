import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Акции РФ", layout="wide")

st.title("📈 Акции РФ")

# Ввод тикера
ticker = st.text_input("Введите тикер (например, SBER, GAZP, LKOH)", value="SBER")

# Кнопка для запроса
if st.button("Узнать цену") or ticker:
    ticker = ticker.upper()
    
    # ---- ПОЛУЧАЕМ ТЕКУЩУЮ ЦЕНУ ----
    url_quote = f"http://localhost:8000/quote/{ticker}"
    
    try:
        response = requests.get(url_quote)
        data = response.json()
        
        if response.status_code == 200:
            # Показываем текущую цену
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Текущая цена", f"{data['current_price']} ₽", 
                         f"{data.get('change_percent', 0)}%")
            with col2:
                st.metric("📊 Максимум", f"{data.get('high', '—')} ₽")
            with col3:
                st.metric("📉 Минимум", f"{data.get('low', '—')} ₽")
            
            st.write(f"📅 Обновлено: {data['timestamp']}")
            
            # ---- ПОЛУЧАЕМ ИСТОРИЮ ЦЕН ДЛЯ ГРАФИКА ----
            url_candles = f"http://localhost:8000/candles/{ticker}?interval=1"
            
            try:
                resp_candles = requests.get(url_candles)
                if resp_candles.status_code == 200:
                    candle_data = resp_candles.json()
                    
                    if candle_data.get("candles"):
                        # Подготавливаем данные для графика
                        times = []
                        prices = []
                        
                        for c in candle_data["candles"]:
                            # Преобразуем время в читаемый формат
                            time_str = c["time"][11:16]  # Берём только HH:MM
                            times.append(time_str)
                            prices.append(c["price"])
                        
                        # Рисуем график
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=times,
                            y=prices,
                            mode='lines+markers',
                            name='Цена',
                            line=dict(color='blue', width=2),
                            marker=dict(size=4)
                        ))
                        
                        fig.update_layout(
                            title=f"Цена {ticker} за сегодня",
                            xaxis_title="Время",
                            yaxis_title="Цена (₽)",
                            height=400,
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Нет данных для графика")
                else:
                    st.warning("Не удалось загрузить график")
                    
            except Exception as e:
                st.warning(f"Ошибка загрузки графика: {e}")
                
        else:
            st.error(f"Ошибка: {data.get('detail', 'Неизвестная ошибка')}")
            
    except requests.exceptions.ConnectionError:
        st.error("❌ Не удалось подключиться к бэкенду. Запущен ли FastAPI?")
    except Exception as e:
        st.error(f"Ошибка: {e}")
