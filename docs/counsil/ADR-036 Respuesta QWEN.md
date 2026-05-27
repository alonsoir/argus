# 🏛️ CONSEJO DE SABIOS — REVISIÓN ADR-036 (BORRADOR)
*Feedback directo, constructivo y centrado en viabilidad para ML Defender (aRGus NDR)*

---

## 🎯 Veredicto Ejecutivo

**APROBADO CON REFINAMIENTOS MAYORES.**

El ADR-036 identifica el problema correcto (*"funciona en mis tests" ≠ "demostrablemente correcto"*) y propone una arquitectura de verificación pragmática en dos fases. Sin embargo, **el alcance actual es demasiado ambicioso para un solo desarrollador** y corre el riesgo de convertirse en deuda técnica perpetua si no se prioriza con ruthless focus.

> *"La verificación formal no es un destino, es una dirección. Y la dirección correcta empieza con lo crítico, no con lo completo."*

---

## 🔍 Análisis Constructivo: Puntos Fuertes y Riesgos

### ✅ Lo que funciona (mantener)
| Propuesta | Por qué es sólida |
|-----------|------------------|
| **Enfoque en dos fases (C puro → C++20)** | Pragmático: Frama-C tiene soporte maduro para C, no para C++ |
| **Checklist adaptado de Hugo Vázquez** | Reutiliza conocimiento validado en dominio similar (firewalls) |
| **Priorización P0/P1/P2 por componente** | Permite progreso incremental sin bloqueo total |
| **Gate ASan+UBSan+Valgrind antes de formal** | Establece baseline de calidad mínima verificable |
| **Propiedades P1-P5 bien formuladas** | Son demostrables, accionables y relevantes para seguridad |

### ⚠️ Riesgos de complejidad (mitigar)
| Propuesta original | Riesgo | Mitigación propuesta |
|-------------------|--------|---------------------|
| **Verificar 10 componentes** | Alcance excesivo: 6-12 meses estimados × 10 = años de trabajo | **Limitar Fase A a 2 componentes P0**: `seed_client` + `crypto-transport`. El resto espera a Fase B o a contribuciones externas. |
| **Dos variantes con perfiles distintos** | Duplicación de esfuerzo: mantener dos baselines de verificación | **Fase A: solo Variante A**. Variante C queda como "research track" con documentación de diferencias, sin implementación paralela. |
| **Frama-C + clang-tidy + ASan + UBSan** | Toolchain fragmentada: cada herramienta requiere configuración, mantenimiento, expertise | **Unificar en Makefile target `make verify-P0`** que orqueste todas las herramientas con configuración pre-validada. |
| **Certificación IEC 62443 / Common Criteria** | Procesos de certificación requieren auditoría externa, documentación exhaustiva, costes elevados | **Documentar como "objetivo a largo plazo"**, no como requisito de cierre del ADR. La verificación formal es prerrequisito técnico, no sustituto de certificación. |

---

## ❓ Respuestas a Preguntas Abiertas (OQ-1 a OQ-4)

### OQ-1: ¿Frama-C/WP o CBMC para partes C puro?

**Veredicto:** **Frama-C/WP como herramienta principal**, con CBMC como complemento para propiedades específicas de seguridad.

**Justificación:** Frama-C tiene mejor integración con código C existente, soporte para anotaciones ACSL maduras, y comunidad activa en Europa (relevante para certificación IEC). CBMC es excelente para bounded model checking de propiedades específicas (ej. "nunca se accede fuera de bounds"), pero requiere reformular el código para BMC. Usar Frama-C para verificación general + CBMC para propiedades críticas de seguridad (P1, P2) ofrece el mejor balance.

**Riesgo si se ignora:** Elegir solo CBMC podría requerir refactorización significativa del código para hacerlo "BMC-friendly", añadiendo complejidad sin beneficio proporcional.

> 💡 *Proactivo:* Crear `docs/formal/tooling.md` con: (1) configuración pre-validada de Frama-C, (2) ejemplos de anotaciones ACSL para funciones críticas, (3) script `make verify-frama-c` reproducible.

---

### OQ-2: ¿Herramientas de verificación formal para C++20 en 2026?

**Veredicto:** **Limitarse a ASan + UBSan + contratos informales anotados para C++20 en Fase A**. No intentar verificación formal completa de C++20 todavía.

**Justificación:** En 2026, el soporte para verificación formal de C++20 sigue siendo experimental: herramientas como CPAchecker o SeaHorn tienen soporte limitado para características modernas de C++. Intentar forzar verificación formal sobre C++20 añadiría complejidad sin garantías de éxito. Los contratos informales anotados (`// @requires`, `// @ensures`) documentan la intención y permiten revisión humana + testing dirigido, que es suficiente para Fase A.

**Riesgo si se ignora:** Perseguir verificación formal completa de C++20 podría paralizar el progreso del ADR-036 durante meses sin entregar valor verificable.

> 💡 *Proactivo:* Documentar en `docs/formal/cpp20-limitations.md` qué características de C++20 son "verificación-hostile" y proponer subconjuntos verificables (ej. evitar templates complejos en funciones críticas).

---

### OQ-3: ¿Certificación realista para hospitales europeos?

**Veredicto:** **IEC 62443-4-2 (Security Level 2) como objetivo realista a medio plazo**. Common Criteria y ENS quedan como "stretch goals" a largo plazo.

