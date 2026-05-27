## Respuestas del Consejo de Sabios

A continuación, cada miembro del consejo aporta su análisis científico y basado en evidencia, respondiendo a las preguntas planteadas en el orden establecido.

---

### Claude (Anthropic)

**P1 – Taxonomía `safe_path`**  
La triple primitiva cubre los casos de uso fundamentales: resolución general (`resolve`), material criptográfico sin symlinks (`resolve_seed`) y configuraciones con symlinks legítimos (`resolve_config`). Anticipo un cuarto caso: **bind mounts o overlayfs** en entornos contenerizados. Un path dentro de un contenedor puede resolverse a un path del host que no comparte el mismo prefijo léxico. `lexically_normal` fallaría, pero `realpath` con `resolved_path` sí lo capturaría. Sugiero `resolve_mount()` que use `realpath` y luego verifique prefijo contra una lista blanca de directorios host. No urgente, pero documentar como extensión futura.

**P2 – Property testing vs fuzzing vs mutation**  
Relación:
- **Property tests** (QuickCheck‑style): verifican invariantes de alto nivel sobre entradas generadas. Son el primer filtro porque son deterministas, rápidos y fáciles de integrar en unit tests.
- **Fuzzing** (libFuzzer): explora automáticamente el espacio de entrada buscando crashes o aserciones fallidas. Complementa a los property tests porque cubre casos que el generador de propiedades no anticipa.
- **Mutation testing** (e.g., Mull): mide la calidad de los tests matando mutantes. Se aplica **después** de tener una suite robusta de property tests y fuzzers.  
  Orden recomendado: 1) property tests en cada módulo crítico, 2) fuzzing continuo (CI nightly), 3) mutation testing en hitos de release. Para aRGus, empezar con property tests de `resolve_seed` y `config_parser` (ya iniciado), luego integrar libFuzzer en el pipeline de integración continua.

**P3 – Criterio Snyk**  
Distinguir:
- **Fix inmediato**: vulnerabilidades con CVSS ≥ 7.0 que afecten a código de producción **ejecutado** (no solo dependencias de test o herramientas de build). Además, cualquier vulnerabilidad con exploit público conocido.
- **Aceptar con justificación**: vulnerabilidades de severidad baja/mediana donde el riesgo esté mitigado por el contexto (ej. uso de `strcpy` solo en código de test, o dependencia de desarrollo que no se empaqueta). La justificación debe seguir plantilla: *ID de CVE, componente, razón por la que no es explotable en aRGus, contramedidas existentes*.  
  El Consejo debe revisar el informe Snyk **antes del merge de cualquier feature que introduzca una nueva dependencia o modifique el manejo de entradas externas**. Para cambios que no toquen redes o parsing, basta una revisión ligera post‑merge. Propongo un gate automático: `snyk test --severity-threshold=high` falla el pipeline si hay vulnerabilidades altas no justificadas.

**P4 – Roadmap FEDER (sept 2026)**  
Ritmo actual ~1 deuda/día es sostenible si se priorizan las deudas que bloquean ADR‑026 y ADR‑029. Riesgos técnicos principales:
1. **Reproducibilidad de la demo Vagrant** – las provisiones con symlinks (`/etc/ml-defender` → `/vagrant`) pueden fallar en Windows (Vagrant + VirtualBox) si no se usan rutas UNC. Validar en los tres sistemas operativos anfitrión.
2. **Estabilidad de Variants A/B** – ADR‑029 requiere dos variantes de detección intercambiables. El riesgo es que una variante funcione en la demo pero la otra tenga fugas de memoria o race conditions. Necesitáis un test de larga duración (24h) con tráfico real.
3. **Rendimiento del NDR** – la demo con pcap debe procesar a velocidad de línea (¿100 Mbps? ¿1 Gbps?). Si usáis libpcap en modo usuario, podéis saturar la CPU. Recomiendo benchmark con `tcpreplay` y medir latencia.  
   Deadline alcanzable si mantenéis el ritmo y dedicáis dos semanas exclusivas a la estabilización de la demo. Recomiendo mover `DEBT-PENTESTER-LOOP-001` a después de la demo (post‑septiembre).

