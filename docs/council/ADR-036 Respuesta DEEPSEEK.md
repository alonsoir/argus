## Análisis del Consejo sobre ADR-036: Formal Verification Baseline

El borrador presentado por Alonso Isidoro Román es **técnicamente sólido y ambicioso**, pero requiere que el Consejo tome decisiones estratégicas sobre el alcance, las herramientas y los objetivos de certificación. A continuación, respondo punto por punto a las preguntas abiertas y ofrezco una evaluación global.

---

### OQ-1: ¿Frama-C/WP o CBMC para las partes C puro?

**Contexto:**  
Los componentes C puro en aRGus NDR son pequeños y bien delimitados: `seed_client` (lectura de seed.bin, validación de longitud) y `crypto-transport` (operaciones criptográficas con libsodium). No hay algoritmos complejos ni aritmética de punteros agresiva.

**Comparativa:**

| Criterio | Frama-C/WP | CBMC |
|----------|------------|------|
| **Madurez** | Muy alta (desde 2008, usado en industria aeroespacial) | Alta (Amazon, ARM, verificaciones de seguridad) |
| **Curva de aprendizaje** | Media-alta (requiere ACSL, lógica de Hoare) | Media (assertions, bounded loops) |
| **Capacidad de prueba** | Demostración deductiva (completa dentro del modelo) | Model checking acotado (busca contraejemplos hasta un límite) |
| **Manejo de bucles** | Necesita invariantes explícitos | Desenrolla hasta un límite (puede perderse bugs más allá) |
| **Integración con libsodium** | Difícil (funciones externas no verificadas) | Similar (modelos stub) |
| **Automatización CI** | Posible pero lenta (minutos por función) | Más rápida para propiedades acotadas |

**Recomendación del Consejo:**  
✅ **Usar CBMC para la fase inicial de baseline** por las siguientes razones:

1. **Propiedades de seguridad concretas** – Las que se quieren demostrar (P1: ausencia de buffer overflow, P3: invariante seed) son **propiedades de seguridad acotadas**, no demostraciones de corrección funcional completa. CBMC es excelente para esto.
2. **Menor fricción** – CBMC permite añadir `assert` y `__CPROVER_assume` directamente en el código C, sin aprender ACSL desde cero.
3. **Tiempo de ejecución** – Para `seed_client` (<500 líneas), CBMC termina en segundos; Frama-C/WP puede tardar minutos y requiere más anotaciones.
4. **Compatibilidad con C++20** – CBMC tiene soporte experimental para C++, pero mejor ceñirse a C puro.

**No obstante**, si el objetivo a largo plazo es **certificación IEC 62443 o Common Criteria**, Frama-C/WP tiene más trayectoria en la industria de componentes críticos. Propongo un enfoque **dual**:

- **Fase 1 (baseline):** CBMC para P1, P2, P4 (propiedades de memoria y razas).
- **Fase 2 (certificación):** Frama-C/WP para los componentes que requieran demostración deductiva completa.

**Decisión para el ADR:**  
Especificar **CBMC como herramienta principal** para las partes C puro, y mencionar Frama-C/WP como opción de respaldo si se busca una certificación más estricta. Añadir una nota: "El checklist de Hugo Vázquez Caramés está pensado para Frama-C, pero se adapta a CBMC sin cambios significativos".

---

### OQ-2: Herramientas de verificación formal para C++20 en 2026

**Situación actual (abril 2026):**  
El ecosistema de verificación formal para C++ moderno sigue siendo inmaduro. Herramientas como:
- **VeriFast** (soporte limitado a un subconjunto de C++11)
- **SMACK** (traduce LLVM a Boogie, pero con problemas con excepciones y RTTI)
- **SeaHorn** (similar, basado en LLVM, pero sin soporte completo de la STL)
- **Clang Static Analyzer** (no es formal, solo análisis simbólico acotado)

Ninguna ofrece garantías deductivas para C++20 con templates, lambdas, y move semantics.

**Recomendación del Consejo:**  
✅ **Limitarse a ASan + UBSan + contratos informales anotados para C++20**, exactamente como propone el borrador. Esto es realista y valioso.

