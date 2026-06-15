Aironman DirtDiver, como **IA adversaria** y bajo el principio de **"medir, no votar"**, voy a desmontar cada frente con metodología científica, centrada en **falsabilidad**, **cobertura de casos críticos** y **honestidad en el claim**. Aquí va mi ataque sistemático, con propuestas accionables y sin concesiones.

---

---

## **Respuestas por Frente**

---

### **Frente 1: ¿Basta el golden de 27 vectores como red permanente?**
**Ataque:**
No. **27 vectores son insuficientes** para garantizar byte-identidad en un espacio de entrada infinito. El riesgo es real: un caso no cubierto (ej: un `float` con precisión extrema no probada, un `community_id` con caracteres Unicode no ASCII, o un `timestamp` en el límite de `int64_t`) podría diverger **silenciosamente** tras B4, cuando `build_row` desaparezca.

**Prueba de falsabilidad:**
- **Fuzzing determinista:** Generar **1M de structs aleatorios** (con `libFuzzer` o `AFL`) y comparar `serialize(to_row(event))` contra el golden **antes de B4**. Si hay divergencia, el golden es incompleto.
- **Oráculo alternativo:** Usar el `build_row` actual como oráculo **solo durante el fuzzing** (no en producción). Tras B4, el golden congelado será el único oráculo.
- **Criterio de parada:** Si el fuzzing no encuentra divergencias en 1M de casos, el golden se considera **suficiente para el claim actual** (pero no para "todos los casos posibles").

**Conclusión:**
**Exijo fuzzing contra `build_row` antes de B4.** Si no se hace, el claim debe incluir la salvedad:
*"Byte-identidad probada solo para los 27 vectores del golden y los casos cubiertos por fuzzing en [fecha]."*

---

### **Frente 2: Locale — ¿Inmunidad probada o asunción?**
**Ataque:**
**El riesgo es crítico y actual.** El `build_row` viejo **no fuerza `classic`**, por lo que:
1. Si el daemon en producción corre bajo `es_ES`, el bronce actual **ya está corrupto** (ej: `0.91` → `0,91`).
2. `serialize` fuerza `classic`, pero **no se ha verificado el locale de producción**. Si el daemon usa `es_ES`, el bronce viejo y el nuevo **divergirán** en campos numéricos.

**Prueba de falsabilidad:**
- **Matriz de locales:** Probar `serialize` bajo **todos los locales con coma decimal** (`es_ES`, `de_DE`, `fr_FR`, `it_IT`, `pt_BR`, `ar_SA`, `ja_JP` con `LC_NUMERIC` modificado).
- **Verificación en producción:** **Condición de merge:** Confirmar que el daemon en producción **ya usa `LC_ALL=C`** (o `classic`). Si no, el bronce viejo es inválido y el refactor **corrige un bug activo**.

**Conclusión:**
**Exijo:**
1. Matriz de locales como gate de merge.
2. **Condición de merge:** Verificación documentada del locale de producción (ej: `locale` en el `Dockerfile` o `systemd` service).
3. **Salvedad en el claim:** *"Inmunidad a locale probada para [lista de locales] en [fecha]. El bronce previo al refactor puede estar corrupto si el daemon usaba locale no-C."*

---

### **Frente 3: D-D diferido — ¿Legítimo o deuda técnica oculta?**
**Ataque:**
**Diferir D-D es legítimo**, pero **el DEBT debe ser bloqueante para el merge** si no tiene:
1. **Criterio de cierre claro:** Ej: *"El guard debe rechazar símbolos no definidos en el enum `DetectorSource` (lista cerrada en `protobuf`) antes del merge de `libcorrelation_v2`."*
2. **Plazo:** Ej: *"DEBT debe cerrarse en los próximos 3 commits o antes del 2026-07-01."*
3. **Prueba de regresión:** Un test que falle si D-D no se implementa (ej: un vector con enum desconocido que hoy pasa, pero que debe ser rechazado tras el DEBT).

**Conclusión:**
**Acepto diferir D-D**, pero **exijo:**
- DEBT explícito en el `README` de la lib con los 3 puntos arriba.
- **No merge sin DEBT documentado.**

---

### **Frente 4: `DEBT-BRONZE-EMBEDDED-NEWLINE-001` — ¿Bloqueante?**
**Ataque:**
**Sí, es bloqueante.** El formato CSV **no soporta newlines embebidos** sin escapado. Si `parse_and_verify` usa `getline`, **partirá el registro** y el HMAC fallará. Esto **rompe el contrato** (el HMAC debe validar la fila completa).

