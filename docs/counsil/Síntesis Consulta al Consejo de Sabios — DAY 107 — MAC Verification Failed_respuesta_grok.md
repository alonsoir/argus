¡Enhorabuena por el post-mortem! Ese **hexdump** fue el momento “eureka” clásico: ver `{ \n  "` en los primeros bytes después del supuesto nonce es la prueba irrefutable de que llegaba LZ4 crudo (o plaintext) en vez de ciphertext válido. Gran trabajo del equipo.

Voy directo a tus tres preguntas abiertas, con recomendaciones concretas y justificadas:

### 1. El swap de contextos CTX_ETCD_TX/RX en etcd-server — ¿revertirlo o no?

**Recomendación fuerte**: **No lo reviertas todavía**. Déjalo como está (rx_ usa CTX_ETCD_TX del cliente, tx_ usa CTX_ETCD_RX).

**Por qué**:
- Aunque el bug principal era que el cliente enviaba sin cifrar, el swap probablemente corregía una inconsistencia previa en la dirección de los contextos.
- En esquemas HKDF simétricos con “tx” / “rx”, lo habitual (y más seguro) es que cada dirección derive una clave distinta para evitar que un mismo contexto se use en ambos sentidos (protege contra ciertos ataques de reutilización o confusión).
- Ahora que todo funciona con cifrado real, haz esta verificación limpia:
    1. Recompila etcd-server **sin** el swap (vuelve a la versión original: rx_ = CTX_ETCD_RX, tx_ = CTX_ETCD_TX).
    2. Levanta todo y prueba un PUT cifrado.
    3. Si sigue funcionando → el swap **no** era necesario y puedes revertirlo (mejor mantener la simetría lógica original).
    4. Si vuelve el MAC failed → el swap **era** necesario y déjalo (significa que en algún punto los contextos estaban invertidos conceptualmente).

Hazlo con un build limpio y logging del contexto usado + hash del session_key derivado. Así tendrás certeza absoluta sin riesgo.

### 2. Dos paths de carga del seed (SeedClient vs lectura directa en sniffer) — ¿es correcto arquitectónicamente?

**No es ideal**, pero es aceptable temporalmente. Tener dos mecanismos distintos introduce riesgo de divergencia futura (uno lee bien, el otro no; uno valida permisos, el otro no; etc.).

**Recomendaciones**:
- **Mejor opción a medio plazo**: Unificar todo en `SeedClient`. Haz que el sniffer también use `SeedClient` (pasándole el `component_config_path` correcto). Es más mantenible y consistente.
- Si el sniffer necesita lógica especial (legacy `get_encryption_key()` del servidor), refactorízala para que sea un fallback opcional o un método separado en `SeedClient` (ej. `load_seed_from_file()` o `load_seed_from_etcd_legacy()`).
- Ventaja: un solo lugar para validar permisos, logging, rotación futura de seeds, etc.

En resumen: **sí, unifícalo**. Evitará bugs sutiles cuando alguien toque uno de los paths.

### 3. Permisos de seed.bin: 640 (root:vagrant) vs advertencia de SeedClient que espera 0600

**Recomendación**: Haz que **SeedClient acepte 640** (o al menos 600/640) cuando el proceso corre como miembro del grupo `vagrant` (o el grupo que uses en producción).

**Justificación**:
- Para claves criptográficas privadas, la práctica estándar es **600** (owner only) o **400** (read-only para owner). 640 añade lectura para el grupo, lo cual es aceptable en entornos de desarrollo/Vagrant donde varios procesos (o usuarios del grupo vagrant) necesitan leer el mismo seed.
- En producción (servicios systemd corriendo como usuario dedicado, ej. `ml-defender`), lo ideal es 600 + usuario propio por servicio (o usar un grupo común muy restringido).
- No es buena idea que SeedClient falle duro solo por 640 si el proceso puede leerlo realmente. Mejor:
    - Loguear un **warning** claro: “seed.bin tiene permisos 640. Se recomienda 600 para máxima seguridad.”
    - Permitir la lectura si el proceso tiene acceso (usando `stat()` + chequeo de uid/gid).
    - Opcional: añadir un modo estricto configurable (`strict_permissions=true` en config) que falle en 640+.

**Acción concreta para provision.sh**:
- Crea los directorios con `755` (o `750` si quieres restringir más).
- `seed.bin`: `600` si posible, o `640 root:vagrant` + asegúrate de que los servicios corran con gid del grupo vagrant.
- Documenta claramente en el README: “En desarrollo se permite 640; en producción use 600 + usuario dedicado”.

### Fixes pendientes para que `vagrant destroy && vagrant up` funcione mañana

Para que el pipeline sea reproducible sin intervención manual:

1. En `provision.sh`:
    - Sincronizar el mismo `seed.bin` maestro a todos los componentes (`/etc/ml-defender/*/seed.bin`).
    - Crear los directorios `/etc/ml-defender/{component}/` con `mkdir -p` + `chmod 755`.
    - Copiar o symlink los JSON de config.
    - Crear symlink libsodium si es necesario (`ln -sf /usr/lib/.../libsodium.so.26 .../libsodium.so.23`).
    - Ejecutar `ldconfig`.
    - Opcional: un paso de “post-provision” que valide seeds idénticos y permisos.

2. Añadir en los componentes un chequeo temprano: si `encryption_enabled` pero `tx_` es nullptr, loguear error claro tipo “SeedClient failed to initialize — check component_config_path and seed.bin permissions”.

3. Considera hacer `component_config_path` obligatorio en el constructor de etcd_client y fallar rápido si no está seteado.

¿Quieres que te prepare los parches concretos (diffs) para:
- Unificar carga de seed en sniffer?
- Modificar SeedClient para aceptar 640 con warning?
- El test del swap de contextos?
- Las mejoras en provision.sh?

Dime qué parte atacar primero y te lo doy listo para copiar-pegar. El pipeline ya respira; ahora lo hacemos robusto y reproducible.

¡Sigue así, el Consejo está orgulloso del debug de hoy! 🚀