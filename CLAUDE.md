# CLAUDE.md — ML Defender / aRGus NDR
**Última actualización:** Cierre DAY 88 (16 marzo 2026)
**Mantenido por:** Alonso — Universidad de Extremadura (UEX), Extremadura, España

---

## 1. Qué es este proyecto

**aRGus NDR** (Network Detection & Response) es un sistema open-source de detección y respuesta a intrusiones de red, escrito en C++20, orientado a organizaciones con recursos limitados: hospitales, colegios, pymes. Detecta ransomware y DDoS en tiempo real combinando un Fast Detector heurístico y un pipeline de ML (Random Forest embebido).

- **Repositorio:** ML Defender (nombre del proyecto de investigación)
- **EDR** (endpoint agent) es roadmap futuro — FEAT-EDR-1. El scope actual es **NDR**.
- **Motivación:** Impacto directo del ransomware en hospitales locales de Extremadura.
- **Filosofía:** "Via Appia Quality" — construir para décadas, honestidad científica.
- **Metodología:** "Test Driven Hardening" — peer review multi-modelo (Consejo de Sabios).

---

## 2. Estado actual (DAY 88)

| Aspecto | Estado |
|---|---|
| Pipeline | 6/6 componentes RUNNING ✅ |
| Tests | 70/70 ✅ (crypto 3/3, etcd-hmac 12/12, ml-detector 9/9, trace_id 46/46) |
| Paper | Draft v5 — veredicto unánime Consejo: listo para arXiv ✅ |
| Repo | Limpio post-cleanup DAY 88 ✅ |
| Stress test | Completado DAY 87 ✅ |
| Branch activa | `main` |
| Último commit | `bd94dcfb` (paper v5 + README actualizado) |

---

## 3. Arquitectura del pipeline (6 componentes)

```
[sniffer] → ZeroMQ → [ml-detector] → ZeroMQ → [firewall-acl-agent]
                ↓                          ↓
           [etcd-server]            [rag-ingester] → [rag/]
```

### Componentes

| Componente | Rol |
|---|---|
| `sniffer/` | Captura de paquetes (libpcap/eBPF), extracción de features, Fast Detector heurístico |
| `ml-detector/` | Clasificación ML (Random Forest embebido), emisión de alertas via ZeroMQ |
| `firewall-acl-agent/` | Aplica bloqueos iptables basados en decisión ML |
| `etcd-server/` | Discovery de servicios, configuración distribuida, HMAC key rotation |
| `rag-ingester/` | Ingesta de eventos en FAISS + MetadataDB (SQLite) |
| `rag/` | Interfaz de consulta RAG (rag-local) |

### Configuraciones JSON (JSON is the law)
- Sniffer: `sniffer/config/sniffer.json`
- ML Detector: `ml-detector/config/ml_detector_config.json`
- **Nunca editar configs en `build-debug/`** — son copias del build, no fuente de verdad.

---

## 4. Métricas validadas (paper v5, DAY 86)

Dataset: **CTU-13 Neris** (scenario 10, 19.135 flows totales), 4 runs estables.

| Métrica | Valor |
|---|---|
| F1 | **0.9985** |
| Precision | 0.9969 |
| Recall | 1.0000 |
| TP | 646 (flows C2 activos) |
| TN | 12.075 |
| FP | 2 (artefactos VirtualBox — documentados) |
| FN | 0 |
| FPR ML | 0.0002% |
| FPR Fast Detector | 6.61% (bigFlows) |
| FP reduction | ~500× vs Fast Detector solo |

### Latencia de detección
- DDoS: 0.24 μs
- Ransomware: 1.06 μs

### Stress test (DAY 87, VirtualBox NIC)
- Throughput techo: ~33–38 Mbps (límite NIC VirtualBox, no del sistema)
- Packets procesados: 2.37M
- Drops: 0 | Errors: 0
- RAM estable: ~1.28 GB

### Fast Detector — thresholds hardcodeados (DEBT-FD-001)
```cpp
THRESHOLD_EXTERNAL_IPS = 10
THRESHOLD_SMB_CONNS    = 3
THRESHOLD_PORT_SCAN    = 10
THRESHOLD_RST_RATIO    = 0.20
WINDOW_NS              = 10s
```
Estos valores están en el código fuente (Path A, DAY 13). Path B lee correctamente el JSON.
**DEBT-FD-001:** unificar en DAY 90+ (post-paper).

