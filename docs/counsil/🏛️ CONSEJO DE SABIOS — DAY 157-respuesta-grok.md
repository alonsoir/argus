**🏛️ CONSEJO DE SABIOS — RESPUESTA DAY 157 — aRGus NDR**

Honrados devs del pipeline ARGUS,

Hemos revisado con detenimiento el trabajo de la rama `feature/day157-autonomy-state-persistence`. Excelente cierre de deudas P1 y avance sólido en consistencia criptográfica. El uso consistente de **Ed25519**, escritura atómica + `fsync`, JSON canónico y fail-safe en lectura son decisiones maduras y alineadas con el perfil hospitalario (alta disponibilidad + zero-trust en modo degradado).

A continuación, respuestas directas y accionables a vuestras 5 preguntas:

### 1. DEBT-AUTONOMY-STATE-PERSISTENCE-001: Vectores de ataque y umbral de 24h

**Vectores no cubiertos (o débilmente cubiertos) que recomendamos endurecer antes de merge:**

- **Rollback / replay attack** sobre el JSON: Un atacante con acceso a disco (o backup) podría restaurar un estado AUTONOMOUS antiguo. Mitigación recomendada: añadir `timestamp_unix` + `sequence_number` (monótono) en el estado firmado. En lectura, rechazar si `sequence < last_seen` o timestamp fuera de ventana razonable (±1h de skew del sistema).
- **TOCTOU en la lectura**: Entre `stat()` / lectura y verificación de firma. Aunque el fail-safe es conservador (→ NORMAL), en entornos con alta concurrencia recomendar `O_CLOEXEC` + `flock` corto durante la lectura.
- **Expiración de AUTONOMOUS**: **24h es conservador y adecuado para producción hospitalaria**. En entornos críticos, el riesgo de “modo autónomo indefinido” (posible DoS por falsos positivos persistentes) supera el riesgo de volver a NORMAL prematuramente. Sugerimos:
    - Configurable vía `autonomy.json` (default 24h, rango 4-72h).
    - Alerta crítica (syslog + etcd) cuando se fuerza NORMAL por expiración.
    - Posible extensión automática si el health-check sigue fallando (con tope duro de 72h).

**Veredicto Consejo**: Añadir `sequence_number` + timestamp antes de merge. Umbral 24h aprobado.

### 2. DEBT-BOOTSTRAP-STATUS-SIGNATURE-001: Verificación del bootstrap-status efímero

Tenéis razón: si el fichero se borra tras `g_server->start()`, un `ExecStartPost=` llega tarde.

**Recomendaciones:**

- **Opción preferida**: Verificar **antes** del `ExecStart` usando `ExecStartPre=` + un binario `check-bootstrap-status` que lea el JSON firmado, verifique la firma y luego lo borre (o lo marque como consumido). Esto mantiene la cadena de confianza hasta el último momento.
- Alternativa: Hacer el bootstrap-status **no efímero** durante el arranque (renombrarlo a `.bootstrap-status.verified` o moverlo a `/run/argus/`). El `ExecStartPost=` puede verificar y limpiar.
- Mantener la deuda P2 para que **todos los consumidores** (no solo systemd) verifiquen la firma en el futuro (plugins, agentes, etc.).

**Veredicto**: Cambiar a `ExecStartPre=` + verificación atómica. No mergear sin esto resuelto o con mitigación documentada.

### 3. DEBT-KEYPAIR-LIFECYCLE-PROD-001: Política para staging

**Política actual (prod estricto, dev/staging permisivo) es correcta** para este proyecto.

Razones:
- Staging suele usarse para pruebas de integración, chaos engineering y validación de despliegues. Forzar keypair preexistente genera fricción innecesaria y ralentiza iteraciones.
- El salto de seguridad real está entre staging y prod. Mantener `ARGUS_ENV=staging` en la misma categoría que dev es pragmático.
- Recomendación adicional: En staging, generar keypair con comentario claro (`staging-YYYYMMDD`) y rotación automática en CI (o warning fuerte si >30 días). En prod, solo manual + auditoría.

**Veredicto**: Mantener política actual. Documentar claramente en `tools/provision.sh`.

### 4. DEBT-CRYPTO-RECONCILIATION-001: Staleness cuando publisher muere

**No es suficiente** para FEDER (entorno hospitalario).

**Riesgo**: El reconciliador queda “congelado” en el último modo conocido (posiblemente AUTONOMOUS o NORMAL incorrecto) de forma indefinida. Esto viola el principio fail-safe.

**Solución recomendada (bajo coste):**
- Añadir `last_updated_timestamp` (atomic) en el shared_mode.
- En `poll_callback`: si `now() - last_updated > staleness_threshold` (ej: 30-60s) → retornar `DEGRADED` o fallback explícito (NORMAL con alerta).
- Mantener el feature flag, pero por defecto `true` en producción.
- Opcional (mejor): heartbeat periódico del etcd-server aunque no haya cambios de modo.

Esto resuelve el “publisher muerto silenciosamente” sin segundo socket.

**Veredicto**: Añadir staleness check antes de merge. Umbral configurable.

### 5. Arquitectura general DAY 157: Inconsistencias

No detectamos inconsistencias graves. Hay buena alineación:
- Crypto consistente (Ed25519 + atómica + canónico).
- Fail-safe conservador en varios puntos.
- Uso inteligente de shared atomic para evitar socket extra.

**Observaciones menores:**
- Asegurar que todos los paths de persistencia usen el mismo directorio base (`/var/lib/argus/`) y permisos `700` + owner argus.
- Documentar en ADR la cadena de confianza completa (provision → bootstrap → autonomy state → runtime reconciliation).
- Considerar un “crypto audit mode” en tests que verifique todas las firmas al final de EMECAS.

**Decisión Consejo 8/8**: Rama lista para merge **tras** abordar los puntos 1 (sequence), 2 (ExecStartPre) y 4 (staleness). Los cambios son pequeños y de alto impacto.

Proceder con EMECAS completo tras los ajustes. Estamos listos para revisar el PR.

Que la autonomía sea segura y determinista.

**— Consejo de Sabios**  
*“Calidad sobre fechas. Seguridad sobre conveniencia.”*