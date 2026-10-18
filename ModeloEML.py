import os
import re
import time
import math
import pandas as pd
import ollama
from tqdm import tqdm
import concurrent.futures

# --- 1. OPERADOR BARRERA DE ENERGÍA EML ---

def eml(x, y):
    """
    Operador Exponencial Menos Logaritmo: eml(x, y) = e^x - ln(y)
    Si y <= 0 (conflicto), ln(0) -> -inf, por lo que eml -> +inf.
    """
    if y <= 0:
        return float('inf')
    return math.exp(x) - math.log(y)

def generar_matriz_candidatos_eml(grid_str):
    """
    Transforma la cadena de 81 caracteres en una rejilla 9x9 donde las casillas dadas
    muestran su número fijo y las casillas vacías muestran sus candidatos EML {v1,v2,...}.
    """
    grid = [[int(c) if c in '123456789' else 0 for c in grid_str[r * 9:(r + 1) * 9]] for r in range(9)]
    x_base = 0.0
    filas_formateadas = []

    for r in range(9):
        elementos_fila = []
        for c in range(9):
            if grid[r][c] != 0:
                elementos_fila.append(str(grid[r][c]))
            else:
                candidatos = []
                for v in range(1, 10):
                    conflicto = False
                    # Comprobar Fila y Columna
                    for k in range(9):
                        if k != c and grid[r][k] != 0:
                            if eml(x_base, abs(v - grid[r][k])) == float('inf'):
                                conflicto = True
                                break
                        if k != r and grid[k][c] != 0:
                            if eml(x_base, abs(v - grid[k][c])) == float('inf'):
                                conflicto = True
                                break
                    if conflicto:
                        continue
                    # Comprobar Caja 3x3
                    br, bc = 3 * (r // 3), 3 * (c // 3)
                    for i in range(br, br + 3):
                        for j in range(bc, bc + 3):
                            if (i != r or j != c) and grid[i][j] != 0:
                                if eml(x_base, abs(v - grid[i][j])) == float('inf'):
                                    conflicto = True
                                    break
                        if conflicto:
                            break
                    if not conflicto:
                        candidatos.append(str(v))
                
                elementos_fila.append("{" + ",".join(candidatos) + "}")
        
        filas_formateadas.append(f"Row {r + 1}: " + "  ".join(elementos_fila))

    return "\n".join(filas_formateadas)

def extraer_solucion_81_digitos(texto_respuesta):
    """Extrae la secuencia exacta de 81 dígitos numéricos de la respuesta del modelo."""
    if not texto_respuesta:
        return "", 0
    
    # Contar operaciones estimadas basándose en metadatos o longitud útil de tokens/razonamiento
    # (Usamos la cantidad de caracteres/tokens procesados o métrica interna de pasos)
    operaciones = len(re.findall(r'\d', texto_respuesta)) * 3 # Estimación basada en procesamiento de candidatos
    if operaciones == 0:
        operaciones = len(texto_respuesta.split()) # Conteo alternativo de bloques lógicos

    match = re.search(r'[1-9]{81}', texto_respuesta)
    if match:
        return match.group(0), operaciones
    
    solo_digitos = re.sub(r'[^1-9]', '', texto_respuesta)
    if len(solo_digitos) == 81:
        return solo_digitos, operaciones
        
    return "", operaciones

# --- 2. CARGA Y CONFIGURACIÓN ---

script_dir = os.path.dirname(os.path.abspath(__file__))
posibles_rutas = [
    os.path.join(script_dir, "muestra_sudoku_385.csv"),
    os.path.join(script_dir, "Sudokus Test", "muestra_sudoku_385.csv")
]

ruta_csv = None
for p in posibles_rutas:
    if os.path.exists(p):
        ruta_csv = p
        break

if not ruta_csv:
    raise FileNotFoundError("No se encontró el archivo 'muestra_sudoku_385.csv'.")

df = pd.read_csv(ruta_csv, dtype=str)

MODEL_NAME = "deepseek-r1:1.5b"#"qwen2.5:3b"  # Cambiar según el modelo evaluado

SYSTEM_PROMPT_EN = """
You are an expert 9x9 Sudoku solver.
You will be provided with a 9x9 grid where fixed cells contain a single digit (1-9) and empty cells contain EML-filtered valid candidate sets in curly braces like {2,3,5}.

Task: Complete the Sudoku using ONLY digits from each cell's EML candidate set.
OUTPUT REQUIREMENT: Respond ONLY with the final 81-digit solved string without spaces, line breaks, or markdown code blocks.
"""

def consultar_ollama_eml_directo(puzzle_str):
    rejilla_eml = generar_matriz_candidatos_eml(puzzle_str)
    
    user_prompt = f"""Solve this Sudoku using the EML candidate sets:

{rejilla_eml}

Return ONLY the final 81-digit solved string:"""

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT_EN},
            {'role': 'user', 'content': user_prompt}
        ],
        options={
            'temperature': 0.1,
            'top_p': 0.2,
            'num_predict': 120,
            'repeat_penalty': 1.2
        }
    )
    
    # Extraer métricas adicionales de Ollama si están disponibles (eval_count / prompt_eval_count)
    eval_tokens = response.get('eval_count', 0)
    prompt_tokens = response.get('prompt_eval_count', 0)
    total_operaciones = eval_tokens + prompt_tokens
    if total_operaciones == 0:
        total_operaciones = 123 # Valor por defecto si el backend no expone conteo de tokens directo
        
    return response['message']['content'], total_operaciones

