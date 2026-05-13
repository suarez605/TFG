# Síntesis de dos trabajos sobre detección de falacias y evaluación de LLMs (MAFALDA y LOGIC)

## 1. Visión general

Este informe resume y compara dos trabajos recientes muy relevantes para un TFG sobre verificación de falacias en modelos de lenguaje:

- **Helwe et al. 2024 – MAFALDA: A Benchmark and Comprehensive Study of Fallacy Detection and Classification**.
- **Jin et al. 2022 – Logical Fallacy Detection (LOGIC y LOGICCLIMATE)**.

Ambos trabajos formulan tareas de detección/clasificación de falacias a nivel de texto, construyen benchmarks específicos y evalúan modelos de lenguaje grandes, pero se diferencian en tipo de falacias, diseño del dataset, forma de abordar la subjetividad y tipo de modelos evaluados.


## 2. Paper 1: MAFALDA (Helwe et al., 2024)

### 2.1 Objetivos y motivación

MAFALDA persigue unificar el paisaje fragmentado de datasets de falacias y proporcionar un benchmark sólido para estudiar la capacidad de humanos y LLMs de **detectar y clasificar falacias en textos reales**.
Los autores se centran especialmente en: (i) resolver la falta de consenso en taxonomías, (ii) tratar explícitamente la subjetividad de la anotación de falacias y (iii) medir qué tan lejos están los LLMs del rendimiento humano en este problema.


### 2.2 Taxonomía de falacias

MAFALDA propone una **taxonomía jerárquica en tres niveles** que consolida y refina las colecciones de falacias usadas en trabajos previos.
Esta taxonomía parte de varias fuentes clásicas y modernas de falacias, pero elimina categorías excesivamente amplias o raras, y agrupa las restantes siguiendo la tradición aristotélica (Pathos/Ethos/Logos).

La estructura es:
- **Nivel 0**: clasificación binaria (texto con falacia / sin falacia).
- **Nivel 1**: tres grandes grupos:
  - *Appeal to Emotion* (Pathos)
  - *Fallacy of Credibility* (Ethos)
  - *Fallacy of Logic* (Logos: lógica, relevancia, evidencia).
- **Nivel 2**: falacias finas como *Appeal to Fear*, *Appeal to Ridicule*, *Hasty Generalization*, *False Causality*, *False Dilemma*, *Ad Populum*, *Abusive Ad Hominem*, *Guilt by Association*, *Tu Quoque*, *Circular Reasoning*, *Straw Man*, *Slippery Slope*, etc.

Cada falacia viene con una definición informal y un esquema formal tipo plantilla (por ejemplo, para *Appeal to Ridicule*: E1 sostiene P; E2 presenta una versión ridiculizada P′; se concluye ¬P), lo que es muy útil si se quieren diseñar prompts explicativos o sistemas de explicación automática en el TFG.


### 2.3 Esquema de anotación disyuntivo y métricas

La principal aportación metodológica es un **esquema de anotación disyuntivo** que abraza la subjetividad: un mismo span puede estar asociado a un conjunto de etiquetas alternativas igualmente válidas.

Puntos clave:
- La unidad de anotación es un **span de oraciones contiguas** que contiene premisas y conclusión de la falacia; se permiten pronombres para reducir el tamaño del span.
- El **gold standard** asocia a cada span un conjunto no vacío de etiquetas de falacia; si se incluye un marcador especial ⊥, la anotación para ese span se considera opcional.
- Esto permite que, por ejemplo, un caso ambiguo se etiquete como {False Causality, Causal Oversimplification} sin forzar un consenso artificial entre anotadores.

Para evaluar modelos, los autores definen métricas de **precisión y recall por solapamiento de spans** que se adaptan a estas alternativas:
- Se calcula un score de comparación C que combina el grado de solapamiento entre spans predicho y gold, normalizado por la longitud, y comprueba si la etiqueta predicha está en el conjunto de etiquetas válidas.
- La precisión promedia, para cada predicción, el mejor match posible en el gold; el recall, a la inversa, promedia para cada entrada del gold el mejor match en las predicciones, ignorando spans marcados sólo con ⊥.
- El F1 se define como la media armónica estándar, reduciéndose a las métricas clásicas cuando no hay alternativas ni spans multi-oración.

