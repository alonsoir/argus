# BACKLOG-SEC-REA-HARDENING-AUDIT-001 — Auditoría de hardening de binarios con REA

**Estado:** APARCADO. No tocar hasta que se cumpla el disparo.
**Disparo:** main estabilizada con al menos la cabeza DDoS operativa
(o, como muy tarde, al cierre con todas las cabezas operativas).

## Qué es
REA (https://github.com/morluto/rea, npm `rea-agents`, licencia MIT):
servidor MCP + CLI de ingeniería inversa para LLMs. Analiza binarios
nativos (Hopper / Ghidra / IDA), ELF offline (con pwntools), JS/Electron,
.NET, APK, firmware. Cada resultado sale como registro de evidencia con
procedencia (digest, proveedor, parámetros), confidence/authority y
limitaciones explícitas.

Revisado el 2026-10-08 (v6.0.0): build limpio, 1411 tests del dominio en
verde. OJO: 6 majors en ~3 meses -> no usar como dependencia, solo como
herramienta puntual. La salida JSON es enorme (31 MB para ~100 KB de
entrada): filtrar antes de pasársela a un LLM.

## Para qué
Ver aRGus con los ojos de un atacante que consigue el binario de un
sensor desplegado. Empezar por el sniffer (única pieza que recibe datos
controlados por el atacante: los paquetes).

## Predicción (escribir ANTES de medir)
- [ ] Mitigaciones: PIE / RELRO / canary / NX -> esperado: ...
- [ ] Símbolos de debug en binarios release -> esperado: ...
- [ ] Strings sensibles (rutas, claves, campos del JSON) -> esperado: ...
- [ ] Librerías dinámicas enlazadas -> esperado: ...

## Después
- Cada hallazgo confirmado -> test de regresión en el gate EMECAS.
- Valorar fuzzing de los parsers del sniffer como siguiente paso.
- Relacionado (futuro): registro de evidencia con limitaciones explícitas
  en las alertas de aRGus (idea tomada del modelo de evidencia de REA).
