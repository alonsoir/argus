El ADR está bien planteado y, sobre todo, **llega en el momento correcto**: acabas de cerrar integridad local (ADR-025) y ahora estás abordando la **cadena de confianza completa**. Eso es exactamente la evolución natural.

Dicho esto, voy directo a lo importante: hay varias decisiones muy buenas, pero también hay **3 puntos críticos que, si no los ajustas ahora, te van a limitar más adelante**.

---

# Evaluación general

✔ Dirección correcta (separación de dominios de confianza)
✔ Modelo mental sólido (supply chain, no solo verificación)
✔ Implementable con coste realista
⚠ Riesgos en: **vendor lock, revocación, y modelo de identidad**

---

# Lo más fuerte del ADR (bien hecho)

### 1. Separación de autoridad (clave fuera del host)

Esto es lo más importante del documento.

Has pasado de:

> “integridad local”

a:

> “supply chain verificable”

Ese salto es el que diferencia un sistema serio de uno académico.

---

### 2. Fail-closed coherente con el modelo

Mantienes consistencia con ADR-025:

* sin firma → no carga
* sin vendor → no hay código

No hay contradicciones. Bien.

---

### 3. Manifest con semántica (no solo firma)

Esto es clave:

* `customer_id`
* `expires_at`
* `scope`

Estás pasando de **integridad → política de ejecución**, que es exactamente lo correcto.

---

# Problemas importantes (a corregir)

## 1. ❗ Riesgo de “vendor single point of failure”

Ahora mismo:

> Solo existe **una clave global vendor**

### Problema real

* Si pierdes la YubiKey → no puedes firmar nada
* Si la comprometen → todo el ecosistema queda comprometido
* Si el proyecto crece → no escala (equipo, contributors, etc.)

---

## Recomendación clara

Introduce **key hierarchy desde el inicio**

### Modelo mínimo:

```text
Root Key (offline, muy protegida)
   ↓
Signing Keys (rotables, YubiKey)
   ↓
Plugins
```

---

### Cambios concretos en el ADR

Añadir:

```json
"key_id": "argus-signing-2026-q2",
"issuer": "argus-root-v1"
```

Y en el loader:

* aceptar múltiples claves públicas
* permitir rotación sin recompilar binario

---

## Conclusión

✔ No uses una única clave hardcodeada a largo plazo
⚠ Añade soporte multi-key desde ya (aunque uses una sola al principio)

---

## 2. ❗ Problema de revocación (el mayor agujero ahora mismo)

Ahora mismo preguntas:

> ¿lista de revocación local o etcd?

La realidad:

👉 **Sin revocación, el sistema está incompleto**

---

### Escenario real

* firmas plugin v1
* descubres vulnerabilidad
* el cliente lo tiene instalado

→ **no puedes hacer nada**

---

## Recomendación fuerte

Define desde ya:

### Opción mínima viable

```json
revocation_list.json (firmada por vendor)

{
  "revoked_plugins": [
    {
      "sha256": "...",
      "reason": "CVE-2026-XXXX",
      "revoked_at": "..."
    }
  ]
}
```

Loader:

* carga lista en arranque
* si hash está → rechaza

---

### Opción mejor (futuro)

* distribución vía:

    * HTTPS pull
    * o etcd (como ya usas)
* cache local + firma obligatoria

---

## Conclusión

⚠ Esto no es opcional
✔ Añádelo como parte del ADR (no como pregunta abierta)

---

## 3. ❗ customer_id binding (más complejo de lo que parece)

Tu pregunta:

> ¿cómo evitar que un cliente copie plugin?

Respuesta corta:
👉 **No puedes evitarlo completamente sin infraestructura**

---

### Problema

El cliente controla:

* filesystem
* binario
* entorno

Puede:

* parchear loader
* copiar plugin + manifest
* falsificar `customer_id`

---

## Recomendación pragmática

Define claramente:

> `customer_id` = control lógico, no criptográfico fuerte

Y opcionalmente:

### Nivel 2 (si quieres endurecerlo)

* binding a:

    * machine-id
    * TPM (si disponible)
    * o certificado local

---

## Conclusión

✔ Mantén `customer_id`
⚠ No lo vendas como seguridad fuerte
✔ Documenta limitación explícitamente

---

# Respuestas a tus preguntas

## Q1 — YubiKey PIV vs alternativas

### Veredicto

✔ YubiKey correcto
❗ Pero no uses PIV si puedes evitarlo

---

### Mejor opción

* **Ed25519 puro (libsodium / age / minisign style)**
* o **OpenPGP en YubiKey**

---

### Evitar

* PIV → más complejo, menos natural para este caso
* TPM → no portable (cliente)
* FIDO2 → no pensado para signing arbitrario

---

## Recomendación

👉 Usa YubiKey + Ed25519 (no PIV si puedes)

---

## Q2 — manifest separado o embebido

### Veredicto claro

👉 **Embebido dentro de la firma**

---

### Por qué

Evita:

* desincronización `.sig` / `.manifest`
* manipulación del manifest

---

### Formato recomendado

```json
.sig = firma( JSON {
  metadata + hash
})
```

---

## Q3 — customer_id viable

✔ Sí, como control lógico
❗ No como seguridad fuerte

---

## Q4 — revocación

👉 Obligatorio implementar
Recomendación: lista firmada distribuida

---

## Q5 — TPM measured boot

### Veredicto

✔ Interesante
❗ Pero fuera de este ADR

---

👉 Hazlo como:

**ADR separado (ej: ADR-033)**

---

# Mejora estructural del ADR

Te recomiendo añadir una sección nueva:

## “Security Model Clarifications”

```text
- customer_id is not a strong anti-copy mechanism
- revocation is required for real-world operation
- multiple signing keys must be supported
```

Esto sube mucho el nivel del documento.

---

# Conclusión final

Este ADR es:

✔ Correcto en dirección
✔ Realista en coste
✔ Muy alineado con tu filosofía (“la verdad por delante”)

Pero para que sea **de nivel producción serio**, necesitas:

### Obligatorio antes de implementar

1. Soporte multi-key (aunque uses una)
2. Mecanismo de revocación definido
3. Clarificación de límites de `customer_id`

---

# Insight final

Estás pasando de:

> “seguridad del sistema”

a:

> **“seguridad de la cadena de suministro”**

Ese es el salto que separa proyectos técnicos buenos de sistemas que pueden vivir en producción real.

Si cierras bien este ADR, estás construyendo algo que ya entra en conversaciones de **ingeniería de plataforma, no solo NDR**.
