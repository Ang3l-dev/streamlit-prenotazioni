import streamlit as st
from datetime import datetime, timedelta, date
import pandas as pd
import os

# Configurazione iniziale
TIME_PER_DEVICE = 3  # Minuti per caricare un apparato
START_TIME = "09:00"
END_TIME = "16:00"
FILE_NAME = "prenotazioni.xlsx"

# Credenziali di accesso
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"}
}

# Funzione per generare fasce orarie
def generate_time_slots(start_time, end_time):
    slots = []
    current_time = datetime.strptime(start_time, "%H:%M")
    end_time = datetime.strptime(end_time, "%H:%M")
    while current_time < end_time:
        slots.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=TIME_PER_DEVICE)
    return slots

# Funzione per calcolare la fascia oraria
def calculate_time_slot(start_time, num_devices):
    start = datetime.strptime(start_time, "%H:%M")
    duration = timedelta(minutes=num_devices * TIME_PER_DEVICE)
    end = start + duration
    return start.strftime("%H:%M"), end.strftime("%H:%M")

# Funzione per inizializzare il file Excel se non esiste
def initialize_bookings(file_name):
    if not os.path.exists(file_name):
        df = pd.DataFrame(columns=["Data", "Inizio", "Fine", "Nome", "Apparati"])
        df.to_excel(file_name, index=False)
    else:
        try:
            df = pd.read_excel(file_name)
            required_columns = ["Data", "Inizio", "Fine", "Nome", "Apparati"]
            if not all(col in df.columns for col in required_columns):
                raise ValueError("Il file Excel non ha le colonne necessarie.")
        except:
            df = pd.DataFrame(columns=["Data", "Inizio", "Fine", "Nome", "Apparati"])
            df.to_excel(file_name, index=False)

# Funzione per leggere le prenotazioni
def load_bookings(file_name):
    return pd.read_excel(file_name)

# Funzione per salvare le prenotazioni
def save_bookings(df, file_name):
    df.to_excel(file_name, index=False)

# Aggiorna i dati in caso di modifiche
def refresh_bookings():
    st.session_state["bookings"] = load_bookings(FILE_NAME)

# Assicura che il file Excel sia inizializzato
initialize_bookings(FILE_NAME)

# Login
def login(username, password):
    user = USERS.get(username)
    if user and user["password"] == password:
        return user["role"]
    return None

# Gestione dello stato della sessione per accesso e dati
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["role"] = None
    st.session_state["bookings"] = load_bookings(FILE_NAME)

# Interfaccia di login
if not st.session_state["authenticated"]:
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        role = login(username, password)
        if role:
            st.session_state["authenticated"] = True
            st.session_state["role"] = role
            st.success(f"Accesso effettuato come {role}")
        else:
            st.error("Credenziali non valide")
