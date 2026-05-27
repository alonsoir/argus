## Respuesta del Consejo de Sabios – Revisión de ADR-032 (Borrador)

El Consejo agradece la propuesta de ADR-032. Aborda un vector real (clave privada en disco) y extiende la cadena de confianza de forma coherente con ADR-025. Sin embargo, **el borrador tiene problemas de claridad, viabilidad y omisiones significativas** que deben resolverse antes de aceptarlo como BACKLOG. A continuación, el análisis detallado.

---

### Fortalezas del ADR

1. **Identifica correctamente una limitación real** del modelo actual (clave privada en disco vulnerable a atacante con shell).
2. **Propone una solución basada en HSM portátil** (YubiKey) que es económica (55 USD) y práctica para un vendor individual.
3. **Introduce el concepto de manifiesto** con campos útiles (`sha256`, `key_id`, `customer_id`, `expires_at`), que permite control granular.
4. **Reconoce que esto es una evolución** de ADR-025, no un reemplazo, y lo relaciona con otros ADRs.

---

### Problemas críticos (deben corregirse antes de aprobar)

#### 1. La premisa “clave privada nunca en disco” es técnicamente imposible en el flujo descrito

> “La clave privada NUNCA abandona el hardware del YubiKey”

Pero luego se dice: `provision.sh sign --hsm <plugin.so>` → firma vía YubiKey PIV.  
El problema: para firmar un `.so`, el plugin-loader necesita el **par de claves completo** o al menos la clave privada para generar la firma. Si el YubiKey realiza la firma internamente (como un HSM real), entonces la clave privada nunca sale del dispositivo, pero **el binario resultante (`.sig`) debe contener la firma**. Eso es posible: el YubiKey recibe el hash del `.so` (o el archivo completo) y devuelve la firma. El script de firma no necesita tener la clave privada en disco. **Pero el ADR no especifica cómo se comunica el script con el YubiKey** (¿usando `ykman`? ¿`openssl engine`? ¿`pkcs11-tool`?). Tampoco aclara si el YubiKey soporta firmar archivos grandes (el `.so` puede ser de varios MB). La mayoría de tokens solo firman hashes, no archivos completos.

