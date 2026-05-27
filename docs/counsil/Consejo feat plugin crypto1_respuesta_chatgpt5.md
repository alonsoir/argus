Decisión arquitectónica clara: estás en un punto donde elegir “lo fácil ahora” penaliza todo lo que viene después.

---

# 🧠 Q1 — Opción A vs Opción B

## 🎯 Recomendación firme

> **Elegir Opción A (MessageContext).**
> Y no como “una opción más limpia”, sino como **la única correcta a medio plazo**.

---

## 🔍 Por qué Opción B es un error (aunque funcione)

Ampliar `PacketContext` introduce un problema estructural:

```text
Mezcla de capas → acoplamiento → pérdida de modelo mental
```

---

### ❌ Consecuencias reales

1. **Rompes la abstracción de plugins**

  * plugins dejan de ser “por dominio”
  * pasan a ser “if (campo != NULL) entonces…”

---

2. **Testing degradado**

  * no puedes testear transporte aislado sin simular red
  * introduces ruido en todos los tests

---

3. **Escalabilidad futura bloqueada**

Cuando metas:

* Noise protocol
* PQC (post-quantum)
* compresión alternativa

👉 `PacketContext` se convierte en un “struct monstruo”

---

4. **Violas tu propia arquitectura**

Tu sistema ya separa:

```text
red ≠ transporte ≠ aplicación
```

Opción B rompe eso.

---

## ✔ Qué representa realmente Opción A

No es solo “otro struct”.

Es esto:

```text
Plugin system → multi-layer aware
```

---

## 💡 Insight clave

Has pasado de:

```text
plugins de red
```

a

```text
plugins de pipeline
```

👉 necesitas **hooks por capa**, no un contexto único.

---

## ✔ Conclusión Q1

> ✔ Opción A correcta
> ❌ Opción B deuda estructural seria
> 💡 Estás diseñando una arquitectura extensible real, no un parche

---

# 🧠 Q2 — Gestión del breaking change

## 🎯 Recomendación

> **NO hagas breaking change obligatorio todavía.**

---

## ✔ Estrategia correcta

### `plugin_process_message` → **OPCIONAL**

---

## 🔧 Loader behavior

```c
void* sym = dlsym(handle, "plugin_process_message");

if (sym != NULL) {
    // registrar como plugin de transporte
} else {
    // plugin solo de red
}
```

---

## ✔ Ventajas

* no rompes plugins existentes
* migración progresiva
* reduces fricción

---

## ❌ Cuándo hacer obligatorio

Más adelante (PHASE 3 o 4):

* cuando tengas ≥2 plugins reales de transporte
* cuando el ecosistema lo requiera

---

## ✔ `PLUGIN_API_VERSION`

> ❌ NO subir aún

Mantén:

```text
PLUGIN_API_VERSION = 1
```

y documenta:

```text
plugin_process_message is optional extension
```

---

## 💡 Patrón conocido

Esto es equivalente a:

```text
“capability-based plugins”
```

El plugin declara lo que sabe hacer por símbolos exportados.

---

## ✔ Conclusión Q2

> ✔ Hook opcional
> ✔ Sin bump de versión
> ✔ Loader dinámico por capacidades

---

# 🧠 Q3 — Estrategia dual-mechanism

## ✔ Evaluación

Tu estrategia es **correcta y madura**.

Pero necesita un ajuste importante.

---

## 🔧 Ajuste crítico

Añadir una fase explícita de **comparación determinista**

---

## ✔ Versión refinada

### PHASE 2a — paralelo + equivalencia

```text
CryptoTransport (core)
CryptoPlugin (plugin)

TEST-INTEG-4:
core_encrypt(x) == plugin_encrypt(x)
core_decrypt(x) == plugin_decrypt(x)
```

👉 no solo “funciona”, sino **es idéntico**

---

### PHASE 2b — shadow mode

```text
plugin activo
core sigue ejecutándose en paralelo (no usado)
comparación silenciosa
```

👉 detectas divergencias reales

---

### PHASE 2c — switch

```text
core desactivado
plugin único camino
```

---

### PHASE 2d — eliminación

```text
borrar CryptoTransport del core
```

---

## ❗ Riesgo que faltaba

Sin comparación explícita puedes tener:

```text
ambos funcionan
pero no son equivalentes
```

---

## ✔ Conclusión Q3

> ✔ Estrategia correcta
> 🔧 Añadir fase de equivalencia estricta

---

# 🔐 Pregunta implícita — Fail-closed en plugin crypto

## 🎯 Respuesta clara

> **Debe seguir siendo FAIL-CLOSED.**

---

## ✔ Comportamiento esperado

Si el plugin falla:

```text
→ abortar proceso
→ nunca enviar plaintext
```

---

## ❌ Lo que NO puedes permitir

```text
if (crypto fails) → send unencrypted
```

👉 eso rompe todo el modelo de amenaza

---

## ✔ Alineado con ADR-022

* coherente con tu diseño actual
* coherente con hospitales / entornos sensibles

---

# 🧠 Sobre ADR-012 (plugins no bloqueantes)

Tu interpretación es correcta:

> ✔ El plugin crypto **no decide**, solo transforma

---

## ✔ Distinción clave

```text
Firewall plugin → decisión (bloquear)
Crypto plugin → transformación (cifrar)
```

👉 no hay conflicto con ADR-012

---

# 🔥 Insight arquitectónico importante

Lo que estás diseñando ya no es:

```text
un sistema con plugins
```

Es
