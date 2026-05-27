```
REVISOR: External cs.CR Reviewer
FECHA: 2026-04-01

VEREDICTO GLOBAL ADR-023: ACCEPTED CON CONDICIONES
VEREDICTO GLOBAL ADR-024: DISEÑO CON RESERVAS
```

---

# HALLAZGOS CRÍTICOS (bloquean aceptación)

* **(ADR-023) Degradación elegante rompe el modelo de seguridad**

    * Permitir `plugin_process_message` ausente → payload raw introduce un estado donde:

      ```
      cifrado esperado ≠ cifrado aplicado
      ```
    * Esto viola explícitamente el principio **fail-closed** del sistema.
    * En un entorno real, esto es indistinguible de:

        * downgrade attack
        * misconfiguración silenciosa

---

* **(ADR-023) `channel_id` como `const char*` no autenticado**

    * El contexto criptográfico depende semánticamente de `channel_id`
    * Pero:

        * no está autenticado
        * no está ligado criptográficamente al payload
    * Riesgo:

      ```
      plugin malicioso o bug → cambia channel_id → desincronización lógica
      ```

---

* **(ADR-024) Reutilización de `seed_family` como PSK sin separación fuerte**

    * HKDF con `"noise-ik-psk"` es correcto en intención
    * Pero:

        * mismo root material (`seed_family`) se usa para:

            * HKDF canal (actual)
            * PSK Noise (nuevo)
    * Riesgo:

      ```
      key material reuse across protocols
      ```
    * Esto es un anti-pattern conocido si no se separa estrictamente

---

# HALLAZGOS RECOMENDADOS (no bloquean)

* `MessageContext.result_code` mezcla:

    * errores criptográficos
    * errores de buffer
      → separar o documentar claramente

* Falta flag explícito de:

  ```
  autenticación verificada (MAC OK)
  ```

* `reserved[8]` es correcto, pero:

    * deberías documentar layout esperado futuro (alignment/endianness)

* Retry strategy en ADR-024 es demasiado naive (5×2s)

    * no considera backoff ni particiones de red

---

# RESPUESTAS A PREGUNTAS ESPECÍFICAS

---

## Q1 — Superficie de ataque en MessageContext

Sí, hay 3 puntos relevantes:

### 1. `payload` mutable sin ownership claro

* ¿quién posee el buffer?
* riesgo:

  ```
  plugin modifica fuera de límites si max_length incorrecto
  ```

---

### 2. `channel_id` no autenticado (CRÍTICO)

* debería ser:

    * constante del host
    * no modificable por plugin
* idealmente:

  ```
  no pasar como puntero mutable
  ```

---

### 3. Falta estado de autenticación

Recomendado añadir:

```c
uint8_t authenticated; // 0/1
```

---

## Q2 — Degradación elegante

> ❌ Incorrecta para este sistema

Dado tu modelo:

```
fail-closed everywhere
```

👉 la única opción coherente es:

```
plugin requerido → ausencia = abort
```

---

### Alternativa segura

* permitir ausencia SOLO en:

    * modo explícito `DEV_MODE`
    * o flag de configuración fuerte

---

## Q3 — Orden de integración

Actual:

```
firewall → rag-ingester → rag-security
```

### Evaluación

* firewall → correcto (más simple, menos estado)
* rag-ingester → correcto
* rag-security → correcto como último

✔ Orden adecuado

---

## Q4 — Minoría Gemini (API v2 inmediata)

### Mi posición:

> ❌ No adoptar ahora

Pero:

> ✔ registrar como deuda explícita

---

### Argumento

* aún no tienes:

    * replay protection activa
    * necesidad real de timestamp

👉 prematuro

---

## Q5 — Noise pattern

> ✔ IKpsk3 es correcto **si controlas identidades**

---

### Pero hay matiz importante

IK requiere:

```
responder static key known beforehand
```

---

### Si tu sistema evoluciona a dinámico:

👉 mejor opción:

```
Noise_XXpsk3
```

---

### Recomendación

* FASE 1: IKpsk3 ✔
* FASE 3+: considerar XXpsk3

---

## Q6 — PSK derivado de seed_family

> ⚠️ Correcto pero incompleto

---

### Problema

Aunque usas:

```
HKDF(seed_family, "noise-ik-psk")
```

👉 falta separación fuerte de dominios

---

### Recomendación mínima

```text
HKDF(seed_family, info="ml-defender:noise:psk:v1")
```

y documentar:

```
NO reuse outside Noise
```

---

### Mejor aún (ideal)

Separar raíz:

```
seed_family
 ├─ HKDF → channel_keys
 └─ HKDF → noise_psk_root
```

---

## Q7 — noise-c

### Evaluación

✔ ligera
✔ C compatible
✔ razonable para embedded

---

### Riesgos

* menos auditada que libsodium
* mantenimiento externo

---

### Alternativas

* ❌ implementar tú → no
* ⚠️ libsodium (no tiene Noise completo)
* ✔ noise-c → aceptable

---

## Q8 — Open questions

Bien planteadas, pero falta una crítica:

---

### ❗ Falta añadir:

**5. Replay protection strategy**

* actualmente:

    * nonce monotónico local
    * pero no global ni validado cross-node

---

### ❗ También:

**6. Compromise recovery**

* si se filtra:

    * static key
    * seed_family
      → ¿cómo se rota?

---

## Q9 — Contradicciones ADR-023 vs ADR-024

Sí, hay una tensión conceptual:

---

### ADR-023

```
host controla crypto
plugins no acceden a claves
```

---

### ADR-024

```
introduces dynamic session keys
```

---

### Problema

¿Dónde vive el estado de sesión?

* no está definido claramente

---

### Riesgo

```
session lifecycle ambiguo
```

---

### Recomendación

Definir explícitamente:

```
SessionManager (host-owned)
```

---

## Q10 — Status ADR-024

> ❌ No debería ser solo "DISEÑO"

---

### Recomendación

```
STATUS: DESIGN FROZEN (PRE-IMPLEMENTATION)
```

---

### Por qué

* ya impacta decisiones actuales
* no es exploratorio, es estructural

---

# POSICIÓN DE MINORÍA (importante registrar)

* **Eliminar completamente degradación elegante**

    * incluso en DEV_MODE
    * forzar siempre cifrado
    * argumento: evitar estados duales del sistema

---

* **No usar PSK derivado de seed_family**

    * usar:

        * provisioning separado para Noise
    * argumento: separación total de dominios criptográficos

---

* **Adoptar Noise_XX desde el inicio**

    * evitar migración futura

---

# CONCLUSIÓN FINAL

```text
ADR-023 → correcto, pero debe endurecer su modelo de fallo
ADR-024 → bien encaminado, pero aún no completamente aislado criptográficamente
```

El mayor riesgo ahora mismo no es técnico profundo.

Es este:

```text
inconsistencias en el modelo de seguridad (fail-open vs fail-closed)
```

Si corriges eso, el diseño pasa de “muy bueno” a “difícil de romper”.
