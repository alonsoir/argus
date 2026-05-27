# CONSEJO DE SABIOS — DAY 129 — Acta de Revisión

**Fecha:** 25 abril 2026  
**Branch:** main — commit `55383638`  
**Quórum requerido:** 8/8 (Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral)

---

## Contexto de la sesión

DAY 129 completó 4 deudas técnicas, todas con evidencia RED→GREEN.
Pipeline 6/6 RUNNING. ALL TESTS COMPLETE pre y post merge.

---

## Hitos completados DAY 129

### 1. DEBT-IPTABLES-INJECTION-001 — CWE-78 CERRADA
**Surface eliminada:** 13 call-sites de `popen()`/`system()` en `iptables_wrapper.cpp`.  
**Solución:** `safe_exec.hpp` — 4 primitivos `fork()+execv()` sin shell:
- `safe_exec()` — sin output
- `safe_exec_with_output()` — captura stdout/stderr
- `safe_exec_with_file_out()` — stdout→fichero (iptables-save)
- `safe_exec_with_file_in()` — stdin←fichero (iptables-restore)

**Validadores añadidos:**
- `validate_chain_name()` — allowlist `[A-Za-z0-9_-]` 1..29 chars + null byte check explícito
- `validate_table_name()` — conjunto fijo {filter, nat, mangle, raw, security}
- `validate_filepath()` — sin `..` ni metacaracteres shell

**Evidencia:**
- `test_safe_exec.cpp`: 15/15 GREEN (4 unit + 4 property + 7 integración)
- `grep popen\|system( iptables_wrapper.cpp` → 0 resultados

**Incidencias durante implementación:**
- Fichero `.cpp` tenía markdown corruption literal (`[rule.in](http://rule.in)_interface`) — fix por número de línea
- `CRLF` en VM vs `LF` en macOS — fix por número de línea en la VM
- `INVALID_ARGUMENT` no existía en el enum — corregido a `INVALID_RULE`
- `safe_exec.hpp` línea con `\` al final de comentario → line-continuation → `validate_chain_name` no visible

---

### 2. DEBT-ETCDCLIENT-LEGACY-SEED-001 — CERRADA (parcial)
**Problema:** `EtcdClient` en `ml-detector` asignaba `component_config_path` siempre, incluso cuando `encryption_enabled=false` (endpoint con `http://`). Los tests mock usaban `http://` pero el constructor intentaba cargar `/etc/ml-defender/ml-detector/seed.bin` → excepción.

**Fix:** `component_config_path` solo se asigna cuando `encryption_enabled=true`.

**Evidencia:** `EtcdClientHmacTest` 9/9 PASSED (antes 9/9 FAILED).

**Parcial porque:** La arquitectura HTTP para distribución de claves HMAC es pre-P2P. Migración completa a ADR-024 (Noise_IKpsk3) pendiente.

---

### 3. DEBT-FEDER-SCOPE-DOC-001 — CERRADA
**Entregable:** `docs/FEDER-SCOPE.md`
- Scope mínimo viable: NDR standalone + 2 nodos Vagrant simulados
- Go/no-go técnico: **1 agosto 2026**
- Prerequisitos: ADR-026 merged + ADR-029 Variants A/B + demo pcap reproducible
- Argumento FEDER: 1 investigador + 8 AIs en 1 año → Fases 5+6 requieren financiación
- Estructura `scripts/feder-demo.sh` (implementación en backlog)

---

### 4. DEBT-FIREWALL-CONFIG-PATH-001 — CERRADA (verificación)
**Hallazgo:** `resolve_config()` ya estaba correctamente implementada y testeada.
- `config_loader.cpp` usa `argus::safe_path::resolve_config(config_path, allowed_prefix)`
- prefix siempre fijo — nunca derivado del input
- `ConfigLoaderTraversal` 3/3 GREEN (pre-existente)

**Añadido:** Tabla de verificación en `docs/SECURITY-PATH-PRIMITIVES.md`.

---

## Deuda pendiente (estado post-DAY 129)

```
⏳ DEBT-SEED-CAPABILITIES-001       → v0.6+ — CAP_DAC_READ_SEARCH
⏳ DEBT-SAFE-PATH-RESOLVE-MODEL-001 → feature/adr038-acrl
⏳ DEBT-FUZZING-LIBFUZZER-001       → DAY 130 candidato
⏳ DEBT-PENTESTER-LOOP-001          → post-FEDER
🔴 ADR-026 merge bloqueado          → CIC-IDS-2017 real fixtures pendientes
🔴 ADR-029 Variants A/B             → bloqueado por ADR-026
```

---

## Preguntas al Consejo

### P1 — REGLA PERMANENTE DAY 129 (propuesta)
Se propone formalizar la siguiente regla permanente:

> **"Toda transferencia de ficheros entre VM y macOS usa `scp -F vagrant-ssh-config` 
> o `vagrant scp`. Nunca `vagrant ssh -c "cat ..." > fichero` — el pipe zsh trunca 
> a 0 bytes silenciosamente."**

¿El Consejo aprueba añadirla como regla permanente al continuity prompt?

### P2 — build-debug en .gitignore
Los ficheros `firewall-acl-agent/build-debug/Makefile`, `build-debug/firewall-acl-agent`, 
y `build-debug/firewall_tests[1]_tests.cmake` aparecen como `Changes not staged` en cada 
sesión porque no están en `.gitignore`. ¿Añadir `**/build-debug/` al `.gitignore`?

### P3 — Prioridad DAY 130
Deuda disponible sin bloqueantes:
- A) `DEBT-FUZZING-LIBFUZZER-001` — libFuzzer sobre `validate_chain_name` + parsers ZMQ
- B) `DEBT-SEED-CAPABILITIES-001` — CAP_DAC_READ_SEARCH en systemd units
- C) Paper §5 — actualizar con property testing + safe_path taxonomy (Draft v17)

¿Cuál prioriza el Consejo para DAY 130?

### P4 — Null byte en validate_chain_name
El test `ChainNameRejectsShellMetachars` requirió constructor explícito 
`std::string("chain\\x00null", 10)` porque el literal C++ se trunca en `\\0`.
La implementación actual hace check explícito `name.find('\\0') != npos`.

¿Es suficiente este check o se recomienda también sanitizar en `safe_exec()` 
antes de pasar a `execv()` (defensa en profundidad)?

### P5 — .gitguardian.yaml deprecated keys
Warnings en cada commit:
```
Config key paths-ignore is deprecated, use paths_ignore instead.
Unrecognized key in config: paths_ignore
```
¿Vale la pena limpiar `.gitguardian.yaml` ahora o es ruido tolerable?

---

## Métricas DAY 129

| Métrica | Valor |
|---|---|
| Deudas cerradas | 4 |
| Tests añadidos | 15 (safe_exec) |
| Tests que pasaron de FAILED a PASSED | 9 (EtcdClientHmac) |
| Ficheros modificados | 6 |
| popen()/system() eliminados | 13 call-sites |
| Incidencias de entorno | 4 (CRLF, markdown corruption, zsh pipe, backslash comment) |
| Pipeline al cierre | 6/6 RUNNING |
| ALL TESTS COMPLETE | ✅ |

---

*"Via Appia Quality — Un escudo que aprende de su propia sombra."*  
*Commit: `55383638` — main*
"""

path = "/Users/aironman/CLionProjects/test-zeromq-docker/docs/CONSEJO-DAY-129-acta.md"
with open(path, "w") as f:
    f.write(content)
print(f"OK: {path}")
PYEOF


