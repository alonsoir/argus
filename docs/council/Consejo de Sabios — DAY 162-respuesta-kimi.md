**Sesión Plenaria del Consejo de Sabios — aRGus NDR**  
*Asunto: Ciclo de vida criptográfico enterprise (DAY 161)*  
*Quorum: 8 miembros presentes*

---

### Dictamen del Sabio #1 — *Arquitecto de Seguridad (Crypto)*

**Riesgo principal:** El keypair vendor (`01cd1509...`) hardcodeado en `CMakeLists.txt` es un secreto de compilación, no de runtime. Cualquier binario community compilado con el flag enterprise inadvertidamente embarca la clave pública del vendor, ampliando la superficie de ataque.

**Recomendación:**
1. **Inmediato:** Mover la clave pública del vendor fuera del árbol de fuentes. Debe inyectarse en el pipeline de build como secreto de CI (Jenkins Credential + CMake `-DARGUS_VENDOR_PUBKEY_B64=...`), nunca en git.
2. **Antes de rotación automática:** Implementar `CryptoProvider::reload()` con semántica RCU (Read-Copy-Update) para que threads en vuelo usen el keypair activo mientras se carga el nuevo, sin lock global.
3. **Orden:** Seguridad de build → Hot-reload seguro → Rotación.

**Veto explícito a:** Generar el keypair privado del vendor en Jenkins sin HSM o al menos envelope encryption con Vault Transit. Si Jenkins es el CA, Jenkins es el target.

---

### Dictamen del Sabio #2 — *Arquitecto de Sistemas Distribuidos*

**Riesgo principal:** ADR-013 establece que la rotación debe ser atómica entre extremos ZMQ. Sin un coordenador de cut-over, tendrás partición de red criptográfica: Node-A habla con Keyₙ, Node-B con Keyₙ₊₁, y el canal Noise_IKpsk3 falla silenciosamente (no hay retry cripto en ZMQ, se desconecta).

**Recomendación:**
1. **Implementar primero:** Un `CryptoEpoch` monotónico en etcd. Todos los componentes observan `/argus/crypto/epoch/<component_id>`.
2. **Protocolo de rotación:**
    - Fase 1: Jenkins genera nuevo keypair, lo sube a Vault KV v2 (versión explícita).
    - Fase 2: Jenkins escribe `epoch_target=N+1` en etcd con TTL de lease.
    - Fase 3: Cada componente, al ver `epoch_target > local_epoch`, carga nueva clave *pero no la activa*.
    - Fase 4: Jenkins verifica que todos los componentes reportan `epoch_ready=N+1` (health check semántico).
    - Fase 5: Jenkins escribe `epoch_active=N+1`.
    - Fase 6: Componentes activan la nueva clave simultáneamente.
3. **Rollback:** Si Fase 5 no converge en T segundos, Jenkins revierte `epoch_active=N`.

**Dependencia crítica:** etcd debe tener autenticación mTLS *antes* de que el coordenador de rotación entre en producción. Si etcd es abierto, cualquier nodo malicioso puede forzar una rotación DoS.

---

### Dictamen del Sabio #3 — *Ingeniero de Platform / Vault*

**Riesgo principal:** `enterprise_vendor.key` vive en la VM, no en Vault. Esto rompe el principio de "Vault como único source of truth". Si la VM muere, perdemos la capacidad de validar tokens enterprise existentes.

**Recomendación:**
1. **Orden de implementación:**  
   a. Subir `enterprise_vendor.key` a Vault KV (`secret/argus/enterprise/vendor-key`).  
   b. Modificar `plugin-loader` para leer la clave pública de Vault (con cache local + watcher) en lugar de CMake.  
   c. Implementar `vault-agent` o `consul-template` sidecar para inyectar el token enterprise en los componentes que lo necesiten (ml-detector, etcd-server, etc.), eliminando la distribución manual.
