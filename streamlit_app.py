import streamlit as st
from pydantic import ValidationError

from supportflow.client import send_message
from supportflow.config import Settings
from supportflow.models import MAX_MESSAGE_CHARS


def render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message.get("is_error", False):
            st.error(message["text"])
        else:
            st.text(message["text"])


def main() -> None:
    st.set_page_config(
        page_title="SupportFlow — soporte técnico", page_icon="💬", layout="centered"
    )
    st.title("SupportFlow")
    st.caption("Cuéntanos qué necesitas para configurar el producto o resolver una incidencia.")
    st.info("Las respuestas se generan con Azure OpenAI a través del backend seguro.")

    try:
        settings = Settings()
    except ValidationError:
        st.error("El servicio no está configurado correctamente. Inténtalo de nuevo más tarde.")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.sidebar:
        st.subheader("Tu conversación")
        st.caption("El historial permanece en esta sesión. Cada mensaje se envía por separado.")
        if st.button("Limpiar conversación", key="clear_chat"):
            st.session_state.messages = []

    for message in st.session_state.messages:
        render_message(message)

    prompt = st.chat_input(
        "Escribe tu consulta…",
        key="message_input",
        max_chars=MAX_MESSAGE_CHARS,
        submit_mode="disable",
    )
    if prompt is not None:
        user_message = {"role": "user", "text": prompt}
        st.session_state.messages.append(user_message)
        render_message(user_message)

        with st.spinner("Enviando tu mensaje…"):
            result = send_message(
                prompt, api_url=str(settings.api_url), timeout=settings.http_timeout_seconds
            )

        reply = {"role": "assistant", "text": result.text, "is_error": result.is_error}
        st.session_state.messages.append(reply)
        render_message(reply)


main()
