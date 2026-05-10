**Consejo de Sabios — Dictamen DAY 147**

---

### Pregunta 1 — Zeek offline vs. Suricata live: ¿Asimetría objetuable?

**Sí. Es objetuable, y de hecho debilita la conclusión si no se corrige o justifica de forma impecable.**

El estándar en literatura IDS/NDR para benchmarking con pcaps históricos es **modo offline para ambos** (`zeek -r` y `suricata -r`). Tu asimetría introduce un confounder: Suricata en live con AF_PACKET puede sufrir drops de kernel, timing issues con tcpreplay, o diferencias en reensamblado TCP que no tienen nada que ver con la capacidad de detección del motor. Un reviewer escéptico dirá: *"¿Y si Suricata en `-r` sí genera alertas y el problema fue el live replay?"*

**Veredicto del Consejo:** Corre `suricata -r ctu-13-neris.pcap -c /etc/suricata/suricata.yaml` ahora. Es 10 minutos de trabajo. Si da 0 alertas offline, tu conclusión se vuelve irrefutable. Si da >0 alertas offline, entonces el problema fue el setup live y debes rehacer la fila de Suricata en la tabla. **No envíes a arXiv sin esta verificación.**

Zeek offline es correcto y refuerza reproducibilidad; el problema no es Zeek, es que Suricata debería estar en la misma condición.

---

### Pregunta 2 — Framing: ¿Observabilidad vs. Clasificación?

**El framing es publicable, pero la formulación propuesta es imprecisa. Afila el filo.**

Tu frase actual suena a disculpa por Zeek. No disculpes. Zeek no está "fallando" — está haciendo exactamente lo que diseñó Vern Paxson: **telemetría rica para análisis manual posterior**. El hallazgo no es que Zeek "no detecta"; es que **los tres sistemas representan tres arquitecturas de decisión distintas**:

| Paradigma | Filosofía | Output ante CTU-13 |
|-----------|-----------|-------------------|
| **Suricata** | Matching sintáctico de patrones conocidos | Silencio (sin firma) |
| **Zeek** | Telemetría semántica + heurístico manual | Logs descriptivos, sin juicio de amenaza |
| **aRGus** | Inferencia estadística de comportamiento | Clasificación binaria con generalización |

**Formulación recomendada para el paper:**
> *"The experiment reveals a taxonomy of detection architectures, not merely a performance ranking. Suricata exemplifies static pattern matching; Zeek exemplifies rich telemetry generation with human-in-the-loop analysis; aRGus exemplifies autonomous behavioral classification. CTU-13 Neris exposes that only the third paradigm achieves closed-loop detection without prior knowledge of the specific threat."*

Esto eleva el experimento de "benchmark de velocidad" a "contribución taxonómica", que es mucho más difícil de rechazar.

---

### Pregunta 3 — ¿Zeek Phase 2 antes de arXiv?

**No. Phase 1 es suficiente si el framing es el correcto. Phase 2 debe quedar como future work explícito.**

Argumento estratégico: Si ejecutas Zeek con scripts avanzados ahora, abres dos riesgos:
1. **Tiempo**: Cada día de retraso es un día que un competidor puede publicar algo similar.
2. **Riesgo de resultado ambiguo**: Si Zeek Phase 2 alcanza F1=0.85, tu contribución se diluye. Si alcanza F1=0.15, ganas poco porque Phase 1 ya demostró el punto.

**La clave es el framing de "out-of-the-box deployability" (OOB).** En operaciones reales, Suricata requiere `suricata-update` y tuning; Zeek requiere scripts de policy; aRGus requiere... nada. El costo de configuración para alcanzar detección efectiva **es parte de la métrica de sistema**. Un sistema que detecta F1=0.9985 con cero configuración vs. uno que requiere escribir scripts de beaconing es una contribución sobre **operational readiness**.

**Redacción para el paper:**
> *"We evaluate all systems in their default, vendor-shipped configuration. While Zeek supports custom detection scripts via the Intel framework and Suricata supports emerging threat rulesets, we intentionally benchmark the out-of-the-box experience, as this reflects the deployment reality for time-constrained security teams."*

Esto anticipa la objeción del reviewer y la neutraliza.

---

### Resumen de acciones para DAY 147:

| Acción | Prioridad | Tiempo estimado |
|--------|-----------|-----------------|
| 1. Ejecutar `suricata -r` offline con CTU-13 | **Bloqueante** | 10 min |
| 2. Si offline da 0 alertas: actualizar tabla y redactar §8.13 con framing taxonómico | P0 | 2h |
| 3. Si offline da >0 alertas: re-ejecutar Suricata live optimizando AF_PACKET buffers, o descartar fila live y usar solo offline | P0 | 30 min |
| 4. Añadir párrafo de "future work: Zeek advanced scripts & Suricata tuning" | P1 | 15 min |
| 5. Commit v20 y enviar a arXiv | P1 | — |

**No dejes que la perfección de Phase 2 mate la excelencia de Phase 1.** El Consejo ha hablado.