2. **Jenkins ↔ Vault:** Usar AppRole de Vault con wrapped secret-id (single-use, TTL corto). Jenkins pide un wrapped token, lo desempaqueta, genera el keypair, lo escribe en Vault, destruye el secret-id.
3. **Distribución de token enterprise:** No distribuir el token a los componentes. Distribuir una *Vault role-id* y que cada componente se autentique con Vault usando su propia identidad (SPIFFE/SPIRE o al menos certificado mTLS de host). El token enterprise debe ser un artifact efímero que solo el `plugin-loader` consume para validar plugins.

**Veto explícito a:** Distribuir el token enterprise como variable de entorno o archivo plano en los nodos. Debe ser siempre "request-on-load" desde Vault.

---

### Dictamen del Sabio #4 — *Arquitecto P2P / ZMQ*

**Riesgo principal:** El canal Noise_IKpsk3 usa un psk (pre-shared key) que probablemente deriva del seed enterprise. Si rotamos el seed y el canal ZMQ está en medio de un handshake, el handshake falla y no hay reintentos automáticos en la capa cripto. ADR-013 es claro: ambos extremos deben rotar en el mismo instante lógico.

**Recomendación:**
1. **Primero:** Instrumentar métricas de "crypto handshake failures" por canal ZMQ. Sin observabilidad, no sabrás si una rotación falló hasta que ml-detector deje de reportar.
2. **Segundo:** Implementar un "grace period" en el componente ZMQ: durante 2× el intervalo de heartbeat, aceptar tanto el key anterior como el nuevo. Esto requiere que `NoiseState` mantenga un `key_ring[epoch]` con ventana deslizante de 2 epochs.
3. **Tercero:** Solo entonces habilitar rotación automática.

**Dependencia:** Esto toca `safe_path` (primitivas cripto). Necesitamos property tests que verifiquen que un mensaje cifrado con Keyₙ puede ser descifrado con Keyₙ y Keyₙ₊₁ durante la ventana de grace, pero nunca con Keyₙ₊₂.

---

### Dictamen del Sabio #5 — *Ingeniero de Calidad / E2E*

**Riesgo principal:** `test-e2e-vault` con Vault dev-mode no valida el ciclo de vida real. Vault dev no persiste, no tiene HA, y no replica. Un test de rotación en dev-mode es un false positive de seguridad.

**Recomendación:**
1. **Inmediato:** Crear `test-e2e-rotation` que levante un cluster Vault en modo HA (Raft, 3 nodos, Docker Compose) y ejecute el protocolo de 6 fases del Sabio #2.
2. **Criterio de aceptación:** Durante la rotación, el throughput de eventos ZMQ no cae >5% y no hay desconexiones permanentes (>3s).
3. **Property test:** Para todo `epoch`, `decrypt(encrypt(msg, epoch), epoch) == msg` y `decrypt(encrypt(msg, epoch), epoch+1) == FAIL` (excepto durante grace window explícita).
4. **Orden:** Este gate E2E debe existir *antes* de mergear la rotación automática. No después.

---

### Dictamen del Sabio #6 — *Arquitecto de Estado / etcd*

**Riesgo principal:** Usar etcd como coordenador de rotación sin considerar particiones de red. Si un nodo está particionado durante la rotación, su `epoch_local` queda desfasado. Al reincorporarse, intentará hablar con key antigua y será rechazado por el cluster.

**Recomendación:**
1. **Primero:** Implementar `epoch_local` como parte del estado persistente de cada componente (fichero local en `/var/lib/argus/crypto_epoch`). Al arrancar, un componente debe saber qué epoch espera, no preguntar etcd desde cero.
2. **Segundo:** Definir política de "epoch skew máxima tolerada". Si un nodo arranca con `epoch_local = N` pero el cluster está en `N+3`, abortar con `FATAL: crypto epoch drift too large, manual intervention required`. Esto evita que un nodo stale intente conectar con keys obsoletas y genere ruido de alertas.
3. **Tercero:** etcd debe usar autenticación con el token enterprise (o mejor, con certificados mTLS rotados por un CA independiente). No podemos depender de etcd sin auth para coordinar la auth.

---

### Dictamen del Sabio #7 — *Ingeniero de Operaciones / SRE*

**Riesgo principal:** Si la rotación automática falla a las 3 AM, ¿quién sabe qué hacer? Un sistema que rota claves automáticamente pero requiere un runbook de 40 pasos para recuperarse es más peligroso que la rotación manual.

