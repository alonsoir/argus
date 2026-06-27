## 📝 Notas del Consejo de Sabios — DAY 181 (8/8) · ADR-057 (1ª vuelta)

> "DAY 181 — Primera vuelta del Consejo sobre ADR-057 (capa de consulta del grafo, bitemporalidad,
> NL→plantilla). Veredicto agregado: **dirección aprobada por los 8, Fase 0 (`ingested_at`) con luz
> verde unánime, todo lo demás condicionado a medir antes de implementar.** Nadie rechaza el ADR ni
> pide cambiar de rumbo. El Consejo no vota: entrega un paquete de mediciones baratas que disuelven
> casi todas las divergencias. Arbitraje de Alonso en los 5 puntos de juicio.
>
> **El único choque factual — concurrencia de Kuzu — se resuelve midiendo, no votando.**
> Kimi: Kuzu NO permite ni un lector READ_ONLY externo mientras el engine tiene el handle de
> escritura (issues primarios #3295 y #3872, error de lock exacto) → in-process es *físicamente
> obligatorio*, no elegido; propone eliminar el smoke. Qwen: lo contrario (MVCC permite RO
> concurrente, cita `transaction_manager.cpp`). Grok y Mistral matizan: RO+RO sí, RW+RO mezclados no.
> El caso de aRGus es engine con handle RW permanente, que es exactamente el escenario de los issues
> de Kimi. **Resolución [ÁRBITRO]: el smoke se ADELANTA a Fase 0, NO se elimina** — es lo único que
> zanja el desacuerdo Kimi↔Qwen con evidencia. Mide dos cosas distintas que el Consejo mezcló:
> (1) ¿multiproceso RW+RO? (resuelve el choque); (2) ¿contención de lectura in-process bajo carga de
> escritura? (p95 < +20%, escritura no bloqueada >100ms — Qwen) — válida aunque la 1 diga "no", y es
> la de verdad peligrosa (una consulta puede provocar drop de paquetes en el sniffer).
>
> **Corrección al ponente (Claude): el desacople de CLOCK-INJECTION estaba sobrevendido.**
> Cinco modelos convergen: `ingested_at` desacopla el EJE DE TRANSACCIÓN del reloj envenenado del
> sniffer (cierto y valioso), pero NO inmuniza el eje de evento (Gemini: si `flow_start_window` cae
> en el futuro por `bpf_ktime_get_ns()`, `T_v > T_t` = anomalía bitemporal), es first_seen y no
> transaction-time completo (ChatGPT, Kimi: no captura updates; es punto, no intervalo Snodgrass/
> Jensen), y se rompe en replay (Qwen: reflejaría el tiempo del replay). **Enmiendas incorporadas:**
> flag `temporal_anomaly=TRUE` cuando `flow_start_window > ingested_at + margen` (Gemini); jerarquía
> de fuentes — el WAL prevalece en replay, el campo Kuzu es vista del estado actual (Qwen); ns UTC +
> monotonía garantizada ante step NTP (Qwen, Mistral); índice sobre `ingested_at` (Mistral, Qwen).
>
> **Kuzu archivado (Kimi, DeepSeek — CRÍTICO, pero no es rechazo a Kuzu).** Solo 2/8 lo elevan a
> bloqueante; Grok lo defiende activamente; nadie propone abandonarlo. Lo que piden es plan de
> contingencia explícito — que YA EXISTE: `DEBT-KUZU-UPSTREAM-ARCHIVED-001` (P2, DAY 180) + abstracción
> `IGraphSink` + plan B fork `Vela-Engineering/kuzu`. Acción: referenciarlo en el §1 del ADR. El
> catálogo de plantillas queda como frontera de portabilidad — no acumular Cypher nativo fuera de él.
>
> **Catálogo tras arbitraje:** T1 (vecindario, con LIMIT fan-out + timeout obligatorio — un supernode
> explota O(d^n)) · T2 (contexto de alerta) · T3 (densidad de amenaza, acotada por tiempo) ·
> **T4 [ÁRBITRO: acotada y honesta]** (retro-hunt de IOC = apariciones + dos timestamps; NO
> point-in-time) · **T5 ELIMINADA** (7/8, filtro tabular → ORO) · **T6 [ÁRBITRO: sobrevive como
> bridge-ORO]** (la capa enruta a ORO; riesgo de scope creep asumido, condición de muerte si
> benchmark >2× lento vs DuckDB; "aprenderemos") · **T7 [ÁRBITRO: adoptada]** (camino de propagación/
> attack path, shortest path entre Alerts vía CORRELATES_FLOW — ChatGPT, genuinamente graph-native) ·
> T-hist (reconstrucción "a fecha de", futura, depende de DEBT-LABEL-WAL-001).
>
> **NL→plantilla [ÁRBITRO: rechazo duro].** Alonso: "no nos podemos permitir la ambigüedad". Si la
> confianza no supera umbral, rechaza y pide reformular — NO devuelve candidatos (el Consejo estaba
> dividido 5/3 hacia interactivo; el árbitro elige seguridad). El NL se DESACOPLA a ADR propio con
> benchmark obligatorio (convergencia 5/8): TinyLlama es generativo, no clasificador entrenado;
> params estrictos por gramática/regex, LLM solo clasifica la plantilla; umbral a MEDIR con corpus
> etiquetado. Riesgo de jailbreak (Kimi): forzar clasificación a plantilla de menor escrutinio →
> adversarial examples en el benchmark. Firma del catálogo: solo en arranque, no por query (Qwen);
> diferida a Fase 4 con revocación/rotación/TTL (Kimi).
>
> **Plan reordenado:** Fase 0 = `ingested_at` + smoke ADELANTADO (concurrencia + contención +
> monotonía NTP). Fase 1 = catálogo podado in-process con aislamiento de recursos. Fase 2 = benchmark
> T6 vs DuckDB. Fase 3 = NL (ADR propio). Fase 4 = firma + T-hist sobre WAL + smoke de recuperación
> ante corrupción del WAL (ChatGPT).
>
> **Nuevas deudas:** DEBT-NL-BENCHMARK-001 (P2), DEBT-KUZU-CONCURRENCY-SMOKE-001 (P1),
> restore_from_wal_smoke_test (bajo DEBT-LABEL-WAL-001).
>
> **Posiciones registradas:** in-process 8/8 · `ingested_at` Fase 0 8/8 · podar T5 7/8 ·
> NL rechazo-vs-interactivo 3/5 (árbitro: rechazo) · smoke eliminar(Kimi 1) vs adelantar(resto) →
> adelantar. Pendiente para 2ª vuelta o cierre: ejecutar el smoke y adjuntar resultados medidos.
>
> 'No introducir un modelo donde basta una tabla.' — ChatGPT · 'Un escudo que corta sin medir no
> protege: amputa.' — Qwen (reusada) · DAY 181"
> — Consejo de Sabios (8/8) · DAY 181 · ADR-057 1ª vuelta · feature/day170-community-id-protobuf