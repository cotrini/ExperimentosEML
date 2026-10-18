import os
import time
import math
import pandas as pd

# --- 1. OPERADOR Y BARRERA DE ENERGÍA EML ---

def eml(x, y):
    """
    Operador Exponencial Menos Logaritmo: eml(x, y) = e^x - ln(y)
    Si y <= 0 (conflicto de dígitos), ln(0) -> -inf, provocando eml -> +inf.
    """
    if y <= 0:
        return float('inf')  # Divergencia: Barrera de energía infinita
    return math.exp(x) - math.log(y)

def calcular_energia_eml_paso(grid_81, r, c, v):
    """
    Evalúa la barrera de energía EML para la propuesta del dígito 'v'
    en la celda (r, c) sobre el estado PARCIAL del tablero en tiempo de ejecución.
    """
    x_base = 0.0
    energia_total = 0.0
    
    # 1. Evaluar interacción EML en Fila y Columna
    for k in range(9):
        # Mismo entorno de Fila
        if k != c and grid_81[r * 9 + k] != 0:
            y = abs(v - grid_81[r * 9 + k])
            e = eml(x_base, y)
            if e == float('inf'):
                return float('inf')  # Colapso instantáneo por conflicto
            energia_total += e

        # Mismo entorno de Columna
        if k != r and grid_81[k * 9 + c] != 0:
            y = abs(v - grid_81[k * 9 + c])
            e = eml(x_base, y)
            if e == float('inf'):
                return float('inf')  # Colapso instantáneo por conflicto
            energia_total += e

    # 2. Evaluar interacción EML en Caja 3x3
    box_r, box_c = 3 * (r // 3), 3 * (c // 3)
    for br in range(box_r, box_r + 3):
        for bc in range(box_c, box_c + 3):
            if (br != r or bc != c) and grid_81[br * 9 + bc] != 0:
                y = abs(v - grid_81[br * 9 + bc])
                e = eml(x_base, y)
                if e == float('inf'):
                    return float('inf')  # Colapso instantáneo por conflicto
                energia_total += e

    return energia_total

# --- 2. ESTRUCTURA DE KNUTH DANCING LINKS (DLX HÍBRIDO CON EML) ---

class Node:
    def __init__(self, col=None, row_id=None):
        self.left = self
        self.right = self
        self.up = self
        self.down = self
        self.col = col
        self.row_id = row_id

class ColumnNode(Node):
    def __init__(self, name):
        super().__init__(col=self)
        self.name = name
        self.size = 0

class DLX_EML:
    def __init__(self, num_cols):
        self.header = ColumnNode("header")
        self.cols = []
        prev = self.header
        for i in range(num_cols):
            c = ColumnNode(i)
            self.cols.append(c)
            c.left = prev
            c.right = self.header
            prev.right = c
            self.header.left = c
            prev = c
        self.solution = []
        self.ops = 0

    def add_row(self, row_id, col_indices):
        first = None
        for c_idx in col_indices:
            c = self.cols[c_idx]
            node = Node(col=c, row_id=row_id)
            node.up = c.up
            node.down = c
            c.up.down = node
            c.up = node
            c.size += 1
            if first is None:
                first = node
            else:
                node.left = first.left
                node.right = first
                first.left.right = node
                first.left = node

    def cover(self, c):
        c.right.left = c.left
        c.left.right = c.right
        i = c.down
        while i != c:
            j = i.right
            while j != i:
                j.down.up = j.up
                j.up.down = j.down
                j.col.size -= 1
                j = j.right
            i = i.down

    def uncover(self, c):
        i = c.up
        while i != c:
            j = i.left
            while j != i:
                j.col.size += 1
                j.down.up = j
                j.up.down = j
                j = j.left
            i = i.up
        c.right.left = c
        c.left.right = c

    def search(self, grid_parcial):
        self.ops += 1
        if self.header.right == self.header:
            return True

        # Heurística MRV (Minimum Remaining Values)
        c = self.header.right
        min_size = c.size
        curr = c.right
        while curr != self.header:
            if curr.size < min_size:
                c = curr
                min_size = curr.size
            curr = curr.right

        if c.size == 0:
            return False

        self.cover(c)
        r = c.down
        while r != c:
            row_r, col_c, val_v = r.row_id
            
            # CHECK DE BARRERA DE ENERGÍA EML EN TIEMPO DE EXPLORACIÓN
            energia = calcular_energia_eml_paso(grid_parcial, row_r, col_c, val_v)
            
            # Solo si la energía se mantiene acotada (sin conflicto) exploramos la rama
            if energia < float('inf'):
                # Actualizar el estado del tablero parcial
                grid_parcial[row_r * 9 + col_c] = val_v
                self.solution.append(r)
                
                j = r.right
                while j != r:
                    self.cover(j.col)
                    j = j.right

                # Búsqueda recursiva en el siguiente estado
                if self.search(grid_parcial):
                    return True

                # Deshacer estado parcial (Backtracking)
                node_r = self.solution.pop()
                grid_parcial[row_r * 9 + col_c] = 0
                
                j = node_r.left
                while j != node_r:
                    self.uncover(j.col)
                    j = j.left

            r = r.down

        self.uncover(c)
        return False

def solve_sudoku_knuth_eml(grid_str):
    dlx = DLX_EML(324)
    grid_parcial = [int(ch) if ch in '123456789' else 0 for ch in grid_str]
    
    for r in range(9):
        for c in range(9):
            box = 3 * (r // 3) + (c // 3)
            val_given = grid_parcial[r * 9 + c]
            
            for v in range(1, 10):
                if val_given != 0 and val_given != v:
                    continue
                row_id = (r, c, v)
                c1 = r * 9 + c
                c2 = 81 + r * 9 + (v - 1)
                c3 = 162 + c * 9 + (v - 1)
                c4 = 243 + box * 9 + (v - 1)
                dlx.add_row(row_id, [c1, c2, c3, c4])

    t0 = time.perf_counter()
    solved = dlx.search(grid_parcial)
    t1 = time.perf_counter()
    
    elapsed_ms = (t1 - t0) * 1000.0
    
    if solved:
        res_grid = [0] * 81
        for node in dlx.solution:
            r, c, v = node.row_id
            res_grid[r * 9 + c] = str(v)
        for i in range(81):
            if res_grid[i] == 0:
                res_grid[i] = str(grid_parcial[i])
        sol_str = "".join(res_grid)
    else:
        sol_str = ""
        
    return sol_str, elapsed_ms, dlx.ops

# --- 3. PROCESAMIENTO Y GENERACIÓN DE CSV ---

script_dir = os.path.dirname(os.path.abspath(__file__))
posibles_rutas = [
    os.path.join(script_dir, "muestra_sudoku_385.csv"),
    os.path.join(script_dir, "Sudokus Test", "muestra_sudoku_385.csv")
]

ruta_csv = None
for r in posibles_rutas:
    if os.path.exists(r):
        ruta_csv = r
        break

if not ruta_csv:
    raise FileNotFoundError("No se encontró el archivo 'muestra_sudoku_385.csv'.")

df = pd.read_csv(ruta_csv, dtype=str)
results = []

for idx, row in df.iterrows():
    puzzle = str(row['question']).strip()
    expected = str(row['answer']).strip()
    
    sol, t_ms, ops = solve_sudoku_knuth_eml(puzzle)
    is_correct = (sol == expected)
    
    results.append({
        'id_tablero': row.get('id_tablero', idx + 1),
        'dificultad_categoria': row.get('dificultad_categoria', 'N/A'),
        'rating': row.get('rating', '0'),
        'question': puzzle,
        'answer_expected': expected,
        'answer_eml': sol,
        'correcto': is_correct,
        'tiempo_ms': round(t_ms, 4),
        'operaciones': ops
    })

res_df = pd.DataFrame(results)
output_path = os.path.join(script_dir, 'resultados_knuth_eml.csv')
res_df.to_csv(output_path, index=False)

print("--- PROCESAMIENTO CON BARRERA EML FINALIZADO ---")
print(f"Total procesados: {len(res_df)}")
print(f"¿Todos correctos?: {res_df['correcto'].all()} ({res_df['correcto'].sum()}/{len(res_df)})")