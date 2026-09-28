# 📐 Sokratinė Matematikos Sistema (5–6 kl.)

Prototipas, skirtas 5–6 klasių moksleiviams spręsti matematikos užduotis sokratiniu būdu. Sistema analizuoja vadovėlių ar sąsiuvinių nuotraukas, išskiria užduotis po vieną dalį, generuoja DINAMINES SVG vizualizacijas bei teikia Sokratinį grįžtamąjį ryšį.

## 🚀 Savybės

* **Rolių atskyrimas:** Atskiri langai ir galimybės mokytojui bei moksleiviui.
* **Mokytojo panelė:**
  * Vadovėlio nuotraukos analizė naudojant **Gemini 3.5 Flash** modelį.
  * Formulių bei taisyklių redagavimas ir tvirtinimas.
  * Mokinių veiksmų žurnalo (`mokiniu_logai.txt`) peržiūra ir atsisiuntimas.
* **Mokinio panelė:**
  * Užduočių išskaidymas atskirais puslapiais ($a, b, c$ dalys).
  * Dinaminis SVG vizualizavimo variklis pagal atnaujintas BP 5–6 kl. programas (kvadratas, trikampis, stačiakampis, skaičių tiesė, kampai, trapecija, apskritimas).
  * Atsakymų tikrinimas ir Sokratinės užuominos gavimas darant klaidą (atsakymas neišduodamas).
  * Baigiamoji AI reziumė ir patarimai kitai pamokai.

## 🛠️ Technologijos

* **Kalba:** Python 3.10+
* **Karkasas:** Streamlit
* **AI Modelis:** Google Gemini 3.5 Flash (`google-generativeai`)
* **Grafika:** Dinaminis SVG

## ⚙️ Lokalus paleidimas

1. Klonuokite arba atsisiųskite šią saugyklą.
2. Įdiekite reikalingas bibliotekas:
   ```bash
   pip install -r requirements.txt
