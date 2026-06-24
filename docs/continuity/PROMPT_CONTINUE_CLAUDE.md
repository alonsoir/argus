# aRGus NDR — PROMPT DE CONTINUIDAD · DAY 195

## ESTADO EMOCIONAL / CONTEXTO HUMANO
DAY 194 cerró con dos hallazgos duros sobre el detector de ransomware.
Terminé agotado y desanimado. NO es carta de defunción: son dos deudas
acotadas y reparables. El modelo corre; falla la trazabilidad documentada.
Retomar en frío, sin arrastrar el ánimo de anoche.

## MÉTODO (invariante)
"Medir, no votar." Tirar hacia atrás desde el binario, no hacia delante
desde el yacimiento. Toda afirmación verificada contra fichero, nunca
contra memoria. Ese método es el que sacó esto a la luz en junio.

## LO PROBADO AYER (por el dato, cerrado)
- Header de producción `ml-detector/src/forest_trees_inline.hpp` proviene
  del JSON de NACIMIENTO `830b0ec0` → raíz tree_0 = 0.9150086343, byte a byte.
- El JSON del repo fue REESCRITO en `5bbddd11` ("EPIC normalización",
  3.664 líneas, thresholds → [0,1], raíz tree_0 = 0.3815). El header de
  ransomware NUNCA se regeneró (solo `830b0ec0` + chore permisos `5d9711a1`).
- Conclusión: header compilado = bosque SIN normalizar; JSON del repo =
  bosque normalizado. `model_info` describe el normalizado, NO el desplegado.
  Generador `generate_cpp_forest.py` ya no está en el árbol de trabajo
  (existe solo dentro de `830b0ec0`).

## DEUDAS ABIERTAS PARA EL CONSEJO
### DEBT-RANSOMWARE-MODEL-DESYNC-001 (P1, pre-FEDER)
Header ≠ JSON. No citar `model_info` (feature_importances, 0.36 entropy)
en el paper como propiedad del modelo en ejecución hasta resolver.
Acción: decidir bosque canónico → regenerar header con pipeline
determinista y versionado, O restaurar+versionar el JSON de origen.

### DEBT-RANSOMWARE-FEATURE-SEMANTICS-001 (Escenario B, firme por datos)
`synthetic_ratio_experiment.py` modela sobre `data/files_guaranteed.csv`
y `data/processes_guaranteed.csv` (espacio host real: entropía de fichero,
operaciones de fichero, anomalía de proceso) que el sensor network de
aRGus NO puede medir. feature[1] "entropy" en producción = varianza de
longitud de paquete / 100000, no Shannon. Independiente del desync.

## PRIMER ACTO DAY 195 (la pregunta que dirime todo)
¿`5bbddd11` solo REESCALÓ thresholds o REENTRENÓ el modelo?
- Si reescaló → header y JSON son el MISMO árbol en dos escalas →
  corrección = regenerar header. Reparación limpia.
- Si reentrenó → son DOS modelos distintos → decidir cuál es el bueno.
  Comando árbitro:
  git show 5bbddd11 -- ml-training/scripts/ransomware/train_simple_effective.py
  (44 líneas tocadas en el --stat; leer qué cambió en el entrenamiento)
  Complementario, ver el alcance real del diff del JSON:
  git show 5bbddd11 -- ml-training/scripts/ransomware/complete_forest_100_trees.json | head -120

## NO HACER
- No tocar main aún. No citar model_info en el paper. No asumir muerte
  del proyecto. No tirar de hilos nuevos hasta cerrar reescaló-vs-reentrenó.

## REPO
/Users/aironman/CLionProjects/test-zeromq-docker (remote github.com/alonsoir/argus)
EMECAS++ antes de cualquier merge. PRs obligatorios.