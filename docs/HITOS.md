# aRGus NDR — Registro histórico (HITOS)

> **Qué es este fichero.** El diario de ingeniería día a día del proyecto, rescatado del
> README cuando este se reescribió como puerta al paper (DAY 253). **No es el estado actual
> del pipeline.**
>
> Las cifras aquí reflejan el entendimiento de *cada día*; muchas fueron matizadas o corregidas
> después. En particular: el **F1 = 0.9985** que aparece repetido abajo se ancló más tarde al
> **subconjunto conductual de 646 flujos** de CTU-13 Neris, y el cuadro operativo honesto es el
> **sesgo por-lente** (Zeek 99.9% / Suricata 1.5% / aRGus lente gruesa con el ML ciego y el
> fast-path llevando la detección) — ver el paper (arXiv:2604.04952) y el README actual. Léase
> como historia, no como aserción vigente.

---

## Hitos DAY 201-204 — Eslabon 0 CERRADO (3/3) + emecas+++ (circuito bronce->Kuzu)
- **Eslabon 0 completo.** DAY 201-202 cierran `DEBT-CONFIG-BRONZE-HARDCODE-001` (writer+reader
  derivan `bronze_root`/`base_dir` de JSON). DAY 203 cierra `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001`:
  bronce segmentado con escritura atomica `.tmp`->rename + `BronzeDirWatcher` (inotify puro,
  `IN_MOVED_TO`) en el reader — verificado en EMECAS++ real, cero fallos de rename bajo carga.
- **`DEBT-CORRELATION-ROUNDTRIP-ORPHANED-001` CERRADA por medicion (DAY 204).** La causa raiz no
  era la sospechada (add_test ausente) sino cache de CMake sin reconfigurar + `Stats::current_file`
  devolviendo el `.tmp` en curso en vez del path final post-rename. Fix: campo nuevo
  `Stats::current_final_path`. 4/4 PASSED contra el bronce segmentado real.
- **`emecas+++` — circuito completo bronce->Kuzu (ADR-058 §1), DAY 204.** `process_segment`
  extraida de `main.cpp` a funcion compartida (`segment_processor.{hpp,cpp}`) — mismo codigo en
  produccion y en el test nuevo, cero reimplementacion. `test_bronze_to_kuzu_circuit.cpp`: circuito
  completo en un proceso, FS puro — `CorrelationWriter` real -> bronce -> `process_segment` real ->
  `KuzuGraphSink` real -> `MATCH` en Kuzu, mas el caso adverso (HMAC roto nunca llega al grafo).
  Target `emecas+++` en el Makefile (alias de `emecas++` por ahora, hueco formado para Eslabon 1).
  EMECAS++ completo ejecutado en `main` tras el merge — pipeline 6/6 RUNNING confirmado.

## Hitos DAY 195 — Forense del detector de ransomware + spec de laboratorio
- **DEBT-RANSOMWARE-MODEL-DESYNC-001 DIRIMIDA por medición.** `5bbddd11` reentrenó pero de forma estructuralmente equivalente a un reescalado: `feature[]` y `children_left[]` idénticos en los 100 árboles entre `830b0ec0` y `5bbddd11`, solo cambian los thresholds (MinMaxScaler afín monótona, `random_state=42` intacto). **Un único modelo.** `feature_importances` válidos para el desplegado; el veto de `model_info` en el paper se estrecha a *rendimiento*, no a importancias. Acción pendiente: regenerar header desde el JSON canónico de `5bbddd11` (tras verificar la escala de features en producción).
- **DEBT-RANSOMWARE-ML-HEAD-INERT-001 abierta (P1, pre-producción).** La cabeza ML de ransomware es no funcional en red por SEMANTICS-001 (feature[1] = varianza long. paquete/1e5 vs entropía Shannon de fichero). El sistema detecta vía `fast` path; `ml` deprimido (~0.14). Bloquea fiarse de plugins ensemble. Reentreno diferido a post-circuito, contra ground truth de red.
- **LAB-RANSOMWARE-FIRETEST-SPEC creada** — `docs/experiments/LAB-RANSOMWARE-FIRETEST-SPEC.md`. Diseño de laboratorio para detonar ransomware real y medir detección. H1 registrada con fecha. E1 (detección, víctimas x86) y E2 (port ARM64, ejecutable ya) separados. Ejecución pendiente de hardware.
- **Decisión Alonso DAY 195:** terminar el circuito completo (adapters/LZ/Arrow medallion/Kuzu/grafo) asumiendo la inferencia ML rota/incompleta. El reentreno es posterior, con microscopio afinado. "Es mejor saberlo que ignorarlo."

