Leyendo todos los documentos. Sintetizo:

```bash
cat > docs/counsil/DAY135_consejo_sintesis.md << 'EOF'
# Consejo de Sabios — Síntesis DAY 135
*aRGus NDR · arXiv:2604.04952 · 29 Abril 2026*
*Modelos presentes: Claude, ChatGPT, DeepSeek, Gemini, Kimi, Mistral, Qwen (7/8)*
*Ausente: Grok (problemas técnicos — posiblemente en reentrenamiento)*

---

## Veredicto global

**MERGE APROBADO — 7/7 modelos presentes, sin bloqueantes técnicos.**

---

## Q1 — `FailureAction=reboot` + timeout

### Consenso (6/6)
- **`FailureAction=reboot` APROBADO** — filosofía correcta sin excepción.
- **NO hacer configurable via etcd/JSON** — consenso fuerte (5/6).
  - Razón: bootstrapping circular. Si apt está comprometido, el canal
    de configuración también podría estarlo. La política debe ser
    estática, verificable en binario, independiente de red.
  - Excepción: ChatGPT y Mistral aceptarían configurabilidad con mínimo
    hardcodeado (30s floor), pero el resto lo rechaza.

### Divergencia: timeout
- **30s:** Claude (suficiente en red local estable)
- **60s:** ChatGPT, Mistral (hospitales rurales, redes lentas)
- **Mecanismo en lugar de timeout:** Qwen, Gemini
  ```ini
  ExecStopPre=/usr/bin/journalctl --flush
  ExecStopPre=/usr/bin/logger -p auth.crit "APT INTEGRITY FAILED: rebooting"
  ```
Esta aproximación es más robusta: garantiza flush antes del reboot
independientemente del tiempo de red.

### Mejoras adicionales consensuadas
- `Requires=rsyslog.service` + `After=rsyslog.service` (Mistral, Qwen)
- Documentar en `docs/OPERATIONS.md` que syslog remoto debe estar
  configurado antes de activar la política (Claude, ChatGPT)
- Crear `DEBT-APT-TIMEOUT-CONFIG-001` para post-FEDER (DeepSeek)

### Aportación única de Kimi (Q1)
`StartLimitIntervalSec=300` + `StartLimitBurst=2` — anti-bootloop:
si el check falla 2 veces en 5 minutos, systemd marca la unidad como
failed y NO reintenta. Evita que un bug en el script convierta el nodo
en un brick de reboot cíclico. **Adoptar.**

### Decisión adoptada
Implementar `ExecStopPre=/usr/bin/journalctl --flush` +
`ExecStopPre=/usr/bin/logger -p auth.crit` antes del reboot.
Aumentar timeout de 30s a 60s. NO configurable via etcd ahora.
Añadir `StartLimitIntervalSec=300` + `StartLimitBurst=2` (anti-bootloop).

---

## Q2 — DEBT-SEEDS-SECURE-TRANSFER-001

### Consenso unánime (6/6): **Opción C — generación local en hardened VM**

**¿Viola ADR-013?** → NO (6/6 coinciden)
- ADR-013 prohíbe seeds hardcodeados, no generación local.
- La generación local refuerza "conocimiento cero" por parte del host.
- Unicidad garantizada por `getrandom()` / `/dev/urandom`.

**Condiciones para implementar Opción C:**
1. Mismo script de generación (`tools/generate_seed.sh` o equivalente)
2. Permisos `0400 argus:argus` inmediatos post-generación
3. `mlock()` para seed en memoria
4. **Backup obligatorio** en almacenamiento aislado
   (YubiKey / offline vault) — señalado por Qwen como crítico
5. Documentar en ADR-013 como sección adicional

**Para Vagrant dev/test:** mantener `/vagrant` (aceptable en contexto aislado)
**Para producción real (post-FEDER):** Opción C + backup offline

**Deuda a crear:** `DEBT-SEEDS-LOCAL-GEN-001`

---

## Q3 — Merge a main

### Consenso unánime (6/6): **APROBADO, sin bloqueantes**

Condiciones menores post-merge coincidentes:
- Tag `v0.6.0-hardened-variant-a` con release notes (Qwen, Gemini)
- Actualizar README.md con comandos `hardened-full`, `hardened-redeploy` (DeepSeek)
- Merge con `--no-ff` para preservar historial de branch (Mistral)
- Crear `docs/KNOWN-DEBTS-v0.6.md` listando deudas no bloqueantes (Qwen)

Deuda de validación documentada (Claude): el ciclo completo
destroy→check con seeds nunca se ha validado de una sola pasada.
No bloqueante, sí documentable.

---

## Q4 — Flujo diario + ¿`hardened-full-with-seeds`?

### Consenso (5/6): **Mantener separación actual**

Flujo correcto validado:
```
make hardened-redeploy       # infra: build → deploy → check
make prod-deploy-seeds       # secretos: deploy explícito (D2)
make check-prod-permissions  # verificación limpia
```

**¿Añadir `hardened-full-with-seeds`?**
- Mayoría: SÍ, pero **marcado explícitamente como TEST/FEDER ONLY**
- Nombre propuesto: `hardened-full-with-seeds` (ChatGPT, Qwen)
  o `hardened-full-deploy` (Claude) para denotar material criptográfico real
- **NUNCA** en pipelines de producción ni CI automático

Implementación consensuada:
```makefile
hardened-full-with-seeds:
    @echo "⚠️  TESTING/FEDER ONLY — no usar en producción"
    $(MAKE) hardened-full
    $(MAKE) prod-deploy-seeds
    $(MAKE) check-prod-all
    @echo "✅ Entorno hardened completo + seeds listo para testing"