else:
    # Logout
    st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"authenticated": False, "role": None}))

    # Layout principale
    st.title("Sistema di Prenotazione Apparati")

    # Selezione della data tramite calendario
    selected_date = st.date_input("Seleziona la data:", min_value=date.today())

    # Filtra le prenotazioni per la data selezionata
    filtered_bookings = st.session_state["bookings"][
        st.session_state["bookings"]["Data"] == selected_date.strftime("%Y-%m-%d")
    ]

    # Mostra le prenotazioni attuali
    st.header("Prenotazioni Attuali")
    if not filtered_bookings.empty:
        st.table(filtered_bookings.sort_values("Inizio"))
    else:
        st.write("Nessuna prenotazione effettuata.")

    # Funzionalità Admin
    if st.session_state["role"] == "admin":
        st.sidebar.header("Funzionalità Admin")

        # Aggiungi prenotazione
        st.sidebar.subheader("Nuova Prenotazione")
        time_slots = generate_time_slots(START_TIME, END_TIME)
        available_slots = []
        for slot in time_slots:
            potential_start = datetime.strptime(slot, "%H:%M")
            potential_end = potential_start + timedelta(minutes=TIME_PER_DEVICE)
            if not any(
                (
                    datetime.strptime(row["Inizio"], "%H:%M") < potential_end and
                    datetime.strptime(row["Fine"], "%H:%M") > potential_start
                )
                for _, row in filtered_bookings.iterrows()
            ):
                available_slots.append(slot)

        with st.sidebar.form(key="booking_form"):
            selected_slot = st.selectbox("Seleziona l'orario di inizio:", available_slots)
            name = st.text_input("Inserisci il tuo nome:")
            num_devices = st.number_input("Numero di apparati:", min_value=1, step=1)
            submit_button = st.form_submit_button(label="Prenota")

        if submit_button:
            start, end = calculate_time_slot(selected_slot, num_devices)
            new_booking = pd.DataFrame({
                "Data": [selected_date.strftime("%Y-%m-%d")],
                "Inizio": [start],
                "Fine": [end],
                "Nome": [name],
                "Apparati": [num_devices]
            })
            st.session_state["bookings"] = pd.concat([st.session_state["bookings"], new_booking], ignore_index=True)
            save_bookings(st.session_state["bookings"], FILE_NAME)
            refresh_bookings()
            st.success(f"Prenotazione per {name} aggiunta con successo! ({start} - {end})")

        # Annulla prenotazione
        st.sidebar.subheader("Annulla Prenotazione")
        if not filtered_bookings.empty:
            selected_booking = st.sidebar.selectbox(
                "Seleziona una prenotazione da annullare:",
                filtered_bookings.index.tolist(),
                format_func=lambda idx: f"{filtered_bookings.loc[idx, 'Nome']} - {filtered_bookings.loc[idx, 'Inizio']} ({filtered_bookings.loc[idx, 'Fine']})"
            )
            if st.sidebar.button("Annulla"):
                st.session_state["bookings"] = st.session_state["bookings"].drop(index=selected_booking)
                save_bookings(st.session_state["bookings"], FILE_NAME)
                refresh_bookings()
                st.success("Prenotazione annullata con successo!")

        # Modifica prenotazione
        st.sidebar.subheader("Modifica Prenotazione")
        if not filtered_bookings.empty:
            selected_booking_to_edit = st.sidebar.selectbox(
                "Seleziona una prenotazione da modificare:",
                filtered_bookings.index.tolist(),
                format_func=lambda idx: f"{filtered_bookings.loc[idx, 'Nome']} - {filtered_bookings.loc[idx, 'Inizio']} ({filtered_bookings.loc[idx, 'Fine']})"
            )
            if selected_booking_to_edit is not None:
                with st.sidebar.form(key="edit_booking_form"):
                    new_name = st.text_input("Nuovo Nome:", value=filtered_bookings.loc[selected_booking_to_edit, "Nome"])
                    new_num_devices = st.number_input("Nuovo Numero di Apparati:", min_value=1, step=1, value=filtered_bookings.loc[selected_booking_to_edit, "Apparati"])
                    new_time_slot = st.selectbox("Nuovo Orario di Inizio:", time_slots, index=time_slots.index(filtered_bookings.loc[selected_booking_to_edit, "Inizio"]))
                    submit_edit = st.form_submit_button(label="Modifica")

                if submit_edit:
                    new_start, new_end = calculate_time_slot(new_time_slot, new_num_devices)
                    st.session_state["bookings"].loc[selected_booking_to_edit, "Nome"] = new_name
                    st.session_state["bookings"].loc[selected_booking_to_edit, "Inizio"] = new_start
                    st.session_state["bookings"].loc[selected_booking_to_edit, "Fine"] = new_end
                    st.session_state["bookings"].loc[selected_booking_to_edit, "Apparati"] = new_num_devices
                    save_bookings(st.session_state["bookings"], FILE_NAME)
                    refresh_bookings()
                    st.success("Prenotazione modificata con successo!")