Este marco es muy interesante para tu TFG porque muestra cómo definir métricas que no penalicen injustamente la **ambigüedad razonable** en anotación de falacias.


### 2.4 Dataset: construcción y estadísticas

MAFALDA fusiona cuatro corpus públicos de falacias y propaganda para obtener un conjunto heterogéneo de textos en inglés:
- Reddit (Sahai et al., 2021),
- noticias (Martino et al., 2019),
- ejemplos lógicos y clima (Jin et al., 2022),
- debates políticos estadounidenses (Goffredo et al., 2022).

Tras limpieza y normalización, el corpus tiene **9.745 textos**; sobre una muestra estratificada de **200 textos** los autores eliminan las etiquetas originales y los **anotan manualmente desde cero** siguiendo su taxonomía y esquema.

Características de la parte anotada:
- 200 textos, 268 spans, de los cuales 203 contienen al menos una falacia.
- 137 textos tienen alguna falacia y 63 resultan no falaciosos.
- Media ≈ 1,34 spans por texto; el 28% de los spans tiene **≥2 etiquetas alternativas**.
- Se observan co-ocurrencias naturales (por ejemplo, *Guilt by Association* a menudo coaparece con *Abusive Ad Hominem*, pues son variantes de ad hominem).

El tamaño hace que el dataset sea más adecuado como **benchmark de evaluación (zero/few-shot)** que para fine-tuning masivo, pero la diversidad de fuentes lo convierte en un buen test de robustez.


### 2.5 Evaluación de LLMs y humanos

MAFALDA se usa exclusivamente para **evaluar modelos en zero-shot**, no para entrenarlos, siguiendo un enfoque bottom‑up: se pide a los modelos que etiqueten oraciones con falacias de Nivel 2 y a partir de ello se derivan etiquetas de Niveles 1 y 0.

Modelos evaluados:
- ChatGPT (GPT‑3.5) y 12 modelos open-source (familias LLaMA2, Vicuna, WizardLM, Mistral, Zephyr, Falcon) con tamaños entre 7B y 13B parámetros.

Resultados (F1 con las nuevas métricas):
- A nivel binario (Nivel 0), GPT‑3.5 llega a **0,627** F1; varios modelos 7B/13B rondan 0,5–0,57.
- A nivel de grandes categorías (Nivel 1) y falacias finas (Nivel 2), el rendimiento baja drásticamente: GPT‑3.5 obtiene **0,201** (Nivel 1) y **0,138** (Nivel 2).
- Un estudio con 4 anotadores humanos en 20 ejemplos muestra que, incluso usando las mismas métricas exigentes, los humanos superan claramente a los modelos: F1 medio humano ≈ 0,749 (Nivel 0), 0,352 (Nivel 1), 0,186 (Nivel 2).

Además, los autores analizan errores y detectan que tanto modelos como humanos tienen especial dificultad con las **falacias de apelación a la emoción**, porque muchos textos expresan emociones sin ser necesariamente falaces; se detectan también problemas en modelos pequeños como Falcon, con tendencia a predecir muchas falacias irrelevantes en un mismo span.


### 2.6 Limitaciones y riesgos

Los autores reconocen varias limitaciones:
- **Tamaño reducido** de la parte anotada (200 textos) debido al alto coste de anotación detallada; el benchmark está pensado para evaluación zero/few-shot, no para entrenar desde cero.
- Posible **sesgo de los anotadores**, aunque se mitigó involucrando perfiles culturales y políticos diversos y usando plantillas formales para justificar cada anotación.
- El dataset contiene contenido sensible (racismo, misoginia, etc.), inevitable al trabajar con propaganda y desinformación.
- Riesgo de **mal uso**: los mismos recursos podrían ayudar a generar argumentos falaces más convincentes; se enfatiza que los modelos entrenados con el dataset no deben utilizarse para etiquetar automáticamente textos como “falaces” sin verificación humana.


