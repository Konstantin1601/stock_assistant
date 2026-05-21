import streamlit as st
import requests

st.title("Акции РФ")

ticker = st.text_input("Введите тикер (например, SBER, GAZP, LKOH)", value="SBER")

if st.button("Узнать цену"):
    url = f"http://localhost:8000/quote/{ticker.upper()}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            st.success(f"{data['name']} ({data['ticker']})")
            st.metric("Цена", f"{data['current_price']} ₽", f"{data.get('change_percent', 0)}%")
        else:
            st.error(f"Ошибка: {data.get('detail', 'Неизвестная ошибка')}")
    except:
        st.error("Не удалось подключиться к бэкенду. Запущен ли FastAPI?")