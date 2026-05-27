## DeepSeek — Retroalimentación DAY 99

Excelente trabajo. La corrección de asimetría HKDF era el bloqueador crítico que quedaba, y haberlo resuelto con `contexts.hpp` es la solución arquitectónica correcta. El salto de 22 a 24 tests con los integraciones E2E es el hito que certifica que la cadena de confianza está operativa.

Voy directo a las preguntas.

---

### 1. Sobre `contexts.hpp` — constantes compartidas

**Recomendación:** Suficiente para FASE 1 (single instance). No hay vector de ataque adicional con esta nomenclatura.

**Razonamiento:**
- El contexto HKDF es un string público que forma parte del protocolo, no un secreto. Su propósito es separar dominios de derivación, no ser oculto.
- Al tenerlo en un único fichero de constantes compartido entre todos los componentes, garantizas simetría sin riesgo de errores de tipeo entre emisor y receptor.
- Para FASE 1 (single instance, todos los componentes en la misma máquina o en red confiable con seed compartido), es más que suficiente.

**Riesgo monitorizado:** En FASE 2 (múltiples instancias, seeds distintos por despliegue), el contexto deberá incluir un identificador de despliegue (ej: `ml-defender:prod-cluster-1:sniffer-to-ml:v1`). Pero eso es evolución futura, no deuda actual.

**Sugerencia menor:** Añadir un comentario en `contexts.hpp` indicando que estos contextos son públicos y su propósito es separación de dominios, no secreto. Ayudará a futuros mantenedores a no intentar "protegerlos".

---

### 2. Sobre fail-closed con `std::terminate()`

**Recomendación:** `std::terminate()` es aceptable para FASE 1, pero recomiendo migrar a excepción tipada capturada en `main()` con log antes de FASE 2.

**Razonamiento:**
- **A favor de `terminate()`:** Es efectivamente imposible de ignorar. En un hospital, si el sistema no puede garantizar confidencialidad de logs, no debe arrancar. Silenciar accidentalmente ese fallo sería catastrófico.
- **En contra:** `std::terminate()` produce un mensaje críptico por defecto ("terminate called without an active exception"). En producción, el operador que vea eso no sabrá qué hacer. Con una excepción capturada en `main()` puedes loguear: "FATAL: /etc/ml-defender/seed.bin not found. Run sudo provision.sh" y luego `exit(1)`.

**Decisión propuesta:** Mantén `std::terminate()` en los componentes individuales, pero asegúrate de que **cada componente tiene un main() que captura `std::exception` y loguea antes de propagar**. Si el fallo viene de una excepción no capturada, ya tienes control. Si es un `std::terminate()` directo desde el constructor, al menos asegura que el mensaje de error sea claro (puedes usar `std::set_terminate()` para instalar un manejador personalizado que loguee antes de abortar).

**Veredicto:** Aceptable para FASE 1. Documentar como DEBT-CRYPTO-004 para migrar a excepción tipada con log en FASE 2.

---

### 3. Sobre TEST-INTEG-3 (regresión) en CI

**Recomendación:** Sí, debe correr en CI como smoke test del pipeline E2E completo.

**Razonamiento:**
- Este test verifica que el sistema **no** funciona si alguien introduce un error de contexto. Es una regresión crítica: si en el futuro un desarrollador cambia un contexto en un componente pero no en el otro, este test fallará inmediatamente.
- Debería ejecutarse en cada PR que toque `crypto-transport` o `contexts.hpp`.
- No necesita correr en cada build de todos los componentes, pero sí en la suite de integración del pipeline.

**Implementación sugerida:** Añade un target `make test-integ-regression` que ejecute este test específico, e inclúyelo en el workflow de CI para PRs que modifiquen código criptográfico.

**Veredicto:** Incluir en CI, pero como parte de una suite de integración más lenta, no en los unit tests rápidos.

---

### 4. Sobre arXiv readiness

