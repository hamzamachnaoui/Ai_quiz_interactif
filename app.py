from __future__ import annotations

import html
import json
import random
import re
from io import BytesIO
from typing import Any

import streamlit as st
from langchain_ollama import ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from docx import Document

MODEL_NAME = "mistral"
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

Contraintes :
- La question doit pouvoir etre resolue uniquement avec le contexte.
- La reponse attendue doit etre concise mais exacte.
- L'explication doit justifier clairement la bonne reponse.
- La question doit porter sur le fond du contenu, pas sur la structure du document.
- Interdiction de poser une question sur un numero de chapitre, une page, une section, un titre, un nom de fichier ou l'organisation du document.
- Evite les formulations vagues comme "dans le chapitre", "dans la section" ou "dans le document".
- Prefere une question sur un concept, une definition, une etape, une regle, une comparaison ou un exemple utile pour l'apprentissage.
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
def get_llm() -> ChatOllama:
    return ChatOllama(model=MODEL_NAME, temperature=0.2)


@st.cache_resource
def get_json_llm() -> ChatOllama:
    return ChatOllama(model=MODEL_NAME, temperature=0.1, format="json")


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

        page_index, text = random.choice(non_empty_pages)
        return text, f"Page aléatoire sélectionnée: {page_index + 1}/{len(reader.pages)}"

    if lower_name.endswith(".docx"):
        document = Document(BytesIO(file_bytes))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
        non_empty_paragraphs = [text for text in paragraphs if text]
        if not non_empty_paragraphs:
            return "", "Aucun paragraphe exploitable"

        window_size = min(8, len(non_empty_paragraphs))
        max_start = max(0, len(non_empty_paragraphs) - window_size)
        start_index = random.randint(0, max_start) if max_start else 0
        excerpt = "\n".join(non_empty_paragraphs[start_index : start_index + window_size]).strip()
        return excerpt, "Bloc aléatoire sélectionné dans le document Word"

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


