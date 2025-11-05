import streamlit as st
from pymongo import MongoClient
from datetime import timedelta
from bson import ObjectId

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
st.subheader("🏆 Top 3 usuários com mais cartas únicas")
total_unique_cards = cards_col.count_documents({})
top_users = users_col.find().sort("total_unique_cards", -1).limit(3)
for user in top_users:
    st.write(f"{user['twitch_name']} - {user['total_unique_cards']}/{total_unique_cards}")

st.markdown("---")

# --- Seleção de usuário ---
all_users = list(users_col.find())
user_options = [u["twitch_name"] for u in all_users]
selected_user_name = st.selectbox("Selecione o usuário", user_options)

# --- Garantir que selected_user_doc está definido ---
selected_user_doc = users_col.find_one({"twitch_name": selected_user_name})
selected_user_id = selected_user_doc["_id"]

# 🪙 --- Mostrar tokens do usuário ---
tokens = selected_user_doc.get("tokens", 0)
st.markdown(f"**🪙 Tokens:** {tokens}")

# Inicializa session_state para armazenar dados do usuário
if "current_user" not in st.session_state or st.session_state.current_user != selected_user_name:
    st.session_state.current_user = selected_user_name
    st.session_state.cards_list = []
    st.session_state.logs_list = []

    # --- Buscar cartas do usuário ---
    user_inventory = inventory_col.find({"user_id": selected_user_id})
    for item in user_inventory:
        card_doc = cards_col.find_one({"_id": item["card_id"]})
        if card_doc:
            st.session_state.cards_list.append({
                "number": card_doc.get("card_number", 0),
                "name": card_doc["name"],
                "rarity": card_doc["rarity"],
                "image_url": card_doc["image_url"],
                "quantity": item.get("quantity", 1),
                "card_id": card_doc["_id"]
            })

    # --- Buscar histórico ---
    logs_cursor = log_col.find({"twitch_id": selected_user_doc["twitch_id"]}).sort("timestamp", -1)
    for log in logs_cursor:
        ts = log["timestamp"]
        ts_brasil = ts - timedelta(hours=3)
        details = log.get("details", {})

        # Extrai informações detalhadas do log
        card_name = details.get("card_name", "")
        rarity = details.get("rarity", "")
        nova_carta = details.get("nova_carta", None)
        tokens_ganhos = details.get("tokens_ganhos", 0)

        # Define o texto "Nova" ou "Repetida"
        if nova_carta is True:
            status_text = "🆕 Nova"
        elif nova_carta is False:
            status_text = "♻️ Repetida"
        else:
            status_text = ""

        # Monta o texto final do log
        log_line = (
            f"{ts_brasil.strftime('%Y-%m-%d %H:%M:%S')} - {log['action']} - "
            f"{card_name} ({rarity}) {status_text} - 💰 +{tokens_ganhos} tokens"
        )

        st.session_state.logs_list.append(log_line)

# --- Novo filtro: todas / só do usuário / só não do usuário ---
st.subheader("⚙️ Filtrar cartas")
filter_option = st.selectbox("Mostrar cartas:", ["Todas", "Só as do usuário", "Só as que ele não tem"])

# --- Preparar lista de cartas para exibir ---
all_cards = list(cards_col.find())
user_card_ids = set(item["card_id"] for item in inventory_col.find({"user_id": selected_user_id}))

display_cards = []
for card in all_cards:
    has_card = card["_id"] in user_card_ids
    if filter_option == "Todas":
        display_cards.append((card, has_card))
    elif filter_option == "Só as do usuário" and has_card:
        display_cards.append((card, True))
    elif filter_option == "Só as que ele não tem" and not has_card:
        display_cards.append((card, False))

# --- Mostrar cartas ---
st.subheader(f"📦 Cartas de {selected_user_name}")
num_cols = 5
for i in range(0, len(display_cards), num_cols):
    row_cards = display_cards[i:i + num_cols]
    cols = st.columns(num_cols)
    for idx, (card, has_card) in enumerate(row_cards):
        col = cols[idx]
        img_style = "" if has_card else "filter: grayscale(100%);"
        quantity_text = (
            f" x{next((c['quantity'] for c in st.session_state.cards_list if c['card_id'] == card['_id']), 0)}"
            if has_card else ""
        )
        col.markdown(f"""
            <div style="
                display:flex;
                flex-direction: column;
                align-items:center;
                justify-content:flex-start;
                min-height:250px;
                text-align:center;
                margin-bottom:10px;
            ">
                <img src="{card['image_url']}" width="285" loading="lazy" style="flex-shrink:0; {img_style}">
                <div style="margin-top:5px;">{card['name']} - {card['rarity']}{quantity_text}</div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# --- Mostrar histórico ---
st.subheader(f"📜 Histórico de ações de {selected_user_name}")
if st.session_state.logs_list:
    st.text_area(
        label="Histórico",
        value="\n".join(st.session_state.logs_list),
        height=5 * 35,
        disabled=True
    )
else:
    st.write("Nenhum registro encontrado")
