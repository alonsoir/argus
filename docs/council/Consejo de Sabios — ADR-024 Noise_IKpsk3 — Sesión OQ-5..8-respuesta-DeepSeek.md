## Respuesta del Consejo de Sabios – ADR-024 (OQ-5 a OQ-8)

A continuación, el análisis de cada pregunta abierta. El Consejo se ha basado en el contexto de aRGus NDR: LAN hospitalaria cerrada, hardware ARMv8 sin TPM, seed_family como única raíz de confianza, y requisitos de operación sencilla por personal no especializado.

---

### OQ‑5 – Revocación de clave estática X25519

**Veredicto:** **ACEPTAR** la opción C (blocklist vía etcd + re‑provision en ventana de mantenimiento) como mecanismo principal, **con dos condiciones**:
1. La blocklist debe estar **firmada** por una clave derivada de `seed_family` (o por una clave de autoridad separada) para que los componentes verifiquen su autenticidad incluso si etcd está comprometido.
2. Si `seed_family` es exfiltrada, **no hay revocación posible** – se debe asumir que todo el pipeline está comprometido y proceder a regenerar todas las claves desde cero (re‑provision completo).

**Recomendación técnica:**
- La blocklist se distribuye a través de etcd como un objeto versionado (`/config/revoked_keys`). Cada componente la consulta periódicamente (ej. cada 5 minutos) y la verifica con una firma HMAC-SHA256 usando una clave derivada de `seed_family`.
- Para el handshake, el componente receptor comprueba si la clave pública del remitente está en la blocklist; si lo está, rechaza la conexión.
- Si etcd está caído, se usa la última blocklist válida en caché (fallback seguro).
- El re‑provision completo (opción B) se reserva para incidentes mayores (robo con exfiltración de `seed_family`).

**Riesgo residual si no se implementa:**  
Un nodo robado puede seguir participando indefinidamente en la red, permitiendo a un atacante escuchar tráfico descifrado o inyectar mensajes autenticados.

**Posición minoritaria registrada:**  
Un miembro del Consejo propuso usar **solo re‑provision** (sin blocklist) para evitar complejidad. Fue rechazado porque el downtime de re‑provision completo es inaceptable en entornos hospitalarios.

---

### OQ‑6 – Continuidad de sesión durante rotación de clave

**Veredicto:** **ACEPTAR** la opción A (dual‑key acceptance window) como solución más simple y segura para el primer lanzamiento, **con una mitigación adicional** para evitar downgrade.

**Recomendación técnica:**
- Cada componente mantiene una lista de “claves estáticas aceptadas” que incluye la clave actual (activa) y la nueva clave durante una ventana de **T = 48 horas** (configurable).
- La rotación se inicia manualmente o vía etcd: se publica la nueva clave pública junto con un timestamp.
- Durante la ventana, el componente acepta handshakes con cualquiera de las dos claves. Después de T, elimina la antigua.
- **Para evitar ataques de downgrade:** el componente nunca acepta una clave más antigua que la actual. Si un peer presenta una clave que ya fue retirada (pero aún dentro de la ventana de otra rotación anterior), se rechaza. La ventana es única por transición.

**Respuesta a preguntas específicas:**
1. ¿Dual‑key seguro? Sí, siempre que la clave antigua se descarte completamente después de la ventana y no se permita volver a ella.
2. ¿Hot update de `deployment.yml`? No es necesario si se usa el mecanismo de ventana; los componentes pueden leer la nueva clave desde etcd o un archivo local sin reiniciar.
3. Secuencia mínima para cero downtime:
   - Generar nuevo keypair en el componente a rotar.
   - Publicar la nueva clave pública en etcd (o archivo compartido).
   - Cada peer actualiza su lista de claves aceptadas (sin reiniciar).
   - El componente rotado empieza a usar la nueva clave para nuevos handshakes, pero sigue aceptando la antigua durante T.
   - Después de T, elimina la antigua de su propia configuración.

**Riesgo residual si no se implementa:**  
Rotación de clave requiere detener el pipeline, causando downtime. Esto viola el requisito operacional de hospitales.

**Posición minoritaria registrada:**  
Ninguna.

---

### OQ‑7 – Replay protection en primer mensaje del handshake

**Veredicto:** **ACEPTAR el riesgo documentado para v1** (no implementar timestamp), con la condición de que se añada una nota explícita en el threat model del paper.

