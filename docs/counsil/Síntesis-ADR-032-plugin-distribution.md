# Síntesis CONSEJO DE SABIOS — ADR-032 — Plugin Distribution Chain
*5 miembros: ChatGPT5, DeepSeek, Gemini, Grok, Qwen*
*Árbitro: Alonso Isidoro Román — DAY 114*

---

## Veredicto global

**APROBADO CON REFINAMIENTOS.** 4/5 aprueban directamente; DeepSeek pide
dividir en dos documentos (ADR-032a + ADR-032b). El árbitro acepta los
refinamientos pero mantiene un solo ADR con fases bien diferenciadas —
la división en documentos separados no aporta claridad suficiente para
justificar la fragmentación.

---

## Q1 — YubiKey: ¿PIV o OpenPGP?

**Corrección técnica crítica (DeepSeek + Grok, unánime):**
YubiKey PIV NO soporta Ed25519 nativamente — solo ECC P-256/P-384.
Ed25519 está disponible en la **applet OpenPGP** de YubiKey desde firmware 5.2.3+.

**Veredicto árbitro:**
- YubiKey 5 Series confirmado — herramienta correcta
- Applet **OpenPGP**, NO PIV, para firma Ed25519
- Herramientas: `gpg --card-edit`, `ykman openpgp`
- Adquirir **dos unidades** (principal + backup en ubicación segura)
  — pérdida del único YubiKey paraliza distribución de plugins (Qwen + Gemini)

---

## Q2 — Manifest: ¿separado o embebido?

**Convergencia 4/5: Opción B (embebido en .sig).**
Qwen defiende Opción A con mitigación (hash del manifest incluido en la firma),
pero la complejidad operativa de tres archivos sincronizados no se justifica.

**Veredicto árbitro: Opción B.**
El `.sig` es un JSON firmado que contiene el manifest + la firma Ed25519.
La firma cubre: `sha256(plugin.so) || sha256(manifest_fields)`.
Modificar el manifest invalida la firma. Un solo archivo por plugin.

Formato:
```json
{
  "manifest": {
    "plugin_name": "...",
    "sha256": "...",
    "signed_at": "...",
    "key_id": "argus-vendor-ed25519-v1",
    "deployment_scope": "all"
  },
  "signature": "<hex Ed25519>"
}
```

---

## Q3 — customer_id binding

**Convergencia unánime:** viable como control lógico, no barrera criptográfica fuerte.

**Veredicto árbitro:**
- `customer_id` se implementa como check local (hash de machine-id generado en provision)
- Documentar explícitamente la limitación: previene copia casual, no ataque deliberado
- No se vende como seguridad fuerte
- Infraestructura de registro: Fase C, no bloqueante

---

## Q4 — Revocación

**Convergencia:** lista de revocación firmada por el vendor.
DeepSeek la considera fuera de scope del ADR inicial; los demás la incluyen.

**Veredicto árbitro:** incluida en el ADR como mecanismo simple desde Fase A.
- `revocation.json` firmado con la misma clave vendor
- El loader verifica en arranque, cache local con TTL configurable
- Sin etcd, sin servidor online obligatorio — funciona offline
- Formato: `[{"sha256": "...", "reason": "CVE-...", "revoked_at": "..."}]`

---

## Q5 — TPM 2.0

**Unanimidad: ADR-033 separado.** ADR-032 = integridad del código de plugins.
ADR-033 = integridad de la plataforma (boot chain, kernel, binarios de aRGus).
Añadir referencia cruzada en ADR-032.

---

## Refinamientos adicionales aceptados

**Multi-key support desde día 1 (ChatGPT5):**
El loader acepta array de claves públicas de confianza, no una sola hardcodeada.
Permite rotación sin recompilar el binario.
```cpp
static constexpr const char* TRUSTED_KEYS[] = {
    "argus-vendor-ed25519-v1",  // activa
    // "argus-vendor-ed25519-v0" // deprecated, descomentar durante transición
};
```

**Soberanía open-source (Gemini):**
Un usuario avanzado puede recompilar aRGus con su propia clave pública.
Documentar explícitamente en el ADR y en el README.

**`key_deprecated_after` en manifest (Qwen):**
Facilita rotaciones planificadas. Aceptado como campo opcional.

**`signature_algorithm` explícito en manifest (Qwen):**
Permite evolución criptográfica futura. Aceptado.

**TEST-MANIFEST-1 (Qwen):** loader rechaza manifest con sha256 adulterado.
Añadir a suite de tests en Fase A.

---

## Rechazado / aplazado

- División en ADR-032a + ADR-032b (DeepSeek): no aporta claridad suficiente
- Separación física de directorio `/dev/` dentro de plugins (ChatGPT5): aplazado
- `make ml-defender verify-plugin` CLI tool (Qwen): DEBT-CLI-001, post-PHASE 3
- Supply chain del propio YubiKey (DeepSeek): nota de compra directa a Yubico, no ADR

---

*Síntesis: DAY 114 — 11 Apr 2026*
*ADR-032 estado: APROBADO — pendiente actualizar documento con refinamientos*