**Justificación:** IEC 62443-4-2 está diseñada para componentes industriales en entornos OT/IT convergentes (como hospitales), tiene proceso de certificación más ágil que Common Criteria, y es reconocida en la UE. Common Criteria EAL4+ requiere años de esfuerzo y costes elevados (>100k€), justificable solo para productos comerciales a gran escala. ENS es específico de España y menos relevante para despliegue internacional.

**Riesgo si se ignora:** Apuntar a Common Criteria desde el inicio podría desviar recursos de la verificación técnica hacia documentación de certificación prematura, retrasando la entrega de valor real.

> 💡 *Proactivo:* Incluir en el paper una sección "Path to Certification" que documente cómo la verificación formal de ADR-036 es prerrequisito para IEC 62443-4-2, sin prometer certificación inmediata.

---

### OQ-4: ¿Justifica el esfuerzo mantener ambas variantes en roadmap de verificación?

**Veredicto:** **Variante C (seL4) como "research track" separado**, no como parte del roadmap principal de verificación.

**Justificación:** La Variante C tiene valor científico público (paper independiente sobre seL4 + NDR), pero su coste de verificación es órdenes de magnitud mayor debido a las proof obligations de seL4. Mantener ambas variantes en paralelo duplicaría esfuerzo sin beneficio proporcional para el objetivo principal (despliegue en hospitales). Separar Variante C como investigación permite avanzar en Variante A (práctica) mientras se explora Variante C (académica) sin bloquear ninguna.

**Riesgo si se ignora:** Intentar verificar ambas variantes simultáneamente podría agotar recursos sin completar ninguna, dejando el proyecto sin baseline verificable en producción.

> 💡 *Proactivo:* Crear rama `research/sel4-verification` separada de `feature/formal-verification`, con documentación clara de que son tracks independientes con diferentes criterios de éxito.

---

## 🛠️ Recomendaciones Técnicas Concretas

### 1. Reducir alcance de Fase A a 2 componentes P0
```diff
- seed_client, crypto-transport, plugin_loader, etcd-server, sniffer, ml-detector...
+ Fase A: seed_client + crypto-transport (únicos con código C puro crítico)
+ Fase B: plugin_loader (C++20 con contratos)
+ Resto: pendiente de contribuciones o Fase C
```

### 2. Unificar toolchain en Makefile
```makefile
# make verify-P0
verify-P0: verify-frama-c verify-asan verify-ubsan verify-valgrind
	@echo "✓ P0 components passed formal baseline checks"

verify-frama-c:
	frama-c -wp -wp-prover alt-ergo src/seed_client.c src/crypto_transport.c

verify-asan:
	./build-asan/test-all  # debe pasar sin errores

# ... etc
```

### 3. Documentar "escape hatches" para código no verificable
```markdown
## Código fuera de alcance de verificación formal

Las siguientes categorías quedan explícitamente fuera del scope de Fase A:
- Interfaz con librerías externas (libsodium, FAISS, ZeroMQ)
- Código de logging y telemetría
- Manejo de errores de E/S del sistema operativo

Justificación: Estas capas son "environment assumptions" (Checklist paso 6).
Su corrección se garantiza mediante testing + sandboxing (AppArmor/seL4),
no mediante verificación formal del código de aRGus.
```

### 4. Añadir criterio de "parada" para Fase A
```markdown
## Criterios de cierre de Fase A

Fase A se considera completada cuando:
- [ ] seed_client: propiedad P1 demostrada con Frama-C/WP
- [ ] crypto-transport: propiedad P3 demostrada con Frama-C/WP
- [ ] 0 warnings ASan/UBSan/Valgrind en componentes P0
- [ ] docs/formal/assumptions.md revisado y aprobado por Consejo

Si tras 3 meses no se han demostrado P1 y P3, re-evaluar enfoque o alcance.
```

---

## 📋 Checklist de Aprobación Condicionada

```markdown
- [x] Problema bien definido (demostración de corrección)
- [x] Checklist adaptado de fuente validada
- [x] Propiedades P1-P5 accionables y relevantes
- [ ] Reducir alcance Fase A a 2 componentes P0 (seed_client + crypto-transport)
- [ ] Variante C como research track separado, no roadmap principal
- [ ] IEC 62443-4-2 como objetivo realista, Common Criteria como stretch goal
- [ ] Unificar toolchain en `make verify-P0` reproducible
- [ ] Documentar código fuera de alcance + justificación
- [ ] Añadir criterio de parada temporal para Fase A (3 meses)
- [ ] Crear docs/formal/tooling.md con configuración pre-validada
```

---

## 🏁 Palabras Finales

Alonso:

ADR-036 representa un salto de ambición técnica admirable. Querer que aRGus no solo "funcione", sino que sea *demostrablemente correcto*, es la diferencia entre un proyecto útil y uno transformador.

Pero permítanme ser directo: **la verificación formal es un maratón, no un sprint**. Si intentáis verificar 10 componentes, 2 variantes y aspirar a certificación en un solo ADR, el riesgo no es fallar — es no empezar.

> *"Lo perfecto es enemigo de lo verificable."*

La propuesta refinada que os ofrecemos mantiene la visión, pero la ancla en lo ejecutable: empezar con lo crítico, demostrar valor temprano, y escalar desde ahí. Eso no es conformismo; es estrategia.

Aprobamos el ADR-036 con los refinamientos anteriores como condición. Una vez incorporados, proceded con Fase A: `seed_client` + `crypto-transport`. El Consejo estará atento a la primera propiedad demostrada.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 117** 🛡️