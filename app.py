from __future__ import annotations

import html
import json
import os
import random
import re
from io import BytesIO
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from docx import Document

# Charger les variables d'environnement
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL_NAME = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
MAX_CONTEXT_CHUNKS = 2


QUESTION_PROMPT = """
Tu es un formateur exigeant.
A partir du contexte fourni, genere exactement une question de comprehension pour tester l'utilisateur.
La question doit etre precise, basee uniquement sur le document, et d'un niveau raisonnable.

Reponds uniquement en JSON valide avec ce schema :
{{
  "question": "...",
  "answer": "...",
  "explanation": "..."
}}

Contraintes CRITIQUES :
- La question doit porter UNIQUEMENT sur le contenu pédagogique : concepts, définitions, étapes, règles, comparaisons, exemples.
- INTERDICTION ABSOLUE :
  * Questions sur la structure du document (chapitre, section, page, titre)
  * Questions sur les métadonnées (auteur, institution, droits, réservation, copyright)
  * Questions sur l'organisation (énumérer, lister, combien de)
  * Questions sur les droits ou l'utilisation (réservée à, institution, formation initiale)
  * Questions vagues ou sans réponse claire dans le contexte

- La question doit pouvoir etre resolue uniquement avec le contexte fourni.
- La reponse attendue doit etre concise mais exacte.
- L'explication doit justifier clairement la bonne réponse.
- Préfère une question sur un concept, une définition, une étape, une règle importante, une comparaison utile ou un exemple pédagogique.
"""


CORRECTION_PROMPT = """
Tu corriges la reponse d'un utilisateur a partir d'un document pedagogique.
Utilise uniquement le contexte ci-dessous.

Question : {question}
Reponse attendue : {expected_answer}
Reponse utilisateur : {user_answer}

Reponds uniquement en JSON valide avec ce schema :
{{
  "is_correct": true,
  "score": 0,
  "feedback": "...",
  "correct_answer": "...",
  "explanation": "..."
}}

Contraintes :
- score est un entier entre 0 et 10.
- is_correct vaut true seulement si la reponse est globalement correcte.
- feedback doit etre clair et utile pour apprendre.
- correct_answer doit rester fidele au document.
"""


@st.cache_resource
def get_llm() -> ChatGroq:
    if not GROQ_API_KEY:
        st.error("❌ Clé API non configurée. Veuillez créer un fichier .env")
        st.stop()
    return ChatGroq(model=MODEL_NAME, temperature=0.2, api_key=GROQ_API_KEY)


@st.cache_resource
def get_json_llm() -> ChatGroq:
    if not GROQ_API_KEY:
        st.error("❌ Clé API non configurée. Veuillez créer un fichier .env")
        st.stop()
    return ChatGroq(model=MODEL_NAME, temperature=0.1, api_key=GROQ_API_KEY)


@st.cache_resource
def get_question_llm() -> ChatGroq:
    if not GROQ_API_KEY:
        st.error("❌ Clé API non configurée. Veuillez créer un fichier .env")
        st.stop()
    return ChatGroq(model=MODEL_NAME, temperature=0.35, api_key=GROQ_API_KEY)


def is_focus_text_usable(text: str) -> bool:
    normalized = text.casefold()
    if len(normalized.split()) < 80:
        return False

    banned_markers = [
        "copyright",
        "tous droits réservés",
        "droits réservés",
        "reproduction",
        "formation initiale",
        "institution",
        "publié par",
        "édité par",
        "sommaire",
        "table des matières",
    ]
    matches = sum(marker in normalized for marker in banned_markers)
    return matches < 2


