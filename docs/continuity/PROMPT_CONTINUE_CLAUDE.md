# PROMPT DE CONTINUIDAD — DAY 198 (continúa DAY 197)

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria; trazar hacia atrás desde el binario.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable durable y verificable; Kuzu = proyección reconstruible).
- **EMECAS++** antes de cualquier merge · **PR obligatorio** (commit de doc no pasa el gate de build).
- **Consejo de Sabios** (8 modelos) ratifica decisiones de arquitectura.
- Un día, una batalla.

## Estado al cierre de DAY 197
- **Plan ratificado por el Consejo (9/9 en forma del oro).** Documento consolidado: `PLAN — Circuito completo aguas abajo (DAY 196 → implementación).md` con dictamen DAY 197 + correcciones de coherencia incorporadas.
- **Forma del oro CERRADA, unánime:** oro-como-ledger + join en Kuzu (write-time). El ledger es el ÚNICO oro; Kuzu y cualquier wide-table (incl. matriz de features ML, ADR-040) son **proyecciones co-iguales reconstruibles**. No hay caso para oro-como-join.
- **Todas las preguntas abiertas del §10 cerradas** salvo 10.8 (parámetros de join adaptativo en el ledger — diferida con ticket, `DEBT-JOIN-CONFIDENCE-001`; hoy son deterministas en JSON → propiedad mantenida).
- **Decisiones nuevas DAY 197:** (a) `flow_uid` es la PK del grafo, NO `community_id` (coherencia ADR-052); (b) `node_id`/`community_id`/`flow_start_window` deben ser columnas de primera clase del oro-ledger (hipótesis del proyecto: contribución por nodo); (c) Wazuh → contrato `host_domain_v1` separado, decisión sube antes del Eslabón 1; (d) timestamp se funde en la LZ, NO en el writer C++; (e) ZMQ handoff = PUSH/PULL, no PUB/SUB (at-least-once); (f) HMAC por-fila heredado al oro + firma del Parquet (replay coherente en el tiempo); (g) Andrés congelado con razón escrita (repo sin código).
- **[MEDIDO DAY 197]** Conector PARQUET→Kuzu NO existe, ni prototipo → circuito verde cierra primero por **Camino 0** (`ifstream` bronce→Kuzu, ya existe). Tres caminos: Camino 0 (existe) / Flujo A (bronce→AVRO→Parquet oro, greenfield) / Flujo B (Parquet→Kuzu, greenfield). Criterio de cierre del medallón = **test de equivalencia Camino-0 ≡ Flujo-A+B**.
- **[MEDIDO DAY 197]** `node_id` (col 3) y `community_id` (col 4) ya son columnas de primera clase en bronce. La dilución (si la hay) está en el converter Flujo A, no en el contrato bronce.

## Decisión VIVA para el Consejo
Ninguna abierta. 10.8 diferida con ticket. El plan está listo para cerrar como ADR.

## Acciones DAY 198 (en orden)
1. **[verif P0 — §8.5]** ¿`node_id`/`community_id`/`flow_start_window` propagan al oro como columnas, o solo alimentan `flow_uid`? Decidir si `flow_start_window` se materializa explícito (recomendado) o se re-deriva de cols 5-6.
```bash
   grep -nE 'node_id|community_id|flow_start_window|flow_start_sec|flow_start_nano' \
     ml-detector/include/correlation_writer.hpp
```
2. **[verif P0 — §8.6]** ¿`parse_and_verify` acepta `-1` en TODAS las numéricas (5-6, 9-10, 14-16) sin descartar fila? Si rechaza negativos como "ilegibles", el segundo centinela rompe el circuito en silencio.
3. **[verif §8.2]** writer y reader resuelven al mismo path (grep config_loader/zmq_handler/main.cpp).
4. Con las 3 verificaciones verdes → **cerrar el ADR del circuito** con todo lo decidido y pasarlo al Consejo para ratificación final.
5. → **Eslabón 0:** config bronce a JSON (`bronze_root` + patrón naming, calcado de `csv_writer` `config_loader.cpp:455`) + watcher `inotify`/`IN_CLOSE_WRITE` + escritura atómica `.tmp`→rename + cierre por tiempo absoluto. Cierra `DEBT-CONFIG-BRONZE-HARDCODE-001` + `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` (ambas P0).

## Deudas abiertas (prioridad)
- **P0:** `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001`, `DEBT-CONFIG-BRONZE-HARDCODE-001`, `DEBT-GOLD-NODE-DIMENSION-001`, `DEBT-PARSE-VERIFY-SENTINEL-001`
- **P1:** `DEBT-HOST-DOMAIN-CONTRACT-001` (pre-Eslabón 1), `DEBT-PARQUET-KUZU-CONNECTOR-001`, `DEBT-GOLD-INTEGRITY-HMAC-001`, `DEBT-ZMQ-DELIVERY-GUARANTEE-001`, `DEBT-CIRCUIT-FS-DROP-001`
- **P2:** `DEBT-ADAPTERSPEC-ENVELOPE-001`, `DEBT-DOCS-MEDALLION-DUALITY-001`, `DEBT-JOIN-CONFIDENCE-001`
- **P3:** higiene `backups/`/`.backup` → `git rm --cached` / `.gitignore`

## Punteros
- `PLAN — Circuito completo aguas abajo (DAY 196 → implementación).md` (consolidado DAY 197, §10 = decisiones cerradas)
- `docs/engineering_decisions/AdapterSpec v1` (enmienda v1.1 pendiente: envelope inexistente + PUSH/PULL)
- ADR-046 v4, ADR-051 (parity gate), **ADR-052 (flow_uid identidad multi-nodo)**, ADR-057 (Kuzu / bitemporalidad)
- `ml-detector/include/correlation_writer.hpp` (contrato 19 cols; node_id=3, community_id=4)
- `correlation-engine/src/main.cpp` (Camino 0: ifstream → parse_and_verify → flow_uid → Kuzu)
- `scripts/parquet/` (RAG-127, capa DISTINTA — no tocar para el circuito)

## Rama
`day196/circuit-adapters-zmq`. El plan-doc es el commit de apertura (no pasa gate de build, va con la implementación del Eslabón 0 en el mismo PR). Confirmar que `day194/ransomware-provenance-desync` está cerrada antes de abrir.