**OQ-5 — Revocación de clave estática X25519**

**Veredicto:** IMPLEMENTAR (combinación C con integración en deployment.yml)

**Recomendación técnica:**  
Integrar la “Fingerprint Blocklist” directamente como lista `allowed_static_keys` (por peer) dentro de deployment.yml; cada componente la consulta desde caché local antes de aceptar handshake (sin query a etcd en ruta crítica).  
Actualización de la lista se hace vía etcd hot-reload (sin restart).  
En caso de seed_family exfiltrada, ejecutar re-provision completo (nuevo seed_family + nuevos keypairs X25519) en ventana de mantenimiento; la rotación del PSK invalida automáticamente cualquier conexión del nodo robado.  
La combinación da respuesta inmediata (blocklist) y revocación total cuando el root-of-trust (seed_family) está comprometido.  
No se introduce ninguna dependencia nueva en la ruta crítica de handshake.

**Riesgo residual si no se implementa:** Impersonación indefinida del nodo robado (con static key + PSK conocido) hasta re-provision manual completo.

**Posición minoritaria registrada:** Ninguna.

**OQ-6 — Continuidad de sesión durante rotación de clave**

**Veredicto:** IMPLEMENTAR (opción A + B)

**Recomendación técnica:**  
Adoptar ventana de gracia dual-key (A) + versioned deployment.yml distribuido por etcd (B).  
Los componentes cargan los static keys desde config en cada nuevo handshake (no solo en init); noise-c/libsodium permiten esto sin restart.  
Secuencia mínima de rotación con cero downtime (6 componentes):
1. Generar nuevo keypair offline para el nodo objetivo.
2. Actualizar deployment.yml a versión N+1 con dual pubkey (old + new) para ese peer.
3. etcd distribuye → todos los componentes recargan config en próximo heartbeat.
4. Nodo rotado activa nueva private key inmediatamente.
5. Después de T (ej. 60 min) se publica versión N+2 con single new key.  
   Opción C (coordinator) es innecesaria y añade complejidad; el par A+B es suficiente y seguro en LAN cerrada.

**Riesgo residual si no se implementa:** Durante la ventana de gracia podría usarse temporalmente la clave antigua (riesgo práctico muy bajo en entorno sin adversario externo).

**Posición minoritaria registrada:** Ninguna.

**OQ-7 — Replay protection en primer mensaje del handshake**

**Veredicto:** ACEPTAR riesgo documentado para v1

**Recomendación técnica:**  
El binding PSK (seed_family) en Noise_IKpsk3 es protección anti-replay suficiente: sin PSK correcto el handshake aborta antes de completar y no se establece sesión.  
No añadir timestamp ni nonce en payload del primer mensaje: introduce complejidad de sincronía de relojes (NTP no fiable en LAN hospitalaria sin Internet) y overhead innecesario.  
Mantener la decisión provisional de ADR-024; documentar explícitamente el riesgo en sección “Threat Model” y “Accepted Risks”.  
Monitorizar en logs cualquier ráfaga de primeros mensajes replayed (puede indicar intento de DoS).  
Si el modelo de amenaza evoluciona (adversario activo persistente en LAN), considerar mitigación timestamp en v2.

**Riesgo residual si no se implementa:** Posible DoS menor por re-procesamiento de mensajes replayed (si la implementación no es completamente stateless), sin compromiso de confidencialidad ni autenticación.

**Posición minoritaria registrada:** Ninguna.

**OQ-8 — Rendimiento ARMv8 + comparación Noise_IKpsk3 vs Noise_KK**

**Veredicto:** CONDICIONAL (mantener Noise_IKpsk3 si benchmarks reales confirman footprint < 200 KB y latencia < 50 ms; evaluar cambio a Noise_KK si paridad)

**Recomendación técnica:**  
En despliegue cerrado (6 componentes, todas claves estáticas pre-provisionadas en deployment.yml) el identity-hiding de IKpsk3 no aporta beneficio real: todas las identidades ya son conocidas de antemano.  
Noise_KK es más simple (menos tokens, menos código), ofrece mejor resistencia KCI y cumple los mismos requisitos de 1-RTT y PSK (vía modificador psk si se requiere).  
noise-c vendored (commit-pinned) debe verificarse en ARMv8; si supera 200 KB, implementación directa sobre libsodium (X25519 + HKDF-SHA256 + ChaCha20-Poly1305) es criptográficamente equivalente para el patrón concreto, pero se pierde el framework Noise (validación formal de patrones y facilidad de auditoría).  
Estimación analítica en Cortex-A72 (Raspberry Pi 4/5): X25519 ≈ 1–2 ms, 2×ChaCha20-Poly1305 ≈ 0,1–0,2 ms, HKDF negligible → handshake completo << 10 ms (cumple holgadamente < 50 ms).  
Recomendación final: ejecutar benchmark real en hardware objetivo antes de producción; si paridad de rendimiento, cambiar a KK simplifica implementación y reduce superficie.

**Riesgo residual si no se implementa:** Ninguno significativo para v1 (IKpsk3 es funcional y seguro); únicamente mayor complejidad de código sin ganancia de seguridad en este entorno.

**Posición minoritaria registrada:** Equipo de implementación podría preferir mantener IKpsk3 por consistencia con ADR-024 ya aprobado (posición minoritaria razonable).

**Resumen global del ADR propuesto (puntos fuertes, débiles y a mejorar)**  
**Fuertes:** Uso correcto de Noise con PSK como único root-of-trust, diseño minimalista (sin TPM/PKI), enfoque en zero-downtime y hardware commodity.  
**Débiles:** Dependencia circular etcd/seed_family en revocación y rotación; falta de mecanismo de revocación totalmente offline.  
**A mejorar (prioridad alta):** Integrar allowed_static_keys en deployment.yml + hot-reload (resuelve OQ-5 y OQ-6 de forma elegante), y realizar benchmark real ARMv8 antes de producción (OQ-8).

El Consejo de Sabios aprueba avanzar a implementación de las recomendaciones anteriores. El diseño resultante es robusto, simple y adecuado para el entorno de hospitales/escuelas/municipios.