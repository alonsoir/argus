# Síntesis CONSEJO DE SABIOS — DAY 114 — SESIÓN DE CIERRE
*5 miembros: ChatGPT5, DeepSeek, Gemini, Grok, Qwen*
*Árbitro: Alonso Isidoro Román*

---

## Q1 — DEBT-SIGN-AUTO: diseño firma automática

**Convergencia unánime — riesgo crítico identificado:**

El diseño propuesto tiene un fallo de modelo de confianza: si `check-and-sign-plugins` firma automáticamente cualquier `.so` presente en `/usr/lib/ml-defender/plugins/`, un atacante que deposite un binario malicioso y dispare un re-provision obtiene una firma legítima. Se rompe el principio de offline signing de ADR-025.

**Veredicto árbitro:**

DEBT-SIGN-AUTO se implementa con separación estricta de contextos:

- **Build/provision time (Makefile + Vagrant):** firma automática de artefactos recién compilados. Solo se firma lo que acaba de construirse. Idempotente: si ya está firmado con la clave actual → skip.
- **Runtime / producción:** NUNCA firmar automáticamente. Solo verificar. Si falta firma o es inválida → error explícito, no firma silenciosa.
- **Mecanismo:** `provision.sh check-plugins` verifica que todo plugin referenciado en los JSON configs existe en `/usr/lib/ml-defender/plugins/` y tiene `.sig` válido para la clave pública activa. Si falta → error en modo producción, firma en modo provisioning.
- **Rotación de clave:** tras `provision.sh --reset`, ejecutar `provision.sh sign --force` explícitamente. Nunca automático.
- **Adicionalmente aceptado (ChatGPT5 + Qwen):** `plugin-manifest.json` con sha256, key_version, signed_at. Aplazado a post-PHASE 3 — no bloqueante.
- **Adicionalmente aceptado (ChatGPT5):** `make diagnose` como target de observabilidad. Aplazado a PHASE 3 junto con DEBT-OPS-002.

---

## Q2 — DEBT-HELLO-001: eliminar libplugin_hello.so de producción

**Unanimidad: Opción C.**

- `BUILD_DEV_PLUGINS=OFF` por defecto en CMakeLists.txt. En CI: `BUILD_DEV_PLUGINS=ON` explícito para TEST-INTEG-4x.
- JSON configs de producción sin referencia a `libplugin_hello.so`.
- Plugin hello permanece en el repositorio bajo `plugins/hello/` para validación ADR-012 en desarrollo.
- **Aceptado (DeepSeek):** envolver `add_subdirectory(hello)` con `if(BUILD_DEV_PLUGINS)`.
- **Aceptado (Qwen):** check en CI que falla si un JSON de producción referencia `libplugin_hello`. Target: `make validate-prod-configs`.
- **Aplazado:** separación física de directorios `/dev/` dentro de plugins (ChatGPT5) — post-PHASE 3.

---

## Q3 — PHASE 3: orden de priorización

**Convergencia mayoritaria sobre dependencia oculta:**

DEBT-SIGN-AUTO debe completarse antes de TEST-PROVISION-1 (CI no puede pasar sin firma automática resuelta). AppArmor debe ir después de estabilidad operativa (signing + deployment limpios), no antes.

**Orden definitivo árbitro:**

1. **systemd units** — Restart=always, RestartSec=5s, unset LD_PRELOAD (base de resiliencia)
2. **DEBT-SIGN-AUTO** — firma automática build-time, idempotente, segura (mini-sprint con DEBT-HELLO-001)
3. **DEBT-HELLO-001** — `BUILD_DEV_PLUGINS=OFF` + JSON limpios + `make validate-prod-configs`
4. **TEST-PROVISION-1** — gate CI formal (depende de 1+2+3 estables)
5. **AppArmor profiles** — 6 componentes + denegar write `/usr/bin/ml-defender-*` para root
6. **DEBT-ADR025-D11** — provision.sh --reset (deadline 18 Apr, no se mueve)

---

## Q4 — Troubleshooting documentation

**Convergencia:** `docs/TROUBLESHOOTING.md` en Markdown + resumen ejecutivo en `CLAUDE.md`.

**Casos adicionales aceptados para el árbol:**

```
Pipeline no arranca →
  ¿std::terminate() en algún componente? →
    [plugin-loader] CRITICAL →
      "cannot open plugin (symlink?)" → make plugin-hello-build + make sign-plugins
      "Ed25519 INVALID"              → make sign-plugins
      ".sig not found"               → make sign-plugins
      "path outside allowed prefix"  → revisar JSON config plugin path
  ¿Arranca pero no procesa tráfico? →
    ¿sniffer corriendo? → bpftool prog list + ip link show (XDP attach OK?)
    ¿ZeroMQ sockets? → netstat -lntp | grep <puerto>, HWM configurado?
    ¿ml-detector 100% CPU? → ONNX model cargado, OOM killer activo?
  ¿Crash inmediato sin mensaje? →
    strace -f <binario> → syscall fallida
    Verificar permisos /usr/lib/ml-defender/plugins/
    Verificar LD_PRELOAD unset (systemd unit)
  Específico PHASE 3 (AppArmor) →
    EPERM / EACCES → dmesg + aa-status + modo complain vs enforce
```

**Aceptado (ChatGPT5):** `make diagnose` — verifica plugins, firmas, sockets, procesos en un solo comando. Implementar como parte de DEBT-OPS-002.

**Aceptado (Gemini):** `--check-config` flag en cada componente para validar firmas sin arrancar el pipeline completo. Candidato para DAY 115+.

---

## Observaciones adicionales aceptadas

**TRUST-CONTRACT.md (Qwen):** documento que explicita qué asume cada componente sobre los demás (firmas, paths, permisos, timeouts). Aplazado a post-PHASE 3 como DEBT-DOCS-001.

**Formalización:** el Consejo señala unanimidad en que el proyecto ha cruzado el umbral de "diseñar seguridad" a "diseñar operación segura". PHASE 3 es exactamente la respuesta correcta a ese diagnóstico.

---

*Síntesis elaborada: DAY 114 — 11 Apr 2026*
*5/7 miembros respondieron. Parallel.ai y Claude no incluidos en esta síntesis (Claude es árbitro).*