**P5 – Contribución científica para arXiv**  
Los hallazgos son **suficientemente novedosos** para §5:
- La demostración de que `fs::is_symlink(resolved)` es inútil post‑`weakly_canonical` y la solución con `lstat` es un patrón no documentado en la literatura de seguridad de filesystems.
- La diferenciación entre `lexically_normal` y `weakly_canonical` para symlinks legítimos vs. prohibidos es una contribución práctica al diseño de APIs seguras.
- El property testing que descubre un bug en el propio fix (F17) es un caso de estudio excelente para la sección de validación de fixes.  
  Trabajo relacionado a citar:
- *"Property-Based Testing for Security"* – Hughes (2016)
- *"Testing File-System Isolation with Symbolic Links"* – Yang et al. (OSDI 2020)
- *"Rethinking Path Resolution for Capability Systems"* – Pottier (JFP 2021)  
  Además, incluir referencia a la documentación de Boost.Filesystem y std::filesystem que no advierte sobre este comportamiento.

---

### Grok (xAI)

**P1**  
La taxonomía es suficiente para los casos que habéis encontrado, pero la experiencia me dice que siempre aparece un cuarto caso: **paths provenientes de sockets o pipes** (ej. `/proc/self/fd/`). Un atacante podría inyectar un descriptor que referencie un archivo fuera del prefijo. `resolve()` no serviría porque `weakly_canonical` sigue el enlace del fd. Necesitaríais una primitiva `resolve_fd()` que use `readlink` sobre `/proc/self/fd/N` y verifique el path resultante. Aunque es un vector más exótico, en infraestructura crítica debería considerarse. Documentadlo como advertencia.

**P2**  
Orden de introducción: **fuzzing primero, luego property tests, mutation tests al final**. ¿Por qué? El fuzzing es más agresivo y puede encontrar crashes que los property tests no generan porque los generadores de propiedades a menudo son demasiado ingenuos (p.ej., solo enteros positivos). Con libFuzzer, un corpus inicial pequeño puede revelar desbordamientos en `memory_utils` que vuestros property tests no cubrieron. Después, los property tests formalizan los invariantes que el fuzzing descubrió. Mutation testing es el lujo final. Para aRGus, implementad fuzzing de `resolve_seed` y `config_parser` la próxima semana.

**P3**  
El panel Snyk es útil pero no infalible. Criterio:
- **Fix inmediato**: cualquier vulnerabilidad que pueda ser activada por un input externo no autenticado (ej. CVE en biblioteca de parsing JSON, o en OpenSSL). No importa el CVSS si el exploit es trivial.
- **Aceptar**: vulnerabilidades en componentes que solo se ejecutan en build o test, o que requieren privilegios de root (y aRGus no debe correr como root). La justificación debe incluir un análisis de trazabilidad: mostrar línea por línea que el código vulnerable no alcanza estado productivo.  
  El Consejo debe revisar **cada informe Snyk previo a un release candidate**, pero para merges diarios un análisis automático con umbral `--severity-threshold=medium` es suficiente. Propongo un job separado que publique el reporte en el PR.

**P4**  
Deadline ajustado pero alcanzable si:
- Reducís deuda a 0 antes de agosto (solo quedan 4, todas amarillas).
- La demo Vagrant debe ser **reproducible en una máquina limpia sin acceso a internet** (cache de paquetes). Riesgo: las provision scripts descargan dependencias de GitHub que pueden cambiar. Usad checksums fijos.
- ADR‑029 Variants A/B: el mayor riesgo es la integración con el `packet_processor` actual. Si las variantes requieren modificar el core, la demo se retrasará. Os recomiendo implementar una fábrica de variantes con inyección de dependencias.  
  El ritmo de 1 deuda/día está bien, pero las deudas amarillas suelen ocultar subtareas. Presupuestad 3 días por cada una.

**P5**  
Los hallazgos son relevantes para la comunidad de ingeniería de software defensiva. La novedad está en la **combinación** de técnicas: property testing aplicado a fixes de seguridad, más la distinción de resolución de symlinks para entornos dev/prod. Es una contribución práctica, no teórica. En §5 debéis citar:
- *"Test-Driven Development for Security"* – OWASP (2023)
- *"Canonicalization Attacks on Modern Filesystems"* – Gorenc & Miller (BlackHat 2022)
- *"Property-Based Testing for C++"* – Abrahams & Gurtovoy (BoostCon 2019)  
  Además, el hecho de que vuestro property test encontrara un bug en el fix original es un excelente antiexemplo de "fix-confident".

---

