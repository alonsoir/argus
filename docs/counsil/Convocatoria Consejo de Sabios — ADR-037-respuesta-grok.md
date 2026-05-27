**MODELO: Grok (Consejo de Sabios — DAY 123)**

**P1:** ACEPTO `weakly_canonical` para los casos de escritura.  
`weakly_canonical` es la elección correcta y más segura en este contexto. `canonical` fallaría legítimamente en paths de escritura a ficheros aún inexistentes (común en configs o seeds generadas en provisioning), forzando workarounds frágiles que aumentarían la superficie de ataque o complejidad. La implementación propuesta (`resolve` + `resolve_writable` con comprobación explícita del directorio padre) mitiga los riesgos de symlinks y `..` sin introducir TOCTOU innecesario en el flujo principal. Es consistente con recomendaciones estándar de sanitización en C++ para prevenir CWE-23 (path traversal). No propongo alternativa: esta es mínima, zero-dependencias y suficiente para la superficie actual.

**P2:** ACEPTO granularidad por componente.  
Más granularidad = más restricción = menor superficie de ataque. Usar prefijos específicos (`/etc/ml-defender/keys/` para material criptográfico, `/etc/ml-defender/` para configs generales) es preferible a un prefijo único `/etc/ml-defender/`. La semilla ChaCha20 merece aislamiento extra; un traversal que escape a `/keys/` es mucho más crítico que a un config genérico. El coste de mantenimiento es bajo (unos pocos strings en llamadas a `resolve()`) y el beneficio en defensa en profundidad es alto, especialmente bajo AppArmor. Un prefijo único simplificaría, pero relajaría la política precisamente donde más importa.

**P3:** MISMO estándar para contrib/tools.  
Aplica el mismo `safe_path::resolve()` (con prefijo `/shared/` o `/vagrant/` según entorno). Aunque contrib/tools no corran en producción ni bajo AppArmor, aplicar el estándar uniformemente:
- Forma hábito defensivo en todo el equipo.
- Evita bifurcación de políticas (“aquí sí, allá no”).
- Simplifica code review y futuro refactoring (si una tool se promociona a producción).  
  El riesgo operacional es bajo, pero el coste de aplicar el header-only es prácticamente cero. Documentad la diferencia de riesgo, pero no relajéis el enforcer.

**P4:** ACEPTO FP — no modificar código.  
El análisis propio es correcto: `n` proviene de `read()` con buffer fijo de 4096 bytes, por lo que `ptr < buf + n` nunca puede desbordar en la práctica (el puntero `ptr` avanza dentro del buffer acotado). Snyk no traza el origen de `n` hasta su bound real, generando un falso positivo clásico en análisis estático. No veo vector de ataque viable aquí (no hay input externo arbitrario que controle `n` más allá del tamaño del read). Documentad la justificación en el ADR (incluyendo el bound `BUF_SIZE`) y cerrad el finding sin cambio de código. Segunda pasada Snyk post-fix debe confirmar 0 findings reales en producción.

**OBSERVACIONES ADICIONALES:**
- La solución `safe_path` es excelente: header-only, cero dependencias externas, rechazo explícito con mensaje claro, y `resolve_writable` añade capa extra para escritura. Refuerza el principio “superficie mínima es la superficie más segura”.
- Añadid como regla permanente en code review: “Cualquier nuevo `std::ifstream`/`ofstream` con input no-constante debe pasar por `argus::safe_path::resolve()`”.
- El fix del integer overflow (cast a `int64_t`) es correcto y suficiente.
- Este ADR cierra limpiamente los 17 findings de Snyk sin inflar la superficie de ataque. Una vez mergeado, ADR-036 (Formal Verification Baseline) puede avanzar sin bloqueo.
- Recomendación menor: en `resolve()`, normalizad también el `allowed_prefix` con `weakly_canonical` para consistencia (evita discrepancias de trailing slash).

Veredicto global: **APROBADO**. Merge a `feature/adr037-snyk-hardening` autorizado una vez implementados los pasos 1-6 del plan y tests PASSED. Esto endurece el pipeline de forma pragmática y mantiene **Via Appia Quality**: seguro, mantenible y pequeño.

*Via Appia Quality — la superficie mínima es la superficie más segura.*

Consejo listo para el siguiente paso (ADR-036 o cierre de DEBT-PRECISION-GATE-001 residual). ¿Queréis ayuda revisando el `test_safe_path.cpp` o el párrafo de documentación de FPs en el ADR?

