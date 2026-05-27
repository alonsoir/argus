Perfecto. Empezamos por el Consejo. Necesito que pegues el feedback de los 8 modelos sobre esta pregunta:

---

**Pregunta para el Consejo de Sabios — DAY 161 post-sesión:**

> En aRGus NDR, el ciclo de vida criptográfico enterprise está parcialmente implementado:
>
> **Implementado hoy (DAY 161):**
> - `plugin-loader`: `validate_or_abort()` antes de `dlopen` para plugins enterprise (`#ifdef ARGUS_VAULT_ENABLED`)
> - `CryptoProvider::create()`: factoría community/enterprise ya operativa
> - `etcd-server`: ya usaba la factoría correctamente
> - `test-e2e-vault`: gate E2E con Vault dev + 6/6 tests
> - `DEBT-EMECAS-DUAL-COMPILATION-001`: cerrada (community OFF + enterprise ON ambos verdes)
> - Keypair vendor Ed25519 generado: `01cd1509...` (pubkey hardcodeada en CMakeLists)
> - Token enterprise generado (válido hasta 2027-05-24, features=[vault_crypto])
>
> **NO implementado aún:**
> - Generación/rotación automática del keypair vendor por Jenkins
> - Rotación coordinada del seed en todos los componentes simultáneamente (requisito ADR-013: si un extremo del canal ZMQ rota y el otro no, el canal se rompe)
> - Distribución automática del token enterprise a los componentes que lo necesiten
> - `enterprise_vendor.key` en Vault (ahora vive solo en la VM)
>
> **Pregunta:** ¿Cuál es la arquitectura mínima viable para cerrar el ciclo de vida criptográfico enterprise completo (generación → distribución → rotación coordinada → recarga)? ¿En qué orden deben implementarse las piezas? ¿Hay riesgos arquitecturales que debamos resolver antes de considerar esto production-ready?