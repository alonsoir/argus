# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 248

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git branch --show-current
    git tag | grep pre-release
    vagrant status
Tras DAY 247: feat/zeek-to-graph MERGEADA a main, tag pre-release-0.0.1 sobre main.
Si sigues en feat, `git checkout main && git pull`. VMs probablemente aborted.

## Estado que ordena el día — pipeline cerrado y etiquetado; empieza el proyecto que queda
- ✅ Pipeline multi-sensor COMPLETO y en main: aRGus/Suricata/Zeek/Wazuh → MITRE (nmap) →
  DOS grafos Kuzu (red correlation_v1 + host host_domain_v1). Integridad HMAC real e2e en los
  3 sensores de red (A, con guards). host-engine en el gate. emecas+++ VERDE from-scratch (2h01m).
- ✅ Tag pre-release-0.0.1 = hito del PIPELINE. NO es el estado de datos del paper.
- 🎯 PROYECTO QUE QUEDA: herramienta(s) de generación de DATASETS desde los grafos.
  Prerequisito de los datos del paper y del tag 0.0.2. Ver [[dashboard-export]] para el scope
  ya decidido (DAY 244): serie de herramientas → CSV de mediciones sobre el grafo de RED,
  rumbo a Hugging Face con gate de calidad. El FIN real: afinar el pipeline como instrumento
  científico en las tres lentes (aRGus/Suricata/Zeek); los datasets son subproducto de esa calidad.

## Batalla candidata DAY 248 — arrancar la herramienta de datasets (medir primero)
1. MEDIR qué expone el grafo: leer schema.cypher (correlation-engine/schema/) y correr kuzu_query
   sobre una BD de red fresca (la última de mitre-start sirve) para inventariar nodos/aristas/
   propiedades REALES consultables. No diseñar el export sin ver qué hay.
2. Decidir la PRIMERA medición-dataset (una, no todas): p.ej. por cada NetworkFlow, sus features
    + source_sensor + si está corroborado cross-sensor. CSV plano, reproducible desde un comando.
3. Esqueleto de la herramienta como target del Makefile (reproducibilidad = propiedad del repo):
   `dataset-export` que corre kuzu_query(s) → CSV en ruta canónica. Empezar por el grafo de RED.
4. La herramienta es la cazadora de bugs desconocidos: al extraer sistemáticamente, anota toda
   inconsistencia (p.ej. el conocido argus N filas→M TelemetryEvent — ¿pérdida real o mapeo?).

## Deudas DIFERIDAS post-0.0.1 (apuntadas, NO bloqueantes)
DEBT-HMAC-KEY-INSECURE-TRANSPORT-001 (transporte HMAC HTTP plano; fix = Vault HTTPS/auth/leases) ·
Vault productivo · rotación de claves real · fault-injection real ·
DEBT-ENV-BOOTSTRAP-NOT-REPRODUCIBLE-001 (pipeline-start no arrastra build) ·
DEBT-ADAPTER-AUTOMATION-DOWNSTREAM-001 (B: adapter autónomo — auto-obtención curl + folder-watch
+ procesados/) · DEBT-MITRE-START-WAZUH-REACT-001 · bugs menores del harness
  (test_integ_sign abort, sign-plugins manual tras rebuild).

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando/fichero.
- Un día, una batalla. Vía Appia (bronce/oro = fuente de verdad; grafo = proyección).
- Reproducibilidad = propiedad del repo: todo dato del paper, generable por un comando del Makefile.
- Grafo RED = fresco por medición; grafo HOST = nombre estable (acumular vs por-corrida, pendiente).
- No datasets per se: el fin es el instrumento; los datasets salen cuando pasen el gate de calidad
  (irán a Hugging Face solo entonces). NO entregar el pcap-replay CTU (check de fontanería, no deliverable).
- sed -i de macOS/BSD exige sufijo de backup: `sed -i ''`. Alonso no tiene str_replace: entregar
  script parcheador (idempotente, ancla por texto) o fichero completo.

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. Ya en main (post-merge). Hilos de memoria:
[[dashboard-export]] (datasets, scope DAY 244), [[cierre-paper]] (roadmap + tesis honesta del paper),
[[parquet-a-kuzu]] (loader/consulta del grafo red), [[host-a-kuzu]] (grafo host),
[[hmac-secrets-provisioning]] (A hecha / B pendiente / secretos).