**MODELO: Grok (Consejo de Sabios — DAY 123)**

**P1:** ACEPTO `weakly_canonical` para los casos de escritura.  
`weakly_canonical` es la opción correcta y más práctica. `canonical` lanzaría excepción en paths de escritura a ficheros que aún no existen (caso común en generación de seeds, configs o outputs durante provisioning). La función `resolve_writable()` ya añade la comprobación explícita del directorio padre, lo que mitiga riesgos adicionales sin introducir TOCTOU innecesario en el flujo principal. Es consistente con el principio de minimización de superficie y resuelve el problema real de path traversal (CWE-23) sin complicaciones artificiales. No propongo alternativa: esta es limpia, zero-dependencias y suficiente.

**P2:** ACEPTO granularidad por componente.  
La granularidad propuesta es correcta y preferible.
- `/etc/ml-defender/keys/` para material criptográfico (seed ChaCha20) ofrece aislamiento extra donde más importa.
- `/etc/ml-defender/` para configs generales es suficiente para el resto.

Un prefijo único `/etc/ml-defender/` simplificaría el código, pero reduciría la defensa en profundidad precisamente en el punto más sensible (la seed). El coste de mantenimiento es mínimo (solo strings en las llamadas a `resolve()`), mientras que el beneficio en seguridad es tangible bajo AppArmor. Más restricción = mejor.

**P3:** MISMO estándar para contrib/tools.  
Aplica el **mismo estándar** (`safe_path::resolve()` con prefijo `/shared/` o `/vagrant/`).  
Aunque contrib y tools no corran en producción ni bajo AppArmor, aplicar la misma política:
- Forma hábito defensivo en todo el equipo.
- Evita bifurcación de reglas (“aquí enforzamos, allá no”).
- Facilita futuras promociones de código de contrib a producción.  
  El overhead es prácticamente nulo (header-only). Documentad la diferencia de riesgo operacional, pero no relajéis el enforcer.

**P4:** ACEPTO FP — no modificar código.  
Acepto el veredicto de falso positivo en los findings inotify (F15/F16).  
`n` proviene directamente de `read()` con un buffer fijo de `BUF_SIZE = 4096`, por lo que el puntero `ptr` nunca puede avanzar más allá del buffer asignado. Snyk no realiza el rastreo completo del valor de `n` hasta su bound real, generando un warning clásico de análisis estático. No identifico ningún vector de ataque viable que invalide este análisis (no hay input externo arbitrario capaz de controlar `n` más allá del tamaño devuelto por `read()`).

Documentad la justificación en el ADR (incluyendo el bound explícito de `BUF_SIZE`) y cerrad el finding sin tocar el código. La segunda pasada de Snyk debe confirmar 0 findings reales en la superficie de producción.

**OBSERVACIONES ADICIONALES:**
- La utilidad `safe_path` es una solución elegante y alineada con **Via Appia Quality**: header-only, cero dependencias externas, rechazo explícito con mensaje claro y `resolve_writable` como capa adicional. Rechazar correctamente las sugerencias de Snyk (librerías pesadas y fuera de contexto) fue la decisión correcta.
- Añadid como regla permanente en el checklist de code review: “Cualquier nuevo uso de `std::ifstream` / `std::ofstream` con input no-constante en código de producción **debe** pasar por `argus::safe_path::resolve()` o `resolve_writable()` según corresponda.”
- El fix del integer overflow con casts explícitos a `int64_t` es correcto y suficiente.
- Una vez implementados los pasos 1-6 del plan y pasados los tests, este ADR puede mergearse sin bloqueos. ADR-036 (Formal Verification Baseline) queda desbloqueado.

**Veredicto global:** **APROBADO**.  
Merge a `feature/adr037-snyk-hardening` autorizado una vez completado el plan de implementación y verificado que la segunda pasada de Snyk muestre 0 findings en código de producción.

Esto endurece la superficie de ataque de forma pragmática, mantiene el pipeline pequeño y seguro, y protege realmente los entornos críticos (hospitales, escuelas, municipios) para los que se diseñó aRGus.

*Via Appia Quality — la superficie mínima es la superficie más segura.*

Consejo listo. ¿Quieres que revise el `test_safe_path.cpp` propuesto, ayude a redactar la documentación de los FPs en el ADR, o pasamos directamente al siguiente paso (ADR-036)?

