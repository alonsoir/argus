Evaluación directa, con foco en lo que puede fallar en producción real.

---

# Valoración global DAY 116

**Estado:** Muy sólido.
Has cruzado un punto importante: el sistema ya no solo funciona, **se defiende activamente contra errores operativos**.

El hallazgo del `seed_family` no es menor:

> Has descubierto un **invariante criptográfico crítico no documentado**.

Eso, en otro contexto, habría acabado en caída total en producción.

---

# Puntos fuertes

### 1. `--reset` bien diseñado (muy importante)

* Fail-closed validado → correcto
* Recovery path probado → imprescindible
* Backup automático → evita desastre humano

Esto ya es nivel sistema serio.

---

### 2. TEST-PROVISION-1 (7/7) está en el camino correcto

Ahora mismo es:

> Tu “última línea de defensa antes de producción”

Especialmente acertado:

* permisos
* consistencia plugins
* fail temprano con instrucciones

---

### 3. AppArmor bien planteado (clave)

* Has incluido paths de provisioning → acierto crítico
* 0 denials en complain → buena cobertura inicial
* Separación por componente → correcta

---

# Puntos débiles (importantes)

### 1. `seed_family` sigue siendo un punto de fallo catastrófico

Ahora mismo tienes:

* 1 secreto compartido
* sin rotación automática coordinada
* sin protección hardware

**Problema real:**
Si se filtra → todo el sistema cae criptográficamente.

---

### 2. Permisos `640 root:vagrant` (esto hay que corregirlo)

Esto es un compromiso de entorno dev, no de producción.

* `vagrant` no debe existir en producción
* grupo compartido = superficie innecesaria

---

### 3. AppArmor aún no ha sido “probado de verdad”

0 denials en complain puede significar:

* bien perfilado
  **o**
* demasiado permisivo

Ahora mismo no lo sabes.

---

# Respuestas a tus preguntas

---

## Q1 — AppArmor enforce strategy

**Veredicto:** **Orden: menor privilegio → mayor privilegio (correcto)**

**Secuencia recomendada:**

1. rag-* + ml-detector
2. etcd-server
3. firewall-acl-agent
4. sniffer (último, más delicado)

**Ajuste clave:**

* sniffer: mantener más tiempo en complain
* firewall: validar manualmente reglas activas

**Riesgo si no se sigue:**
Rompes captura o bloqueo → pérdida de capacidad defensiva sin darte cuenta

---

## Q2 — DEBT-SEED-PERM-001

**Veredicto:** **(a) Corregir mensaje + migrar a 600 en producción**

**Recomendación concreta:**

* DEV: permitir 640 (temporal)
* PROD: exigir 600 (`root:root`)

**Nunca:**

* correr todo como root (descartado completamente)

**Riesgo si no se corrige:**
Lectura del seed por procesos no previstos → compromiso total del sistema

---

## Q3 — Próxima fase

**Veredicto:** **NO abrir ADR-026 aún**

**Orden correcto:**

1. AppArmor → enforce completo
2. Resolver DEBTs críticos
3. Validación en entorno realista (no solo Vagrant)
4. THEN ADR-026

**Razonamiento:**
Ahora mismo estás en fase de:

> “cerrar superficie”, no “añadir capacidad”

**Riesgo si no se sigue:**
Construyes sobre base insegura → deuda exponencial

---

## Q4 — seed_family como ADR

**Veredicto:** **SÍ — ADR propio (ADR-033)**

**Porque:**
No es un detalle → es:

* raíz de confianza
* dependencia global
* punto único de fallo

Debe definir:

* generación
* almacenamiento
* rotación
* recovery

**Riesgo si no se documenta:**
El siguiente cambio rompe CryptoTransport otra vez

---

# Observaciones críticas adicionales

---

## 1. Falta una cosa clave: detección de drift

Ahora mismo verificas:

* estado inicial (provision)

Pero no:

* cambios en runtime

Necesitas en el futuro:

* verificación periódica (timer systemd o similar)

---

## 2. `--reset` es poderoso (y peligroso)

Ahora mismo:

* puede ejecutarse → cambia TODO

Falta:

* confirmación fuerte (tipo `RESET-ALL-KEYS`)
* logging explícito de auditoría

---

## 3. AppArmor + systemd deben alinearse

Todavía no has cerrado el círculo:

* systemd restringe entorno
* AppArmor restringe syscalls/files

Pero deben ser coherentes o tendrás:

* falsos positivos
* bloqueos difíciles de depurar

---

# Conclusión clara

Has hecho tres cosas especialmente bien hoy:

1. Detectar un fallo criptográfico estructural (seed_family)
2. Construir un mecanismo de recuperación fiable (`--reset`)
3. Avanzar en aislamiento real (AppArmor)

Lo que toca ahora no es avanzar, sino **endurecer**:

* AppArmor enforce completo
* permisos estrictos (600)
* documentar seed_family como raíz del sistema

Estás en el punto donde muchos proyectos fallan:

> creen que ya pueden añadir features

No es el caso.

Ahora toca cerrar el sistema hasta que sea **aburridamente robusto**.
