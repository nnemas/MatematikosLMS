import json
import os
import re
from datetime import datetime
import google.generativeai as genai
import streamlit as st

# ==============================================================================
# 1. PUSLAPIO IR SESIJOS BŪSENŲ KONFIGŪRACIJA
# ==============================================================================
st.set_page_config(
    page_title="Sokratinis Math LMS (5-6 kl.)", layout="wide", page_icon="📐"
)

default_states = {
    "role": None,
    "user_name": "",
    "sub_task_list": [],
    "current_sub_idx": 0,
    "user_progress": {},
    "user_answers": {},
    "feedback_messages": {},
    "raw_formulas": "",
    "approved_formulas": "",
}

for key, val in default_states.items():
  if key not in st.session_state:
    st.session_state[key] = val

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or st.sidebar.text_input(
    "Gemini API Raktas:", type="password"
)
if GEMINI_API_KEY:
  try:
    genai.configure(api_key=GEMINI_API_KEY)
  except Exception as e:
    st.sidebar.error(f"Klaida konfigūruojant API raktą: {e}")


def log_event(student_name, task_id, action, details=""):
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  log_entry = f"[{timestamp}] Mokinys: {student_name} | Užduotis: {task_id} | Veiksmas: {action} | Detalės: {details}\n"
  try:
    with open("mokiniu_logai.txt", "a", encoding="utf-8") as f:
      f.write(log_entry)
  except Exception as e:
    st.error(f"Klaida įrašant logus: {e}")


