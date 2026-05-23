# ── PROMPT DE CONTINUIDAD DAY 162 ──────────────────────────────────────────────
prompt = """# PROMPT DE CONTINUIDAD — aRGus NDR DAY 162
*Generado: 2026-05-23 · Branch: feature/day161-cicd-pipeline (pendiente merge)*

---

## Contexto esencial

Proyecto: aRGus NDR — C++20 NDR open-source para infraestructura crítica (hospitales, municipios).
PI: Alonso Isidoro Román (Badajoz). Paper: arXiv:2604.04952. Colaboración: Dr. Andrés Caro Lindo (UEx/INCIBE).
Metodología: TDH, EMECAS++, Consejo de Sabios (8 modelos), Via Appia Quality.

**EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
**EMECAS++:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all && make test-e2e`

---

## Estado al inicio de DAY 162

### Git
- `main` en `v0.9.4-day160` (commit `178a1fb5`)
- Branch activa: `feature/day161-cicd-pipeline` — **PENDIENTE EMECAS++ y merge a main**
- Commits DAY 161: `79bcea48` · `e912ec4c` · `21096b23` · `f0ef51df` · `3c5a6d24` · `634cc1fe`

### Lo que se hizo en DAY 161
1. ✅ **DEBT-WIRE-PROTOCOL-TEST-001 CERRADA** — `common/tests/test_wire_protocol.cpp` 6/6 tests. Integrado en CMakeLists + `make test-wire-protocol`. El bug DAY 98 no puede repetirse.
2. ✅ **Jenkinsfile.dev + Jenkinsfile.prod** — `Jenkinsfile` renombrado a `.prod`. `.dev` nuevo con `agent any`.
3. ✅ **DEBT-E2E-LIVE-DELTA-001 parcial** — `test-e2e-live` usa modo `snapshot → 60s → check` (delta). Falta inyector sintético.
4. 📋 DEBT-CONFIG-JINJA2-PIPELINE-001 documentada (varios días, post-hardware UEx)
5. 📋 DEBT-PACKAGE-DEB-001 documentada (post-FEDER)
6. ✅ Consejo de Sabios DAY 161 — 8/8 respondieron, síntesis guardada.

### Decisiones del Consejo DAY 161
- **Q5 DAY 162:** A) SURICATA primero (6/8), luego B) NTP en DAY 163-164
- **DEBT-WIRE-CRYPTO-INTEGRATION-TEST-001** abierta P2 — test integración CryptoTransport completo, post-Suricata
- **test-e2e-live:** inyectar sintético mínimo (pendiente mini-fix DAY 162 antes de Suricata)

### VM
- `defender` RUNNING
- Vault unsealed (`VAULT_ADDR=http://127.0.0.1:8200`)

---

## PRIMER PASO obligatorio DAY 162

### 1. EMECAS++ en la rama actual
```bash
vagrant status
make vault-dev-start
vagrant destroy -f && vagrant up && make bootstrap && make test-all && make test-e2e
```

Si EMECAS++ verde → PR de `feature/day161-cicd-pipeline` → merge main → tag `v0.9.5-day161`.

### 2. Mini-fix inyector sintético (antes de Suricata)
El `test-e2e-live` falla en Vagrant si no hay tráfico orgánico. Añadir inyección mínima:
- Opción simple: `ping -c 3 8.8.8.8` o `curl -s http://example.com` antes del `sleep 60`
- Alternativa: usar el injector sintético existente para garantizar ≥1 evento

### 3. DEBT-ARGUSPP-SURICATA-001 (ADR-048 F2)
Primera señal externa al pipeline. Decisión Consejo: inotify sobre `/var/log/suricata/eve.json`.
- Suricata ya está en el Vagrantfile (`make up-suricata` disponible)
- AppArmor para Suricata OBLIGATORIO antes de despliegue
- Solo eventos `alert` con `community_id` para correlación inicial

---

## Deudas activas ordenadas por prioridad

| DEBT | Prioridad | Estado | Target |
|------|-----------|--------|--------|
| DEBT-ARGUSPP-SURICATA-001 | 🔴 P0 | OPEN | DAY 162 — ADR-048 F2 |
| DEBT-ARGUSPP-NTP-001 | 🔴 P0 | OPEN | DAY 163-164 — prerequisito correlación |
| DEBT-E2E-LIVE-DELTA-001 | 🟡 P1 | 60% | DAY 162 mini-fix — inyector sintético |
| DEBT-WIRE-CRYPTO-INTEGRATION-TEST-001 | 🟡 P2 | OPEN | post-Suricata |
| DEBT-CONFIG-JINJA2-PIPELINE-001 | 🟡 P2 | Documentada | varios días + hardware UEx |
| DEBT-PACKAGE-DEB-001 | 🟡 P2 | Documentada | post-FEDER |
| DEBT-ALERTING-LIBCRYPTO-PROVIDER-001 | 🟡 P1 | OPEN | mover AlertClient a libcrypto_provider.so |
| DEBT-CRYPTO-AUTONOMY-001 | 🟡 P1 | OPEN | EXTENDED_AUTONOMY state machine |
| DEBT-JENKINS-PROD-001 | 🔴 P0 | OPEN | post-hardware UEx |

---

## Constantes técnicas permanentes

- **Keypair activo:** regenera en cada `vagrant destroy+up` — leer de `/etc/ml-defender/etcd-server/public.pem`
- **Vault dev:** no persiste entre sesiones — `make vault-dev-start` al inicio
- **File edits en macOS:** siempre Python3 heredoc (`python3 << 'PYEOF'`), nunca `sed -i` sin `-e ''`
- **Vagrant:** siempre `vagrant ssh -c '...'` desde macOS host; nunca desde dentro de la VM
- **JSON is the law:** configs desde JSON canónico, originales SAGRADOS
- **`-Werror`:** 0 warnings es invariante permanente
- **`alert_client.hpp`** NUNCA incluir en componentes que linkean `libetcd_client.so` (DEBT-ALERTING-LIBCRYPTO-PROVIDER-001)
- **PR obligatorio:** no merge directo a main, siempre PR en GitHub
- **EMECAS++ antes de mergear:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all && make test-e2e`

---

## Contexto estratégico

- Gate real UEx/INCIBE = datasets de valor científico (no demo NDR)
- ADR-048: 5 fases de señal creciente (F1=aRGus done, F2=+Suricata, F3=+Zeek, F4=+Wazuh, F5=+Neo4j)
- community_id = pegamento entre engines para correlación temporal
- FEDER deadline 22-Sep-2026 = referencia de ritmo, no deadline duro
- Principio rector: calidad sobre fechas — los datasets se generan cuando el pipeline esté listo
  """

