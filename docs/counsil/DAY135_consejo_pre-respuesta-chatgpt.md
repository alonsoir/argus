A continuación se responde a cada cuestión con recomendaciones concretas, justificación técnica y forma de verificación reproducible.

---

# Q1 — `FailureAction=reboot` en integridad de APT

### Recomendación

* **Mantener `FailureAction=reboot`**, pero con dos ajustes:

  1. **Persistencia de logs garantizada** antes del reboot.
  2. **Timeout ampliado a 60–90 segundos** (no 30s).
* **Hacer el timeout configurable vía JSON/etcd**, pero con un mínimo hardcoded (ej. 30s) para evitar desactivación accidental.

### Justificación técnica

* La decisión **fail-closed** es correcta: un sistema con supply-chain comprometido no es confiable.
* El riesgo real no es solo persistencia local, sino:

  * propagación lateral (ZeroMQ / etcd)
  * ejecución de binarios manipulados en reboot posterior
* 30s puede ser insuficiente en:

  * redes hospitalarias con congestión
  * entornos sin collector local (envío remoto lento)
* systemd no garantiza entrega de logs remotos antes de reboot.

### Riesgo

* **Reboot loop** si:

  * hash baseline corrupto
  * error de implementación
* **Pérdida de evidencia forense** si logs no se envían a tiempo

### Test reproducible

```bash
# 1. Corromper sources.list
echo "malicious" >> /etc/apt/sources.list

# 2. Reiniciar servicio
systemctl start argus-apt-integrity.service

# 3. Medir:
journalctl -u argus-apt-integrity.service
tcpdump -i eth0 port 514  # verificar envío de logs

# 4. Validar:
- reboot ocurre
- logs llegan antes del reboot
```

---

# Q2 — Transferencia segura de seeds

### Recomendación

**Opción C (generación local en hardened VM) es la arquitectura correcta.**

Complemento:

* Derivar seeds mediante:

  * **CSPRNG + entropy del sistema**
  * opcional: **KDF con identidad del nodo (machine-id)**

### Justificación técnica

* Eliminar transferencia elimina toda una clase de ataques:

  * MITM
  * exposición en disco intermedio (/vagrant)
* Seguridad > control centralizado en este caso
* Compatible con principios de:

  * **zero-trust**
  * **secret locality**

No viola ADR-013 si:

* las claves privadas **no necesitan ser compartidas entre nodos**
* el sistema está diseñado para **identidad local independiente**

### Alternativa válida (si necesitas distribución central)

* Noise IK (opción B) con:

  * claves bootstrap hardcoded
  * rotación posterior

### Riesgo

* Pérdida de capacidad de:

  * revocación centralizada
  * sincronización de secretos
* Entropía insuficiente en hardware embebido (ARM sin TRNG)

### Test reproducible

```bash
# Generar seed en hardened
hexdump -C /etc/ml-defender/*/seed.bin

# Reiniciar VM → verificar persistencia
# Comparar entre nodos → deben ser distintos
sha256sum seed.bin
```

---

# Q3 — ¿Bloqueantes antes de merge?

### Evaluación

**No hay bloqueantes críticos.**
El sistema cumple:

* aislamiento build/runtime ✔
* BSR verificado mecánicamente ✔
* AppArmor enforce ✔
* capabilities mínimas ✔
* pipeline reproducible ✔

### Recomendación

Aprobar merge con **2 condiciones menores**:

1. Añadir test de:

  * **reboot-loop prevention (APT integrity)**
2. Documentar explícitamente:

  * modelo de confianza de seeds (ADR complementario)

### Riesgo residual

* warnings de compilación (no crítico funcional)
* canal de seeds aún no hardened (ya reconocido)

---

# Q4 — Flujo `hardened-redeploy` + seeds

### Recomendación

El flujo actual es correcto, pero incompleto para ciertos escenarios.

Añadir:

```
make hardened-full-with-seeds
```

### Separación recomendada

| Caso                | Flujo                      |
| ------------------- | -------------------------- |
| Desarrollo          | `hardened-redeploy`        |
| Validación completa | `hardened-full`            |
| Deploy real         | `hardened-full-with-seeds` |

### Justificación técnica

* Seeds son **estado sensible**, no deben mezclarse con:

  * builds reproducibles
  * EMECAS puro
* Separación actual respeta:

  * determinismo del build
  * control explícito de secretos

### Riesgo

* Error humano al olvidar `prod-deploy-seeds`
* Inconsistencias entre nodos

### Test reproducible

```bash
make hardened-full
make prod-deploy-seeds
make check-prod-permissions

# validar:
ls -l /etc/ml-defender/*/seed.bin
```

---

# Q5 — Prioridad DAY 136

### Recomendación clara: **Opción B — ADR-029 Variant B (libpcap)**

### Justificación técnica

1. **Necesidad científica**

  * comparación XDP vs libpcap = resultado publicable
  * evidencia empírica, no afirmaciones

2. **Necesidad FEDER**

  * hardware ARM requiere fallback
  * XDP no siempre disponible

3. **Riesgo de no hacerlo**

  * sistema no portable
  * dependencia fuerte de kernel/NIC

4. **Valor estratégico**

  * demuestra:

    * adaptabilidad
    * ingeniería pragmática

### Orden recomendado

1. Variant B (libpcap ARM)
2. Demo reproducible FEDER
3. Luego:

  * presentación (A)
  * warnings (C)

---

# Respuesta técnica adicional — estado general

El sistema ha alcanzado un punto importante:

* separación build/runtime → correcta
* superficie de ataque → reducida estructuralmente
* reproducibilidad → demostrada
* seguridad → basada en mecanismos verificables, no configuración

El siguiente salto no es añadir features, sino:

* **validación en hardware real**
* **comparativas empíricas**
* **robustez cross-platform**

---

# Conclusión

* Q1: mantener reboot, ampliar timeout, asegurar logs
* Q2: generar seeds localmente (opción C)
* Q3: merge aprobado sin bloqueantes
* Q4: flujo correcto, añadir variante con seeds
* Q5: priorizar Variant B (libpcap)

El proyecto está listo para pasar de **ingeniería controlada** a **validación experimental real**, que es donde se obtiene valor científico y credibilidad externa.
