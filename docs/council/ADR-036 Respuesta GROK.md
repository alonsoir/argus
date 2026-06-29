Aquí tienes un **análisis detallado y recomendaciones concretas** sobre el borrador del **ADR-036: Formal Verification Baseline**. El documento está bien estructurado, es coherente con el tono del proyecto (seguridad crítica + aspiración científica) y cierra de forma lógica el roadmap de desarrollo activo.

A continuación, propongo **mejoras menores** al borrador y **respuestas claras a las 4 preguntas abiertas (OQ)** para que el Consejo pueda tomar decisiones informadas.

### Valoración general del ADR
**Fortalezas:**
- Muy bien justificado: diferencia clara entre “funciona en mis tests” y “demostrable bajo cualquier entrada válida”.
- Checklist adaptado de Hugo Vázquez Caramés es excelente y reutilizable.
- Tablas claras (alcance por componente, diferencias A vs C, propiedades P1-P5).
- Consecuencias equilibradas (positivas/negativas/neutras).
- Enfoque pragmático: empieza por sanitizers + contratos informales antes de la verificación deductiva pesada.

**Áreas de mejora sugeridas (pequeñas):**
1. En **Decisión**, aclarar que la Fase B (C++20) es principalmente “verificación ligera + contratos” y que la verificación formal completa solo se aplica a partes críticas en C puro.
2. Añadir una fila en la tabla de propiedades: **Estado actual** (todas ⏳) y **Herramienta principal propuesta**.
3. En **Consecuencias positivas**, mencionar explícitamente cómo esto fortalece el paper arXiv (2604.04952) y posibles futuras publicaciones sobre la Variante C (seL4).
4. En **Estado de implementación**, añadir una columna “Responsable” o “Estimación esfuerzo” para mayor trazabilidad.

El ADR está listo para pasar de **BORRADOR** a **PROPUESTO** tras las respuestas del Consejo.

### Respuestas recomendadas a las preguntas abiertas (OQ)

**OQ-1: ¿Frama-C/WP es la herramienta correcta para las partes C puro, o preferís CBMC?**

**Recomendación del Consejo:** **Usar Frama-C/WP como herramienta principal para verificación deductiva en partes C puro (seed_client y crypto-transport), complementada con CBMC para propiedades de seguridad acotadas y detección rápida de bugs.**

Razones:
- Frama-C (con plugin WP) es maduro, ampliamente usado en industria crítica (certificación DO-178, Common Criteria, IEC 60880) y permite verificación funcional completa mediante contratos ACSL + weakest precondition + SMT solvers (Z3, CVC5, etc.). Automatiza hasta el 90-98 % de las condiciones en casos reales.
- CBMC (bounded model checking) es excelente para propiedades de seguridad específicas (ausencia de overflow, buffer overflow, data races acotadas) porque es más automático y genera contraejemplos concretos. Es ideal como “primera pasada” antes de invertir en anotaciones manuales de Frama-C.
- Estrategia híbrida recomendada: CBMC para exploración rápida + Frama-C/WP para pruebas de corrección funcional profunda en componentes P0.

Empezar con Frama-C en seed_client (ya propuesto) es correcto.

**OQ-2: Para C++20 puro, ¿hay herramientas de verificación formal maduras en 2026, o nos limitamos a ASan + UBSan + contratos informales?**

