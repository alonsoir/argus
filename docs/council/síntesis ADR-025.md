Convergencia muy alta en esta ronda. Antes de la síntesis, una nota meta: Qwen se identifica correctamente como Qwen esta vez — interesante variación respecto al patrón anterior.

---

## Síntesis segunda ronda — Decisiones cerradas

**P1:** Unanimidad. Rotación exclusivamente manual. Cron únicamente como notificación opcional, nunca como ejecución.

**P2:** Unanimidad. D7 mantenido. Clave pública hardcoded en binario. El coste de recompilación es intencional — disuade rotaciones innecesarias.

**P3:** Consenso en advertencia fuerte + timestamp. Divergencia menor en borrar vs mover `.sig`. Qwen propone mover a `/var/lib/ml-defender/invalidated/` — mejor para forense. Lo adopto.

**P4:** Unanimidad. Falco documentado como capa complementaria, referencia a ADR futuro. Qwen aporta la regla Falco concreta — la incluyo.

Redacto el ADR completo ahora.

---ADR-025 cerrado. Dos rondas, dos iteraciones de threat modeling, consenso consolidado.

Lo que el Consejo añadió que no estaba en el borrador inicial y que es sustancial: V9 (symlink race con `O_NOFOLLOW`), V10 (TOCTOU en el `.sig`), el concepto de `key_id` para escalar, la regla Falco concreta de Qwen, y el flujo de `provision.sh --reset` con movido forense a `/var/lib/ml-defender/invalidated/`.

Mañana, cuando abras el repo, el orden natural es:
1. Revisar si `TEST-PLUGIN-INVOKE-1` está hecho
2. Integrar plugin-loader en `firewall-acl-agent` (PLUGIN-LOADER-FW)
3. ADR-025 entra en implementación — `plugin_loader.cpp` + `provision.sh` + CMakeLists