## 3. Paper 2: Logical Fallacy Detection (Jin et al., 2022)

### 3.1 Objetivos y enfoque

Jin et al. formulan explícitamente la tarea de **detección de falacias lógicas** y construyen dos datasets: **LOGIC** (falacias generales) y **LOGICCLIMATE** (falacias en afirmaciones sobre cambio climático).
El objetivo es doble: (i) ofrecer un nuevo desafío de razonamiento para modelos de lenguaje y (ii) contribuir a combatir la desinformación, ya que muchos mensajes falaces pueden ser factualmente correctos pero lógicamente defectuosos.

A diferencia de MAFALDA, este trabajo se centra en un conjunto cerrado de **13 tipos de falacias lógicas** y en arquitecturas de clasificación (incluyendo un modelo “structure‑aware”), más que en la unificación taxonómica o la subjetividad de la anotación.


### 3.2 Datasets LOGIC y LOGICCLIMATE

**LOGIC**:
- 2.449 ejemplos de falacias lógicas recopilados de materiales educativos online (quizzes, webs didácticas, etc.).
- Cada ejemplo pertenece a una de 13 clases: *Faulty Generalization*, *Ad Hominem*, *Ad Populum*, *False Causality*, *Circular Claim*, *Appeal to Emotion*, *Fallacy of Relevance*, *Deductive Fallacy*, *Intentional Fallacy*, *Fallacy of Extension*, *False Dilemma*, *Fallacy of Credibility* y *Equivocation*.
- Es un problema de **clasificación multi‑clase (una etiqueta por ejemplo)**; el dataset se divide en train/dev/test (1.849/300/300).

**LOGICCLIMATE**:
- Conjunto de extrapolación con 1.079 ejemplos de falacias en frases extraídas de artículos sobre cambio climático del portal Climate Feedback.
- Anotado por dos hablantes nativos y revisado, permite etiquetas múltiples por ejemplo (multi‑label) con las mismas 13 clases.
- Se usa para probar la **generalización out‑of‑domain** de modelos entrenados en LOGIC.

Comparado con datasets previos (por ejemplo, sobre suficiencia de argumentos o detección de ad hominem), LOGIC es más grande y cubre múltiples tipos de falacias, lo que lo hace una base de entrenamiento más rica para clasificadores.


### 3.3 Modelo structure‑aware

El trabajo introduce un **clasificador aware de la estructura lógica** que sirve de baseline avanzado frente a modelos de lenguaje genéricos.
Se apoya en modelos de inferencia natural (NLI) y destilación de estructura de argumentos, inspirado en la tradición lógica de abstraer el contenido en formas simbólicas.

Componentes clave:
- **Backbone NLI**: se usa un modelo pre‑entrenado tipo ELECTRA para inferencia textual, viendo el texto con posible falacia como “premisa” y una oración plantilla sobre una falacia concreta como “hipótesis”.
- **Premise structure‑aware**: el texto se procesa para identificar spans semánticamente similares (mediante coreferencia, lematización, Sentence‑BERT y similitud coseno), que se reemplazan por máscaras [MSK1], [MSK2], etc., de forma que se preserva la **estructura lógica** pero se abstraen contenidos léxicos concretos.
- **Hypothesis structure‑aware**: en lugar de la plantilla simple “This example is [falacia]”, la hipótesis incluye la **forma lógica típica** de cada falacia, también con máscaras (por ejemplo, para falsa causalidad, un esquema del tipo “α ocurre junto con β, luego α causa β”).

La combinación de estas dos representaciones fuerza al modelo a hacer matching de **formas de razonamiento** más que de palabras clave superficiales, lo que resulta relevante para estudiar razonamiento defectuoso en LLMs.


