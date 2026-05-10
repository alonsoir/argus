# Pregunta 1 — Validez metodológica

No es un problema grave de fairness, siempre que lo expliquéis explícitamente y justifiquéis por qué cada herramienta se ejecutó en su modo operacional más apropiado para el experimento.

De hecho, en investigación con datasets históricos en PCAP:

* Zeek offline (`zeek -r`) es completamente estándar y muy aceptado.
* Suricata offline también existe (`suricata -r`), pero vuestro uso live tiene sentido porque queríais evaluar pipeline IDS realista con replay controlado.

Un reviewer serio probablemente no objetará “invalidez”, pero sí podría pedir:

> “¿Por qué no ejecutar ambos en el mismo modo?”

La respuesta fuerte es:

* el objetivo no era benchmarking de throughput bruto,
* sino comparar capacidad de detección bajo configuraciones operacionales representativas.

Y además:

* Zeek offline elimina packet loss,
* preserva reproducibilidad exacta,
* favorece análisis semántico profundo,
* mientras Suricata live representa despliegue IDS clásico.

Eso incluso puede fortaleceros metodológicamente si lo escribís bien.

La recomendación del Consejo:

Añadid una nota metodológica explícita:

> “Zeek was executed in offline analysis mode to maximize semantic extraction fidelity and eliminate replay-induced packet loss, a common methodology in retrospective PCAP analysis research.”

Y añadid honestamente:

> “Execution modes differ operationally and may influence timing-sensitive detections.”

Eso os blinda bastante.

---

# Pregunta 2 — Framing científico

Sí, el framing es correcto. Bastante bueno, de hecho.

Pero el Consejo afinaría una cosa importante:

No definir Zeek como “detección selectiva”.

Porque Zeek realmente no está diseñado como IDS clásico basado en alerting exhaustivo.

Zeek es:

* network analysis framework,
* telemetry engine,
* protocol semantics platform,
* event generation system.

La idea potente no es:

> “Zeek detecta poco.”

La idea potente es:

> “Observability does not imply classification.”

Esa es la distinción realmente importante.

Formulación más precisa y académicamente fuerte:

> “The experiment highlights the distinction between semantic network observability and explicit malicious behavior classification. Zeek successfully extracted rich protocol-level indicators and anomalous events, yet default policy scripts produced limited security alerts. This suggests that high-fidelity telemetry alone does not necessarily translate into operational detection performance without additional behavioral or policy layers.”

Eso es muy publicable.

Porque:

* no atacáis Zeek,
* reconocéis su fortaleza real,
* y definís claramente dónde entra aRGus.

Eso además posiciona elegantemente aRGus como:

> “behavioral interpretation layer over telemetry.”

Muy buena narrativa.

---

# Pregunta 3 — Zeek Phase 2

El Consejo cree que sí merece la pena hacerla, pero NO es bloqueante para arXiv v1.

Importante diferencia.

## Lo que ya tenéis es suficientemente interesante

Porque el hallazgo Phase 1 ya enseña:

* Suricata:

    * fuerte dependencia de firmas contemporáneas.

* Zeek:

    * enorme riqueza observacional,
    * baja clasificación por defecto.

* aRGus:

    * clasificación comportamental explícita.

Eso ya es un experimento comparativo sólido de paradigmas.

---

## Pero Phase 2 tiene mucho valor defensivo ante reviewers

Porque un reviewer probablemente preguntará:

> “¿Usasteis Zeek adecuadamente o solo defaults?”

Y honestamente:

* los defaults de Zeek son deliberadamente conservadores,
* mucha gente usa:

    * Intel framework,
    * notice policies,
    * JA3/JA4,
    * scripts comunitarios,
    * feeds externos.

Entonces, aunque no sea necesario para demostrar vuestra tesis principal, sí fortalece mucho el paper.

---

# Recomendación concreta

## Para arXiv v1

Publicad ya con:

```text
Phase 1: Default Operational Configurations
```

y explicitad:

* Zeek default scripts only,
* no external threat intel,
* no custom detection policies.

Eso hace el paper reproducible y honesto.

---

## Después (v2 o workshop)

Haced:

```text
Phase 2: Enhanced Zeek Detection Stack
```

con:

* Intel framework,
* feeds,
* scripts community,
* policy tuning.

Y ahí podéis responder otra pregunta MUY interesante:

> “¿Cuánta ingeniería manual necesita Zeek para acercarse a un behavioral NDR?”

Eso es científicamente valioso.

---

# La observación más importante del Consejo

Ahora mismo vuestro experimento ya no es simplemente:

```text
ML vs signatures
```

Se ha convertido en:

| Paradigma | Filosofía                               |
| --------- | --------------------------------------- |
| Suricata  | Explicit signature matching             |
| Zeek      | Semantic network observability          |
| aRGus     | Behavioral inference and classification |

Eso es muchísimo más interesante académicamente.

Porque ya no comparáis “herramientas”.

Estáis comparando modelos conceptuales de detección de red.

Y eso eleva bastante el nivel del paper.
