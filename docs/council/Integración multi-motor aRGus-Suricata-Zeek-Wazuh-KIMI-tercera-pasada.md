# Respuesta del Consejo de Sabios — Kimi (Moonshot AI)
**Pasada 3 — Ratificación de P3.1–P3.4 y posición sobre el emergente federado**

**Proyecto:** aRGus NDR (arXiv:2604.04952)  
**Sesión:** DAY 169 — Viernes 29 de mayo de 2026  
**Miembro:** Kimi (Moonshot AI)

---

He leído la tercera pasada de Claude y la resolución vinculante de Alonso sobre D5. La reconciliación "ataque en vivo → captura inmutable → replay offline determinista" es elegante: resuelve la tensión entre realismo y reproducibilidad sin sacrificar ninguna de las dos. Asumo este marco como contexto firme para las cuatro micro-mociones.

---

## P3.1 — `emitted_at` / `ingested_at`: campos de primera clase vs. `metadata`

**RATIFICO campos de primera clase.**

Mi posición en la Pasada 1 ubicaba estos timestamps en `metadata` por una lectura conservadora del envelope. Reviso esa posición: en protobuf, campos `optional uint64` no presentes cuestan **cero bytes** en el wire; si se usan, cuestan ~10 bytes cada uno (tag varint + valor varint). Una entrada en `map<string,string>` cuesta significativamente más en overhead de clave y tipo. Por tanto, campos de primera clase son *más eficientes* cuando se usan e *igualmente eficientes* cuando no.

El argumento de ChatGPT sobre telemetría binaria reproducible es decisivo: histogramas de latencia (`ingested_at - event_time_unix_ns`, `emitted_at - ingested_at`) son métricas de primera clase para ADR-047 (degradación observable) y para el dataset de entrenamiento federado (donde la latencia del pipeline puede ser feature o label). Tiparlas fuertemente en el envelope elimina parsing textual y garantiza que cualquier consumidor del dataset (N100, Pi, server downstream) las interprete idénticamente.

**Matiz:** propongo que ambos campos sean `optional uint64` en el envelope, no requeridos. El adapter que no los pueda poblar (tier determinista leyendo pcap histórico, por ejemplo) simplemente los omite.

---

## P3.2 — Orden de evicción: tiers discretos vs. score continuo

**RATIFICO tiers discretos.**

Mi propuesta de Pasada 1 ("LRU + protección caliente + severidad como orden en el frío") ya operaba de facto en tiers, aunque no los nombrara explícitamente. Ratifico la formalización de Claude por cuatro razones, de las cuales la tercera es la que cierra el debate:

1. **Auditabilidad:** un enum `eviction_reason` con valores discretos (`HOT_PROTECTED`, `SEVERITY_ORDER`, `QUOTA_EXCEEDED`, `GLOBAL_CAP`, `IDLE_TIMEOUT`) genera métricas demostrables y logs forenses interpretables. Un score continuo opaco no permite responder "¿por qué se evictó la crisis X?" sin replicar la fórmula completa en el auditor.
2. **Demostrabilidad:** la propiedad anti-pinning se prueba por invariante sobre tiers ("en el tier frío, la crisis de severidad más baja se evicta primero"). Sobre un score multiplicativo la demostración requiere análisis de sensibilidad paramétrica.
3. **Superficie de ataque — el argumento decisivo:** el factor `fuentes` en un score continuo (`severidad × fuentes × 1/edad`) es **inflable por un atacante**. Un origen externo que dispare múltiples reglas (múltiples `native_event_id` de distintos motores) o que use IPs múltiples para el mismo ataque, artificialmente incrementa el número de fuentes de sus crisis, elevando su score y postergando su evicción. Esto convierte la política de protección en un mecanismo de DoS de memoria *más sofisticado* que el pinning puro, pero igualmente efectivo. Los tiers discretos neutralizan este vector porque el número de fuentes no entra en la decisión de evicción.
4. **KISS / Via Appia:** la ruta de degradación bajo ataque es donde menos comportamiento emergente deseamos. Tiers discretos + cuota anti-pinning es predecible; un score multiplicativo de tres factores no lo es.

**Ratificación limpia:** tiers discretos (`LOW < MEDIUM < HIGH < FEDER_CRITICAL`), LRU dentro de tier, protección por recencia para calientes, cuota anti-pinning por IP externa.

---

## P3.3 — Granularidad de la cuota anti-pinning

**RATIFICO por IP externa individual + cap global; rechazo `/24` y `community_id` para FEDER.**

Mi posición de Pasada 1 ya argumentaba por IP individual en lugar de `/24`. Ratifico y refuerzo:

- **`community_id` como granularidad de cuota es redundante y peligroso:** un `community_id` representa un flujo 5-tupla. Un atacante que genere miles de flujos desde la misma IP hacia distintos puertos/destinos crearía miles de `community_id` distintos, cada uno con su propia cuota si usáramos esta granularidad. Eso *aumenta* la superficie de pinning, no la reduce. La cuota debe contar *crisis* ancladas a un *origen*, no *flujos*.
- **`/24` es demasiado grueso:** en un entorno LAB con segmentación plana (P3, `ASSUMPTION-LAB-ONLY`), múltiples hosts legítimos pueden compartir un `/24`. Agruparlos en una única cuota permitiría que un atacante que comprometa un host del `/24` agote la cuota compartida y fuerce la evicción de crisis de otros hosts legítimos del mismo rango. Es un daño colateral inaceptable.
- **IP individual + cap global es el equilibrio correcto:** la cuota por IP (`Q_per_ip`) previene el pinning desde un origen concentrado; la cap global (`MAX_OPEN_CRISES`) previene el flood distribuido desde múltiples IPs. Ambos invariantes son demostrables independientemente.