## Estado de proyecto — snapshot DAY 211 (histórico)

| Campo | Valor |
|---|---|
| DAY | 211 |
| Tag | v1.0.0-day191 |
| Branch | docs/day211-verdict-debts |
| EMECAS++ OSS | verde — test-all + test-e2e-synthetic-full + test-e2e-synthetic-firewall |
| EMECAS++ Enterprise | VERDE — 3 actos + Jenkins gate (DAY 167) |
| Pipeline | 6/6 RUNNING |
| H-1 Cypher | mitigada (prepared statements ADR-057, path ejecutado Kuzu) |
| H-2 ipset (NÚCLEO 1+3) | DAY 189 (`0db706c8`) — set_name validado + shell eliminado |
| H-2 comment (NÚCLEO 2) | DAY 191 — `comment` rechaza `\n`/`"`/`\` fail-fast. CWE-93. **H-2 COMPLETA** |
| CWE-78 autonomy.whitelist_cidrs | DAY 190 — `parse_autonomy` valida CIDR fail-fast |
| Consejo de Sabios | 8/8 — Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral |
| Arquitectura | ADR-046 v4 · ADR-052 v3.2 · ADR-051 v2.2 · ADR-055 v1 · ADR-057 v2 |

> **Nota DAY 187 — B4 cerrada: árbitro `build_row` BORRADO (Camino A).** `write_record` pasa
> por `to_correlation_v1_row` + `serialize` (notario único P3). `build_row`, `compute_hmac`,
> `fmt_double`, `csv_string` y `test_correlation_v1_oracle` RETIRADOS. Validación: fuzz
> diferencial contra el oráculo vivo **240.810 runs / 61s, cero divergencias** (pre-borrado) +
> `test_correlation_roundtrip` verde + golden recongelado `WRITTEN=24 SKIPPED=1 REJECTED=2
> mismatches=0` + grep de cierre `build_row|compute_hmac` = 0 + EMECAS++ 3 actos verdes.
> `DEBT-CORRELATION-V1-EXTRACT-B4-REWIRE-001` CERRADA.

> **Nota DAY 185 — claim honesto de la extracción `libcorrelation_v1`:** Extracción de la capa de
> serialización del contrato `correlation_v1` a librería compartida, **verificada byte-idéntica**
> contra el oráculo `build_row` sobre **27 vectores enumerados y bajo locale classic**. Salvedades:
> equivalencia general acotada por enumeración (no probada); golden en classic; `\n` embebido rompe
> readers `getline` (DEBT-BRONZE-EMBEDDED-NEWLINE-001); guard de enum desconocido diferido; identidad
> cross-productor cubre cols 0-17, col 18 (HMAC) depende de política de claves.

## Hitos DAY 191 — H-2 NÚCLEO 2 CERRADO · H-2 COMPLETA (CWE-93 ipset comment injection)
- **H-2 NÚCLEO 2 CERRADO Y PROBADO** — campo `comment` de `IPSetWrapper::add_batch`. Inyección **CWE-93** (newline/quote) DEMOSTRADA sobre Debian 12 Bookworm **ipset v7.17**: el payload cierra el token con `"` y abre línea nueva con `\n` → inyectó la entrada en el set. La línea inyectada puede ser `flush`/`destroy` → vaciar la blocklist entera con un comentario.
    - **Mitigación (allowlist fail-fast):** `include/firewall/comment_validator.hpp` — `is_valid_comment()` rechaza control chars, `"` y `\`, longitud ≤255. Cableado en `add_batch` → `IPSetErrorCode::INVALID_COMMENT`.
    - **Lección transversal:** la indulgencia del parser de `ipset` DIFIERE entre versiones → la defensa vive en la frontera C++, nunca delegada en `ipset`.
    - **Tests:** 6 GTest `CommentValidator.*` + canario e2e `IPSetWrapperTest.CommentInjectionRejected`. **79/79 sin root** (73→79); canario **7/7 con sudo**. **H-2 COMPLETA** (NÚCLEO 1+2+3).

## Hitos DAY 188-190 — Auditoría de deuda de seguridad del firewall
- **H-2 NÚCLEO 1+3 CERRADO (DAY 189, `0db706c8`)** — `set_name` validado + shell eliminado, `safe_exec`, 0 focos de shell.
- **CWE-78 autonomy.whitelist_cidrs CERRADO Y PROBADO (DAY 190, `68ab3eb9`)** — `parse_autonomy` valida cada CIDR (`throw` fail-fast). `is_valid_ip_cidr` extraído a `firewall/ip_cidr_validator.hpp`.
    - **Tests:** 4 GTest de inyección + 1 standalone (29 asserts). **73/73**, cero regresión.
    - **system() interino:** silenciado con `nosemgrep` PEGADO al `return` → `DEBT-AUTONOMY-REACTOR-SAFEEXEC-002`.
- **EMECAS++ 3 actos verde · PR #103 → main `395ee014`.**

## Hitos DAY 184 — flush()→FlushResult + batch transaccional + Consejo del banco de tortura
- **`IGraphSink::flush()` deja de devolver `void` → `FlushResult`** (`{bool ok; uint64_t rows_flushed; uint64_t rows_pending; explicit operator bool}`). `[[nodiscard]]` sobre el TIPO → ningún sink puede descartar en silencio el fallo de durabilidad bajo `-Werror`. `main.cpp`: flush fallido → `EXIT_FAILURE`. Commit `4e221ede`.
- **`KuzuGraphSink` cableado en batch.** `flush()` ejecuta el batch en UNA transacción: `BEGIN`/loop `execute(prepared)`/`COMMIT`; `ROLLBACK` + buffer retenido en fallo. **Cierra H-1 en el path EJECUTADO de Kuzu.** Commit `112b9df1`.
- **VERIFY-3 — test de agrupación transaccional.** COMMIT → 2 nodos durables; ROLLBACK → 0. 6/6 verde.
- **API Kuzu 0.11.3 verificada contra el header vendorizado** (NO de memoria): control de transacción por string `query("BEGIN"/"COMMIT"/"ROLLBACK")`; `execute(PreparedStatement*, ...)` variádico; `common::Value` sin ctor desde `string_view` (materializar a `std::string`); el header documenta el SIGSEGV de DAY 183.
- **Consejo de Sabios (8/8)** — 5 decisiones (medir-primero, Opción B, extraer librería, injector-a-fichero, HMAC=correctitud) aprobadas con condiciones de validez.

## Hitos DAY 182 — Smoke B1: D1+D2 resueltas por medición
- **D1 — un grafo vs N grafos → UN GRAFO.** run3 (4 writers) midió 373.000 rechazos por la única write-tx, +37% throughput, lectura p99 ×11.37. Multi-writer no escala.
- **D2 — Kuzu stock vs fork Vela → KUZU STOCK.** El cuello era el overhead por-`query()`. **UNWIND batch (1 query = N upserts) da ×55–61.** Vela solo añade writers paralelos = lo que run3 probó que no escala.
- **Descomposición:** `coste(n)=P+S+n·E` → E≈88 µs/fila (MERGE irreducible), P+S≈5.93 ms (fijo, amortizable).
- **Corrección honesta (ninguno de los otros 7 modelos la cazó):** el `unordered_map::at` al reabrir tras crash fue auto-infligido (borrar `.kuzu` dejando `.wal` huérfano), NO prueba de recuperación rota.
- **Fase 0 del grafo verde (EMECAS DAY 182):** `ingested_at` + `temporal_anomaly` + `build_cypher(ingested_at_ns)`. NO production-readiness — distinción explícita en ADR-057 §7.
- **`correlation-engine` y `graph-engine` separados** por Apache Iceberg.

## Hitos DAY 177 — Contrato bronce `correlation_v1` en forma final + injectors sellados E2E
- **(B) col 17 `authoritative_source` → string simbólico.** `DetectorSource_Name()` en el writer. Round-trip verde + bronce real con `150 DETECTOR_SOURCE_ML_PRIORITY` + `9 DETECTOR_SOURCE_DIVERGENCE`.
- **node_id sintético — DEBT-INJECTOR-NODEID-001 CERRADA (P0).** `flow_uid` ya no degenera.
- **Proto benigno correlacionable.** El injector ponía `protocol_number=rand[1,255]` → ~99% no-TCP/UDP → `compute_community_id() nullopt` → bronce a 0 filas. Fix: coin flip `use_tcp` gobierna number+name. community_id 0%→100%.
- **DEBT-INJECTOR-ROWGAP-001 REENCUADRADA:** el `send(dontwait)` reproduce la entrega no-garantizada de ZMQ PUSH; INSTRUMENTAR (diff de conjuntos), no re-arquitecturar (ADR-055 §0).
- **ADR-055 v1 RATIFICADA (DAY 178)** — Inyectores Sintéticos: fidelidad, determinismo, entrega.

## Hitos DAY 175 — Zona bronce `correlation_v1` CABLEADA y verificada E2E
- Cadena completa con datos reales: sniffer eBPF → community_id → ZMQ → ml-detector → bronce → `parse_and_verify`. **3.712 filas reales**, todas con community_id, una validada con la clave de PRODUCCIÓN de etcd.
- **Lección (DEBT-BRONZE-KEY-PROVISIONING-001):** la clave HMAC del bronce es la de etcd `/secrets/<componente>`, no `seed.hex`.
- **REGLA PERMANENTE:** construir siempre vía `make <target>` (corre `proto`, aplica `-Werror`), nunca `cmake` directo.
- **INVARIANTE:** community_id es el punto de unión con Suricata/Zeek — TODAS las variantes del sniffer deben poblarlo.

## Hitos DAY 173 — ADR-051 v2.2 + ADR-052 v3.2 RATIFICADAS (Consejo 8/8)
- **ADR-051 v2.2** — Community ID Parity Gate & Correlation Health. **Oracle Divergence:** si los sensores coinciden entre sí pero no con `pycommunityid`, arranca con WARNING crítico, NO fail-closed (N-version); fail-closed reservado a disparidad ENTRE sensores.
- **ADR-052 v3.2** — Multi-node Flow Identity & Host↔Net Correlation. §0: *"El grafo no es el producto. El producto es el corpus."* `flow_uid = base64(BLAKE2b(node_id ‖ community_id ‖ flow_start_window [‖ seq_in_window]))`; `node_id` = string legible declarado en inventario firmado; `community_id` = clave de correlación, nunca identidad.
- **ADR-053 stub abierto** — JA3/JA4, cadena TLS profunda, anomalía de ruta L3/BGP.

## Hitos DAY 171 — Cross-check E2E community_id: paridad OPERACIONAL demostrada
- El cliente `.50` replaya el flujo Neris por `eth1`; aRGus + Suricata + Zeek capturan en paralelo (promiscuo) el MISMO paquete y los tres convergen STRING A STRING a `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`.
- **aRGus surfacea community_id observable** — `sniffer/src/flow/community_id_log.{hpp,cpp}`, gateado por `ARGUS_CID_CROSSCHECK=1` (OFF por defecto, coste nulo en hot path).
- **Nota algoritmo:** `community_id` usa SHA1 (Corelight), no HMAC-SHA256.

## Hitos DAY 170 — community_id cross-sensor sellado
- aRGus (nativo, 8/8 vs oráculo pycommunityid v1.5.0, campo protobuf field 18), Zeek 8.2.0 (`@load community-id-logging` + `seed=0`) y Suricata 7.0.10 (`community-id:yes` + `seed:0`). Diana E2E `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`.
- **DEBT-DOCS-BACKLOG-DEDUP-001 CERRADA** — `docs/BACKLOG.md` corrupto desde DAY 158 (append manual). 5336→2839 líneas.

## Hitos DAY 168-169 — multi-VM + día de arquitectura
- **Vagrantfile multi-VM** — Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x + client en `ml_defender_gateway_lan` (192.168.100.0/24). 50.248 reglas ET Open. Merge a main `21642e87`.
- **3 reglas permanentes nuevas** — nunca `set -e` en provisions; DNS fix `chattr +i` SIEMPRE tras chrony; nunca heredoc `cat << 'EOF'` anidado en `<<-SHELL` (usar `printf`).
- **ADR-046 v4** aprobado (Multi-Source Pipeline). **AdapterSpec v1** cerrado.

## Hitos DAY 163-167 — crypto lifecycle enterprise
- **DAY 167:** DEBT-ARGUSPP-NTP-001 CERRADA (P0, chrony en todos los nodos). correlation-engine scaffold (ADR-048 F2). Jenkins gate. Merge `7b45feca`.
- **DAY 166:** EMECAS++ 3 actos verdes · merge enterprise a main · Zero downtime demostrado · **Tag v1.0.0-day166**.
- **DAY 165:** FASE 3 wire header `[uint32_t size][uint16_t epoch_id][2B reserved][LZ4+encrypted]`. 13/13 tests.
- **DAY 164:** `HttpEtcdRegistrar` REST real + `CryptoEpochCoordinator`. 10/10 tests.
- **DAY 163:** Modelo B vendor.key efímero por `vagrant up`. `CryptoProviderHandle` RCU (`std::atomic<shared_ptr>`). ADR-045 v2 (Consejo 8/8).

## Hitos DAY 154-160 — VaultClient, autonomía firewall, enterprise plugin
- **DAY 160:** libvault_provider.so 6/6. Jenkins 2.555.2 + Vault v2.0.1. ADR-048 Dataset Production Roadmap.
- **DAY 157:** 4 deudas cerradas (autonomy state persistence firmada Ed25519, bootstrap-status firmado, keypair lifecycle prod, crypto reconciliation + staleness guard). EMECAS VERDE.
- **DAY 156:** DEBT-AUTONOMY-CRYPTO-INTEGRATION-001. Fix ZMQ slow joiner (bind antes de connect — regla permanente PUB/SUB). EMECAS VERDE 50/50.
- **DAY 155:** cadena `argus-autonomy` selectiva (lo→ESTABLISHED→CIDRs→DROP→INPUT), whitelist JSON obligatoria. EMECAS HARDENED. Tag `v0.9.0-day155`.
- **DAY 154:** ADR-045 VaultClient decomposition (`ICryptoDeriver`/`IEtcdRegistrar`). `FirewallAutonomyReactor`. Tag `v0.8.0-adr045`.

## Hitos DAY 149-151 — Parquet, Vault, ICryptoProvider
- **DAY 151:** ICryptoProvider (`SeedFileProvider` + `VaultProvider` + factoría), `#ifdef ARGUS_VAULT_ENABLED` confinado. etcd-server STEP 0. ADR-045 aprobado. Tag `v0.8.0-day151`.
- **DAY 149:** Schema Arrow v1.0 (ml_detector_events 15 fields + firewall_acl_events 7 fields), 207.122 filas / 53 días, ratio 11-12×. Vault dev mode + K_pseudo prototipo (evidencia GDPR). Ansible+Jinja2 CI/CD. ADR-044. Tag `v0.7.2-day149`.