```

Mejora adicional (DeepSeek): mensaje post-`hardened-full` recordando
ejecutar `prod-deploy-seeds`.

**Aportación única de Kimi (Q4):** `check-prod-all` debe verificar
condicionalmente — si `encryption_enabled=true`, entonces seed debe
existir. En EMECAS el check pasa (componentes no activos). En
operación real fallaría explícitamente si falta el seed.
**Adoptar como deuda:** `DEBT-CHECK-PROD-SEED-CONDITIONAL-001`

---

## Q5 — Próximos pasos DAY 136

### Resultado de votación:

| Modelo | Recomendación | Justificación clave |
|--------|--------------|---------------------|
| Claude | **A (FEDER)** | Deadline no trivial, prerequisites no triviales |
| ChatGPT | **B (libpcap)** | Validación en hardware real, portabilidad |
| DeepSeek | **A (FEDER)** | Hito crítico para financiación |
| Gemini | **B (libpcap)** | Delta XDP/libpcap = argumento irrefutable para revisores |
| Mistral | **B (libpcap)** | Prerequisito científico para FEDER |
| Kimi | **B (libpcap)** | Prerequisito FEDER; delta XDP/libpcap no existe en literatura para NDR open-source ARM |
| Qwen | **B (libpcap)** | Variant B es prerequisito para demo FEDER completa |

**Mayoría: B (libpcap) — 5/7**
**Minoría: A (FEDER directo) — 2/7**

### Argumento ganador (Qwen + Mistral + Gemini):
Variant B no es alternativa a FEDER — **es prerequisito**.
La demo FEDER sin métricas ARM/libpcap cubre solo x86, reduciendo
alcance y contribución científica. La comparativa XDP vs libpcap
es además publicación independiente (arXiv cs.CR).

### Cronograma consensuado:
- **MAY-JUN:** Variant B estable + benchmarks x86 vs ARM64
- **JUL:** `scripts/feder-demo.sh` + §6.9 paper con métricas reales
- **AGO:** Dry-run FEDER + hardening final
- **SEP 22:** Presentación Andrés Caro Lindo

### Opción C (warnings):
Todos: post-FEDER o en batch durante refactorización. No urgente.

---

## Decisiones vinculantes DAY 136

**D1:** Merge `feature/adr030-variant-a` → `main` con `--no-ff`
**D2:** Tag `v0.6.0-hardened-variant-a` + release notes
**D3:** `argus-apt-integrity.service`: añadir `ExecStopPre` flush +
aumentar timeout a 60s + `Requires=rsyslog.service`
**D4:** Crear `DEBT-SEEDS-LOCAL-GEN-001` en BACKLOG
**D5:** Crear `DEBT-APT-TIMEOUT-CONFIG-001` en BACKLOG
**D6:** Añadir `hardened-full-with-seeds` (TEST/FEDER ONLY) en Makefile
**D7:** Iniciar `feature/variant-b-libpcap` — ADR-029 Variant B

---

## Nuevas deudas identificadas por el Consejo

| ID | Descripción | Severidad | Plazo |
|----|-------------|-----------|-------|
| DEBT-APT-TIMEOUT-CONFIG-001 | Timeout apt-integrity configurable (min 30s hardcoded) | 🟡 Media | post-FEDER |
| DEBT-SEEDS-LOCAL-GEN-001 | Generación local seeds en hardened VM (Opción C) | 🔴 Alta | post-FEDER |
| DEBT-SEEDS-BACKUP-001 | Backup offline obligatorio de seeds (YubiKey/vault) | 🔴 Alta | post-FEDER |
| DEBT-FEDER-DEMO-SCRIPT-001 | `scripts/feder-demo.sh` reproducible | 🟡 Media | DAY 136+ |

---

*DAY 135 — Síntesis Consejo de Sabios — 29 Abril 2026*
*7/8 modelos · Grok ausente (reentrenamiento)*
*"Un escudo que no se prueba contra el ataque real es un escudo de teatro."* 🏛️
EOF
echo "OK: DAY135_consejo_sintesis.md creado"
```