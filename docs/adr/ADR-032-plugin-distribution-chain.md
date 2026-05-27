# ADR-032 — Plugin Distribution Chain: Offline HSM Signing and Vendor-Controlled Plugin Authority

**Estado:** APROBADO — Pendiente implementación post-PHASE 3
**Fecha:** DAY 114 — 11 Apr 2026
**Autor:** Alonso Isidoro Román
**Revisado por:** Consejo de Sabios DAY 114 (5/7 miembros)
**Rama:** feature/phase3-hardening (documentación) → implementación post-PHASE 3

---

## Contexto

ADR-025 implementa verificación de integridad de plugins mediante Ed25519. La clave
privada de firma (`plugin_signing.sk`) reside actualmente en disco dentro de la VM.
Un atacante con acceso shell al servidor — incluso sin acceso físico — puede:

1. Leer `plugin_signing.sk` desde disco
2. Firmar un plugin malicioso con ella
3. Depositarlo en `/usr/lib/ml-defender/plugins/`
4. Obtener una firma válida para código arbitrario

El problema es arquitectónico: **la autoridad de firma y el servidor de producción
comparten el mismo dominio de confianza**. Esta frase es el axioma que ADR-032 resuelve.

---

## Decisión

### Nivel 1 — Vendor Signing Authority

La clave privada de firma **nunca existe en disco en ningún servidor de producción**.
Reside exclusivamente en un HSM portátil:

**Hardware:** YubiKey 5 Series — applet **OpenPGP** con curva Ed25519
(firmware ≥5.2.3 requerido; YubiKey PIV no soporta Ed25519).
**Herramientas:** `gpg --card-edit`, `ykman openpgp`.
**Unidades:** DOS (principal + backup en ubicación física separada).
La pérdida del único YubiKey paraliza la distribución de plugins.
Adquirir directamente de Yubico o distribuidor autorizado; verificar paquete de fábrica.

Flujo de firma:

```
1. Plugin compilado en entorno de desarrollo
2. Vendor conecta YubiKey
3. provision.sh sign --hsm <plugin.so>:
   - Calcula SHA-256 del .so
   - Envía hash al YubiKey vía OpenPGP (clave privada NUNCA abandona el hardware)
   - YubiKey devuelve firma Ed25519
   - Se genera plugin.so.sig (JSON con manifest + firma)
4. Vendor distribuye: plugin.so + plugin.so.sig
```

### Nivel 2 — Deployment Verification

El servidor de producción solo verifica firmas, nunca las genera.
La clave pública del vendor está hardcodeada en el binario.
El loader acepta un **array de claves de confianza** para permitir rotación
sin recompilar:

```cpp
// plugin_loader.hpp
static constexpr const char* TRUSTED_KEYS[] = {
    "argus-vendor-ed25519-v1",  // clave activa
    // "argus-vendor-ed25519-v0" // uncomment durante período de transición
};
```

### Soberanía open-source

Un usuario avanzado puede recompilar aRGus NDR con su propia clave pública,
manteniendo soberanía total sobre su hardware. El modelo vendor-controlled es
la configuración por defecto, no una restricción irrenunciable.

---

## Formato de firma (.sig)

El `.sig` es un JSON firmado que contiene manifest + firma Ed25519.
La firma cubre: `sha256(plugin.so) || sha256(manifest_fields)`.
Modificar cualquier campo del manifest invalida la firma.
**Un solo archivo adicional por plugin.**

```json
{
  "manifest": {
    "plugin_name": "libplugin_anomaly_detector.so",
    "version": "1.0.0",
    "sha256": "a3f8c2...",
    "signed_at": "2026-04-11T14:30:00Z",
    "key_id": "argus-vendor-ed25519-v1",
    "key_deprecated_after": null,
    "signature_algorithm": "Ed25519",
    "hash_algorithm": "SHA256",
    "deployment_scope": "all",
    "customer_id": null,
    "expires_at": null
  },
  "signature": "<hex Ed25519 sobre sha256(plugin.so) || sha256(manifest)>"
}
```

Para firma con scope restringido por cliente:

```json
{
  "manifest": {
    "plugin_name": "libplugin_custom_hospital.so",
    "version": "1.0.0",
    "sha256": "b7d9e1...",
    "signed_at": "2026-04-15T09:00:00Z",
    "key_id": "argus-vendor-ed25519-v1",
    "key_deprecated_after": null,
    "signature_algorithm": "Ed25519",
    "hash_algorithm": "SHA256",
    "deployment_scope": "single_customer",
    "customer_id": "hospital-badajoz-001",
    "expires_at": "2027-04-15T00:00:00Z"
  },
  "signature": "<hex>"
}
```

---

## customer_id binding — limitaciones documentadas

El `customer_id` es un **control lógico, no una barrera criptográfica fuerte**.

- Previene: copia casual de plugins entre clientes, errores operativos
- No previene: un atacante con acceso a múltiples instalaciones legítimas que conozca los IDs

Implementación: el `customer_id` se genera en el primer `provision.sh` de cada
instalación como hash de `machine-id + salt` y se almacena en
`/etc/ml-defender/customer.id` (permisos 0600, root only).

El vendor obtiene este ID del cliente (fuera de banda) al firmar un plugin específico.

---

## Revocación de plugins

Lista de revocación firmada por el vendor. Sin servidor online obligatorio —
funciona offline con caché local.