# ==============================================================================
# 2. DINAMINIS SVG GRAPHICS ENGINE (SU SKAIČIŲ TIESE)
# ==============================================================================
def render_dynamic_shape(figure_data):
  if not isinstance(figure_data, dict):
    figure_data = {}

  shape_type = str(figure_data.get("shape_type", "triangle")).lower()
  vertices = (
      figure_data.get("vertices")
      if isinstance(figure_data.get("vertices"), list)
      else []
  )
  angles = (
      figure_data.get("angles")
      if isinstance(figure_data.get("angles"), dict)
      else {}
  )
  sides = (
      figure_data.get("sides")
      if isinstance(figure_data.get("sides"), dict)
      else {}
  )

  def is_right(val):
    str_v = str(val).lower() if val is not None else ""
    return "90" in str_v or "status" in str_v or "right" in str_v

  # --------------------------------------------------------------------------
  # 1. SKAIČIŲ TIESĖ (NAUJA / ATNAUJINTA)
  # --------------------------------------------------------------------------
  if shape_type in ["number_line", "skaiciu_tiese", "tiese"]:
    points = figure_data.get("points")
    if not isinstance(points, dict):
      points = {"A": "-3", "B": "4"}

    p_items = list(points.items())
    p1_label = p_items[0][0] if len(p_items) > 0 else "A"
    p1_val = p_items[0][1] if len(p_items) > 0 else "-3"
    p2_label = p_items[1][0] if len(p_items) > 1 else "B"
    p2_val = p_items[1][1] if len(p_items) > 1 else "4"

    svg_code = f"""
        <svg width="360" height="130" viewBox="0 0 360 130" xmlns="http://www.w3.org/2000/svg" style="background-color: #f9f9f9; border-radius: 8px; border: 1px solid #ddd;">
            <!-- Pagrindinė ašis -->
            <line x1="20" y1="65" x2="330" y2="65" stroke="#333" stroke-width="2.5"/>
            <polygon points="330,60 340,65 330,70" fill="#333"/>
            <text x="345" y="70" font-size="14" font-weight="bold" fill="#333">X</text>
            
            <!-- Nulio taškas -->
            <line x1="180" y1="57" x2="180" y2="73" stroke="#333" stroke-width="2.5"/>
            <text x="177" y="90" font-size="13" font-weight="bold" fill="#333">0</text>
            
            <!-- Taškas 1 (neigiamas / kairėje) -->
            <circle cx="110" cy="65" r="5" fill="#d93025"/>
            <text x="105" y="48" font-size="14" font-weight="bold" fill="#d93025">{p1_label}</text>
            <text x="100" y="90" font-size="12" font-weight="bold" fill="#333">{p1_val}</text>
            
            <!-- Taškas 2 (teigiamas / dešinėje) -->
            <circle cx="260" cy="65" r="5" fill="#1a73e8"/>
            <text x="255" y="48" font-size="14" font-weight="bold" fill="#1a73e8">{p2_label}</text>
            <text x="255" y="90" font-size="12" font-weight="bold" fill="#333">{p2_val}</text>
        </svg>
        """

  # --------------------------------------------------------------------------
  # 2. KVADRATAS
  # --------------------------------------------------------------------------
  elif shape_type in ["square", "kvadratas"]:
    v0 = vertices[0] if len(vertices) > 0 else "A"
    v1 = vertices[1] if len(vertices) > 1 else "B"
    v2 = vertices[2] if len(vertices) > 2 else "C"
    v3 = vertices[3] if len(vertices) > 3 else "D"
    s_side = sides.get("a", sides.get(f"{v0}{v1}", sides.get("AB", "")))

    svg_code = f"""
        <svg width="360" height="240" viewBox="0 0 360 240" xmlns="http://www.w3.org/2000/svg" style="background-color: #f9f9f9; border-radius: 8px; border: 1px solid #ddd;">
            <rect x="105" y="40" width="150" height="150" fill="rgba(156, 39, 176, 0.1)" stroke="#9c27b0" stroke-width="3"/>
            <path d="M 105,55 L 120,55 L 120,40" fill="none" stroke="#d93025" stroke-width="2"/>
            <text x="85" y="35" font-size="16" font-weight="bold" fill="#333">{v0}</text>
            <text x="265" y="35" font-size="16" font-weight="bold" fill="#333">{v1}</text>
            <text x="265" y="210" font-size="16" font-weight="bold" fill="#333">{v2}</text>
            <text x="85" y="210" font-size="16" font-weight="bold" fill="#333">{v3}</text>
            <text x="180" y="25" font-size="13" font-weight="bold" fill="#1b806a" text-anchor="middle">a = {s_side}</text>
            <text x="270" y="120" font-size="13" font-weight="bold" fill="#1b806a" text-anchor="start">a = {s_side}</text>
        </svg>
        """

  # --------------------------------------------------------------------------
  # 3. TRIKAMPIS
  # --------------------------------------------------------------------------
  elif shape_type in ["triangle", "trikampis"]:
    v0 = vertices[0] if len(vertices) > 0 else "A"
    v1 = vertices[1] if len(vertices) > 1 else "B"
    v2 = vertices[2] if len(vertices) > 2 else "C"

    ang_a = angles.get(v0, angles.get("A", ""))
    ang_b = angles.get(v1, angles.get("B", ""))
    ang_c = angles.get(v2, angles.get("C", ""))

    sq = (
        '<path d="M 70,155 L 85,155 L 85,170" fill="none" stroke="#d93025"'
        ' stroke-width="2"/>'
        if is_right(ang_a)
        else ""
    )

    s_ab = sides.get(f"{v0}{v1}", sides.get(f"{v1}{v0}", sides.get("AB", "")))
    s_bc = sides.get(f"{v1}{v2}", sides.get(f"{v2}{v1}", sides.get("BC", "")))
    s_ac = sides.get(f"{v0}{v2}", sides.get(f"{v2}{v0}", sides.get("AC", "")))

    svg_code = f"""
        <svg width="360" height="240" viewBox="0 0 360 240" xmlns="http://www.w3.org/2000/svg" style="background-color: #f9f9f9; border-radius: 8px; border: 1px solid #ddd;">
            <polygon points="70,170 290,170 70,40" fill="rgba(66, 133, 244, 0.1)" stroke="#1a73e8" stroke-width="3"/>
            {sq}
            <text x="45" y="185" font-size="16" font-weight="bold" fill="#333">{v0}</text>
            <text x="300" y="185" font-size="16" font-weight="bold" fill="#333">{v1}</text>
            <text x="55" y="30" font-size="16" font-weight="bold" fill="#333">{v2}</text>
            <text x="95" y="160" font-size="12" font-weight="bold" fill="#d93025">{ang_a if not is_right(ang_a) else '90°'}</text>
            <text x="240" y="160" font-size="12" font-weight="bold" fill="#d93025">{ang_b}</text>
            <text x="80" y="65" font-size="12" font-weight="bold" fill="#d93025">{ang_c}</text>
            <text x="175" y="190" font-size="13" font-weight="bold" fill="#1b806a" text-anchor="middle">{v0}{v1} = {s_ab}</text>
            <text x="195" y="100" font-size="13" font-weight="bold" fill="#1b806a" text-anchor="start">{v1}{v2} = {s_bc}</text>
            <text x="10" y="110" font-size="13" font-weight="bold" fill="#1b806a" text-anchor="start">{v0}{v2} = {s_ac}</text>
        </svg>
        """

  # --------------------------------------------------------------------------
  # 4. STAČIAKAMPIS / KETURKAMPIS
  # --------------------------------------------------------------------------
  elif shape_type in [
      "rectangle",
      "quadrilateral",
      "staciakampis",
      "keturkampis",
  ]:
    v0 = vertices[0] if len(vertices) > 0 else "A"
    v1 = vertices[1] if len(vertices) > 1 else "B"
    v2 = vertices[2] if len(vertices) > 2 else "C"
    v3 = vertices[3] if len(vertices) > 3 else "D"

    s_ab = sides.get(f"{v0}{v1}", sides.get("AB", ""))
    s_bc = sides.get(f"{v1}{v2}", sides.get("BC", ""))

    svg_code = f"""
        <svg width="360" height="240" viewBox="0 0 360 240" xmlns="http://www.w3.org/2000/svg" style="background-color: #f9f9f9; border-radius: 8px; border: 1px solid #ddd;">
            <rect x="70" y="50" width="220" height="120" fill="rgba(52, 168, 83, 0.1)" stroke="#34a853" stroke-width="3"/>
            <text x="50" y="45" font-size="16" font-weight="bold" fill="#333">{v0}</text>
            <text x="300" y="45" font-size="16" font-weight="bold" fill="#333">{v1}</text>
            <text x="300" y="190" font-size="16" font-weight="bold" fill="#333">{v2}</text>
            <text x="50" y="190" font-size="16" font-weight="bold" fill="#333">{v3}</text>
            <text x="180" y="35" font-size="13" font-weight="bold" fill="#1b806a" text-anchor="middle">{s_ab}</text>
            <text x="300" y="115" font-size="13" font-weight="bold" fill="#1b806a" text-anchor="start">{s_bc}</text>
        </svg>
        """

  # --------------------------------------------------------------------------
  # 5. KAMPAI
  # --------------------------------------------------------------------------
  elif shape_type in ["angle", "kampas", "gretutiniai_kampai"]:
    ang_a = angles.get("A", "60°")
    ang_b = angles.get("B", "120°")
    svg_code = f"""
        <svg width="360" height="180" viewBox="0 0 360 180" xmlns="http://www.w3.org/2000/svg" style="background-color: #f9f9f9; border-radius: 8px; border: 1px solid #ddd;">
            <line x1="30" y1="140" x2="330" y2="140" stroke="#333" stroke-width="2.5"/>
            <line x1="180" y1="140" x2="260" y2="40" stroke="#1a73e8" stroke-width="2.5"/>
            <path d="M 210,140 A 30,30 0 0,0 200,115" fill="none" stroke="#d93025" stroke-width="2"/>
            <text x="220" y="125" font-size="13" font-weight="bold" fill="#d93025">{ang_a}</text>
            <path d="M 150,140 A 30,30 0 0,1 160,115" fill="none" stroke="#1b806a" stroke-width="2"/>
            <text x="130" y="125" font-size="13" font-weight="bold" fill="#1b806a">{ang_b}</text>
            <circle cx="180" cy="140" r="4" fill="#333"/>
            <text x="175" y="160" font-size="14" font-weight="bold">O</text>
        </svg>
        """

  # --------------------------------------------------------------------------
  # 6. TRAPECIJA
  # --------------------------------------------------------------------------
  elif shape_type in ["trapezoid", "trapecija"]:
    v0 = vertices[0] if len(vertices) > 0 else "A"
    v1 = vertices[1] if len(vertices) > 1 else "B"
    s_ab = sides.get("AB", "")
    s_cd = sides.get("CD", "")
    svg_code = f"""
        <svg width="360" height="240" viewBox="0 0 360 240" xmlns="http://www.w3.org/2000/svg" style="background-color: #f9f9f9; border-radius: 8px; border: 1px solid #ddd;">
            <polygon points="50,170 290,170 230,50 110,50" fill="rgba(255, 153, 0, 0.1)" stroke="#ff9900" stroke-width="3"/>
            <text x="30" y="185" font-size="16" font-weight="bold" fill="#333">{v0}</text>
            <text x="300" y="185" font-size="16" font-weight="bold" fill="#333">{v1}</text>
            <text x="170" y="40" font-size="13" fill="#1b806a" text-anchor="middle">{s_cd}</text>
            <text x="170" y="190" font-size="13" fill="#1b806a" text-anchor="middle">{s_ab}</text>
        </svg>
        """

  # --------------------------------------------------------------------------
  # 7. APSKRITIMAS
  # --------------------------------------------------------------------------
  elif shape_type in ["circle", "apskritimas", "skritulys"]:
    r_val = sides.get("r", "")
    svg_code = f"""
        <svg width="360" height="240" viewBox="0 0 360 240" xmlns="http://www.w3.org/2000/svg" style="background-color: #f9f9f9; border-radius: 8px; border: 1px solid #ddd;">
            <circle cx="180" cy="115" r="70" fill="rgba(234, 67, 53, 0.1)" stroke="#ea4335" stroke-width="3"/>
            <circle cx="180" cy="115" r="4" fill="#333"/>
            <line x1="180" y1="115" x2="250" y2="115" stroke="#ea4335" stroke-width="2" stroke-dasharray="4"/>
            <text x="160" y="110" font-size="14" font-weight="bold" fill="#333">O</text>
            <text x="200" y="135" font-size="13" fill="#1b806a">r = {r_val}</text>
        </svg>
        """

  else:
    svg_code = f"<div style='padding:10px; color:#666;'>Geometrinės figūros ({shape_type}) vizualizacija nepasiekiama.</div>"

  st.components.v1.html(svg_code, height=150 if "tiese" in shape_type else 250)


