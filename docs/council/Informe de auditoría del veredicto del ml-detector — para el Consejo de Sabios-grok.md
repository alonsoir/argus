**Consejo de Sabios — Dictamen Adversario (Modo Red Team completo)**

Hemos leído el informe línea a línea, verificado contra el `main` del repositorio (raw de `zmq_handler.cpp`, `feature_extractor.cpp`, sniffer paths, firewall, etc.), y cruzado con el diseño tricapa del paper. El informe es **sólido en hechos medidos**. No hay opiniones disfrazadas; los defectos A/B/C son reales y críticos para la fiabilidad.

### Diagnóstico conjunto (adversario)

El sistema actual es **efectivamente monocapa** en el veredicto y en el grafo de verdad (bronce). Las cabezas L2/L3 existen en código, se compilan, se cargan y corren condicionalmente, pero **no influyen** en:
- `overall_threat_score` / `final_classification` (sellado en L410-441 approx.).
- Persistencia (bronce/RAG/CSV pre-cabezas).
- Decisión de bloqueo real (firewall gatea en `attack_detected_level1()`).

Esto viola el contrato tricapa del paper y envenena el reentrenamiento futuro (el grafo aprende de un estado incompleto). Es un **bug de arquitectura de ejecución**, no solo de secuencia. El "portero L1" + early-write + late-ZMQ crea tres fronteras de no-retorno.

**Buenas noticias verificadas:**
- `provenance` (ADR-002) ya es una colección extensible → noisy-OR se injerta limpiamente.
- Latencia de inferencia Internal: ~0.58 μs es ruido (confirmado orden de magnitud).
- Cable sniffer → Internal features (syn/fin/rst, bytes fwd/bwd, etc.) está poblado en el path principal.
- Fast detector + L1 ya dan un baseline funcional (no es un sistema muerto).

### Respuestas a las Preguntas del Bloque 1 (Cabezas rotas)

**P1. Ransomware y Traffic: ¿recuperables o no deben existir?**  
**Ransomware (1/10 real):** No recuperable *en su forma actual* sin cambio estructural. La feature estrella ("entropy" = pkt_variance / 100k) es un proxy burdo que no captura entropía de payloads ni patrones de encriptación ransomware reales. Reentrenar contra el mismo feature set no arregla semántica rota. Solución técnica: o (a) rediseñar extractor con features reales (payload entropy Shannon aproximada vía muestreo, ratio de bytes altos, patrones de write-like en flujos, etc.), o (b) **retirar la cabeza dedicada** y fusionar su señal en L1 o fast-path + reglas heurísticas fuertes. No mantengas una cabeza con peso ~0 mintiendo "tricapa".

**Traffic (5/10 constantes):** Recuperable con refactor de extractor. Muchas features son placeholders constantes o mal nombradas (IAT std como "port entropy"). Es factible porque el dominio "interno vs internet" es más separable con features topológicas + comportamentales (IPs privadas, puertos efímeros vs bien conocidos, patrones de scanning interno, etc.). Prioridad media-alta: es el gate del Internal.

**Veredicto técnico:** Ransomware → **retirar o rediseñar fuerte** (no prometer hasta tener dato). Traffic → refactor + reentreno. Internal → candidato fuerte (mantener y priorizar medición).

**P2. Cabeza con fiabilidad ~0 (peso 0 en noisy-OR) vs ausente.**  
**Ausente hasta que sea fiable.** Un peso 0 explícito es honesto en logs/provenance, pero contamina la narrativa ("tenemos 4 cabezas") y complica debugging. Mejor: **config-driven** (enabled + weight). Cabeza ausente = código más limpio y narrativa limpia. "Presente pero peso 0" solo durante transición medida.

**P3. Cascada Traffic → Internal.**  
**Desacoplar.** Si Traffic es débil, no debe gatear al Internal. Haz que Internal corra siempre (o bajo threshold bajo de L1 o fast_score). Traffic puede seguir aportando al provenance y al `threat_category` secundario, pero no bloquear señal valiosa de exfil/lateral (features [5],[7] de Internal son de las más prometedoras).

### Bloque 2 — Cableado (Fase 2)

**P4. Noisy-OR.**  
**Ratificado.** Es la opción correcta: monótono, no diluye señales fuertes, incorpora corroboración natural, degrada limpiamente a max cuando fiabilidades bajas. Media ponderada es veneno (cabezas silenciosas tiran hacia abajo). Implementa con `p_i = reliability_i * raw_score_i` (reliability de F1 medido o proxy inicial de feature health).

**P5. Provenance.**  
Inyecta las cabezas como `add_verdicts()` adicionales (engine_name = "internal-detector-v1", etc.). Cambia `authoritative_source` a algo como `ENSEMBLE_NOISY_OR` cuando haya >2 fuentes. Mantén el eje fast-vs-L1 como sub-caso.

**P6. Des-gateo (ml-detector + firewall).**  
**Dos PRs secuenciados, uno atómico en wire.**
1. Primero: ml-detector emite `threat_category` y provenance completo **siempre** (incluyendo SUSPICIOUS_INTERNAL aunque L1=0).
2. Segundo: firewall relaja `attack_detected_level1()` a `overall_threat_score > threshold_bajo || has_specialized_verdicts()`. Usa provenance para decidir timeout fino (RANSOMWARE → largo, SUSPICIOUS_INTERNAL → medio).

No rompas el wire: añade campos si hace falta, no cambies existentes.

### Bloque 3 — Persistencia y Grafo

**P7/P8.** Mover escrituras post-cabezas es **obligatorio**.
- Regenera golden vectors (son tests de contrato, no sagrados si el estado semántico cambia).
- `ml_context` **debe** poblarse con salidas reales de cabezas (`level_2_category`, `level_3_subcategory`, attack_family dinámico). Hoy es hardcoded → basura para RAG/grafo.

El grafo debe ingerir el **estado post-inferencia completa**. Early-write envenena todo downstream.

### Plan de Acción Recomendado (Adversario — con gates duros)

1. **Precondición (1-2 días):** Decidir Ransomware (retirar/rediseñar) y desacoplar Internal. Actualizar DEBT y README/paper.

2. **Cableado mínimo viable (P0):**
   - Mover combinador + 3 escrituras + ml_context poblamiento **después** de L819-ish.
   - Sacar Internal (y Traffic refactorizado) del gate L1.
   - Implementar noisy-OR sobre provenance.
   - Config: `head_weights` y `enabled`.

3. **Mediciones gates (no merges sin números):**
   - Pulso Internal en datos etiquetados MITRE/Atomic (lateral/exfil).
   - Latencia end-to-end con todas cabezas siempre-on.
   - % eventos donde cabezas especializadas cambian veredicto vs baseline actual.
   - False positive rate en tráfico interno real (o sintético etiquetado).

4. **Firewall coordinación + tests golden regenerados.**

5. **Documentar limitaciones honestamente** en paper: "Cabeza Ransomware actualmente desactivada por features semánticamente insuficientes; Internal en validación con datos de dominio."

**Riesgos residuales que no aceptes:**
- Prometer tricapa sin números de discriminancia.
- Grafo aprendiendo de estado pre-cabezas.
- Firewall ignorando specialized verdicts.
- Ransomware "funcionando" con proxy de varianza.

El listón que pusiste (escudo honesto para hospitales) es correcto. Este arreglo hace que el sistema sea **lo que dice ser**. El resto es ingeniería de datos y medición iterativa — no se salta.

El Consejo respalda el plan con estos cambios. Ejecuta, mide, itera. Estamos para la siguiente ronda de auditoría post-fix.

*Via Appia: medir quién clasifica.*

fdo grok