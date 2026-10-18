import os
import re
import time
import json
import pandas as pd
from tqdm import tqdm
from google import genai
from google.genai import types

# --- 1. CONFIGURACIÓN DE LA API Y PARÁMETROS ---

os.environ["GEMINI_API_KEY"] = ""

client = genai.Client()

MODEL_NAME = "gemini-flash-latest"

# Pausa regular entre peticiones para el Free Tier (15 RPM -> 4.0s)
PAUSA_ENTRE_PETICIONES = 4.0

# --- 2. RUTAS DE ARCHIVOS Y REANUDACIÓN DESDE EL ÚLTIMO FALLIDO ---

script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
posibles_rutas_input = [
    os.path.join(script_dir, "muestra_sudoku_385.csv"),
    os.path.join(script_dir, "Sudokus Test", "muestra_sudoku_385.csv"),
    "muestra_sudoku_385.csv"
]

ruta_csv_input = None
for p in posibles_rutas_input:
    if os.path.exists(p):
        ruta_csv_input = p
        break

if not ruta_csv_input:
    raise FileNotFoundError("No se encontró el archivo 'muestra_sudoku_385.csv'. Verifica la ubicación.")

df_input = pd.read_csv(ruta_csv_input, dtype=str)
ruta_csv_output = os.path.join(script_dir, 'resultados_gemini.csv')

# Filtrar e identificar celdas procesadas correctamente (True)
procesados_correctos = set()

if os.path.exists(ruta_csv_output):
    try:
        df_existente = pd.read_csv(ruta_csv_output, dtype=str)
        if 'correcto' in df_existente.columns and 'id_tablero' in df_existente.columns:
            # Mantener SOLO los registros donde correcto == True
            df_exitosos = df_existente[df_existente['correcto'].astype(str).str.upper() == 'TRUE']
            procesados_correctos = set(df_exitosos['id_tablero'].astype(str).tolist())
            
            # Sobrescribir el CSV dejando solo las respuestas exitosas
            df_exitosos.to_csv(ruta_csv_output, index=False)
            
            num_eliminados = len(df_existente) - len(df_exitosos)
            print(f"--- REANUDACIÓN ACTIVADA ---")
            print(f"Sudokus resueltos correctamente conservados (True): {len(procesados_correctos)}")
            if num_eliminados > 0:
                print(f"Sudokus fallidos (False) removidos para reintento: {num_eliminados}")
    except Exception as e:
        print(f"Aviso al procesar archivo CSV previo: {e}")

# --- 3. INSTRUCCIONES DEL SISTEMA ---

SYSTEM_INSTRUCTION = """
You are a deterministic 9x9 Sudoku solver logic engine.
Given an 81-character Sudoku string where dots (.) represent empty cells, solve it completely.

Respond ONLY in valid JSON with this exact structure:
{
  "solved_sudoku": "81_digit_string_here",
  "estimated_operations": number_of_logical_steps_or_constraint_checks_executed
}
"""

def extraer_solucion_81_digitos(texto_raw):
    """Extrae mediante expresión regular la secuencia limpia de 81 dígitos."""
    if not texto_raw:
        return ""
    match = re.search(r'[1-9]{81}', texto_raw)
    if match:
        return match.group(0)
    solo_digitos = re.sub(r'[^1-9]', '', texto_raw)
    if len(solo_digitos) == 81:
        return solo_digitos
    return ""

# --- 4. BUCLE DE EXPERIMENTACIÓN CON RETRY Y MANEJO DE INDISPONIBILIDAD ---

print(f"\n--- EJECUTANDO EVALUACIÓN CON GEMINI ({MODEL_NAME}) ---")
print(f"Total de Sudokus a procesar / reintentar: {len(df_input) - len(procesados_correctos)}")

