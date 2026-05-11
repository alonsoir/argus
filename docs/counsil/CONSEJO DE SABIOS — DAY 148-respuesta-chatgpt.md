# CONSEJO DE SABIOS — RESPUESTA DAY 148

---

# P1 — Validez científica del framing de complementariedad

## Veredicto corto

Sí, el framing actual es científicamente defendible en el abstract **si se formula como observación arquitectónica y no como claim de integración operacional demostrada**.

La frase actual:

> *"The three paradigms are complementary..."*

es razonable porque:

* los experimentos ya demostraron propiedades distintas
* cada sistema opera sobre capas semánticas diferentes
* no afirmas mejora cuantitativa por integración
* no afirmas ensemble validado
* no afirmas aumento de detección

Lo importante es esto:

> “operate naturally alongside”

Eso describe compatibilidad arquitectónica, no validación empírica de fusión.

---

## Lo que NO deberías afirmar todavía

Evitar expresiones tipo:

* “combined system improves detection”
* “integrated architecture outperforms”
* “fusion increases coverage”
* “ensemble superiority”

Porque eso sí requeriría:

* implementación integrada
* métricas conjuntas
* evaluación estadística

---

## Recomendación del consejo

Mantener el framing en el abstract, pero reforzar precisión epistemológica.

### Formulación sugerida

> *"The results suggest that the three paradigms are architecturally complementary, with each operating at a distinct semantic and encoding layer..."*

La palabra importante es:

* “suggest”
* “architecturally”

Eso reduce superficie de ataque en peer review.

---

## Conclusión P1

✔ Puede quedarse en abstract
✔ También debe permanecer en Future Work
✔ No presenta problema metodológico si se mantiene como framing arquitectónico y no claim experimental

---

# P2 — Estrategia óptima para cerrar DEBT-PARQUET-SCHEMA-001

---

# P2a — Granularidad: flow vs packet

## Veredicto del consejo

### Flow-level es la decisión correcta.

Packet-level:

* explota volumen
* destruye escalabilidad
* complica Neo4j
* genera cardinalidad inmanejable

Además:

* tu pipeline ya es conductual
* el modelo ML opera sobre agregación
* Suricata ya cubre packet semantics

Por tanto:

> packet-level no aporta suficiente valor arquitectónico para memoria histórica.

---

## Recomendación concreta

### Unidad mínima:

```text
flow window aggregation
```

Ejemplo:

* src/dst
* proto
* bytes
* packets
* duration
* flags aggregate
* entropy metrics
* anomaly score

---

# P2b — Registrar todo vs solo alertas

## Veredicto

### Episódica local:

✔ registrar todo (SQLite)

### Consolidada central:

⚠ NO registrar todo.

El consejo recomienda:

| Tipo evento                      | Centralizar |
| -------------------------------- | ----------- |
| attack                           | Sí          |
| anomaly                          | Sí          |
| deny/drop                        | Sí          |
| high-confidence normal baselines | Muestreo    |
| tráfico normal completo          | No          |

---

## Motivo

Si centralizas todo:
Neo4j termina siendo:

> “un SIEM caro con grafos”

y no:

> memoria estructural útil.

---

## Recomendación concreta

### Política híbrida:

#### Always ingest:

* alerts
* denies
* anomalies
* high severity
* rare protocol
