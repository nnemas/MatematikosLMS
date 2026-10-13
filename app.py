import streamlit as st
import google.generativeai as genai
import pandas as pd
import json, os, re, math, html, hmac
from datetime import datetime

# ---------------- KONFIGŪRACIJA ----------------
st.set_page_config(page_title="Sokratinis Math LMS", layout="wide", page_icon="📐")

MODEL = "gemini-2.5-flash"
LESSON_FILE = "pamoka.json"          # bendras visiems naudotojams (session_state tarp naršyklių nesidalija!)
LOG_FILE = "mokiniu_logai.txt"
TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD", "")  # nustatykite aplinkos kintamajame


def _get_key():
    k = os.getenv("GEMINI_API_KEY")
    if k:
        return k
    try:
        return st.secrets.get("GEMINI_API_KEY")
    except Exception:
        return None


API_KEY = _get_key()

for k, v in {
    "role": None, "user_name": "", "idx": 0, "progress": {}, "answers": {},
    "feedback": {}, "attempts": {}, "draft": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------------- PAGALBINĖS ----------------
def load_lesson():
    try:
        with open(LESSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"formulas": "", "tasks": [], "published": False}


def save_lesson(lesson):
    with open(LESSON_FILE, "w", encoding="utf-8") as f:
        json.dump(lesson, f, ensure_ascii=False, indent=2)


def log_event(student, task_id, action, details=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = str(details).replace("\n", " ")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] Mokinys: {student} | Užduotis: {task_id} | Veiksmas: {action} | Detalės: {details}\n")
    except Exception as e:
        st.error(f"Klaida įrašant logus: {e}")


def ask_ai(contents, json_mode=False):
    genai.configure(api_key=API_KEY)
    cfg = {"response_mime_type": "application/json"} if json_mode else None
    model = genai.GenerativeModel(MODEL, generation_config=cfg)
    return model.generate_content(contents).text


# ---------------- ATSAKYMŲ TIKRINIMAS ----------------
NUM_RE = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?)\s*(.*)$")


def parse_answer(text):
    """Grąžina (skaičius, vienetas) arba (None, tekstas)."""
    s = str(text).strip().lower().replace("−", "-")
    m = NUM_RE.match(s)
    if not m:
        return None, s
    num, unit = m.group(1).replace(" ", ""), m.group(2).strip()
    try:
        if "/" in num:
            a, b = num.split("/")
            val = float(a.replace(",", ".")) / float(b)
        else:
            val = float(num.replace(",", "."))
    except (ValueError, ZeroDivisionError):
        return None, s
    unit = unit.replace("kv.", "").replace("^2", "²").replace("^3", "³").replace(" ", "").rstrip(".")
    unit = re.sub(r"([a-z]+)2$", r"\1²", unit)
    unit = re.sub(r"([a-z]+)3$", r"\1³", unit)
    return val, unit


def check_answer(user, correct):
    """Grąžina (ar_teisingai, pastaba)."""
    if not str(user).strip() or not str(correct).strip():
        return False, ""
    uv, uu = parse_answer(user)
    cv, cu = parse_answer(correct)
    if uv is None or cv is None:
        norm = lambda t: re.sub(r"\W", "", str(t).lower())
        return norm(user) == norm(correct), ""
    tol = 0.0 if float(cv).is_integer() else 0.011   # leidžiame apvalinimą iki šimtųjų (pvz., su π ≈ 3,14)
    if abs(uv - cv) > tol:
        return False, ""
    if uu and cu and uu != cu:
        return False, "Skaičius tinka, bet patikrinkite matavimo vienetus (pvz., cm ar cm²)."
    return True, ""


# ---------------- BRĖŽINIAI ----------------
def _text(x, y, t, size, color):
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size}" font-weight="bold" fill="{color}" '
            f'text-anchor="middle">{html.escape(str(t))}</text>')


def _svg(body):
    return ('<svg width="360" height="240" viewBox="0 0 360 240" xmlns="http://www.w3.org/2000/svg" '
            'style="background-color:#f9f9f9;border-radius:8px;border:1px solid #ddd;">' + body + "</svg>")