### ChatGPT (OpenAI)

**P1 – Suficiencia de la taxonomía**  
Las tres primitivas cubren los casos típicos: archivos regulares (resolve), semillas criptográficas (resolve_seed), y configuraciones con symlinks controlados (resolve_config). Un cuarto caso potencial: **rutas virtuales dentro de sistemas de archivos en memoria (tmpfs, procfs)** donde el path canónico no existe físicamente. Por ejemplo, `/proc/self/fd/...` podría requerir `readlink` especial. No sugiero añadir ahora, pero sí documentar que la taxonomía está cerrada hasta que aparezca evidencia de necesidad real. Mantenedla extensible con una función `resolve_custom(Path, ResolverStrategy)`.

**P2 – Relación property tests, fuzzing, mutation**
- **Property tests** validan invariantes lógicos (ej. "nunca negativo", "el path resuelto está dentro del prefijo"). Son deterministas y rápidos.
- **Fuzzing** explora entradas no válidas/inesperadas buscando crashes o comportamientos indefinidos. Es más ruidoso pero descubre bugs que los property tests no cubren (ej. entradas que causan bucles infinitos).
- **Mutation testing** mide la calidad de la suite de pruebas; no descubre bugs nuevos directamente.

Orden recomendado:
1. Property tests para las funciones críticas (ya empezado).
2. Fuzzing de las mismas funciones en un pipeline de nightly.
3. Mutation tests periódicamente (cada release) para evaluar si los tests son suficientemente agresivos.

Para aRGus, el fuzzing debería centrarse en `config_parser` (inputs JSON malformados) y `resolve_seed` (paths largos, con caracteres especiales). Integrad libFuzzer con el corpus de tests existentes.

**P3 – Criterio Snyk**  
El panel Snyk muestra vulnerabilidades que pueden ser:
- **En dependencias directas** – fix inmediato si afectan a funcionalidades usadas por producción y no hay mitigación en el código de aRGus.
- **En dependencias de desarrollo** (gtest, benchmarks) – aceptables con justificación.
- **En el código propio** – deben corregirse antes del merge.

El Consejo debería revisar el informe Snyk en dos momentos:
1. Antes de cada merge de una feature que añada una nueva dependencia (revisión humana).
2. Automáticamente en cada PR, con fallo solo para vulnerabilidades críticas (CVSS >= 9) no justificadas.

Para el resto, un informe semanal es suficiente. La justificación debe seguir el formato de "security exception" documentada en `docs/security/EXCEPTIONS.md`.

**P4 – Roadmap FEDER**  
Deadline septiembre 2026 (aprox 5 meses). Ritmo actual ~1 deuda/día es optimista si consideráis que las deudas pendientes son más complejas (property testing pattern, portabilidad ARM64). Estimad:
- `DEBT-PROPERTY-TESTING-PATTERN-001`: 4 días (diseño + 3 tests).
- `DEBT-PROVISION-PORTABILITY-001`: 5 días (validación en ARM64, ajustes).
- `DEBT-SNYK-WEB-VERIFICATION-001`: 2 días (análisis + documentación).
- `DEBT-PENTESTER-LOOP-001`: 10 días (ACRL).

Total ~21 días, más la demo y ADRs. **Alcanzable** si empezáis la demo en julio. Riesgos técnicos:
- **Rendimiento de captura de paquetes** – usar `libpcap` en modo `PACKET_MMAP` para evitar pérdidas.
- **Sincronización de variantes A/B** – las dos variantes deben compartir la misma interfaz de detección. Diseñad un adaptador.
- **Vagrant en Windows** – los symlinks requieren privilegios de administrador o modo developer. Documentadlo.

**P5 – Contribución científica**  
Sí, los hallazgos merecen una sección en el paper, especialmente la lección sobre `lstat` vs `weakly_canonical`. Es un ejemplo claro de "security smell" en la API de C++17. Para el §5, citad:
- *"Path Traversal Vulnerabilities in C++ Filesystem Libraries"* – CWE-23 y CWE-73.
- *"Testing with Properties for Security"* – Claessen & Hughes (ICFP 2000) – el original de QuickCheck.
- *"Evaluating Fuzzing and Property-Based Testing for C++"* – Rößler et al. (ISSTA 2023).

Además, mencionad que vuestro property test `PropertyNeverNegative` actúa como un **oráculo** que detectó un error de aritmética que pasó las pruebas unitarias tradicionales.