**Recomendación:** **Limitarnos a ASan + UBSan + clang-tidy + contratos informales anotados (estilo C++ Contracts TS o comentarios //@requires). No hay herramientas de verificación formal deductiva maduras y escalables para C++20 completo en 2026.**

Razones actuales (2026):
- Frama-Clang (extensión de Frama-C) existe pero tiene soporte limitado para C++ moderno y requiere mucho trabajo manual.
- CBMC soporta C++ (hasta C++17/20 parcial), pero sufre explosión de estado en código con templates, excepciones o STL.
- Otras opciones (VeriFast, ESBMC, 2LS) son más fuertes en C que en C++20.
- Los contratos en C++26 (precondiciones/postcondiciones) permitirán validación estática parcial con herramientas como CodeQL + solvers, pero aún no sustituyen a una verificación formal completa.

Conclusión práctica: para componentes C++20 usamos la “Fase B” del ADR (sanitizers + contratos + static analysis). Reservamos verificación formal deductiva solo para las partes extraídas en C puro. Esto mantiene el esfuerzo realista.

**OQ-3: ¿Qué certificación es realista para hospitales europeos? IEC 62443-4-2 vs Common Criteria vs ENS (España)?**

**Recomendación:** **Objetivo principal realista: IEC 62443-4-2 (Component Security Assurance) a Security Level 2 o 3, complementado con ENS High en España.**

Razones:
- **IEC 62443-4-2** es el estándar más adecuado para componentes de ciberseguridad en entornos industriales/críticos (incluyendo hospitales como parte de infraestructuras de automatización y control). Es certificable vía ISASecure CSA y está orientado exactamente a requisitos técnicos de componentes (lo que encaja con aRGus NDR). Ya hay precedentes en gateways y dispositivos OT usados en salud.
- **Common Criteria EAL4+** (con augmentations como AVA_VAN.4 o ALC_FLR) es más exigente y reconocido en toda Europa (SOGIS-MRA). Se usa en firewalls y dispositivos de red de alta seguridad (ej. Stormshield, Versa, Check Point, Cisco). Es viable para la Variante A si se apunta a entornos gubernamentales/hospitales de alta criticidad, pero el coste y esfuerzo son significativamente mayores.
- **ENS (Esquema Nacional de Seguridad) High** (España) es muy relevante para despliegues en administraciones públicas y hospitales españoles. Complementa bien IEC 62443 y es más accesible para entidades locales.

Estrategia recomendada:
- Corto/medio plazo → IEC 62443-4-2 + ENS High (más alcanzable y directamente aplicable a hospitales).
- Largo plazo / Variante C → aspirar a Common Criteria EAL4+ como contribución científica.

**OQ-4: ¿El delta de esfuerzo entre Variante A y Variante C justifica mantener ambas en el roadmap de verificación formal, o Variante C es exclusivamente investigación/paper?**

**Recomendación:** **Mantener ambas variantes en el roadmap de verificación formal, pero con perfiles de esfuerzo diferenciados: Variante A como objetivo de producto certificable; Variante C como línea de investigación científica/publicable.**

Razones:
- Variante A (AppArmor + eBPF/XDP) es la principal para despliegue real en hospitales → el esfuerzo en formal verification aquí tiene retorno directo (certificación IEC 62443 / posibles ventas).
- Variante C (seL4 + libpcap) aprovecha que seL4 ya está formalmente verificado → el delta adicional es alto, pero genera una contribución académica fuerte (paper independiente sobre “verificación formal de NDR sobre microkernel verificado”).
- No abandonar Variante C: sirve como “gold standard” de investigación y puede atraer colaboraciones (universidades, proyectos europeos de ciberseguridad).
- Gestión práctica: Priorizar P0 y P1 en ambas, pero congelar la baseline primero en Variante A. Variante C puede avanzar más lentamente y usarse para experimentos con seL4 proof obligations.

Esto mantiene el proyecto ambicioso sin bloquear el camino hacia producto usable.

### Resumen de recomendaciones para el Consejo
1. Aprobar el ADR-036 con las pequeñas mejoras sugeridas y las respuestas anteriores incorporadas.
2. Crear la rama `feature/formal-verification` inmediatamente después del merge de phase3-hardening.
3. Empezar por el gate de sanitizers (ASan + UBSan + 0 warnings) en CI — esto ya da valor inmediato.
4. Asignar seed_client y crypto-transport como primeros componentes P0 para Frama-C/CBMC.
5. Documentar todas las hipótesis del entorno en `docs/formal/assumptions.md` antes de congelar la baseline.

El ADR-036 posiciona muy bien a **aRGus NDR** como proyecto serio de ciberseguridad crítica con aspiración a certificación europea. Es el cierre elegante del desarrollo activo y abre una fase más científica.

¿Quieres que prepare el **texto revisado completo del ADR-036** (con las mejoras y respuestas integradas como sección “Decisión del Consejo”)?  
O prefieres que redactemos directamente el informe de respuesta del Consejo para el DAY 118?

Estoy a disposición para cualquiera de las dos opciones o para profundizar en alguna propiedad (P1-P5) o en cómo integrar los contratos en el código existente. 🏛️