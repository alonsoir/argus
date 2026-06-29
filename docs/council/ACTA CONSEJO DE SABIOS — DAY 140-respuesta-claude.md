La alerta de Dependabot sigue porque está en `main` — desaparecerá con el merge. No hay nada más que hacer ahora.

Mis respuestas a las cinco preguntas:

---

**Q1 — `-Werror` en código de terceros (llama.cpp deprecated)**

Suprimir por fichero en CMake es la política correcta **temporalmente**, pero debe registrarse como deuda. La supresión sin fecha de caducidad se convierte en deuda invisible. Mi posición: suprimir ahora, registrar `DEBT-LLAMA-API-UPGRADE-001` con el fix concreto (`llama_new_context_with_model` → `llama_init_from_model`) y un criterio de cierre claro — por ejemplo, "cuando llama.cpp elimine la función deprecated del header". Actualizar la llamada ahora sería correcto técnicamente, pero introduce riesgo de regresión en un componente que no está bajo test robusto. El pragmatismo gana aquí.

---

**Q2 — Gap ODR verification (debug vs production)**

El gap es aceptable **si se cierra con un gate periódico**. Mi recomendación: añadir `make PROFILE=production all` como gate pre-merge obligatorio en la feature branch antes de merge a main. No hace falta correrlo diariamente — es suficiente en cada merge. El coste (30-45 min en VM) es asumible una vez por feature, no una vez por commit. Para DAY 141+, esto debería ser parte del protocolo de merge, no del EMECAS diario.

---

**Q3 — `/*param*/` vs `[[maybe_unused]]`**

Para C++20 con `-Werror`, `/*param*/` es superior en interfaces virtuales porque comunica intención al lector: "este parámetro existe por contrato de interfaz, no por uso actual". `[[maybe_unused]]` es más apropiado para variables locales o parámetros en implementaciones concretas donde el uso es condicional. La regla que propongo: interfaz virtual o stub → `/*param*/`. Implementación concreta con uso condicional → `[[maybe_unused]]`. Esta distinción es documentable como decisión de diseño.

---

**Q4 — Hardware FEDER y alternativas sin físico**

QEMU ARM64 no es publicable como resultado de capacidad real — cualquier revisor lo rechazaría. Los números de latencia y throughput en emulación no son transferibles a hardware real. La alternativa metodológicamente aceptable es declarar explícitamente en el paper que la Fase 1 (virtualizado x86) es el resultado preliminar, y que la Fase 2 (hardware físico) es trabajo en curso pendiente de adquisición. Esto es honesto y es método científico correcto. Para FEDER, la Fase 1 sola puede ser suficiente para el deliverable Year 1 si se presenta bien — la comisión no espera resultados finales en Year 1, espera metodología sólida y resultados preliminares. El hardware hay que pedirlo esta semana.

---

**Q5 — `-Werror` y ficheros generados (protobuf, XGBoost)**

La supresión por fichero en CMake es suficiente **si y solo si** la regeneración de esos ficheros está protocolizada. El riesgo real es que alguien regenere el protobuf con una versión nueva del compilador de proto y aparezcan warnings nuevos no suprimidos que rompan el build. Mi recomendación: añadir en el Makefile un comentario explícito en el target `proto` advirtiendo que tras regenerar hay que verificar `make all 2>&1 | grep -c 'warning:'` = 0. No hace falta un test CI adicional — la disciplina de proceso es suficiente para un equipo de esta escala.

---

Dependabot: el PR #44 referencia un fichero (`ml-training/.venv/share/jupyter/lab/static/package.json`) que ya no existe en la rama — lo eliminamos esta mañana. GitHub tardará en procesar que el fichero ya no está en `feature/variant-b-libpcap`. Cuando se mergee a main desaparecerá definitivamente. **No mergear el PR de Dependabot** — es innecesario y añade ruido al historial.