---

## 5. Decisiones arquitecturales clave (ADRs)

| ADR | Decisión |
|---|---|
| ADR-001 | ZeroMQ como bus de mensajes entre componentes |
| ADR-002 | Protobuf para serialización de eventos |
| ADR-003 | ChaCha20 para cifrado de transporte |
| ADR-004 | HMAC key rotation con ventana de cooldown (max 2 claves concurrentes válidas) |
| ADR-005 | `MISSING_FEATURE_SENTINEL = -9999.0f` — matemáticamente fuera del dominio de splits RF |
| ADR-006 | Proto3 C++3.21: submensajes con todos los floats a `0.0f` no se serializan → `init_embedded_sentinels()` inicializa a `0.5f` |
| ADR-007 (propuesto) | OR logic para alertas, AND logic para bloqueos — previene ML score poisoning |

### Principios core
- **"JSON is the law"** — configuración en JSON, nunca hardcoded en producción.
- **"Via Appia Quality"** — código que dure décadas.
- **Sentinel values** — deterministas, fuera del dominio de splits (≠ semantic values, ≠ placeholders).

---

## 6. Deuda técnica activa

| ID | Descripción | Prioridad | Estado |
|---|---|---|---|
| DEBT-FD-001 | FastDetector Path A ignora sniffer.json — thresholds hardcodeados | P1-PHASE2 | post-paper |
| ADR-007 | AND-consensus firewall (OR alertas / AND bloqueos) | P1-PHASE2 | post-paper |
| DNS-001 | DNS payload parsing real (ahora superficial) | P2 | roadmap |

---

## 7. Roadmap (backlog priorizado)

### FEAT-ENTRY (onboarding)
| ID | Feature |
|---|---|
| FEAT-ENTRY-1 | Script de instalación one-liner |
| FEAT-ENTRY-2 | Docker Compose (re-introducir, solo para demo) |
| FEAT-ENTRY-3 | Tutorial getting started |
| FEAT-ENTRY-4 | Dashboard web básico |

### Features de red y detección
| ID | Feature | Prioridad |
|---|---|---|
| FEAT-NET-1 | DNS anomaly / DGA detection | P1 |
| FEAT-NET-2 | Threat intelligence feeds | P1 |
| FEAT-AUTH-1 | Auth log ingestion (SSH brute via syslog) | P2 |
| FEAT-EDR-1 | Lightweight endpoint agent (→ EDR completo) | P3 |

### Backlog técnico largo plazo
| ID | Feature |
|---|---|
| ENT-1 | Federated Threat Intelligence |
| ENT-2 | Attack Graph Generation |
| ENT-3 | P2P Seed Distribution via Protobuf |
| ENT-4 | Hot-Reload JSON config |

---

## 8. Estado del paper

- **Fichero:** `docs/Ml defender paper draft v5.md`
- **Secciones:** 13 secciones completas + Abstract v3
- **Veredicto Consejo de Sabios (ronda v5):** unánime — publicable en arXiv
- **Rename definitivo:** aRGus EDR → **aRGus NDR** (scope actual NDR; EDR = FEAT-EDR-1 roadmap)
- **Cambios integrados v5:** GEM1, DSV1-DSV4, CGV2-CGV6, G3, G5, Q1, Q3, CGP1
- **Próximo paso:** LaTeX conversion + endorsers arXiv

### Endorsers arXiv (Tier 1)
1. **Sebastian Garcia** — sebastian.garcia@agents.fel.cvut.cz (CTU Prague, autor CTU-13)
2. **Yisroel Mirsky** — Ben-Gurion University (autor Kitsune)
3. **Ariel Shabtai** — Ben-Gurion University (co-autor Kitsune)

### Endorsers arXiv (Tier 2, si Tier 1 no responde en 2 semanas)
4. Ali Habibi Lashkari — York University (autor CIC-IDS2017)
5. Iman Sharafaldin — UNB (co-autor CIC-IDS2017)
6. Battista Biggio — Universidad de Cagliari (adversarial ML)

