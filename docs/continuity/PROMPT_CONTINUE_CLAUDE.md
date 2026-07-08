# PROMPT DE CONTINUIDAD — DAY 211 (continúa DAY 210)

## Instrucciones generales para Claude
1. Piensa antes de codificar. Expón suposiciones. Pregunta cuando no estés seguro. Nunca adivines.
2. Simplicidad primero. Código mínimo. Sin abstracciones que nadie pidió.
3. Cambios quirúrgicos. No toques código no relacionado. Cada línea rastreable a lo pedido.
4. Ejecución orientada a metas. Instrucciones vagas → criterios de éxito verificables.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria; trazar hacia atrás desde el binario.
- **Lección DAY 209:** trazar la correspondencia entre el DIAGRAMA/narrativa y el binario. El bug del veredicto vivió un año porque los tests validaban que el código es *correcto*, pero nadie verificó que ejecutara la arquitectura que el diagrama *dibujaba*.
- **Lección DAY 211 (lecturas parciales):** NO concluir "X no se ejecuta" a partir de un `sed -n` truncado. En esta sesión se leyó 345–415 y se concluyó erróneamente "solo corre L1"; las 4 cabezas SÍ corrían, en 558–802. La conclusión correcta ("corren pero desconectadas del veredicto Y gateadas por L1") solo apareció tras `grep` de la función ENTERA. Regla: grep completo de la función antes de afirmar ausencia. Es "medir no votar" aplicado a la propia lectura.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable; Kuzu = proyección reconstruible).
- **EMECAS+++** antes de cualquier merge · **PR obligatorio** (main tiene branch protection).
- **Consejo de Sabios** ratifica decisiones de arquitectura.
- macOS/zsh: comillas en globs de grep (`--include='*.cpp'`), NUNCA `sed -i`, `sed -n 'A,Bp'` para leer. Python3 heredoc para editar. Commits/push desde el HOST.
- Rama ANTES del primer `git add` (no antes del commit). Scripts scratch `.py` → `.gitignore` al momento de crearlos.
- Un día, una batalla. Features pequeñas, merge frecuente vía EMECAS+++.

---

## Estado al cierre de DAY 211

### Contexto: sesión de AUDITORÍA (no de código)
DAY 211 fue enteramente **auditar el cableado del veredicto** en `zmq_handler.cpp` vía
greps sucesivos. (La conversación empezó la tarde de DAY 210 pero quedó inacabada — los
comandos se lanzaron la mañana de DAY 211.) No se escribió código ni se mergeó nada.
Resultado: **diagnóstico COMPLETO de `DEBT-VERDICT-MONOCAPA-001` + decisión firme de rama.**

### DIAGNÓSTICO COMPLETO — el veredicto tiene DOS defectos apilados

**CONFIRMADO de DAY 210 (sin cambios):**
- La vieja sobrescritura (bug DAY 11–12) YA NO EXISTE. `fast_score` se lee (352) y se preserva.
- `ml_score = confianza de L1` (408). `final_score = max(fast_score, ml_score)` (410). `set_overall_threat_score` (411). Comentario del propio código: *"Dual-Score Architecture"* — el autor documentó que aquí hay 2 scores, no 3.
- Las 4 cabezas (DDoS 558, ransomware 626, traffic 697, interno 756) predicen y rellenan `ml_analysis`; NINGUNA vuelve a tocar `overall_threat_score`.

**NUEVO de DAY 211 (lo que el prompt de DAY 210 NO tenía):**
- **Defecto A (secuencia):** el veredicto se sella en 411, ANTES de que corran las 4 cabezas (558–802). Las especializadas son observadores que escriben un informe que el veredicto ya no lee.
- **Defecto B (GATE) — CAUSA RAÍZ:** línea 552 `if (label_l1 == 1 && confidence_l1 >= config_.ml.thresholds.level1_attack)`. Las 4 especializadas SOLO corren si L1 dijo ATTACK. **L1 es portero, no compañero de ensemble.** Es H4 hecho código: un flujo que el interno vería como exfiltración/lateral pero que L1 (genérico, CICIDS2017) marca BENIGN, sale BENIGN y el interno NUNCA se ejecuta.
- **Consecuencia clave para el plan:** mover el veredicto (arregla A) **NO arregla B**. Hay que sacar interno+traffic de debajo del gate de L1. B condiciona A → decidir B primero.
- **Cascada existente (749):** el interno solo corre si traffic dice "interno" — anidado dentro de traffic. Flujo real: L1 general → traffic decide dominio → interno mira dentro. Es *casi* la tricapa del paper, salvo que la salida de la cascada nunca sube al `max`.
- **NUEVO DEBT — `DEBT-RAG-ATTACKFAMILY-HARDCODED-001` (P2):** línea 505 `ml_context.attack_family = "RANSOMWARE"; // TODO: Get from detector`. Todo lo que entra al RAG log sale etiquetado "RANSOMWARE" sea lo que sea. Crítico si el RAG entra en el circuito de reentrenamiento. (NO confundir con `threat_category`, que es otro campo — ver Flanco abierto.)
- **Activo aprovechable:** bloque 414–424 (`authoritative_source`: DIVERGENCE / CONSENSUS / FAST_PRIORITY / ML_PRIORITY) ya razona fast vs ml y escribe `decision_metadata` + provenance (`add_verdicts`, `discrepancy_score`). Germen del combinador, extensible de 2 a 5 fuentes. No se parte de cero en la trazabilidad.