def _toward(p, q, d):
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy) or 1
    return p[0] + dx / L * d, p[1] + dy / L * d


def _is_right(v):
    s = str(v).lower()
    return "90" in s or "status" in s or "right" in s


def _side_label(sides, names, i, n, shape):
    a, b = names[i], names[(i + 1) % n]
    for k in (a + b, b + a):
        if k in sides:
            return f"{k} = {sides[k]}"
    if shape == "square" and "a" in sides:
        return f"a = {sides['a']}"
    if shape == "rectangle":
        k = "a" if i % 2 == 0 else "b"
        if k in sides:
            return f"{k} = {sides[k]}"
    return ""


def _polygon(pts, names, color, sides, angles, shape):
    n = len(pts)
    cx, cy = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
    out = [f'<polygon points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="{color}22" stroke="{color}" stroke-width="3"/>']
    for i, p in enumerate(pts):
        lx, ly = _toward((cx, cy), p, math.hypot(p[0] - cx, p[1] - cy) + 16)
        out.append(_text(lx, ly + 5, names[i], 16, "#333"))
        ang = angles.get(names[i], "")
        if _is_right(ang) and ang != "":
            u, w = _toward(p, pts[(i - 1) % n], 14), _toward(p, pts[(i + 1) % n], 14)
            c = (u[0] + w[0] - p[0], u[1] + w[1] - p[1])
            out.append(f'<path d="M {u[0]:.1f},{u[1]:.1f} L {c[0]:.1f},{c[1]:.1f} L {w[0]:.1f},{w[1]:.1f}" '
                       'fill="none" stroke="#d93025" stroke-width="2"/>')
        elif ang:
            ax, ay = _toward(p, (cx, cy), 36)
            out.append(_text(ax, ay + 4, ang, 12, "#d93025"))
    for i in range(n):
        lab = _side_label(sides, names, i, n, shape)
        if lab:
            p, q = pts[i], pts[(i + 1) % n]
            mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            lx, ly = _toward((cx, cy), (mx, my), math.hypot(mx - cx, my - cy) + 18)
            out.append(_text(lx, ly + 4, lab, 13, "#1b806a"))
    return _svg("".join(out))


SHAPE_ALIASES = {
    "kvadratas": "square", "trikampis": "triangle", "staciakampis": "rectangle", "stačiakampis": "rectangle",
    "keturkampis": "quadrilateral", "trapecija": "trapezoid", "apskritimas": "circle", "skritulys": "circle",
}


def render_dynamic_shape(fig):
    shape = str(fig.get("shape_type", "triangle")).lower()
    shape = SHAPE_ALIASES.get(shape, shape)
    vs = [str(v) for v in fig.get("vertices", [])]
    angles = {str(k): v for k, v in (fig.get("angles") or {}).items()}
    sides = {str(k): v for k, v in (fig.get("sides") or {}).items()}

    if shape == "circle":
        body = ('<circle cx="180" cy="115" r="75" fill="#ea433522" stroke="#ea4335" stroke-width="3"/>'
                '<circle cx="180" cy="115" r="4" fill="#333"/>')
        if "d" in sides and "r" not in sides:
            body += ('<line x1="105" y1="115" x2="255" y2="115" stroke="#ea4335" stroke-width="2" stroke-dasharray="4"/>'
                     + _text(180, 105, f"d = {sides['d']}", 13, "#1b806a"))
        else:
            body += ('<line x1="180" y1="115" x2="255" y2="115" stroke="#ea4335" stroke-width="2" stroke-dasharray="4"/>'
                     + _text(218, 105, f"r = {sides.get('r', '')}", 13, "#1b806a"))
        body += _text(168, 133, "O", 14, "#333")
        st.components.v1.html(_svg(body), height=250)
        return

    layouts = {
        "square": ([(105, 40), (255, 40), (255, 190), (105, 190)], "#9c27b0"),
        "rectangle": ([(80, 55), (280, 55), (280, 175), (80, 175)], "#34a853"),
        "quadrilateral": ([(80, 55), (280, 55), (280, 175), (80, 175)], "#34a853"),
        "trapezoid": ([(70, 175), (290, 175), (240, 55), (120, 55)], "#ff9900"),
    }
    if shape == "triangle":
        right = any(_is_right(a) for a in angles.values() if a)
        # statusis trikampis tik jei tikrai nurodytas status kampas
        pts = [(90, 175), (270, 175), (90, 45)] if right else [(70, 175), (290, 175), (180, 45)]
        if right:
            names = (vs + list("ABC"))[:3]
            r_at = next((k for k, a in angles.items() if _is_right(a)), None)
            if r_at in names and names.index(r_at) != 0:   # pasukam, kad status kampas būtų pirmoje viršūnėje
                j = names.index(r_at)
                names = names[j:] + names[:j]
        pts_names, color = (names if right else (vs + list("ABC"))[:3]), "#1a73e8"
        st.components.v1.html(_polygon(pts, pts_names, color, sides, angles, "triangle"), height=250)
        return
    if shape not in layouts:
        st.info(f"Figūros ({shape}) vizualizacija nepasiekiama.")
        return
    pts, color = layouts[shape]
    names = (vs + list("ABCD"))[:4]
    st.components.v1.html(_polygon(pts, names, color, sides, angles, shape), height=250)


