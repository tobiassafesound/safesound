# ===============================================
# 🛡️ SAFE & SOUND - INSURANCE COMPARATOR (v2)
# ===============================================
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os, io, json
from dotenv import load_dotenv
from openai import OpenAI
from google.cloud import vision
from pdf2image import convert_from_bytes
from flask_cors import CORS
from pyppeteer import launch
import tempfile
import asyncio
import subprocess
import logging
logging.basicConfig(level=logging.DEBUG)



# ===============================================
# ⚙️ CONFIGURACIÓN BASE
# ===============================================
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config["JSON_AS_ASCII"] = False
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # Máx 10MB

# Detectar sistema operativo (Windows vs Render/Linux)
if os.name == "nt":  # Windows local
    POPPLER_PATH = r"C:\Program Files\poppler-25.07.0\Library\bin"
else:  # Render (Linux)
    POPPLER_PATH = None  # Usar el poppler integrado en el contenedor

# Inicializar clientes externos
client_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Inicializar cliente de Google Vision (manejo de credenciales)
if os.getenv("RENDER") == "true":  # Render define automáticamente esta variable
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/etc/secrets/vision_key.json"
    print("✅ Cargando credenciales de Google Vision desde Secret File (Render)")
else:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "backend/vision_key.json"
    print("✅ Cargando credenciales de Google Vision desde archivo local")

client_vision = vision.ImageAnnotatorClient()

# ===============================================
# 🔍 OCR con Google Cloud Vision
# ===============================================
def extract_text_from_pdf(file):
    """Convierte PDF a texto usando OCR con Google Cloud Vision."""
    print("🔍 Extrayendo texto del PDF con Google Vision...")
    text = ""
    try:
        file_bytes = file.read()
        images = convert_from_bytes(
            file_bytes,
            dpi=200,
            poppler_path=POPPLER_PATH if POPPLER_PATH else None
        )
        for i, img in enumerate(images):
            print(f"🖼 Procesando página {i+1}/{len(images)}...")
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="PNG")

            image = vision.Image(content=img_byte_arr.getvalue())
            response = client_vision.document_text_detection(image=image)

            if response.error.message:
                print(f"⚠️ Error en página {i+1}: {response.error.message}")
                continue

            text += response.full_text_annotation.text + "\n"

        print(f"✅ Texto extraído: {len(text)} caracteres")
        return text

    except Exception as e:
        print(f"⚠️ Error en extracción OCR: {e}")
        return ""

