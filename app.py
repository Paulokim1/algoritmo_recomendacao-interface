import uuid
import requests
import streamlit as st

# Constants
API_URL = "https://cc9by7c67e.execute-api.us-east-1.amazonaws.com/dev/chat"

# Initialize session state defaults
defaults = {
    "session_started": False,
    "session_id": None,
    "id_pessoa": None,
    "messages": [],
    "session_state": None,
    "output": {},
    "selected_case": None,
    "selected_exam": None,
    "subgroup": None,
}
for key, val in defaults.items():
    st.session_state.setdefault(key, val)

# API interaction
def call_api(message: list):
    headers = {
        "x-api-key": st.session_state.chat_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "session_id": st.session_state.session_id,
        "id_pessoa": st.session_state.id_pessoa,
        "message": message,
    }
    response = requests.post(API_URL, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

# Start a new session (initial or subsequent)
def start_session():
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages.clear()
    data = call_api(["START_SESSION"])
    st.session_state.session_started = True
    st.session_state.session_state = data.get("session_state")
    st.session_state.output = data.get("output", {})

# Renew session while preserving credentials
def renew_session():
    # Preserve credentials
    api_key = st.session_state.chat_api_key
    id_pessoa = st.session_state.id_pessoa
    # Reset all defaults
    for key, val in defaults.items():
        st.session_state[key] = val
    # Restore credentials
    st.session_state.chat_api_key = api_key
    st.session_state.id_pessoa = id_pessoa
    # Start fresh session
    start_session()

# Sidebar: login or new-session button
def render_sidebar():
    st.sidebar.header("🔒 Sessão")
    if not st.session_state.session_started:
        with st.sidebar.form("login_form", clear_on_submit=False):
            st.session_state.chat_api_key = st.text_input(
                "API Key da API", type="password"
            )
            st.session_state.id_pessoa = st.text_input(
                "ID da Pessoa"
            )
            if st.form_submit_button("Iniciar Sessão"):
                if not st.session_state.chat_api_key or not st.session_state.id_pessoa:
                    st.sidebar.error("Preencha API Key e ID da Pessoa.")
                else:
                    start_session()
                    st.sidebar.success("Sessão iniciada!")
                    st.sidebar.markdown(f"**ID da Pessoa:** {st.session_state.id_pessoa}")
                    st.sidebar.markdown(f"**Session ID:** {st.session_state.session_id}")
    else:
        st.sidebar.markdown(f"**ID da Pessoa:** {st.session_state.id_pessoa}")
        st.sidebar.markdown(f"**Session ID:** {st.session_state.session_id}")
        
        if st.sidebar.button("Iniciar outra sessão"):
            with st.spinner(""):
                renew_session()
                st.experimental_rerun()

# Display chat history
def render_chat_history():
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

# Handle option-based flows
def render_options():
    state = st.session_state.session_state
    if state == 0:
        st.write("Por favor, escolha uma das opções abaixo:")
        for case, text in st.session_state.output.items():
            if st.button(text, key=case):
                st.session_state.selected_case = case
    elif state == 2:
        st.write("Escolha um dos exames abaixo:")
        for exam in st.session_state.output:
            cod = exam["cod_prod_med"]
            with st.container(border=True):
                st.markdown(f"**{exam['dsc_prod_med']}**")
                st.markdown(f"Data de Emissão: {exam['dat_emissao']}")
                if st.button("Selecionar", key=f"exam_{cod}"):
                    st.session_state.selected_exam = cod

# Process selected_case
def process_selection():
    if st.session_state.session_state == 0:
        choice = st.session_state.selected_case
    elif st.session_state.session_state == 2:
        choice = st.session_state.selected_exam
    else:
        return
    if not choice:
        return
    with st.spinner(""):
        data = call_api([choice])
    st.session_state.session_state = data.get("session_state")
    st.session_state.output = data.get("output")

    if st.session_state.session_state == 1:
        reply = data.get("output")
        if isinstance(reply, list):
            reply = reply[0]
        st.session_state.messages.append({"role": "assistant", "content": reply})

    if st.session_state.session_state == 2:
        if not st.session_state.output:
            st.write("⚠️ Atenção!")
            with st.container(border=True):
                st.write(f"Paciente não possui exames registardos no sistema")
        else:
            render_options()

    if st.session_state.session_state == 3:
        if not st.session_state.output:
            st.write("⚠️ Atenção!")
            with st.container(border=True):
                st.write(f"Não há médicos que realizem este procedimento")
        else:
            render_medic_list()

        

# Regular chat input
def chat_input_area():
    if st.session_state.session_state != 1:
        return
    prompt = st.chat_input("Digite sua mensagem:")
    if not prompt:
        return
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    with st.spinner(""):
        data = call_api([prompt])
    st.session_state.session_state = data.get("session_state")
    st.session_state.subgroup = data.get("subgroup")
    st.session_state.output = data.get("output")
    if st.session_state.session_state == 3:
        render_medic_list()
    else:
        st.session_state.messages.append({"role": "assistant", "content": st.session_state.output})
        st.chat_message("assistant").write(st.session_state.output)

# Render the list of doctors
def render_medic_list():
    st.write("Segue a lista de médicos:")
    with st.container(border=True):
        st.write(f"**Subgrupo:** {st.session_state.subgroup}")
        st.write("Lista de Médicos:")
        st.write(st.session_state.output)

# Main app
def main():
    st.set_page_config(page_title="💬 Recomendação POC")
    render_sidebar()
    st.title("💬 Algoritmo de Recomendação - POC")
    if not st.session_state.session_started:
        st.info("Clique em **Iniciar Sessão** na barra lateral.")
        return
    if st.session_state.session_state in [0, 2]:
        render_options()
        process_selection()
    if st.session_state.session_state == 1:
        render_chat_history()
        chat_input_area()

if __name__ == "__main__":
    main()