**Recomendación técnica:**
- El primer mensaje (`→ e, es, s, ss`) no es replayable en el sentido de que un atacante no puede completar el handshake sin conocer el PSK (`seed_family`). El replay solo causa que el receptor realice cálculos inútiles, pero no permite descifrar ni inyectar tráfico autenticado.
- En una LAN hospitalaria controlada, el adversario realista ya tiene acceso a la red; un ataque de replay no añade capacidades significativas.
- Si se desea una protección adicional sin NTP, se puede incluir un **nonce generado por el receptor** en el primer mensaje (desafío). Sin embargo, eso añade un RTT extra (convirtiendo el handshake en 2‑RTT). No vale la pena para v1.

**Respuesta a preguntas específicas:**
1. ¿PSK suficiente? Sí, porque el PSK es necesario para derivar las claves de cifrado. Sin PSK, el handshake falla aunque se replique el primer mensaje.
2. Timestamp requeriría NTP sincronizado (no garantizado en entornos aislados). Ventana de ±30s es factible pero añade dependencia.
3. Escenario realista: un adversario podría inundar el receptor con paquetes replay para consumir CPU (DoS ligero). Pero el mismo adversario ya podría enviar tráfico legítimo falso; la mitigación real es la limitación de tasa (rate limiting), no timestamp.
4. **Veredicto:** ACEPTAR riesgo documentado.

**Riesgo residual si no se implementa:**  
Un atacante con acceso a la LAN podría causar una pequeña carga adicional de CPU (handshakes fallidos). No se considera crítico.

**Posición minoritaria registrada:**  
Un miembro abogó por implementar timestamp con ventana de 5 segundos, asumiendo NTP presente. La mayoría prevaleció por simplicidad.

---

### OQ‑8 – Rendimiento ARMv8 + comparación Noise_IKpsk3 vs Noise_KK

**Veredicto:** **MANTENER Noise_IKpsk3** para v1, con la recomendación de implementar directamente sobre libsodium (sin vendorear noise‑c) si noise‑c excede 200 KB.

**Recomendación técnica:**
- **Identity hiding** de IKpsk3 es marginalmente útil incluso en LAN cerrada: oculta qué componente está iniciando la conexión, reduciendo información para un atacante pasivo. No es crítico pero no perjudica.
- **KCI resistance** de KK (Key Compromise Impersonation) es teóricamente mejor, pero en la práctica, si un keypair estático se compromete, el atacante ya puede hacerse pasar por ese componente independientemente del patrón Noise. La diferencia no es relevante para el modelo de amenaza de aRGus.
- **Rendimiento:** X25519 + ChaCha20-Poly1305 + HKDF en ARMv8 Cortex‑A72 (Pi 4) debe estar por debajo de 50 ms. Estimar: X25519 ≈ 20-30 ms, ChaCha20-Poly1305 ≈ 5-10 ms, HKDF ≈ <1 ms. Total < 50 ms razonable.
- **Implementación directa sobre libsodium** es criptográficamente equivalente a noise‑c, pero se pierde la verificación de la librería (ruido de implementación). Se puede hacer una implementación propia de Noise_IKpsk3 usando libsodium con menos de 200 líneas de código. El Consejo recomienda esta ruta si noise‑c supera el límite de footprint.

**Respuesta a preguntas específicas:**
1. Beneficio real de identity hiding: bajo pero no nulo. No justifica cambiar a KK.
2. KCI resistance: no es un argumento suficiente porque el escenario de compromiso de clave estática ya está cubierto por revocación (OQ‑5).
3. Implementación sobre libsodium pierde el soporte de otros patrones Noise, pero para IKpsk3 es trivial. No se pierde seguridad.
4. Estimación < 50 ms es plausible; se deberá medir en hardware real.

**Riesgo residual si se implementa sobre libsodium (en lugar de noise‑c):**  
Mayor riesgo de errores de implementación en el handshake. Se recomienda revisión de código y tests formales.

**Posición minoritaria registrada:**  
Un miembro sugirió cambiar a Noise_KK por simplicidad y KCI. La mayoría rechazó por no aportar ventaja práctica y perder identity hiding.

---

**Conclusión del Consejo para ADR-024:**  
Las cuatro preguntas quedan resueltas según lo anterior. El autor puede proceder a la implementación de Noise_IKpsk3 con las siguientes directrices:

- Implementar revocación mediante blocklist firmada (OQ‑5) y rotación de clave con ventana dual (OQ‑6).
- Aceptar replay del primer mensaje como riesgo documentado (OQ‑7).
- Implementar handshake directamente sobre libsodium si noise‑c es demasiado grande; de lo contrario, vendorear noise‑c (OQ‑8).
- Actualizar el ADR-024 con estas decisiones y sus justificaciones.

*Via Appia Quality · Un escudo, nunca una espada.*  
*Acta del Consejo – 12 Abril 2026*