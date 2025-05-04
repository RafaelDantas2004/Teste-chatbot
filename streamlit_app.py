# Versão com suporte a OCR no Streamlit Cloud via EasyOCR
import streamlit as st
import os
from PIL import Image
import time
import json
import pdfplumber
import docx
from io import BytesIO
from openai import OpenAI
import easyocr
import numpy as np

# Configurações iniciais
st.set_page_config(
    page_title="TJCE Professor Virtual",
    page_icon="🏛️",
    layout="wide",
)

# Caminho para a logo do bot
LOGO_BOT_PATH = "assets/icon_tjce.jpg"
ICON_PATH = "assets/icon_car.jpg"

if os.path.exists(ICON_PATH):
    col1, col2 = st.columns([1.5, 4])
    with col1:
        st.image(ICON_PATH, width=30)
    with col2:
        st.title("Professor Virtual TJCE")
else:
    st.title("Professor Virtual TJCE")

st.markdown(
    '<p class="subtitulo">Olá, tudo bem? Sou um assistente virtual feito pelo TJCE em parceria com o Instituto Publix para te auxiliar e te dar apoio na realização dos cursos e capacitações ofertados.</p>',
    unsafe_allow_html=True
)

if "mensagens_chat" not in st.session_state:
    st.session_state.mensagens_chat = []

def salvar_estado():
    estado = {"mensagens_chat": st.session_state.mensagens_chat}
    with open("estado_bot.json", "w") as f:
        json.dump(estado, f)

def carregar_estado():
    if os.path.exists("estado_bot.json"):
        with open("estado_bot.json", "r") as f:
            estado = json.load(f)
            st.session_state.mensagens_chat = estado.get("mensagens_chat", [])

def limpar_historico():
    st.session_state.mensagens_chat = []
    salvar_estado()

def extrair_texto_arquivo(arquivo):
    nome = arquivo.name.lower()
    if nome.endswith(".txt"):
        return arquivo.read().decode("utf-8")
    elif nome.endswith(".pdf"):
        with pdfplumber.open(BytesIO(arquivo.read())) as pdf:
            return "\n".join([page.extract_text() or "" for page in pdf.pages])
    elif nome.endswith(".docx"):
        doc = docx.Document(arquivo)
        return "\n".join([p.text for p in doc.paragraphs])
    elif nome.endswith((".png", ".jpg", ".jpeg")):
        try:
            image = Image.open(arquivo).convert("RGB")
            img_array = np.array(image)
            reader = easyocr.Reader(['pt', 'en'], gpu=False)
            results = reader.readtext(img_array)
            return "\n".join([r[1] for r in results])
        except Exception as e:
            return f"[Erro ao usar EasyOCR: {str(e)}]"
    return ""

def dividir_texto(texto, max_tokens=800):
    palavras = texto.split()
    chunks = []
    atual = ""
    for p in palavras:
        if len(atual.split()) + len(p.split()) <= max_tokens:
            atual += p + " "
        else:
            chunks.append(atual.strip())
            atual = p + " "
    if atual:
        chunks.append(atual.strip())
    return chunks

def selecionar_chunks_relevantes(pergunta, chunks):
    palavras_chave = pergunta.lower().split()
    return [c for c in chunks if any(p in c.lower() for p in palavras_chave)][:4]

def gerar_resposta(pergunta, contexto):
    if not contexto:
        return "⚠️ Nenhum contexto foi carregado."

    chunks = dividir_texto(contexto)
    relevantes = selecionar_chunks_relevantes(pergunta, chunks)

    prompt = (
        "Você é um chatbot estratégico desenvolvido pela AD&M Consultoria, "
        "uma empresa especialista em gestão empresarial com foco em operações, finanças, marketing e estratégia. "
        "Seu papel é oferecer respostas inteligentes e críticas que ajudem o cliente a pensar de forma estratégica, "
        "tanto para dúvidas básicas quanto para geração de insights valiosos.\n\n"
    )

    for i, c in enumerate(relevantes):
        prompt += f"--- Parte {i+1} do Contexto ---\n{c}\n\n"

    mensagens = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": pergunta}
    ]

    try:
        time.sleep(1)
        client = OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=mensagens,
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erro ao gerar resposta: {str(e)}"

carregar_estado()

if os.path.exists(LOGO_BOT_PATH):
    try:
        LOGO_BOT = Image.open(LOGO_BOT_PATH)
        st.sidebar.image(LOGO_BOT, width=300)
    except:
        st.sidebar.markdown("**Logo não encontrada**")

api_key = st.sidebar.text_input("🔑 Chave API OpenAI", type="password")
if api_key:
    import openai
    openai.api_key = api_key
    if st.sidebar.button("🧹 Limpar Histórico do Chat"):
        limpar_historico()
        st.sidebar.success("Histórico limpo com sucesso!")
else:
    st.warning("Por favor, insira sua chave de API para continuar.")

arquivos = st.sidebar.file_uploader(
    "📎 Envie arquivos de contexto (PDF, DOCX, TXT, JPG, PNG)",
    type=["pdf", "docx", "txt", "jpg", "jpeg", "png"],
    accept_multiple_files=True
)

contexto = ""
if arquivos:
    for arq in arquivos:
        contexto += f"--- {arq.name} ---\n"
        contexto += extrair_texto_arquivo(arq)

user_input = st.chat_input("💬 Sua pergunta:")
if user_input and api_key:
    st.session_state.mensagens_chat.append({"user": user_input, "bot": None})
    resposta = gerar_resposta(user_input, contexto)
    st.session_state.mensagens_chat[-1]["bot"] = resposta
    salvar_estado()

if st.session_state.mensagens_chat:
    for mensagem in st.session_state.mensagens_chat:
        if mensagem["user"]:
            with st.chat_message("user"):
                st.markdown(f"**Você:** {mensagem['user']}")
        if mensagem["bot"]:
            with st.chat_message("assistant"):
                st.markdown(f"**AD&M Consultoria:**\n\n{mensagem['bot']}")
else:
    with st.chat_message("assistant"):
        st.markdown("👋 Olá! Envie arquivos e faça sua pergunta para obter insights estratégicos.")
