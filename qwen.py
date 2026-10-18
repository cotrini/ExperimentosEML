import re
import time
import ollama

# --- 1. DATOS DEL SUDOKU DE PRUEBA ---
SUDOKU_INPUT = "...4..91.....5.2.887..39.4618...347...672..9......5...4.1.96..372..14....3...8.2."
MODELO_OLLAMA = "qwen2.5:3b"  # Puedes cambiarlo por "deepseek-r1:1.5b" o "llama3.2:3b"

# --- 2. FUNCIONES DE APOYO Y VERIFICACIÓN EN PYTHON ---

def convertir_a_coordenadas_explicitas(cadena_81):
    """
    Transforma la cadena de 81 caracteres en un texto con coordenadas explícitas
    (R1..R9, C1..C9) para evitar confusiones de tokenización en el LLM.
    """
    filas = [cadena_81[i * 9:(i + 1) * 9] for i in range(9)]
    lineas_texto = []
    
    for r_idx, fila in enumerate(filas):
        celdas = []
        for c_idx, ch in enumerate(fila):
            val_str = ch if ch in '123456789' else '_'
            celdas.append(f"C{c_idx + 1}={val_str}")
        lineas_texto.append(f"Row R{r_idx + 1}: " + " | ".join(celdas))
        
    return "\n".join(lineas_texto)

def validar_solucion_sudoku(cadena_81):
    """Verifica si una cadena de 81 dígitos cumple estrictamente las reglas del Sudoku."""
    if len(cadena_81) != 81 or not cadena_81.isdigit() or '0' in cadena_81:
        return False, "La respuesta no contiene exactamente 81 dígitos entre 1 y 9."
    
    grid = [[int(cadena_81[r * 9 + c]) for c in range(9)] for r in range(9)]
    
    # 1. Validar Filas y Columnas
    for i in range(9):
        if len(set(grid[i])) != 9:
            return False, f"Conflicto de duplicado en la Fila R{i+1}."
        col = [grid[r][i] for r in range(9)]
        if len(set(col)) != 9:
            return False, f"Conflicto de duplicado en la Columna C{i+1}."
            
    # 2. Validar Cajas de 3x3
    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            caja = [grid[r][c] for r in range(br, br + 3) for c in range(bc, bc + 3)]
            if len(set(caja)) != 9:
                return False, f"Conflicto de duplicado en la caja 3x3 ({br+1},{bc+1})."
                
    return True, "¡Sudoku 100% válido y resuelto correctamente!"

# --- 3. CONSTRUCCIÓN DEL PROMPT OPTIMIZADO ---

tablero_coordenadas = convertir_a_coordenadas_explicitas(SUDOKU_INPUT)

PROMPT_SUDOKU = f"""You are a deterministic logic solver.
I will give you a 9x9 Sudoku board with explicit Row (R1 to R9) and Column (C1 to C9) coordinates.
Underscores (_) represent empty cells to be filled with digits 1 to 9.

Board State:
{tablero_coordenadas}

Task:
1. Internally solve the board using standard Sudoku rules (no repeated digits per row, column, or 3x3 box).
2. Output ONLY the completed 81-digit solved string continuously on a single line (e.g. 563482...).
3. Do NOT include any explanations, code blocks, or spaces in your final response.
"""

# --- 4. EJECUCIÓN CON OLLAMA Y EVALUACIÓN DE RESULTADOS ---

print(f"Enviando Sudoku a Ollama ({MODELO_OLLAMA})...")
print("-" * 50)

t0 = time.perf_counter()

# Llamada directa sin plantilla de chat para máxima precisión
respuesta = ollama.generate(
    model=MODELO_OLLAMA,
    prompt=PROMPT_SUDOKU,
    raw=True,  # Pasa el prompt directamente a la red sin decoradores de chat
    options={
        'temperature': 0.0,   # Determinismo total
        'num_predict': 100,   # Tokens suficientes para los 81 dígitos
        'top_p': 0.1
    }
)

t1 = time.perf_counter()
tiempo_ms = (t1 - t0) * 1000.0

texto_raw = respuesta['response'].strip()

# Extracción mediante expresión regular de la cadena de 81 dígitos
match = re.search(r'[1-9]{81}', texto_raw)
solucion_extraida = match.group(0) if match else re.sub(r'[^1-9]', '', texto_raw)

# Verificación con el motor lógico de Python
es_correcto, mensaje_validacion = validar_solucion_sudoku(solucion_extraida)

print(f"Respuesta cruda de Ollama: {texto_raw}")
print(f"Cadena de 81 dígitos extraída: {solucion_extraida}")
print(f"Tiempo de inferencia: {tiempo_ms:.2f} ms")
print(f"Resultado de Validación: {mensaje_validacion}")
print("-" * 50)