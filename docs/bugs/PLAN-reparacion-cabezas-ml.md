# Plan de reparación de las cabezas del ml-detector

**Rama:** `diag/ml-heads` (off main @ `9f1799f8`, tag `pre-release-0.0.2`)
**Base:** informe forense `docs/bugs/Informe ml detector features centinela.MD` (4 cabezas medidas, 890/3065 splits = 29% sobre centinela −9999).
**Regla del plan:** cabeza por cabeza — **medir estado actual → arreglar → medir mejora objetivamente → decidir → siguiente.** HECHO ≠ SOSPECHADO. Si un arreglo no mejora medido, se revierte, no se justifica.

---

## Arquitectura objetivo (a validar por medición, no por decreto)

- **ml-detector (inline, tiempo real, sub-µs):** cabezas de red nativas + fast-path. Set esperado tras reparación = `{Traffic, Internal, DDoS-reparado, fast-path}`. Que DDoS-ML se quede o se colapse en el fast-path es un **resultado a medir** (¿bate el bosque DDoS a las heurísticas de rate?), no una decisión previa.
- **Ransomware → SALE del ml-detector** a un conector de dominio host sobre Wazuh. Naturaleza asíncrona: la evidencia host se acumula (I/O + FIM + proceso). El conector emite un evento de bloqueo hacia el **ipset** cuando hay evidencia segura, como segunda fuente del `firewall-acl-agent` (la respuesta pasa a ser multi-fuente, no solo ml-detector).
- **DDoS NO se externaliza:** su señal vive en la red y el bloqueo volumétrico debe ser inline. Su feature muerta (geo) es una columna removible, no un desajuste de dominio.

Principio rector de toda reparación: **el vector de entrada del modelo solo contiene features deterministamente presentes; toda feature que pueda faltar, o se excluye del modelo, o su ausencia se codifica idéntica en train y serve.**

---

## FASE 0 — Procedencia (medir el estado actual, base objetiva para todas las cabezas)

Objetivo: cuantificar la distribución de entrenamiento de cada feature muerta (la estructura del árbol YA prueba que variaban; esto pone el número) y fijar el baseline a batir. Comandos scoped a `ml-training/`, salida corta, bloques separados.

```
# 0.1 — ¿dónde se fija el VALOR DE ENTRENAMIENTO de las features muertas?
git grep -ln 'geographical_concentration\|io_intensity\|resource_usage\|file_operations\|process_anomaly\|tcp_udp_ratio\|flow_duration_std\|protocol_variety\|connection_duration_std' -- ml-training/
```

```
# 0.2 — ¿hay reportes de importancia / params de modelo committeados?
git grep -ln 'feature_importances\|importance\|feature_names' -- ml-training/
ls -la ml-training/scripts/*/model_verification_report_*.json
```

```
# 0.3 — los generadores sintéticos (cómo sintetizan cada columna)
git grep -n 'lognormal\|beta\|poisson\|np.random\|scipy.stats\|def .*generat' -- ml-training/scripts/ransomware/
```

Prioridad de lectura: **ransomware primero** (impacto 41.9%, `io_intensity` 24%), **DDoS después** (caso limpio geo). Para cada feature muerta anotar: rango/dist. de entrenamiento (o "no localizable" como hallazgo). Baseline por cabeza = `ml_score` medio sobre el Neris etiquetado por tipo de ataque (hoy ~0.07 global sobre MALICIOUS).

Métrica sistémica de la reparación (objetiva, reproducible por Makefile): **% de splits sobre centinela por cabeza** → debe caer a 0 tras el arreglo. Hoy: DDoS 6.25%, Traffic 9.6%, Internal 5.0%, Ransomware 41.9%.

---

## FASE 1 — DDoS (la más limpia, proof-of-method)

- **Medir actual:** 16 splits sobre `geographical_concentration` (idx 7, −9999 siempre); baseline `ml_score` DDoS sobre Neris; ¿qué aporta el bosque DDoS sobre el fast-path?
- **Arreglar:** quitar `geographical_concentration` del vector de entrada del modelo; reentrenar; regenerar `ddos_trees_inline.hpp`. **Conservar** el campo en el contrato protobuf como enriquecimiento opcional (desacoplar entrada del modelo de enriquecimiento).
- **Medir mejora:** % splits sobre centinela → 0; `ml_score` DDoS antes/después sobre Neris; separabilidad en held-out; **DDoS-ML vs fast-path** (¿gana el sitio?).
- **Decidir:** DDoS-ML reparado se queda inline / se colapsa en fast-path. Gate: la mejora es medida o se revierte.

## FASE 2 — Traffic

- **Medir actual:** 44 splits sobre idx 2/5/8 (`tcp_udp_ratio`, `flow_duration_std`, `protocol_variety`); baseline.
- **Arreglar:** implementar las 3 features (2 desde el aggregator ya vivo; `tcp_udp_ratio` exige campo protocolo en `FlowStatistics`); reentrenar. Alternativa si el valor real ≠ rango de entrenamiento: reentrenar con la feature implementada.
- **Medir mejora / decidir:** igual gate.

## FASE 3 — Internal

- **Medir actual:** 21 splits sobre idx 4 (`connection_duration_std`); baseline.
- **Arreglar:** implementar desde el aggregator; reentrenar.
- **Medir mejora / decidir:** igual gate.

## FASE 4 — Ransomware (arquitectónico, proyecto aparte — NO fix in-place)

- **Medir actual:** 41.9% splits sobre 4 features host (`io_intensity` 24%, `resource_usage`, `file_operations`, `process_anomaly`).
- **Arreglar (arquitectura, no columna):** retirar la cabeza ransomware del ml-detector. Diseñar el **conector wazuh-ransomware**: (a) driver que induzca comportamiento ransomware en VM Wazuh aislada (emulación benigna controlada de la firma de cifrado, NO malware real) → alerts.json; (b) reusar el camino host ya construido (`wazuh-adapter` → bronce `host_domain_v1` → oro → Kuzu host); (c) modelo de dominio host entrenado sobre esa telemetría; (d) conector asíncrono → ipset con evidencia segura, como 2ª fuente del `firewall-acl-agent`; (e) correlación red↔host por `community_id`/`flow_uid`.
- **Fuente de datos:** NO los datasets académicos de red (CTU/CIC son pcaps, no llevan señal host). Sí: dataset host-behavior de ransomware mapeado a `host_domain_v1`, o telemetría generada por emulación en la VM Wazuh.
- **Medir mejora / decidir:** esto es un arco de varias sesiones; gate por hitos (driver → telemetría → modelo → correlación).

---

## Invariantes
- Medir contra fichero, pegar salida. Fichero completo, no str_replace. `git grep` o fichero concreto, nunca `grep -rn` desde raíz. Comandos de salida grande en bloques separados.
- Reentrenar exige el pipeline de training verde; cada regeneración de `*_trees_inline.hpp` se verifica (shasum + censo) como hicimos en el diagnóstico.
- main PROTEGIDA: todo por PR cuando el arreglo esté medido. Mientras, commits en `diag/ml-heads`.
- Cada mejora se corre por el gate (`ctu-start` → dataset → medición) para que el número sea reproducible por comando.