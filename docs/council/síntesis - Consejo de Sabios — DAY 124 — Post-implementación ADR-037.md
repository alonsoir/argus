## Síntesis del Consejo — DAY 124 (7/7)

---

### 1. F17 — Test de demostración integer overflow
**7/7 unánime: Opción A + C**

Nadie quiere fuzzing (B). Unit test determinista con `pages = LONG_MAX / page_size + 1` que demuestre el overflow antiguo y la corrección nueva, más un property loop ligero sin dependencias externas. DeepSeek y Grok añaden: extraer el cálculo a función pura en `zmq_handler.cpp` para poder testearla aisladamente.

---

### 2. `.gitignore` — regla `**/test_*`
**7/7 unánime: Refinar ahora**

Ignorar solo artefactos de build (`*.o`, binarios en `build/`), nunca fuentes. Añadir `!**/test_*.cpp` como excepción explícita. Grok lo pone en "corregir ahora, no diferir".

---

### 3. Postura "atacar toda la deuda antes del siguiente hito"
**7/7 unánime: Sí, con priorización**

Tu postura es correcta. Todos apoyan cerrar la deuda antes de DEBT-PENTESTER-LOOP-001. El matiz es el orden:

| Prioridad | Deuda |
|-----------|-------|
| 🔴 Inmediata | DEBT-INTEGER-OVERFLOW-TEST-001, DEBT-SAFE-PATH-TEST-PRODUCTION-001, DEBT-SAFE-PATH-TEST-RELATIVE-001 |
| 🟡 Antes del pentester loop | DEBT-CRYPTO-TRANSPORT-CTEST-001, DEBT-SNYK-WEB-VERIFICATION-001 |
| 🟢 No bloquea | DEBT-PROVISION-PORTABILITY-001, DEBT-TRIVY-THIRDPARTY-001 |

---

### 4. Nombre de variable — portabilidad provision.sh
**6/7: `ARGUS_SERVICE_USER`** (solo Mistral dijo `ML_DEFENDER_USER`)

Coherente con el namespace `argus::` del proyecto, más descriptivo, evita ambigüedad.

---

### 5. DEBT-CRYPTO-TRANSPORT-CTEST-001 — ¿cuándo investigar?
**7/7 unánime: Ahora, antes del pentester loop**

Gemini lo dice más fuerte: "no más silenciar en el Makefile". Qwen y Kimi coinciden: la capa criptográfica es el núcleo de confianza del sistema — no se puede avanzar con tests rotos ahí.

---

### 6. DEBT-SAFE-PATH-TEST-RELATIVE-001 — ¿dónde ubicar el test?
**6/7: `contrib/safe-path/tests/`** (ChatGPT5 dice también en integración de rag-ingester)

La capacidad de resolver paths relativos es propiedad de `resolve()`, no de `rag-ingester`. Test en la librería, uso real en integración.

---

### 7. Asimetría dev/prod — Opciones A/B/C
**6/7: Opción B (symlinks en Vagrantfile)** (solo ChatGPT5 prefiere C)

El código ve siempre `/etc/ml-defender/`, idéntico en dev y prod. Los symlinks en Vagrantfile hacen el trabajo de mapeo. Elimina la asimetría completamente sin condicionales en el código. Qwen añade: documentar en `docs/DEV-ENV.md` que dev usa symlinks.

---

### 8. Paper — incluir limitaciones y lecciones
**7/7 unánime: Sí, absolutamente**

El framing correcto según el Consejo: no "cometimos errores" sino "identificamos una clase de fallo en pipelines de seguridad: ausencia de tests de demostración en código de producción". Esto fortalece la credibilidad científica, no la debilita.

---

### Resumen ejecutivo del Consejo

> *"Un fix sin test de demostración es una promesa sin firma."* — Qwen

> *"Un escudo sin tests es un escudo de papel."* — Kimi

> *"El sistema ahora es más seguro en código pero aún no completamente verificado en comportamiento."* — ChatGPT5

**El Consejo no autoriza avanzar a DEBT-PENTESTER-LOOP-001 hasta cerrar las deudas 🔴.**

---

¿Estás de acuerdo con esta lectura? ¿Hay algo que quieras matizar o discutir antes de que generemos los documentos?