# ===============================================
# 🤖 ANÁLISIS DE TEXTO CON GPT-5 (estructura abierta)
# ===============================================
def analyze_insurance_text(text):
    """
    Analiza el contenido de una cotización PDF y devuelve una estructura abierta:
    {
      "aseguradora": "AXA",
      "plan": "Amplia Plus",
      "tipo_seguro": "Auto",
      "campos": { "Daños Materiales": "Valor comercial", ... },
      "prima_total": "$12,000",
      "vigencia": "2024-2025"
    }
    """
    lower = text.lower()

    # 1️⃣ Detección heurística del tipo de seguro
    if any(k in lower for k in ["gastos médicos", "gmm", "gmmi", "salud", "hospitalario", "coaseguro", "maternidad", "tabulador"]):
        tipo = "Medico"
    elif any(k in lower for k in ["hogar", "vivienda", "edificio", "contenidos", "rc familiar", "terremoto", "cristales"]):
        tipo = "Hogar"
    elif any(k in lower for k in ["auto", "vehículo", "automóvil", "responsabilidad civil", "robo total", "daños materiales"]):
        tipo = "Auto"
    else:
        tipo = "Desconocido"

    print(f"🧠 Tipo de seguro detectado: {tipo}")

    # 2️⃣ Prompts por tipo
    if tipo == "Auto":
        prompt = f"""
        Eres un analista experto en seguros de automóviles.
        Tu tarea es leer el texto de una cotización de seguro de auto y devolver SOLAMENTE un JSON VÁLIDO, sin comentarios ni texto adicional.

        === FORMATO ESTRICTO ===
        Devuelve exactamente esto (solo cambia los valores):

        ```json
        {{
          "aseguradora": "",
          "plan": "",
          "tipo_seguro": "Auto",
          "campos": {{
            "Daños Materiales": "",
            "Robo Total": "",
            "Deducible por pérdida total": "",
            "Deducible robo total": "",
            "Responsabilidad Civil": "",
            "RC USA": "",
            "RC Familiar": "",
            "Gastos Médicos Ocupantes": "",
            "Defensa Jurídica": "",
            "Asistencia Vial": "",
            "Automóvil Sustituto": "",
            "Coberturas adicionales": "",
            "...": ""
          }},
          "prima_total": "",
          "vigencia": ""
        }}
        ```

        === INSTRUCCIONES ===
        - Analiza TODO el texto y agrega todos los conceptos/coberturas detectados dentro de "campos".
        - Usa exactamente el nombre como aparece en el texto (ej. "RC USA", "RC Familiar", "Ayuda para gastos de transporte HDI").
        - Si un valor dice "Amparada", "No amparada", "Incluida", etc., escríbelo tal cual.
        - Si el concepto tiene monto o porcentaje, inclúyelo limpio (ej. "$1,500,000" o "5%").
        - Si hay más de un valor posible (por ejemplo, primas mensual / anual), usa la más alta prioridad: Anual.
        - No resumas ni homologues nombres.
        - No agregues ningún texto fuera del bloque JSON.
        - Si no puedes detectar algún campo, simplemente omítelo.

        === TEXTO A ANALIZAR ===
        {text}
        """

    elif tipo == "Hogar":
        prompt = f"""
        Eres un analista experto en seguros de hogar.
        Analiza el texto de la cotización y devuelve SOLO un JSON válido y correctamente cerrado. 

        === FORMATO EXACTO ===
        ```json
        {{
          "aseguradora": "",
          "plan": "",
          "tipo_seguro": "Hogar",
          "campos": {{
            "Suma asegurada edificio": "",
            "Suma asegurada contenidos": "",
            "Responsabilidad civil": "",
            "Fenómenos hidrometeorológicos": "",
            "Terremoto": "",
            "Cristales": "",
            "Robo": "",
            "Deducible": "",
            "Coaseguro": "",
            "Asistencia": "",
            "RC Familiar": "",
            "Otros": ""
          }},
          "prima_total": "",
          "vigencia": ""
        }}
        ```

        === INSTRUCCIONES ===
        - Incluye todos los conceptos que se mencionen, tal cual se escriben (no los unifiques).
        - Los nombres de clave en "campos" deben ser EXACTOS al texto (ej. "Fenómenos Hidrometeorológicos", "Incendio").
        - Si un valor no existe, omítelo.
        - Todos los valores deben ir como string limpio (ej. "$25,000", "Amparada").
        - No incluyas texto fuera del bloque JSON ni comillas extra.

        === TEXTO ===
        {text}
        """

    elif tipo == "Medico":
        prompt = f"""
        Eres un analista experto en seguros de Gastos Médicos Mayores (GMMI).
        Analiza el texto de la cotización y devuelve SOLO un JSON válido (sin texto adicional).

        === FORMATO EXACTO ===
        ```json
        {{
          "aseguradora": "",
          "plan": "",
          "tipo_seguro": "Medico",
          "campos": {{
            "Suma asegurada": "",
            "Deducible": "",
            "Coaseguro": "",
            "Tope de coaseguro": "",
            "Hospitalización": "",
            "Ambulatorio": "",
            "Maternidad": "",
            "Medicamentos": "",
            "Honorarios médicos": "",
            "Red hospitalaria": "",
            "Tabulador": "",
            "Coberturas adicionales": ""
          }},
          "prima_total": "",
          "vigencia": ""
        }}
        ```

        === INSTRUCCIONES ===
        - Incluye cada concepto detectado como clave dentro de "campos".
        - Usa los mismos nombres que aparecen en el texto (ej. “Deducible”, “Maternidad”, “Hospitalización”).
        - No inventes campos. Si no aparece, omítelo.
        - Montos y porcentajes en formato limpio (“$20,000”, “10%”).
        - Si hay varias frecuencias de pago, prioriza la anual.
        - Devuelve SOLO JSON válido (sin comillas incorrectas, sin texto adicional).
        - No incluyas explicaciones ni comentarios.

        === TEXTO ===
        {text}
        """

    else:
        # fallback genérico si no se detecta tipo
        prompt = f"""
        Devuelve SOLO un JSON válido con cualquier información estructurada que detectes en esta cotización.
        Incluye un objeto "campos" con todas las coberturas o conceptos detectados.
        Ejemplo:
        {{
          "aseguradora": "",
          "plan": "",
          "tipo_seguro": "Desconocido",
          "campos": {{}},
          "prima_total": "",
          "vigencia": ""
        }}
        Texto:
        {text}
        """

    # 3️⃣ Llamada a GPT y parseo seguro
    try:
        resp = client_openai.responses.create(model="gpt-5", input=prompt)
        raw = resp.output_text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)

        print(f"✅ GPT analizó correctamente → {parsed.get('aseguradora','(sin nombre)')}")
        return parsed

    except json.JSONDecodeError:
        print("⚠️ GPT devolvió texto no parseable como JSON.")
        return None
    except Exception as e:
        print(f"⚠️ Error analizando texto con GPT: {e}")
        return None

