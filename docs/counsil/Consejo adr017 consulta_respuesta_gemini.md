## Gemini (Google) — Consulta #1 (ADR-017)

Alonso, como miembro del **Consejo de Sabios**, he analizado la arquitectura de interfaces para el sistema de plugins. Estamos en un punto de inflexión: el paso de un sistema estático a un **ecosistema extensible**. Mi enfoque será estrictamente ingenieril, priorizando la **seguridad de tipos**, el **rendimiento en el hot-path** y la **viabilidad en hardware restringido**.

Aquí mis votos y razonamientos para las 5 preguntas abiertas:

---

### PREGUNTA 1 — Contextos tipados por componente
**Recomendación:** **Opción A (Contextos específicos por familia).**
**Razonamiento:** En C++20, la seguridad de tipos en tiempo de compilación es nuestra mejor defensa contra errores de memoria en el sniffer. La Opción B (`void*`) es una "invitación al desastre" en un sistema que debe procesar paquetes a velocidad de cable; el coste de un cast incorrecto es un *Segmentation Fault* que tumba todo el NDR del hospital.
**Riesgos:** Mayor verbosidad en el SDK de plugins, pero se mitiga con una buena documentación de las cabeceras `plugin_api_*.h`.
**Blocker:** Ninguno.

### PREGUNTA 2 — Función de entrada por familia
**Recomendación:** **Acuerdo total con la separación funcional.**
**Razonamiento:** Un plugin de `ml-detector` no debería ver un `PacketContext` si su trabajo es puramente matemático sobre vectores de features. Separar `plugin_process_packet`, `plugin_predict` y `plugin_enrich` permite que el cargador (`libplugin_loader.so`) use `dlsym` para validar no solo que el plugin existe, sino que implementa la **capacidad** que el host requiere.
**Riesgos:** Ninguno significativo.
**Blocker:** Esta decisión es dependiente de que la Pregunta 1 sea la Opción A.

### PREGUNTA 3 — Plugins con contratos desconocidos
**Recomendación:** **Opción C (Solo primero-partido en PHASE 2).**
**Razonamiento:** Estamos construyendo la **Via Appia**. Intentar diseñar hoy una interfaz `"generic"` (Opción B) sin conocer los casos de uso de terceros resultará en una interfaz mediocre que tendremos que mantener por retrocompatibilidad. Implementemos los plugins de la casa primero (JA4, DNS_DGA) y dejemos que el contrato "emerja" de la necesidad real en la PHASE 3.
**Riesgos:** Ralentiza la adopción por parte de la comunidad externa, pero asegura la estabilidad para los usuarios actuales (hospitales).
**Blocker:** No afecta a las demás.

### PREGUNTA 4 — ¿Unificar skills de rag-security?
**Recomendación:** **NO UNIFICAR.**
**Razonamiento:** Las skills de `rag-security` viven en el dominio del texto y JSON, invocadas por un LLM con una latencia de segundos. Los plugins del sniffer viven en el dominio de los microsegundos y bytes crudos. Unificar los mecanismos de carga añade una capa de abstracción innecesaria que solo "satisface la simetría" pero no aporta valor técnico real.
**Riesgos:** Duplicación mínima de código de carga (mecanismo de búsqueda de ficheros), pero mantiene los dominios de falla aislados.
**Blocker:** Ninguno.

### PREGUNTA 5 — Plugins eBPF de kernel-telemetry
**Recomendación:** **Separar en ADR-018.**
**Razonamiento:** Conceptualmente son plugins, pero operacionalmente son **objetos BPF**. Su ciclo de vida depende del verificador del kernel y de mapas BPF, no de la pila de usuario. Mezclarlos en ADR-017 oscurecería el contrato de los plugins `.so`. Necesitamos un `EbpfManager` específico en el componente 7.
**Riesgos:** Inconsistencia menor en el nombre de las funciones de identidad, que debe resolverse mediante una convención de nombres estricta.
**Blocker:** Ninguno.

---

## Validación de la Jerarquía Propuesta



La jerarquía propuesta es **robusta y elegante**. Mi única corrección es sobre la familia **SnifferPlugin**:

1.  **Validación:** La distinción entre `PacketPlugin` (DPI) e `InferencePlugin` es correcta.
2.  **Sugerencia de Fusión:** El `EbpfUprobePlugin` (ej. `ebpf_tls`) no debería ser una rama separada en la jerarquía de interfaces `.so`. Técnicamente, el plugin de usuario simplemente recibe los eventos que el programa eBPF le pasa. Propongo que sea un `EnrichmentPlugin` especializado que se comunica con el kernel, pero que ante el host (`sniffer`) se comporte como cualquier otro extractor de features.
3.  **Familia Faltante:** **`ExporterPlugin` (en el futuro).** Alguien querrá enviar logs a una plataforma SIEM específica (Splunk, Sentinel). Un plugin que reciba el veredicto final y lo exporte será necesario en la PHASE 3.

### Veredicto de Gemini para ADR-017:

**Voto a favor de la estructura propuesta con Opción A en todas las preguntas.** Alonso, el sistema de plugins es el "sistema nervioso" que permitirá a **aRGus NDR** sobrevivir a nuevas amenazas como Ryuk o Conti sin tener que recompilar el core. La convención de nombres `lib{familia}_{nombre}_v{N}.so` es excelente para la auditoría forense en los servidores del hospital.

**The Council has spoken. Procede con la redacción del ADR-017. El código del DAY 95 espera.** 🏛️🛡️🚀