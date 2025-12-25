# AgenteInformeFIME (Demo IBEX 35)

Demo didactica de un agente hibrido (LLM + reglas deterministas) para analizar el IBEX 35
con metricas financieras reproducibles y un informe ejecutivo auditable.

La idea es que puedas ver, de principio a fin, que parte es calculo controlado (formulas y
reglas) y que parte es texto generado por LLM. Las salidas quedan guardadas para poder
replicar el resultado meses despues.

## Que hace

- Lee un Excel con precios historicos (columna `Date` + tickers en columnas).
- Calcula metricas financieras deterministas: rentabilidad, volatilidad anualizada y max drawdown.
- Aplica scoring y hard stops con reglas fijas y ranking estable.
- Enriquece con sectores (archivo local controlado).
- Genera un resumen LLM en tres secciones (sin datos externos, temperatura 0).
- Produce graficas y un informe final (Markdown + PDF) con los resultados.

## Flujo paso a paso (lo que veras en la app)

1) Carga y validacion del Excel (determinista).
2) Calculo de metricas (determinista).
3) Scoring + hard stops (determinista).
4) Flags de calidad (determinista).
5) Ranking final (determinista).
6) Sectorizacion desde archivo local (controlado).
7) Grafica top 5.
8) Grafica bottom 5.
9) Analisis general con LLM.
10) Comparativa por sectores con LLM.
11) Sugerencia de cartera con LLM.
12) Informe unificado.
13) Grafica de la cartera propuesta.

## Entrada requerida

- Excel de precios con:
  - Columna `Date` (fechas).
  - Una columna por ticker (precios).
- Archivo de sectores (se usa por defecto):
  - `data/ibex35_ticker_sector_bmex.xlsx`

## Salida generada (por ejecucion)

Cada corrida crea una carpeta en `outputs/<timestamp>/` con:
- Copia del Excel de entrada.
- Copia del archivo de sectores usado (si existe).
- `ibex35_metrics_scoring_2025.xlsx` con metricas, score y ranking.
- `informe.md` con el texto final.
- `ibex35_summary.pdf` con el informe y tablas.
- Graficas PNG:
  - `grafica_top5.png`
  - `grafica_bottom5.png`
  - `grafica_cartera.png`

La carpeta `outputs/` se versiona en el repo para conservar resultados y poder
comparar ejecuciones a lo largo del tiempo.

## Reproducibilidad y trazabilidad

- Metricas, scoring, ranking y graficas son 100% deterministas.
- El LLM solo redacta texto a partir de resultados internos.
- Se usa temperatura 0 y no se consulta informacion externa.
- Todos los insumos y salidas quedan versionados por timestamp.

## Requisitos

- Python 3.11+
- Ollama con un modelo local (por defecto `llama3.2:3b`)

## Instalacion

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install matplotlib reportlab
```

## Uso

```powershell
.\.venv\Scripts\python -m streamlit run app\streamlit_app.py
```

Dentro de la app puedes:
- Subir tu Excel de precios.
- Elegir el modelo de Ollama.
- Ajustar el timeout.
- Ejecutar el pipeline y descargar Excel/PDF.

## Estructura del repo (archivos clave)

- `app/streamlit_app.py`: interfaz Streamlit paso a paso.
- `src/`: logica de calculo, scoring, LLM y reporting.
  - `pipeline.py`: pipeline determinista.
  - `metrics.py`: metricas financieras.
  - `scoring.py`: scoring determinista.
  - `io_excel.py`: lectura y exportacion Excel.
  - `sectors.py`: carga de sectores.
  - `llm_summary.py`: prompts y llamadas a Ollama.
  - `reporting.py`: graficas y generacion de PDF.
- `data/`: datos de entrada (precios y sectores).
- `outputs/`: resultados por ejecucion (timestamp).

## Notas utiles

- Si el modelo de Ollama no esta disponible, el pipeline fallara en los pasos LLM.
- Si todos los sectores salen iguales, revisa el Excel de sectores.
- Puedes abrir el `informe.md` para comparar texto antes de generar el PDF.
