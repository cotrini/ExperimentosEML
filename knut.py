# knut algoritm to solve provided sudokus, test the amount of operations, time to solve each sudoku, readed from csv file
# compare the result with provided solution, and write the result to a csv file

import time
from pathlib import Path

import pandas as pd

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

class DLX:
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

    def search(self):
        self.ops += 1
        if self.header.right == self.header:
            return True

        # Heurística MRV: Seleccionar la columna con menor número de elementos (size)
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
            self.solution.append(r)
            j = r.right
            while j != r:
                self.cover(j.col)
                j = j.right

            if self.search():
                return True

            node_r = self.solution.pop()
            j = node_r.left
            while j != node_r:
                self.uncover(j.col)
                j = j.left
            r = r.down

        self.uncover(c)
        return False

def solve_sudoku_dlx(grid_str):
    if len(grid_str) != 81:
        raise ValueError("A Sudoku puzzle must contain exactly 81 characters.")
    if any(char not in ".0123456789" for char in grid_str):
        raise ValueError("A Sudoku puzzle may contain only digits, '.' or '0'.")

    # Matriz de cobertura exacta de 324 columnas
    dlx = DLX(324)
    
    for r in range(9):
        for c in range(9):
            box = 3 * (r // 3) + (c // 3)
            val_given = int(grid_str[r * 9 + c]) if grid_str[r * 9 + c] in '123456789' else 0
            
            for v in range(1, 10):
                if val_given != 0 and val_given != v:
                    continue
                row_id = (r, c, v)
                c1 = r * 9 + c                        # Restricción 1: Celda ocupada (0..80)
                c2 = 81 + r * 9 + (v - 1)             # Restricción 2: Fila-Valor (81..161)
                c3 = 162 + c * 9 + (v - 1)            # Restricción 3: Columna-Valor (162..242)
                c4 = 243 + box * 9 + (v - 1)          # Restricción 4: Caja-Valor (243..323)
                dlx.add_row(row_id, [c1, c2, c3, c4])

    t0 = time.perf_counter()
    solved = dlx.search()
    t1 = time.perf_counter()
    
    elapsed_ms = (t1 - t0) * 1000.0
    
    if solved:
        res_grid = [0] * 81
        for node in dlx.solution:
            r, c, v = node.row_id
            res_grid[r * 9 + c] = str(v)
        sol_str = "".join(res_grid)
    else:
        sol_str = None
        
    return sol_str, elapsed_ms, dlx.ops


def main():
    base_dir = Path(__file__).resolve().parent
    input_path = base_dir / "Sudokus Test" / "muestra_sudoku_385.csv"
    output_path = base_dir / "resultados_knuth_dlx.csv"
    df = pd.read_csv(input_path, dtype={"question": str, "answer": str})
    results = []

    for idx, row in df.iterrows():
        puzzle = row["question"]
        expected = row["answer"]

        sol, t_ms, ops = solve_sudoku_dlx(puzzle)
        is_correct = sol == expected

        results.append({
            "id_tablero": row.get("id_tablero", idx + 1),
            "dificultad_categoria": row.get("dificultad_categoria", "N/A"),
            "rating": row.get("rating", 0),
            "question": puzzle,
            "answer_expected": expected,
            "answer_dlx": sol,
            "correcto": is_correct,
            "tiempo_ms": round(t_ms, 4),
            "operaciones": ops
        })

    pd.DataFrame(results).to_csv(output_path, index=False)


if __name__ == "__main__":
    main()