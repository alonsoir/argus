# Consejo de Sabios — DAY 135
*aRGus NDR · arXiv:2604.04952 · 29 Abril 2026*
*Solicitud de revisión adversarial — 8 modelos*

---

## Lo que se completó en DAY 135

### EMECAS dev (04:00)
- `vagrant destroy -f && vagrant up && make bootstrap && make test-all` → ✅ ALL TESTS COMPLETE
- Línea base limpia confirmada antes de cualquier trabajo en hardened VM

### P2 — DEBT-VENDOR-FALCO-001 ✅ CERRADO
- Problema: `dist/vendor/` no existía, `vendor-download` intentaba descargar desde dev VM (fallaba)
- Solución arquitectónica: Vagrantfile dev es el **productor** de `dist/vendor/falco_*.deb` + `CHECKSUMS`
- `vendor-download` convertido en **verificador puro** (SHA-256, fail si no hay EMECAS dev previo)
- `.gitignore`: `dist/vendor/*.deb` ignorado, `dist/vendor/CHECKSUMS` committeado (D4 Consejo)
- Commits: `531b9792`

### P0 — `make hardened-full` ✅ GATE PRE-MERGE PASSED
- Implementados targets: `hardened-full`, `hardened-redeploy`, `vendor-download`
- `hardened-full`: destroy → up → vendor-download → provision → build → deploy → check
- Decisión Consejo D6 (Kimi): gate obligatorio antes de merge a main
- Bugs encontrados y corregidos durante ejecución:
    - `etcd` en apt del Vagrantfile hardened → eliminado (no existe en bookworm, aRGus lo compila)
    - `setup-falco.sh` buscaba `.deb` en `/vagrant/` → corregido a `/vagrant/dist/vendor/`
- **`check-prod-all` PASSED — 5/5 gates:**
    - BSR: no compiler ✅
    - AppArmor: 6/6 enforce ✅
    - Capabilities: cap_bpf + cap_net_admin ✅
    - Permissions: root:argus correcto ✅
    - Falco: 10 reglas aRGus cargadas ✅
- Commit: `ecce0334`

### Docs — DEBT-COMPILER-WARNINGS-001
- Documentado en BACKLOG.md: ODR violations, Protobuf dual-copy, signed/unsigned conversions
- Clasificados como no-bloqueantes para merge actual, bloqueantes para certificación formal
- Commit: `4ac23ad6`

### P1 — DEBT-PROD-APT-SOURCES-INTEGRITY-001 ✅ CERRADO (Mistral D7)
- `setup-apt-integrity.sh`: captura SHA-256 de apt sources en provisioning
- `/usr/local/bin/argus-apt-integrity-check`: verificador en boot
- `argus-apt-integrity.service` (systemd oneshot): **FailureAction=reboot** (decisión Alonso DAY 135)
    - Filosofía: nodo con apt sources comprometidos NO arranca. Fail-closed. Fail-loud. Fail-fast.
    - Riesgo de infección a toda la red aRGus via ZeroMQ/etcd es peor que un nodo parado.
- Falco regla 11: `argus_apt_sources_modified` (supply-chain detection)
- AppArmor 6/6 perfiles: `deny /etc/apt/** w` (prevención)
- Makefile: `hardened-setup-apt-integrity` + integrado en `hardened-provision-all`
- Commits: `57bbe236`, `e8709788`

### P3 — DEBT-SEEDS-DEPLOY-001 ✅ CERRADO (D2 Consejo)
- `prod-deploy-seeds`: 6 seeds + `plugin_signing.pk` desplegados en hardened VM
- Ownership correcto: `400 argus:argus` para seeds, `444 root:argus` para `.pk`
- Solo clave pública desplegada en hardened (`.sk` nunca sale de dev VM)
- `check-prod-permissions` PASSED **sin WARNs** — WARNs eliminados de forma natural
- Deuda documentada: `DEBT-SEEDS-SECURE-TRANSFER-001` (transferencia via /vagrant aceptable
  en Vagrant; producción real requiere canal cifrado directo — post-FEDER)
- Commit: `bf4c21bf`

### P4 — DEBT-CONFIDENCE-SCORE-001 ✅ CERRADO (D5 Consejo)
**Inspección estática:**
- `confidence_score` en proto (network_security.proto:350) ✅
- `set_confidence_score()` activo en `zmq_handler.cpp` ✅
- Campo poblado en CSV `2026-04-29.csv`

**Variabilidad verificada con tráfico real (tcpreplay CTU-13 Neris):**
- BENIGN: `confidence_score = 0.854557`
- RANSOMWARE_CONFIRMED: `confidence_score = 0.700000`
- `MISSING_FEATURE_SENTINEL = -9999.0` correcto por diseño (fuera del dominio RF)

**Observación:** L2 dice `RANSOMWARE_CONFIRMED` pero L1 dice `BENIGN` en los eventos del CSV.
Esto se debe a que son eventos del rag-ingester procesando features sintéticas de ransomware,
no tráfico real del sniffer. Comportamiento esperado por diseño.
- Commit: `7691f867` (--allow-empty)