**Soluciones:**
1. **Escapar newlines:** Reemplazar `\n` por `\x0A` (o similar) en `serialize`.
2. **Cambiar el formato:** Usar JSON o Protobuf para el bronce (pero esto es un cambio de contrato mayor).
3. **Documentar la limitación:** Si se elige no actuar, el claim debe incluir: *"El contrato bronce no soporta newlines embebidos en campos string. Los productores deben garantizar que no ocurran."*

**Conclusión:**
**Bloqueante.** **Exijo:**
- O bien escapado de newlines en `serialize` (y actualización del golden).
- O bien **salvedad explícita en el claim** (y DEBT para solucionarlo en `v2`).

---

### **Frente 5: ¿El claim es honesto?**
**Ataque:**
El claim actual **sobre-concede**. Falta:
1. **Salvedad de cobertura:** *"Byte-identidad probada solo para los 27 vectores del golden y los casos cubiertos por [fuzzing/matriz de locales]."*
2. **Salvedad de locale:** *"Inmunidad a locale probada para [lista] bajo `imbue(classic)`. El bronce previo al refactor puede estar corrupto si el daemon usaba locale no-C."*
3. **Salvedad de newlines:** *"El contrato no soporta newlines embebidos (DEBT-BRONZE-EMBEDDED-NEWLINE-001)."*
4. **Salvedad de D-D:** *"El guard de enum desconocido (D-D) está diferido (DEBT con criterio [X])."*

**Claim reescrito (honesto):**
*"Refactor de la capa de serialización a una librería compartida (`libcorrelation_v1`), probado byte-idéntico contra un golden congelado de 27 vectores y contra el oráculo en vivo (`build_row`), bajo locale `classic`. La byte-identidad está acotada a los casos probados (golden + [fuzzing/matriz de locales]). El contrato no soporta newlines embebidos (DEBT-BRONZE-EMBEDDED-NEWLINE-001). El guard de enum desconocido (D-D) está diferido con criterio de cierre [X]. La lib no valida el locale de producción (debe ser responsabilidad del deployer)."*

---

---
---
## **Transversal: ¿Es seguro el plan de B4?**
**Ataque:**
**Sí, pero con riesgos controlables:**
1. **Riesgo de B4:** Tras el rewire, `write_record` usará `serialize`, por lo que **la comparación contra el golden es la única red que sobrevive**. Esto es correcto **solo si**:
    - El golden se capturó **antes de B4** (ya hecho).
    - El fuzzing (Frente 1) se ejecuta **antes de B4**.
    - El locale de producción se verifica **antes de B4** (Frente 2).
2. **Riesgo oculto:** Si el golden no cubre un caso crítico (ej: un `float` con precisión no probada), **B4 lo congelará como "correcto"** aunque diverja del `build_row` viejo.

**Conclusión:**
**El plan de B4 es seguro si:**
- Se ejecuta el fuzzing (Frente 1) y la matriz de locales (Frente 2) **antes de B4**.
- Se documentan las salvedades en el claim (Frente 5).

---

---
---
## **Resumen de Exigencias (Accionables)**
| Frente | Exigencia | Tipo |
|--------|-----------|------|
| **F1** | Fuzzing de 1M structs aleatorios contra `build_row` **antes de B4** | Gate de merge |
| **F2** | Matriz de locales + verificación de locale en producción | Gate de merge |
| **F3** | DEBT explícito con criterio de cierre y plazo | Gate de merge |
| **F4** | Escapado de newlines **o** salvedad en claim + DEBT | Bloqueante |
| **F5** | Claim reescrito con salvedades (cobertura, locale, newlines, D-D) | Requisito |
| **B4** | Ejecutar F1 y F2 antes de B4 | Requisito |

---
---
## **Pregunta Final para el Consejo**
**¿Aceptáis que el claim actual es deshonesto sin las salvedades propuestas, o consideráis que el riesgo de "etiquetar mal lo que se mide" justifica rechazar el merge hasta que se cierren F1, F2 y F4?**

*(Mi postura: **el merge puede proceder si se añaden las salvedades y se ejecutan F1/F2 antes de B4**, pero el claim actual es insostenible sin ellas.)*

FDO

MISTRAL