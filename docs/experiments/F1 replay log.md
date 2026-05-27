# ML Defender — F1 Replay Log

**Fuente de verdad:** `f1_replay_log.csv`  
**Protocolo de replay:** CTU-13 Neris botnet dataset (PCAP fijo en VM)  
**Condición de comparabilidad:** dos entradas son comparables **solo si** `pcap_file` y `total_events` coinciden.

---

## Nota de honestidad científica

Las entradas DAY79 y DAY80 fueron registradas retroactivamente a partir del
prompt de continuidad del proyecto. Los `replay_id` son desconocidos — los
replays se ejecutaron en sesiones distintas sin registro sistemático previo.

El número de eventos difiere entre ambos (6810 vs 6035), lo que hace el FPR
**no comparable directamente**. Los datos se conservan con asterisco como
evidencia parcial del progreso, no como comparativa controlada.

**A partir de DAY81, cada replay recibe un `replay_id` explícito y se
registra en este fichero en el momento de ejecución.**

---

## Tabla de experimentos

| replay_id | day | date | ddos | ransom | traffic | internal | total_ev | FP | FN | F1 | Precision | Recall | notas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| UNKNOWN_DAY79 ⚠️ | 79 | 2026-03-07 | 0.70 | 0.75 | 0.70 | 6.5e-9 | 6810 | 106 | 0 | 0.9921 | 0.9844 | 1.0000 | Thresholds hardcoded. Replay distinto ⚠️ |
| UNKNOWN_DAY80 ⚠️ | 80 | 2026-03-09 | 0.85 | 0.90 | 0.80 | 0.85 | 6035 | 79 | 0 | 0.9934 | 0.9869 | 1.0000 | Thresholds JSON. Replay distinto ⚠️ |

---

## Protocolo para nuevas entradas (DAY81+)

Antes de cada replay:

```bash
# 1. Anotar el pcap en uso
vagrant ssh -c "ls -lah /vagrant/pcaps/"

# 2. Limpiar logs
make logs-lab-clean

# 3. Arrancar pipeline fresco
make pipeline-stop && make pipeline-start && sleep 15

# 4. Levantar client
vagrant up client

# 5. Ejecutar replay
make test-replay-neris
```

Después del replay, registrar en `f1_replay_log.csv`:

```
replay_id = DAY<N>_<condicion>   # ej: DAY81_thresholds_085090
date = YYYY-MM-DD
total_events, FP, FN, F1, Precision, Recall, FPR
```

---

## Comparativas controladas planificadas

| Experimento | Condición A | Condición B | Estado |
|---|---|---|---|
| Thresholds hardcoded vs JSON | 0.70/0.75 | 0.85/0.90 | ⚠️ Replay distinto — pendiente repetir |
| Thresholds conservadores vs agresivos | 0.85/0.90 | 0.70/0.75 | 📋 Planificado DAY81 |
| 28/40 features vs 40/40 features | Phase 1 | Phase 2 | 📋 Planificado post-Phase2 |
| CTU-13 Neris vs dataset balanceado | desequilibrado | balanceado | 📋 Planificado DAY81-82 |

---

*Iniciado DAY81 — 10 marzo 2026*  
*Consejo de Sabios — ML Defender*