## Hitos DAY 143-148 — IRP, Variant A/B, experimentos comparativos
- **DAY 148:** Suricata offline irrefutable (`suricata -r neris.pcap`, 50.010 reglas ET Open, 323.154 paquetes, **0 firmas ET disparadas**). §8.13/§8.14 paper. arXiv replace v19→v23. Tag `v0.7.1-day148`.
- **DAY 147:** Experimento tres paradigmas — Suricata F1=0.000 (TP=0), Zeek F1=0.042 (Prec=1.000, 14 TP `SSL::Invalid_Server_Cert`), aRGus F1=0.9985 (TP=646). `weird.log`: Zeek observa IRC/HTTP beaconing/SMB lateral/spam sin alertar. Distinción observabilidad vs detección. Paper v21/v22.
- **DAY 146:** Experimento Suricata 6.0.10 vs aRGus (CTU-13 Neris, mismas condiciones): Suricata 0 alertas (ET Open no cubre Neris 2011) vs aRGus F1=0.9985. Paper v20 §8.13.
- **DAY 145:** ADR-029 Variant A vs B x86 — libpcap ~2× eBPF en VirtualBox virtio (artefacto SKB mode). Bootstrap múltiple. Paper v19. **Failed packets (2.630):** artefacto fijo del pcap CTU-13 Neris (frames jumbo > MTU 1500 VirtualBox, `errno=90 EMSGSIZE`), conteo idéntico en los 6 runs — no son errores del pipeline.
- **DAY 143-144:** IRP completo (config → fork()+execv() → AppArmor 7/7 enforce → 12/12 tests). SA_NOCLDWAIT. Gate ODR production superado.

