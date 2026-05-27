**CONSEJO DE SABIOS — VEREDICTO DAY 140**

Excelentísimos artífices del pipeline. Habéis alcanzado un hito que pocos proyectos rozan: **0 warnings con `-Werror` activo en un sistema C++20 de alto rendimiento**. No se trata de un logro estético, sino de una vacuna permanente contra regresiones sutiles. Os recibimos con el respeto que merece una sesión de 9 horas de cirugía de compilador.

Abordamos vuestras cinco preguntas con la precisión que exigís.

---

### **Q1 — `-Werror` frente a APIs deprecadas en código de terceros**

La supresión selectiva mediante `-Wno-deprecated-declarations` para `llama_integration_real.cpp` es **correcta como parche inmediato**, pero no puede convertirse en política de estado. El criterio del Consejo es tripartito:

1. **Código de terceros que *nosotros* no mantenemos** (librería externa, no fork):  
   Si la librería avisa de deprecación y la nueva API es estable, **actualizamos de inmediato**. Cada release de llama.cpp es una oportunidad para eliminar el `#pragma`. Mantener la supresión indefinidamente acumula deuda de compatibilidad y nos expone a que la API vieja desaparezca sin aviso.

2. **Código generado o incluido vía `add_subdirectory` sin control directo** (protobuf, XGBoost trees):  
   La supresión por fichero es la herramienta correcta (véase Q5).

3. **Stubs propios o interfaces virtuales**:  
   No debe usarse supresión de deprecación; se actualiza el código (véase Q3).

**Recomendación para `llama.cpp`**: Dado que ya habéis identificado el cambio (`llama_new_context_with_model` → `llama_init_from_model`), abrid una tarea para actualizar la llamada. La supresión actual se mantiene solo si la actualización no puede hacerse antes del merge. Colocad un comentario `// TODO(DAY-140): Migrar a llama_init_from_model cuando se estabilice` y un issue asociado.

---

### **Q2 — Alcance de la verificación ODR**

El gap entre el build diario (`debug`, sin LTO) y la verificación ODR (`production` con LTO) **no es aceptable para infraestructura crítica**. La Violación de la Regla de Una Definición (ODR) es un error de ligado que puede manifestarse como corrupción de memoria, comportamiento incorrecto en `typeid`, o fallos de seguridad. Si el build diario no lo detecta, estáis entregando código potencialmente roto a QA y a vosotros mismos.

**La solución no es compleja**: añadid un **CI gate periódico** (sugerimos semanal, o idealmente pre-merge si el tiempo de build lo permite) que compile con `PROFILE=production` y `-Werror`, y ejecute al menos un smoke test. Esto garantiza que el pipeline de producción (y por tanto la detección ODR) no se rompa.

Mientras tanto, una medida complementaria inmediata: añadir un target `make check-odr` que compile con `-flto -Wodr` (o el equivalente de vuestro compilador) y que se ejecute manualmente antes de cada merge a `main`. No es obstáculo para el flujo diario, pero crea disciplina.

**Veredicto**: El gap debe cerrarse. Priorizad un job semanal en CI que haga `make PROFILE=production all test-all`. A medio plazo, extended esto a la verificación pre-merge.

---

### **Q3 — `/*param*/` vs `[[maybe_unused]]` en C++20**

La política correcta, especialmente con `-Werror` activo, es **usar `[[maybe_unused]]` en la declaración**. No solo es semánticamente más rico (comunica la intención al compilador y al desarrollador), sino que **no interfiere con la optimización** y es resistente a refactorizaciones.

El comentario `/*param*/` es un artefacto de C heredado que silencia el aviso pero no informa al compilador. En C++20, `[[maybe_unused]]`:
- Elimina la advertencia de forma portátil y estándar.
- No impide que el parámetro se use en futuras implementaciones.
- Cuando finalmente se implemente la interfaz virtual, podéis eliminar el atributo sin riesgo de olvido.

**Para interfaces virtuales**: el atributo es ideal. La interfaz declara que el parámetro *puede* no usarse en algunas implementaciones, lo cual es una decisión de diseño explícita. Si una implementación futura lo usa, simplemente no lo marca. No hay conflicto.

