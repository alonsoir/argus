# PROMPT DE CONTINUIDAD — DAY 210 (continúa DAY 209)

## Instrucciones generales para Claude
1. Piensa antes de codificar. Expón suposiciones. Pregunta cuando no estés seguro. Nunca adivines.
2. Simplicidad primero. Código mínimo. Sin abstracciones que nadie pidió.
3. Cambios quirúrgicos. No toques código no relacionado. Cada línea rastreable a lo pedido.
4. Ejecución orientada a metas. Instrucciones vagas → criterios de éxito verificables.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria; trazar hacia atrás desde el binario.
- **Y una capa más, lección DAY 209:** trazar también la correspondencia entre el DIAGRAMA/narrativa y el binario. El bug de este día vivió un año porque los tests validaban que el código es correcto, pero nadie verificó que el código ejecutara la arquitectura que el diagrama dibujaba. La vigilancia miraba corrección, no correspondencia narrativa.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable; Kuzu = proyección reconstruible).
- **EMECAS+++** antes de cualquier merge · **PR obligatorio** (main tiene branch protection).
- **Consejo de Sabios** (9 modelos) ratifica decisiones de arquitectura.
- macOS/zsh: comillas en globs de grep (`--include='*.cpp'`), NUNCA `sed -i`, `sed -n 'A,Bp'` para leer sí. Python3 heredoc para editar. Commits/push desde el HOST.
- Rama ANTES del primer `git add` (no antes del commit). Scripts scratch `.py` → `.gitignore` al momento de crearlos.
- Un día, una batalla. Features pequeñas, merge frecuente vía EMECAS+++.

## Estado al cierre de DAY 209

### CERRADO Y MERGEADO
- `test_flujo_a_b_equivalence` (ADR-058 §3.1, Camino-0 ≡ Flujo-A+B): escrito, verde en
  aislado (0.71s), **EMECAS+++ verde**, **mergeado a main**. Frente cerrado.
- Housekeeping: BACKLOG con fleet-architecture, GeoIP, MITRE/Atomic Red Team;
  DEBT-KUZU-CONTINUITY actualizado con forks. `proto_aligned` PENDIENTE de `git rm`.

### HALLAZGO CENTRAL DEL DÍA — el veredicto del pipeline es MONOCAPA
Rastreo del ml-detector (medido por lectura completa de `zmq_handler.cpp::process_event`,
líneas 322–880). Disparado por auditoría de features del ransomware inerte, derivó en
descubrir que **el veredicto NO usa la arquitectura tricapa que el diagrama afirma**:

```
ml_score    = confianza de Level 1  (RandomForest ONNX 23 feat, "ATTACK vs BENIGN")
final_score = max(fast_score, ml_score)                          // línea 406
final_classification = final_score >= malicious_threshold ? MALICIOUS : BENIGN  // 432
```

Las 4 cabezas embebidas (DDoS, Ransomware [L2]; Traffic/externo, Internal [L3]) se
ejecutan DESPUÉS (líneas 558–794), escriben en `ml_analysis.specialized_predictions` y
`threat_category` (telemetría → CSV/bronce), y **NINGUNA toca el veredicto**.

**Causa raíz (medida + memoria recuperada de conversaciones ago-2025 y DAY 83):**
NO es desconfianza deliberada. Es residuo de una crisis de concurrencia (ago 2025): 7
modelos con race conditions → recorte a 4 → hardcodeo para estabilizar → veredicto quedó
en L1, nunca revertido. Combinado con la restricción dura de latencia SUBMILISEGUNDO.

### DECISIÓN DE ALONSO (tomada, firme)
**Actualizar el paper para contar la verdad.** Reconocer el bug (`DEBT-VERDICT-MONOCAPA-001`),
con los ficheros del repo como evidencia. Narrativa honesta: fast-path heurístico (alto
recall, alto FPR) validado por L1 (reduce FPR ~15.500×, medición DAY 83), cabezas L2/L3 =
enriquecimiento categórico. NO inflar "tricapa". El resultado de reducción de FP sostiene
el paper por sí solo. Camino A (corregir narrativa) pre-FEDER; Camino B (integrar 4
cabezas al veredicto + re-medir) post-FEDER.

### RANKING DE SALUD DE LOS 4 EXTRACTORES (medido, feature_extractor.cpp)
| Cabeza | Extractor | Veredicto |
|---|---|---|
| **Internal (L3)** | 8/10 honesto; `[5]` lateral y `[7]` exfil REALES; `[1]`,`[2]` constantes | **mejor candidato** |
| DDoS (L2) | 6/10 honesto, 3 constantes ([2],[3],[7]), features de peso reales | degradado, vivo |
| Traffic (L3) | NO auditado aún | ? |
| Ransomware (L2) | 1/10 real, 9/10 proxies de host (entropy=varianza de paquete) | roto por diseño |

### GIRO ESTRATÉGICO (lo bueno entre los escombros)
El clasificador **interno** tiene extractor sano en lo que importa (lateral movement `[5]`,
exfiltración `[7]` = fases de red del ransomware) + dataset de procedencia PROPIA (Alonso
generó los datasets de tráfico web e interno con scripts que recorrieron internet). Es el
activo más prometedor. **El camino más corto a "ransomware-por-red" quizá no sea entrenar
un modelo nuevo con MITRE, sino arreglar 2 constantes del interno + reconectarlo al
veredicto + medir su pulso.** Mucho menos trabajo que un modelo desde cero.