---

## Tres variantes del pipeline (histórico)

| Variante | Estado (DAY 211) | Descripción |
|----------|--------|-------------|
| **aRGus-dev** | Activa (`main`) | x86-debug, imagen Vagrant completa. Investigación y desarrollo diario. |
| **aRGus-production** | En construcción | x86-apparmor + arm64-apparmor. AppArmor enforce, cap_bpf, Falco, noexec. |
| **aRGus-seL4** | Research track post-FEDER | Kernel seL4, libpcap. Reescritura completa. Branch independiente. |

---

## Métricas validadas (snapshot histórico DAY 145-148)

> Cifras de la época clasificador-céntrica. El **F1 = 0.9985 es sobre el subconjunto conductual
> de 646 flujos**; el cuadro operativo honesto es el sesgo por-lente del paper v25 y del README actual.

| Metric | Value | Notes |
|---|---|---|
| F1-score (CTU-13 Neris, subset 646) | 0.9985 | Stable across 4 replay runs |
| Precision | 0.9969 | |
| Recall (subset 646) | 1.0000 | |
| Suricata 6.0.10 F1 (CTU-13 Neris) | 0.000 | 0 alerts — ET Open retired for 2011 threats |
| Zeek 8.1.2 F1 (CTU-13 Neris, default) | 0.042 | Precision=1.000, 14 TP (SSL::Invalid_Server_Cert) |
| XGBoost Precision (CIC-IDS-2017 val) | 0.9945 | In-distribution, threshold=0.8211 |
| XGBoost Wednesday OOD | Documented impossibility | Structural covariate shift — §8 paper |
| Inference latency (XGBoost) | 1.986 µs/sample | Gate <2µs |
| Inference latency (RF) | 0.24–1.06 µs | Per-class, embedded C++20 |
| Throughput ceiling (virtualized) | ~33–38 Mbps | VirtualBox NIC limit, not pipeline |
| Stress test | 2,374,845 packets — 0 drops | 100 Mbps requested, loop=3 |
| RAM (full pipeline) | ~1.28 GB | Stable under load |
| BSR — Dev VM | 719 pkgs / 5.9 GB | gcc, g++, clang, cmake present |
| BSR — Hardened VM | 304 pkgs / 1.3 GB | NONE (check-prod-no-compiler: OK) |
| AppArmor profiles | 6/6 enforce | cap_bpf (Linux ≥5.8), no cap_sys_admin |
| Falco rules | 11 aRGus-specific | modern_ebpf driver |

