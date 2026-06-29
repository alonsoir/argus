El ADR está bien enfocado y, en esencia, listo para ir al Consejo. Lo que merece la pena es afinar dos cosas: (1) completar el threat model con un par de vectores que faltan y (2) endurecer ligeramente algunas mitigaciones “ahora en diseño” para que no queden como opcionales.

Voy directo a lo útil.

---

# Evaluación del threat model (ampliado y ordenado)

### **V1 — Compromiso de clave privada (CRÍTICO)**

Correcto y bien priorizado.

**Refinamiento importante:**
No basta con “no residir en el host”. Debe quedar explícito:

* Firma **solo en build pipeline offline**
* Host contiene **solo clave pública embebida o en config inmutable**
* Rotación de claves definida (aunque sea manual)

✔ Mitigable en diseño (obligatorio)

---

### **V2 — Escritura en `/usr/lib/ml-defender/plugins/`**

Correcto, pero incompleto.

**Falta una capa clave:**
Incluso sin clave privada, un atacante puede:

* Borrar `.so` o `.sig` → DoS
* Reemplazar `.sig` por basura → DoS silencioso

**Mitigación realista:**

* Permisos root-only + immutable flag (`chattr +i`) en producción
* Directorio **no writable** por el daemon

✔ Mitigable parcialmente ahora
✔ Hardening Debian refuerza

---

### **V3 — Supply chain / provision.sh comprometido**

Correcto.

Añadir explícitamente:

* Hash reproducible del `.so` antes de firma
* Logging de firma (audit trail)

✔ Diferible (documentar en ADR)

---

### **V4 — Path traversal / config poisoning**

Correcto, pero aquí hay un matiz crítico.

**Problema:**
`canonical()` no es suficiente si se hace después de abrir.

**Mitigación robusta:**

* Validar path **antes de open()**
* Verificar que:

    * Es absoluto
    * Prefijo exacto permitido
* Opcional fuerte:

    * Abrir con `openat(dirfd, ...)` sobre directorio ya validado

✔ Mitigable en diseño (recomendado endurecer)

---

### **V5 — FD reuse / lifecycle bug**

Correcto pero poco probable si se implementa bien.

**Clave:**

* No cerrar fd
* No duplicar fd innecesariamente
* Pasar directamente `/proc/self/fd/N` sin reabrir

✔ Mitigable en diseño

---

### **V6 — LD_PRELOAD / entorno**

Correcto, pero se puede hacer más determinista.

**Mitigación clara:**
En el launcher del daemon:

```bash
unset LD_PRELOAD
unset LD_LIBRARY_PATH
```

Y opcional:

* `secure_getenv()` en lugar de `getenv()`

✔ Mitigable en diseño (muy barato)

---

### **V7 — libsodium comprometida**

Correcto.

Añadir:

* Verificación de hash de libs en build
* O confiar en sistema + IMA

✔ Diferible (hardening Debian)

---

### **V8 — Plugin firmado pero malicioso**

Correcto y muy importante.

**Aquí hay una decisión arquitectónica:**

Ahora:

* D8 (integridad de contexto)

Futuro recomendable:

* Aislamiento por proceso (fork + seccomp)
* O al menos:

    * watchdog de tiempo
    * límites de CPU/memoria

✔ Parcialmente mitigable ahora
✔ Evolución clara PHASE 3+

---

# Vectores que faltaban (importantes)

### **V9 — Symlink attack**

Un clásico que aquí aplica directamente.

Ejemplo:

```
libplugin.so → symlink → /tmp/malicious.so
```

**Mitigación:**

* `open(..., O_NOFOLLOW)`
* Verificar `fstat()` → tipo regular file

✔ Mitigable en diseño (añadir explícitamente)

---

### **V10 — TOCTOU en el `.sig`**

Has protegido el `.so`, pero:

* `.sig` se abre por path independiente

**Ataque:**
Cambiar `.sig` entre lectura y verificación

**Mitigación:**

* Mismo patrón que `.so`:

    * `open()` → fd
    * leer desde fd
    * no volver a path

✔ Mitigable en diseño

---

### **V11 — Mixed signing (confusión de claves)**

Si en el futuro hay múltiples componentes firmando:

**Ataque:**

* Plugin firmado por clave válida pero **no autorizada para ese host**

**Mitigación:**

* Asociar clave pública a componente explícito
* (ej: firewall solo acepta clave X)

✔ Mitigable en diseño (importante para escalar)

---

# Evaluación del diseño ADR-025

El diseño es **sólido y correcto**. Pero para que sea realmente robusto, propondría elevar estos puntos a **decisiones explícitas (no implícitas)**:

### Añadir al ADR:

**D12 — Path safety**

* Validación de prefijo
* `O_NOFOLLOW`
* `fstat()` regular file

**D13 — FD-only discipline**

* `.so` y `.sig` verificados y cargados solo desde fd

**D14 — Key model**

* Firma offline obligatoria
* Clave pública única por componente

**D15 — Environment sanitization**

* Limpieza explícita de `LD_*`

---

# Respuesta directa a tu pregunta

Sí, puedes mandar esto al Consejo tal cual, pero **con estos ajustes**:

### Añadir:

* Symlink attack (V9)
* TOCTOU en `.sig` (V10)
* Confusión de claves (V11)

### Endurecer:

* Path validation (antes de open)
* Uso de `O_NOFOLLOW`
* FD también para `.sig`
* Modelo de claves explícito

---

# Veredicto del Consejo (anticipado)

Si lo mandas así refinado, lo esperable sería:

* Aprobación del enfoque criptográfico
* Recomendación de endurecer filesystem + fd discipline
* Posible sugerencia futura de aislamiento de plugins

---

Si quieres, en el siguiente paso puedo devolverte el ADR-025 ya reescrito con estas mejoras integradas, listo para commit directo.