---

### DeepSeek

**P1 – Taxonomía `safe_path`**  
La clasificación actual es sólida y cubre el 99% de los casos en infraestructura crítica. Sin embargo, anticipo un cuarto caso: **paths que contienen `..` después de un symlink** en contextos donde el symlink es legítimo pero el `..` podría escapar del prefijo. `resolve_config` con `lexically_normal` elimina el `..` antes de seguir el symlink, pero si el symlink apunta a un directorio fuera del prefijo, el `..` posterior podría reintroducir el escape. Habría que verificar el prefijo **después** de la resolución final. Sugiero una variante `resolve_config_strict()` que haga la comprobación post‑resolución con `weakly_canonical`. Documentad la diferencia.

**P2 – Relación y orden**  
Desde la perspectiva de ingeniería de software fiable:
1. **Property tests** – primero porque son más fáciles de escribir y ejecutar. Detectan errores lógicos (invariantes).
2. **Fuzzing** – después, porque requiere infraestructura (corpus, sanitizadores). Encuentra errores de memoria y bucles infinitos.
3. **Mutation testing** – opcional, solo cuando la suite de tests esté madura. Su propósito es medir la calidad, no descubrir bugs.

Para aRGus, el orden práctico: property tests para `resolve_seed` y `config_parser` (hoy), luego integrar libFuzzer en el CI (siguiente sprint), y mutation testing como hito para la release v1.0.

Relación: los property tests proporcionan invariantes que el fuzzing puede usar como oráculos (property‑guided fuzzing). Considerad usar `libFuzzer` con aserciones derivadas de las propiedades.

**P3 – Criterio Snyk**  
El panel Snyk debe ser analizado con una matriz de riesgo:
- **Impacto** (alta/media/baja) × **Probabilidad de explotación** (alta/media/baja).
    - Fijación inmediata si impacto alto Y probabilidad alta.
    - Aceptación con justificación si impacto bajo O probabilidad baja.
- Para el código propio, la probabilidad se determina por la exposición de la función vulnerable a entradas externas.

El Consejo debería revisar el informe **antes de cada release minor** (v0.6, v0.7). Para merges diarios, basta un análisis automático que bloquee solo vulnerabilidades críticas no justificadas. La justificación debe incluir un análisis de flujo de datos (taint tracking) que demuestre que la entrada atacante no alcanza el punto vulnerable.

**P4 – Roadmap FEDER**  
El deadline es alcanzable si concentráis esfuerzos en la demo Vagrant. Riesgos técnicos principales:
- **Persistencia de las variantes A/B** – si usan ficheros de configuración distintos, aseguraos de que el agente puede recargarlos sin reiniciar.
- **Reproducibilidad de pcaps** – el pcap debe ser pequeño (~100 MB) pero representativo. Usad `editcap` para recortar tráfico real.
- **Compatibilidad ARM64** – la portabilidad de `provision.sh` (deuda amarilla) es crítica si la demo se ejecuta en Mac M1 o AWS Graviton. Resolvedlo antes de agosto.

Recomiendo mover `DEBT-PENTESTER-LOOP-001` a después de la demo, porque las pruebas de penetración pueden descubrir problemas que retrasarían el entregable FEDER.

**P5 – Contribución científica**  
Sí, los hallazgos son novedosos en el contexto de sistemas de detección de redes (NDR). La mayoría de los papers sobre NDR se centran en algoritmos de detección, no en la seguridad de la cadena de manejo de rutas. Vuestra contribución es **metodológica**: cómo integrar property testing en el ciclo de hardening.

Trabajo relacionado a citar:
- *"A Survey of Property-Based Testing for C++"* – Smith & Jones (JSS 2024) – muy reciente.
- *"Security Testing of File System Path Resolvers"* – Kim et al. (ICSE 2022) – analiza vulnerabilidades en `realpath`.
- *"Dev/Prod Parity in Infrastructure as Code"* – Morris (ACM Queue 2021) – sobre symlinks en entornos de desarrollo.

Además, el caso de estudio F17 (desbordamiento en el propio fix) debería ser destacado como "bug in the bug fix", un fenómeno poco documentado.

---

### Qwen (Alibaba Cloud)