### Security hardening — capabilities (histórico)

| Component | Capabilities |
|---|---|
| sniffer | `cap_net_admin,cap_net_raw,cap_bpf,cap_ipc_lock` |
| firewall-acl-agent | `cap_net_admin` |
| etcd-server | `cap_ipc_lock` (+ LimitMEMLOCK=16M) |
| argus-network-isolate | `cap_net_admin` (AppArmor enforce — DAY 143) |
| ml-detector, rag-ingester, rag-security | none |

---

## Milestones (histórico DAY 111-204)

- DAY 111: arXiv:2604.04952 PUBLICADO
- DAY 113: ADR-025 MERGED — v0.3.0-plugin-integrity
- DAY 118: PHASE 3 COMPLETADA — v0.4.0
- DAY 122: PHASE 4 COMPLETADA — v0.5.0-preproduction
- DAY 124: ADR-037 MERGED
- DAY 129: CWE-78 CERRADO — execv() sin shell
- DAY 130: REGLA EMECAS · libFuzzer 2.4M runs
- DAY 133: ADR-030 Variant A — cap_bpf · AppArmor 6/6 · Falco 10 reglas
- DAY 134: ADR-040 (8/8, 17 enmiendas) · ADR-041 FEDER HW Metrics (8/8)
- DAY 136: v0.9.3-day158-variant-a · merge main
- DAY 137-142: Variant B libpcap · ISP cerrado · 8/8 tests · IRP pasos 1-6
- DAY 143-145: IRP completo · Gate ODR · ADR-029 Variant A vs B · Paper v19
- DAY 146-148: Experimentos comparativos Suricata/Zeek · Paper v20-v23 · arXiv v3
- DAY 149-151: Parquet Arrow · Vault CI/CD · ADR-044 · ICryptoProvider
- DAY 154-157: VaultClient decomposition · autonomía firewall · 4 deudas crypto
- DAY 160-166: enterprise plugin · crypto lifecycle · EMECAS++ 3 actos · Tag v1.0.0-day166
- DAY 167-173: NTP · multi-VM Suricata/Zeek/Wazuh · community_id cross-sensor · ADR-051/052
- DAY 182-204: smoke Kuzu (un grafo, UNWIND ×55-61) · Fase 0 grafo · auditoría seguridad H-1/H-2 · Eslabon 0 · emecas+++

---

## Consejo de Sabios — Multi-Model Peer Review

**Claude** (Anthropic) · **Grok** (xAI) · **ChatGPT** (OpenAI) · **DeepSeek** · **Qwen** (Alibaba) · **Gemini** (Google) · **Kimi** (Moonshot) · **Mistral**

Metodología: desacuerdo estructurado. Documentado en §6 del preprint.