# aRGus NDR — PROMPT DE CONTINUIDAD · DAY 196

## ESTADO EMOCIONAL / CONTEXTO HUMANO
DAY 195 cerró bien. Lo que entró como dos deudas "carta de defunción" salió
como una reparación de header con el modelo intacto detrás. El método —tirar
hacia atrás desde el binario— evitó escribir "dos modelos, reentreno" leyendo
solo el script. Retomar en frío, sin prisa. Cuido a mis padres en paralelo;
el hardware llega cuando llega y eso es el ritmo realista, no un retraso.

## MÉTODO (invariante)
"Medir, no votar." Tirar hacia atrás desde el binario. Toda afirmación contra
fichero, nunca contra memoria. EMECAS++ antes de cualquier merge. PRs obligatorios.

## LO CERRADO AYER (DAY 195, por el dato)
- DEBT-RANSOMWARE-MODEL-DESYNC-001 DIRIMIDA: 5bbddd11 reentrenó pero de forma
  estructuralmente equivalente a un reescalado. feature[] y children_left[]
  idénticos en los 100 árboles entre 830b0ec0 y 5bbddd11; solo cambian thresholds
  (MinMaxScaler afín monótona, random_state=42 intacto). UN único modelo.
  feature_importances VÁLIDOS para el desplegado. Veto de model_info en el paper
  se estrecha a RENDIMIENTO, no a importancias.
- DEBT-RANSOMWARE-ML-HEAD-INERT-001 abierta (P1, pre-producción): cabeza ML de
  ransomware no funcional en red por SEMANTICS-001. Detecta vía fast path; ml ~0.14.
- LAB-RANSOMWARE-FIRETEST-SPEC creada en docs/experiments/. Diseño cerrado,
  ejecución pendiente de hardware. H1 registrada con fecha.

## PENDIENTE DE AYER ANTES DE ABRIR FEATURE
1. Pegar las inserciones de BACKLOG (3) + README (estado DAY 195) que quedaron
   redactadas. Revisar git diff completo. NO usar script Python — edición a mano,
   el diff es la red de seguridad.
2. git add de LAB-RANSOMWARE-FIRETEST-SPEC.md (dos capas: staged + modificado).
3. Commit en day194/ransomware-provenance-desync, push, y decidir merge a main.

## PRIMER ACTO DAY 196 (decisión de arranque del circuito)
Abrir rama nueva para la PRIMERA feature del circuito completo. Dos candidatas,
ambas avanzan sin hardware peligroso:
- BACKLOG-CIRCUIT-ADAPTERS-ZMQ-001: productores ZMQ en los adapters bajo ADAPTER-V1.
- E2 / port ARM64 (LAB-RANSOMWARE-FIRETEST-SPEC §9): compilar aRGus a ARM64,
  correr el sniffer en una RPi sobre tráfico BENIGNO. Deja el sensor probado para
  cuando llegue el laboratorio. Trabajo de circuito, cero malware.

## ENCUADRE DEL CIRCUITO (decisión Alonso DAY 195)
Terminar el circuito completo —adapters, LZ con consumidores ZMQ, capa Arrow/C++
CSV→AVRO(bronce)→PARQUET(plata)→PARQUET unificado(oro), conector Kuzu sobre oro,
dashboard de consulta al grafo— ASUMIENDO la inferencia ML rota/incompleta. NO es
el pipeline de producción (producción requiere ETCD HA + reentreno + resto de
deudas pre-FEDER). Objetivo: microscopio afinado (join community_id, correlación
Wazuh↔community_id) para poder medir si una mejora del modelo es real antes de
fiarse de plugins ensemble. El reentreno (ransomware real EN RED, no sintético
host) es POSTERIOR al circuito.

## NO HACER
- No citar model_info como RENDIMIENTO de producción en el paper (importancias sí).
- No fiarse de plugins ensemble del ml-detector hasta cerrar ML-HEAD-INERT-001.
- No detonar nada sin la contención seria de LAB-RANSOMWARE-FIRETEST-SPEC §4.
- No reentrenar los fundacionales antes de tener el microscopio (ground truth de
  circuito), ni contra el eval host que ya sabemos que no transfiere.
- No comprar Raspberry Pi como VÍCTIMA: el malware x86 no corre en ARM. La RPi es
  SENSOR (E2). Víctimas = x86 pequeñas.

## REPO
/Users/aironman/CLionProjects/test-zeromq-docker (remote github.com/alonsoir/argus)
Rama actual: day194/ransomware-provenance-desync
Paper: arXiv:2604.04952, Draft v2 (12 correcciones, 22 jun).