import streamlit as st, requests, base64, time, re, json, uuid
import streamlit.components.v1 as components

st.set_page_config(page_title="LYRA", page_icon="✨", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap');
* {font-family:'Inter', sans-serif;}

/* --- Palette façon Claude : crème chaud + accent terracotta --- */
.stApp {background:#F5F4EE!important; color:#1F1E1D!important;}
section[data-testid="stSidebar"] {background:#EDEBE3!important; border-right:1px solid #E0DDD1!important;}
div[data-testid="stChatMessages"] {gap: 1.4rem!important; padding-top: 2rem; padding-bottom: 6rem;}

/* Message assistant : pas d'encadré, se fond dans la page, comme Claude */
.stChatMessage:has(div[data-testid="stChatMessageAvatarAssistant"]) {
    background:transparent!important;
    border:none!important;
    box-shadow:none!important;
    padding: 8px 4px!important;
    max-width: 720px!important;
    margin: 0 auto!important;
}
/* Message utilisateur : bulle discrète alignée, comme Claude */
.stChatMessage:has(div[data-testid="stChatMessageAvatarUser"]) {
    background:#EAE7DC!important;
    border:none!important;
    border-radius:18px!important;
    padding: 14px 20px!important;
    max-width: 640px!important;
    margin: 0 auto!important;
    box-shadow:none!important;
}
div[data-testid="stChatMessageAvatarUser"] {background:#8A8578!important;}
div[data-testid="stChatMessageAvatarAssistant"] {background:#C15F3C!important;}
.stChatMessage p,.stChatMessage li {
    font-family:'Source Serif 4', serif!important;
    font-size: var(--lyra-font-size, 17px)!important;
    line-height: 1.75!important;
    letter-spacing: 0.1px!important;
    color: #1F1E1D!important;
}
.stChatMessage h1,.stChatMessage h2,.stChatMessage h3 {
    font-family:'Inter', sans-serif!important;
    font-weight:600!important;
    color:#1F1E1D!important;
    margin-top: 1.2em!important;
}
div[data-testid="stChatInput"] {
    background:#ffffff!important;
    border:1px solid #D9D5C7!important;
    border-radius:24px!important;
    max-width: 760px!important;
    margin: 0 auto!important;
}

/* Accent terracotta sur les boutons et toggles, comme Claude */
.stButton button, .stDownloadButton button {
    border-radius:10px!important;
    border:1px solid #E0DDD1!important;
    background:#ffffff!important;
    color:#1F1E1D!important;
}
.stButton button:hover, .stDownloadButton button:hover {
    border-color:#C15F3C!important;
    color:#C15F3C!important;
}
div[data-baseweb="checkbox"] span, .stToggle {accent-color:#C15F3C!important;}
[data-testid="stMarkdownContainer"] a {color:#C15F3C!important;}

.lyra-warning {
    background:#FBF0E4; border:1px solid #E3A96B; border-radius:12px;
    padding:12px 16px; color:#8A5A20; font-size:14px; margin-bottom:1rem;
}
.lyra-crisis {
    background:#FBEAE6; border:1px solid #C15F3C; border-radius:12px;
    padding:14px 18px; color:#8A3A20; font-size:14px; margin-bottom:1rem; line-height:1.6;
}
.lyra-footer {
    text-align:center; color:#9A9686; font-size:12px; padding:1.5rem 0 0.5rem 0;
}
.conv-btn button {
    text-align:left!important; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
</style>
""", unsafe_allow_html=True)

# --- Thème clair (défaut, façon Claude) / sombre ---------------------------
if st.session_state.get("theme", "Clair") == "Sombre":
    st.markdown("""
    <style>
    .stApp {background:#0f0f10!important; color:#ececec!important;}
    section[data-testid="stSidebar"] {background:#18181b!important; border-right:1px solid #27272a!important;}
    .stChatMessage:has(div[data-testid="stChatMessageAvatarUser"]) {background:#232326!important;}
    .stChatMessage p,.stChatMessage li {color:#ececec!important;}
    .stChatMessage h1,.stChatMessage h2,.stChatMessage h3 {color:#fff!important;}
    div[data-testid="stChatInput"] {background:#18181b!important; border:1px solid #3f3f46!important;}
    .stButton button, .stDownloadButton button {background:#18181b!important; border:1px solid #3f3f46!important; color:#ececec!important;}
    .lyra-footer {color:#71717a!important;}
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# CRITÈRES D'UNE BONNE IA — appliqués dans tout le fichier
# 1. Utilité & pédagogie active     6. Sécurité des mineurs & contenu approprié
# 2. Honnêteté & transparence       7. Anti-dépendance affective
# 3. Sécurité & gestion de crise    8. Robustesse technique & accessibilité
# 4. Confidentialité & sobriété     9. Limites clairement énoncées
#    des données                   10. Expérience type ChatGPT (historique de
# 5. Neutralité & absence de biais      conversations, réponse en flux, fichiers)
# ---------------------------------------------------------------------------

# --- 10. Multi-conversations façon ChatGPT ---------------------------------
if "conversations" not in st.session_state:
    first_id = str(uuid.uuid4())
    st.session_state.conversations = {first_id: {"title": "Nouvelle conversation", "messages": []}}
    st.session_state.current_conv = first_id
if "niveau" not in st.session_state: st.session_state.niveau = "Terminale"
if "cycle" not in st.session_state: st.session_state.cycle = "Lycée"
if "last_call" not in st.session_state: st.session_state.last_call = 0.0
if "font_size" not in st.session_state: st.session_state.font_size = "Normale"

def current_messages():
    return st.session_state.conversations[st.session_state.current_conv]["messages"]

def set_conv_title_from_first_message(text):
    conv = st.session_state.conversations[st.session_state.current_conv]
    if conv["title"] == "Nouvelle conversation":
        conv["title"] = (text[:40] + "…") if len(text) > 40 else text

KEY = st.secrets.get("GROQ_API_KEY", "").strip()
CYCLES = {
    "Collège": ["6e", "5e", "4e", "3e"],
    "Lycée": ["Seconde", "Première", "Terminale"],
    "Université": ["Licence 1", "Licence 2", "Licence 3", "Master 1", "Master 2", "Doctorat"]
}
PROGRAMMES = {
    "6e": "bases fractions, décimaux, géométrie simple", "5e": "fractions, proportionnalité", "4e": "Pythagore, Thalès, équations",
    "3e": "fonctions, racine carrée, Brevet", "Seconde": "fonctions, vecteurs", "Première": "dérivées, suites",
    "Terminale": "limites, intégrales, Bac", "Licence 1": "analyse réelle, algèbre linéaire", "Licence 2": "analyse avancée",
    "Licence 3": "topologie", "Master 1": "master recherche", "Master 2": "expert", "Doctorat": "recherche doctorale"
}
MINEUR_CYCLES = {"Collège", "Lycée"}  # utilisateurs probablement mineurs -> ton et contenu adaptés

# --- 3. Sécurité & gestion de crise -----------------------------------------
CRISIS_PATTERNS = [
    r"\bsuicid", r"\bme tuer\b", r"\bme faire du mal\b", r"\benvie de mourir\b",
    r"\bscarification", r"\bplus envie de vivre\b", r"\bharc[eè]l"
]

def detect_crisis(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in CRISIS_PATTERNS)

CRISIS_MESSAGE = """Ce que tu traverses semble difficile, et ça compte. Je suis une IA pédagogique et je ne suis pas la bonne ressource pour ça — mais il existe des personnes formées pour t'aider vraiment.

**En France :**
- **3114** — numéro national de prévention du suicide, gratuit, 24h/24
- **Fil Santé Jeunes : 0 800 235 236** (appel et tchat anonymes)
- Ou parle à un adulte de confiance : parent, infirmier(ère) scolaire, professeur

Tu n'as pas à traverser ça seul(e). N'hésite pas à contacter une de ces ressources."""

PRIVACY_NOTE = "LYRA ne conserve tes conversations que dans ton navigateur pour cette session — rien n'est envoyé à un serveur permanent par l'application elle-même."

# --- 1, 2, 5, 6, 7, 10. Prompt système --------------------------------------
# Comportement assoupli façon ChatGPT : LYRA répond volontiers à des questions
# hors programme (curiosité générale, culture, aide méthodologique...) au lieu
# de les refuser, tout en restant identifiable comme tutrice scolaire et en
# recentrant naturellement vers le niveau de l'élève quand c'est pertinent.
def system_prompt(niveau, cycle, detailed=False):
    prog = PROGRAMMES.get(niveau, "")
    contexte_mineur = ""
    if cycle in MINEUR_CYCLES:
        contexte_mineur = """
9. L'élève est probablement mineur : garde un contenu strictement adapté à son âge, sans aucune ambiguïté, et ne développe jamais de sujets sensibles (violence, sexualité, substances) même si la question dévie vers ça — recentre poliment sur le scolaire."""
    mode_note = ("\n\nMODE DÉTAILLÉ ACTIVÉ : développe davantage — étapes intermédiaires, exemples supplémentaires, contre-exemples si utile — sans pour autant délayer inutilement."
                 if detailed else "")
    return f"""Tu es LYRA, assistante pédagogique polyvalente pour un élève de {cycle} {niveau}.
Programme de référence pour ce niveau : {prog}.

RÈGLES DE FOND (à respecter strictement) :
1. Tu es avant tout une tutrice scolaire pour {niveau}, mais comme un assistant IA généraliste, tu peux répondre à des questions hors programme (culture générale, méthode de travail, curiosité, aide à la rédaction, etc.) au lieu de refuser — adapte simplement le niveau de langage à l'âge de l'élève.
2. Pour les exercices et notions du programme, ne donne jamais une réponse finale brute sans explication : décompose le raisonnement étape par étape, et privilégie un indice avant la solution complète si l'élève bloque.
3. Si tu n'es pas certaine d'un résultat ou d'un calcul, dis-le explicitement plutôt que d'affirmer avec assurance une chose fausse.
4. Vérifie mentalement tes calculs avant de les présenter.
5. Ne fais jamais le travail à la place de l'élève sans qu'il ait au moins tenté de comprendre la méthode, pour les exercices notés/évalués.
6. Reste neutre sur toute question politique, religieuse ou sociétale : présente les faits et différents points de vue, jamais une opinion personnelle.
7. Tu es une IA, pas un ami ni un confident : reste chaleureuse et encourageante, mais rappelle si besoin que tu es un outil, pas un substitut à des relations humaines réelles.
8. Refuse poliment tout contenu dangereux, illégal ou inapproprié, indépendamment du sujet scolaire ou non.
9. Ne complimente pas de façon automatique ou creuse ("excellente question !" avant même de savoir si elle l'est) : la reconnaissance doit être méritée et sincère, jamais systématique.
10. Si la question de l'élève est ambiguë ou incomplète, pose UNE question de clarification courte plutôt que de deviner et de partir dans la mauvaise direction — sauf si une hypothèse raisonnable permet de répondre utilement tout de suite, auquel cas énonce-la brièvement et réponds.
11. Si tu te trompes et que l'élève te corrige avec raison, reconnais-le simplement et corrige-toi, sans t'excuser de façon excessive ni te justifier longuement.
12. Si l'élève est frustré, impatient ou agressif, reste posée et respectueuse ; ne deviens jamais froide ou cassante en retour.
13. Adapte la longueur et la structure au besoin réel : une question simple mérite une réponse courte et directe (pas de titres inutiles) ; un exercice complexe mérite une réponse structurée avec titres, étapes numérotées et exemples. Ne rallonge jamais artificiellement.{contexte_mineur}

FORMAT DE RÉPONSE (adapte-toi à la question, ne suis pas un gabarit fixe) :
- Question simple ou factuelle → réponse courte, 1 à 3 phrases, sans titres inutiles.
- Explication ou méthode → structure avec des titres courts (##), des étapes numérotées ou des listes à puces, jamais un mur de texte.
- N'ajoute pas de longue introduction qui répète la question ni de conclusion creuse ; va à l'essentiel puis développe.
- Si un extrait de résultat de recherche web t'est fourni dans le message, appuie-toi dessus et signale que l'information vient d'une recherche récente.
- MATHÉMATIQUES : écris TOUTE expression ou formule mathématique en LaTeX entouré de symboles dollar — `$...$` pour une expression dans le texte, `$$...$$` sur sa propre ligne pour une formule mise en avant. N'utilise jamais de crochets `\\[ \\]` ni de texte brut : toujours par exemple `$\\lim_{{x \\to 0}}$`, `$\\frac{{a}}{{b}}$`, `$\\ln(x)$`.

Ton direct, clair, sans flatterie inutile, mais encourageant et respectueux — chaleureux sans complaisance, honnête même quand ce n'est pas ce que l'élève espère entendre.
Réponse en français, adaptée en longueur et en structure à la question, au niveau {niveau}.{mode_note}"""

# --- Recherche web (façon ChatGPT/Claude "search") --------------------------
# Optionnelle : nécessite une clé SERPER_API_KEY dans les secrets Streamlit
# (https://serper.dev, gratuit jusqu'à un certain volume). Sans clé, LYRA
# répond simplement à partir de ses propres connaissances.
SERPER_KEY = st.secrets.get("SERPER_API_KEY", "").strip()

def web_search(query, num=4):
    if not SERPER_KEY:
        return None, "no_key"
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num, "gl": "fr", "hl": "fr"},
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("organic", [])[:num]
        if not results:
            return None, "no_results"
        formatted = "\n".join(
            f"- {it.get('title','')} : {it.get('snippet','')} ({it.get('link','')})"
            for it in results
        )
        return formatted, "ok"
    except requests.exceptions.RequestException:
        return None, "error"

# --- 8. Robustesse technique : cooldown simple anti-abus / anti-surcoût ----
MIN_INTERVAL = 1.5

def cooldown_ok():
    now = time.time()
    if now - st.session_state.last_call < MIN_INTERVAL:
        return False
    st.session_state.last_call = now
    return True

# --- 10. Réponse en flux façon ChatGPT --------------------------------------
def stream_text(q, niveau, cycle, extra_context="", detailed=False):
    if not KEY:
        yield "⚠️ Clé API manquante. Configure GROQ_API_KEY dans les secrets Streamlit."
        return
    if not cooldown_ok():
        yield "⏳ Une question à la fois — attends une seconde avant d'envoyer la suivante."
        return
    user_content = q if not extra_context else f"{q}\n\n[Contexte du fichier joint]\n{extra_context[:6000]}"
    try:
        with requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {KEY}"},
            json={
                "model": "openai/gpt-oss-20b",
                "messages": [
                    {"role": "system", "content": system_prompt(niveau, cycle, detailed)},
                    {"role": "user", "content": user_content}
                ],
                "stream": True
            },
            timeout=60,
            stream=True
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if not line.startswith("data: "):
                    continue
                payload = line[len("data: "):]
                if payload.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except (KeyError, IndexError, json.JSONDecodeError):
                    continue
    except requests.exceptions.Timeout:
        yield "⏱️ LYRA met trop de temps à répondre. Réessaie dans un instant."
    except requests.exceptions.RequestException as e:
        yield f"⚠️ Problème de connexion avec LYRA : {type(e).__name__}"

def call_vision(q, img_bytes, niveau):
    if not KEY:
        return "⚠️ Clé API manquante. Configure GROQ_API_KEY dans les secrets Streamlit."
    if not cooldown_ok():
        return "⏳ Une question à la fois — attends une seconde avant d'envoyer la suivante."
    try:
        b64 = base64.b64encode(img_bytes).decode()
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {KEY}"},
            json={
                "model": "qwen/qwen3.6-27b",
                "messages": [
                    {"role": "system", "content": f"Tu es LYRA, tutrice {niveau}. Analyse l'image avec rigueur, décompose le raisonnement étape par étape, et signale si l'écriture ou l'énoncé est ambigu plutôt que de deviner. Si l'image ne contient pas d'exercice scolaire, dis-le poliment sans analyser le reste du contenu. Écris toute expression mathématique en LaTeX entouré de symboles dollar ($...$ ou $$...$$ sur sa propre ligne), jamais de crochets ni de texte brut."},
                    {"role": "user", "content": [
                        {"type": "text", "text": q},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}
                ]
            },
            timeout=60
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        return f"⚠️ Erreur {code} lors de l'analyse de l'image. Si ça persiste, le modèle de vision a peut-être changé côté Groq — vérifie console.groq.com/docs/deprecations."
    except requests.exceptions.RequestException as e:
        return f"⚠️ Problème de connexion avec LYRA : {type(e).__name__}"
    except (KeyError, ValueError, IndexError):
        return "⚠️ Impossible d'analyser cette image. Réessaie avec une photo plus nette."

def transcribe(b):
    if not KEY:
        return ""
    try:
        files = {"file": ("a.wav", b, "audio/wav")}
        data = {"model": "whisper-large-v3", "language": "fr"}
        r = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {KEY}"},
            files=files, data=data, timeout=60
        )
        r.raise_for_status()
        return r.json().get("text", "")
    except requests.exceptions.RequestException:
        return ""

# --- 10. Recherche web légère (infos à jour) --------------------------------
SEARCH_TRIGGERS = [
    r"\baujourd'hui\b", r"\bactuel", r"\bactuellement\b", r"\bderni[eè]r", r"\bmaintenant\b",
    r"\bcette ann[eé]e\b", r"\b202[4-9]\b", r"\ben ce moment\b", r"\brécent"
]

def needs_web_search(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in SEARCH_TRIGGERS)

def web_search_snippet(query: str) -> str:
    """Recherche légère via DuckDuckGo Instant Answer (sans clé API)."""
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=8
        )
        r.raise_for_status()
        data = r.json()
        parts = []
        if data.get("AbstractText"):
            parts.append(data["AbstractText"])
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(topic["Text"])
        return "\n".join(parts)[:1500]
    except requests.exceptions.RequestException:
        return ""

# --- 10. Upload de documents (pdf/txt) façon ChatGPT ------------------------
# --- Lecture vocale des réponses (synthèse vocale du navigateur, sans clé API) ---
def speak_button(text, key):
    safe_text = json.dumps(text)
    html = f"""
    <button id="lyra-speak-{key}" style="
        background:#ffffff;color:#1F1E1D;border:1px solid #E0DDD1;border-radius:10px;
        padding:6px 12px;font-size:13px;cursor:pointer;font-family:Inter,sans-serif;">
        🔊 Écouter
    </button>
    <script>
    const btn_{key} = document.getElementById("lyra-speak-{key}");
    btn_{key}.onclick = function() {{
        const synth = window.speechSynthesis;
        synth.cancel();
        const utter = new SpeechSynthesisUtterance({safe_text});
        utter.lang = "fr-FR";
        synth.speak(utter);
    }};
    </script>
    """
    components.html(html, height=42)

# --- Export PDF (nécessite fpdf2 ; repli propre si absent) -----------------
def build_pdf(text):
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.set_auto_page_break(auto=True, margin=15)
        clean = text.replace("**", "").replace("##", "").replace("#", "")
        for line in clean.split("\n"):
            pdf.multi_cell(0, 8, line.encode("latin-1", "replace").decode("latin-1"))
        return bytes(pdf.output())
    except Exception:
        return None

def extract_document_text(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".txt"):
        try:
            return uploaded_file.getvalue().decode("utf-8", errors="ignore")
        except Exception:
            return ""
    if name.endswith(".pdf"):
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(uploaded_file)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            return "[PyPDF2 non installé : impossible d'extraire ce PDF côté serveur]"
        except Exception:
            return "[Impossible de lire ce PDF]"
    return ""

with st.sidebar:
    st.markdown("## ✨ LYRA")
    if not KEY:
        st.markdown('<div class="lyra-warning">Clé GROQ_API_KEY absente des secrets.</div>', unsafe_allow_html=True)

    if st.button("➕ Nouvelle conversation", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.conversations[new_id] = {"title": "Nouvelle conversation", "messages": []}
        st.session_state.current_conv = new_id
        st.rerun()

    st.caption("Conversations")
    # --- 10. Historique des conversations façon ChatGPT ---
    for conv_id, conv in list(st.session_state.conversations.items()):
        cols = st.columns([5, 1])
        active = conv_id == st.session_state.current_conv
        with cols[0]:
            st.markdown('<div class="conv-btn">', unsafe_allow_html=True)
            if st.button(("🟢 " if active else "") + conv["title"], key=f"sel_{conv_id}", use_container_width=True):
                st.session_state.current_conv = conv_id
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with cols[1]:
            if len(st.session_state.conversations) > 1 and st.button("🗑️", key=f"del_{conv_id}"):
                del st.session_state.conversations[conv_id]
                if st.session_state.current_conv == conv_id:
                    st.session_state.current_conv = next(iter(st.session_state.conversations))
                st.rerun()

    st.markdown("---")
    cycle = st.segmented_control("Cycle", list(CYCLES.keys()), default=st.session_state.cycle)
    if cycle: st.session_state.cycle = cycle
    niveau = st.segmented_control("Niveau", CYCLES[st.session_state.cycle], default=st.session_state.niveau if st.session_state.niveau in CYCLES[st.session_state.cycle] else CYCLES[st.session_state.cycle][0])
    if niveau: st.session_state.niveau = niveau
    st.caption(f"🔒 Verrouillé sur {st.session_state.niveau}")

    st.markdown("---")
    theme_choice = st.radio("🎨 Thème", ["Clair", "Sombre"], index=0 if st.session_state.get("theme", "Clair") == "Clair" else 1, horizontal=True)
    st.session_state.theme = theme_choice

    st.markdown("---")
    font_choice = st.select_slider("🔠 Taille du texte", options=["Petite", "Normale", "Grande"], value=st.session_state.font_size)
    st.session_state.font_size = font_choice

    st.markdown("---")
    with st.expander("ℹ️ À propos de LYRA"):
        st.caption("LYRA est une intelligence artificielle, pas un enseignant humain. Elle peut se tromper : vérifie toujours les points importants avec ton professeur.")
        st.caption(PRIVACY_NOTE)

_size_map = {"Petite": "15px", "Normale": "17px", "Grande": "20px"}
st.markdown(f"<style>:root {{ --lyra-font-size: {_size_map[st.session_state.font_size]}; }}</style>", unsafe_allow_html=True)

st.markdown(f"### ✨ LYRA • {st.session_state.cycle} — {st.session_state.niveau}")
st.caption("Ta tutrice pédagogique : elle t'aide à comprendre, pas seulement à trouver la réponse")

# --- Suggestions de démarrage façon Claude, sur conversation vide -----------
suggestion_clicked = None
if not current_messages():
    prog = PROGRAMMES.get(st.session_state.niveau, "")
    suggestions = [
        f"Explique-moi une notion clé de {st.session_state.niveau} ({prog.split(',')[0].strip()})",
        "Aide-moi à organiser une fiche de révision",
        "Pose-moi une question pour tester mes connaissances",
        "J'ai un exercice, comment je peux te le montrer ?"
    ]
    st.caption("Pour démarrer :")
    scols = st.columns(2)
    for i, s in enumerate(suggestions):
        with scols[i % 2]:
            if st.button(s, key=f"sugg_{i}", use_container_width=True):
                suggestion_clicked = s

for idx, m in enumerate(current_messages()):
    with st.chat_message(m["role"]):
        if m["role"] == "user":
            is_last_user = idx == len(current_messages()) - 1 or (idx == len(current_messages()) - 2 and current_messages()[-1]["role"] == "assistant")
            editing_key = f"editing_{idx}"
            if is_last_user and st.session_state.get(editing_key, False):
                new_text = st.text_area("Modifier ta question", value=m["content"], key=f"edit_area_{idx}", label_visibility="collapsed")
                ecols = st.columns([1, 1, 6])
                with ecols[0]:
                    if st.button("✅ Renvoyer", key=f"save_edit_{idx}"):
                        del current_messages()[idx:]
                        current_messages().append({"role": "user", "content": new_text})
                        st.session_state.regenerate_query = new_text
                        st.session_state[editing_key] = False
                        st.rerun()
                with ecols[1]:
                    if st.button("✖️ Annuler", key=f"cancel_edit_{idx}"):
                        st.session_state[editing_key] = False
                        st.rerun()
            else:
                st.markdown(m["content"])
                if is_last_user:
                    if st.button("✏️ Modifier", key=f"editbtn_{idx}"):
                        st.session_state[editing_key] = True
                        st.rerun()
        if m["role"] == "assistant":
            st.markdown(m["content"])
            is_last = idx == len(current_messages()) - 1
            action_cols = st.columns([1, 1, 1, 1, 1, 5]) if is_last else st.columns([1, 1, 1, 1, 6])
            with action_cols[0]:
                with st.popover("📋"):
                    st.code(m["content"], language=None)
            with action_cols[1]:
                speak_button(m["content"], key=f"speak_{idx}")
            feedback_key = f"feedback_{idx}"
            with action_cols[2]:
                if st.button("👍", key=f"up_{idx}"):
                    st.session_state[feedback_key] = "up"
            with action_cols[3]:
                if st.button("👎", key=f"down_{idx}"):
                    st.session_state[feedback_key] = "down"
            if st.session_state.get(feedback_key) == "up":
                st.caption("Merci pour ton retour 👍")
            elif st.session_state.get(feedback_key) == "down":
                st.caption("Merci, LYRA va essayer de faire mieux 👎")
            if is_last:
                with action_cols[4]:
                    if st.button("🔄", key=f"regen_{idx}", help="Régénérer"):
                        # Retrouve la dernière question de l'élève et relance la génération
                        prev_user = next((mm["content"] for mm in reversed(current_messages()[:idx]) if mm["role"] == "user"), None)
                        if prev_user:
                            current_messages().pop()  # retire l'ancienne réponse
                            st.session_state.regenerate_query = prev_user
                        st.rerun()

# --- Barre d'outils façon Claude : pilules sous la zone de saisie ----------
st.markdown(f"""
<div style="max-width:760px;margin:0 auto;display:flex;align-items:center;gap:10px;padding:6px 4px 2px 4px;">
    <span style="background:#EAE7DC;border-radius:999px;padding:7px 16px;font-size:14px;color:#1F1E1D;">
        🔒 {st.session_state.cycle} · {st.session_state.niveau}
    </span>
</div>
""", unsafe_allow_html=True)
tb_cols = st.columns([1, 1, 1, 1, 4])
with tb_cols[0]:
    with st.popover("➕"):
        st.caption("Joindre un fichier")
        st.file_uploader("📸 Photo exo", type=["jpg", "png", "jpeg"], key="up", label_visibility="collapsed")
        st.camera_input("Caméra", key="cam", label_visibility="collapsed")
        st.file_uploader("📄 Document (pdf/txt)", type=["pdf", "txt"], key="doc", label_visibility="collapsed")
with tb_cols[1]:
    web_on = st.toggle("🔎", value=False, help="Recherche web avant de répondre")
with tb_cols[2]:
    detailed_mode = st.toggle("🧠", value=False, help="Mode détaillé : explications plus développées")
with tb_cols[3]:
    with st.popover("🎙️"):
        st.caption("Message vocal")
        st.audio_input("Message vocal", key="aud", label_visibility="collapsed")
if web_on and not SERPER_KEY:
    st.caption("⚠️ Aucune clé SERPER_API_KEY configurée : la recherche web sera ignorée.")

# --- Photo : import fiabilisé -----------------------------------------------
# Corrections : distinction claire caméra/upload (au lieu d'un "or" ambigu),
# aperçu visible pour confirmer que le fichier est bien reçu, message d'erreur
# explicite en cas d'échec de lecture, et types acceptés élargis.
up_file = st.session_state.get("up")
cam_file = st.session_state.get("cam")
img_source = up_file if up_file is not None else cam_file

if img_source is not None:
    try:
        img_bytes = img_source.getvalue()
        if not img_bytes:
            raise ValueError("empty")
        st.image(img_bytes, caption="Photo prête à être analysée", width=220)
        if st.button("📸 Analyser la photo"):
            with st.spinner("Analyse en cours..."):
                ans = call_vision("Résous l'exercice sur l'image étape par étape", img_bytes, st.session_state.niveau)
            current_messages().append({"role": "user", "content": "📸 [Photo d'exercice]"})
            current_messages().append({"role": "assistant", "content": ans})
            set_conv_title_from_first_message("Photo d'exercice")
            st.rerun()
    except Exception:
        st.error("⚠️ Impossible de lire cette photo. Formats acceptés : JPG, JPEG, PNG. Si tu es sur iPhone et que la photo est en HEIC, convertis-la d'abord en JPG.")

# Vocal
aud = st.session_state.get("aud")
if aud:
    txt = transcribe(aud.getvalue())
    if txt:
        current_messages().append({"role": "user", "content": f"🎙️ {txt}"})
        set_conv_title_from_first_message(txt)
        if detect_crisis(txt):
            current_messages().append({"role": "assistant", "content": CRISIS_MESSAGE})
            st.rerun()
        else:
            with st.chat_message("assistant"):
                full = st.write_stream(stream_text(txt, st.session_state.niveau, st.session_state.cycle, detailed=detailed_mode))
            current_messages().append({"role": "assistant", "content": full})
            st.rerun()
    else:
        st.warning("Je n'ai pas réussi à comprendre l'audio, réessaie ou écris ta question.")

q = st.chat_input(f"Question de {st.session_state.niveau}...") or suggestion_clicked
regen_q = st.session_state.pop("regenerate_query", None)

if regen_q:
    with st.chat_message("assistant"):
        full = st.write_stream(stream_text(regen_q, st.session_state.niveau, st.session_state.cycle, detailed=detailed_mode))
    current_messages().append({"role": "assistant", "content": full})
    st.rerun()

if q:
    doc_text = ""
    doc_file = st.session_state.get("doc")
    if doc_file is not None:
        doc_text = extract_document_text(doc_file)

    # --- Recherche web optionnelle, injectée comme contexte supplémentaire ---
    if web_on and SERPER_KEY:
        with st.spinner("🔎 Recherche en cours..."):
            web_results, status = web_search(q)
        if status == "ok":
            doc_text = (doc_text + "\n\n" if doc_text else "") + f"[Résultats de recherche web]\n{web_results}"

    current_messages().append({"role": "user", "content": q + (f"\n\n📄 *(avec {doc_file.name})*" if doc_file is not None else "")})
    set_conv_title_from_first_message(q)
    with st.chat_message("user"):
        st.markdown(q)

    if detect_crisis(q):
        current_messages().append({"role": "assistant", "content": CRISIS_MESSAGE})
    else:
        with st.chat_message("assistant"):
            full = st.write_stream(stream_text(q, st.session_state.niveau, st.session_state.cycle, extra_context=doc_text, detailed=detailed_mode))
        current_messages().append({"role": "assistant", "content": full})
    st.rerun()

# --- Artifacts : exporter la dernière réponse en fichier téléchargeable -----
msgs = current_messages()
if msgs and msgs[-1]["role"] == "assistant":
    exp_cols = st.columns([1, 1, 6])
    with exp_cols[0]:
        st.download_button(
            "📥 Markdown",
            data=msgs[-1]["content"],
            file_name="lyra_reponse.md",
            mime="text/markdown"
        )
    with exp_cols[1]:
        pdf_bytes = build_pdf(msgs[-1]["content"])
        if pdf_bytes:
            st.download_button(
                "📄 PDF",
                data=pdf_bytes,
                file_name="lyra_reponse.pdf",
                mime="application/pdf"
            )
        else:
            st.caption("Export PDF indisponible (fpdf2 non installé)")

st.markdown('<div class="lyra-footer">LYRA est une IA et peut faire des erreurs — vérifie les points importants avec ton professeur.</div>', unsafe_allow_html=True)