for idx, row in tqdm(df_input.iterrows(), total=len(df_input), desc="Evaluando Sudokus"):
    id_tablero = str(row.get('id_tablero', idx + 1)).strip()

    # Si ya se resolvió exitosamente (correcto == True), se omite
    if id_tablero in procesados_correctos:
        continue

    puzzle = str(row['question']).strip()
    expected = str(row['answer']).strip()
    categoria = str(row.get('dificultad_categoria', 'N/A'))
    rating = str(row.get('rating', '0'))

    prompt_user = f"Solve this Sudoku puzzle string:\n{puzzle}"

    answer_gemini = ""
    operaciones_gemini = 0
    error_msg = ""
    tiempo_ms = 0.0

    # Bucle de reintento en caso de servidor no disponible / cuota (HTTP 503, 429, ResourceExhausted, etc.)
    while True:
        t0 = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_user,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.0,
                )
            )

            t1 = time.perf_counter()
            tiempo_ms = (t1 - t0) * 1000.0

            texto_resp = response.text.strip() if response.text else ""

            try:
                parsed = json.loads(texto_resp)
                solved_raw = str(parsed.get("solved_sudoku", ""))
                operaciones_gemini = int(parsed.get("estimated_operations", 0))
                answer_gemini = extraer_solucion_81_digitos(solved_raw)
            except Exception:
                answer_gemini = extraer_solucion_81_digitos(texto_resp)
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    operaciones_gemini = getattr(response.usage_metadata, 'total_token_count', 0)

            break  # Salida exitosa del bucle de reintento

        except Exception as e:
            err_str = str(e).lower()
            palabras_clave_indisponible = [
                'unavailable', '503', '429', 'resource_exhausted', 
                'quota', 'rate', 'overloaded', 'try again', 'server error'
            ]

            # Si el servidor no está disponible o se sobrepasó la tasa, esperar 60 segundos y reintentar
            if any(k in err_str for k in palabras_clave_indisponible):
                tqdm.write(f"\n⚠️ Servidor no disponible o límite de API alcanzado para ID {id_tablero} ({e}). Espere 60s...")
                time.sleep(60)
                continue
            else:
                # Error fatal no recuperable
                t1 = time.perf_counter()
                tiempo_ms = (t1 - t0) * 1000.0
                error_msg = str(e)
                break

    is_correct = (answer_gemini == expected)

    fila_resultado = {
        'id_tablero': id_tablero,
        'dificultad_categoria': categoria,
        'rating': rating,
        'question': puzzle,
        'answer_expected': expected,
        'answer_gemini': answer_gemini,
        'correcto': is_correct,
        'tiempo_ms': round(tiempo_ms, 4),
        'operaciones_gemini': operaciones_gemini,
        'error_log': error_msg
    }

    # Guardado incremental inmediato en disco
    df_single = pd.DataFrame([fila_resultado])
    necesita_cabecera = not os.path.exists(ruta_csv_output)
    df_single.to_csv(ruta_csv_output, mode='a', header=necesita_cabecera, index=False)

    if is_correct:
        procesados_correctos.add(id_tablero)

    # Pausa de cortesía para respetar la cuota
    if PAUSA_ENTRE_PETICIONES > 0:
        time.sleep(PAUSA_ENTRE_PETICIONES)

# --- 5. REPORTES DE RESULTADOS ---

if os.path.exists(ruta_csv_output):
    res_df = pd.read_csv(ruta_csv_output, dtype=str)
    res_df['correcto'] = res_df['correcto'].astype(str).str.upper() == 'TRUE'
    res_df['tiempo_ms'] = pd.to_numeric(res_df['tiempo_ms'], errors='coerce')
    res_df['operaciones_gemini'] = pd.to_numeric(res_df['operaciones_gemini'], errors='coerce')

    print("\n" + "="*60)
    print("--- RESUMEN FINAL COMPLETO DE RESULTADOS ---")
    print("="*60)
    print(f"Archivo guardado en: {ruta_csv_output}")
    print(f"Total procesados:   {len(res_df)}")
    print(f"Aciertos totales:   {res_df['correcto'].sum()}/{len(res_df)} ({res_df['correcto'].mean()*100:.2f}%)")
    print(f"Tiempo promedio:    {res_df['tiempo_ms'].mean():.2f} ms")

    print("\nDesglose cuantitativo por dificultad:")
    print(res_df.groupby('dificultad_categoria').agg(
        aciertos=('correcto', 'sum'),
        total=('id_tablero', 'count'),
        tiempo_ms=('tiempo_ms', 'mean'),
        operaciones_promedio=('operaciones_gemini', 'mean')
    ))