Formato `revocation.json`:
```json
{
  "version": 1,
  "issued_at": "2026-04-11T00:00:00Z",
  "revoked": [
    {
      "sha256": "a3f8c2...",
      "plugin_name": "libplugin_vuln.so",
      "reason": "CVE-2026-XXXX",
      "revoked_at": "2026-04-11T00:00:00Z"
    }
  ]
}
```

`revocation.json` está firmado con la misma clave vendor Ed25519.
El loader verifica en arranque, cache local con TTL configurable (default: 24h).
Distribución: bundle de instalación o `make update-revocation`.

---

## Threat Model — mejora sobre ADR-025

| Vector de ataque | ADR-025 | ADR-032 |
|---|---|---|
| Atacante sin shell | Bloqueado | Bloqueado |
| Atacante con shell remoto | **Vulnerable** (clave en disco) | Bloqueado |
| Atacante con acceso físico al servidor | **Vulnerable** | Bloqueado |
| Atacante con servidor + YubiKey robado | N/A | Bloqueado (requiere PIN) |
| Atacante con servidor + YubiKey + PIN | N/A | Game over (aceptable) |
| Plugin de tercero no autorizado | Bloqueado | Bloqueado + scope check |
| Vendor comprometido (YubiKey + PIN) | N/A | Game over — límite del modelo |

**Nota sobre supply chain del YubiKey:** adquirir directamente de Yubico.
El YubiKey mismo es un punto de confianza; su integridad física es prerrequisito.

---

## Relación con ADRs existentes

- **ADR-025:** base de verificación. ADR-032 extiende el modelo de confianza hacia el vendor.
- **ADR-030 (AppArmor):** complementario — restringe qué hace un plugin en runtime.
- **ADR-031 (seL4):** agnóstico a plataforma kernel.
- **ADR-024 (Noise IKpsk3):** ortogonal — protege transporte; ADR-032 protege código.
- **ADR-033 (propuesto):** Platform Integrity via TPM 2.0 Measured Boot — complementaría
  ADR-032 asegurando que el binario de aRGus no ha sido modificado antes de cargar plugins.

---

## Modelo de distribución / negocio

```
aRGus NDR (vendor) = gatekeeper de código
Plugin firmado     = código aprobado por el vendor
Instalación cliente = solo ejecuta código aprobado

Flujo para cliente:
1. Cliente solicita plugin (o actualización)
2. Vendor compila, audita, firma con YubiKey
3. Vendor distribuye bundle: plugin.so + plugin.so.sig
4. Cliente ejecuta: make install-plugin BUNDLE=...
5. Loader verifica firma y manifest antes de activar
```

Coste para el cliente: ninguno adicional al hardware base (~150-200 USD).
Coste para el vendor: ~110 USD (dos YubiKeys, inversión única).

---

## Implementación — fases

### Fase A (post-PHASE 3 — sin YubiKey)
- Modificar plugin-loader para leer y verificar `plugin.so.sig` en formato JSON
- Verificar `sha256` del binario contra manifest, `key_id`, `expires_at`, `customer_id`
- Soporte multi-key en el loader (array de claves de confianza)
- Verificar `revocation.json` firmado en arranque
- Tests: TEST-MANIFEST-1 (sha256 adulterado → rechazo), TEST-MANIFEST-2 (expirado → rechazo)
- Documentar en paper §10.11 y §11

### Fase B (cuando haya hardware — YubiKey)
- Migrar `provision.sh sign` a firma vía YubiKey OpenPGP
- Eliminar `plugin_signing.sk` de disco en entornos de producción
- TEST-INTEG-SIGN-8: firma HSM produce .sig válido para el loader

### Fase C (largo plazo)
- `customer_id` binding con registro ligero
- Distribución automática de `revocation.json`
- DEBT-CLI-001: `ml-defender verify-plugin --bundle <bundle>` CLI tool

---

## Impacto en el paper (arXiv:2604.04952)

### §10.11.3 (No hardware root of trust — actualizar):
```
The current design stores the signing private key on disk, making it vulnerable
to attackers with shell access. ADR-032 addresses this by moving signing authority
to an offline HSM (YubiKey 5, OpenPGP applet, Ed25519), ensuring the private key
never leaves the hardware device. This is scoped to post-PHASE 3 implementation.
```

### §11.x (Future Work — nueva entrada):
```
Plugin Distribution Chain (ADR-032): the current signing model stores the private
key on disk, making it vulnerable to attackers with shell access. ADR-032 moves
signing authority to an offline HSM (YubiKey ~55 USD), establishing a
vendor-controlled plugin distribution chain. Per-deployment and time-bounded
signatures enable fine-grained control over what code runs in each installation.
Hardware cost is borne exclusively by the vendor; client deployments require no
additional hardware. The open-source nature of aRGus NDR ensures user sovereignty:
organizations may recompile the platform with their own root-of-trust if desired.
```

---

## Estado de implementación

- [x] Borrador — DAY 114
- [x] Revisión Consejo de Sabios — DAY 114 (5/7 miembros)
- [x] ADR aprobado con refinamientos incorporados
- [ ] Fase A: formato manifest + verificación en loader + tests
- [ ] Texto paper actualizado (§10.11.3 + §11.x)
- [ ] Hardware adquirido (2× YubiKey 5)
- [ ] Fase B: firma HSM
- [ ] Fase C: customer_id + revocación dinámica

---

*Via Appia Quality · Un escudo, nunca una espada.*
*DAY 114 — 11 Apr 2026*