**Recomendación:**
1. **Antes de automatizar:** Documentar el runbook de "rotación manual de emergencia" que funcione con los mecanismos del Sabio #2 pero disparados por un humano via CLI (`argusctl crypto rotate --epoch=N+1`).
2. **Observabilidad:** Cada componente debe exponer métricas:
    - `argus_crypto_epoch_local`
    - `argus_crypto_epoch_target`
    - `argus_crypto_rotation_latency_seconds`
    - `argus_crypto_handshake_failures_total`
3. **Circuit breaker:** Si `handshake_failures` > umbral durante una ventana post-rotación, el componente debe auto-revertir a `epoch-1` (si la clave aún está en memoria) y alertar. Nunca dejar un nodo aislado criptográficamente.
4. **Orden:** Runbook manual → Métricas → Circuit breaker → Automatización.

---

### Dictamen del Sabio #8 — *Arquitecto Jefe / Integrador*

**Riesgo sistémico:** Estamos tratando de automatizar un pipeline criptográfico enterprise cuando aún no hemos resuelto el "bootstrap paradox": ¿cómo se autentica Jenkins con Vault para generar el primer keypair, si el token que usa Jenkins para hablar con Vault es él mismo un secreto enterprise? Y ¿cómo se autentica el primer nodo aRGus para leer de Vault si aún no hay token enterprise distribuido?

**Recomendación integrada (roadmap mínimo viable):**

| Fase | Pieza | Riesgo mitigado | Dependencias |
|------|-------|-----------------|--------------|
| **0** | Mover pubkey vendor de CMake a Vault KV + inyección en build | Secreto en fuente | Ninguna |
| **1** | `plugin-loader` lee pubkey de Vault (caché local + reload) | Runtime coupling a build | Fase 0 |
| **2** | Implementar `CryptoEpoch` en etcd + health semántico | Coordinación distribuida | etcd auth mTLS |
| **3** | Implementar `reload()` RCU en `CryptoProvider` | Zero-downtime key swap | Fase 1 |
| **4** | Grace window de 2 epochs en ZMQ Noise | ADR-013 compliance | Fase 3 |
| **5** | `test-e2e-rotation` con Vault HA + throughput check | Validación real | Fases 2-4 |
| **6** | Runbook manual + métricas + circuit breaker | Operabilidad | Fase 5 |
| **7** | Automatizar Jenkins: generación → Vault → epoch bump | Cierre del ciclo | Fases 0-6 |
| **8** | Distribución via Vault Agent / SPIFFE (no token plano) | Eliminación de secreto estático | Fase 7 |

**Veto del Consejo a producción:** No considerar production-ready hasta que:
1. El keypair vendor no esté en git ni en binarios community.
2. Exista `test-e2e-rotation` verde en CI.
3. El runbook de rollback manual haya sido ejecutado exitosamente en un drill.
4. Todos los componentes expongan métricas de `crypto_epoch`.

---

### Veredicto Unánime del Consejo

**No se autoriza la rotación automática (Fase 7) hasta que las Fases 0-6 estén implementadas y verdes.**

El ciclo de vida mínimo viable es:
1. **Vault como único source of truth** (Fase 0-1).
2. **Coordinación explícita via etcd con epochs** (Fase 2).
3. **Recarga segura con RCU + grace window criptográfica** (Fases 3-4).
4. **Validación E2E realista** (Fase 5).
5. **Operabilidad y rollback manual** (Fase 6).
6. **Automatización** (Fase 7).

**Riesgo arquitectural crítico pendiente:** Si se implementa la rotación antes de la grace window en ZMQ, el sistema será inherentemente frágil en redes con latencia variable. ADR-013 no es opcional; es un requisito de diseño, no de deployment.

**Próximo paso inmediato:** Crear ADR-0XX "Crypto Epoch Coordination" que formalice el protocolo de 6 fases y las métricas de salud requeridas. El Consejo exige que esta ADR sea aprobada antes de cualquier PR de Fase 2 en adelante.

*Sesión cerrada. Quorum mantenido.*