### ACTUALIZACIÓN DE LA DECISIÓN DE DAY 210 (importante — resuelve una contradicción)
- **DAY 210 decía:** Camino A (corregir narrativa del paper) pre-FEDER; Camino B (reconectar las 4 cabezas + re-medir) DIFERIDO a post-FEDER.
- **DAY 211 ESCALA:** se crea rama `fix/verdict-multihead-honest` para reconectar el **CABLEADO** pre-FEDER, con honestidad de pesos. Solo el **ARREGLO de los modelos ransomware/ddos** (reentrenar contra ground truth de red) se difiere a post-FEDER.

**Alcance de la rama (Opción 1, firme):** reconectar las 4 cabezas al veredicto;
ransomware y ddos entran con **peso ≈0 (fiabilidad medida)**; su reentrenamiento diferido
a post-FEDER.
- "Honesto" ≠ "las 4 fiables". Honesto = el veredicto usa cada señal según su fiabilidad medida Y el paper lo dice. Una cabeza con fiabilidad ≈0 entrando con peso ≈0 es honesta.
- Meter "las 4 fiables" como precondición sería recomprometerse con el Camino B completo, que NO cabe antes del go/no-go (1-ago). Riesgo FEDER real: vigilar que la rama no se expanda a reentrenar ransomware/ddos.
- **Puerta abierta por construcción:** reconectar ransomware/ddos ya arreglados post-FEDER = cambiar 1 peso de config de ≈0 a su valor medido. Una línea por cabeza. NO reabre arquitectura, NO toca el cableado, NO es un segundo `DEBT-VERDICT`. Esta opción es la que MÁS abierta deja la puerta.

### OPERADOR DE COMBINACIÓN (acordado)
**noisy-OR:** `P = 1 − ∏(1 − pᵢ)`, con `pᵢ_efectivo = fiabilidad_i · score_crudo_i`.
- Monótono (nadie suprime a nadie — **NO usar media ponderada, diluye** y deja que vecinos callados voten a la baja una cabeza fiable que dispara). Corroboración incorporada (ransomware+interno se refuerzan). Siempre ≥ que `max` (fast-path domina cuando dispara).
- Pesos = fiabilidad MEDIDA (5.2b + F1 por cabeza), NO votada. Provisionales: interno y traffic ALTAS (H5/H7); ransomware y ddos ≈0 (features rotas → no envenenan aunque capturen telemetría).

### FORMULACIÓN HONESTA PARA EL PAPER (evitar sesgo de confirmación tipo Q1)
Con ransomware/ddos a peso ≈0, NO entran en el veredicto → **NO pueden *causar* divergencia
con Suricata/Zeek.** Lo suyo es un **HUECO DE COBERTURA** (no hay cabeza dedicada funcional;
la detección de esas clases recae en fast-path + fases de red del interno), **NO una
divergencia predicha.** NO pre-explicar divergencias aún no medidas. Suricata F1=0.000 /
Zeek F1=0.042 en Neris = **paradigma** (firma vs comportamiento), no las cabezas de aRGus.
**Regla de oro:** la limitación es una frase sobre aRGus ("aún no tenemos estas 2 cabezas"),
NO una predicción sobre la comparativa ("por eso divergiremos"). Cualquier divergencia
observada = hallazgo a investigar flujo a flujo, no excusa escrita antes de mirar.

---

## Rama `fix/verdict-multihead-honest` — plan de fases (TDH + EMECAS+++)
Rama ANTES del primer `git add`. Cada fase con gate de medición; nada sube al veredicto sin su pulso medido.

1. **Pulso del interno (5.2b) + COSTE — EL paso que lo decide todo.**
    - (i) ¿Separa clases sobre CTU-13/tráfico etiquetado? (extractor sano ≠ clasificador bueno).
    - (ii) ¿Cuánto cuesta correrlo DESACOPLADO de L1 (en todos los flujos)? ¿Cabe en <10ms recepción→clasificación→firewall?
    - Esto decide la arquitectura del gate (Defecto B). SIN este número, todo lo demás es especulación.
    - A verificar: firma de `InternalDetector::predict`; reusar `test_*_unit` si existe.
2. **Reconexión del cableado (Defectos A+B).** Mover veredicto tras 802; sacar interno+traffic del gate de L1; sustituir `max` por noisy-OR con fiabilidades provisionales. Tests unitarios del combinador: (a) una cabeza dispara, (b) dos corroboran, (c) cabeza fiabilidad-0 NO envenena.
3. **Integración + stress test** (el que sustituye al sniffer) con medición de latencia por cabeza.
4. **pcap relay e2e en hardware propio**, TTL real recepción→clasificación→firewall.
5. **Solo entonces** los números TTL → paper, acompañados de la config honesta (qué cabeza pesa cuánto; ransomware/ddos ≈0).