# ===============================================
# 🌐 ENDPOINT /compare
# ===============================================
@app.route("/compare", methods=["POST"])
def compare_pdfs():
    files = request.files.getlist("files")
    cliente = request.form.get("cliente", "Cliente")
    periodo_pago = (request.form.get("periodo_pago", "anual") or "").lower()

    if not files or len(files) < 2:
        return jsonify({"error": "Se requieren al menos dos archivos PDF"}), 400

    print(f"\n👤 Cliente: {cliente} | Archivos recibidos: {len(files)}")

    cotizaciones = []

    # 1️⃣ Procesar PDFs
    for f in files:
        try:
            print(f"📄 Analizando archivo: {f.filename}")
            text = extract_text_from_pdf(f)
            if not text.strip():
                print(f"⚠️ {f.filename}: sin texto OCR.")
                continue

            parsed = analyze_insurance_text(text)
            if not parsed:
                print(f"⚠️ {f.filename}: GPT no devolvió JSON válido.")
                continue

            cotizacion = {
                "aseguradora": parsed.get("aseguradora", "(sin nombre)").strip(),
                "plan": parsed.get("plan", "").strip(),
                "tipo_seguro": parsed.get("tipo_seguro", "Desconocido"),
                "valores": parsed.get("campos", {}),
                "prima_total": parsed.get("prima_total", ""),
                "vigencia": parsed.get("vigencia", "")
            }

            cotizaciones.append(cotizacion)
            print(f"✅ Procesado → {cotizacion['aseguradora']} ({len(cotizacion['valores'])} campos)")

        except Exception as e:
            print(f"❌ Error procesando {f.filename}: {e}")

    if not cotizaciones:
        return jsonify({"error": "No se pudo analizar ningún archivo"}), 500

    # 2️⃣ Unificar todos los campos detectados
    all_keys = set()
    for c in cotizaciones:
        if isinstance(c.get("valores"), dict):
            all_keys.update(c["valores"].keys())

    campos_unicos = sorted(all_keys)
    print(f"📋 Campos únicos detectados: {len(campos_unicos)}")

    # 3️⃣ Resumen
    resumen = {"total": len(cotizaciones)}

    # 4️⃣ Estructura final
    try:
        result = {
            "mensaje": "Comparativo generado exitosamente",
            "cliente": cliente,
            "periodo_pago": periodo_pago,
            "resumen": resumen,
            "campos": campos_unicos,
            "cotizaciones": cotizaciones
        }
        print("✅ Comparativo completado con éxito:", json.dumps(result, ensure_ascii=False)[:500])
        return jsonify(result), 200
    except Exception as e:
        print("💥 Error al generar respuesta final:", e)
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    """Genera un solo PDF (una hoja completa, sin saltos) del comparativo renderizado en Astro."""
    import subprocess, json, os

    # 1️⃣ Recibir los datos desde el front
    raw_body = request.get_data(as_text=True) or "{}"
    try:
        parsed = json.loads(raw_body)
    except Exception:
        parsed = {}
    cliente = (parsed.get("cliente") or "SafeAndSound").strip()

    # 2️⃣ URL de la vista Astro
    url_front = "http://localhost:4321/presentacion"

    # 3️⃣ Ruta de salida
    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(base_dir, "comparativos")
    os.makedirs(out_dir, exist_ok=True)
    safe_name = cliente.replace(" ", "_")
    pdf_path = os.path.join(out_dir, f"comparativo_{safe_name}.pdf")

    # 4️⃣ Preparar el JSON como string JavaScript (para inyectar en localStorage)
    raw_json_for_js = raw_body.replace("\\", "\\\\").replace("`", "\\`")

    # 5️⃣ Ejecutar Chrome headless con Puppeteer
    command = [
        "python",
        "-c",
        f"""
import asyncio, sys
from pyppeteer import launch

sys.stdout.reconfigure(encoding='utf-8')
CHROME_PATH = "C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe"

RAW = r\"\"\"{raw_json_for_js}\"\"\"  # datos de localStorage

async def main():
    browser = await launch(
        headless=True,
        executablePath=CHROME_PATH,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--window-size=1920,1080"
        ]
    )
    page = await browser.newPage()

    # Inyectar localStorage antes de cargar la página
    await page.evaluateOnNewDocument(
        \"\"\"() => {{
            try {{
                localStorage.setItem('comparativoData', `{raw_json_for_js}`);
            }} catch (e) {{
                console.error('setItem error', e);
            }}
        }}\"\"\"
    )

    # Ir a la página y esperar al marcador
    await page.goto("{url_front}", {{ "waitUntil": "networkidle0", "timeout": 120000 }})
    await page.waitForSelector("#pdf-ready", {{ "timeout": 120000 }})

    # Medir altura total del contenido
    total_height = await page.evaluate("document.body.scrollHeight")
    print(f"📏 Altura total detectada: {{total_height}}px")

    # Generar PDF de una sola hoja
    pdf_bytes = await page.pdf({{
        "printBackground": True,
        "width": "1120px",
        "height": f"{{total_height}}px",
        "margin": {{"top": "0", "bottom": "0", "left": "0", "right": "0"}}
    }})

    with open(r"{pdf_path}", "wb") as f:
        f.write(pdf_bytes)
    await browser.close()

asyncio.get_event_loop().run_until_complete(main())
"""
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Subproceso falló:", result.stderr or result.stdout)
        return jsonify({"error": "No se pudo generar el PDF"}), 500

    print("✅ PDF generado correctamente:", pdf_path)
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f"comparativo_{cliente}.pdf",
        mimetype="application/pdf",
    )

# ===============================================
# 🚀 SERVIDOR
# ===============================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