# ---------------- AI UŽDUOČIŲ ANALIZĖ ----------------
def analysis_prompt(grade):
    return f"""Išanalizuok šios matematikos užduoties nuotrauką. Mokinių klasė: {grade}.
Remkis atnaujinta Lietuvos bendrąja matematikos programa: terminija ir pažymėjimai lietuviški
(perimetras P, plotas S, kraštinė, viršūnė, statusis kampas), skaičių dalis atskiriama KOMU (3,14),
matavimo vienetai: cm, cm², m, m² ir pan. Naudok tik tą metodiką, kuri atitinka {grade} klasės lygį.
Užduotis spręsk pats ir atsakymą PATIKRINK dar kartą. Jei atsakymo patikimai nustatyti negali, 'correct_answer' palik "".

Grąžink TIK JSON (be markdown):
{{
  "formulas": "Svarbiausios taisyklės ir formulės trumpai, punktais lietuvių kalba.",
  "tasks": [
    {{
      "task_number": "1",
      "question": "Bendra užduoties sąlyga.",
      "sub_tasks": [
        {{
          "label": "a",
          "prompt": "Apskaičiuokite kvadrato perimetrą, kai jo kraštinė a = 5 cm.",
          "correct_answer": "20 cm",
          "has_figure": true,
          "figure_data": {{
            "shape_type": "square",
            "vertices": ["A", "B", "C", "D"],
            "angles": {{"A": "90°", "B": "90°", "C": "90°", "D": "90°"}},
            "sides": {{"a": "5 cm"}}
          }},
          "formula_hint": "Kvadrato perimetras P = 4 · a"
        }}
      ]
    }}
  ]
}}

TAISYKLĖS:
1. 'correct_answer' – skaičius su vienetu (plotui – cm², perimetrui – cm), jei vienetai reikalingi.
2. shape_type: 'square', 'triangle', 'rectangle', 'quadrilateral', 'trapezoid', 'circle'. Jei figūra kitokia – has_figure=false.
3. Visas žinomas kraštines surašyk į 'sides' (raktai: 'AB', 'BC' ... arba 'a', 'b', 'r', 'd'). Statųjį kampą žymėk "90°".
4. NENAUDOK $ ar LaTeX.
5. Jei užduotis neturi dalių (a, b...), 'sub_tasks' palik tuščią ir 'correct_answer', 'has_figure', 'figure_data', 'formula_hint' rašyk prie pačios užduoties.
"""


