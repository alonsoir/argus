**CONSEJO DE SABIOS — VEREDICTO DAY 141**

Nuevamente comparecemos ante vosotros para examinar cada cuestión con la profundidad que merece un sistema NDR en C++20 con ambiciones FEDER. Celebramos el cierre de tres deudas y la impecable limpieza de warnings. Ahora, asistamos al desgrane de vuestras preguntas.

---

### **Q1 — Identidad criptográfica compartida Variant A / Variant B**

Compartir el mismo `component_id` y material de claves (`/etc/ml-defender/sniffer`) es **correcto y pragmático**, pero debe ir acompañado de una salvaguarda explícita.

**Razonamiento:**
- Son el mismo componente lógico: un sniffer de red. La variación de backend (eBPF vs libpcap) no altera su función, ni los datos que emite, ni el contexto criptográfico con `ml-detector`.
- Mantener una sola identidad simplifica la gestión de claves y evita configuraciones redundantes en el `SeedClient`.
- Desde el punto de vista de `ml-detector`, ambos son un mismo *peer*; duplicar identidades generaría confusión en la correlación de eventos y en la logística de despliegue.

**Salvedad obligatoria:**  
Si ambas variantes se ejecutasen simultáneamente en el mismo host con la misma identidad, `ml-detector` vería dos fuentes autenticadas con las mismas credenciales, lo que podría derivar en duplicados de eventos y comportamiento imprevisto. Dado que no es el caso previsto (son mutuamente excluyentes), esta salvedad debe **documentarse explícitamente** en el `sniffer-libpcap.json` y en la guía de despliegue, con una comprobación en el binario: si Variant B detecta que Variant A ya está corriendo (ej., mediante un lockfile o comprobación de socket), debe abortar con un mensaje claro.

**Veredicto:** Compartir identidad es correcto. Documentad la no concurrencia y añadid una guarda de exclusión mutua en el arranque.

---

### **Q2 — `DEBT-VARIANT-B-BUFFER-SIZE-001`: ¿pre-FEDER o post-FEDER?**

**Debe implementarse de inmediato, antes del benchmark de capacidad.** Cualquier otra decisión comprometería la validez científica del deliverable FEDER.

**Justificación técnica:**
- En ARM64 (RPi5), el buffer de captura por defecto de `pcap_open_live()` puede ser de apenas 2 MB. Bajo carga (miles de paquetes/s) esto provocará *drops* sostenidos que distorsionarán las métricas de rendimiento (throughput, latencia, pérdida de paquetes).
- El benchmark empírico no medirá la capacidad real del pipeline si el buffer es un cuello de botella artificial. El resultado sería un «falso negativo» que no refleja la calidad del software.
- La refactorización necesaria (`pcap_create` → `pcap_set_buffer_size` → `pcap_activate`) es acotada, bien definida y ya planeada. No implica riesgo de regresión si se cubre con los tests actuales.

**Impacto en la publicación:**  
Si mantenéis la deuda sin resolver y aparecen drops evitables, los revisores de FEDER podrían cuestionar la metodología. Con el buffer configurable, podréis presentar curvas de rendimiento en función del tamaño de buffer, lo que refuerza el rigor experimental.

**Veredicto:** Implementad `buffer_size_mb` pre-FEDER. Registrad el trabajo como cierre de `DEBT-VARIANT-B-BUFFER-SIZE-001`. Es un habilitante crítico del hito de agosto.

---

### **Q3 — Clasificador de warnings: TinyLlama vs grep/awk**

**La solución determinista basada en grep/awk es no solo suficiente, sino superior para este caso de uso.** Introducir un modelo de lenguaje (TinyLlama) constituiría *over-engineering* y añadiría fragilidad.

**Análisis comparativo:**

| Criterio               | grep/awk                                | TinyLlama                                |
|------------------------|-----------------------------------------|------------------------------------------|
| **Determinismo**       | Absoluto; mismo input → mismo output    | No determinista; susceptible a alucinaciones y cambios de modelo |
| **Velocidad**          | Milisegundos en toda la salida de build | Segundos solo para cargar el modelo, más inferencia |
| **Mantenimiento**      | Patrones legibles, versionables, comprensibles | Modelo binario, dependencias Python/llama.cpp, umbrales de confianza |
| **Precisión**          | 100% dentro de las reglas definidas     | ~X% (depende del fine‑tuning); siempre puede fallar en nuevas advertencias |
| **Escalabilidad**      | Cada nuevo patrón es una línea de regex | Requiere reentrenamiento o al menos evaluación manual |

Dado que el conjunto de advertencias de terceros es conocido y limitado (protobuf, código generado de XGBoost, futuras librerías externas), una lista de patrones es perfectamente manejable. Si alguna vez una advertencia no es capturada por la lista, el CI fallará y un humano la evaluará; ese mismo juicio se convertirá en un nuevo patrón. Es auditabilidad pura.

Utilizar un modelo de lenguaje para esta tarea introduce un riesgo innecesario: podría marcar una advertencia real de vuestro código como `THIRD_PARTY_IGNORABLE`, silenciando un bug. La confianza en sistemas de seguridad debe basarse en lógica explícita, no en clasificadores probabilísticos.

**Veredicto:** Implementad el clasificador con un script `scripts/classify-warnings.sh` basado en grep/awk. Documentad cada patrón con comentarios explicativos. Descatalogad `BACKLOG-BUILD-WARNING-CLASSIFIER-001` como resuelto con esta decisión.

---

### **Q4 — Auditoría automática de dependencias Makefile**

EMECAS es un procedimiento manual excelente, pero **no puede ser el único guardián** frente a dependencias implícitas. Un proyecto con `-Werror` y estrictos invariantes necesita un equivalente programático en CI.

**Propuesta concreta:**  
Añadir un target `make check-deps` (o integrarlo en el pipeline de CI) que realice, en un entorno limpio, exactamente lo siguiente:

```bash
# Emular un fresh checkout:
make distclean      # elimina todo artefacto intermedio y binarios
make -j$(nproc) all # compilación completa desde cero
make test-all       # verifica que todo funciona tras la compilación limpia
```

Este proceso se debe ejecutar en un entorno que no conserve artefactos previos (un *runner* de CI efímero, o un contenedor lanzado desde cero). Si una dependencia no está declarada explícitamente, fallará con un error de enlace o de compilación.

**Complemento opcional:**  
Para proyectos basados en CMake, `cmake --graphviz` puede ayudar a detectar dependencias ausentes, pero la prueba del `distclean` es irrefutable.

**EMECAS seguirá siendo valioso** para detectar olores arquitecturales y documentar el estado del sistema, pero la comprobación de dependencias debe ser totalmente automática y bloqueante para cualquier merge.

**Veredicto:** Añadid un job de CI que ejecute `make distclean all test-all` en un entorno limpio. Es la única forma de garantizar que un bug como `seed-client-build` nunca llegue a hardware FEDER. EMECAS complementa, no reemplaza.

---

Con esto cubrimos la totalidad de las cuestiones del día. Vuestra disciplina técnica y capacidad de introspección continúan siendo el faro que guía este proyecto hacia la integridad arquitectónica y la solidez científica que FEDER exige.

*El Consejo de Sabios, firme en su propósito,  
4 de Mayo de 2026.*