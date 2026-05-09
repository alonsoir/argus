El Consejo responde.

El resultado es extremadamente interesante, pero requiere una interpretación rigurosa para que el paper gane credibilidad científica en lugar de parecer una comparación injusta. La clave es evitar la narrativa “Suricata no sirve” y enfocarlo como una diferencia de paradigma entre IDS basado en firmas y NDR basado en comportamiento.

# 1. Interpretación correcta del resultado

La lectura técnicamente sólida es:

> “Suricata funcionó correctamente bajo su modelo operacional esperado; sin embargo, el enfoque basado en firmas no produjo detecciones sobre CTU-13 Neris usando el ruleset ET Open contemporáneo.”

Eso es muy distinto de:

> “Suricata falla.”

Porque realmente no hay evidencia de fallo técnico:

* el motor arrancó,
* las reglas cargaron,
* el tráfico se procesó,
* simplemente no hubo match.

Y eso es completamente coherente con cómo funcionan los IDS basados en firmas.

CTU-13 Neris es:

* tráfico de 2011,
* botnet muy concreta,
* comportamiento ya antiguo,
* IOC/sigs posiblemente eliminadas hace años,
* ET Open actual optimizado para amenazas contemporáneas.

Desde el punto de vista científico, el resultado importante NO es:

> “aRGus detecta y Suricata no.”

El resultado importante es:

> “Los enfoques conductuales conservan capacidad de generalización temporal frente a reglas estáticas contemporáneas.”

Eso sí es una afirmación fuerte y defendible.

---

# 2. Repetir con ET Open histórico 2011

Sí. Absolutamente sí.

Eso fortalece muchísimo el paper.

Porque separa dos hipótesis distintas:

## Hipótesis A

“Nunca existió firma.”

## Hipótesis B

“La firma existió, pero desapareció por envejecimiento operacional.”

Esa diferencia importa muchísimo.

Si conseguís rulesets de 2011 y aparecen alertas:

* demostrará obsolescencia temporal de firmas,
* reforzará el argumento de deriva temporal (“signature drift”),
* será un hallazgo muy valioso.

Si incluso con rules históricas sigue en 0:

* refuerza aún más el valor del enfoque NDR,
* porque significa que ni siquiera hubo cobertura histórica suficiente.

Ambos resultados son científicamente útiles.

---

# 3. Dónde colocar esto en el paper

No lo metería solo en §8.7.

Merece sección propia.

Recomendación:

```text
§8.13 Temporal Robustness and Signature Aging
```

o:

```text
§8.13 Comparative Evaluation Against Contemporary Signature-Based IDS
```

Porque el hallazgo no es solo “comparativa SOTA”.

El hallazgo real es:

* degradación temporal de firmas,
* dependencia del mantenimiento de IOC,
* persistencia del comportamiento estadístico,
* resiliencia temporal del modelo ML.

Eso tiene entidad suficiente para sección independiente.

---

# 4. Problemas metodológicos potenciales

Aquí el Consejo sí ve algunos puntos que debéis blindar antes de publicar.

## A. Suricata no es un NDR

Debéis explicitarlo claramente.

Porque reviewers podrían decir:

> “Comparáis categorías distintas.”

Y tienen razón parcialmente.

Suricata:

* IDS basado en firmas/protocol decoding.

aRGus:

* NDR comportamental + ML.

La comparación sigue siendo válida operacionalmente, pero debéis explicarlo así:

> “Both systems operate at network telemetry level and target malicious traffic detection, although their internal detection paradigms differ.”

---

## B. Riesgo de “configuration bias”

Necesitáis demostrar:

* rules cargadas correctamente,
* HOME_NET correcto,
* checksum validation no descartando tráfico,
* pcap reproducido íntegramente,
* no packet drops relevantes.

Incluid:

```text
suricata -T
```

y métricas de:

* packets processed,
* flows,
* decoder stats.

Si no, un reviewer puede decir:

> “Quizá Suricata estaba mal configurado.”

---

## C. CTU-13 es dataset antiguo

Esto NO invalida el experimento.

Pero sí condiciona la interpretación.

Debéis reconocer explícitamente:

> “The age of CTU-13 introduces potential temporal mismatch against contemporary IDS signatures.”

Eso os protege académicamente.

---

## D. Comparativa justa

La comparativa es bastante justa realmente:

* mismo hardware,
* misma VM,
* mismo tráfico,
* mismo replay,
* mismas velocidades.

Eso está muy bien diseñado.

De hecho, mejor que muchos papers.

---

# 5. Lo más importante del resultado

El verdadero hallazgo aquí no es F1.

Es esto:

## Las firmas tienen memoria histórica limitada.

Mientras que:

## El comportamiento estadístico del malware persiste.

Ese es el núcleo conceptual potente del paper.

Neris sigue comportándose “como botnet” aunque sus IOC hayan envejecido.

Y eso es precisamente donde un NDR basado en telemetría tiene ventaja estructural.

---

# 6. Recomendación estratégica para el paper

No ataquéis a Suricata.

Eso sería un error académico y os perjudicaría.

La narrativa fuerte es:

* firmas y NDR son complementarios,
* pero los datasets históricos muestran limitaciones temporales de las firmas,
* mientras que modelos comportamentales pueden mantener capacidad de detección más allá de la vida útil de los IOC.

Esa formulación es mucho más madura y científicamente sólida.

---

# 7. Experimentos futuros MUY valiosos

El Consejo cree que esto abre una línea experimental potentísima:

## “Temporal decay benchmark”

Ejemplo:

| Dataset Year | Rules Year | Detection Rate |
| ------------ | ---------- | -------------- |
| 2011         | 2011       | ?              |
| 2011         | 2015       | ?              |
| 2011         | 2020       | ?              |
| 2011         | 2026       | 0              |

Eso sería un resultado muy publicable.

Y compararlo contra:

* modelo ML entrenado una vez,
* modelo ML actualizado,
* firma contemporánea.

Eso empieza a parecer investigación seria de primer nivel sobre resiliencia temporal de IDS.

---

# Recomendación final del Consejo

Mañana:

1. Blindar metodología Suricata.
2. Extraer stats completas de procesamiento.
3. Buscar ET Open histórico.
4. Crear sección nueva §8.13.
5. Enfatizar “signature aging” y “temporal robustness”.
6. Evitar framing agresivo contra Suricata.

Porque el resultado, bien presentado, es realmente interesante.