def flatten_tasks(data):
    flat = []
    for t in data.get("tasks", []):
        num = str(t.get("task_number", "1"))
        subs = t.get("sub_tasks") or []
        if subs:
            for s in subs:
                flat.append({
                    "include": True, "display_id": f"{num}{s.get('label', '')}",
                    "main_question": t.get("question", ""), "sub_prompt": s.get("prompt", ""),
                    "correct_answer": str(s.get("correct_answer", "")).strip(),
                    "has_figure": bool(s.get("has_figure", False)), "figure_data": s.get("figure_data") or {},
                    "formula_hint": s.get("formula_hint", ""),
                })
        else:
            flat.append({
                "include": True, "display_id": num, "main_question": t.get("question", ""),
                "sub_prompt": "Apskaičiuokite ir įrašykite atsakymą:",
                "correct_answer": str(t.get("correct_answer", "")).strip(),
                "has_figure": bool(t.get("has_figure", False)), "figure_data": t.get("figure_data") or {},
                "formula_hint": t.get("formula_hint", ""),
            })
    return flat


def socratic_hint(item, user_ans):
    prompt = f"""Mokinys (pagal atnaujintą Lietuvos matematikos programą, 5–6 klasė) sprendžia užduotį: '{item['sub_prompt']}'.
Teisingas atsakymas (mokiniui NEPASAKYK): '{item['correct_answer']}'.
Mokinio atsakymas: '{user_ans}'.
Parašyk 1–2 trumpus Sokratinius klausimus lietuviškai: paskatink mokinį paaiškinti, kurią formulę ar veiksmą naudojo,
ir patikrinti vienetus bei skaičiavimą. Neatskleisk atsakymo, nenaudok $ ar LaTeX."""
    text = ask_ai(prompt).strip()
    if item["correct_answer"] and item["correct_answer"].lower() in text.lower():
        return "Dar kartą perskaityk sąlygą ir pasitikrink formulę bei vienetus. Kurį veiksmą darei pirmiausia?"
    return text


# ==============================================================================
# 1. PRISIJUNGIMAS
# ==============================================================================
if not st.session_state.role:
    st.title("📐 Sokratinė Matematikos Sistema")
    c, _ = st.columns(2)
    with c:
        name = st.text_input("Jūsų vardas:", placeholder="pvz., Mantas ar Mokytoja Rasa")
        pw = st.text_input("Mokytojo slaptažodis (tik mokytojui):", type="password") if TEACHER_PASSWORD else ""
        if not TEACHER_PASSWORD:
            st.caption("⚠️ TEACHER_PASSWORD nenustatytas – mokytojo panelė atvira visiems.")
        b1, b2 = st.columns(2)
        if b1.button("🎓 Aš esu Mokinys", use_container_width=True, type="primary"):
            if name.strip():
                st.session_state.update(user_name=name.strip(), role="student")
                st.rerun()
            else:
                st.warning("Prašome įvesti vardą!")
        if b2.button("👨‍🏫 Aš esu Mokytojas", use_container_width=True):
            if not name.strip():
                st.warning("Prašome įvesti vardą!")
            elif TEACHER_PASSWORD and not hmac.compare_digest(pw, TEACHER_PASSWORD):
                st.error("Neteisingas slaptažodis.")
            else:
                st.session_state.update(user_name=name.strip(), role="teacher")
                st.rerun()