@st.cache_data(show_spinner=False, max_entries=8)
def extract_focus_text(file_name: str, file_bytes: bytes) -> tuple[str, str]:
    lower_name = file_name.lower()
    if lower_name.endswith(".pdf"):
        reader = PdfReader(BytesIO(file_bytes))
        indexed_pages = [
            (page_index, page.extract_text() or "")
            for page_index, page in enumerate(reader.pages)
        ]
        non_empty_pages = [
            (page_index, text.strip())
            for page_index, text in indexed_pages
            if text.strip()
        ]
        if not non_empty_pages:
            return "", "Aucune page exploitable"

        usable_pages = [
            (page_index, text)
            for page_index, text in non_empty_pages
            if is_focus_text_usable(text)
        ]

        candidate_pages = usable_pages or non_empty_pages

        page_index, text = random.choice(candidate_pages)
        return text, f"Page aléatoire sélectionnée: {page_index + 1}/{len(reader.pages)}"

    if lower_name.endswith(".docx"):
        document = Document(BytesIO(file_bytes))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
        non_empty_paragraphs = [text for text in paragraphs if text]
        if not non_empty_paragraphs:
            return "", "Aucun paragraphe exploitable"

        window_size = min(8, len(non_empty_paragraphs))
        max_start = max(0, len(non_empty_paragraphs) - window_size)
        candidate_windows: list[tuple[int, str]] = []
        fallback_windows: list[tuple[int, str]] = []

        for start_index in range(max_start + 1):
            excerpt = "\n".join(non_empty_paragraphs[start_index : start_index + window_size]).strip()
            fallback_windows.append((start_index, excerpt))
            if is_focus_text_usable(excerpt):
                candidate_windows.append((start_index, excerpt))

        selected_start, excerpt = random.choice(candidate_windows or fallback_windows)
        return excerpt, f"Bloc sélectionné dans le document Word: paragraphes {selected_start + 1} à {selected_start + window_size}"

    raise ValueError("Format de fichier non supporte")


@st.cache_data(show_spinner=False, max_entries=8)
def split_document(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def _extract_json(content: str) -> dict[str, Any]:
    normalized = content.strip()
    if normalized.startswith("```"):
        normalized = re.sub(r"^```(?:json)?\s*|\s*```$", "", normalized, flags=re.DOTALL)

    decoder = json.JSONDecoder()
    candidates = [normalized, *re.findall(r"\{.*?\}", normalized, re.DOTALL)]
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            payload, _ = decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload

    raise ValueError("Aucune réponse JSON exploitable n'a été trouvée")


def pick_context(chunks: list[str], index: int) -> str:
    if not chunks:
        return ""

    start = (index * MAX_CONTEXT_CHUNKS) % len(chunks)
    selected = []
    for offset in range(min(MAX_CONTEXT_CHUNKS, len(chunks))):
        selected.append(chunks[(start + offset) % len(chunks)])
    return "\n\n".join(selected)


def build_context_candidates(chunks: list[str], question_index: int) -> list[str]:
    if not chunks:
        return []

    candidates: list[str] = []
    seen_contexts: set[str] = set()

    def add_candidate(candidate: str) -> None:
        normalized = candidate.strip()
        if not normalized or normalized in seen_contexts:
            return
        candidates.append(normalized)
        seen_contexts.add(normalized)

    add_candidate(pick_context(chunks, question_index))

    for offset in range(len(chunks)):
        start = (question_index + offset) % len(chunks)
        add_candidate(chunks[start])

    if len(chunks) > 1:
        for offset in range(len(chunks)):
            start = (question_index + offset) % len(chunks)
            pair = [chunks[start], chunks[(start + 1) % len(chunks)]]
            add_candidate("\n\n".join(pair))

    return candidates


def is_question_acceptable(question: str) -> bool:
    normalized = question.casefold().strip()
    if not normalized:
        return False

    banned_fragments = [
        # Structure du document
        "chapitre",
        "section",
        "page",
        "titre",
        "nom du fichier",
        "dans le document",
        "dans ce document",
        "composant de base créé",
        
        # Métadonnées & droits
        "institution",
        "réservée",
        "auteur",
        "droit",
        "copyright",
        "propriété",
        "reproduction",
        "formation initiale",
        "édité par",
        "publié par",
        "version",
        
        # Questions trop vagues
        "combien de",
        "nombre de",
        "liste",
        "énumérer",
    ]
    return not any(fragment in normalized for fragment in banned_fragments)


def _normalize_question_bank(payload: dict[str, Any], count: int) -> list[dict[str, str]]:
    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, list):
        raise ValueError("Le modèle n'a pas renvoyé une liste de questions exploitable")

    cleaned_questions: list[dict[str, str]] = []
    seen_questions: set[str] = set()

    for item in raw_questions:
        if not isinstance(item, dict):
            continue

        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        explanation = str(item.get("explanation", "")).strip()

        if not question or not answer or not explanation:
            continue

        normalized_question = question.casefold()
        if normalized_question in seen_questions:
            continue

        cleaned_questions.append(
            {
                "question": question,
                "answer": answer,
                "explanation": explanation,
            }
        )
        seen_questions.add(normalized_question)

        if len(cleaned_questions) == count:
            break

    if not cleaned_questions:
        raise ValueError("Aucune question valide n'a pu être générée")

    return cleaned_questions


