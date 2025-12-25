# AgenteInformeFIME

Demo didactica de un agente hibrido (LLM + reglas deterministas) para analizar el IBEX 35
con metricas financieras reproducibles y un informe ejecutivo auditable.

## Objetivo

- Mostrar un flujo "input -> ejecutar -> output" para una clase de modelos de razonamiento.
- Separar calculo determinista (metricas, scoring, ranking) del texto generado por LLM.
- Generar salidas trazables: Excel, informe PDF y graficas.

## Flujo general

1) Carga de precios (Excel con columna Date y tickers).
2) Calculo de metricas: rentabilidad, volatilidad anualizada y max drawdown.
3) Scoring determinista con hard stops y ranking.
4) Enriquecimiento con sectores (archivo local).
5) Analisis LLM en tres secciones y consolidacion del informe.
6) Graficas deterministas (top 5, bottom 5, cartera) e informe PDF final.

## Estructura

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

## Requisitos

- Python 3.11+
- Ollama con modelo local (por defecto `llama3.2:3b`)

## Instalacion

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install matplotlib reportlab
```

## Uso

```powershell
.\.venv\Scripts\python -m streamlit run app\streamlit_app.py
```

## Notas de trazabilidad

Cada ejecucion crea una carpeta en `outputs/<timestamp>/` con:
- copias de los inputs usados,
- Excel de resultados,
- informe markdown y PDF,
- graficas PNG.