### ENCUADRE CORRECTO (correcciones a premisas de Alonso, para no autoinculparse)
- "El pipeline se queda sin detección de ransomware/ddos" → FALSO. El fast-path detecta
  fases de red de ransomware (tiene `send_ransomware_features` desde DAY 37) + L1. La
  detección existe; lo que no funciona son las cabezas ML de refinamiento *encima*.
- "Fracasamos en generar los clasificadores" → mezcla 3 fallos distintos: modelo (NO
  medido), adaptador de features (roto, medido), cableado del veredicto (desconectado,
  medido). No afirmar "fracaso de modelado" hasta la prueba de pulso.
- MITRE/Atomic Red Team NO arregla clasificadores — genera tráfico etiquetado (materia
  prima). Medir su VOLUMEN antes de prometerlo como training (un atomic C2 puede ser un
  `curl` → decenas de flujos, no los miles que exige entrenar).
- Ensemble de regresión (OK/KO): viable, pero solo sobre señales FIABLES (L1 + traffic +
  internal). Basura dentro = basura fuera.

## Feedback del Consejo (7-2) sobre la propuesta de auditoría
7 aprobaron las 5 preguntas (desactivar ransomware, DEBTs, Opción A red, MITRE). 2
adversarios (ChatGPT, Claude) señalaron el pecado raíz: nadie MIDIÓ, se infirió del
código. El terreno común: no firmar el ADR de desactivación sin medir el pulso. Aportación
de ChatGPT ignorada por los 7: reformular "detector de ransomware" como scorer de técnicas
ATT&CK (inferencia de nivel superior, no clase binaria). El plan de campaña recoge todo.

## Acciones DAY 210 (en orden de valor)

1. **PRIMERO, housekeeping de docs (Alonso lo pidió para DAY 210):**
    - Actualizar `docs/BACKLOG.md` y `README.md` con el hallazgo del veredicto monocapa y
      el estado real del pipeline. La fuente de verdad es el PLAN DE CAMPAÑA (fichero en
      repo) — copiar de ahí, no regenerar.
    - Registrar `DEBT-VERDICT-MONOCAPA-001` formalmente.
    - `git rm` del `proto_aligned` con su DEBT (pendiente de DAY 209).

2. **5.2b — Pulso del clasificador interno (EL paso más valioso).** ¿Su distribución de
   scores separa clases sobre tráfico etiquetado? Extractor sano ≠ clasificador bueno.
   Decide la estrategia entera: si separa, reconectar (barato); si no, reentrenar (MITRE).
   A VERIFICAR: firma de `InternalDetector::predict`, reusar `test_*_unit` si existe.

3. **5.2a — Feature importance del modelo interno.** ¿Pesan mucho las 2 constantes
   (`[1]`,`[2]`)? Si sí, hay desajuste train/inference. Leer metadata JSON del modelo.

4. **5.1 — ¿NERIS activa el interno?** Correr relay NERIS + `grep SUSPICIOUS_INTERNAL
   detector.log`. Dice si ya hay fuente de datos internos o si MITRE es imprescindible.
   Con `[5]` real, si NERIS tiene escaneo lateral, DEBERÍA dispararse.

5. **5.2c — Auditar `extract_level3_traffic_features`** (~línea 347). El único extractor
   sin auditar. Completa el ranking.

6. **0.3 — Distribución de `authoritative_source`** sobre un `detector.log` de pcap relay
   existente. Cuantifica fast-path vs L1 en el veredicto (ya sabemos que no hay más
   contribuyentes). Log ya existe (línea 428, `[DUAL-SCORE] ... source={}`).

## Flanco abierto (no urgente, anotar)
Las cabezas no cambian `final_classification`, pero `threat_category` ("RANSOMWARE",
"SUSPICIOUS_INTERNAL") SÍ viaja al bronce/firewall. ¿Algún consumidor río abajo actúa
sobre `threat_category`? Rastrear quién la lee antes de afirmar "las cabezas no sirven
para nada": sirven para etiquetar, aunque no para el veredicto binario.

## Estado emocional / ritmo (para Claude, contexto)
Alonso cerró el día golpeado por descubrir bugs longevos pese a la vigilancia adversaria.
Decisión sana: NO publicar en LinkedIn hoy. Encuadre correcto para retomar: los bugs
existían igual ayer; descubrirlos 6 semanas antes del go/no-go (1 ago) con margen para la
verdad es la vigilancia FUNCIONANDO, no fallando. El escudo protege a hospitales/pymes
igual — se apoya en fast-path+L1, no en las cabezas rotas. No dejar que el cansancio
convierta "descubrimos trabajo que ya existía" en "nos impusimos una losa".

## Punteros
- `PLAN DE CAMPAÑA -- Medicion fast-path vs ml-detector...md` — FUENTE DE VERDAD. H1–H7,
  fases 0–5, criterios de parada.
- `ml-detector/src/zmq_handler.cpp` — `process_event` 322–880. Veredicto en 406/432.
- `ml-detector/src/feature_extractor.cpp` — 4 extractores. Internal 404–448 (8/10 sano).
- `ml-detector/config/ml_detector_config.json` — las 4 cabezas `enabled:true` (pero
  desconectadas del veredicto).
- Paper: arXiv:2604.04952 — PENDIENTE de corregir narrativa tricapa→monocapa (Camino A).

*Via Appia Quality — medir quién clasifica, no solo cómo de bien. Un escudo que conoce
sus propias sombras, incluida la sombra entre su código y su diagrama.*