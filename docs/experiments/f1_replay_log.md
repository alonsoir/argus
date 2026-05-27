
## DAY82-001 — CTU-13 smallFlows (2026-03-11)

| Campo | Valor |
|---|---|
| Dataset | CTU-13 smallFlows.pcap (9.1MB, 14261 packets, 1209 flows) |
| Thresholds | prod JSON: DDoS=0.85 / Ransomware=0.90 / Traffic=0.80 / Internal=0.85 |
| ML attacks | **0** ✅ |
| ML score máximo | **0.3818** |
| Fast Detector alertas | **3,741** ⚠️ |
| IP botnet real presente | NO (147.32.84.165 ausente en este PCAP) |
| Conclusión | **Todos FPs** — tráfico Windows legítimo (Microsoft CDN, Google, Windows Update) |

### Hallazgo: DEBT-FD-001

Fast Detector Path A (`is_suspicious()`) usa constantes hardcodeadas en `fast_detector.hpp`,
ignorando completamente la configuración JSON. Viola "JSON is the law".

| Constante | Valor | JSON equivalente |
|---|---|---|
| `THRESHOLD_EXTERNAL_IPS` | 10 | `external_ips_30s: 15` (Path B) |
| `THRESHOLD_SMB_CONNS` | 3 | `smb_diversity: 10` (Path B) |
| `THRESHOLD_PORT_SCAN` | 10 | — sin equivalente |
| `THRESHOLD_RST_RATIO` | 0.2 | — sin equivalente |
| `WINDOW_NS` | 10s | — sin equivalente |

Construido DAY 13, antes del sistema de configuración JSON. Fix PHASE2.

### Valor científico

- Validación de especificidad completada: ML RandomForest **no genera FPs** en tráfico benigno ✅
- Fast Detector FPR elevado en tráfico Windows moderno (CDNs, telemetría, Windows Update)
- Arquitectura dual-score funciona como safety net: ML no confirma alertas Fast Detector
- Documentable honestamente como limitación Phase 1

## DAY82-002 — CTU-13 bigFlows (2026-03-11)

| Campo | Valor |
|---|---|
| Dataset | CTU-13 bigFlows.pcap (352MB, 791615 packets, 40467 flows) |
| Thresholds | prod JSON: DDoS=0.85 / Ransomware=0.90 / Traffic=0.80 / Internal=0.85 |
| ML label=1 (log 🚨 ATTACK) | **7** |
| ML attacks_detected (stats, conf>=0.65) | **2** |
| ML score máximo | **0.6897** (threshold level1_attack=0.65) |
| Fast Detector alertas | **31,065** |
| Ground truth disponible | ❌ IPs 172.16.133.x no en binetflow Neris |

### Hallazgo: Tres contadores con semántica distinta

| Contador | Condición | Valor |
|---|---|---|
| log `🚨 ATTACK` | `label_l1 == 1` (voto binario RF) | 7 |
| `stats_.attacks_detected` | `label_l1==1 AND conf>=0.65` | 2 |
| `final_classification=MALICIOUS` | `final_score>=malicious_threshold` | pendiente |

Comportamiento correcto — semántica no documentada hasta DAY 82.
