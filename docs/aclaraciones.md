1. Qué es un “corpus” en tu TFG
En este contexto, un corpus es simplemente un conjunto estructurado de ejemplos de texto, con información asociada, que vas a usar para tus experimentos.

En tu trabajo sería algo así como una tabla o JSON donde cada fila tiene, por ejemplo:

un identificador (id),

el tipo de falacia prevista (según tu taxonomía reducida),

el prompt que se mandó al LLM,

el texto generado por el LLM,

las respuestas de otros LLMs ante ese texto (si las hay),

y opcionalmente, una etiqueta humana (tú) diciendo si realmente contiene la falacia X o no, y quizá algún comentario.

Ese corpus es tu “materia prima” para analizar: qué falacias saben generar, cuáles detectan, cuándo las aceptan, etc.

2. ¿Por qué generar tú las falacias con prompts?
Aquí está el punto clave del diseño del TFG.

Podrías usar ejemplos existentes de falacias (de libros, webs, datasets), pero tu objetivo global es justo:

ver cómo se comportan los LLMs cuando se les pide explícitamente generar falacias,

y qué hacen cuando se les enseñan esos argumentos falaces (¿los aceptan? ¿los critican? ¿los corrigen?).

Por eso tiene sentido que:

Definas tú las clases de falacias (taxonomía reducida).

Diseñes prompts que pidan al modelo “haz una falacia de tipo X sobre tema Y”.

Dejes que el LLM invente el argumento siguiendo tus instrucciones.

Ventajas de esto:

Ves si el LLM entiende operativamente lo que es una falacia (no solo repetir definiciones).

Obtienes muchos ejemplos relativamente rápido, adaptados exactamente a tu taxonomía y tus temas.

Te aseguras de que el corpus está alineado con tu experimento: sabes qué falacia se intentaba inducir en cada caso.

3. Entonces, ¿qué haces con esas salidas? ¿Revisarlas a mano?
Sí, pero con matices:

3.1. Paso 1: generación “intencionada”
Tu pipeline, a grandes rasgos:

Eliges una falacia, por ejemplo falsa causa.

Preparas un prompt del estilo:

“Genera un argumento corto sobre las vacunas que cometa la falacia de falsa causa, según esta definición: […]. No expliques qué falacia es, solo da el argumento.”

El LLM responde con un texto.

Eso entra en tu corpus con la etiqueta “falacia prevista = falsa causa”.

Aquí, la etiqueta es “intención” (lo que tú le pediste al LLM), no lo que realmente ha hecho.

3.2. Paso 2: ver si realmente es falaz (validación)
Ahora toca ver si el modelo ha “obedecido” o no:

Puedes revisar a mano una muestra (o todos, si no son demasiados) y marcar:

“Sí, contiene falsa causa como estaba previsto.”

“No, en realidad es un argumento válido o comete otra falacia distinta.”

Opcionalmente, puedes apoyar esta revisión con un LLM juez:

Le pasas el texto generado y le pides:

“Lee este argumento, di si contiene una falacia de falsa causa (sí/no) y justifica tu respuesta brevemente.”

Pero lo ideal es que tú revises al menos bastante parte para que el TFG no dependa solo del juez automático.

En el corpus, podrías tener columnas como:

falacia_prevista (la que pediste en el prompt),

falacia_generada_humano (lo que tú crees que es realmente),

falacia_generada_juez (lo que dice el LLM fuerte, si lo usas).

Eso te permite luego hacer análisis del tipo:

¿Con qué frecuencia el LLM genera la falacia correcta cuando se la pides?

¿Hay falacias que le cuesta más producir bien?

¿Tiende a “portarse bien” y evitar la falacia, aunque se la pidas?

4. La segunda parte: cómo reaccionan otros LLMs ante esas falacias
Una vez tienes argumentos falaces generados (y minimamente validados), puedes hacer la otra mitad del experimento:

Tomas un ejemplo del corpus: un argumento que tú has marcado como “falsa causa”.

Se lo mandas a otro modelo (o al mismo) con un prompt tipo:

“Lee el siguiente argumento y responde si estás de acuerdo o no, y explica por qué.”

o bien

“Identifica si este argumento contiene alguna falacia de razonamiento. Si es así, dime cuál y explícalo.”

Guardas la respuesta en el corpus.

Luego miras:

¿Lo acepta sin crítica?

¿Lo corrige o lo discute?

¿Señala correctamente el tipo de falacia?

¿Da una explicación razonable?

Aquí otra vez puedes:

Anotar tú (a mano) algunas respuestas:

“Crítica correcta”, “crítica parcial”, “aceptación acrítica”, etc.

Usar un LLM juez para ayudarte a clasificar de forma más masiva, si llegas a esa fase.

5. Resumen de la idea global (para que te cuadre mentalmente)
El objetivo no es simplemente “mirar si los LLMs cometen falacias al azar”, sino:

Forzar el contexto:

Les pides explícitamente generar falacias de tipos concretos.

Así puedes medir: ¿entienden y reproducen esos patrones falaces?

Crear un corpus sintético controlado:

Cada ejemplo viene con información de qué falacia se esperaba.

Tú verificas (al menos en parte) que eso se cumple.

Evaluar su comportamiento crítico:

Luego les presentas esos mismos argumentos falaces como si fueran “noticias” u opiniones.

Mides si los LLMs los tragan, los rechazan, o los desmontan correctamente.

Todo eso se apoya en el corpus que generas: sin corpus, no tienes base para hacer análisis sistemático.
Y al generarlo tú con prompts, el corpus refleja exactamente las falacias y los escenarios que quieres estudiar, que es la contribución principal del TFG.

Si quieres, en el siguiente mensaje puedo dibujarte el flujo entero en pasos numerados (de 1 a 10) tipo “pipeline del experimento”, y sugerirte cómo lo mapearías a scripts Python concretos.s