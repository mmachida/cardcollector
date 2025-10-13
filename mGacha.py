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

# Inicializa session_state para armazenar dados do usuário
if "current_user" not in st.session_state or st.session_state.current_user != selected_user_name:
    st.session_state.current_user = selected_user_name
    st.session_state.cards_list = []
    st.session_state.logs_list = []

    # --- Buscar dados do usuário ---
    selected_user_doc = users_col.find_one({"twitch_name": selected_user_name})
    if selected_user_doc:
        selected_user_id = selected_user_doc["_id"]
        user_inventory = inventory_col.find({"user_id": selected_user_id})
        for item in user_inventory:
            card_doc = cards_col.find_one({"_id": item["card_id"]})
            if card_doc:
                st.session_state.cards_list.append({
                    "number": card_doc.get("card_number", 0),
                    "name": card_doc["name"],
                    "rarity": card_doc["rarity"],
                    "image_url": card_doc["image_url"],
                    "quantity": item.get("quantity", 1)
                })

        logs_cursor = log_col.find({"twitch_id": selected_user_doc["twitch_id"]}).sort("timestamp", -1)
        for log in logs_cursor:
            ts = log["timestamp"]
            ts_brasil = ts - timedelta(hours=3)
            details = log.get("details", {})
            name = details.get("name", "")
            rarity = details.get("rarity", "")
            st.session_state.logs_list.append(
                f"{ts_brasil.strftime('%Y-%m-%d %H:%M:%S')} - {log['action']} - {name} - {rarity}"
            )

# --- Filtros de ordenação ---
st.subheader("⚙️ Ordenar cartas")
if "reverse" not in st.session_state:
    st.session_state.reverse = False
if "prev_sort_type" not in st.session_state:
    st.session_state.prev_sort_type = None

col_sort, col_reverse = st.columns([5,1])

with col_sort:
    sort_type = st.selectbox("Tipo de ordenação:", ["Número", "Alfabético", "Raridade", "Quantidade"])

    # Resetar reverse se o tipo de ordenação mudou
    if st.session_state.prev_sort_type != sort_type:
        st.session_state.reverse = True if sort_type == "Quantidade" else False
        st.session_state.prev_sort_type = sort_type

with col_reverse:
    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
    rev_clicked = st.button("⇅")
    if rev_clicked:
        st.session_state.reverse = not st.session_state.reverse

# --- Ordenar e mostrar cartas ---
st.subheader(f"📦 Cartas de {selected_user_name}")
cards_list = st.session_state.cards_list.copy()  # copia para não alterar permanentemente

if cards_list:
    if sort_type == "Número":
        cards_list.sort(key=lambda x: x["number"], reverse=st.session_state.reverse)
    elif sort_type == "Alfabético":
        cards_list.sort(key=lambda x: x["name"].lower(), reverse=st.session_state.reverse)
    elif sort_type == "Raridade":
        rarity_order = ["legendary", "epic", "rare", "common"]
        cards_list.sort(key=lambda x: rarity_order.index(x["rarity"].lower()), reverse=st.session_state.reverse)
    elif sort_type == "Quantidade":
        cards_list.sort(key=lambda x: x["quantity"], reverse=st.session_state.reverse)

    num_cols = 4
    for i in range(0, len(cards_list), num_cols):
        row_cards = cards_list[i:i+num_cols]
        cols = st.columns(num_cols)
        for idx, card in enumerate(row_cards):
            col = cols[idx]
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
                    <img src="{card['image_url']}" width="285" loading="lazy" style="flex-shrink:0;">
                    <div style="margin-top:5px;">{card['name']} - {card['rarity']} x{card['quantity']}</div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.write("Nenhuma carta encontrada")

st.markdown("---")

# --- Mostrar histórico ---
st.subheader(f"📜 Histórico de ações de {selected_user_name}")
if st.session_state.logs_list:
    st.text_area(
        label="Histórico",
        value="\n".join(st.session_state.logs_list),
        height=5*35,
        disabled=True
    )
else:
    st.write("Nenhum registro encontrado")
