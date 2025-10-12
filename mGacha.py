import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz

# --- Conexão MongoDB ---
MONGO_URI = st.secrets["MONGO"]["uri"]
client = MongoClient(MONGO_URI)
db = client["gacha"]
users_col = db["users"]
inventory_col = db["inventory"]
cards_col = db["cards"]
log_col = db["log_history"]

# --- Configurações Streamlit ---
st.set_page_config(page_title="mGacha", layout="centered")
st.title("🎴 mGacha Dashboard")

# --- Top 3 usuários ---
st.subheader("🏆 Top 3 usuários com mais cartas")
top_users = users_col.find().sort("total_unique_cards", -1).limit(3)
for user in top_users:
    st.write(f"{user['twitch_name']} - {user['total_unique_cards']} cartas")

st.markdown("---")

# --- Seleção de usuário ---
all_users = list(users_col.find())
user_options = [u["twitch_name"] for u in all_users]
selected_user_name = st.selectbox("Selecione o usuário", user_options)

selected_user_doc = users_col.find_one({"twitch_name": selected_user_name})
selected_user_id = selected_user_doc["_id"] if selected_user_doc else None

# --- Cartas ---
st.subheader(f"📦 Cartas de {selected_user_name}")
if selected_user_id:
    user_inventory = inventory_col.find({"user_id": selected_user_id})
    cards_list = []
    for item in user_inventory:
        card_doc = cards_col.find_one({"_id": item["card_id"]})
        if card_doc:
            cards_list.append({
                "name": card_doc["name"],
                "rarity": card_doc["rarity"],
                "image_url": card_doc["image_url"],
                "quantity": item.get("quantity", 1)
            })
    if cards_list:
        cols = st.columns(4)
        for idx, card in enumerate(cards_list):
            col = cols[idx % 4]
            # Ajuste de largura com width, substituindo use_container_width
            col.image(card["image_url"], width=285)  # ajuste o valor conforme necessário
            col.caption(f"{card['name']} - {card['rarity']} x{card['quantity']}")
    else:
        st.write("Nenhuma carta encontrada")
else:
    st.write("Usuário não encontrado")

st.markdown("---")

# --- Histórico ---
st.subheader(f"📜 Histórico de ações de {selected_user_name}")

if selected_user_id:
    selected_user_twitch_id = selected_user_doc["twitch_id"]
    logs_cursor = log_col.find({"twitch_id": selected_user_twitch_id}).sort("timestamp", -1)
    
    logs_list = []
    for log in logs_cursor:
        ts = log["timestamp"]
        # Subtrai 3 horas
        ts_brasil = ts - timedelta(hours=3)
        
        details = log.get("details", {})
        name = details.get("name", "")
        rarity = details.get("rarity", "")
        logs_list.append(f"{ts_brasil.strftime('%Y-%m-%d %H:%M:%S')} - {log['action']} - {name} - {rarity}")

    if logs_list:
        # Caixa com scroll, mostrando apenas 5 linhas de altura
        st.text_area(
            label="Histórico",
            value="\n".join(logs_list),
            height=5*35,  # aproximadamente 25px por linha
            disabled=True
        )
    else:
        st.write("Nenhum registro encontrado")
else:
    st.write("Usuário não encontrado")