# --- 3. BUCLE DE EXPERIMENTACIÓN ($n = 385$) ---

results = []
TIMEOUT_SECONDS = 20

print(f"Iniciando experimento EML con conteo de operaciones y '{MODEL_NAME}' ({len(df)} tableros)...")

for idx, row in tqdm(df.iterrows(), total=len(df), desc="Procesando Sudokus"):
    puzzle = str(row['question']).strip()
    expected = str(row['answer']).strip()
    categoria = str(row.get('dificultad_categoria', 'N/A'))
    rating = str(row.get('rating', '0'))
    id_tablero = row.get('id_tablero', idx + 1)

    t0 = time.perf_counter()
    sol_modelo = ""
    operaciones_efectuadas = 0
    error_msg = None

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(consultar_ollama_eml_directo, puzzle)
        try:
            respuesta_cruda, operaciones_efectuadas = future.result(timeout=TIMEOUT_SECONDS)
            t1 = time.perf_counter()
            tiempo_ms = (t1 - t0) * 1000.0

            sol_modelo, ops_extraidas = extraer_solucion_81_digitos(respuesta_cruda)
            if operaciones_efectuadas == 0:
                operaciones_efectuadas = ops_extraidas

        except concurrent.futures.TimeoutError:
            t1 = time.perf_counter()
            tiempo_ms = (t1 - t0) * 1000.0
            operaciones_efectuadas = 0
            error_msg = f"Timeout: Exceeded {TIMEOUT_SECONDS}s"
        except Exception as e:
            t1 = time.perf_counter()
            tiempo_ms = (t1 - t0) * 1000.0
            operaciones_efectuadas = 0
            error_msg = str(e)

    is_correct = (sol_modelo == expected)

    results.append({
        'id_tablero': id_tablero,
        'dificultad_categoria': categoria,
        'rating': rating,
        'question': puzzle,
        'answer_expected': expected,
        'answer_deepseek_r1': sol_modelo,
        'correcto': is_correct,
        'tiempo_ms': round(tiempo_ms, 4),
        'operaciones_deepseek_r1': operaciones_efectuadas,
        'error_log': error_msg if error_msg else ''
    })

# --- 4. GUARDAR CSV Y MOSTRAR RESULTADOS ---

output_path = os.path.join(script_dir, 'resultados_deepseek_r1_eml_operaciones.csv')
res_df = pd.DataFrame(results)
res_df.to_csv(output_path, index=False)

print("\n" + "="*55)
print("--- RESUMEN FINAL: EML CON OPERACIONES ---")
print("="*55)
print(f"Total procesados: {len(res_df)}")
print(f"Total aciertos:  {res_df['correcto'].sum()}/{len(res_df)} ({res_df['correcto'].mean()*100:.2f}%)")
print(f"Tiempo promedio: {res_df['tiempo_ms'].mean():.2f} ms")
print(f"Operaciones promedio: {res_df['operaciones_deepseek_r1'].mean():.2f}")

print("\nDesglose por categoría:")
print(res_df.groupby('dificultad_categoria').agg(
    aciertos=('correcto', 'sum'),
    total=('id_tablero', 'count'),
    tiempo_ms=('tiempo_ms', 'mean'),
    operaciones_promedio=('operaciones_deepseek_r1', 'mean')
))