# Atsakymų tikrinimas
def check_answer_accuracy(user_input, correct_input):
  if user_input is None or correct_input is None:
    return False
  clean_u = (
      re.sub(r"[^0-9a-zA-Z,/.-]", "", str(user_input))
      .replace(",", ".")
      .strip()
      .lower()
  )
  clean_c = (
      re.sub(r"[^0-9a-zA-Z,/.-]", "", str(correct_input))
      .replace(",", ".")
      .strip()
      .lower()
  )
  if not clean_u or not clean_c:
    return False
  if clean_u == clean_c:
    return True

  if "/" in clean_u or "/" in clean_c:
    try:
      u_val = (
          float(clean_u.split("/")[0]) / float(clean_u.split("/")[1])
          if "/" in clean_u
          else float(clean_u)
      )
      c_val = (
          float(clean_c.split("/")[0]) / float(clean_c.split("/")[1])
          if "/" in clean_c
          else float(clean_c)
      )
      return abs(u_val - c_val) < 0.01
    except Exception:
      pass

  try:
    if abs(float(clean_u) - float(clean_c)) < 0.01:
      return True
  except ValueError:
    pass
  return False


# ==============================================================================
# 3. ROLIŲ SELEKTORIUS
# ==============================================================================
if not st.session_state.role:
  st.title("📐 Sokratinė Matematikos Sistema (5-6 kl.)")
  st.write("Sveiki! Įveskite savo vardą ir pasirinkite prisijungimo rolę.")

  col1, _ = st.columns([1, 1])
  with col1:
    name_input = st.text_input(
        "Jūsų vardas:", placeholder="pvz., Mantas ar Mokytoja Rasa"
    )
    st.write("---")
    st.subheader("Pasirinkite rolę:")

    c1, c2 = st.columns(2)
    with c1:
      if st.button(
          "🎓 Aš esu Mokinys", use_container_width=True, type="primary"
      ):
        if name_input.strip():
          st.session_state.user_name = name_input.strip()
          st.session_state.role = "student"
          st.rerun()
        else:
          st.warning("Prašome įvesti vardą!")
    with c2:
      if st.button("👨‍🏫 Aš esu Mokytojas", use_container_width=True):
        if name_input.strip():
          st.session_state.user_name = name_input.strip()
          st.session_state.role = "teacher"
          st.rerun()
        else:
          st.warning("Prašome įvesti vardą!")