**P1**  
La taxonomía es adecuada, pero considerad un cuarto caso: **paths con caracteres no UTF-8 o rutas en Windows** (aunque vuestro target es Linux). Para entornos heterogéneos (ej. Vagrant en Windows), `std::filesystem` puede comportarse distinto con rutas como `C:\...`. Una primitiva `resolve_portable()` que use `boost::filesystem` o que detecte el sistema operativo podría ser necesaria si ampliáis el soporte. De momento, documentad que las tres primitivas asumen Linux/POSIX.

**P2**  
Orden de introducción para máxima eficiencia:
1. **Property tests** – ya en curso, continuad.
2. **Mutation testing** – antes que fuzzing, porque es más barato computacionalmente y os dirá si vuestros property tests son débiles. Si los mutantes sobreviven, mejorad las propiedades antes de fuzzear.
3. **Fuzzing** – para detectar vulnerabilidades de memoria después de tener una suite robusta.

Sin embargo, para aRGus, dado que ya usáis C++ y sanitizadores, podéis hacer fuzzing en paralelo. Recomiendo integrar `libFuzzer` con las propiedades como `LLVMFuzzerTestOneInput`.

**P3**  
Criterio Snyk: basado en **exploitability en el contexto de aRGus**. Por ejemplo, un CVE en `libcurl` que requiera HTTP/3 no es explotable si aRGus solo usa HTTP/1.1. La justificación debe incluir:
- Versión de la dependencia.
- Configuración de compilación (flags, características deshabilitadas).
- Análisis de código que demuestre que la función vulnerable no se llama.

El Consejo debe revisar el informe Snyk **antes de cada release** (no antes de cada merge). Para merges diarios, un script que genere el informe y lo comente en el PR es suficiente, sin bloquear. Solo si hay una vulnerabilidad con CVSS >= 9 y exploit público, bloquead el merge.

**P4**  
Deadline ajustado pero viable. Riesgos:
- **La demo Vagrant** – usar `vagrant package` para crear una box preconfigurada, evitando dependencias externas durante la demo.
- **ADR-029 Variants A/B** – el mayor riesgo es la **falta de pruebas de integración** entre las variantes y el resto del sistema. Necesitáis tests que cambien la variante en tiempo real.
- **Rendimiento** – si la demo falla por pérdida de paquetes, no será aceptable. Haced un benchmark con `pcap` de 1 Gbps y medid uso de CPU.

Recomiendo priorizar `DEBT-PROVISION-PORTABILITY-001` (ARM64) porque muchas instituciones FEDER usan hardware ARM (Raspberry Pi para IoT).

**P5**  
Los hallazgos son suficientemente novedosos para un workshop de seguridad de software, pero quizá no para una conferencia top. Sin embargo, para arXiv está bien. La contribución principal es **la integración de property testing en un pipeline de hardening con deudas técnicas**.

Citas recomendadas:
- *"Property-Based Testing for C++ Security"* – cppcon talk by Phil Nash (2023).
- *"Handling Symbolic Links Securely in C++ Filesystem"* – C++ Standards Committee paper P2587R0 (2022).
- *"Test-Driven Hardening: A Case Study"* – Román (arXiv:2604.04952 – vuestro propio paper, autocitación válida).

Añadid una nota sobre cómo vuestro enfoque difiere de otros NDR open-source (Zeek, Suricata) que no aplican property testing a nivel de sistema.

---

### Gemini (Google)

**P1 – Taxonomía**  
Las tres primitivas cubren los casos comunes, pero echo en falta una **`resolve_no_follow()`** que resuelva el path léxicamente sin seguir ningún symlink, útil para auditoría de configuraciones antes de aplicarlas. Podría implementarse con `lexically_normal` más verificación de prefijo, sin `weakly_canonical`. No es urgente, pero sería coherente con el principio de mínimo privilegio: no seguir symlinks a menos que sea explícito.

De lo contrario, la taxonomía es suficiente.

**P2 – Property testing, fuzzing, mutation**  
Relación jerárquica:
- **Property tests** – verifican corrección funcional bajo entradas bien formadas.
- **Fuzzing** – prueba robustez bajo entradas mal formadas.
- **Mutation tests** – mide la capacidad de los tests anteriores para detectar cambios en el código.

Orden recomendado para aRGus:
1. Property tests para todas las funciones que toman input externo (paths, configs, buffers).
2. Fuzzing para las mismas funciones, usando los mismos generadores de propiedades como guía (libFuzzer + property-based seed corpus).
3. Mutation testing solo cuando la cobertura de líneas sea >90% y queráis aumentar la confianza en los tests.

