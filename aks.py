import math

def aks_es_primo(n: int) -> bool:
    """
    Determina si n es un número primo utilizando el algoritmo determinista AKS.
    Retorna True si es primo, False si es compuesto.
    """
    if n <= 1:
        return False
    if n <= 3:
        return True

    # -------------------------------------------------------------------------
    # Paso 1: Verificar si n es una potencia perfecta (a^b para a > 1, b > 1)
    # -------------------------------------------------------------------------
    # Si n = a^b, entonces b <= log2(n)
    max_b = math.floor(math.log2(n))
    for b in range(2, max_b + 1):
        # Raíz b-ésima entera aproximada
        a = round(n ** (1 / b))
        if a ** b == n:
            return False

    # -------------------------------------------------------------------------
    # Paso 2: Encontrar el menor orden r tal que ord_r(n) > log2(n)^2
    # -------------------------------------------------------------------------
    log2_n = math.log2(n)
    limite_r = math.ceil(log2_n ** 2)
    
    r = 2
    while True:
        # Calcular el orden de n modulo r: el menor k tal que n^k ≡ 1 (mod r)
        if math.gcd(n, r) == 1:
            k = 1
            mod_val = n % r
            temp = mod_val
            
            while temp != 1 and temp != 0:
                temp = (temp * mod_val) % r
                k += 1
                
            if k > limite_r:
                break
        r += 1

    # -------------------------------------------------------------------------
    # Paso 3: Si 1 < gcd(a, n) < n para algún a <= r, entonces n es compuesto
    # -------------------------------------------------------------------------
    for a in range(2, r + 1):
        g = math.gcd(a, n)
        if 1 < g < n:
            return False
        elif g == n:
            # Si n <= r y pasó la prueba del MCD, entonces es primo
            return True

    # -------------------------------------------------------------------------
    # Paso 4: Si n <= r, entonces n es primo
    # -------------------------------------------------------------------------
    if n <= r:
        return True

    # -------------------------------------------------------------------------
    # Paso 5: Congruencia polinomial: (x + a)^n ≡ x^n + a (mod x^r - 1, n)
    # -------------------------------------------------------------------------
    # Se evalúa para 1 <= a <= floor(sqrt(phi(r)) * log2(n))
    # Para simplicidad usaremos la cota superior estándar: sqrt(r) * log2(n)
    limite_a = math.floor(math.sqrt(r) * log2_n)

    # Multiplicación de polinomios en el anillo Z_n[x] / (x^r - 1)
    def mult_poly(p1: list[int], p2: list[int], r: int, mod: int) -> list[int]:
        res = [0] * r
        for i, c1 in enumerate(p1):
            if c1 == 0:
                continue
            for j, c2 in enumerate(p2):
                if c2 == 0:
                    continue
                # (x^i * x^j) mod (x^r - 1) reduce el exponente a (i + j) % r
                idx = (i + j) % r
                res[idx] = (res[idx] + c1 * c2) % mod
        return res

    # Exponenciación binaria de polinomios: p(x)^exp mod (x^r - 1, mod)
    def power_poly(base: list[int], exp: int, r: int, mod: int) -> list[int]:
        res = [0] * r
        res[0] = 1  # Polinomio identidad: 1
        
        curr = base[:]
        while exp > 0:
            if exp % 2 == 1:
                res = mult_poly(res, curr, r, mod)
            curr = mult_poly(curr, curr, r, mod)
            exp //= 2
        return res

    for a in range(1, limite_a + 1):
        # Representamos (x + a) como un polinomio de grado r-1
        poly_base = [0] * r
        poly_base[0] = a % n
        poly_base[1] = 1  # 1*x + a
        
        # Lado izquierdo: (x + a)^n mod (x^r - 1, n)
        lhs = power_poly(poly_base, n, r, n)
        
        # Lado derecho: (x^n + a) mod (x^r - 1, n)
        rhs = [0] * r
        rhs[0] = a % n
        rhs[n % r] = (rhs[n % r] + 1) % n

        if lhs != rhs:
            return False

    # -------------------------------------------------------------------------
    # Paso 6: Si supera todas las pruebas, n es primo
    # -------------------------------------------------------------------------
    return True


# --- Ejemplo de Uso y Verificación ---
if __name__ == "__main__":
    numeros_prueba = [2, 3, 4, 13, 17, 25, 31, 561, 1009]
    
    print("--- Verificación con Algoritmo AKS ---")
    for num in numeros_prueba:
        es_primo = aks_es_primo(num)
        print(f"¿El número {num:4d} es primo? -> {es_primo}")