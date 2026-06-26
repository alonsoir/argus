# PROMPT DE CONTINUIDAD — DAY 197 (continúa DAY 196)

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria; trazar hacia atrás desde el binario.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable durable; Kuzu = proyección reconstruible).
- **EMECAS++** antes de cualquier merge · **PR obligatorio** (commit de doc no pasa el gate de build).
- **Consejo de Sabios** (8 modelos: Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral) ratifica decisiones de arquitectura.
- Un día, una batalla.

## Estado al cierre de DAY 196
- **Plan completo escrito:** `PLAN-CIRCUITO-COMPLETO-DAY196.md` — pendiente de revisión del Consejo.
- **Objetivo del circuito:** completar aguas abajo (adapters → bronce → LZ medallón → Kuzu → dashboard) como **instrumento de medición** ANTES de tocar ML / mecanismo MITRE. ML asumido roto (`DEBT-RANSOMWARE-ML-HEAD-INERT-001`).
- **Nomenclatura cerrada:** `AdapterSpec v1` = contrato de **comportamiento** de ingesta (at-least-once, dedup `(source_engine,native_event_id)`, checkpoint, ZMQ §7.1) ≠ `correlation_v1` = contrato de **dato** (19 cols CSV+HMAC, bronce). "AspectV1" = corrupción de AdapterSpec; no existe.
- **[MEDIDO]** El envelope protobuf `SecurityEvent` de AdapterSpec §3 **NO existe**; el proto solo tiene `NetworkSecurityEvent` (L569). Salida real al cable = `correlation_v1` CSV+HMAC, **nunca protobuf**. → enmienda AdapterSpec v1.1 (`DEBT-ADAPTERSPEC-ENVELOPE-001`).
- **[MEDIDO]** `correlation-engine` lee bronce CSV por `ifstream` (chapu interina); `kuzu_graph_sink` existe y lee bronce **directo**. Medallón de correlación = **greenfield**.
- **[MEDIDO]** `scripts/parquet/` existe pero es del **RAG-127/Ed25519** (capa distinta, NO correlación). → `DEBT-DOCS-MEDALLION-DUALITY-001`. Reutilizar **patrones** (centinela→null, roundtrip, dictionary, timestamp-ns-en-origen), no código.
- **[MEDIDO]** `adapter-argus` = **NO-OP**: `correlation_writer` (en ml-detector) ya escribe bronce.
- **Tabla de mapeo por motor:** resuelta (§4 del plan). `source_sensor` constante; `community_id` nativo argus/suri/zeek (join flujo↔flujo, validado ADR-051); Wazuh host-domain (join por IP, **NO** community_id — `host_key` ≠ community_id).
- **Centinela:** `-1` numéricas / `UNKNOWN` strings en CSV → `null` tipado en parquet (precedente DAY 148, `SENTINEL=-9999.0`→None).

## Decisión VIVA para el Consejo (única abierta)
**Forma del oro** (§10.2): oro-como-join (arrow funde por community_id) vs **oro-como-ledger** (Kuzu une).
**LEAN:** ledger + join en Kuzu — Via Appia (oro = ledger durable, Kuzu reconstruible) + paper reproducible (ADR-046 §3.11) + Kuzu existe para unir-por-clave-en-relaciones. Oro-como-join solo si un consumidor **no-Kuzu** necesita el wide-table. **Ratificar.**

## Acciones DAY 197 (en orden)
1. Pasar `PLAN-CIRCUITO-COMPLETO-DAY196.md` a revisión del Consejo (8 modelos).
2. **[verif §8.2]** writer y reader resuelven al **mismo path** antes de Eslabón 0:
   ```bash
   grep -nE 'base_dir|bronze|ARGUS_BRONZE_CSV|--bronze' \
     ml-detector/src/config_loader.cpp ml-detector/src/zmq_handler.cpp \
     correlation-engine/src/main.cpp
   ```
3. **[verif §8.1 pendiente]** ¿converter RAG-127 en uso o infra parada? (no bloquea; solo no romper algo vivo).
4. Con plan ratificado → **Eslabón 0:** sacar hardcode bronce de `zmq_handler.cpp:154` a JSON (`DEBT-CONFIG-BRONZE-HARDCODE-001`), patrón calcado de `csv_writer` (`config_loader.cpp:455`).

## Deudas abiertas (ticket pendiente)
- `DEBT-CIRCUIT-FS-DROP-001` (P1, post-circuito): ifstream → ZMQ §7.1
- `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` (P1): writer rota datado / engine sigue un fichero → corte mudo a medianoche
- `DEBT-ADAPTERSPEC-ENVELOPE-001` (P2 doc): enmienda §3 v1.1
- `DEBT-CORRELATION-V1-HOSTKEY-001` (P2 pre-Wazuh): `correlation_v1` sin `host_key`
- `DEBT-CONFIG-BRONZE-HARDCODE-001` (P1 Eslabón 0)
- `DEBT-DOCS-MEDALLION-DUALITY-001` (P2 doc): dos pipelines parquet
- Higiene: `backups/`/`.backup` ensucian árbol y greps → `git rm --cached` / `.gitignore`

## Punteros
- `PLAN-CIRCUITO-COMPLETO-DAY196.md` (plan + Apéndice A: evidencia medida)
- `docs/engineering_decisions/AdapterSpec v1 — Contrato de Ingesta de Adapters (aRGus++ NDR-EDR).md`
- ADR-046 v4 (pipeline multi-fuente), ADR-051 (community ID parity gate), ADR-057 (Kuzu / bitemporalidad)
- `ml-detector/include/correlation_writer.hpp` (contrato correlation_v1, 19 cols)
- `correlation-engine/src/main.cpp` (consumidor bronce → Kuzu)
- `scripts/parquet/` (converter RAG-127 — capa DISTINTA, no tocar para el circuito)

## Rama
Plan es documentación → el commit no pasa el gate de build. Confirmar a qué rama se sube (cerrar `day194/ransomware-provenance-desync` primero si sigue abierta, antes de abrir `day196/circuit-adapters-zmq` para implementación).