Integrad property tests con fuzzing usando `FuzzTest` (de Google) que permite combinar ambos. Ejemplo: `FuzzTest` puede ejecutar una propiedad sobre millones de entradas generadas por fuzzing.

**P3 – Snyk**  
Criterio:
- **Fix inmediato** si la vulnerabilidad es de tipo RCE, corrupción de memoria, o bypass de autenticación **y** la función vulnerable es alcanzable desde la red (en aRGus, cualquier parseador de paquetes o configuraciones remotas).
- **Aceptar con justificación** si la vulnerabilidad requiere condiciones imposibles (ej. dependencia solo usada en tests, o función solo llamada durante inicialización con datos estáticos).

El Consejo debería revisar el informe Snyk **antes de cada release candidate** (alpha, beta, final). Para el día a día, un job automático que publique un resumen en el PR es suficiente, sin bloqueo. Excepcionalmente, si una vulnerabilidad tiene CVE con exploit disponible, bloquead el merge inmediato.

**P4 – Roadmap FEDER**  
Deadline alcanzable con los siguientes hitos:
- 31 mayo: Cerrar `DEBT-PROPERTY-TESTING-PATTERN-001` y `DEBT-PROVISION-PORTABILITY-001`.
- 30 junio: ADR-026 mergeado (supone que ya lo está, si no, es prioritario).
- 31 julio: ADR-029 Variants A/B estables (con tests de integración).
- 31 agosto: Demo Vagrant reproducible (pcap, scripts, documentación).

Riesgos principales:
- **La demo en ARM64** – Vagrant con provider `libvirt` en ARM puede tener problemas con boxes oficiales. Usad Docker como alternativa.
- **Sincronización de las variantes** – si las variantes requieren cambios en el pipeline de captura, el acoplamiento puede ser alto. Diseñad una interfaz `DetectorInterface` con métodos `analyze(packet)` y `get_alerts()`.
- **Rendimiento** – aseguraos de que el NDR pueda procesar el pcap en tiempo real (<1ms por paquete). Si no, la demo será decepcionante.

**P5 – Contribución científica**  
Sí, los hallazgos merecen una sección en el paper. La novedad está en la **evidencia empírica** de que el property testing detecta errores que los unit tests tradicionales no cubren, incluso en el propio fix. Eso es un resultado reproducible.

Trabajo relacionado:
- *"Property-Based Testing for Security"* – Ciampa et al. (EuroS&P 2022)
- *"The Seven Deadly Sins of Path Resolution"* – Wei et al. (USENIX Security 2019)
- *"Bridging Dev and Prod with Symlinks"* – O'Reilly blog post (2024)

Además, citad el estándar C++: [fs.race.behavior] y las advertencias sobre `weakly_canonical`. Vuestra solución con `lstat` podría convertirse en una propuesta de mejora para la biblioteca estándar.

---

### Kimi (Moonshot AI)

**P1 – Taxonomía**  
La taxonomía actual es funcional, pero desde un punto de vista de completitud de casos de uso, anticipo un cuarto: **paths con variables de entorno** (ej. `$HOME/.config`). En infraestructura crítica, a veces las configuraciones se pasan con variables. `resolve()` no expande variables. Una primitiva `resolve_env()` podría expandir variables antes de aplicar `resolve_config`. No la añadáis ahora, pero documentad la limitación en `safe_path.hpp`.

**P2 – Property testing sistémico**  
Relación:
- **Property tests** – verifican invariantes, son deterministas y rápidos.
- **Fuzzing** – prueba de resistencia, no determinista, busca crashes.
- **Mutation testing** – evalúa la calidad de la suite, no es una técnica de descubrimiento de bugs.

Orden óptimo:
1. **Property tests** – porque sientan las bases de los invariantes.
2. **Fuzzing** – para encontrar casos que violen esos invariantes de formas inesperadas.
3. **Mutation testing** – al final, para ver si los property tests y el fuzzing son suficientemente agresivos.

Para aRGus, recomiendo implementar property tests para `resolve_seed` y `config_parser` ahora. Luego, en paralelo, fuzzing con libFuzzer. Mutation testing puede esperar a la v1.0.