**Ampliación posible:**  
Para componentes C++ muy críticos (ej: `plugin_loader`), se puede **reescribir una versión simplificada en C puro** específicamente para verificación formal, manteniendo el original C++ para producción. Esto ya se hace en sistemas de alta integridad (ej: seL4, Linux kernel). El ADR podría mencionar esta opción como "plan B".

**Conclusión:**  
El borrador es correcto al no prometer verificación formal completa para C++20. Mantener la redacción actual, pero añadir una nota: "Se revisará el estado del arte en Q4 2026; si surge una herramienta madura, se extiende el alcance".

---

### OQ-3: ¿Qué certificación es realista para hospitales europeos?

**Análisis del dominio:**  
Los hospitales europeos (especialmente bajo la Directiva NIS2 y el Reglamento de Ciberseguridad de Productos (EU) 2024/2847) exigen diferentes niveles según el rol del dispositivo:

- **Dispositivo médico (regulación MDR):** Requiere evaluación por organismo notificado. El software de red (NDR) no es un dispositivo médico a menos que monitorice directamente equipos médicos. aRGus NDR probablemente no entra.
- **Sistema de control industrial (IEC 62443):** Aplicable si se despliega en infraestructuras críticas de hospitales (HVAC, energía, gases medicinales). El checklist de verificación formal ayuda a cumplir los requisitos de SL‑A (Security Level A) o SL‑2.
- **Common Criteria (ISO/IEC 15408):** Muy costoso (200k-500k €) y lento (12-18 meses). Solo justificable si un cliente lo exige explícitamente.
- **ENS (Esquema Nacional de Seguridad, España):** Para despliegues en administración pública. Es más ligero que Common Criteria y acepta análisis estático + pruebas de penetración. La verificación formal no es obligatoria pero suma puntos.

**Recomendación realista:**  
✅ **IEC 62443-4-2 (Security Level 2) como objetivo principal.**
- Es alcanzable con la baseline de verificación formal + hardening ya implementado (AppArmor, tests invariantes).
- Relevante para hospitales (sistemas de automatización, redes OT).
- Coste moderado (unos 50k € en consultoría + documentación).

**Para Variante C (seL4):**
- Puede aspirar a **Common Criteria EAL4+** como proyecto de investigación, pero no como producto comercial inmediato.
- El ADR debería separar claramente: "La Variante C es experimental; la certificación no está en el roadmap de producto hasta 2028".

**Acción sugerida:**  
Añadir una sección "Objetivo de certificación" en el ADR, con:
- **Corto plazo (2026):** IEC 62443-4-2 SL2 para Variante A.
- **Largo plazo (2027+):** Evaluación de ENS para despliegues públicos.

---

### OQ-4: Delta de esfuerzo entre Variante A y Variante C – ¿mantener ambas?

**Estimación de esfuerzo (en meses-hombre):**

| Actividad | Variante A | Variante C | Diferencia |
|-----------|------------|------------|------------|
| ASan/UBSan/Valgrind gate | 1 mes | 1 mes | igual |
| Contratos anotados (C++20) | 2 meses | 2 meses | igual |
| CBMC para seed_client y crypto-transport | 1 mes | 1 mes | igual |
| Verificación del sniffer (eBPF) | 3 meses (verificación de programas eBPF con bpf-verifier + CBMC) | 2 meses (libpcap, solo UBSan + contratos) | -1 mes para C |
| Adaptación a seL4 (capabilities, IPC) | N/A | 4 meses | +4 |
| Documentación de hipótesis para microkernel | 1 mes | 3 meses | +2 |
| Total estimado | **8 meses** | **13 meses** | **+5 meses** |

**Análisis:**  
La Variante C añade **~5 meses de trabajo en solitario** (o 2.5 meses con dos personas). Esto es significativo pero no inviable.

**Recomendación del Consejo:**  
✅ **Mantener ambas variantes en el roadmap de verificación formal, pero con un orden claro:**

