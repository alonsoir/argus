## Consejo de Sabios — Respuestas DAY 134 (EMECAS hardened)

Evaluación centrada en: **reproducibilidad fuerte, seguridad operativa y tiempo de iteración razonable**.

---

# Q1 — Atomicidad de `make hardened-full`

### Veredicto: 🟢 **Fail-fast + cache explícita (no checkpoints implícitos)**

Ni fail-fast puro ni checkpoints tradicionales. La solución correcta es:

### ✔ Modelo recomendado

* **Fail-fast obligatorio**
* **Separación build vs deploy**
* **Cache de artefactos (dist/)**

---

### Arquitectura propuesta

```bash
make hardened-full:
    hardened-destroy
    hardened-up
    hardened-provision-all
    prod-deploy-from-dist
    check-prod-all
```

Y separar:

```bash
make prod-build-x86   # lento (cacheable)
make prod-deploy-x86  # rápido
```

---

### Justificación

* Fail-fast:

    * garantiza reproducibilidad total (EMECAS real)
* Cache:

    * evita recompilar innecesariamente

---

### Riesgo si usas checkpoints

* estado intermedio inconsistente
* errores no reproducibles

---

### Test reproducible

```bash
make prod-build-x86
make hardened-full   # no recompila
```

---

# Q2 — Semillas en hardened VM

### Veredicto: 🔴 **NO transferir seeds desde dev VM**

---

### Modelo correcto

| Entorno     | Seeds                     |
| ----------- | ------------------------- |
| dev VM      | sí                        |
| hardened VM | ❌ NO (hasta runtime real) |

---

### Justificación

* transferencia rompe:

    * aislamiento
    * modelo de amenaza

* seeds son:

    * **material criptográfico sensible**

---

### Alternativa correcta

* generar seeds:

    * **en runtime (primer arranque)**
* o:

    * inyectar desde sistema seguro externo (futuro)

---

### Estado actual (`WARN seed.bin no existe`)

✔ **Correcto por diseño**

---

### Riesgo si los copias

* exposición en shared folder
* reproducibilidad contaminada

---

# Q3 — Idempotencia

### Veredicto: 🟢 **NO idempotente — siempre reconstrucción completa**

---

### Regla

EMECAS implica:

```bash
vagrant destroy -f
```

Siempre.

---

### Justificación

* elimina:

    * drift
    * estado oculto

---

### Excepción permitida (solo desarrollo rápido)

```bash
make hardened-redeploy
```

Pero:

* **no forma parte de EMECAS**

---

### Riesgo si haces idempotente

* falsos verdes
* bugs no reproducibles

---

# Q4 — Falco .deb

### Veredicto: 🟡 **NO commitear binarios — usar artefacto versionado externo**

---

### Opciones evaluadas

| Opción                              | Veredicto                   |
| ----------------------------------- | --------------------------- |
| Git repo                            | ❌                           |
| Git LFS                             | ❌                           |
| Descarga en provision               | ⚠️ (rompe reproducibilidad) |
| dist/ local                         | 🟡                          |
| **Artefacto versionado + checksum** | 🟢                          |

---

### Recomendación

```bash
dist/artifacts/
  falco_0.43.1_amd64.deb
  SHA256SUMS
```

* ignorado por git
* documentado en EMECAS
* verificado con hash

---

### Alternativa ideal (post-FEDER)

* mirror propio
* o release fijado en CI

---

### Riesgo actual

* descarga externa → no determinista

---

# Q5 — `confidence_score` prerequisito ADR-040

### Veredicto: 🔴 **OBLIGATORIO verificar con doble método**

---

### Método correcto

#### 1. Test de integración (principal)

Capturar salida real:

```bash
zmq_subscriber → parse JSON → assert field exists
```

---

#### 2. Inspección de código (secundario)

* verificar:

    * dónde se calcula
    * rango esperado

---

### Por qué ambos

| Método       | Problema                 |
| ------------ | ------------------------ |
| Solo código  | puede no ejecutarse      |
| Solo runtime | no sabes cómo se calcula |

---

### Test reproducible

```bash
make test-ml-detector-output

assert "confidence_score" in event
assert 0.0 <= value <= 1.0
```

---

### Mejora crítica

Formalizar contrato:

```json
{
  "prediction": "attack|benign",
  "confidence_score": float,
  "model_version": "hash"
}
```

---

### Riesgo si no lo haces

* IPW mal implementado
* sesgo acumulativo

---

# Evaluación global DAY 134

### Estado del sistema

| Área              | Estado           |
| ----------------- | ---------------- |
| Pipeline hardened | 🟢 sólido        |
| Seguridad         | 🟢 avanzada      |
| Reproducibilidad  | 🟢 alta          |
| Arquitectura ML   | 🟢 bien dirigida |

---

### Riesgos restantes

1. gestión de artefactos (Falco, dist/)
2. separación build/deploy aún no completamente formalizada
3. contrato de salida ML no fijado completamente

---

# Directiva del Consejo para DAY 135

1. Implementar `hardened-full`:

    * fail-fast
    * sin checkpoints
2. Separar build vs deploy claramente
3. No introducir seeds en hardened
4. Añadir verificación SHA256 a artefactos externos
5. Crear test de integración para `confidence_score`

---

# Veredicto final

El sistema ha pasado de:

* “pipeline funcional”

a

* **pipeline reproducible, auditable y cercano a producción real**

El siguiente salto (DAY 135) no es técnico, es disciplinario:

**convertir todo en un único procedimiento determinista que siempre funcione o siempre falle.**