def generate_question(chunks: list[str], question_index: int) -> dict[str, Any]:
    seen_questions = {
        question.casefold().strip()
        for question in st.session_state.get("asked_questions", [])
        if question.strip()
    }
    llm = get_question_llm()
    previous_questions = [question for question in st.session_state.get("asked_questions", []) if question.strip()]
    previous_questions_block = "\n".join(f"- {question}" for question in previous_questions[-8:])
    contexts = build_context_candidates(chunks, question_index)

    for attempt, context in enumerate(contexts[:8], start=1):
        prompt = (
            f"{QUESTION_PROMPT}\n\n"
            f"Question numero : {question_index + 1}\n"
            f"Tentative : {attempt}\n"
            f"Questions deja posees a eviter :\n{previous_questions_block or '- Aucune'}\n\n"
            f"Contexte documentaire :\n{context}"
        )
        response = llm.invoke(prompt)
        payload = _extract_json(response.content)
        question = str(payload.get("question", "")).strip()
        answer = str(payload.get("answer", "")).strip()
        explanation = str(payload.get("explanation", "")).strip()
        normalized_question = question.casefold()

        if (
            is_question_acceptable(question)
            and answer
            and explanation
            and normalized_question not in seen_questions
        ):
            return {
                "question": question,
                "answer": answer,
                "explanation": explanation,
            }

    raise ValueError("Impossible de générer une autre question claire et différente pour ce fichier")


def correct_answer(
    chunks: list[str],
    question: str,
    expected_answer: str,
    user_answer: str,
    question_index: int,
) -> dict[str, Any]:
    llm = get_json_llm()
    context = pick_context(chunks, question_index)
    prompt = (
        CORRECTION_PROMPT.format(
            question=question,
            expected_answer=expected_answer,
            user_answer=user_answer,
        )
        + f"\n\nContexte documentaire :\n{context}"
    )
    response = llm.invoke(prompt)
    return _extract_json(response.content)


