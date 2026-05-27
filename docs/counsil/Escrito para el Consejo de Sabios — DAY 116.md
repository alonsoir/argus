## Escrito para el Consejo de Sabios — DAY 116

**Para:** Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Parallel.ai
**De:** Alonso Isidoro Román
**Fecha:** 13 de Abril de 2026 — DAY 116
**Rama:** feature/phase3-hardening
**Estado pipeline:** 6/6 RUNNING | 12/12 PASSED

---

### Lo que hemos completado hoy

**PASO 1 — DEBT-ADR025-D11: `provision.sh --reset` (deadline 18 Apr)**

Implementado y validado con tres tests:

- TEST-RESET-1 ✅: `--reset` regenera 6 keypairs Ed25519 + keypair de firma, con backup automático
- TEST-RESET-2 ✅: post-reset, pipeline en fail-closed (plugins con firma inválida rechazados)
- TEST-RESET-3 ✅: recuperación completa — build + sign + start → 6/6 RUNNING

Durante la implementación encontramos y resolvimos un **bug arquitectural crítico**: la primera versión de `reset_all_keys()` generaba seeds independientes para cada componente, rompiendo la invariante de CryptoTransport. HKDF deriva claves distintas desde seeds distintos → MAC fail en todos los PUTs de config. Root cause: el diseño asumía implícitamente un **seed_family compartido** (ADR-021) que nunca había sido documentado como invariante del reset. Corregido: `reset_all_keys()` genera ahora UN solo seed distribuido a los 6 componentes antes de regenerar los keypairs.

Deuda técnica identificada: **DEBT-SEED-PERM-001** — `SeedClient` emite advertencia `chmod 600` pero el permiso correcto para `seed.bin` es `640` (root:vagrant). El mensaje engañoso causó un incidente de pipeline durante el troubleshooting.

**PASO 2 — TEST-PROVISION-1 checks #6 y #7**

- Check #6 ✅: permisos ficheros sensibles (`.sk` no world/group-writable, `seed.bin` = 640)
- Check #7 ✅: consistencia JSONs — plugins referenciados con `active:true` tienen `.so` + `.sig` en `/usr/lib/ml-defender/plugins/`

El gate ahora tiene 7/7 checks. En producción actual: sin plugins activos en configs (correcto, DEBT-HELLO-001 limpiado DAY 115).

**PASO 3 — AppArmor profiles (complain mode)**

6 perfiles creados e instalados en `/etc/apparmor.d/`, copiados al repo en `tools/apparmor/`:

| Componente | Capabilities |
|---|---|
| sniffer | net_raw, net_admin, sys_admin, bpf |
| firewall-acl-agent | net_admin, net_raw |
| etcd-server, rag-security, rag-ingester, ml-detector | ninguna especial |

Todos los perfiles incluyen paths de `provision.sh --reset` (evitar bloqueo futuro) y `deny write /usr/bin/ml-defender-*`. Verificado: 0 denials en complain mode con pipeline 6/6 RUNNING + 12/12 PASSED.

Deuda técnica identificada: **DEBT-VAGRANTFILE-001** — `apparmor-utils` no estaba en el Vagrantfile de provision. Instalado manualmente hoy.

---

### PHASE 3 — Estado final

```
1. systemd units              ✅ DAY 115
2. DEBT-SIGN-AUTO             ✅ DAY 115
3. DEBT-HELLO-001             ✅ DAY 115
4. TEST-PROVISION-1 (5/5)     ✅ DAY 115
5. DEBT-ADR025-D11 --reset    ✅ DAY 116
6. TEST-PROVISION-1 (7/7)     ✅ DAY 116
7. AppArmor complain (6/6)    ✅ DAY 116
```

**PHASE 3: COMPLETA ✅**

---

### Preguntas al Consejo para DAY 117

**Q1 — AppArmor enforce strategy:**
Llevamos 6 perfiles en complain mode. El plan es: revisar audit logs tras 24h → `aa-logprof` para refinar → enforce uno a uno. ¿Recomendáis enforce en orden de menor a mayor privilegio (etcd-server primero, sniffer último) o en orden inverso? ¿Algún componente que deba permanecer en complain más tiempo?

**Q2 — DEBT-SEED-PERM-001:**
El mensaje de advertencia de `SeedClient` dice `chmod 600` pero el permiso correcto es `640` (root:vagrant). Opciones: (a) corregir solo el mensaje, (b) cambiar el modelo de permisos a `600` y hacer que los procesos corran como root, (c) documentar como known-issue y añadir al onboarding. ¿Cuál preferís?

**Q3 — Próxima fase:**
PHASE 3 completada. El backlog incluye ADR-026 (XGBoost plugins Track 1) y ADR-029 (variantes hardened). ¿Abrimos ADR-026 en DAY 117 tras resolver los DEBT pendientes, o dedicamos DAY 117 íntegro a AppArmor enforce + DEBTs antes de abrir nueva fase?

**Q4 — seed_family como ADR:**
El invariante "todos los componentes comparten seed_family" estaba implícito en ADR-021 pero nunca explicitado como requisito del reset. ¿Merece un ADR propio (ADR-033) o un addendum a ADR-021?

---

### Commits DAY 116

- `3c0a214f` — feat(ADR-025-D11): provision.sh --reset con seed_family compartido
- `e01b5919` — feat(PHASE3): TEST-PROVISION-1 checks 6+7
- `efe203bf` — feat(PHASE3): AppArmor profiles complain mode (6 componentes)