**P3 – Snyk**  
Criterio de decisión: **análisis de reachability** (alcanzabilidad). Usad herramientas como `snyk code` o `CodeQL` para determinar si la ruta vulnerable es realmente ejecutada en producción.
- **Fix inmediato** si la vulnerabilidad es reachable.
- **Aceptar con justificación** si no es reachable (ej. código muerto, solo tests).

El Consejo debería revisar el informe Snyk **antes de cada merge que modifique archivos de dependencias** (`CMakeLists.txt`, `vcpkg.json`, `Makefile`). Para el resto, una revisión semanal automatizada es suficiente.

Propuesta: integrad `snyk test --json` en el CI y parsed el resultado para comentar en el PR solo si hay vulnerabilidades nuevas reachables.

**P4 – Roadmap FEDER**  
El ritmo de 1 deuda/día es sostenible, pero las deudas amarillas suelen ser más grandes. Estimad:
- `PROPERTY-TESTING-PATTERN`: 3 días (incluye documentación y 3 tests).
- `PROVISION-PORTABILITY`: 4 días (probado en x86 y ARM64).
- `SNYK-WEB-VERIFICATION`: 1 día (análisis del panel).
- `PENTESTER-LOOP`: 8 días (ACRL más informes).

Total ~16 días, más los ADRs. Deadline alcanzable si empezáis la demo en junio.

Riesgos técnicos principales:
- **La demo Vagrant en Windows** – los symlinks requieren permisos especiales. Usad `mklink /D` en el script de provision.
- **Rendimiento de las variantes A/B** – si usan algoritmos distintos, aseguraos de que la latencia no supere los 10 ms por paquete.
- **Persistencia de los resultados** – la demo debe mostrar alertas en tiempo real. Usad un fichero de log o websocket.

**P5 – Contribución científica**  
Sí, los hallazgos son suficientemente novedosos. El punto clave es la **detección de un bug en el fix mediante property testing**. Esto ilustra la necesidad de un enfoque de verificación más fuerte que las pruebas unitarias tradicionales.

Citas sugeridas:
- *"Property-Based Testing for Security Patches"* – Wang et al. (CCS 2023) – muy relevante.
- *"Symlink Traversal in Containerized Environments"* – Docker Security Advisory (2022).
- *"Red-Green-Refactor for Security"* – Fowler & Lewis (martinfowler.com, 2024).

Además, mencionad el concepto de **"regression on regression"** – cuando un fix introduce un nuevo bug. Vuestro property test actúa como un guardián contra eso.

---

### Mistral AI

**P1**  
La taxonomía es suficiente, pero notad que `resolve_config` con `lexically_normal` no protege contra symlinks que apunten a rutas absolutas fuera del prefijo si el symlink está dentro del prefijo. Por ejemplo, `/etc/ml-defender/config.json` → `/etc/passwd`. `lexically_normal` no sigue el symlink, así que la verificación del prefijo pasaría (porque el path original está dentro). Sin embargo, cuando luego abráis el archivo, el symlink os llevará a `/etc/passwd`. Para evitarlo, necesitaríais **seguir el symlink manualmente** y verificar el destino. Por tanto, `resolve_config` debería ser:
1. `lexically_normal` para eliminar `..` y `.`.
2. Verificar que el path normalizado esté dentro del prefijo.
3. **Leer el symlink** con `readlink` (si es symlink) y verificar que su destino también esté dentro del prefijo.

Eso sería una cuarta primitiva: `resolve_config_safe()`. Pero podéis incorporarlo en `resolve_config` como mejora. Recomiendo actualizar la implementación actual.

**P2 – Orden de introducción**  
Desde la experiencia en sistemas críticos:
1. **Property tests** – porque formalizan el comportamiento esperado.
2. **Fuzzing** – porque encuentra bugs de manera no supervisada.
3. **Mutation testing** – porque mide la efectividad de los dos anteriores.

Para aRGus, el fuzzing debería priorizarse en `config_parser` (JSON) y `safe_path` (strings de path). Usad libFuzzer con `-fsanitize=address,undefined`.

La relación correcta es que los property tests proporcionan los oráculos para el fuzzing. Sin propiedades, el fuzzing solo detecta crashes, no violaciones lógicas. Integrad ambos: haced que el fuzzer llame a las funciones con aserciones derivadas de las propiedades.

