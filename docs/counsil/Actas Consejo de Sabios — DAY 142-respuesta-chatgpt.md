Revisión técnica del DAY 142 con foco en robustez real en producción crítica.

---

# Evaluación general del trabajo del día

El salto cualitativo es claro: el IRP deja de ser arquitectura y pasa a ser **sistema ejecutable y verificable**.
El diseño de `argus-network-isolate` tiene buenas propiedades:

* atomicidad real (`nft -f`)
* validación previa (`-c`)
* rollback automático (timer)
* separación como binario independiente (correcto para confinamiento)

Dicho esto, hay puntos donde el sistema aún puede fallar en escenarios reales adversos.

---

# P1 — Criterio de disparo

**Conclusión:**
El umbral único es correcto para FEDER, pero **insuficiente para producción hospitalaria**.

### Problema del umbral simple

Un único `score >= 0.95`:

* es fácil de auditar ✔
* pero es vulnerable a:

  * falsos positivos puntuales
  * ataques de trigger (DoS lógico)

Ejemplo real:

* un flujo mal clasificado como ransomware → aislamiento completo
* impacto clínico inmediato

### Recomendación (pragmática, no over-engineered)

No ir a una matriz compleja arbitraria. Usar un **modelo híbrido mínimo**:

```id="3d9b0g"
trigger =
  score >= 0.95
  AND event_type ∈ {ransomware, c2_beacon}
  AND burst >= N eventos en ventana corta
```

Donde:

* `N = 2 o 3`
* ventana = 10–30s

### Por qué este modelo

* evita disparos por eventos aislados
* sigue siendo explicable
* introduce **histeresis mínima**

### Estándar industria equivalente

* sistemas EDR/XDR usan:

  * severity + confidence + frequency
* nunca dependen de una sola señal

### Veredicto

* FEDER: umbral simple ✔
* producción: **añadir condición de burst mínima (obligatorio)**

---

# P2 — `execv()` vs `fork() + execv()`

**Conclusión:**
`fork() + execv()` es la única opción correcta.

Tu intuición es correcta, pero hay más implicaciones.

### Problema de `execv()`

* destruye el proceso `firewall-acl-agent`
* pierdes:

  * telemetría
  * correlación de eventos
  * capacidad de logging durante aislamiento

En términos de seguridad:
→ reduces visibilidad justo en el momento crítico

### Recomendación completa

```cpp id="r1u0sl"
pid = fork()
if (pid == 0) {
    execv(...)
}
```

Pero además:

### Mejora clave (importante)

* usar **supervisión del hijo**:

  * `waitpid` no bloqueante o señal
  * logging del exit status

### Alternativa más robusta (nivel superior)

Usar systemd directamente:

```bash id="tv2n3b"
systemd-run --unit=argus-isolate ...
```

Ventajas:

* aislamiento de recursos (cgroups)
* logging automático (journal)
* reinicio controlado

### Veredicto

* mínimo: `fork + execv`
* ideal: delegar a systemd-run

---

# P3 — AppArmor: enforce vs complain

**Conclusión:**
`enforce` desde el inicio es correcto, pero con una condición crítica.

### Riesgo real

`argus-network-isolate`:

* ejecuta `nft`
* interactúa con red
* usa systemd

Un perfil incompleto en `enforce` puede:
→ bloquear el aislamiento en el momento crítico

### Recomendación equilibrada

1. Desarrollo:

  * generar perfil en `complain`
  * capturar accesos reales

2. Antes de merge a main:

  * pasar a `enforce`
  * con cobertura validada por tests IRP

### Patrón industria

* AppArmor/SELinux siempre siguen ciclo:

  * observe → refine → enforce

### Veredicto

* tu postura es válida **si ya está testeado en flujo completo**
* si no: estás introduciendo riesgo silencioso

---

# P4 — Rollback y estado persistente

**Conclusión:**
El diseño actual es correcto para FEDER, pero **incompleto para producción**.

### Problema actual

Solo manejas:

* tabla `argus_isolate`

No gestionas:

* reglas externas del sistema
* configuraciones del cliente
* cambios concurrentes

### Riesgo real

En entorno hospitalario:

* pueden existir reglas personalizadas
* el aislamiento puede interferir con ellas
* rollback no restaura intención original

### Recomendación por fases

### FEDER (correcto)

* mantener diseño actual ✔
* simple, demostrable

### Producción (necesario)

Implementar **last-known-good snapshot**:

```id="qk1qv3"
/etc/argus/firewall/last-known-good.nft
```

Pero con matiz importante:

⚠️ No snapshot completo global (puede romper otras herramientas)

→ snapshot **scope controlado**, por ejemplo:

* solo tablas gestionadas por Argus
* o namespace dedicado (`argus_*`)

### Alternativa más avanzada

* usar `nft list ruleset` + tagging de reglas Argus
* restauración selectiva

### Veredicto

* FEDER: OK
* producción: persistencia parcial obligatoria

---

# Observaciones adicionales (no preguntadas, pero críticas)

## 1. Riesgo en aislamiento de interfaces

```bash
ip link set ethX down
```

Problemas:

* no es reversible sin contexto
* puede afectar routing inesperadamente

Alternativa más segura:

* filtrar tráfico con nftables (drop)
* no bajar interfaz

→ más control, menos efectos colaterales

---

## 2. Timer de rollback (300s)

Buen diseño, pero:

* ¿qué pasa si:

  * systemd falla?
  * el proceso muere?

Recomendación:

* watchdog adicional o confirmación explícita

---

## 3. Exclusión mutua con tmux

Funciona en dev, pero:

* no es robusto en producción
* depende de herramienta de usuario

Alternativa real:

* lockfile (`flock`)
* PID file

---

# Resumen ejecutivo del Consejo

### Decisiones validadas

* separación en binario independiente ✔
* transacciones nftables ✔
* rollback automático ✔
* `fork + execv` ✔

### Cambios recomendados (alta prioridad)

1. Añadir **burst condition** al trigger (