---

## 9. Consejo de Sabios

7 modelos frontier como peer reviewers y co-autores:

| Modelo | Org |
|---|---|
| Claude | Anthropic |
| Grok | xAI |
| ChatGPT | OpenAI |
| DeepSeek | DeepSeek |
| Qwen | Alibaba |
| Gemini | Google |
| Parallel.ai | — |

Metodología documentada en el paper como contribución independiente ("Test Driven Hardening").

---

## 10. Infraestructura y operativa

### Entorno
- **macOS (BSD sed):** NUNCA `sed -i` sin `-e ''`. Preferir Python3 inline desde dentro de la VM.
- **VM:** `vagrant ssh defender` (no `server`)
- **Dataset paths en VM:**
    - `/vagrant/datasets/ctu13/neris.pcap` (CTU-13 scenario 10)
    - `/vagrant/datasets/ctu13/bigFlows.pcap` (CTU-13 scenario bigFlows)

### Dataset sources
- CTU-13: https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-42/
- Mirror: https://www.stratosphereips.org/datasets-ctu13

### Logs y outputs
- CSV ml-detector: `/vagrant/logs/ml-detector/events/YYYY-MM-DD.csv`
- CSV firewall: `/vagrant/logs/firewall_logs/firewall_blocks.csv`

### Comandos frecuentes
```bash
# F1 calculator
python3 scripts/calculate_f1_neris.py <sniffer.log> --total-events 19135

# Pipeline completo
make run-all

# Tests
make test-crypto
make test-etcd-hmac
make test-ml-detector
make test-trace-id
```

### RAM requirements (TinyLlama 4-bit quantized)
- Mínimo: 4 GB
- Producción recomendado: 8–16 GB

---

## 11. Estructura del repo (post-cleanup DAY 88)

### Raíz
```
CLAUDE.md          ← este fichero
LICENSE.txt
Makefile
README.md
Vagrantfile
```

### Carpetas activas del pipeline
```
sniffer/           ml-detector/       etcd-server/
firewall-acl-agent/ rag-ingester/     rag/
common/            common-rag-ingester/ protobuf/
etcd-client/       crypto-transport/  tools/
scripts/           docs/              third_party/
```

### Carpetas pendientes de revisión futura (no urgente)
```
models/            722 MB local — solo README.md trackeado
ml-training/       historia de experimentos de entrenamiento
pcap_testing/      pcaps pequeños, no trackeados
testing/           no trackeado
mawi/              datasets MAWI
datasets/          no trackeados (gitignore)
contract-validation/ experimento DAY 52
contrib/           revisar en sesión futura
```

---

## 12. Hitos del proyecto (cronología)

| DAY | Hito |
|---|---|
| 13 | FastDetector con thresholds hardcodeados (Path A) |
| 52 | ContractValidator (experimento, no en pipeline activo) |
| 63–71 | Dual CSV pipelines, MetadataDB migrado a 14 columnas |
| 72–73 | Sistema trace_id determinista (SHA256) |
| 74–75 | Full pipeline integration — 6/6 componentes running |
| 76 | Fix SIGSEGV Proto3, merge feature/rag-firewall-hmac-security, tag v0.76.0 |
| 77–78 | MISSING_FEATURE_SENTINEL, TimeWindowAggregator, 9 feature extractors multi-flow |
| 79 | F1=0.9921 baseline CTU-13 Neris; 8 placeholders → sentinels |
| 80 | F1=0.9934; "JSON is the law"; fix 4-layer bug chain |
| 82 | DEBT-FD-001 descubierto; ADR-007 propuesto |
| 84 | 70/70 tests (fix timestamp bug + fallback_applied bug) |
| 85 | Paper draft completo — 10 secciones, Abstract v3, TDH methodology |
| 86 | F1=0.9985 estable (4 runs); métricas definitivas |
| 87 | Stress test: 2.37M packets, 0 drops, RAM ~1.28 GB |
| 88 | Paper v5 veredicto unánime; README actualizado; repo limpio; rename NDR |

---

*CLAUDE.md generado al cierre de DAY 88. Próxima actualización: cierre DAY 89.*