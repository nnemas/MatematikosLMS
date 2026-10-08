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
# 2. DINAMINIS SVG GRAPHICS ENGINE
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

  # 1. SKAIČIŲ TIESĖ
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
            <line x1="20" y1="65" x2="330" y2="65" stroke="#333" stroke-width="2.5"/>
            <polygon points="330,60 340,65 330,70" fill="#333"/>
            <text x="345" y="70" font-size="14" font-weight="bold" fill="#333">X</text>
            <line x1="180" y1="57" x2="180" y2="73" stroke="#333" stroke-width="2.5"/>
            <text x="177" y="90" font-size="13" font-weight="bold" fill="#333">0</text>
            <circle cx="110" cy="65" r="5" fill="#d93025"/>
            <text x="105" y="48" font-size="14" font-weight="bold" fill="#d93025">{p1_label}</text>
            <text x="100" y="90" font-size="12" font-weight="bold" fill="#333">{p1_val}</text>
            <circle cx="260" cy="65" r="5" fill="#1a73e8"/>
            <text x="255" y="48" font-size="14" font-weight="bold" fill="#1a73e8">{p2_label}</text>
            <text x="255" y="90" font-size="12" font-weight="bold" fill="#333">{p2_val}</text>
        </svg>
        """

  # 2. KVADRATAS
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

  # 3. TRIKAMPIS
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
            <text x="95" y="160" font-size="12" font-weight="bold" fill="#d93025">{ang_a if not is_right(ang_a) else '90°'}</