### 3.4 Evaluación de modelos

Los autores evalúan 12 modelos grandes en LOGIC:
- **Zero‑shot**: TARS, BART‑MNLI, RoBERTa‑MNLI, GPT‑2, GPT‑3, usando plantillas NLI o prompts directos.
- **Fine‑tuned**: ALBERT, BERT, BigBird, DeBERTa, DistilBERT, ELECTRA, MobileBERT, RoBERTa, con entrenamiento supervisado sobre LOGIC.

Resultados principales (micro‑F1 en LOGIC):
- Zero‑shot se queda cerca del azar: entre 8,6% y 13,7%, ligeramente mejor que el baseline aleatorio (12%).
- Entre los modelos fine‑tuned, **ELECTRA** es el mejor lenguaje modelo estándar (53,31% F1), seguido de DeBERTa (~50%).
- El clasificador propuesto **ELECTRA‑StructAware** alcanza **58,77% micro‑F1**, mejorando en 5,46 puntos a ELECTRA y logrando también más exact matches de etiqueta.

En la evaluación por clase, falacias como *Ad Hominem* y *Ad Populum* se detectan relativamente bien (F1 ≈ 79%), mientras que **falacias deductivas** alcanzan apenas F1 ≈ 26%, y otras como *Intentional Fallacy* o *Equivocation* también resultan difíciles.


### 3.5 Generalización a LOGICCLIMATE

Para probar robustez, se evalúan modelos entrenados en LOGIC sobre LOGICCLIMATE:
- Transferencia directa: ELECTRA logra 22,72% micro‑F1, mientras que ELECTRA‑StructAware sube a 27,23%.
- Tras un pequeño fine‑tuning adicional en LOGICCLIMATE, las puntuaciones mejoran algo (hasta 23,71% y 29,37% respectivamente), pero siguen muy por debajo de las de LOGIC, mostrando que **generalizar a un dominio realista como el discurso climático es difícil**.

La conclusión general es que incluso modelos relativamente sofisticados entrenados de forma supervisada tienen **limitaciones fuertes en detectar falacias lógicas, especialmente en dominios nuevos y con formas más sutiles de argumentación**.


### 3.6 Limitaciones

El trabajo reconoce varias limitaciones relevantes para tu TFG:
- El modelo structure‑aware depende de que existan spans parafrásticos claros; se degrada en texto natural complejo donde las relaciones lógicas no se reflejan en repeticiones léxicas obvias.
- Sólo se especifica **una forma lógica** por cada falacia; en la práctica, muchas tienen múltiples patrones razonables, lo que limita la cobertura.
- El rendimiento en el dominio climático es bajo, lo que indica que se necesita más trabajo en **generalización out‑of‑domain** y en capturar conocimiento de mundo relevante.
- La anotación de algunas instancias es debatible, ya que varias falacias pueden aplicarse simultáneamente; la tarea se formula como single‑label en LOGIC, lo que ignora parcialmente esta subjetividad.


## 4. Comparación entre MAFALDA y LOGIC

### 4.1 Objetivos y tipo de tarea

- **MAFALDA** se centra en construir un **benchmark unificado y taxonómicamente coherente**, con énfasis en subjetividad de anotación, estructura jerárquica de falacias y evaluación comparativa LLMs vs. humanos en zero‑shot.
- **LOGIC/LOGICCLIMATE** se orienta a definir una **tarea supervisada de clasificación de falacias lógicas concretas** y a explorar modelos que exploten explícitamente la estructura lógica, sobre todo en el contexto de desinformación y cambio climático.

Para un TFG sobre verificación de falacias en LLMs, MAFALDA es muy adecuado como **benchmark de evaluación zero/few‑shot**, mientras que LOGIC es útil como **dataset de entrenamiento o fine‑tuning** de clasificadores o como base para estudiar arquitecturas structure‑aware.


### 4.2 Manejo de la subjetividad

