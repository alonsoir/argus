**CLAUDE — CONSEJO DAY 148**

---

**P1 — VALIDEZ DEL FRAMING DE COMPLEMENTARIEDAD**

El framing es defendible en el abstract. La afirmación no es empírica — es arquitectónica, y está directamente justificada por los resultados experimentales: los tres sistemas operan en capas distintas (telemetría, firmas, clasificación behavioral) y sus outputs son ortogonales. No hay contradicción lógica en que coexistan. El experimento de tres vías demuestra precisamente que ninguno cubre el espacio del otro.

La distinción importante: no estamos afirmando que *hemos implementado* la integración — estamos afirmando que la integración es *arquitectónicamente natural*. Es una inferencia válida de los datos, no una promesa de implementación. Si un revisor lo cuestiona, la defensa es: "los tres sistemas producen outputs en capas distintas (telemetría estructurada, alertas de firma, clasificación behavioral) que no se solapan — su combinación no requiere demostración empírica adicional más allá de lo que ya mostramos."

Recomendación: mantener en el abstract. La frase es corta, precisa y científicamente honesta.

---

**P2 — ESTRATEGIA DEBT-PARQUET-SCHEMA-001**

(a) **Granularidad: por flow, no por paquete.** El pipeline ya opera a nivel de flow — `Detection` en el proto es por flow. Por paquete sería un cambio de contrato, no una validación. El schema debe reflejar lo que el sistema ya produce.

(b) **Registrar solo alertas/denies en primera versión.** Todos los eventos generaría volúmenes no caracterizados y sin ground truth para Neo4j. El schema P0 es el contrato mínimo viable: lo que dispara el IRP y lo que bloquea el firewall. El schema completo (todos los flows) es P3 post-FEDER.

(c) **Tipos Arrow:**
- Timestamps: `int64` UTC epoch nanoseconds (ya decidido en ADR-0043) — `pa.timestamp('ns', tz='UTC')`
- Scores float: `pa.float32()` — consistente con el fix DAY 148
- IPs: `pa.string()` o `pa.large_utf8()` — no `pa.binary()`, necesitamos legibilidad en Neo4j
- DetectionType enum: `pa.dictionary(pa.int8(), pa.string())` — compacto y legible
- Booleanos (auto_isolate, block): `pa.bool_()`

Estrategia para la sesión: (1) levantar el pipeline en Vagrant, (2) capturar 5-10 minutos de tráfico CTU-13 Neris, (3) examinar los CSVs reales que produce `ml-detector` y `firewall-acl-agent`, (4) mapear cada columna a un tipo Arrow, (5) estimar volumen por nodo por mes con los datos reales.

---

**P3 — PRIORIDAD DAY 149**

Secuencia óptima considerando FEDER deadline y dependencias:

**DAY 149: opción A — DEBT-PARQUET-SCHEMA-001.** Es el P0 bloqueante de ADR-0043, que es el componente diferenciador del FEDER (memoria episódica distribuida). Sin schema validado, el pipeline de ingesta Neo4j no puede avanzar, y Neo4j es la demostración de valor añadido más visible para los evaluadores FEDER. Una sesión, resultado concreto.

**DAY 150-151: opción D — ARM64 scope.** El hardware FEDER (Raspberry Pi 4/5, miniPC) es el argumento central de la propuesta. Tener un scope definido para ARM64 antes del go/no-go técnico (1-Ago) es estratégicamente prioritario. No necesita implementación completa — necesita un ADR con criterios de aceptación medibles.

**DAY 152+: opciones B y C.** Jenkins y Vault son infraestructura de soporte. Importantes pre-FEDER pero no bloquean la demo técnica ni el argumento científico.

**Opción E:** No la recomiendo como día dedicado — pero sí como práctica diaria. Leer feedback arXiv en paralelo a cualquier tarea técnica.

Dependencia crítica que cambia el orden: si Dr. Andrés Caro Lindo solicita una reunión técnica antes del go/no-go, la demo FEDER (`make feder-demo`, DEBT-ADR041-003) sube a P0 inmediato independientemente de cualquier otra tarea.