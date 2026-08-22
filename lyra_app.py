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

/* Empêche les rangées d'icônes (actions sous les réponses, barre d'outils)
   de s'empiler verticalement sur mobile — les garde compactes et alignées,
   comme la barre d'icônes de Claude. */
div[data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap!important;
    gap: 6px!important;
    align-items: center!important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    width: fit-content!important;
    min-width: 0!important;
    flex: 0 0 auto!important;
}
div[data-testid="stHorizontalBlock"] .stButton button,
div[data-testid="stHorizontalBlock"] .stDownloadButton button,
div[data-testid="stHorizontalBlock"] .stPopover button {
    padding: 6px 10px!important;
    min-height: 34px!important;
    font-size: 14px!important;
    white-space: nowrap!important;
}
div[data-testid="stHorizontalBlock"] .stToggle {
    transform: scale(0.85);
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
   
