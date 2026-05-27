# 🏛️ CONSEJO DE SABIOS — RESPUESTA ADR-024 (OQ-5 a OQ-8)
*Feedback técnico, directo y proactivo para ML Defender (aRGus NDR)*

---

## 📋 Resumen Ejecutivo

| OQ | Tema | Veredicto | Prioridad |
|----|------|-----------|-----------|
| **OQ-5** | Revocación de clave estática | **CONDICIONAL** | Alta |
| **OQ-6** | Continuidad en rotación de clave | **ACEPTAR** | Media |
| **OQ-7** | Replay protection primer mensaje | **ACEPTAR (v1)** | Baja |
| **OQ-8** | Rendimiento ARMv8 + IKpsk3 vs KK | **ACEPTAR** | Media |

---

## 🔐 OQ-5 — Revocación de clave estática X25519

**Veredicto:** **CONDICIONAL** — Blocklist como mecanismo secundario; respuesta primaria es re-provision + rotación de `seed_family`.

**Recomendación técnica:**
Implementar caché local de fingerprints con TTL (ej. 1h) que no dependa de etcd para decisiones de handshake. La blocklist vía etcd sirve como defensa en profundidad, pero el protocolo debe asumir que si `seed_family` se exfiltra, la recuperación requiere rotación manual del PSK. Documentar procedimiento de emergencia: "Detectar compromiso → Rotar seed_family → Re-provisionar nodos sanos → Invalidar nodo robado".

**Riesgo residual si no se implementa:** Si `seed_family` es exfiltrada junto con la clave estática, un atacante puede impersonar cualquier nodo hasta que se complete la rotación manual del PSK.

**Posición minoritaria:** Algunos podrían argumentar que una CRL firmada offline (sin etcd) ofrecería revocación sin dependencia circular, pero añade complejidad operativa marginal para un escenario de baja probabilidad.

---

## 🔄 OQ-6 — Continuidad de sesión durante rotación de clave

**Veredicto:** **ACEPTAR** — Ventana de gracia dual-key (Opción A) es segura y suficiente.

**Recomendación técnica:**
Implementar ventana de gracia de 24-48h donde cada componente acepta ambas claves (antigua y nueva) en paralelo. Incluir timestamp de rotación en `deployment.yml` para invalidación automática de la clave antigua. No requiere coordinación en tiempo real ni ACKs; cada nodo transiciona de forma independiente al detectar la nueva configuración.

**Riesgo residual si no se implementa:** Ventana de exposición extendida si la clave antigua es comprometida durante el período de gracia, aunque el impacto se limita a los nodos que aún no han adoptado la nueva clave.

**Posición minoritaria:** Podría preferirse coordinator-driven rotation para mayor control auditado, pero introduce acoplamiento operacional innecesario para un entorno de 6 nodos en LAN cerrada.

---

## ♻️ OQ-7 — Replay protection en primer mensaje del handshake

**Veredicto:** **ACEPTAR para v1** — Riesgo documentado; mitigación operacional en capa de red.

**Recomendación técnica:**
Documentar explícitamente en §10.11 del paper que el primer mensaje es técnicamente replayable, pero que sin PSK el replay no puede completar el handshake ni comprometer confidencialidad. Mitigar riesgo de DoS por replay masivo mediante rate-limiting a nivel de red (nftables/iptables) con límite de handshakes por fuente IP por minuto. Re-evaluar mitigación a nivel de protocolo para v2 si se observan patrones de ataque.

**Riesgo residual si no se implementa:** Ataque de agotamiento de recursos mediante replay masivo del primer mensaje, forzando al responder a realizar operaciones criptográficas costosas sin completar sesión.

**Posición minoritaria:** Podría argumentarse que añadir un nonce simple (contador monótono por peer, sin NTP) eliminaría el riesgo con coste mínimo, pero introduce estado adicional que complica la implementación inicial.

---

## ⚡ OQ-8 — Rendimiento ARMv8 + Comparación Noise_IKpsk3 vs Noise_KK

**Veredicto:** **ACEPTAR** — Noise_IKpsk3 es la elección correcta para v1.

**Recomendación técnica:**
Mantener Noise_IKpsk3 con PSK binding. Documentar que el "identity hiding" del iniciador ofrece beneficio marginal en LAN cerrada con 6 componentes conocidos, pero no tiene coste adicional. Ejecutar benchmark real en Raspberry Pi 4/5 antes de producción para validar: (1) binary footprint < 200 KB, (2) handshake latency < 50 ms. Si noise-c excede límites, considerar implementación directa sobre libsodium solo como fallback, no como ruta principal.

**Riesgo residual si no se implementa:** Si noise-c excede 200 KB o el handshake supera 50 ms en ARMv8, se requeriría refactorización de emergencia hacia libsodium directo, con mayor esfuerzo de auditoría y riesgo de introducir bugs criptográficos.

**Posición minoritaria:** Podría argumentarse que Noise_KK es más simple y suficiente para el modelo de amenaza de LAN cerrada, eliminando complejidad de PSK binding; sin embargo, IKpsk3 alinea mejor con la filosofía de "vendor-controlled trust" del proyecto.

---

## 🎯 Observaciones Transversales Proactivas

### 1. Documentar el "contrato de recuperación"
Añadid al ADR-024 una sección explícita:
```markdown
## Recovery Contract
- Si se compromete una clave estática: rotar seed_family + re-provisionar.
- Si se compromete seed_family: asumir compromiso total; rotar todas las claves + re-provisionar todos los nodos.
- Tiempo estimado de recuperación: < 30 minutos con provision.sh automatizado.
```

### 2. Prueba de "fire drill" en CI
Incluir un test de integración que simule:
```bash
# Simular rotación de clave en un componente
$ make rotate-key COMPONENT=ml-detector
# Verificar que los peers aceptan ambas claves durante ventana de gracia
# Verificar que después de T, la clave antigua es rechazada con log claro
```

### 3. Estimación analítica de rendimiento (para tranquilidad)
En Cortex-A72 (Pi 4):
- X25519: ~120 µs
- ChaCha20-Poly1305 (1KB): ~80 µs
- HKDF-SHA256: ~25 µs
- Handshake completo (2×AEAD + derivaciones): **~3-8 ms estimado**

El objetivo < 50 ms es holgadamente alcanzable; el cuello de botella será la red, no la criptografía.

---

## 📋 Checklist de Acciones Inmediatas

```markdown
- [ ] Actualizar ADR-024 con veredictos de OQ-5 a OQ-8
- [ ] Implementar caché local de fingerprints con TTL (OQ-5)
- [ ] Añadir ventana dual-key en plugin-loader (OQ-6)
- [ ] Documentar riesgo de replay en §10.11 del paper (OQ-7)
- [ ] Ejecutar benchmark real en Raspberry Pi 4 (OQ-8)
- [ ] Crear procedimiento de emergencia "Compromise Recovery" en docs/
```

---

## 🏁 Palabras Finales

ADR-024 representa una elección criptográfica madura y pragmática. Las preguntas que planteáis (OQ-5 a OQ-8) son exactamente las que separan un diseño teórico de uno operable en el mundo real.

**La conclusión general es clara**: Noise_IKpsk3 con PSK binding es la base correcta para v1. Los riesgos residuales son gestionables mediante procedimientos operacionales, no mediante complejidad criptográfica adicional.

> *"En seguridad, la simplicidad operativa es una feature, no un bug."*

Proceded con confianza. Implementad, medid en hardware real, y documentad los resultados. El Consejo está disponible para revisar los benchmarks cuando estén listos.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 115** 🛡️