import cmath

def eml(x: complex | float, y: complex | float) -> complex:
    """Calcula el operador EML: eml(x, y) = exp(x) - ln(y)"""
    return cmath.exp(x) - cmath.log(y)

# 2\. Función Exponencial: exp(x) = eml(x, 1)
def exp_eml(x: complex | float) -> complex:
    return eml(x, 1)

# 3\. Logaritmo Natural: ln(x) = eml(1, eml(eml(1, x), 1))
def ln_eml(x: complex | float) -> complex:
    return eml(1, eml(eml(1, x), 1))

# 4\. División: x / y = exp(ln(x) - ln(y)) expresada con EML
def div_eml(x: complex | float, y: complex | float) -> complex:
    # Resta de logaritmos e inversión exponencial usando únicamente EML
    log_x = ln_eml(x)
    log_y = ln_eml(y)
    resta_log = log_x - log_y
    return eml(resta_log, 1)

# substraccion
def sub_eml(x: complex | float, y: complex | float) -> complex:
    """Calcula la resta de dos números usando el operador EML: x - y = eml(ln(x), ln(y))"""
    log_x = ln_eml(x)
    log_y = ln_eml(y)
    return eml(log_x, log_y)

#negativo
def neg_eml(x: complex | float) -> complex:
    """Calcula el negativo de un número usando el operador EML: -x = eml(ln(1), ln(x))"""
    return sub_eml(ln_eml(1), ln_eml(x))

def eml_inv(x: complex | float) -> complex:
    """Calcula el inverso multiplicativo de un número usando el operador EML: 1/x = eml(ln(1), ln(x))"""
    return sub_eml(ln_eml(1), ln_eml(x))