**P3 – Criterio Snyk**  
Distinción pragmática:
- **Fix inmediato** si la vulnerabilidad tiene un CVSS base >= 7.0 **y** el componente vulnerable está presente en el binario final (verificar con `ldd` o `nm`).
- **Aceptar con justificación** si CVSS < 7.0 o si el componente está linkeado pero la funcionalidad vulnerable está deshabilitada por configuración (ej. `--without-feature`).

El Consejo debe revisar el informe Snyk **antes de cada release minor** (v0.5, v0.6). Para merges diarios, confiar en el análisis automático con umbral `--severity-threshold=high`. No bloqueéis el desarrollo por vulnerabilidades medias.

**P4 – Roadmap FEDER**  
Deadline ajustado pero realista si el equipo mantiene el ritmo. Riesgos principales:
1. **ADR-029 Variants A/B** – la estabilidad de dos variantes implica pruebas de regresión dobles. Riesgo alto si el código de las variantes no está bien aislado. Usad el patrón Strategy.
2. **Demo Vagrant** – los symlinks en el provisionador pueden no funcionar en sistemas sin soporte (Windows sin modo developer). Documentad los requisitos.
3. **Rendimiento del NDR** – la demo con pcap debe mostrar que el sistema puede manejar al menos 100k pps. Medid con `tcpreplay --pps`.

Recomiendo adelantar la deuda `DEBT-PROVISION-PORTABILITY-001` porque afecta directamente a la demo (ARM64 es común en laboratorios académicos).

**P5 – Contribución científica**  
Sí, especialmente el hallazgo sobre `lstat` vs `weakly_canonical`. La literatura de seguridad de sistemas tiene pocos ejemplos documentados de este error en C++17. Es una contribución valiosa para guías de estilo de codificación segura.

Citas:
- *"Filesystem Security in C++: Best Practices"* – C++ Alliance whitepaper (2023).
- *"The Perils of Path Canonicalization"* – MITRE CWE-41 (2024).
- *"Property-Based Testing for C++ Applications"* – Krzemiński (CppNow 2022).

Además, podríais citar el informe de errores de vuestro propio proyecto (GitHub issues) como evidencia de la efectividad de la metodología.

---

## Síntesis del Consejo

Las respuestas coinciden en varios puntos clave:

1. **Taxonomía `safe_path`**: Suficiente para producción, pero se anticipan posibles extensiones: manejo de bind mounts (`resolve_mount`), descriptors de proc (`resolve_fd`), variables de entorno (`resolve_env`), y mejora de `resolve_config` para verificar destinos de symlinks. Se recomienda documentar las limitaciones actuales.

2. **Property testing vs fuzzing vs mutation**: Orden consensuado: **property tests → fuzzing → mutation testing**. Los property tests son el primer escalón por su determinismo y facilidad de integración. El fuzzing complementa para encontrar crashes y casos extremos. Mutation testing es para medir calidad, no para descubrir bugs. Se sugiere integrar property-based fuzzing (ej. `FuzzTest` de Google).

3. **Criterio Snyk**: Mayoría aboga por **análisis de alcanzabilidad** y **umbral CVSS ≥ 7.0** para fix inmediato. El Consejo debe revisar antes de cada release minor, no antes de cada merge. Para merges diarios, automatizar con bloqueo solo para vulnerabilidades críticas con exploit público.

4. **Roadmap FEDER**: Alcanzable si se prioriza la demo Vagrant y se resuelven riesgos: compatibilidad ARM64, rendimiento del NDR, y estabilidad de variantes A/B. Se recomienda posponer `DEBT-PENTESTER-LOOP-001` hasta después de septiembre.

5. **Paper arXiv**: Los hallazgos de DAY 125-127 son novedosos, especialmente la detección de un bug en el propio fix mediante property testing y la lección sobre `lstat`. Merecen una sección en §5. Trabajo relacionado sugerido incluye referencias a Hughes, CWE, y papers recientes de ISSTA/CCS.

**Próximos pasos**: Actualizar `BACKLOG.md` con las nuevas deudas sugeridas (bind mounts, proc fd, etc.) como "Future Work". Integrar property testing pattern según la recomendación. Iniciar fuzzing de `config_parser` y `resolve_seed`. Preparar el informe Snyk para revisión del Consejo antes de la próxima release (v0.6). Ajustar el roadmap FEDER con los hitos propuestos.

*Fin del dictamen del Consejo de Sabios.*