def is_question_acceptable(question: str) -> bool:
    normalized = question.casefold().strip()
    if not normalized:
        return False

    banned_fragments = [
        "chapitre",
        "section",
        "page",
        "titre",
        "nom du fichier",
        "dans le document",
        "dans ce document",
        "composant de base créé",
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
    llm = get_json_llm()
    for attempt in range(6):
        context = pick_context(chunks, question_index + attempt)
        prompt = (
            f"{QUESTION_PROMPT}\n\n"
            f"Question numero : {question_index + 1}\n"
            f"Tentative : {attempt + 1}\n\n"
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
        if st.session_state.chunks:
            return

        st.header("Configuration")
        st.write(f"Modèle Ollama: {MODEL_NAME}")
        st.write("Formats acceptés: PDF, DOCX")
        st.write("Mode de génération: une question à la fois")
        st.caption(
            "Assurez-vous qu'Ollama est lancé et que le modèle mistral est disponible localement."
        )


def render_hero() -> None:
    st.markdown(
        """
        <section class="hero-panel">
            <div class="hero-kicker">Entraînement intelligent</div>
            <h1 class="hero-title">Transformez un document en session de quiz guidée</h1>
            <p class="hero-copy">
                Importez un support PDF ou Word, préparez un lot de questions dès le départ,
                puis laissez l'application corriger chaque réponse et enchaîner vers la suivante sans attente inutile.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_metrics() -> None:
    metrics = [
        ("moteur", f"Ollama / {MODEL_NAME}", "Génération locale des questions et corrections"),
        ("format", "PDF + DOCX", "Supports de cours, documentation et fiches"),
        ("rythme", "1 par 1", "Temps de réponse réduit à chaque génération"),
    ]
    tiles = []
    for label, value, note in metrics:
        tiles.append(
            f"<div class='metric-tile'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>"
        )
    st.markdown(f"<section class='metric-ribbon'>{''.join(tiles)}</section>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="Quiz documentaire Ollama",
        page_icon=":material/local_library:",
        layout="wide",
    )
    init_state()
    render_theme()
    render_sidebar()
    if not st.session_state.chunks:
        render_hero()
        render_metrics()

    uploaded_file = None
    if not st.session_state.chunks:
        uploaded_file = st.file_uploader(
            "Importer un document pédagogique",
            type=["pdf", "docx"],
            help="Vous pouvez importer une documentation, un cours ou un support de formation.",
        )

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        if st.button("Analyser et préparer le quiz", type="primary"):
            progress_bar = st.progress(0, text="Initialisation du document...")
            progress_note = st.empty()
            try:
                progress_note.caption("Sélection d'un extrait aléatoire du document...")
                text, source_focus_label = extract_focus_text(uploaded_file.name, file_bytes)
                progress_bar.progress(20, text="Texte extrait")

                if not text.strip():
                    st.error("Le document ne contient pas de texte exploitable.")
                    st.stop()

                progress_note.caption("Découpage du document en segments pédagogiques...")
                chunks = split_document(text)
                progress_bar.progress(70, text="Segments préparés")

                progress_note.caption("Génération de la première question...")
                first_question = generate_question(chunks, 0)
                progress_bar.progress(100, text="Quiz prêt")

                reset_quiz_state(uploaded_file.name, text, chunks, source_focus_label)
                set_current_question(first_question)
                st.success("Le document a été analysé et la première question est prête.")
            except Exception as exc:
                st.error(f"Impossible de préparer le quiz: {exc}")
            finally:
                progress_note.empty()
                progress_bar.empty()

    if st.session_state.chunks:
        st.markdown("<section class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Document chargé", icon=":material/description:")
        document_col, batch_col, more_col, reset_col = st.columns([2.0, 1.0, 1.2, 1.0])
        with document_col:
            st.write(f"Fichier: {st.session_state.source_name}")
            if st.session_state.source_focus_label:
                st.caption(st.session_state.source_focus_label)
            st.caption(f"Nombre de segments analysés: {len(st.session_state.chunks)}")
        with batch_col:
            st.metric(
                "Question actuelle",
                st.session_state.question_index + 1,
            )
        with more_col:
            if st.button("Générer la suivante", width="stretch"):
                try:
                    with st.spinner("Génération de la prochaine question..."):
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
                    st.error(f"Impossible d'ajouter plus de questions: {exc}")
        with reset_col:
            if st.button("Changer de document", width="stretch"):
                clear_quiz_state()
                st.rerun()
        st.markdown("</section>", unsafe_allow_html=True)

    current_question = st.session_state.current_question
    if current_question:
        st.markdown("<section class='glass-card'>", unsafe_allow_html=True)
        st.subheader(f"Question {st.session_state.question_index + 1}", icon=":material/quiz:")
        st.markdown(
            f"""
            <div class="question-shell">
                <div class="question-tag">Question active</div>
                <div class="question-text">{html.escape(current_question['question'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form(key=f"answer_form_{st.session_state.question_index}"):
            user_answer = st.text_area(
                "Votre réponse",
                placeholder="Saisissez ici votre réponse...",
                key=f"user_answer_{st.session_state.question_index}",
                height=180,
            )
            submitted = st.form_submit_button("Corriger la réponse", width="stretch")

        if submitted:
            if not user_answer.strip():
                st.warning("Veuillez saisir une réponse avant la correction.")
            else:
                with st.spinner("Correction en cours..."):
                    try:
                        st.session_state.last_correction = correct_answer(
                            st.session_state.chunks,
                            current_question["question"],
                            current_question["answer"],
                            user_answer,
                            st.session_state.question_index,
                        )
                    except Exception as exc:
                        st.error(f"Impossible de corriger la réponse: {exc}")
        st.markdown("</section>", unsafe_allow_html=True)

    if st.session_state.last_correction:
        correction = st.session_state.last_correction
        st.markdown("<section class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Correction", icon=":material/fact_check:")

        score = int(correction.get("score", 0))
        is_correct = bool(correction.get("is_correct", False))

        if is_correct:
            st.success(f"Bonne réponse. Score: {score}/10")
        else:
            st.error(f"Réponse à améliorer. Score: {score}/10")

        st.write("Retour pédagogique")
        st.write(correction.get("feedback", ""))

        st.write("Réponse exacte")
        st.write(correction.get("correct_answer", ""))

        st.write("Explication")
        st.write(correction.get("explanation", ""))

        if st.button("Passer à une autre question", width="stretch"):
            try:
                with st.spinner("Génération de la prochaine question..."):
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
                st.error(f"Impossible de passer à la question suivante: {exc}")
        st.markdown("</section>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
