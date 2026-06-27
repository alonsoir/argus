Evaluación directa, centrada en operabilidad real y superficie de fallo.

---

## Q1 — AppArmor: complain vs enforce

**Veredicto:** **Complain → Enforce (obligatorio, sin atajos)**

**Justificación:**
El sniffer y firewall usan capabilities sensibles (`CAP_BPF`, `CAP_SYS_ADMIN`, `CAP_NET_ADMIN`). Un perfil mal ajustado rompe silenciosamente el pipeline. Complain permite observar syscalls reales y cerrar perfiles sin degradar servicio.

**Riesgo si se ignora:**
Pipeline inestable o parcialmente ciego (peor que caído: falsa sensación de seguridad).

---

## Q2 — `provision.sh --reset` (rotación + plugins)

**Veredicto:** **Proceso en dos fases (manual controlado)**

**Justificación:**

* Fase 1: rotación de claves (sin firma automática)
* Fase 2: firma explícita offline (o entorno controlado)
  Esto respeta el modelo de **no firma en producción** (alineado con ADR-032).

**Riesgo si se ignora:**
Reintroduces exactamente el problema que ADR-032 intenta eliminar (clave activa en host).

---

## Q3 — Orden AppArmor vs `--reset`

**Veredicto:** **AppArmor primero (al menos baseline funcional)**

**Justificación:**
`--reset` toca rutas críticas (`/etc`, plugins, claves). Si AppArmor entra después, puedes romper operaciones de recuperación. Necesitas perfiles que contemplen explícitamente provisioning/rotación.

**Riesgo si se ignora:**
Lock-out operativo: sistema seguro pero irrecuperable sin intervención manual.

---

## Q4 — TEST-PROVISION-1: cobertura

**Veredicto:** **Añadir 3 checks críticos**

**Justificación:**

1. **Hash/integridad de binarios (mínimo SHA-256)**

   * Detecta tampering post-build

2. **Permisos y ownership de rutas críticas**

   * `/usr/lib/ml-defender/plugins/` (root:root, no writable)
   * `/etc/ml-defender/` (sin world-write)

3. **Verificación de AppArmor activo (cuando aplique)**

   * `aa-status` → perfiles cargados/enforce esperado

**Riesgo si se ignora:**
Vector local trivial: modificar binarios o plugins sin romper checks actuales.

---

# Observaciones clave (fuera de Q1–Q4)

### 1. Has cerrado un riesgo serio sin darte cuenta del todo

> 4 componentes con `active:true` en hello plugin

Esto es exactamente el tipo de fallo que en producción se convierte en RCE trivial. La introducción de `validate-prod-configs` es una decisión muy correcta. Mantenerlo como gate obligatorio.

---

### 2. TEST-PROVISION-1 está empezando a ser tu “root of truth”

Lo correcto ahora es:

* Todo lo que rompa seguridad → debe fallar ahí
* Nada debe arrancar fuera de ese gate

Estás en el punto donde ese test se convierte en más importante que muchos tests unitarios.

---

### 3. systemd hardening (siguiente iteración recomendada)

No está en preguntas, pero es el siguiente salto lógico:

Añadir progresivamente:

* `NoNewPrivileges=yes`
* `PrivateTmp=yes`
* `ProtectSystem=strict`
* `ProtectHome=yes`

Especial cuidado con sniffer/firewall → necesitarán excepciones.

---

### 4. Estado global

Lo relevante aquí no es que funcione — eso ya lo hace.

Lo relevante es que:

* Estás cerrando vectores reales (firma, paths, dev plugins)
* Estás separando correctamente provisioning vs producción
* Estás empezando a construir una cadena de confianza coherente

Los riesgos que quedan ya no son de diseño, sino de:

* operación (AppArmor mal perfilado)
* gestión de secretos (seed_family)
* disciplina de despliegue

Eso es exactamente donde debería estar el proyecto en DAY 115.

---

## Conclusión

* Q1: nunca saltarse complain
* Q2: rotación ≠ firma (separación estricta)
* Q3: AppArmor antes de tocar claves
* Q4: añadir integridad binaria + permisos + estado AppArmor

El pipeline ya no necesita más features urgentes; necesita **cerrar completamente la superficie operativa** antes de escalar complejidad.
