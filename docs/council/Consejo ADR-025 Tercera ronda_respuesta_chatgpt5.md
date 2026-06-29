Después de presentar el borrador final del ADR-025, el consejo da una tercera ronda.


El ADR-025 está en un nivel muy alto. Se nota que ya no es un diseño teórico, sino uno que ha pasado por threat modeling serio y decisiones incómodas bien resueltas.

Mi evaluación es clara: **esto es production-grade**. Aun así, te dejo observaciones finas para llevarlo de “muy sólido” a “difícil de romper incluso por equipos rojos buenos”.

---

# Veredicto global

* **Seguridad:** Muy alta (correctamente priorizada sobre operatividad)
* **Coherencia interna:** Excelente
* **Cobertura de vectores:** Prácticamente completa
* **Decisiones difíciles (D7, D9, D11):** Bien tomadas

No hay errores conceptuales. Solo ajustes de precisión y un par de endurecimientos opcionales.

---

# Observaciones críticas (pequeñas pero importantes)

## 1. Orden en D4 (detalle técnico sutil)

Actualmente:

```
fd = open(...)
fstat(fd)
prefix_check(so_path)
```

Esto introduce una pequeña incoherencia conceptual:

* Estás validando el path **después** de abrir

### Recomendación

Invertir:

```
prefix_check(so_path)
fd = open(...)
fstat(fd)
```

**Por qué:**

* El prefix check es política (input validation)
* El open es operación privilegiada

Esto no rompe seguridad ahora mismo, pero mejora la claridad del modelo mental.

---

## 2. `weakly_canonical()` puede ocultar fallos

En D3 usas:

```cpp
weakly_canonical()
```

Problema:

* Puede resolver paths parcialmente inexistentes
* Puede dar sensación de seguridad falsa

### Recomendación

Usar:

```cpp
canonical()
```

y si falla → rechazar

✔ Más estricto
✔ Menos ambigüedad

---

## 3. Validación de tamaño del `.so` (falta explícita)

En V10 mencionas truncamiento, pero no hay regla explícita.

### Añadir en D2 o D4:

```cpp
if (st.st_size <= 0 || st.st_size > MAX_PLUGIN_SIZE) {
    reject;
}
```

Define `MAX_PLUGIN_SIZE` (ej: 50MB o lo que tenga sentido)

✔ Mitiga:

* truncamientos
* archivos maliciosos gigantes (DoS)

---

## 4. `/proc/self/fd/N` — matiz importante

Esto es correcto, pero hay un edge case:

* Algunos loaders pueden re-evaluar rutas internas o dependencias

### Mejora opcional (no bloqueante):

Documentar:

> “Se asume que el loader dinámico respeta el fd abierto y no reevalúa el path original”

Y dejar `memfd_create()` como evolución real (bien puesto en alternativas).

---

## 5. D9 — `std::terminate()` (decisión fuerte)

Esto está muy bien, pero tiene implicación operativa:

* Un plugin corrupto → tumba el servicio completo

### Mi recomendación (no obligatoria):

Mantener como está, pero añadir:

> “Los componentes deben estar supervisados por systemd (Restart=always)”

Para evitar:

* caída permanente por error puntual

---

## 6. D11 — rotación: excelente, pero falta un detalle

Has definido muy bien el proceso, pero falta una verificación en runtime:

### Añadir explícitamente:

> “El plugin-loader debe rechazar cualquier firma generada con una clave distinta a la embebida, sin excepción”

Aunque implícito en Ed25519, esto conviene declararlo como **garantía contractual**.

---

## 7. D12 — `allowed_key_id` (muy buena decisión)

Esto es de lo mejor del ADR.

Sugerencia mínima:

* Define ya el formato aunque no se use:

Ejemplo:

```json
"allowed_key_id": "ed25519:2026-04-prod"
```

✔ Evita decisiones futuras inconsistentes
✔ Facilita auditoría

---

# Observaciones no críticas (pero elegantes)

## Logging forense (D6)

Muy buena idea. Si quieres elevarlo más:

* Loggear también:

  * tamaño del fichero
  * timestamp de modificación (`st_mtime`)

Esto ayuda mucho en análisis post-incidente.

---

## Falco rule (muy bien pensada)

Solo añadiría:

```yaml
and not proc.name in ("provision.sh", "dpkg", "apt")
```

Para evitar ruido en updates legítimos.

---

# Lo mejor del ADR (lo destacable de verdad)

Esto merece decirse claramente:

### 1. FD discipline + O_NOFOLLOW

Esto elimina una clase entera de ataques reales que muchos sistemas no cubren.

### 2. Clave hardcoded (D7)

Decisión madura. Evita el error típico de “todo configurable = todo vulnerable”.

### 3. Rotación sin cron

Esto es ingeniería seria. Evita automatizar algo que no debe automatizarse.

### 4. Fail-closed real (no cosmético)

Muchos sistemas dicen fail-closed y luego no lo son. Aquí sí lo es.

---

# Conclusión final

El ADR-025 está:

* Correcto conceptualmente
* Bien defendido frente a ataques realistas
* Coherente con el resto del sistema

Con los pequeños ajustes indicados, pasa a ser:

> **Un diseño robusto incluso frente a atacantes con buen conocimiento del sistema**

---

Si quieres, el siguiente paso lógico sería:

* revisar el código de implementación línea por línea (plugin_loader.cpp)
* ahí sí pueden aparecer errores sutiles (orden, flags, errores de retorno, etc.)

Y es justo donde estos diseños suelen romperse.
