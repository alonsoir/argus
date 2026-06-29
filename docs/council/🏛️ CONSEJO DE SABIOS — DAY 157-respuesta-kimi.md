## 🏛️ Dictamen del Consejo de Sabios — DAY 157

**Dictamen:** `APROBADO CONDICIONADO` — Merge permitido tras resolver las condiciones P1 marcadas.

---

### 1. DEBT-AUTONOMY-STATE-PERSISTENCE-001 — Vectores de ataque y umbral de expiración

**Vectores NO cubiertos identificados:**

| Vector | Riesgo | Mitigación requerida |
|--------|--------|----------------------|
| **Rollback** (atacante reemplaza por snapshot anterior firmado válidamente) | Alto | Incluir `monotonic_counter` o `timestamp_issued` en el payload firmado; rechazar si `timestamp_issued < last_accepted_timestamp` |
| **TOCTOU en lectura** (race entre `open()` y `read()` con `rename`) | Medio | Usar `open(O_RDONLY)` sobre fd ya existente, no re-`open()` post-stat; o bloquear con flock durante escritura |
| **Permisos de archivo** (`/var/lib/argus/` group-writable) | Medio | Validar `st_mode` antes de aceptar lectura: `S_IRUSR` únicamente, `S_IWUSR` para owner; rechazar si group/other tienen write |
| **Clock skew** (NTP desajustado hace que 24h sea 48h o 0h) | Medio | Usar `CLOCK_MONOTONIC` relativo al arranque del proceso, no wall-clock absoluto, para la expiración |

**Sobre las 24h en entorno hospitalario:**  
**Condición P1.** 24h es excesivo para un sistema de firewall autónomo en producción clínica. El Consejo recomienda:

- **Default producción hospitalaria: 4 horas** (balance entre continuidad operativa y contención de riesgo)
- **Hacer configurable vía `ARGUS_AUTONOMY_MAX_STALENESS_HOURS`** con validación en `provision.sh` (mínimo 1h, máximo 72h)
- **Razón:** Un modo AUTONOMOUS prolongado sin validación del orquestador representa riesgo de blind spot en DICOM/HL7 traffic inspection. 4h permite una noche de mantenimiento sin falso fallback, pero no un fin de semana completo.

---

### 2. DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 — Timing de verificación vs. systemd

**Dictamen:** `ExecStartPost=` es **incorrecto** para un archivo efímero.

**Arquitectura correcta:**

```
STEP 0a: Generar bootstrap-status.json + firmar
STEP 0b: Verificar firma (self-check antes de consumir)
STEP 0c: etcd-server lee y valida su propio bootstrap
STEP 0d: g_server->start()
STEP 0e: (OPCIONAL) Renombrar a /var/lib/argus/bootstrap-status.done.json con timestamp
STEP 0f: Borrar efímero original
```

**Para systemd:**  
No uses `ExecStartPost=` para verificar un archivo que ya no existe. Dos opciones:

1. **Opción A (recomendada):** El propio `etcd-server` en `STEP 0b` hace `crypto_sign_verify_detached()` antes de llamar `start()`. Si falla, `exit(EXIT_BOOTSTRAP_INTEGRITY)`. Systemd captura el código y entra en `Restart=on-failure` con `StartLimitIntervalSec=`.

2. **Opción B:** Mantener `bootstrap-status.json` como **checkpoint persistente** (no efímero). Systemd `ExecStartPre=/usr/lib/argus/check-bootstrap-status.sh` lo valida. El servidor lo borra explícitamente en `STEP 0f` solo tras confirmar arranque limpio.

**Condición P1:** Implementar opción A antes del merge. La autoverificación en `main.cpp` elimina la dependencia externa y cierra la ventana TOCTOU.

---

### 3. DEBT-KEYPAIR-LIFECYCLE-PROD-001 — Política para `staging`

**Dictamen:** `staging` debe **diferenciarse** de `dev`, pero no igualarse a `prod`.

**Política propuesta por el Consejo:**

| Entorno | Comportamiento | Justificación |
|---------|---------------|---------------|
| `prod` | `exit 1` si ausente. Keypair provisionado por HSM/KMS externo. | No generación silenciosa = no claves en disco sin audit trail |
| `staging` | **Requiere keypair preexistente, pero permite generación explícita** con `ARGUS_STAGING_AUTO_GENERATE=1` | CI/CD pipelines necesitan claves efímeras, pero el default debe ser "parecido a prod" para catch de errores de provision |
| `dev` | Genera automáticamente si ausente | Productividad del desarrollador |

