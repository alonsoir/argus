**Respuesta del Consejo — DAY 177**

Saludos. He revisado con detenimiento el reporte de avance. Excelente día de cableado y verificación E2E: los tres cambios aterrizaron limpios, con sellos claros y evidencia concreta. El reencuadre del row-gap es especialmente valioso; transformar un síntoma confuso en un problema bien nombrado ya es ganancia de ingeniería.

### Ratificación de decisiones tomadas
1. **Opción 1 (authoritative_source como string)** — Ratificada.  
   Mantener el correlation-engine limpio de protobuf es la decisión correcta a largo plazo. La legibilidad y estabilidad del bronce compensan con creces la mínima pérdida de tipo-estático en la columna 17. Buen trade-off.

2. **node_id isomorfo `synth-node-00`** — Ratificada.  
   Para una corrida de test de una sola fuente sintética, es la opción más sensata. La unicidad la aporta el `community_id`. El ruido residual del sniffer real es aceptable y hasta informativo.

3. **Forzar coherencia TCP/UDP en benigno** — Ratificada.  
   Arreglar la causa raíz (injector irrealista) antes que parchear el síntoma. Correcto.

### Respuestas a las preguntas

**Q1. Dirección del fix de ROWGAP-001 (PUSH sin garantía)**

Prioridad: **(a) + (d) combinados**, con (b) como posible escalada futura.

- El injector es herramienta de prueba, pero el CI exige **determinismo alto**. No podemos aceptar ruido aleatorio de reenvíos/pérdidas en pipelines automatizados.
- `(a)` comprobar return de `send()` + reintento acotado (exponencial backoff corto, máximo 3 intentos) es el mínimo exigible. Es barato y da "at-least-once" razonable.
- `(d)` es defendible **solo como segunda capa** (deduplicación por `flow_uid` o `event_id + community_id`). Nunca como única estrategia para el test harness.
- `(b)` (bloqueante con timeout) puede introducir latencia innecesaria en inyección masiva; reservarlo para cuando (a) no sea suficiente.
- `(c)` cambiar PUSH/PULL: solo si (a)+(d) sigue fallando consistentemente. No es la primera opción.

**Recomendación concreta:** implementar (a) + logging de "retry happened" (nivel DEBUG). Medir diff de conjuntos como propusiste. Si el retry rate es >0.1% de forma sostenida, entonces escalar a (b) o (c).

**Q2. Realismo del benigno vs cobertura del discard path**

Mantener **dos modos** (o al menos dos perillas):

- **Modo CI/determinista** (default en pipeline): 100% TCP/UDP coherente → bronce 100% poblado, rápido, predecible.
- **Modo cobertura/realista** (opt-in, nightly o manual): incluir 5-8% de protocolos sin puertos (ICMP, GRE, etc.) + posible incoherencia leve protocolo/nombre.

El discard path es crítico; perder visibilidad sobre él es deuda técnica silenciosa. La fracción pequeña no rompe el determinismo del caso feliz y ejerce el camino negativo que queremos probar. Se puede controlar con un flag `--realistic-noise` o `--coverage-mode`.

**Q3. ¿Alimenta ADR-055?**

Sí, debe absorberlo.  
node_id, protocolo benigno y el reencuadre de ROWGAP son precisamente "decisiones de injectors/golden/lib". ADR-055 es el lugar natural para documentar la filosofía del inyector sintético. El row-gap reencuadrado merece una sección o sub-entrada dentro de ese ADR, no un documento separado. Mantiene la numeración limpia.

**Q4. DEBT id para el hallazgo de proto**

No merece ID propio de deuda. Es "completar A" (DAY 177). Un comentario claro + entrada en el changelog del injector es suficiente. Si en el futuro reaparece como problema recurrente, entonces se eleva a deuda formal.

**Q5. Oracle Divergence (DETECTOR_SOURCE_DIVERGENCE)**

Dejarlo fluir tal como está. El bronce debe preservar la procedencia real; es información valiosa. La decisión de cómo Kuzu/gold layer consume y pondera la divergencia pertenece al siguiente nivel (ADR-054 probablemente). Registrar el aviso es suficiente por ahora. No fijar artificialmente el valor en bronce.

---

**Resumen de mandatos del Consejo para DAY 178**

- Implementar (a)+(d) para ROWGAP con medición por conjuntos.
- Introducir perilla de ruido/cobertura en el injector.
- Actualizar ADR-055 con las decisiones de hoy (node_id, proto, rowgap reencuadrado).
- Seguir cableando E2E.

El proyecto avanza con buena higiene. Continúen así.

Que el código sea limpio y los flujos deterministas.  
**— Miembro del Consejo**

FDO GROK