### P5 — arXiv replace v15→v18 ✅ ENVIADO
- `main.tex` Draft v18 + `references.bib` subidos a arXiv:2604.04952
- Replace confirmado — Cornell procesando (~1h)

---

## Estado del branch

**Branch:** `feature/adr030-variant-a`
**Último commit:** `7691f867`
**Push:** ✅ `origin/feature/adr030-variant-a` actualizado
**`check-prod-all`:** PASSED (5/5 gates)
**`hardened-full`:** PASSED desde VM destruida

---

## Preguntas para el Consejo

### Q1 — FailureAction=reboot en argus-apt-integrity.service
Hemos implementado `FailureAction=reboot` con `TimeoutStartSec=30s` para dar tiempo
a que los logs lleguen a la central antes del reboot. La filosofía es: un nodo con
apt sources comprometidos no puede arrancar bajo ninguna circunstancia — el riesgo
de infectar toda la red aRGus via ZeroMQ/etcd es inaceptable.

**¿Están de acuerdo con esta decisión? ¿30 segundos es suficiente para que los logs
lleguen a una central de monitorización? ¿Debería ser configurable via JSON (etcd)?**

### Q2 — DEBT-SEEDS-SECURE-TRANSFER-001
Los seeds pasan brevemente por el Mac host via `/vagrant` (shared folder VirtualBox).
Esto es aceptable en Vagrant dev/test pero no en producción real (Jenkins + hardware físico).

**¿Cuál es la arquitectura correcta para la transferencia segura de seeds en producción?
Opciones consideradas:**
- (A) SSH con clave efímera generada en provisioning
- (B) Noise Protocol IK handshake directo entre dev VM y hardened VM
- (C) Seeds generados directamente en la hardened VM (elimina el problema de transferencia)
- (D) Otra opción

**¿La opción C (generación local en hardened VM) viola algún principio de ADR-013?**

### Q3 — merge de feature/adr030-variant-a a main
El gate pre-merge (`make hardened-full` PASSED) está cumplido. Los 5 checks de
`check-prod-all` pasan. Las 7 decisiones del Consejo DAY 134 están implementadas.

**¿Hay algún bloqueante técnico o arquitectónico que el Consejo identifique antes
de aprobar el merge de `feature/adr030-variant-a` a `main`?**

Elementos pendientes conocidos (no bloqueantes para el merge):
- `DEBT-COMPILER-WARNINGS-001` (warnings de compilación — pre-existentes)
- `DEBT-SEEDS-SECURE-TRANSFER-001` (transferencia segura en producción real)
- `hardened-full` no integra `prod-deploy-seeds` (intencional — D2: deploy explícito)

### Q4 — `hardened-redeploy` + `prod-deploy-seeds` en el flujo diario
Actualmente el flujo de iteración rápida es:

make hardened-redeploy        # build → deploy → check (sin destroy)
make prod-deploy-seeds        # deploy explícito de seeds (D2)
make check-prod-permissions   # verificación limpia

**¿Este flujo es correcto para el trabajo diario post-merge? ¿Debería existir
un `make hardened-full-with-seeds` que integre todo para el caso de uso
"deploy completo desde cero incluyendo seeds"?**

### Q5 — Próximos pasos post-merge
Una vez mergeado `feature/adr030-variant-a` a `main`, los candidatos para DAY 136 son:

**Opción A — BACKLOG-FEDER-001 (deadline 22 Sept 2026)**
Preparar presentación para Andrés Caro Lindo. Prerequisites: ADR-026 merged +
ADR-029 Variants A/B stable + reproducible Vagrant pcap demo.

**Opción B — ADR-029 Variant B (Debian+AppArmor+libpcap)**
Vagrantfile separado `vagrant/hardened-arm64/`. Comparativa eBPF/XDP vs libpcap
como contribución científica publicable.

**Opción C — DEBT-COMPILER-WARNINGS-001**
Rama `fix/debt-compiler-warnings-001`. ODR violations en RF inline trees,
Protobuf dual-copy en ml-detector, conversiones signed/unsigned.

**¿Cuál es la recomendación del Consejo para DAY 136?**

---

## Reglas permanentes confirmadas en DAY 135

- **REGLA EMECAS dev:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
- **REGLA EMECAS hardened:** `make hardened-full` (destroy incluido, gate pre-merge)
- **REGLA EMECAS hardened iter:** `make hardened-redeploy` (sin destroy, iteración rápida)
- **REGLA vendor:** Vagrantfile dev produce `dist/vendor/CHECKSUMS`. `vendor-download` solo verifica.
- **REGLA seeds:** NO en EMECAS. `prod-deploy-seeds` explícito (D2 Consejo DAY 134).
- **REGLA apt-integrity:** `FailureAction=reboot`. Nodo comprometido no arranca. Sin excepciones.
- **REGLA macOS sed:** nunca `sed -i` sin `-e ''`; usar `python3` para ediciones.

---

*DAY 135 cerrado — 29 Abril 2026*
*Commits: 531b9792..7691f867 · check-prod-all PASSED · arXiv v18 enviado*
*"Fail-closed. Fail-loud. Fail-fast. Sin excepciones."* 🏛️