# ==============================================================================
# 2. MOKYTOJAS
# ==============================================================================
elif st.session_state.role == "teacher":
    st.sidebar.title(f"👨‍🏫 {st.session_state.user_name}")
    if not API_KEY:
        API_KEY = st.sidebar.text_input("Gemini API raktas:", type="password")
        st.sidebar.caption("Mokinių AI patarimams raktą reikia nustatyti serveryje (GEMINI_API_KEY).")
    if st.sidebar.button("Atsijungti"):
        st.session_state.role = None
        st.session_state.draft = None
        st.rerun()

    st.title("Mokytojo valdymo panelė")
    tab1, tab2 = st.tabs(["📸 Užduotys ir formulės", "📋 Mokinių logai"])

    with tab1:
        grade = st.selectbox("Klasė:", [5, 6, 7, 8], index=1)
        up = st.file_uploader("Įkelkite sąsiuvinio ar vadovėlio nuotrauką", type=["jpg", "jpeg", "png"])
        if up:
            st.image(up, width=400)
            if st.button("Išanalizuoti nuotrauką", type="primary"):
                if not API_KEY:
                    st.error("Įveskite Gemini API raktą šoninėje juostoje!")
                else:
                    with st.spinner("AI analizuoja nuotrauką..."):
                        try:
                            raw = ask_ai([analysis_prompt(grade), {"mime_type": up.type, "data": up.getvalue()}], json_mode=True)
                            m = re.search(r"\{.*\}", raw, re.DOTALL)
                            data = json.loads(m.group(0) if m else raw, strict=False)
                            st.session_state.draft = {"formulas": data.get("formulas", ""), "tasks": flatten_tasks(data)}
                            st.success("Analizė baigta. Būtinai peržiūrėkite atsakymus prieš publikuodami!")
                        except Exception as e:
                            st.error(f"Klaida analizuojant nuotrauką: {e}")

        if st.session_state.draft is None:
            lesson = load_lesson()
            if lesson["tasks"]:
                st.session_state.draft = {"formulas": lesson["formulas"], "tasks": lesson["tasks"]}

        draft = st.session_state.draft
        if draft:
            st.subheader("📝 Formulės ir taisyklės")
            draft["formulas"] = st.text_area("Formulės mokiniui:", value=draft["formulas"], height=150)

            st.subheader("✏️ Užduotys (AI atsakymai gali klysti – patikrinkite)")
            cols = ["include", "display_id", "main_question", "sub_prompt", "correct_answer", "formula_hint"]
            df = pd.DataFrame([{c: t.get(c, "") for c in cols} for t in draft["tasks"]])
            edited = st.data_editor(df, use_container_width=True, hide_index=True, key="task_editor",
                                    column_config={"include": st.column_config.CheckboxColumn("Rodyti")})
            for i, row in enumerate(edited.to_dict("records")):
                draft["tasks"][i].update(row)

            with st.expander("Figūrų peržiūra"):
                for t in draft["tasks"]:
                    if t.get("has_figure") and t.get("figure_data"):
                        st.caption(f"Užduotis {t['display_id']}")
                        render_dynamic_shape(t["figure_data"])

            if st.button("✅ Publikuoti mokiniams", type="primary"):
                tasks = [t for t in draft["tasks"] if t.get("include")]
                save_lesson({"formulas": draft["formulas"], "tasks": tasks, "published": True})
                st.success(f"Paskelbta {len(tasks)} užduočių.")

    with tab2:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = f.read()
            st.text_area("Logai:", logs, height=300)
            st.download_button("Atsisiųsti logus", logs, file_name=LOG_FILE)
        else:
            st.write("Logų dar nėra.")

