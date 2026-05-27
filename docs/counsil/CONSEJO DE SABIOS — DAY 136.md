# Consejo de Sabios — DAY 136
# aRGus NDR — feature/adr030-variant-a MERGEADO A MAIN
# Fecha: 2026-04-29

## Contexto

DAY 136 del proyecto aRGus NDR (C++20, open-source, infraestructura crítica).
Branch feature/adr030-variant-a ha sido mergeado a main y taggeado como
v0.6.0-hardened-variant-a.

## Lo que se completó hoy

### EMECAS PASSED (vagrant destroy && vagrant up completo)
- 6 binarios compilados en production: sniffer, ml-detector, etcd-server,
  firewall-acl-agent, rag-ingester, rag-security
- 6 librerías propias: seed-client, crypto-transport, etcd-client,
  plugin-loader, rag-security (FAISS+ONNX+llama.cpp), rag-ingester
- Ed25519 signing automático sobre binarios y plugins
- AppArmor 6 perfiles enforce, capabilities sin SUID, BSR verificado
- Falco 11 reglas argus activas
- Seeds 6 componentes + plugin_signing.pk desplegados sin WARNs

### Gates superados
- make hardened-full → PASSED
- make prod-deploy-seeds → PASSED
- make check-prod-all → PASSED (sin warnings)

### Merge y documentación
- KNOWN-DEBTS-v0.6.md creado (6 deudas documentadas)
- Merge --no-ff feature/adr030-variant-a → main
- Tag v0.6.0-hardened-variant-a publicado
- Target hardened-full-with-seeds añadido al Makefile (FEDER ONLY)

## Deudas documentadas en KNOWN-DEBTS-v0.6.md
- DEBT-COMPILER-WARNINGS-001 (LTO/ODR, OpenSSL 3.0 deprecated, GTest)
- DEBT-SEEDS-SECURE-TRANSFER-001 (seeds via Mac host — solo Vagrant)
- DEBT-SEEDS-LOCAL-GEN-001
- DEBT-SEEDS-BACKUP-001
- DEBT-IRP-NFTABLES-001 (argus-network-isolate pendiente — ADR-042 E1)
- DEBT-IRP-QUEUE-PROCESSOR-001 (ADR-042 E3)

## Próximo hito: DAY 137
- PASO 5: git checkout -b feature/variant-b-libpcap
- Vagrantfile sin eBPF headers, con libpcap-dev
- Objetivo: delta XDP vs libpcap publicable para paper + FEDER

## Pregunta al Consejo

Con v0.6.0-hardened-variant-a en main y el pipeline E2E hardened
reproducible desde vagrant destroy:

1. ¿Qué riesgos técnicos o arquitectónicos veis en el estado actual
   que deberían resolverse ANTES de la demo FEDER (1 agosto 2026)?

2. Para feature/variant-b-libpcap: ¿qué diferencias de diseño
   críticas anticipáis entre la capa de captura XDP y libpcap que
   deberían documentarse como contribución científica para el paper?

3. ¿Alguna deuda en KNOWN-DEBTS-v0.6.md os preocupa especialmente
   para el contexto de infraestructura crítica (hospitales, municipios)?

La verdad por delante, siempre.