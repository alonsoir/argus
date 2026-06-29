cat > /Users/aironman/CLionProjects/test-zeromq-docker/docs/CONSEJO-DAY-128.md << 'EOF'
# Consejo de Sabios — DAY 128

**Fecha:** 2026-04-24  
**Modelos:** Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral  
**Branch:** `main` — Tag: `v0.5.2-hardened`

---

## Resumen ejecutivo DAY 128

DAY 128 fue un día de documentación, consolidación y un hallazgo técnico
imprevisto que resultó ser más profundo de lo esperado.

### Hitos completados

1. **VM nueva desde cero** — vagrant destroy + up + bootstrap. Pipeline 6/6 RUNNING.

2. **Hallazgo técnico: `resolve_seed()` enforza `0400 root:root`**  
   Al reconstruir la VM, el pipeline no arrancaba. Root cause: todos los componentes
   que leen seeds vía `resolve_seed()` deben correr con `sudo` — la invariante de
   seguridad `0400` es estricta y no negociable. Fix: etcd-server, ml-detector,
   rag-ingester arrancan con `sudo env LD_LIBRARY_PATH=...` en el Makefile.

3. **DEBT-PROVISION-PORTABILITY-001** ✅ — `ARGUS_SERVICE_USER` variable en
   `provision.sh`. Seeds `0400 root:root` — invariante intacta.

4. **DEBT-SAFE-PATH-TAXONOMY-DOC-001** ✅ — `docs/SECURITY-PATH-PRIMITIVES.md`:
   taxonomía completa de las 4 primitivas safe_path con diagrama de decisión,
   PathPolicy enum conceptual, ejemplos correcto/incorrecto.

5. **DEBT-PROPERTY-TESTING-PATTERN-001** ✅ — `docs/testing/PROPERTY-TESTING.md`
    + 5 property tests GREEN en `contrib/safe-path/tests/test_safe_path_property.cpp`.
      Integrados en `make test-all` vía `make test-libs`.

6. **DEBT-SNYK-WEB-VERIFICATION-001** ✅ — 18 findings triados:
    - 5 falsos positivos cerrados
    - 11 contrib/tools no alcanzables
    - 1 HIGH nuevo: `DEBT-IPTABLES-INJECTION-001` (CWE-78, iptables_wrapper)
    - 1 pendiente: `DEBT-FIREWALL-CONFIG-PATH-001` (CWE-23)

7. **DEBT-ETCDCLIENT-LEGACY-SEED-001** — Reclasificado. Los `EtcdClientHmacTest`
   no son regresión — son código legado pre-P2P (ADR-026/027). EtcdClient aún
   intenta leer seed vía `resolve_seed()`. Pendiente cleanup post-ADR-024.

---

## Preguntas al Consejo

### P1 — Invariante `0400` vs portabilidad

`resolve_seed()` enforza exactamente `0400`. La consecuencia es que cualquier
componente que lea seeds debe correr con `sudo`. En la arquitectura actual esto
es correcto — los seeds son material criptográfico de sistema, no de usuario.

**¿Veis algún riesgo en esta decisión? ¿Hay alternativas que no relajen la
invariante pero eviten la necesidad de `sudo` generalizado?**

### P2 — Property testing como gate de merge

DAY 128 introduce el patrón formal de property testing. Los 5 tests actuales
cubren `resolve_seed`, `resolve_config` y `resolve` general. El patrón dice
que toda superficie crítica con operaciones aritméticas o de paths debe tener
property tests.

**¿Qué otras superficies del pipeline deberían tener property tests prioritariamente?
Candidatos identificados: `compute_memory_mb` (F17), parsers ZeroMQ, serialización
protobuf, HKDF key derivation.**

### P3 — `DEBT-IPTABLES-INJECTION-001` (CWE-78)

`IPTablesWrapper::cleanup_rules()` llama a `execute_command(cmd)` donde `cmd`
podría contener input no sanitizado. Es el finding más crítico del análisis Snyk.

**¿Cuál es la estrategia correcta para sanitizar comandos iptables en C++?
Opciones: (a) whitelist de comandos permitidos, (b) execve() directo sin shell,
(c) libiptc (API nativa iptables sin fork/exec). ¿Alguna preferencia del Consejo?**

### P4 — Arquitectura P2P seeds vs etcd-server

`DEBT-ETCDCLIENT-LEGACY-SEED-001` revela que el `EtcdClient` todavía intenta
leer seeds del filesystem — el modelo pre-P2P. En el modelo P2P (ADR-026/027),
los seeds se distribuyen entre pares, no via etcd.

**¿Cuál es la secuencia correcta de cleanup? ¿Primero implementar ADR-024
(Noise_IKpsk3) y luego limpiar EtcdClient, o se puede limpiar EtcdClient antes
de tener ADR-024 funcional?**

### P5 — Demo FEDER (deadline: 22 septiembre 2026)

La pregunta crítica pendiente del Consejo DAY 127: ¿la demo FEDER requiere
federación funcional (ADR-038) o es suficiente con NDR standalone?

**¿Cuál es vuestra recomendación para el scope mínimo viable de la demo FEDER
dado el deadline de septiembre 2026?**

---

## Estado del sistema al cierre DAY 128

Branch:  main — v0.5.2-hardened
Pipeline: 6/6 RUNNING
Tests:   ALL TESTS COMPLETE (EtcdClientHmacTest: legacy, no bloqueante)
Deudas activas bloqueantes: DEBT-IPTABLES-INJECTION-001
Deudas activas no bloqueantes: DEBT-FIREWALL-CONFIG-PATH-001
DEBT-ETCDCLIENT-LEGACY-SEED-001

---

## Commits DAY 128

858895c docs: DAY 128 PASO 4 — SNYK-DAY-128.md + deudas nuevas
eab031a docs: DAY 128 — reclasificar DEBT-HMAC-REGRESSION-001 como legado pre-P2P
06040db test+docs: DAY 128 PASO 2 — property tests safe_path + PROPERTY-TESTING.md
9ef0590 docs: DAY 128 PASO 1 — SECURITY-PATH-PRIMITIVES.md + DEBT-HMAC-REGRESSION-001
33c54d6 fix: DAY 128 — pipeline-start sudo + seed permisos 0400 root:root