- MAFALDA asume que la anotación de falacias es **intrínsecamente subjetiva** y diseña un esquema que admite múltiples etiquetas alternativas por span, con métricas de evaluación adaptadas.
- LOGIC, en cambio, trata la tarea como **multi‑clase con una etiqueta “correcta”** por ejemplo, lo que simplifica el aprendizaje pero no refleja completamente la ambigüedad semántica.

Si en tu TFG quieres **detectar y explicar falacias cometidas por LLMs**, el enfoque de MAFALDA puede inspirar un diseño de evaluación que tolere diferentes interpretaciones razonables, mientras que LOGIC te ofrece formas lógicas prototípicas para cada tipo de falacia.


### 4.3 Cobertura de tipos de falacia

- LOGIC trabaja con 13 falacias lógicas, muchas de ellas centradas en estructura argumental (generalización defectuosa, causalidad falsa, falacias deductivas, dilemas falsos, etc.).
- MAFALDA cubre también falacias emocionales y de credibilidad (Pathos/Ethos), como *Appeal to Fear*, *Appeal to Tradition*, *Appeal to Nature* o *Guilt by Association*, integradas en una taxonomía más amplia.

Combinados, ambos trabajos cubren un espectro amplio: **razonamiento lógico estrictamente defectuoso** (LOGIC) y **técnicas retóricas falaces en discurso real** (MAFALDA).


### 4.4 Evaluación de modelos de lenguaje

En ambos trabajos, los LLMs muestran **limitaciones importantes**:
- En MAFALDA, incluso GPT‑3.5 sólo alcanza F1 ≈ 0,138 a nivel de falacia fina, y queda claramente por debajo de anotadores humanos.
- En LOGIC, los mejores modelos supervisados rondan 0,59 micro‑F1 en el dominio visto, y caen a ≈0,27–0,29 en el dominio climático, lo que refleja problemas de generalización y de capturar patrones de razonamiento sutiles.

Esto apoya la idea de que los LLMs actuales son buenos en **fluidez y correlaciones superficiales**, pero siguen siendo débiles detectando y evitando razonamientos falaces, especialmente cuando cambia el dominio.


## 5. Ideas útiles para tu TFG

A partir de estos dos trabajos se pueden extraer varias ideas prácticas para un TFG sobre verificación de falacias en LLMs:

1. **Definición de tareas y niveles**:
   - Puedes adoptar la estructura de niveles de MAFALDA (0/1/2) para evaluar LLMs tanto en detección binaria de falacia como en clasificación fina y categorización general (Pathos/Ethos/Logos).
2. **Diseño de métricas**:
   - El esquema disyuntivo y las métricas de MAFALDA son un buen punto de partida si piensas recoger anotaciones humanas sobre salidas de LLMs y quieres respetar la subjetividad.
3. **Modelado de estructura lógica**:
   - Las formas lógicas de LOGIC y su modelo structure‑aware ofrecen patrones reutilizables para diseñar prompts o módulos simbólicos que verifiquen si la respuesta del LLM sigue una estructura falaz conocida.
4. **Evaluación zero‑shot vs. fine‑tuning**:
   - MAFALDA se ajusta bien a experimentos zero‑shot o few‑shot sobre modelos generales; LOGIC y LOGICCLIMATE son más adecuados para probar clasificadores especializados, ejecuciones de fine‑tuning o adapters.
5. **Análisis de errores**:
   - Ambos trabajos muestran que las falacias emocionales y ciertas falacias lógicas (deductivas) son especialmente difíciles; puedes focalizar tu TFG en analizar por qué los LLMs fallan ahí y qué técnicas (explicaciones, cadenas de pensamiento, verificación externa) ayudan más.

En conjunto, estos dos artículos te proporcionan la base teórica (taxonomías, definiciones, subjetividad), los recursos empíricos (datasets y métricas) y los primeros resultados experimentales sobre LLMs necesarios para plantear y justificar un TFG sólido sobre verificación de falacias en modelos de lenguaje.