**Exigencia:**
- Especificar el mecanismo concreto: el script calcula SHA-256 del `.so`, envía el hash al YubiKey (vía PKCS#11 o interfaz nativa), este devuelve la firma Ed25519. Luego se empaqueta `.sig` (firma binaria) y `.manifest.json`.
- Verificar que YubiKey 5 Series soporta Ed25519 en modo PIV (no todos los modelos lo tienen; revisar documentación). Alternativa: usar la applet OpenPGP de YubiKey con curva Ed25519 (soportado en firmware 5.2.3+). Añadir nota de verificación.

#### 2. El manifiesto introduce complejidad sin justificar completamente la necesidad de campos como `customer_id` y `expires_at` en el primer hito

- **`customer_id` binding** requiere que cada instalación tenga un identificador único y que el vendor conozca ese ID al firmar. El ADR no propone cómo se genera, distribuye o verifica ese ID (¿un archivo `/etc/ml-defender/customer.id`? ¿Provisionado durante la instalación?). Sin infraestructura de registro, un cliente puede copiar el ID de otro.
- **`expires_at`** obliga a reintroducir la clave privada (o al menos a generar nuevas firmas) periódicamente, lo que contradice el objetivo de no tener la clave en producción. Si el vendor debe re-firmar cada año, el proceso es manual y costoso.

**Recomendación:**
- Dividir el ADR en dos fases bien diferenciadas:
    - **Fase 1 (core):** Solo firma Ed25519 vía HSM, sin manifiesto adicional (o manifiesto mínimo con `sha256` y `key_id`).
    - **Fase 2 (avanzada):** `customer_id`, `expires_at`, revocación.
- Para la Fase 1, basta con que el plugin-loader verifique la firma Ed25519 tal como hace ADR-025, pero obteniendo la firma de un YubiKey externo. El manifiesto puede ser un JSON adicional opcional.
- Aclarar que `customer_id` y `expires_at` son *future work* opcional, no requisito para la implementación inicial.

#### 3. La revocación de plugins no está resuelta

El ADR menciona “lista de revocación local en etcd, o lista firmada distribuida”. Ninguna de las dos es trivial en el contexto actual (aRGus no tiene etcd por defecto; la lista firmada requiere infraestructura de distribución). Sin revocación, un plugin comprometido (pero firmado válidamente) seguiría siendo aceptado indefinidamente.

**Recomendación:**
- Aceptar que la revocación está fuera del alcance de este ADR y documentarlo como limitación conocida.
- Propuesta de solución simple (para futuro): el manifiesto incluye un campo `revoked: false` que podría ser sobreescrito por una lista negra local mantenida por el operador (ej. un archivo JSON en `/etc/ml-defender/revoked_plugins.json`). El plugin-loader comprueba esa lista antes de cargar.

#### 4. Falta un análisis de la cadena de suministro para el propio HSM

El YubiKey debe ser adquirido por el vendor (el autor). ¿Cómo se asegura que el dispositivo no ha sido manipulado antes de llegar? Esto es un problema general de hardware de seguridad, pero el ADR debería al menos mencionar que se recomienda comprar directamente a Yubico o a un distribuidor autorizado y verificar el paquete de fábrica.

#### 5. Impacto en el usuario final (cliente) no se describe suficientemente

- ¿Qué ocurre si el cliente quiere modificar un plugin existente (por ejemplo, para adaptarlo a su red local)? Con ADR-032, no puede, porque la firma debe venir del vendor. Eso puede ser deseable (modelo App Store) pero también limita la autonomía del cliente. El ADR debe discutir esta compensación.
- ¿El cliente puede tener su propio HSM y firmar sus plugins internos? El diseño actual asume que solo el vendor tiene la autoridad. Si una organización quiere ser autónoma, necesitaría generar su propio par de claves y modificar el binario (hardcodear su clave pública). Eso es posible pero no está documentado.

---

### Preguntas específicas (respuesta del Consejo)

#### 1. ¿YubiKey PIV con Ed25519 es la elección correcta?

**Respuesta:** **Sí, pero con matices.**
- YubiKey 5 Series soporta Ed25519 en la applet OpenPGP (no en PIV). PIV soporta ECC P-256/P-384, no Ed25519. Por tanto, se debe usar el modo OpenPGP con la curva Ed25519 (disponible desde firmware 5.2.3).
- Alternativas más robustas al mismo precio: SoloKey (open source), Nitrokey Start (algo más caro). Para un solo vendor, YubiKey es adecuado.
- Recomendación: especificar el modelo concreto (YubiKey 5 NFC, firmware ≥5.2.3) y las herramientas (`gpg --card-edit`, `ykman openpgp`).

#### 2. ¿Manifiesto separado o embebido en `.sig`?

**Respuesta:** **Opción B (embebido en el `.sig` como payload JSON firmado)** es más limpia.
- Razones: un solo archivo por plugin (`.sig`) que contiene el manifiesto + la firma. El plugin-loader extrae el JSON, verifica la firma contra el `.so`, y luego valida los campos.
- Alternativa A (tres archivos) es más simple de implementar pero propensa a errores (el `.sig` podría no estar sincronizado con el manifiesto).
- El ADR debería elegir explícitamente la opción B y definir el formato:
  ```json
  {
    "manifest": { ... },
    "signature": "hex or base64 of Ed25519 signature over (manifest + .so hash?)"
  }
  ```  
  Nota: la firma debe cubrir el hash del `.so` y los campos del manifiesto para evitar separación.

#### 3. ¿`customer_id` binding es viable sin infraestructura de registro?

**Respuesta:** **No es viable sin un sistema de emisión de identidades.**
- Para que el binding tenga sentido, cada instalación debe tener un ID único y secreto (o al menos conocido por el vendor). Sin un servidor de registro, el vendor no puede asociar un ID a un cliente concreto.
- Una alternativa sin registro: el `customer_id` puede ser un hash de la clave pública de la instalación (si cada cliente genera su propio par de claves y el vendor firma el plugin con un campo `target_pubkey_hash`). Pero eso requiere que el cliente envíe su clave pública al vendor (canal fuera de banda).
- **Recomendación:** Aplazar `customer_id` a una fase posterior cuando haya infraestructura de gestión de clientes. Por ahora, el manifiesto puede tener un campo opcional `audience` con valores `"all"` o `"single"` (sin ID concreto).

#### 4. ¿Cómo gestionar la revocación de plugins?

**Respuesta:** **Fuera de alcance para este ADR, pero se debe documentar como limitación.**
- Propuesta de diseño futuro (no bloqueante): el manifiesto incluye un campo `revocation_token` (nonce). El vendor publica una lista de tokens revocados en un endpoint HTTPS conocido. El plugin-loader descarga la lista periódicamente.
- Mientras tanto, la única manera de revocar un plugin es reemplazar el binario (con una nueva versión firmada) o eliminar manualmente el plugin de la configuración.

#### 5. ¿TPM 2.0 measured boot como capa complementaria?

**Respuesta:** **Es un ADR separado.**
- TPM 2.0 puede usarse para atestación remota y para sellar claves, pero no reemplaza la cadena de firma de plugins. Podría combinarse para garantizar que el sistema arranca en un estado conocido antes de cargar plugins.
- El Consejo recomienda que el autor lo estudie como posible ADR-033, no mezclarlo aquí.

---

### Recomendaciones generales para mejorar el ADR

1. **Separar claramente las fases** (Fase A: solo HSM sin manifiesto avanzado; Fase B: manifiesto con `customer_id`/`expires_at`; Fase C: revocación).
2. **Especificar el flujo de firma paso a paso** con comandos concretos (ej. `ykman openpgp sign --hash-alg sha256 --input plugin.so --output plugin.so.sig`).
3. **Añadir una sección de “Limitaciones”** donde se reconozca que:
    - El modelo requiere que el vendor sea confiable (single point of trust).
    - La revocación no está resuelta.
    - El cliente no puede modificar plugins sin el vendor (trade-off seguridad vs flexibilidad).
4. **Actualizar el threat model** para incluir el caso de pérdida/robo del YubiKey (y la necesidad de PIN y políticas de backup).
5. **Evaluar el impacto en el rendimiento** (firmar plugins grandes puede ser lento si se envía el archivo completo al YubiKey; usar hash es rápido).
6. **Incluir una estimación de esfuerzo** para cada fase (personas-día) y dependencias de herramientas externas (`ykman`, `opensc`, `gpg`).

---

### Veredicto preliminar

El ADR-032 es **prometedor pero necesita una revisión sustancial** antes de pasar a estado BACKLOG. El Consejo recomienda al autor:

1. Dividir el ADR en dos documentos: uno para el uso de HSM (YubiKey) para firma offline sin cambios en el formato de firma, y otro para el manifiesto enriquecido (customer_id, expires_at, revocación).
2. Para la parte HSM, simplificarla al máximo: solo reemplazar la generación de firma local por una llamada a YubiKey, manteniendo el mismo formato `.sig` que ADR-025.
3. Aplazar los campos avanzados a un ADR-032b, con una justificación clara de la infraestructura necesaria.
4. Agregar una sección de “Preguntas abiertas resueltas” con las respuestas anteriores.

Una vez realizados estos cambios, el Consejo evaluará de nuevo.

*“La verdad por delante, siempre” – también en el diseño de cadenas de confianza.*

*Via Appia Quality · Un escudo, nunca una espada.*  
*Acta de revisión – 11 Abril 2026*