**Recomendación**: Sustituid todos los `/*param*/` en cabeceras y definiciones por `[[maybe_unused]]` (requiere C++17; en C++20 es totalmente aceptado). Hacedlo sistemáticamente, es una mejora de calidad de código que refuerza el invariante `-Werror`.

---

### **Q4 — Gap de hardware FEDER: alternativas técnicas**

El benchmark empírico de capacidad es un deliverable contractual. Sin hardware real, la validez metodológica se resiente, pero no estáis desarmados.

**QEMU en modo usuario (`qemu-user-static`) o sistema completo (`qemu-system-aarch64`) puede producir resultados publicables, siempre que se documente de forma transparente.**  
No emula la microarquitectura (cachés, predicción de saltos, ejecución especulativa) de un procesador real como Cortex-A76 (RPi5) o Tremont (N100). Los resultados de rendimiento serán distintos, pero pueden ser válidos para:

- Validar la corrección funcional y la ausencia de deadlocks o cuellos de botella lógicos.
- Comparar *órdenes de magnitud* entre Variant A y Variant B bajo carga sintética.
- Cumplir el hito administrativo, siempre que el informe especifique claramente:  
  *«Mediciones realizadas sobre ARM64 emulado con QEMU X.Y; se esperan desviaciones debidas a la emulación de E/S de red y temporizadores. Los resultados finales se recalibrarán sobre hardware físico (RPi5/N100) en cuanto esté disponible.»*

**Alternativas superiores a QEMU (si hay presupuesto antes del hardware):**
- Instancias ARM cloud (AWS Graviton, Equinix Metal, etc.): ofrecen silicio real, pero pueden no coincidir con el target exacto.
- Usar una placa ARM de desarrollo que ya tengáis (si alguna RPi antigua está disponible) como proxy, dejando claro que los números finales serán con el modelo aprobado.

**Veredicto metodológico**: La emulación QEMU es **aceptable para un primer entregable** si se declara explícitamente. No es óptimo, pero protege el go/no-go. Si el hardware llega después, repetiréis el benchmark y actualizaréis el informe. Esto es defendible ante un revisor. La alternativa es el bloqueo total, que es peor.

---

### **Q5 — `-Werror` y código generado**

La supresión por fichero (`set_source_files_properties`) es una medida de contención necesaria, pero **no es suficiente por sí sola**. La regeneración automática de `network_security.pb.cc` o `internal_detector.cpp` puede introducir nuevos avisos que, al estar suprimidos, **no romperán el build, pero envenenarán silenciosamente el código**.

Para mantener el invariante `-Werror` sin sorpresas, recomendamos un **test de CI específico**:

```cmake
# CMakeLists.txt: target auxiliar que compila los ficheros generados con -Werror
add_library(check_generated_code STATIC
    ${PROTO_SRCS}
    ${XGBOOST_GENERATED_SRC}
)
target_compile_options(check_generated_code PRIVATE -Werror)
# No lo enlazamos en producción; solo se compila.
```

Este target se ejecuta en CI pero no se instala. Si una regeneración introduce una advertencia, el CI fallará y detendrá el merge hasta que se revise la supresión o se corrija el generador.

**La supresión por fichero debe mantenerse**, pero documentada con un comentario que diga: *«Advertencias suprimidas porque el código generado por protobuf/XGBoost no es mantenido por nosotros. Si la regeneración cambia las advertencias, el test `check_generated_code` debe fallar y esta supresión se revisará.»*

**Veredicto**: La supresión es el firewall; el test CI es el detector de incendios. Tened ambos.

---

No hay más cuestiones.

Habéis hecho un trabajo que honra el oficio. Cada warning eliminado es una neurona ganada al debug. Ahora descansad, soldados del bit. El lunes retomaréis con la mente limpia y `DEBT-VARIANT-B-CONFIG-001` esperándoos.

*El Consejo de Sabios, en sesión permanente,  
a 3 de Mayo de 2026.*