1. **Primero completar Variante A** (8 meses) – porque es la que se desplegará en hospitales reales a corto plazo.
2. **Luego, como proyecto de investigación/paper**, la Variante C.
    - Se puede publicar un artículo específico sobre "Verificación formal de un NDR sobre seL4" en una conferencia como EMSOFT o CPS-IoT Week.
    - No bloquear el lanzamiento comercial de aRGus NDR esperando a la Variante C.

**Ajuste al ADR:**  
Cambiar la tabla "Diferencias entre Variante A y Variante C" para reflejar que la Variante C es **secundaria y posterior**. Añadir una nota: "El commit `v-formal-baseline` se referirá únicamente a la Variante A; la Variante C tendrá su propio baseline en una rama separada `feature/sel4-formal`".

---

## Observaciones adicionales sobre el ADR

### Puntos fuertes
- ✅ Adaptación inteligente del checklist de Hugo Vázquez Caramés a un proyecto real.
- ✅ Reconocimiento honesto de las limitaciones de C++20.
- ✅ Separación clara de propiedades a demostrar (P1-P5).
- ✅ Consideración de costes y tiempos (aunque se puede afinar).

### Aspectos a mejorar

1. **Falta una estimación de esfuerzo en días/persona** – El Consejo necesita saber si es factible con un solo desarrollador (Alonso) o requiere contratar ayuda. Sugiero añadir una tabla resumen con la estimación anterior.

2. **Gate ASan + UBSan ya existe en CI** – El borrador dice "⏳ feature/formal-verification", pero en DAY 117 ya se ejecuta `make test-all` con UBSan y ASan (según el informe diario). Corregir el estado a ✅.

3. **¿Qué pasa con los plugins XGBoost?** – El ADR-026 está en borrador. Si se añaden plugins en C++ que cargan modelos de ML, también deberían pasar el mismo nivel de verificación (al menos UBSan + contratos). Incluir una nota en el alcance.

4. **Propiedad P5 ("terminación del pipeline bajo carga")** – Demostrar terminación acotada en un sistema de red es muy difícil (depende del tráfico). Sugiero cambiarla por una propiedad más realista: "No hay deadlocks en el pipeline para cualquier tasa de entrada ≤ 1 Gbps". Esto sí es verificable con modelos de concurrencia (CBMC puede explorar interleavings).

5. **Mencionar `-D_GLIBCXX_DEBUG`** – En C++20, la debug mode de libstdc++ detecta muchos UB en contenedores. Añadir como chequeo opcional.

---

## Respuesta consolidada para el Consejo (a incluir en el acta)

| Pregunta | Decisión del Consejo |
|----------|----------------------|
| **OQ-1** | Usar **CBMC** para C puro; Frama-C/WP queda como opción para certificaciones más exigentes. |
| **OQ-2** | Confirmar que para C++20 solo se exigen **ASan + UBSan + contratos informales**. No hay herramientas maduras en 2026. |
| **OQ-3** | Objetivo realista: **IEC 62443-4-2 SL2** para Variante A. Common Criteria solo para Variante C como investigación. |
| **OQ-4** | Mantener ambas variantes, pero **priorizar Variante A** (8 meses). La Variante C se desarrolla después como proyecto académico. |

### Veredicto final sobre el ADR-036

**Aprobado como borrador**, con las siguientes modificaciones obligatorias antes de la aceptación final:

1. Añadir estimación de esfuerzo (meses) y recursos necesarios.
2. Cambiar P5 por "ausencia de deadlocks bajo carga".
3. Corregir el estado de ASan/UBSan en CI.
4. Incluir una sección "Plan de certificación" con IEC 62443 como meta.
5. Especificar que la baseline se aplica primero a la Variante A; la Variante C será un hito separado.

Una vez incorporados estos cambios, el Consejo puede aprobar el ADR-036 como **ACEptado** y asignar la `feature/formal-verification` con una duración prevista de **8 meses** (inicio: mayo 2026, finalización: diciembre 2026).

El trabajo realizado hasta ahora (DAY 117) ha dejado el código en un estado excelente para comenzar la verificación formal. Enhorabuena al equipo.

*— Asesor técnico para el Consejo de Sabios*