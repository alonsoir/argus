# Prompt DAY304 — aRGus NDR

Contexto: DAY303 certificó con EMECAS+++ desde cero (`PROFILE=production`, 2h32m, rc=0) la rama
`fix/ddos-etapa1-histeresis` (cabeza DDoS etapa 1 con histéresis, persistencia del estado por víctima, rangos
protegidos, mitigación real E2E) y se fusionó en main. Detalle: `docs/ml-heads/day303_emecas_desde_cero.md`.

Reglas de trabajo: medir, no votar; predicción escrita antes de medir; si algo no da lo esperado, PARAR. Comandos
exactos y completos, en orden, diciendo dónde se ejecuta cada uno (Mac / defender / client). Ficheros generados
como descarga, verificados con sha256 (nada de pegar heredocs largos: comillas tipográficas). Nunca `printf >>`
sobre ficheros del repo (DAY303: `.gitignore` sin salto final rompió una regla): patchers --check/--apply con
marca. awk con `LC_ALL=C`. `git grep`, nunca `grep -rn .` en la raíz. El JSON es la ley.
Compilar siempre en producción (defecto) y el pipeline completo (`make pipeline-build`). EMECAS se lanza con
`nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null 2>&1 &` y se vigila con
`bash scripts/emecas/emecas_watch.sh 60`. `make lab-e2e` corre los cinco E2E del lab con veredicto (~65 min).

ORDEN DECIDIDO POR ALONSO (DAY303):
1. Rama nueva desde main: deprecar rag/rag-security de forma certificada. Inventario de partida (K6, DAY303):
   Makefile (27 líneas: rag-build en pipeline-build, rag-start en pipeline-start y pipeline-start-x86-libpcap,
   ctest en test-components, pipeline-status y conteo 6/6 → 5/5, stop, logs, semillas 2581-2654), Vagrantfile (6),
   etcd-server/config/ml-defender-rag-security.service + install-systemd-units.sh, set-build-profile.sh
   (COMPONENTS), AppArmor (security/apparmor/argus.rag-security, tools/apparmor/ml-defender-rag-security,
   tools/apparmor-promote.sh), Falco y setup-filesystem de vagrant/hardened-x86 y hardened-arm64,
   tools/provision.sh, scripts/pipeline_health.sh, tests que lo nombran (plugins/test-message/test_integ_4e.cpp,
   common/tests/test_crypto_autonomy.cpp, libs/seed-client/tests/test_seed_client.cpp), common-rag-ingester/build
   versionado. Medido K8: rag-security no se registra en etcd (MAC verification failed) desde septiembre.
   Criterio de HECHO: `git grep` de rag-security/rag-start/rag-build/rag/build vacío fuera de docs e históricos,
   y EMECAS+++ verde con 5/5 componentes. Valorar en la misma rama DEBT-PIPELINE-STATUS-LIVENESS-001.
2. Interruptor de cabezas (DEBT-HEADS-SWITCH-001, decisiones DAY300 en el BACKLOG).
3. Caducidad de flujos (DEBT-SNIFFER-FLOW-EXPIRY-001 + DEBT-SNIFFER-FLOWTABLE-CONFIG-001): la tabla de flujos del
   sniffer (espacio de usuario) tiene tope (16 × 10 000, LRU), así que la memoria NO crece sin límite; lo roto es
   que un flujo nunca caduca por inactividad y sus rasgos (flow_packet_count, flow_completion_rate) se deforman.
   Primeras medidas: RAM por flujo con la tabla llena, y la batería de la etapa 2 antes/después. Predicción
   (DAY303): no hará falta reentrenar, porque caducar acerca el servicio al entrenamiento; decidir con los datos.
4. Después (≈ 2 semanas): REA (BACKLOG-SEC-REA-HARDENING-AUDIT-001): primero auditoría manual del sniffer con
   predicción escrita, luego la fase asíncrona en Jenkins. Revisar antes la licencia de REA.
