# Consejo de Sabios — DAY 115 Cierre
**Fecha:** 2026-04-12 (DAY 115, domingo)
**De:** Alonso Isidoro Román
**A:** Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Parallel.ai

---

## Resumen de lo realizado hoy

DAY 115 comenzó a las 05:07. Se trabajaron 4 de los 6 ítems de PHASE 3
(operación segura del pipeline) y se cerraron las 4 OQs bloqueantes de ADR-024.

### Hitos completados

**ADR-024 OQ-5..8 — CERRADAS (unanimidad Consejo)**
- OQ-5: `allowed_static_keys` en deployment.yml + caché local + re-provision si seed_family comprometida
- OQ-6: Dual-key T=24h + versioned deployment.yml + secuencia 5 pasos cero downtime
- OQ-7: Riesgo replay aceptado v1 + nftables rate-limiting + trigger v2 si WAN
- OQ-8: Noise_IKpsk3 mantenido + benchmark ARMv8 obligatorio pre-producción
- ADR-024 actualizado con Recovery Contract y 2 nuevos tests (TEST-INTEG-8/9)

**PHASE 3 ítems 1-4 completados:**

1. **systemd units (6 componentes):**
    - `Restart=always`, `RestartSec=5s`, `Environment="LD_PRELOAD="` en todos
    - `set-build-profile.sh`: symlinks `build-active → build-debug|release`
    - `EnvironmentFile=/etc/ml-defender/build.env` para cambio de perfil sin editar units
    - DEBT-RAG-BUILD-001 registrado (rag/ no sigue convención build-debug/build-release)
    - DEBT-SYSTEMD-001: checklist completo para despliegue en Raspberry Pi documentado

2. **DEBT-SIGN-AUTO:**
    - `provision.sh check-plugins` — firma automática solo en provisioning
    - `provision.sh check-plugins --production` — verify-only, falla si .sig ausente/inválido
    - Idempotente: .sig válido para clave actual → skip
    - Distinción provisioning/producción implementada y verificada

3. **DEBT-HELLO-001:**
    - `plugins/hello/CMakeLists.txt`: guard `BUILD_DEV_PLUGINS=OFF`
    - `libplugin_hello` eliminado de 5 JSONs de producción
    - **Hallazgo crítico:** 4 componentes tenían `active:true` — bug de seguridad resuelto
    - `make validate-prod-configs`: falla si libplugin_hello en cualquier JSON prod

4. **TEST-PROVISION-1 (CI gate):**
    - 5 checks encadenados: claves, firmas, configs, symlinks, systemd units
    - `pipeline-start` ahora depende de `test-provision-1`
    - Cada check falla con instrucción de fix específica
    - TEST-PROVISION-1 PASSED 5/5 verificado en VM

**Commits:** df976d90, a1b23882, incluido en feature/phase3-hardening

---

## Estado PHASE 3

```
1. systemd units         ✅ COMPLETADO
2. DEBT-SIGN-AUTO        ✅ COMPLETADO
3. DEBT-HELLO-001        ✅ COMPLETADO
4. TEST-PROVISION-1      ✅ COMPLETADO
5. AppArmor profiles     ← DAY 116
6. DEBT-ADR025-D11       ← DAY 116 (deadline 18 Apr, NO SE MUEVE)
```

---

## Preguntas para el Consejo

### Q1 — AppArmor: ¿modo complain primero o enforce directamente?

El plan es crear 6 perfiles AppArmor (uno por componente).
El sniffer requiere `CAP_BPF`, `CAP_SYS_ADMIN` — capabilities amplias.
El firewall-acl-agent requiere `CAP_NET_ADMIN` para iptables/ipset.

**Pregunta:** Para el entorno Vagrant/Debian de desarrollo, ¿es correcto
el flujo `complain → verificar pipeline OK → enforce`?
¿O hay argumentos para ir directamente a enforce dado que el pipeline ya
está bien caracterizado después de 115 días?

**Restricción:** Los perfiles deben funcionar también en Raspberry Pi ARM64
(Debian 13). ¿Hay diferencias en AppArmor entre x86 Vagrant y ARM64 RPi
que debamos anticipar?

### Q2 — DEBT-ADR025-D11: `provision.sh --reset` scope

`provision.sh --reset` debe regenerar todo el material criptográfico:
seed_family, keypairs Ed25519 de componentes, keypair de firma de plugins.

**Pregunta:** ¿Debe `--reset` también invalidar y re-firmar todos los plugins
automáticamente (llamando a `check-plugins` después de rotar claves)?
¿O debe ser un proceso manual en dos pasos para máximo control?

**Restricción:** La firma automática en producción está explícitamente prohibida
(Consejo DAY 114). ¿Cómo encaja `--reset` en producción donde no debe haber
firma automática?

### Q3 — Orden AppArmor vs DEBT-ADR025-D11

El deadline de DEBT-ADR025-D11 es el 18 Apr (6 días).
AppArmor no tiene deadline pero es requisito previo para producción.

**Pregunta:** ¿Recomendáis terminar AppArmor primero (protección completa
antes de --reset) o DEBT-ADR025-D11 primero (cumplir deadline)?

**Contexto:** `provision.sh --reset` modifica claves — si AppArmor está en
enforce y los perfiles no cubren los paths de --reset, podría bloquearse.

### Q4 — TEST-PROVISION-1: ¿falta algún check?

El CI gate actual verifica 5 cosas:
1. Claves criptográficas válidas
2. Plugins firmados (verify-only)
3. No dev plugins en configs de producción
4. build-active symlinks presentes
5. 6 systemd units instalados

**Pregunta:** ¿Falta algún check crítico antes de `pipeline-start`?
¿Debería verificar también que los binarios no han sido modificados
desde la última firma (hash de binarios)?

---

## Formato de respuesta solicitado

Para cada pregunta (Q1-Q4):
- **Veredicto:** recomendación concreta
- **Justificación:** máximo 3 líneas
- **Riesgo si se ignora:** 1 línea

*Via Appia Quality · Un escudo, nunca una espada.*
*DAY 115 — 2026-04-12*