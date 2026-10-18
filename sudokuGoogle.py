import os
import time
import pandas as pd
from google import genai

# Configura tu clave de API (obtenida gratis en https://aistudio.google.com/)
os.environ["GEMINI_API_KEY"] = ""

client = genai.Client()

PROMPT_SUDOKU = """You are a Sudoku solver. 
Solve this 81-character Sudoku string where dots (.) are empty cells:
...4..91.....5.2.887..39.4618...347...672..9......5...4.1.96..372..14....3...8.2.

Respond ONLY with the final 81-digit solved string."""

response = client.models.generate_content(
    model='gemini-flash-latest',
    contents=PROMPT_SUDOKU,
)

print("Respuesta de Gemini API:")
print(response.text)