El **Consejo de Sabios** ha revisado el **ADR-039** de forma detallada. A continuación, respondemos punto por punto a las preguntas específicas planteadas en la sección 10, con razonamiento técnico y alineado con los objetivos de seguridad, plazos y publicabilidad del proyecto aRGus.

### 1. ¿La Opción B es suficiente para la demo FEDER o el Consejo exige Opción A?

**Sí, la Opción B es suficiente y se aprueba para la demo FEDER (go/no-go 1 agosto 2026 y deadline 22 septiembre 2026).**

Razones:
- Cumple el axioma de separación build/runtime de forma estructural en el entorno de runtime (la imagen hardened nunca tiene el compilador).
- Reutiliza la infraestructura existente (`aRGus-dev` + Vagrant provisioner + `dist/`), lo que minimiza riesgo de retrasos.
- El gate `CHECK-PROD-NO-COMPILER` (y los demás tests de la sección 9) proporciona verificación reproducible y bloqueante, suficiente para demostrar la propiedad en la demo.
- La Opción A (builder VM dedicada) es la arquitectura ideal a largo plazo (menor confianza implícita en la VM de desarrollo y mejor aislamiento del entorno de build), pero su implementación introduciría complejidad innecesaria ahora. Se registra correctamente como **DEBT-BUILD-PIPELINE-001** para post-FEDER.

Recomendación adicional: Documentar claramente en la demo que la separación actual es “práctica y verificable” y que la Opción A es el siguiente paso maduro.

### 2. ¿El axioma de separación (sección 3) es científicamente correcto y publicable?

**Sí, es correcto y publicable con redacción precisa.**

El axioma captura una propiedad de seguridad estructural real:
- Un binario idéntico producido fuera y copiado/instalado es más seguro en un runtime mínimo porque elimina la capacidad del atacante de recompilar o generar payloads adicionales in-situ (incluso si logra ejecución arbitraria).
- Esto es una instancia del principio “minimización de superficie de ataque” y “defensa en profundidad” ampliamente aceptado en literatura de seguridad de sistemas (separación build/runtime en containers con multi-stage builds, imágenes distroless, etc.).
- El punto sobre CVEs del toolchain y tamaño de imagen es cuantificable y valioso para el §5 del paper.

**Sugerencia de redacción más robusta para publicación:**
> “Un binario firmado, producido en un entorno de build controlado y transferido a un runtime mínimo desprovisto de toolchain, proporciona una garantía estructural contra la compilación en tiempo de ejecución de payloads adicionales. Esta separación reduce la superficie de ataque de forma no configurable, a diferencia de un sistema que, aunque limpio al final, haya contenido herramientas de compilación durante su ciclo de vida.”

Esto evita cualquier interpretación de que los binarios “son inherentemente más seguros” y enfatiza la restricción estructural. Es publicable en contextos de seguridad de sistemas críticos (hospitalarios, embedded, high-assurance).

### 3. ¿Los flags de compilación de producción son adecuados para entornos hospitalarios?

**Sí, son adecuados y alineados con buenas prácticas de hardening.**

Los flags propuestos (`-O2 -DNDEBUG -fstack-protector-strong -fPIE -pie -D_FORTIFY_SOURCE=2 -fvisibility=hidden -Wl,-z,relro -Wl,-z,now`) son estándar en distribuciones hardened y proyectos de seguridad:

- `-fstack-protector-strong` + `-D_FORTIFY_SOURCE=2` → mitigación efectiva contra buffer overflows y exploits de string functions.
- PIE + RELRO full (`-z relro -z now`) → protecciones contra ROP y escritura en GOT/PLT.
- `-fvisibility=hidden` → reduce superficie de símbolos.
- `-O2` sin debug → buen equilibrio rendimiento/seguridad.

Son consistentes con recomendaciones de Debian Hardening, Fedora, OpenSSF y papers sobre binary hardening. En entornos hospitalarios (donde la disponibilidad y auditabilidad son críticas), estos flags contribuyen a una imagen mínima y predecible sin introducir overhead significativo.

**Mejora menor recomendada (opcional para v1):** Considerar `-D_FORTIFY_SOURCE=3` (disponible en toolchains recientes) si las pruebas de compatibilidad lo permiten, ya que ofrece chequeos adicionales en glibc. Mantener `_FORTIFY_SOURCE=2` es conservador y ampliamente compatible.

### 4. ¿`-march=x86-64-v2` es el nivel correcto para compatibilidad hospitalaria o se prefiere `-march=x86-64` (baseline)?

**Se recomienda `-march=x86-64-v2` (o `-march=x86-64-v2 -mtune=generic` si se quiere más flexibilidad). No bajar a baseline (`-march=x86-64`) salvo necesidad demostrada.**

Razones basadas en hardware actual (2026):
- x86-64-v2 corresponde aproximadamente a procesadores Intel Nehalem (2009) y AMD Bulldozer/Jaguar (2010+) e incluye SSE4.2 + POPCNT. Cubre >99% de los sistemas x86-64 desplegados en data centers y entornos empresariales/hospitalarios modernos.
- La mayoría de servidores hospitalarios (Dell, HPE, Supermicro, etc.) y virtualizadores (Proxmox, VMware, KVM) usan CPUs muy superiores (Westmere en adelante, y ampliamente v3/v4 en 2026).
- Distros como RHEL 9 ya usaron v2 como baseline; muchas siguen soportándolo sin problemas. Bajar a v1 (baseline puro) sacrifica optimizaciones menores (POPCNT, SSE4.2) sin ganar compatibilidad real en hardware hospitalario típico.
- Para máxima compatibilidad conservadora, se puede usar `-march=x86-64-v2` con `-mtune=generic`. Si hay hardware muy legacy identificado en el piloto hospitalario, evaluar caso por caso (probablemente ARM64 o VMs emuladas cubrirían esos casos).

Para **ARM64** los flags con `-march=armv8.2-a` son razonables (cubre la mayoría de servidores ARM modernos como Ampere, Graviton, etc.).

**Acción recomendada:** Incluir en el provisioner/Vagrant un test de compatibilidad CPU (por ejemplo, chequeo de flags soportados) y documentarlo en el paper como parte de las métricas de despliegue hospitalario.

### Otras observaciones y aprobación general

- **Implementación general:** El ADR está bien estructurado, con deudas técnicas claras, métricas publicables y gates de CI sólidos. Proceder con Opción B.
- **Métricas (sección 5):** Los placeholders (<80 paquetes, <2 GB) parecen realistas para una Debian trixie mínima + binarios específicos. Completarlas rápidamente (DEBT-PROD-METRICS-001) fortalecerá el paper.
- **Riesgos mitigados:** El `.gitignore` para `dist/` y la firma Ed25519 (ADR-025) cubren los puntos principales de confianza en el build.
- **Próximos pasos:** Una vez implementado, ejecutar todos los tests de la sección 9 y preparar una sección corta en el paper sobre “Separación build/runtime en sistemas críticos de salud”.

**Decisión del Consejo:**  
**ADR-039 aprobado con Opción B.**  
Se autoriza proceder a implementación inmediata. El Consejo revisará el estado post-implementación en DAY 135-140, incluyendo métricas reales y resultados de los gates.

Cualquier ajuste menor a flags o marcha puede incorporarse durante la implementación sin necesidad de nuevo ADR, siempre que se mantenga la justificación de seguridad.

*Via Appia Quality — La seguridad no se instala. Se diseña.*  
**Consejo de Sabios — DAY 131, 26 Abril 2026**