Aquí van mis respuestas como asiento Claude del Consejo, listas para registrar. Te las doy con el razonamiento, no solo el voto, para que quede traza de por qué — coherente con la honestidad científica del proyecto.

**Q1 — Dirección del fix de ROWGAP-001. Voto: (a) + (d), combinadas.**
El injector es herramienta de test, no el sniffer de producción, así que no le exijo garantías de transporte de grado producción. Y los reenvíos son **inocuos por diseño**: distinto community_id = distinto `flow_uid` = flujo distinto para el bronce y para Kuzu. El dedup por `flow_uid` aguas arriba ya los absorbe — eso es (d), y es defendible. Pero comprobar el return de `send()` cuesta tres líneas y te da gratis la métrica honesta que necesitas para *medir* el gap (saber qué se envió de verdad vs qué se descartó por EAGAIN), así que añado (a). Rechazo (b) y (c) por ahora: cambiar a `send()` bloqueante o reconsiderar PUSH/PULL es resolver con cirugía un problema que el `flow_uid` ya neutraliza, y mete riesgo en un componente de test. Si algún día el patrón PUSH/PULL del injector se promoviera a algo que importe en producción, reabriría (c).

**Q2 — Realismo del benigno vs cobertura del discard path. Voto: dos perillas.**
Modo determinista (100% TCP/UDP) para CI, donde necesitas un bronce reproducible fila a fila; y modo realista-con-ruido (~5% ICMP u otro sin puertos) que **ejercita a propósito** el camino `compute_community_id() == nullopt → community_id vacío → descarte`. Forzar 100% TCP/UDP a secas, como está hoy, deja sin test ese discard path — y justamente hoy hemos visto lo fácil que es que un community_id vacío se cuele sin que nadie lo note (0 filas en bronce y el E2E daba PASSED igual). Ese camino merece cobertura explícita. Implementación sugerida: una env var tipo `ARGUS_PROTO_MIX=deterministic|realistic`, default `deterministic` para no romper CI.

**Q3 — ¿Alimenta ADR-055? Voto: sí, los tres entran en ADR-055.**
node_id, proto benigno y el reencuadre de ROWGAP son todos decisiones de injector/golden, que es exactamente el ámbito que el arranque sembró para ADR-055. No veo razón para fragmentarlo. Matiz: el reencuadre de ROWGAP es lo bastante sustancioso (cambia la naturaleza de la deuda) como para ser una **sección propia dentro de ADR-055**, no una nota al pie. Que ADR-055 documente el hallazgo "PUSH sin control de entrega no es once-only" como parte de la lección de injectors.

**Q4 — DEBT id para el hallazgo de proto. Voto: sí, id propio.**
Aunque nació como "completar A", es un bug de causa raíz con diagnóstico, fix y verificación propios — y además destapó un bug latente (number/name incoherentes). Eso merece traza independiente, no diluirse en "A". Propongo registrarlo como deuda **ya cerrada en el mismo día** (estilo de las que abres y cierras en la jornada), no como deuda viva. El comentario `DAY 177 (A)` en el código que enlace a ese id.

**Q5 — Oracle Divergence en bronce. Voto: dejarlo para el lado consumidor, con una nota ahora.**
Que aparezcan 9 `DETECTOR_SOURCE_DIVERGENCE` confirma que el bronce **preserva** procedencia real (principio "bronce preserva, gold decide") — es buena señal, no algo a arreglar. Cómo se propaga la divergencia hacia Kuzu y cómo pesa en la decisión gold es trabajo del lado consumidor del engine, que aún no está cableado. No lo decidiría hoy. Pero sí dejaría una línea en el día-log: "verificado que `DetectorSource` simbólico transporta DIVERGENCE end-to-end al bronce" — porque es la primera evidencia de que el contrato de col 17 aguanta valores distintos de los detectores nominales.

---

Un apunte de honestidad sobre estos votos, para que lo tengas presente cuando los registres junto a los otros siete: en Q1 y Q2 mi posición se apoya en una premisa que conviene que el Consejo cuestione —**que el injector seguirá siendo siempre herramienta de test**—. Si hay intención de promoverlo a algo con responsabilidad en producción, mis votos de Q1 (d) y Q2 (default laxo) cambiarían hacia más rigor. Si alguno de los otros modelos vota distinto en Q1, probablemente sea porque parte de esa premisa contraria; merece la pena resolver esa premisa antes de contar votos, o estaréis comparando respuestas a preguntas distintas.

¿Quieres que prepare ya el esqueleto de ADR-055 para tenerlo listo cuando vuelvas con el feedback de los siete, o esperamos a tener el consenso antes de redactar nada?

FDO
CLAUDE