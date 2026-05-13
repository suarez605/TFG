Idea de Alto nivel: un pipeline experimental que lanza una batería de prompts con falacias a varios LLMs, guarda las respuestas y, opcionalmente, usa un LLM fuerte como “juez” de las falacias generadas.

1. Objetivo del trabajo (formulado fino)
En términos “de paper”, tu objetivo podría quedar así (para que luego lo copies/adaptes):

Objetivo general:
Estudiar hasta qué punto distintos LLMs son capaces de (a) generar de forma controlada argumentos falaces según una taxonomía reducida, (b) admitir o no dichos argumentos cuando se les presentan, e (c) identificar y criticar razonamientos falaces en textos de entrada.

Objetivos específicos:

Diseñar una batería de prompts que induzca la generación de textos falaces por tipo de falacia.

Construir un corpus sintético etiquetado con el tipo de falacia que se espera (ground truth de intención) y las salidas de varios LLMs.

Evaluar la consistencia de la generación (si el modelo realmente produce la falacia pedida).

Evaluar la respuesta de los LLMs ante textos falaces: si los aceptan, los corrigen, los critican, etc.

Explorar el uso de un LLM fuerte como juez (LLM‑as‑a‑Judge) para etiquetar automáticamente las falacias generadas (tipo de falacia, presencia/ausencia, calidad de la crítica).

Esto encaja perfecto con la descripción que te dio y con el reparto de tareas que tienes asignado.

2. Qué desarrollar a nivel de código
Un script en Python que use Ollama (u otra API) para lanzar prompts a varios modelos y guardar resultados es el núcleo mínimo. Pero conviene que lo organices como pipeline claro y reutilizable, no como un script monolítico.

2.1. Componentes mínimos del pipeline
Definición de la batería de falacias y prompts

Un fichero (por ejemplo JSON/CSV/YAML) con entradas del estilo:

id de ejemplo

tipo_falacia (de tu taxonomía reducida)

prompt_generacion (para que el modelo genere un argumento falaz)

prompt_evaluacion (para que el modelo responda ante un argumento falaz)

Esto te permite separar “diseño experimental” de “código”.

Módulo de ejecución de modelos (runner)

En Python, una función del estilo run_model(model_name, prompt) -> respuesta.

Implementado usando la API de Ollama para modelos locales, y si quieres también llamadas HTTP a APIs externas (OpenAI, etc.).

Soporte para varios modelos: una lista de nombres de modelo y un bucle que los recorra.

Script principal de evaluación

Carga la colección de prompts (tu “colección de falacias”).

Para cada prompt y cada modelo:

Lanza la generación (modo “generar falacia”).

Lanza la respuesta (modo “evaluar argumento falaz”), si procede.

Guarda todo en un formato estructurado (por ejemplo, filas de CSV o JSONL) con campos como:

id_ejemplo, modelo, tipo_falacia, prompt_generacion, texto_generado, prompt_evaluacion, respuesta_modelo, timestamp, etc.

Este fichero será tu corpus sintético bruto.

Módulo de evaluación automática básica

Estadísticas simples:

Por modelo y tipo de falacia: cuántos ejemplos, longitud media, etc.

Por modelo: cuántas veces parece “aceptar” la falacia (por ejemplo, si no la cuestiona, si la refuerza).

Estas heurísticas las puedes codificar con reglas simples (regex, palabras clave como “esto es falaz”, “argumento inválido”, etc.) para un primer análisis.

2.2. LLM fuerte como juez (fase extra si hay tiempo)
La idea que te comentó tu tutor es muy buena y encaja con el patrón LLM‑as‑Judge que se usa en evaluación moderna de LLMs.

Podrías añadir:

Módulo “juez” con LLM fuerte

Toma como entrada las respuestas/argumentos generados por los otros modelos.

Usa un LLM potente (quizá remoto, tipo GPT‑4/Claude) con prompts del estilo:

“Lee este argumento y di: (a) si contiene una falacia, (b) de qué tipo según esta taxonomía, (c) por qué.”

Devuelve una anotación estructurada (por ejemplo en JSON) con:

contiene_falacia (sí/no)

tipo_falacia_detectada (o varios)

juicio_sobre_la_respuesta: la respuesta del modelo crítico es correcta, superficial, errónea, etc.

Guardas esto como nuevas columnas en tu corpus.

Script de análisis de resultados del juez

Cálculo de métricas tipo:

Por modelo: proporción de textos donde el juez detecta la falacia esperada.

Por modelo: capacidad de detectar y criticar argumentos falaces (según el juez).

Comparaciones entre modelos y entre tipos de falacia.

3. Nivel de complejidad razonable para un TFG
Para un TFG de 25 páginas no es necesario montar un framework gigantesco; lo importante es que tu código:

Sea limpio y reproducible (ficheros de configuración, scripts claros).

Permita repetir el experimento cambiando la lista de modelos o la batería de prompts.

Genere un corpus reutilizable (archivo bien documentado en el anexo o repositorio) con todos los campos necesarios para que otra persona pueda replicar tus análisis.

Un plan razonable podría ser:

Primera fase (imprescindible):

Script Python + Ollama que:

Lee una batería de prompts con falacias.

Lanza esos prompts a 2–3 modelos.

Guarda resultados en JSON/CSV.

Segunda fase (muy recomendable):

Scripts de análisis (también en Python, quizá con pandas) que:

Generan tablas y gráficos para la sección de resultados.

Tercera fase (si da tiempo, extra interesante):

Pipeline “juez” con un LLM fuerte que anota las salidas de otros modelos.

Comparación de tus juicios manuales con los del LLM juez en una muestra pequeña, para valorar su fiabilidad.

Si quieres, en el siguiente mensaje puedo proponerte una estructura concreta de paquetes/ficheros Python (por ejemplo config/, src/prompts.py, src/run_models.py, src/judge.py, notebooks/analysis.ipynb) y un mini ejemplo de cómo sería un JSON de configuración de falacias.