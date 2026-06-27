Como **Qwen**, miembro del Consejo de Sabios, aporto la siguiente pasada técnica. He revisado el escrito con rigor, validado las premisas donde corresponde, y respondo punto por punto a las preguntas portantes de diseño. Mi objetivo es desbloquear el contrato `network_security.proto`, blindar la máquina de estados de crisis (ADR-046) y alinear la ejecución con el entregable FEDER.

---

## ✅ Validación de premisas (P1–P5)
- **P1–P2**: Correctas. La especificación `corelight/community-id` exige canonicalización direccional estricta y seed compartido. Confirmo que OpenSSL/libcrypto es la vía estable para SHA1 en entornos Rust/Go/C.
- **P3**: Válida para LAB. Para FEDER/producción, `host_key` debe soportar `agent_id` o `hostname` como fallback cuando NAT/CGNAT rompe la IP estática.
- **P4**: Correcto. NTP/chrony es gate P0. Recomiendo añadir `chronyc tracking` al health-check del cluster.
- **P5**: Correcto. ICMP se difiere formalmente. `DEBT-ARGUSPP-COMMUNITY-ID-ICMP-001` debe quedar firmado como *out-of-scope FEDER*.

---

## 📜 Respuestas a las preguntas (Q1–Q9)

### Q1 — Modelo de claves: ¿PK única o dos claves?
**Posición Qwen:** `community_id` como PK única es insostenible para un NDR moderno que pretende cubrir la kill chain completa. **Adoptar modelo dual**: `flow_key` (`community_id` nullable) + `host_key` (IP interna/`agent_id`/`hostname` nullable).  
**Propuesta de implementación:**
- En `network_security.proto`: campos planos, no `oneof`.
  ```protobuf
  string flow_key = 1;        // community_id o vacío
  string host_key = 2;        // IP interna o agent_id
  string ts_canonical = 3;
  string source_engine = 4;
  string native_event_id = 5;
  EventDomain domain = 6;     // NETWORK | HOST | HYBRID
  ```
- La PK de crisis se genera como `crisis_id = sha256(sorted(flow_key || host_key || ts_bucket))`. Índices separados en `flow_key` y `host_key` para lookup O(1).

### Q2 — Modelo de grafo / abstracción de unión
**Posición Qwen:** Sí, dos tipos de arista, pero con abstracción temporal explícita.  
**Recomendación:**
- Durante la ventana de correlación: **grafo bipartito temporal** `(Evento) —[MISMO_FLUJO]→ (Flujo)` y `(Evento) —[EN_HOST]→ (Host)`.
- El motor de crisis colapsa el subgrafo en un nodo `(:Crisis)` cuando se cumple el umbral de severidad o la ventana expira.
- En Neo4j post-FEDER: `(Crisis)-[:CONTAINS]->(Event)`, `(Crisis)-[:LINKED_FLOW]->(Flow)`, `(Crisis)-[:LINKED_HOST]->(Host)`. Esto permite traversals cruzados sin duplicar lógica de join en tiempo real.

### Q3 — Semántica de `source_wait_timeout` / fuentes esperadas
**Posición Qwen:** Opción **(b) refinada**. Ninguna fuente es "esperada" por defecto. Se calcula dinámicamente por dominio y inventario.  
**Propuesta:**
- `expected_sources = compute_expected(domain, inventory, bridge_window)`
- Si crisis nace de red (`flow_key` presente): Wazuh solo se espera si `host_key` coincide con un endpoint gestionado Y hay una regla Wazuh que cubra el protocolo/puerto en esa IP.
- Si crisis nace de host (`host_key` presente): Suricata/Zeek/aRGus solo se esperan si hay flujos visibles para esa IP en la ventana.
- Timeout adaptativo: `close_when = min(source_wait_timeout, crisis_idle_timeout)`. Si una fuente no aplica, no se cuenta para el cierre.

### Q4 — ¿Wazuh ingiere `eve.json` de Suricata?
**Posición Qwen:** **No**. Cada motor entra por su adapter dedicado. Wazuh no debe actuar como agregador de red. La deduplicación por `(source_engine, native_event_id)` es suficiente y evita fan-out, desincronización de offsets y conteo doble.

### Q5 — Timestamp canónico y tolerancia de reloj
**Posición Qwen:**
- `ts_canonical = source_emission_time` (cuando el motor emite al adapter), normalizado a UTC.
- Preservar `ts_capture` y `ts_event` como metadatos, pero **no** para ventanas de correlación.
- Tolerancia: **≤ 50 ms intra-LAB**, ≥ 200 ms en producción FEDER.
- Gate: NTP/chrony sincronizado + monitorización continua (`drift > threshold → alert + reject merge`). Añadir campo opcional `ts_correction_offset` en el envelope para compensación controlada.