def init_state() -> None:
    defaults = {
        "document_text": "",
        "chunks": [],
        "question_index": 0,
        "asked_questions": [],
        "current_question": None,
        "last_correction": None,
        "source_name": "",
        "source_focus_label": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_quiz_state() -> None:
    st.session_state.document_text = ""
    st.session_state.chunks = []
    st.session_state.question_index = 0
    st.session_state.asked_questions = []
    st.session_state.current_question = None
    st.session_state.last_correction = None
    st.session_state.source_name = ""
    st.session_state.source_focus_label = ""


def reset_quiz_state(
    source_name: str,
    document_text: str,
    chunks: list[str],
    source_focus_label: str,
) -> None:
    st.session_state.source_name = source_name
    st.session_state.document_text = document_text
    st.session_state.chunks = chunks
    st.session_state.question_index = 0
    st.session_state.asked_questions = []
    st.session_state.current_question = None
    st.session_state.last_correction = None
    st.session_state.source_focus_label = source_focus_label


def ensure_question_available() -> bool:
    return st.session_state.current_question is not None


def set_current_question(question: dict[str, Any]) -> None:
    st.session_state.current_question = question
    question_text = str(question.get("question", "")).strip()
    if question_text and question_text not in st.session_state.asked_questions:
        st.session_state.asked_questions.append(question_text)


def render_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(255, 206, 161, 0.55), transparent 28%),
                radial-gradient(circle at top right, rgba(90, 153, 255, 0.22), transparent 30%),
                linear-gradient(180deg, #fffaf3 0%, #f5efe3 100%);
        }

        .stApp::before,
        .stApp::after {
            content: "";
            position: fixed;
            width: 260px;
            height: 260px;
            border-radius: 999px;
            filter: blur(14px);
            opacity: 0.35;
            z-index: 0;
            animation: drift 12s ease-in-out infinite;
        }

        .stApp::before {
            background: rgba(255, 127, 80, 0.34);
            top: 6%;
            right: -60px;
        }

        .stApp::after {
            background: rgba(41, 91, 255, 0.18);
            bottom: 8%;
            left: -70px;
            animation-delay: -4s;
        }

        .block-container {
            padding-top: 2.2rem;
            padding-bottom: 3rem;
            position: relative;
            z-index: 1;
        }

        .hero-panel,
        .glass-card {
            background: rgba(255, 252, 247, 0.78);
            border: 1px solid rgba(165, 117, 70, 0.16);
            border-radius: 28px;
            box-shadow: 0 18px 55px rgba(96, 60, 29, 0.10);
            backdrop-filter: blur(10px);
        }

        .hero-panel {
            padding: 1.7rem 1.7rem 1.5rem 1.7rem;
            margin-bottom: 1.1rem;
            animation: riseIn 0.7s ease-out;
        }

        .hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.35rem 0.85rem;
            border-radius: 999px;
            background: rgba(210, 94, 50, 0.11);
            color: #8d3d1f;
            font-size: 0.92rem;
            font-weight: 700;
            letter-spacing: 0.02em;
        }

        .hero-title {
            margin: 0.9rem 0 0.45rem 0;
            color: #23150d;
            font-size: 3rem;
            line-height: 1.05;
            font-weight: 800;
        }

        .hero-copy {
            margin: 0;
            max-width: 760px;
            color: #554338;
            font-size: 1.02rem;
            line-height: 1.7;
        }

        .metric-ribbon {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.85rem;
            margin: 1rem 0 1.4rem 0;
        }

        .metric-tile {
            padding: 1rem 1rem 0.95rem 1rem;
            border-radius: 22px;
            background: linear-gradient(145deg, rgba(255,255,255,0.90), rgba(252,245,235,0.95));
            border: 1px solid rgba(193, 152, 118, 0.24);
            box-shadow: 0 14px 40px rgba(120, 79, 48, 0.08);
            animation: riseIn 0.8s ease-out;
        }

        .metric-label {
            color: #866b58;
            font-size: 0.84rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 700;
        }

        .metric-value {
            color: #1f130d;
            font-size: 1.8rem;
            font-weight: 800;
            margin-top: 0.2rem;
        }

        .metric-note {
            color: #6b5748;
            font-size: 0.92rem;
            margin-top: 0.28rem;
        }

        .glass-card {
            padding: 1.15rem 1.2rem;
            margin-top: 0.8rem;
            animation: riseIn 0.9s ease-out;
        }

        .question-shell {
            padding: 1rem 1.15rem;
            border-radius: 22px;
            background: linear-gradient(180deg, rgba(255, 252, 248, 0.92), rgba(248, 241, 232, 0.95));
            border: 1px solid rgba(203, 165, 126, 0.25);
        }

        .question-tag {
            display: inline-block;
            margin-bottom: 0.7rem;
            padding: 0.28rem 0.7rem;
            border-radius: 999px;
            background: rgba(54, 107, 217, 0.10);
            color: #2c5eb8;
            font-size: 0.84rem;
            font-weight: 700;
        }

        .question-text {
            color: #2a1a10;
            font-size: 1.08rem;
            line-height: 1.7;
            font-weight: 600;
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stFormSubmitButton"] > button {
            border-radius: 999px;
            border: 0;
            min-height: 2.9rem;
            padding: 0.55rem 1.2rem;
            font-weight: 700;
            transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
            box-shadow: 0 10px 28px rgba(124, 76, 38, 0.18);
        }

        div[data-testid="stButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover {
            transform: translateY(-1px) scale(1.01);
        }

        div[data-testid="stProgressBar"] > div > div {
            background: linear-gradient(90deg, #d85a2d 0%, #ff9f5a 52%, #f5c86b 100%);
        }

        div[data-testid="stTextArea"] textarea {
            border-radius: 20px;
            background: rgba(255, 252, 248, 0.92);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(255, 247, 236, 0.95) 0%, rgba(248, 239, 224, 0.98) 100%);
        }

        @keyframes riseIn {
            from {
                opacity: 0;
                transform: translateY(18px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes drift {
            0%, 100% {
                transform: translate3d(0, 0, 0);
            }
            50% {
                transform: translate3d(0, -14px, 0);
            }
        }

        @media (max-width: 900px) {
            .hero-title {
                font-size: 2.15rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        st.info(f"""
        **Modèle IA:** {MODEL_NAME}
        
        **Format:** PDF, DOCX
        
        **Mode:** Une question à la fois
        """)
        
        st.markdown("---")
        st.markdown("### 📚 À propos")
        st.caption("""
        Cette application génère des questions intelligentes à partir de vos documents.
        
        **Expérience:** quiz interactif avec correction automatique
        """)
        
        st.markdown("---")
        st.markdown("### 🔗 Ressources")
        col1, col2 = st.columns(2)
        with col1:
            st.link_button("📖 Documentation", "https://github.com/hamzamachnaoui/Ai_quiz_interactif")
        with col2:
            st.link_button("🔗 Console API", "https://console.groq.com")


def main() -> None:
    st.set_page_config(
        page_title="🧠 Quiz interactif - Générateur de questions",
        page_icon=":material/local_library:",
        layout="wide",
    )
    init_state()
    render_theme()
    
    # En-tête principal
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h1 style='font-size: 3em; color: #d85a2d; margin: 0;'>🧠 Quiz interactif</h1>
        <p style='font-size: 1.2em; color: #666; margin: 0.5rem 0 0 0;'>Générez des questions intelligentes à partir de vos documents</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    render_sidebar()
    
    # Affichage principal
    if not st.session_state.chunks:
        # Section Upload
        col1, col2 = st.columns([1.5, 1])
        
        with col1:
            st.markdown("### 📄 Étape 1 : Importer votre document")
            uploaded_file = st.file_uploader(
                "Sélectionnez un fichier PDF ou DOCX",
                type=["pdf", "docx"],
                help="Cours, documentation, support de formation...",
                key="doc_uploader",
                label_visibility="collapsed"
            )
            
            if uploaded_file:
                st.info(f"✅ Fichier sélectionné: **{uploaded_file.name}**")
                
                st.markdown("### 📊 Étape 2 : Traiter le document")
                if st.button(
                    "🚀 Lancer l'analyse",
                    type="primary",
                    use_container_width=True,
                    key="analyze_btn"
                ):
                    file_bytes = uploaded_file.getvalue()
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Extraction
                        status_text.info("📖 Extraction du contenu...")
                        progress_bar.progress(25)
                        text, source_focus_label = extract_focus_text(uploaded_file.name, file_bytes)
                        
                        if not text.strip():
                            st.error("❌ Le document ne contient pas de texte exploitable.")
                            st.stop()
                        
                        # Split
                        status_text.info("✂️ Segmentation du document...")
                        progress_bar.progress(50)
                        chunks = split_document(text)
                        
                        # Génération première question
                        status_text.info("🤖 Génération de la première question...")
                        progress_bar.progress(75)
                        first_question = generate_question(chunks, 0)
                        progress_bar.progress(100)
                        
                        # Sauvegarde état
                        reset_quiz_state(uploaded_file.name, text, chunks, source_focus_label)
                        set_current_question(first_question)
                        
                        status_text.success("✨ Document analysé! Commencez à répondre aux questions.")
                        st.rerun()
                        
                    except Exception as exc:
                        st.error(f"❌ Erreur: {exc}")
                    finally:
                        status_text.empty()
                        progress_bar.empty()
        
        with col2:
            st.markdown("### 💡 Comment ça marche?")
            st.markdown("""
            1. **Importez** un PDF ou DOCX
            2. **Lancez** l'analyse 
            3. **Répondez** aux questions générées
            4. **Obtenez** une correction intelligente
            
            **Expérience fluide** ⚡ - analyse et correction intelligentes
            """)
    
    else:
        # Document chargé - Afficher l'état
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📁 Fichier", st.session_state.source_name.split("/")[-1][:20])
        with col2:
            st.metric("❓ Question", f"{st.session_state.question_index + 1}")
        with col3:
            st.metric("📊 Segments", len(st.session_state.chunks))
        with col4:
            if st.button("🔄 Nouveau document", use_container_width=True, key="reset_doc_top"):
                clear_quiz_state()
                st.rerun()
        
        st.markdown("---")
        
        # Afficher la question
        if st.session_state.current_question:
            current_question = st.session_state.current_question
            
            st.markdown("### ❓ Votre Question")
            st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #fff5f0 0%, #ffeae3 100%);
                border-left: 4px solid #d85a2d;
                padding: 1.5rem;
                border-radius: 8px;
                font-size: 1.15em;
                line-height: 1.6;
            '>
            {html.escape(current_question['question'])}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 💬 Saisissez votre réponse")
            
            with st.form(key=f"answer_form_{st.session_state.question_index}"):
                user_answer = st.text_area(
                    "Votre réponse",
                    placeholder="Écrivez votre réponse ici...",
                    height=120,
                    label_visibility="collapsed",
                    key=f"user_answer_{st.session_state.question_index}",
                )
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    submitted = st.form_submit_button(
                        "✅ Soumettre et obtenir la correction",
                        type="primary",
                        use_container_width=True
                    )
                with col2:
                    if st.form_submit_button("⏭️ Passer (sans corriger)", use_container_width=True, key=f"skip_q{st.session_state.question_index}"):
                        try:
                            with st.spinner("Génération nouvelle question..."):
                                st.session_state.question_index += 1
                                next_question = generate_question(
                                    st.session_state.chunks,
                                    st.session_state.question_index,
                                )
                                set_current_question(next_question)
                                st.session_state.last_correction = None
                            st.rerun()
                        except Exception as exc:
                            st.session_state.question_index -= 1
                            st.error(f"❌ Erreur: {exc}")
            
                if submitted:
                    if not user_answer.strip():
                        st.warning("⚠️ Veuillez saisir une réponse!")
                    else:
                        with st.spinner("🤔 Correction en cours..."):
                            try:
                                st.session_state.last_correction = correct_answer(
                                    st.session_state.chunks,
                                    current_question["question"],
                                    current_question["answer"],
                                    user_answer,
                                    st.session_state.question_index,
                                )
                            except Exception as exc:
                                st.error(f"❌ Erreur de correction: {exc}")
        
        # Afficher la correction
        if st.session_state.last_correction:
            correction = st.session_state.last_correction
            score = int(correction.get("score", 0))
            is_correct = bool(correction.get("is_correct", False))
            
            st.markdown("---")
            st.markdown("### 📋 Correction")
            
            if is_correct:
                st.success(f"✅ **Bonne réponse!** Score: {score}/10")
            else:
                st.warning(f"⚠️ **À améliorer.** Score: {score}/10")
            
            with st.expander("💡 Détails de la correction", expanded=True):
                st.markdown("**Votre retour:**")
                st.info(correction.get("feedback", ""))
                
                st.markdown("**Réponse correcte:**")
                st.success(correction.get("correct_answer", ""))
                
                st.markdown("**Explication:**")
                st.info(correction.get("explanation", ""))
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⏭️ Question suivante", type="primary", use_container_width=True, key=f"next_q_after_correction_{st.session_state.question_index}"):
                    try:
                        with st.spinner("Génération nouvelle question..."):
                            st.session_state.question_index += 1
                            next_question = generate_question(
                                st.session_state.chunks,
                                st.session_state.question_index,
                            )
                            set_current_question(next_question)
                            st.session_state.last_correction = None
                        st.rerun()
                    except Exception as exc:
                        st.session_state.question_index -= 1
                        st.error(f"❌ Erreur: {exc}")
            
            with col2:
                if st.button("🔄 Nouveau document", use_container_width=True, key=f"reset_doc_after_correction_{st.session_state.question_index}"):
                    clear_quiz_state()
                    st.rerun()


if __name__ == "__main__":
    main()