# ==============================================================================
# 4. MOKYTOJO PANELĖ
# ==============================================================================
elif st.session_state.role == "teacher":
  st.sidebar.title(f"👨‍🏫 Mokytojas: {st.session_state.user_name}")
  if st.sidebar.button("Atsijungti / Keisti rolę"):
    st.session_state.role = None
    st.rerun()

  st.title("Mokytojo Valdymo Panelė")
  tab1, tab2 = st.tabs(
      ["📸 Užduoties Įkėlimas ir Formulių Redagavimas", "📋 Mokinių Logai"]
  )

  with tab1:
    uploaded_file = st.file_uploader(
        "Įkelkite sąsiuvinio ar vadovėlio nuotrauką", type=["jpg", "jpeg", "png"]
    )

    if uploaded_file:
      st.image(uploaded_file, caption="Įkelta nuotrauka", width=400)

      if st.button("Išanalizuoti nuotrauką", type="primary"):
        if not GEMINI_API_KEY:
          st.error("Įveskite Gemini API raktą šoninėje juostoje!")
        else:
          with st.spinner("AI analizuoja nuotrauką..."):
            try:
              image_bytes = uploaded_file.getvalue()
              image_part = {
                  "mime_type": uploaded_file.type,
                  "data": image_bytes,
              }

              prompt = """Išanalizuok šios matematikos užduoties nuotrauką.
Grąžink atsakymą TIK ŠIUO STRUKTŪRIZUOTU JSON FORMATU (be jokių markdown ```json kodo blokų):

{
  "formulas": "Svarbiausios taisyklės ir formulės trumpai, punktais lietuvių kalba.",
  "tasks": [
    {
      "task_number": "1",
      "question": "Apskaičiuokite figūros perimetrą arba raskite taškų koordinates.",
      "sub_tasks": [
        {
          "label": "a",
          "prompt": "Raskite taško A koordinatę skaičių tiesėje.",
          "correct_answer": "-3",
          "has_figure": true,
          "figure_data": {
            "shape_type": "number_line",
            "points": {"A": "-3", "B": "4"}
          },
          "formula_hint": "Skaičių tiesėje neigiami skaičiai yra į kairę nuo 0."
        }
      ]
    }
  ]
}

GRIEŽTOS TAISYKLĖS:
1. Įtrauk 'correct_answer' reiškmę.
2. shape_type gali būti: 'square', 'triangle', 'rectangle', 'quadrilateral', 'trapezoid', 'circle', 'number_line', 'angle'.
3. NENAUDOK $ arba LaTeX simbolių.
"""
              model = genai.GenerativeModel("gemini-2.5-flash")
              response = model.generate_content([prompt, image_part])
              raw_text = response.text.strip() if response.text else ""

              match = re.search(r"\{.*\}", raw_text, re.DOTALL)
              clean_json = match.group(0) if match else raw_text
              data = json.loads(clean_json, strict=False)

              st.session_state.raw_formulas = data.get("formulas", "") or ""
              st.session_state.approved_formulas = data.get("formulas", "") or ""

              flat_list = []
              for t in data.get("tasks", []):
                if not isinstance(t, dict):
                  continue
                t_num = str(t.get("task_number", "1"))
                subs = t.get("sub_tasks", [])
                if isinstance(subs, list) and len(subs) > 0:
                  for sub in subs:
                    if not isinstance(sub, dict):
                      continue
                    flat_list.append({
                        "display_id": f"{t_num}{sub.get('label', '')}",
                        "main_question": str(t.get("question", "")),
                        "sub_prompt": str(sub.get("prompt", "")),
                        "correct_answer": str(
                            sub.get("correct_answer", "")
                            if sub.get("correct_answer") is not None
                            else ""
                        ).strip(),
                        "has_figure": bool(sub.get("has_figure", False)),
                        "figure_data": (
                            sub.get("figure_data", {})
                            if isinstance(sub.get("figure_data"), dict)
                            else {}
                        ),
                        "formula_hint": str(sub.get("formula_hint", "")),
                    })
                else:
                  flat_list.append({
                      "display_id": f"{t_num}",
                      "main_question": str(t.get("question", "")),
                      "sub_prompt": "Apskaičiuokite ir įrašykite atsakymą:",
                      "correct_answer": str(
                          t.get("correct_answer", "")
                          if t.get("correct_answer") is not None
                          else ""
                      ).strip(),
                      "has_figure": bool(t.get("has_figure", False)),
                      "figure_data": (
                          t.get("figure_data", {})
                          if isinstance(t.get("figure_data"), dict)
                          else {}
                      ),
                      "formula_hint": str(t.get("formula_hint", "")),
                  })

              st.session_state.sub_task_list = flat_list
              st.session_state.current_sub_idx = 0
              st.session_state.user_progress = {}
              st.session_state.user_answers = {}
              st.session_state.feedback_messages = {}

              st.success("Analizė sėkminga! Užduotys paruoštos.")
              st.rerun()
            except Exception as e:
              st.error(f"Klaida analizuojant nuotrauką: {e}")

    if st.session_state.raw_formulas or st.session_state.approved_formulas:
      st.write("---")
      st.subheader("📝 Formulių ir Taisyklių Redagavimas")
      edited_formulas = st.text_area(
          "Formulės ir taisyklės mokiniui:",
          value=st.session_state.approved_formulas
          or st.session_state.raw_formulas,
          height=150,
      )
      if st.button("✅ Patvirtinti formules mokiniams", type="primary"):
        st.session_state.approved_formulas = edited_formulas
        st.success("Formulės patvirtintos!")

  with tab2:
    st.subheader("Mokinių Veiksmų Žurnalas (Ataskaita)")
    if os.path.exists("mokiniu_logai.txt"):
      try:
        with open("mokiniu_logai.txt", "r", encoding="utf-8") as f:
          logs = f.read()
        st.text_area("Logų failo turinys:", logs, height=300)
        st.download_button(
            "Atsisiūsti logų failą", logs, file_name="mokiniu_logai.txt"
        )
      except Exception as e:
        st.error(f"Klaida skaitant logus: {e}")
    else:
      st.write("Logų failas dar nesugeneruotas.")

