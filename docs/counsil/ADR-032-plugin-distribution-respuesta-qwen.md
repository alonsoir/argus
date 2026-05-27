# 🏛️ CONSEJO DE SABIOS — REVISIÓN ADR-032
*Feedback sincero, directo y proactivo sobre "Plugin Distribution Chain: Offline HSM Signing"*

---

## 🎯 Veredicto Ejecutivo

**ADR-032 es excelente.** Cumple con los criterios de calidad que valoramos:
- ✅ **Problema bien definido**: separación clara del dominio de confianza.
- ✅ **Solución pragmática**: YubiKey ~55 USD es accesible y efectivo.
- ✅ **Modelo de amenazas honesto**: reconoce límites ("Game over" con YubiKey+PIN).
- ✅ **Roadmap realista**: fases A→B→C con entregables concretos.
- ✅ **Documentación para el paper**: integración consciente con la publicación científica.

**Recomendación**: **APROBAR CON REFINAMIENTOS MENORES**. No es un "sí, pero..."; es un "sí, y además...".

---

## 🔍 Análisis por Sección

### ✅ Contexto y Decisión
La premisa es sólida: *"la autoridad de firma y el servidor de producción comparten el mismo dominio de confianza"*. Esta frase debería ser cita destacada en el paper.

**Observación proactiva**: Añadid una nota sobre **key rotation**. ¿Qué ocurre cuando `argus-vendor-ed25519-v1` deba ser rotada? Sugerencia:
```json
// En plugin-loader.hpp
static constexpr const char* TRUSTED_KEYS[] = {
  "argus-vendor-ed25519-v1",  // actual
  "argus-vendor-ed25519-v0"   // deprecated, válido hasta YYYY-MM-DD
};
```
Esto permite transiciones suaves sin downtime.

### ✅ Plugin Signature Manifest
El diseño es flexible y bien pensado. Dos sugerencias técnicas:

1. **Campo `algorithm` explícito**:
```json
"signature_algorithm": "Ed25519",
"hash_algorithm": "SHA256"
```
Permite evolución criptográfica futura sin romper compatibilidad.

2. **`deployment_scope` como enum validado**:
```cpp
enum class DeploymentScope { ALL, SINGLE_CUSTOMER, TRIAL, INTERNAL };
```
Evita errores de tipeo y facilita auditoría.

### ✅ Threat Model
Tabla clara y honesta. Un añadido sugerido:

| Vector | ADR-032 | Mitigación adicional |
|--------|---------|---------------------|
| **Supply chain: vendor comprometido** | No cubierto | Firmas multi-pariente (2 de 3 YubiKeys) para plugins críticos |

No es necesario implementarlo ahora, pero documentarlo como "límite del modelo" refuerza la transparencia.

### ✅ Implementación — Fases
El enfoque incremental es acertado. **Atención a Fase A**:
- Si el plugin-loader verifica `manifest.json` *antes* de tener HSM, aseguraos de que la verificación del `sha256` sea **constante-time** para evitar side-channel attacks en la comparación.
- Añadid un test: `TEST-MANIFEST-1: loader rejects manifest with tampered sha256`.

---

## ❓ Respuestas a Preguntas Abiertas

### Q1: ¿YubiKey PIV con Ed25519 o alternativas?

**Veredicto directo**: **YubiKey 5 Series es la elección correcta** para vuestro contexto.

| Opción | Pros | Contras | Recomendación |
|--------|------|---------|--------------|
| **YubiKey 5 PIV + Ed25519** | Robusto, bien documentado, PIN protegido, ~55 USD | Requiere gestión manual del vendor | ✅ **Elegida** |
| YubiKey OpenPGP | Más flexible para múltiples claves | Menos estandarizado para firma de código | ❌ No necesario |
| TPM 2.0 del cliente | Sin coste adicional, disponible en x86 | La clave estaría en el cliente → rompe el modelo vendor-controlled | ❌ Fuera de scope |
| Nitrokey HSM 2 | Open-source firmware, mayor control | ~150 USD, menos soporte en scripts | ⚠️ Considerar para Fase C si hay requisitos de soberanía |

**Consejo proactivo**: Comprad **dos YubiKeys idénticos** desde el inicio. Uno activo, uno de backup en ubicación segura. La pérdida física del único YubiKey paralizaría la distribución de plugins.

---

### Q2: ¿Manifest separado o embebido en .sig?

**Veredicto**: **Opción A (separado): `.so` + `.so.sig` + `.so.manifest.json`**

Razones:
- **Debuggability**: Un operador puede inspeccionar el manifest sin herramientas criptográficas.
- **Flexibilidad**: Podéis actualizar metadatos (ej. `expires_at`) sin regenerar la firma criptográfica si el hash del binario no cambia.
- **Compatibilidad con CI/CD**: Herramientas como `jq` pueden validar campos sin parsear firmas.

**Mitigación de riesgo**: Para evitar que el manifest sea tampered, ** incluid el hash del manifest dentro de la firma**:
```
signature = Ed25519_Sign(sha256(plugin.so) || sha256(manifest.json), private_key)
```
Así, cualquier modificación del manifest invalida la firma.

---

### Q3: ¿`customer_id` binding viable sin infraestructura de registro?

**Veredicto directo**: **Sí, pero con limitaciones conscientes**.