### Q6 — Recursos: 5 VMs simultáneas en M2 Pro 32 GB
**Posición Qwen:** 32 GB es ajustado pero viable para LAB si se **escalonan perfiles**:
- Wazuh manager: 2 GB
- Suricata: 1.5 GB
- Zeek: 1 GB
- aRGus: 1 GB
- Correlation Engine: 2 GB
- Resto: host OS + buffers  
  **Recomendación:** Para EMECAS++ y pruebas de carga, usar **nodo CI dedicado** (GitHub Actions self-hosted / bare metal). En dev local, arranque secuencial + `tmux`/`screen` para validación iterativa. No sacrificar throughput por restricción de RAM.

### Q7 — Cota de crisis abiertas y evicción
**Posición Qwen:**
- Cota dura: **10.000 crisis** (configurable por `MAX_OPEN_CRISIS`).
- Evicción: LRU por `last_activity_ts`, pero **nunca evictar** crisis con `severity >= HIGH` o etiqueta `FEDER_CRITICAL`.
- Degradación (ADR-047): al >80% capacidad, el engine entra en modo `SUMMARY_ONLY`: emite agregados de severidad, mantiene esqueleto de crisis, descarta raw payloads. Nunca bloquea la ingesta.
- Demostración EMECAS++: inyector a 50k flujos/s, monitor `memory_rss`, `open_crisis_count`, `drop_rate`. Verificar meseta y degradación suave.

### Q8 — Alcance de protocolo (ICMP)
**Posición Qwen:** **Firmado**. TCP/UDP/SCTP para FEDER. ICMP diferido a `DEBT-ARGUSPP-COMMUNITY-ID-ICMP-001` con justificación técnica documentada: ausencia de puertos, alta cardinalidad de ruido, baja relación señal/ataque en NDR, y complejidad de canonicalización sin valor proporcional para la entrega actual.

### Q9 — ¿Pipeline vivo o corpus reproducible para el Dr. Caro Lindo?
**Posición Qwen:** **Corpus etiquetado y reproducible primero**, pipeline vivo segundo.  
El entregable académico/FEDER exige *ground truth* verificable. Priorizar:
1. Golden PCAP con `community_id` precalculados y etiquetas de ataque/mitigación.
2. Pipeline determinista que replaya el PCAP y genera el mismo grafo de crisis en cada ejecución.
3. Validación EMECAS++ sobre corpus, no sobre tráfico vivo.  
   El pipeline en vivo se mantiene arquitectónicamente compatible, pero no bloquea la entrega del 22-sep. Esto invierte el orden de fases como anticipaste: reproducibilidad → Fase 0/1.

---

## 🧱 Notas arquitectónicas adicionales

1. **Inventario de hosts como servicio primero-class:** No un YAML. Debe ser un endpoint gRPC/HTTP que exponga `IP ↔ agent_id ↔ hostname ↔ managed_since`. El engine de crisis lo consulta en caliente para decidir `expected_sources`.
2. **Adapter contract antes de código:** Definir `AdapterSpec v1`: offset persistence (SQLite/leveldb), exactly-once semantics idempotentes, retry con backoff exponencial, y health endpoint. Tail de `eve.json` con `inotify` + `atomic rename` para rotación segura.
3. **Envelope flat vs union:** Evitar `oneof` en protobuf para este caso. Los motores de streaming (Redpanda/Kafka/Redis) y los query engines (Neo4j, ClickHouse) optimizan mal `oneof`. Campos nullable + `domain` enum es más predecible.
4. **Ventana de puente host↔flujo:** Definir `bridge_window = 15s` (ajustable). Un evento host y un evento flujo se unen si comparten IP interna y `|ts_host - ts_flow| ≤ bridge_window`. Fuera de ventana, no se fuerzan joins.

---

## 📅 Alineación con fases propuestas (ajustado a Q9)

| Fase | Entregable | Condicionante Q9 |
|------|------------|------------------|
| 0    | `network_security.proto` + golden PCAP + baseline labels | Corpus-first |
| 1    | Adapter Suricata + replay determinista | Validación cross-engine con PCAP |
| 2    | Adapter Zeek + aserción `community_id` idéntico | Golden test inmune a ruido |
| 3    | Adapter Wazuh + clasificación flow/host + inventory service | Puente IP↔endpoint validado |
| 4    | Fusión + máquina de estados v4 + timeout adaptativo | EMECAS++ sobre corpus |
| 5    | E2E FEDER + métricas de degradación + corpus etiquetado | Entrega 22-sep cumplida |

---

## 🔚 Cierre

Coincido con Claude en que el riesgo real no es la implementación de `community_id`, sino la **incompatibilidad estructural** de usarlo como PK única cuando uno de los cuatro motores opera fuera del dominio de red. El modelo dual, la semántica adaptativa de fuentes esperadas, y el enfoque corpus-first para FEDER blindan la arquitectura sin sobrecargar el contrato wire.

Quedo a disposición para iterar sobre el `network_security.proto`, revisar la especificación de la máquina de estados (ADR-046 v4), o validar el inyector EMECAS++ contra el golden set.

**— Qwen, Consejo de Sabios**  
*Firma técnica disponible bajo demanda. Piano, piano.* 🕊️