**Razón:** Si `staging` genera silenciosamente igual que `dev`, nunca detectarás en pre-producción que `prod` fallará por keypair ausente. El costo de un `ARGUS_STAGING_AUTO_GENERATE=1` en el `docker-compose.yml` de CI es mínimo; el beneficio de paridad comportamental con producción es máximo.

**Condición P2:** Modificar `provision.sh` para que `staging` requiera keypair a menos que `ARGUS_STAGING_AUTO_GENERATE=1` esté seteado explícitamente. Loggear `WARNING` en ese caso.

---

### 4. DEBT-CRYPTO-RECONCILIATION-001 — Timeout de staleness en `poll_callback`

**Dictamen:** **No es suficiente para FEDER.** Se requiere timeout de staleness.

**Problema:** Si el ZMQ publisher (etcd-server) muere silenciosamente (ej: `SIGKILL`, OOM killer, network partition sin ZMQ teardown limpio), el subscriber no detecta la desconexión. `last_known_mode_` permanece en `AUTONOMOUS` indefinidamente. En un firewall hospitalario, esto es una degradación silenciosa hacia un estado de riesgo no detectado.

**Diseño requerido:**

```cpp
// En AutonomySubscriber o reconciliador
struct StalenessGuard {
    std::atomic<std::chrono::steady_clock::time_point> last_update_;
    const std::chrono::seconds max_staleness_;

    FirewallAutonomyMode get_safe_mode() {
        auto elapsed = std::chrono::steady_clock::now() - last_update_.load();
        if (elapsed > max_staleness_) {
            return FirewallAutonomyMode::NORMAL; // Fail-safe
        }
        return last_known_mode_.load();
    }
};
```

- **Cada mensaje ZMQ actualiza `last_update_` con `steady_clock::now()`**
- **`poll_callback` consulta `get_safe_mode()`, no `last_known_mode_` directamente**
- **Default `max_staleness_`: 30 segundos** (configurable vía `ARGUS_HEALTH_STALENESS_MS`)
- **Razón:** El health-check loop del etcd-server debería emitir heartbeat cada 5-10s. 30s permite 3 heartbeats perdidos antes de fallback. Para FEDER, demuestra que el sistema no se "queda dormido" en autonomía.

**Condición P1:** Implementar `StalenessGuard` antes del merge. Es un requisito de seguridad funcional, no una mejora.

---

### 5. Arquitectura general — Inconsistencias entre deudas

**Inconsistencia crítica detectada:**

| Deuda | Asume | Conflicto con |
|-------|-------|---------------|
| BOOTSTRAP-STATUS-SIGNATURE-001 | Archivo efímero, firma self-checked | BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 propone verificación externa post-start de un archivo que ya no existe |

**Resolución:** Eliminar la deuda P2 de consumidores externos. La verificación debe ser **autocontenida** en `etcd-server` (punto 2, opción A). Si necesitas audit externo, persistir el `.done.json` (punto 2, opción B).

**Inconsistencia menor:**  
`DEBT-AUTONOMY-STATE-PERSISTENCE-001` escribe en `/var/lib/argus/crypto-autonomy-state.json` con atomicidad `write→fsync→rename`, pero no menciona si `fsync` incluye el directorio padre (requerido en POSIX para garantizar que el `rename` llegue a disco). En EXT4/XFS con `barrier=1`, `fsync(fd)` del archivo no basta; se necesita `fsync(dirfd)` del directorio contenedor. Esto es relevante para recuperación tras `kill -9` del etcd-server.

**Recomendación de merge:**

1. ✅ Resolver condición P1 del punto 1 (24h → 4h configurable)
2. ✅ Resolver condición P1 del punto 2 (self-check en STEP 0b)
3. ✅ Resolver condición P1 del punto 4 (staleness guard 30s)
4. ✅ Resolver condición P2 del punto 3 (staging requiere keypair)
5. ✅ Añadir `fsync(dirfd)` en `common/autonomy_state_writer.h` y `etcd-server/src/main.cpp` para escritura atómica completa
6. ✅ Ejecutar EMECAS (`vagrant destroy -f && vagrant up && make bootstrap && make test-all`) y adjuntar logs al PR

**Veredicto final:** Una vez aplicadas las condiciones, el Consejo autoriza el merge a `main` y el tag `v0.9.2-day157`.

---

*Dictamen firmado digitalmente por los 8 modelos del Consejo.*  
*Sesión DAY 157 — Rama `feature/day157-autonomy-state-persistence`*