El binding `customer_id` funciona como **disuasorio de copia casual**, no como barrera criptográfica absoluta. Un atacante con acceso a dos instalaciones puede copiar un plugin válido.

**Recomendación pragmática**:
1. **Fase A/B**: Implementar `customer_id` como check local (suficiente para la mayoría de casos de uso).
2. **Documentar el límite**: "El customer_id previene errores operativos y copia no autorizada entre clientes, pero no protege contra un atacante con acceso a múltiples instalaciones legítimas."
3. **Fase C (opcional)**: Si surge la necesidad, añadir un **registro ligero en etcd** con `customer_id → public_key_instancia` para firmas específicas por cliente.

**Bonus**: El campo `customer_id` puede usarse para **telemetría ética** (opt-in): "plugin X cargado en instalación Y a tiempo Z", sin enviar datos sensibles.

---

### Q4: ¿Gestión de revocación de plugins?

**Veredicto**: **Lista de revocación local firmada + caché con TTL**.

Diseño propuesto:
```
1. Vendor publica CRL (Certificate Revocation List) firmada:
   crl.json.sig = Ed25519_Sign(crl.json, vendor_key)
   
2. crl.json contiene:
   {
     "version": 3,
     "issued_at": "2026-04-11T00:00:00Z",
     "revoked": [
       {"plugin": "libplugin_vuln.so", "version": "1.0.0", "reason": "CVE-2026-XXXX"}
     ]
   }

3. Plugin-loader:
   - Descarga CRL al iniciar (o usa caché local)
   - Verifica firma de CRL con clave pública hardcodeada
   - Rechaza plugins en lista revocada
   - Caché TTL: 24h (configurable)
```

**Ventajas**:
- Sin dependencia de conexión constante (funciona offline con caché).
- Vendor controla la revocación sin acceso a clientes.
- Transparente para el operador.

**Alternativa más simple para Fase A**: Sin CRL dinámica; la revocación se gestiona mediante `expires_at` en el manifest + nueva versión firmada.

---

### Q5: ¿TPM 2.0 measured boot en scope de ADR-032 o ADR separado?

**Veredicto directo**: **ADR separado (ADR-033)**.

Razones:
- ADR-032 se centra en **integridad del código a nivel de aplicación** (plugins).
- TPM measured boot opera a **nivel de plataforma/kernel** (boot chain, kernel, init).
- Mezclarlos diluiría el foco y complicaría la implementación incremental.

**Recomendación proactiva**: En la sección "Relación con ADRs existentes" de ADR-032, añadid:
> *"ADR-033 (propuesto): Platform Integrity via TPM 2.0 Measured Boot — complementaría ADR-032 asegurando que el propio binario de aRGus NDR no ha sido tampered antes de cargar plugins."*

Así dejáis la puerta abierta sin sobrecargar el ADR actual.

---

## 💡 Sugerencias Adicionales (Proactivas)

### 1. `key_id` versionado con fecha de deprecación
```json
"key_id": "argus-vendor-ed25519-v1",
"key_deprecated_after": "2027-12-31T23:59:59Z"
```
Facilita rotaciones planificadas sin incidentes.

### 2. Comandos de utilidad para operadores
Añadid al ADR (o a docs/PLUGIN-SIGNING.md):
```bash
# Verificar un plugin antes de instalar
$ ml-defender verify-plugin --bundle plugin_bundle.tar.gz
✓ Signature valid (key: argus-vendor-ed25519-v1)
✓ SHA256 matches manifest
✓ Deployment scope: all
✓ Not expired

# Listar plugins cargados con su estado de confianza
$ ml-defender list-plugins --verbose
libplugin_anomaly_detector.so  [TRUSTED]  v1.0.0  signed:2026-04-11
libplugin_hello.so             [DEV-ONLY] v0.3.0  NOT FOR PRODUCTION
```

### 3. Prueba de "fire drill" en CI
Incluir un test que simule un plugin con firma inválida y verifique que:
- El loader lo rechaza con `std::terminate()` (fail-closed).
- El log contiene `[plugin-loader] CRITICAL: Ed25519 verification failed`.
- No hay core dump con información sensible.

---

## 📋 Checklist de Aprobación Condicionada

```markdown
- [x] Problema y decisión bien definidos
- [x] Threat model honesto y completo
- [x] Roadmap de implementación realista
- [x] Integración con paper documentada
- [ ] Añadir nota sobre key rotation (sección "Decision")
- [ ] Clarificar que customer_id es disuasorio, no barrera absoluta
- [ ] Especificar que manifest hash está incluido en la firma
- [ ] Crear ADR-033 placeholder para TPM measured boot (futuro)
```

---

## 🏁 Palabras Finales

ADR-032 representa un salto de madurez en el modelo de confianza de aRGus NDR. No es solo una mejora técnica: es una **declaración de principios éticos** — el vendor asume la responsabilidad de la cadena de firma, liberando al cliente de gestionar claves sensibles.

La elección de YubiKey, la estructura del manifest y el enfoque por fases demuestran pragmatismo sin sacrificar seguridad. Las preguntas abiertas que planteáis son las correctas, y las respuestas que hemos dado buscan equilibrar robustez con viabilidad.

**Acción inmediata sugerida**:
1. Incorporar los refinamientos menores señalados.
2. Marcar ADR-032 como **APROBADO** en el repo.
3. Iniciar Fase A: diseño del formato manifest + tests de verificación.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 114** 🛡️