# ==============================================================================
# 5. MOKINIO PANELĖ
# ==============================================================================
elif st.session_state.role == "student":
  st.sidebar.title(f"🎓 Mokinys: {st.session_state.user_name}")
  if st.sidebar.button("Atsijungti / Keisti rolę"):
    st.session_state.role = None
    st.rerun()

  st.title("Matematikos Užduočių Sprendimas")

  if st.session_state.approved_formulas:
    with st.expander(
        "💡 Pagalbinės Formulės ir Taisyklės (Spauskite čia)", expanded=False
    ):
      st.write(st.session_state.approved_formulas)

  if not st.session_state.sub_task_list:
    st.warning(
        "Užduočių kol kas nėra. Mokytojas dar neįkėlė pamokos medžiagos."
    )
  else:
    st.write("### Užduočių navigacija:")

    total_tasks = len(st.session_state.sub_task_list)
    chunk_size = 8

    for i in range(0, total_tasks, chunk_size):
      chunk = st.session_state.sub_task_list[i : i + chunk_size]
      cols = st.columns(len(chunk))
      for j, item in enumerate(chunk):
        idx_num = i + j
        t_id = item["display_id"]
        status = st.session_state.user_progress.get(t_id, "unanswered")

        if status == "solved":
          label = f"✅ {t_id}"
        elif status == "failed":
          label = f"❌ {t_id}"
        elif status == "skipped":
          label = f"⚪ {t_id}"
        else:
          label = f"📄 {t_id}"

        btn_type = (
            "primary"
            if idx_num == st.session_state.current_sub_idx
            else "secondary"
        )
        if cols[j].button(
            label,
            key=f"nav_btn_{idx_num}",
            type=btn_type,
            use_container_width=True,
        ):
          st.session_state.current_sub_idx = idx_num
          st.rerun()

    st.write("---")

    idx = st.session_state.current_sub_idx
    total_subs = len(st.session_state.sub_task_list)

    if idx < total_subs:
      item = st.session_state.sub_task_list[idx]
      t_id = item["display_id"]

      st.subheader(f"Užduotis {t_id} ({idx + 1} iš {total_subs})")
      st.write(f"**Sąlyga:** {item['main_question']}")

      if item.get("has_figure") and item.get("figure_data"):
        render_dynamic_shape(item["figure_data"])

      if item.get("formula_hint"):
        with st.expander("🔑 Rodyti užuominą"):
          st.info(item["formula_hint"])

      st.write("---")
      existing_ans = st.session_state.user_answers.get(t_id, "")
      user_ans = st.text_input(
          f"👉 {item['sub_prompt']}",
          value=existing_ans,
          key=f"sub_input_{idx}",
      )

      if t_id in st.session_state.feedback_messages:
        fb_type, fb_msg = st.session_state.feedback_messages[t_id]
        if fb_type == "success":
          st.success(fb_msg)
        else:
          st.error(fb_msg)

      col1, col2, col3 = st.columns([1, 1, 1])

      with col1:
        if st.button(
            "Pateikti atsakymą", type="primary", use_container_width=True
        ):
          st.session_state.user_answers[t_id] = user_ans
          is_correct = check_answer_accuracy(
              user_ans, item.get("correct_answer", "")
          )

          if is_correct:
            st.session_state.user_progress[t_id] = "solved"
            st.session_state.feedback_messages[t_id] = (
                "success",
                "🎉 Teisingai! Puikus darbas.",
            )
            log_event(
                st.session_state.user_name, t_id, "TEISINGAS ATSAKYMAS", user_ans
            )
            st.session_state.current_sub_idx += 1
            st.rerun()
          else:
            st.session_state.user_progress[t_id] = "failed"
            log_event(
                st.session_state.user_name,
                t_id,
                "NETEISINGAS ATSAKYMAS",
                user_ans,
            )

            if GEMINI_API_KEY:
              with st.spinner("AI tikrina atsakymą..."):
                s_prompt = f"""Mokinys sprendžia užduotį: '{item['sub_prompt']}'.
Teisingas atsakymas: '{item['correct_answer']}'.
Mokinio įvestas neteisingas atsakymas: '{user_ans}'.

Pateik 1-2 trumpus Sokratinius sakinius lietuvių kalba, kurie nukreiptų 6-oką teisinga linkme, bet NEIŠDUOTŲ teisingo atsakymo.
NENAUDOK $ arba LaTeX.
"""
                try:
                  m = genai.GenerativeModel("gemini-2.5-flash")
                  r = m.generate_content(s_prompt)
                  st.session_state.feedback_messages[t_id] = (
                      "error",
                      f"❌ Neteisingai. Sokratinis patarimas: {r.text}",
                  )
                except Exception:
                  st.session_state.feedback_messages[t_id] = (
                      "error",
                      "❌ Neteisingai. Pasitikrinkite skaičiavimus ir formulę!",
                  )
            else:
              st.session_state.feedback_messages[t_id] = (
                  "error",
                  "❌ Neteisingai. Bandykite dar kartą!",
              )
            st.rerun()

      with col2:
        if st.button("➡️ Praleisti užduotį", use_container_width=True):
          if (
              t_id not in st.session_state.user_progress
              or st.session_state.user_progress[t_id] != "solved"
          ):
            st.session_state.user_progress[t_id] = "skipped"
          log_event(
              st.session_state.user_name,
              t_id,
              "PRALEIDO UŽDUOTĮ",
              "Užduotis praleista",
          )
          st.session_state.current_sub_idx += 1
          st.rerun()

      with col3:
        if st.button(
            "🏁 Baigti ir matyti reziumė", use_container_width=True
        ):
          st.session_state.current_sub_idx = total_subs
          st.rerun()

    # REZIUMĖ LANGAS
    if idx >= total_subs:
      st.balloons()
      st.success("🎉 Užduočių sprendimas baigtas!")
      st.subheader(
          f"📊 Mokinio {st.session_state.user_name} Reziumė ir Ataskaita"
      )

      solved_count = sum(
          1
          for v in st.session_state.user_progress.values()
          if v == "solved"
      )
      failed_count = sum(
          1
          for v in st.session_state.user_progress.values()
          if v == "failed"
      )
      skipped_count = sum(
          1
          for v in st.session_state.user_progress.values()
          if v == "skipped"
      )

      st.write(
          f"* **Teisingai išspręsta:** {solved_count} iš {total_subs}"
      )
      st.write(f"* **Su klaidomis / Neteisingai:** {failed_count}")
      st.write(f"* **Praleista užduočių:** {skipped_count}")

      if st.button(
          "✨ Generuoti AI Įvertinimą ir Patarimus", type="primary"
      ):
        if not GEMINI_API_KEY:
          st.error("Įveskite API raktą šoninėje juostoje!")
        else:
          with st.spinner("AI analizuoja jūsų rezultatus..."):
            summary_prompt = f"""Esi draugiškas matematikos mokytojas. Paruošk trumpą reziumė 6-okui {st.session_state.user_name}.
Mokinio rezultatai:
Atsakymai: {json.dumps(st.session_state.user_answers, ensure_ascii=False)}
Būsenos: {json.dumps(st.session_state.user_progress, ensure_ascii=False)}

Pateik 3 trumpus punktus lietuvių kalba:
1. 🌟 Ką mokinys atliko gerai.
2. 💡 Kur darė klaidas ar praleido.
3. 📚 Konkretus patarimas, ką pasikartoti kitai pamokai.
NENAUDOK $ arba LaTeX.
"""
            try:
              model = genai.GenerativeModel("gemini-2.5-flash")
              res = model.generate_content(summary_prompt)
              st.markdown(res.text)
            except Exception as e:
              st.error(f"Klaida generuojant reziumė: {e}")

      st.write("---")
      if st.button("🔄 Grįžti prie užduočių"):
        st.session_state.current_sub_idx = 0
        st.rerun()