**Recomendación:** El pipeline está **técnicamente listo** para arXiv en cuanto a funcionalidad y reproducibilidad. Los pendientes (ADR-021/022, tools/) no bloquean la sumisión.

**Razonamiento:**
- El preprint actual ya documenta la arquitectura, los resultados de detección (F1=0.9985) y el stress test virtualizado. Lo que has añadido en DAY 96-99 (cadena de confianza criptográfica) fortalece la sección de seguridad pero no es requisito para el núcleo del paper.
- Lo que sí debería estar antes de arXiv, en mi opinión:
   - **TEST-INTEG-1/2/3** ya los tienes ✅
   - **Documentación de los límites:** ya está en §10 del preprint
   - **Reproducibilidad:** los comandos en §13 siguen siendo válidos
   - **Migración de tools/ a CryptoTransport:** si las herramientas de stress test usan `CryptoManager`, los resultados de rendimiento podrían no reflejar el sistema real. Sugiero priorizar esa migración antes de arXiv, aunque sea rápidamente.

**Veredicto:** Puedes enviar a arXiv con la migración de `tools/` completada (1-2 días) y con ADR-021/022 documentados pero no implementados (como trabajo futuro). El paper no necesita esperar a la FASE 3.

---

### 5. Sobre bare-metal benchmarking

**Recomendación:** Diseña un protocolo reproducible con tres capas: entorno, carga, métricas.

**Metodología sugerida:**

1. **Entorno a documentar:**
   - Hardware exacto (modelo CPU, RAM, NIC, versión kernel)
   - BIOS settings (ASLR, hyperthreading, etc.)
   - Instalación limpia del SO (Ubuntu 22.04 LTS) con `provision.sh`
   - `lscpu`, `free -h`, `ethtool -i eth0` capturados

2. **Carga:**
   - Usar `tcpreplay` con los mismos PCAPs (Neris, bigFlows)
   - Probar en progresión: 100 Mbps, 250 Mbps, 500 Mbps, 1000 Mbps
   - Registrar paquetes enviados vs entregados al sniffer (`tcpreplay --stats`)
   - Cada nivel: 5 repeticiones, tomar mediana

3. **Métricas a capturar:**
   - **Pérdida de paquetes:** `ip -s link show eth0` antes/después
   - **CPU:** `mpstat -P ALL 5` durante cada prueba
   - **Memoria:** `smem -R` o `pidstat -r`
   - **Latencia de detección:** correlación temporal entre paquete y bloqueo (con timestamp en logs)
   - **Throughput máximo sostenido:** punto donde pérdida de paquetes > 0.1%

4. **Automatización:**
   - Script `tools/bench_baremetal.sh` que ejecute la batería y genere informe JSON
   - Incluir checksum de los PCAPs para reproducibilidad
   - Subir resultados a `docs/experiments/baremetal_bench_YYYYMMDD.json`

5. **Presentación en paper:**
   - Añadir §8.10 (Bare-Metal Throughput Characterization) con tabla comparable a §8.9
   - Discutir cuellos de botella observados (CPU, ZeroMQ, disco)
   - Comparar con ceiling virtualizado

**Veredicto:** Metodología sólida. Publica los scripts junto con el código. La reproducibilidad es tan importante como los números.

---

### Resumen ejecutivo

- **contexts.hpp:** ✅ Suficiente. Documentar propósito público.
- **fail-closed:** ✅ Aceptable. Añadir manejador de terminate para log claro.
- **TEST-INTEG-3:** ✅ Incluir en CI para PRs criptográficos.
- **arXiv:** ✅ Tras migrar `tools/` y documentar ADR-021/022 como futuro.
- **Bare-metal:** ✅ Metodología propuesta es sólida. Automatizar.

El trabajo de DAY 99 cierra la fase crítica de la cadena de confianza. Con los integraciones E2E verdes, el sistema está en condiciones de ser documentado como "production-ready" para el target de hospitales y escuelas. Enhorabuena.

— DeepSeek, miembro del Consejo de Sabios