**Propuesta de gate para el Defecto B (a validar con la medición de fase 1):** interno+traffic corren SIEMPRE (fiables, desacoplados de L1); ransomware+ddos pueden quedar gateados por COSTE hasta su reconstrucción post-FEDER (gatearlos no cuesta falsos negativos: su señal es ≈0 hoy).

**Mediciones del plan pendientes, subordinadas a la rama (arrastradas de DAY 210):**
- 5.2a — feature importance del modelo interno (¿pesan las 2 constantes `[1]`,`[2]`? → desajuste train/inference). Leer metadata JSON.
- 5.1 — ¿NERIS activa el interno? relay NERIS + `grep SUSPICIOUS_INTERNAL detector.log`. Dice si ya hay fuente de datos internos o si MITRE es imprescindible.
- 5.2c — auditar `extract_level3_traffic_features` (~347), único extractor sin auditar.
- 0.3 — distribución de `authoritative_source` sobre un `detector.log` existente (cuantifica fast-path vs L1 en el veredicto).

---

## Housekeeping pendiente (arrastrado de DAY 210, aún sin hacer)
- Anexar la sección DAY 210 (ampliada en DAY 211: decisión de alcance + formulación honesta de la limitación) al PLAN DE CAMPAÑA local. **La fuente de verdad es el PLAN — copiar de ahí, no regenerar.**
- Registrar `DEBT-VERDICT-MONOCAPA-001` + el nuevo `DEBT-RAG-ATTACKFAMILY-HARDCODED-001` en `docs/BACKLOG.md`.
- Actualizar `docs/BACKLOG.md` y `README.md` con el estado real del pipeline.
- `git rm` del `proto_aligned` con su DEBT.

## Flanco abierto (anotar)
`threat_category` ("RANSOMWARE", "SUSPICIOUS_INTERNAL") viaja al bronce/firewall aunque no
cambie `final_classification`. ¿Algún consumidor río abajo actúa sobre `threat_category`?
Rastrear antes de afirmar "las cabezas no sirven para nada": etiquetan, aunque no decidan.
(Distinto del `attack_family` hardcodeado del RAG — ese es el DEBT nuevo.)

## Punteros (líneas medidas DAY 211 — re-verificar al abrir el fichero)
- `zmq_handler.cpp::process_event`: fast_score **352** · ml_score **408** · max **410** · set **411** · authoritative_source **414–424** · attack_family hardcoded **505** · **GATE L1 552** · DDoS **558** · ransomware **626** · traffic **697** · interno **756** (predict **780**, fin sección ~**802**).
    - *DAY 209 los situó en 406/432; usar los de DAY 211. Si al abrir no cuadran, hubo cambio de líneas entre sesiones — re-grepear `set_overall_threat_score` y `label_l1 == 1 &&`.*
- `feature_extractor.cpp` — 4 extractores. Internal 404–448 (8/10 sano: `[5]` lateral y `[7]` exfil REALES; `[1]`,`[2]` constantes). Traffic ~347 SIN auditar.
- `ml_detector_config.json` — 4 cabezas `enabled:true` pero desconectadas del veredicto.
- PLAN DE CAMPAÑA (repo) — FUENTE DE VERDAD. H1–H7, fases 0–5, criterios de parada.
- Paper arXiv:2604.04952 — corregir narrativa tricapa→monocapa (Camino A) + añadir limitación de hueco de cobertura.

## Ranking de salud de los 4 extractores (medido DAY 209, sin cambios DAY 211)
| Cabeza | Extractor | Veredicto |
|---|---|---|
| **Internal (L3)** | 8/10 honesto; `[5]` lateral y `[7]` exfil REALES; `[1]`,`[2]` constantes | **mejor candidato** |
| DDoS (L2) | 6/10 honesto, 3 constantes, features de peso reales | degradado, vivo |
| Traffic (L3) | NO auditado aún (5.2c) | ? |
| Ransomware (L2) | 1/10 real, 9/10 proxies de host (entropy = varianza de paquete) | roto por diseño |

## Estado emocional / ritmo (contexto para Claude)
DAY 210 cerró golpeado (bug longevo pese a vigilancia adversaria); decisión sana de no
publicar en LinkedIn. DAY 211 el encuadre ya está sano y en acción: el hallazgo del gate
es la vigilancia FUNCIONANDO ~6 semanas antes del go/no-go, con margen para la verdad. El
escudo protege igual (fast-path + L1). La rama convierte "descubrimos un desaguisado" en
"lo arreglamos de una vez, honestamente, sin cerrarnos puertas". No dejar que el cansancio
lo lea como una losa. Ritmo real marcado por el cuidado familiar y las ventanas de crédito.

*Via Appia Quality — medir quién clasifica, no solo cómo de bien. Un escudo que conoce sus
propias sombras, incluida la sombra entre su código y su diagrama.*