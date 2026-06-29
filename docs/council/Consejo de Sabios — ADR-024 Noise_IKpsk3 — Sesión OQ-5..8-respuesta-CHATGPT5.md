Evaluación directa y técnica por cada OQ.

---

# OQ-5 — Revocación de clave estática X25519

**Veredicto:** **CONDICIONAL (C: combinación obligatoria)**

**Recomendación técnica:**

* Blocklist local **firmada y distribuida fuera de etcd** (ej: fichero firmado cargado en arranque).
* etcd puede usarse como **canal de propagación**, pero no como raíz de confianza.
* Procedimiento estándar: *blocklist inmediata + rotación completa (keys + PSK)* en ventana controlada.
* Cachear blocklist en memoria para no depender de etcd en handshake.
* Añadir `key_epoch` en config para invalidación masiva.

**Riesgo residual si no se implementa:**
Nodo robado sigue autenticándose indefinidamente si PSK no rota.

**Posición minoritaria:**
Blocklist-only vía etcd es insuficiente; dependencia circular de confianza.

---

# OQ-6 — Continuidad de sesión durante rotación

**Veredicto:** **IMPLEMENTAR (A + B combinadas, C descartada)**

**Recomendación técnica:**

* **Dual-key window (A)** con límite corto (ej: 10–30 min) + flag explícito `rotation_in_progress`.
* Distribuir nuevas claves vía config versionada (B), recargable en caliente.
* Secuencia mínima:

   1. Distribuir nueva pubkey (sin activar)
   2. Activar modo dual-key en todos los nodos
   3. Rotar nodo a nodo
   4. Finalizar eliminando clave antigua
* Nunca confiar en coordinación fuerte vía etcd (C → frágil).

**Riesgo residual si no se implementa:**
Downtime o partición del pipeline durante rotaciones.

**Posición minoritaria:**
Coordinator-driven añade complejidad y punto único de fallo.

---

# OQ-7 — Replay protection primer mensaje

**Veredicto:** **IMPLEMENTAR (ligero, sin NTP estricto)**

**Recomendación técnica:**

* Añadir **timestamp coarse + nonce aleatorio** en payload del primer mensaje.
* Ventana permisiva: ±2–5 minutos (no requiere NTP perfecto).
* Cache LRU de nonces recientes (pequeño, en memoria).
* Rechazar duplicados dentro de ventana.
* No tocar el protocolo Noise, solo payload.

**Riesgo residual si no se implementa:**
Replay usable para DoS o amplificación en LAN comprometida.

**Posición minoritaria:**
Aceptar riesgo es razonable, pero mitigación cuesta casi cero y mejora robustez.

---

# OQ-8 — Noise_IKpsk3 vs Noise_KK + rendimiento

**Veredicto:** **CONDICIONAL (mantener IKpsk3 salvo benchmark negativo)**

**Recomendación técnica:**

* IKpsk3 sigue siendo mejor elección:

   * PSK integrado (clave en vuestro modelo)
   * Menor acoplamiento conceptual
* Identity hiding aporta poco en LAN, pero no penaliza.
* Si benchmarks muestran igualdad → mantener IKpsk3 por consistencia con ADR-024.
* Latencia estimada en Cortex-A72:

   * X25519 ~1–3 ms
   * Total handshake <10 ms → muy por debajo de 50 ms
* Si noise-c >200 KB:

   * Implementación sobre libsodium es válida
   * Se pierde: garantías formales del framework Noise + menor auditabilidad estándar

**Riesgo residual si no se implementa:**
Elección subóptima de patrón, pero impacto práctico bajo.

**Posición minoritaria:**
Noise_KK es más simple y KCI más fuerte, pero rompe modelo PSK-first.

---

# Observaciones transversales (importantes)

1. **Dependencia crítica real: `seed_family`**

   * Es vuestro “single point of catastrophic failure”.
   * Cualquier decisión (revocación, replay, rotación) colapsa si se filtra.

2. **etcd no puede ser raíz de confianza**

   * Solo transporte / sincronización.
   * Nunca decisión de seguridad crítica.

3. **Modelo correcto emergente**
   Estás convergiendo a:

   * PSK (identidad de dominio)
   * Static keys (identidad de nodo)
   * Firma offline (integridad de código, ADR-032)

   → Esto ya es una arquitectura seria, no un experimento.

4. **Complejidad vs operabilidad**

   * Cada mecanismo añadido debe poder ejecutarlo un sysadmin no experto.
   * Dual-key + script automatizado → bien
   * Coordinadores complejos → mal

---

# Conclusión

* OQ-5: combinación obligatoria, no confiar en etcd
* OQ-6: dual-key + config hot reload, diseño correcto
* OQ-7: implementar mitigación ligera (alto retorno, bajo coste)
* OQ-8: mantener IKpsk3 salvo evidencia empírica en contra

El diseño global es sólido y coherente. Los riesgos que quedan ya no son de diseño, sino de **gestión de secretos y operación en campo**, que es exactamente donde deben estar en este tipo de sistema.