# ==============================================================================
# 3. MOKINYS
# ==============================================================================
elif st.session_state.role == "student":
    st.sidebar.title(f"🎓 {st.session_state.user_name}")
    if st.sidebar.button("Atsijungti"):
        st.session_state.role = None
        st.rerun()

    st.title("Matematikos užduočių sprendimas")
    lesson = load_lesson()
    tasks = lesson["tasks"]

    if lesson["formulas"]:
        with st.expander("💡 Formulės ir taisyklės"):
            st.write(lesson["formulas"])

    if not tasks or not lesson.get("published"):
        st.warning("Užduočių kol kas nėra. Mokytojas dar nepaskelbė pamokos medžiagos.")
    else:
        total = len(tasks)
        prog = st.session_state.progress
        icons = {"solved": "✅", "failed": "❌", "skipped": "⚪"}

        st.write("### Užduočių sąrašas")
        PER_ROW = 8
        for start in range(0, total, PER_ROW):
            row = st.columns(PER_ROW)
            for j, item in enumerate(tasks[start:start + PER_ROW]):
                i = start + j
                lab = f"{icons.get(prog.get(item['display_id']), '📄')} {item['display_id']}"
                kind = "primary" if i == st.session_state.idx else "secondary"
                if row[j].button(lab, key=f"nav_{i}", type=kind, use_container_width=True):
                    st.session_state.idx = i
                    st.rerun()
        st.write("---")

        idx = st.session_state.idx
        if idx < total:
            item = tasks[idx]
            tid = item["display_id"]
            st.subheader(f"Užduotis {tid} ({idx + 1} iš {total})")
            st.write(f"**Sąlyga:** {item['main_question']}")
            if item.get("has_figure") and item.get("figure_data"):
                render_dynamic_shape(item["figure_data"])

            attempts = st.session_state.attempts.get(tid, 0)
            if item.get("formula_hint"):
                with st.expander("🔑 Užuomina", expanded=attempts >= 2):
                    st.info(item["formula_hint"])

            user_ans = st.text_input(f"👉 {item['sub_prompt']}", key=f"ans_{tid}",
                                     help="Rašykite skaičių (kableliu ar tašku) ir, jei reikia, vienetą, pvz. 20 cm")

            if tid in st.session_state.feedback:
                kind, msg = st.session_state.feedback[tid]
                (st.success if kind == "success" else st.error)(msg)

            c1, c2, c3 = st.columns(3)
            if c1.button("Pateikti atsakymą", type="primary", use_container_width=True):
                st.session_state.answers[tid] = user_ans
                ok, note = check_answer(user_ans, item.get("correct_answer", ""))
                if ok:
                    prog[tid] = "solved"
                    st.session_state.feedback[tid] = ("success", "🎉 Teisingai! Puikus darbas.")
                    log_event(st.session_state.user_name, tid, "TEISINGAS ATSAKYMAS", user_ans)
                    st.session_state.idx += 1
                else:
                    if prog.get(tid) != "solved":
                        prog[tid] = "failed"
                    st.session_state.attempts[tid] = attempts + 1
                    log_event(st.session_state.user_name, tid, "NETEISINGAS ATSAKYMAS", user_ans)
                    msg = "❌ Neteisingai. " + (note or "Pabandykite dar kartą!")
                    if API_KEY and not note:
                        try:
                            with st.spinner("AI ruošia patarimą..."):
                                msg = "❌ Neteisingai. " + socratic_hint(item, user_ans)
                        except Exception:
                            msg = "❌ Neteisingai. Pasitikrinkite skaičiavimus ir formulę!"
                    st.session_state.feedback[tid] = ("error", msg)
                st.rerun()

            if c2.button("➡️ Praleisti", use_container_width=True):
                if prog.get(tid) != "solved":
                    prog[tid] = "skipped"
                log_event(st.session_state.user_name, tid, "PRALEIDO UŽDUOTĮ")
                st.session_state.idx += 1
                st.rerun()

            if c3.button("🏁 Baigti ir matyti reziumė", use_container_width=True):
                st.session_state.idx = total
                st.rerun()

        else:
            st.balloons()
            st.success("🎉 Užduočių sprendimas baigtas!")
            vals = list(prog.values())
            st.write(f"* **Teisingai:** {vals.count('solved')} iš {total}")
            st.write(f"* **Su klaidomis:** {vals.count('failed')}")
            st.write(f"* **Praleista:** {vals.count('skipped')}")
            st.write(f"* **Neatsakyta:** {total - len(vals)}")

            if st.button("✨ Generuoti AI įvertinimą ir patarimus", type="primary"):
                if not API_KEY:
                    st.error("Serveryje nenustatytas GEMINI_API_KEY.")
                else:
                    summary = [{"id": t["display_id"], "uzduotis": t["sub_prompt"],
                                "mokinio_atsakymas": st.session_state.answers.get(t["display_id"], ""),
                                "busena": prog.get(t["display_id"], "neatsakyta")} for t in tasks]
                    p = f"""Esi draugiškas matematikos mokytojas. Parašyk trumpą reziumė mokiniui {st.session_state.user_name}.
Duomenys: {json.dumps(summary, ensure_ascii=False)}
Pateik 3 trumpus punktus lietuvių kalba:
1. 🌟 Ką padarė gerai.
2. 💡 Kur klydo ar praleido (įvardink temas, ne tik numerius).
3. 📚 Ką pasikartoti kitai pamokai.
NENAUDOK $ ar LaTeX."""
                    try:
                        with st.spinner("AI analizuoja rezultatus..."):
                            st.markdown(ask_ai(p))
                    except Exception as e:
                        st.error(f"Klaida generuojant reziumė: {e}")

            if st.button("🔄 Grįžti prie užduočių"):
                st.session_state.idx = 0
                st.rerun()