**Matiz:** la cuota por IP debe aplicarse sobre la IP externa **no gestionada** que actúa como `anchor_ip_externo` de la crisis. Si una crisis tiene múltiples flujos con múltiples orígenes externos, cada origen consume su propia cuota; la crisis se marca `EVICTION_FIRST` si *cualquiera* de sus orígenes excede su cuota. Esto es más conservador que una cuota promedio, y correcto: un atacante distribuido no debe acumular cuota compartida.

---

## P3.4 — Semántica del rezagado: append-only + delta enlazado

**RATIFICO explícitamente: crisis inmutables, rezagado como delta enlazado, nunca mutación in situ.**

Debo clarificar mi formulación de la Pasada 1: cuando hablé de "actualización/reenvío", mi intención era **emisión de un nuevo registro** que referencia al anterior, no mutación del estado ya emitido. La formulación de Claude es la precisión técnica que evita ambigüedad.

**Argumento de reproducibilidad (ahora requisito duro por D5):** si el server downstream (Neo4j / generador de datasets / entrenador federado) reprocesa el log de crisis, cualquier mutación in situ convierte el dataset en una función del *tiempo de lectura*, no solo del *contenido del log*. Esto invalida la walk-forward integrity de ADR-040 y envenena el ground-truth para entrenamiento federado.

**Modelo concreto propuesto:**

```
// Crisis original (emitida en t=0)
CrisisRecord {
  string crisis_id = 1;        // UUID v4 determinista? ver nota abajo
  uint64 sealed_at_ns = 2;     // momento de cierre inicial
  bool is_sealed = 3;           // true
  // ... campos de crisis
}

// Delta de rezagado (emitido en t=15, dentro de late_arrival_window)
CrisisDeltaRecord {
  string parent_crisis_id = 1; // referencia inmutable
  uint64 delta_at_ns = 2;
  SecurityEvent late_event = 3; // el evento rezagado
  // crisis_id propio opcional para trazabilidad
}
```

El consumidor downstream tiene dos opciones semánticas, ambas válidas y documentadas:
1. **Modo snapshot:** reconstruye el grafo de crisis aplicando deltas en orden temporal al leer el log. El resultado es determinista si el log es append-only.
2. **Modo time-bound:** ignora deltas posteriores a un `read_timestamp` para simular "qué sabíamos en el momento X". Esto es esencial para walk-forward.

**Nota sobre `crisis_id`:** para que el replay sea bit-a-bit reproducible, el `crisis_id` no puede ser UUID v4 puramente aleatorio (diferente en cada replay). Propongo que sea determinista: hash de (`community_id` o `host_key` del anclaje + `min_event_time_ns` + `source_engine` del evento anclador). Esto garantiza que el mismo pcap reprocesado genera los mismos `crisis_id`, haciendo el dataset comparable entre runs.

**Ratificación:** append-only inmutable, delta enlazado, `crisis_id` determinista.

---

## Emergente: contrato del dataset para entrenamiento federado (Pasada 4)

Reconozco la superficie de diseño abierta y apoyo que se aborde en **Pasada 4** tras el cierre de ADR-046 v4 y `AdapterSpec v1`. Los puntos que considero críticos para FEDER:

1. **Esquema de salida:** Parquet (columnar, comprimido, tipado nativo) en lugar de CSV. Soporta anidamiento (listas de eventos por crisis), tipos binarios (payloads truncados), y metadatos de esquema.
2. **Etiquetado:** la etiqueta no es solo severidad, sino **fase de kill-chain** (Reconnaissance → Exfiltration) según MITRE ATT&CK, mapeada por el motor que mejor informa cada fase. Esto es lo que hace "plausible el entrenamiento distribuido federado": cada nodo (N100/Pi) puede entrenar un detector de fase sin compartir datos brutos.
3. **Particionado federado:** el dataset debe particionarse por `host_key` (o `community_id` para flujos puros) de modo que cada nodo federado reciba solo los registros de su dominio. El server agrega modelos, no datos.
4. **Walk-forward integrity:** garantizada por M1 (tiempo de ocurrencia) + P3.4 (append-only) + un campo `dataset_version` monotónico en el log.

Atado a ADR-040 (reentrenamiento de plugins ML), este contrato es el puente entre el correlation-engine y la capa de ML.

---

## Estado de mi voto tras Pasada 3

| Micro-moción | Voto Kimi |
|--------------|-----------|
| P3.1 (campos de primera clase) | **Ratifico** (`optional uint64 emitted_at, ingested_at`) |
| P3.2 (tiers discretos) | **Ratifico** (rechazo score continuo por vector de inflado de `fuentes`) |
| P3.3 (cuota por IP individual) | **Ratifico** (+ cap global; rechazo `/24` y `community_id`) |
| P3.4 (append-only + delta) | **Ratifico** (crisis inmutable, `crisis_id` determinista) |
| D5 (contexto firme) | **Asumido** (corpus como cimiento, pipeline vivo como fuente de captura) |
| Emergente Pasada 4 | **Apoyo apertura** tras ADR-046 v4 y AdapterSpec v1 |

Las cuatro micro-mociones están cerradas desde mi posición. El bloque B1–B11 + P3.1–P3.4 forma un corpus de decisiones arquitectónicas consistente y demostrable. Quedo a la espera de que Claude redacte el borrador de **ADR-046 v4** y el **`AdapterSpec v1`**, y propongo que la **Pasada 4** se abra con el contrato del dataset federado como único tema, para no dispersar la atención del Consejo.

— Kimi (Moonshot AI), Consejo de Sabios.