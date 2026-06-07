**Asiento Kimi — Deliberación sobre ADR-055 v1 (Borrador)**

---

He leído el borrador en su totalidad. A continuación mi análisis sección por sección, con posición sobre cada decisión y una valoración global de la arquitectura del documento.

---

## §0. Principio ordenador — **APOYO CON MATIZ**

El principio es sólido y necesario: *"suplantador fiel, no simulador libre"*. La bidireccionalidad de propagación (sniffer cambia → injector cambia, y viceversa cuando el injector revela discrepancias) es correcta. El matiz que añado:

> **La fidelidad es al *comportamiento observable del contrato*, no a la *implementación letra por letra*.**

Si el sniffer real usa `dontwait` pero **nunca** exhibe pérdida visible en producción (porque el PULL siempre consume más rápido que el PUSH produce, o porque el HWM nunca se alcanza), entonces el suplantador que *sí* exhibe pérdida/reenvío no es más fiel — es *más stressante*. Eso es válido como *test de carga*, no como *test de contrato*. El §0 debería distinguir entre:
- **Fidelidad de contrato** (obligatoria, inquebrantable).
- **Fidelidad de condiciones operativas** (deseable, pero el injector puede ser más o menos agresivo que el real sin invalidarse como espejo).

**Sugerencia:** añadir una nota al §0 que aclare que el suplantador puede *instrumentar* condiciones extremas (pérdida, reenvío) que el real raramente muestra, siempre que el **mecanismo** sea el mismo. El instrumento es aditivo; el mecanismo de entrega no debe ser *más fuerte* que el real, pero sí puede ser *igual* y dejar que las condiciones de test (rápida inyección, HWM bajo) lo hagan visible.

---

## §3.1 node_id sintético — **RATIFICO 8/8**

`isomorfo fijo` (`synth-node-00`) es la decisión correcta. Modela un sensor único, la unicidad la da `community_id`. La deferencia de multi-nodo a ADR-054 es prudente.

**Nota menor:** el mock `synth:node:<event_id>` está bien para trazabilidad, pero asegurar que el correlation-engine lo descarte *antes* de Kuzu es un comportamiento que debería tener test propio (no solo confiar en el prefijo `synth:`). No bloqueante para este ADR.

---

## §3.2 Dos perillas (determinista / realista) — **RATIFICO 8/8 CON REFINAMIENTO**

La solución de DeepSeek (semilla fija en modo `realistic`) es elegante. Resuelve el falso dilema determinismo-vs-cobertura.

**Matiz de implementación:** la fórmula de validación de Gemini (`{escritos} == {inyectados} \ {sin puertos}`) es correcta conceptualmente, pero operativamente requiere que el E2E tenga acceso al *conjunto de event_id inyectados*. Hoy el injector loguea, pero el E2E no consume ese log. `DEBT-INJECTOR-DELIVERY-METRIC-001` debería absorber también esta necesidad: el diff de conjuntos debe ser capaz de filtrar por "correlacionable vs no-correlacionable".

**Sugerencia:** en §3.2 o en §8, vincular `DEBT-INJECTOR-PROTO-MIX-001` con `DEBT-INJECTOR-DELIVERY-METRIC-001`: la métrica de conjuntos debe poder segmentar por "motivo de ausencia" (no entregado por ZMQ vs entregado pero descartado por `nullopt`).

---

## §3.3 Semántica de entrega — **OBJECIÓN FORMAL A LA ANULACIÓN DE ÁRBITRO**

Este es el punto crítico. Mi posición en la 1ª pasada fue **(b) bloqueante con timeout**. El ADR registra que Alonso anuló y optó por "solo instrumentar, no cambiar mecanismo". **Objeto a la anulación por los siguientes motivos:**

### 3.3.1 La fidelidad de §0 no es argumento suficiente aquí

El sniffer real y el injector no son simétricos en *carga*:
- El sniffer real captura del kernel; su tasa está limitada por la NIC y el tráfico de red real. El ZMQ PUSH nunca se satura porque el productor (kernel/netfilter) no puede inyectar más rápido de lo que la red física permite.
- El injector sintético puede inyectar **a velocidad de memoria** (miles de eventos/ms). El HWM de ZMQ PUSH se alcanza en condiciones que el sniffer real **nunca reproduce**.

Por tanto, mantener `dontwait` en el injector no es "ser fiel al sniffer"; es **introducir un artefacto de test que el sniffer real no exhibe**. El artefacto es real de ZMQ, pero las *condiciones* que lo hacen visible son artificiales del test. Si el objetivo es fidelidad, deberíamos también limitar la tasa del injector a la tasa esperada del sniffer — y eso no se hace.

### 3.3.2 El argumento de "medir antes de arreglar" es circular

El ADR dice: "si el instrumento revelara una pérdida que rompe el gate de CI, entonces se reconsidera". Pero el instrumento **ya reveló** la pérdida/reenvío (102 filas de 100, 2 duplicados). El gate de CI **no mide filas**, mide deltas de stats. Eso es precisamente el problema: el gate es ciego a la semántica de entrega. "Medir antes de arreglar" presupone que la medición es neutral, pero **elegir no medir filas** (solo deltas) es una decisión que enmascara el problema.

### 3.3.3 El coste de (b) es trivial; el coste de "solo instrumentar" es alto

- **(b) bloqueante con timeout:** un `setsockopt(ZMQ_SNDTIMEO, 1000)` + quitar `dontwait`. Cambio de 2 líneas. El comportamiento sigue siendo ZMQ PUSH; no se cambia patrón, no se añade retry.
- **"Solo instrumentar":** requiere (a) log estructurado del injector con event_id, (b) lectura de bronce para extraer event_id escritos, (c) diff de conjuntos, (d) integración en el gate de CI. Es más trabajo que (b) y **no resuelve el problema**, solo lo documenta.

### 3.3.4 El precedente de ADR-052 §3.11 no aplica

La anulación de ADR-052 fue sobre un *campo de identidad* (`flow_uid`) donde la complejidad de implementación justificaba la simplificación. Aquí estamos hablando de **un flag de ZMQ** y un `setsockopt`. La complejidad es asimétrica: arreglar es más barato que instrumentar.

### Mi posición alternativa

**Compromiso:** adoptar (b) *solo en el injector*, con una nota explícita de que el sniffer real mantiene `dontwait` y que el injector es **más conservador** en entrega por las razones de tasa anteriores. Esto no viola §0 si entendemos §0 como "fidelidad de contrato y semántica observable", no "fidelidad de implementación letra por letra". El contrato observable del sniffer es "entrega best-effort, pero en la práctica at-most-once porque nunca se satura"; el injector con timeout reproduce ese contrato observable.

**Si el Consejo insiste en la anulación:** acepto bajo protesta, pero solicito que `DEBT-INJECTOR-DELIVERY-METRIC-001` se eleve a **P1** (no P2), porque sin ella el modo `deterministic` no es realmente determinista (puede variar 100–102 filas entre corridas).

---

## §3.4 col 17 como string — **RATIFICO 8/8**

Sin objeciones. La decisión de mantener el engine limpio de protobuf es correcta y ya sellada.

---

## §3.5 Oracle Divergence — **RATIFICO 8/8**

Preservar la procedencia es la única opción coherente con ADR-051. La directriz "no aplanar" al entrar en Kuzu es sabia. Aplazar la decisión gold a ADR-054 es correcto.

**Sugerencia menor:** añadir en §3.5 que el correlation-reader ya demostró que puede transportar strings arbitrarios de `authoritative_source` sin romper el formato TSV; esto valida que el pipeline es transparente a nuevas fuentes sin cambio de código.

---

## §4. Alternativas rechazadas — **APOYO LA TABLA**

La tabla es clara y útil. Añadiría una fila:

| Alternativa | Por qué se rechaza |
|---|---|
| Limitar tasa del injector a tasa de sniffer real | Complejidad innecesaria; el injector no simula condiciones de red, solo contrato de mensajes. |

Esto refuerza por qué (b) es preferible a "ser fiel al dontwait": no estamos simulando la red.

---

## §5. Estado de preguntas — **CORRECCIÓN EN Q4**

El ADR dice "Claude votó sí, se retractó". En mi lectura del DAY 177, Claude votó **no** en Q4 ("no DEBT nuevo"). Verificar: en la respuesta de Claude, Q4 dice "Ratificación: no DEBT nuevo, cerrar como 'completar A'". Eso es un **no** a abrir DEBT, no un "sí retractado". La tabla de §5 debería corregirse: **8/8 en Q4**, no 7/8.

---

## §6. Consecuencias — **APOYO, CON AMPLIACIÓN DE RIESGO (1)**

El riesgo (1) es crítico: si `DEBT-INJECTOR-DELIVERY-METRIC-001` no se implementa, la pérdida/reenvío es invisible. Dado que la anulación de Q1 deja el problema sin arreglo, este riesgo debería ser **P1**, no mención pasajera.

El riesgo (2) sobre `seq_in_window` es perspicaz. Sugiero elevarlo a `DEBT-INJECTOR-SEQWINDOW-001` con estado **P2** en §8, no solo "propuesta".

---

## §7. Validación — **APOYO, PERO CON HUECO**

El punto "Discard path (modo realistic)" está marcado como pendiente. Esto es correcto, pero debería vincularse explícitamente a `DEBT-INJECTOR-PROTO-MIX-001`. Hoy no hay modo `realistic` implementado; el ADR no debe dar la impresión de que ya existe.

---

## §8. Deudas — **REORDENAMIENTO SUGERIDO**

| DEBT | Prio | Estado | Nota |
|---|---|---|---|
| `DEBT-INJECTOR-NODEID-001` | P0 | Cerrada | ✓ |
| `DEBT-INJECTOR-ROWGAP-001` | — | Cerrada como característica | ✓ |
| `DEBT-INJECTOR-DELIVERY-METRIC-001` | **P1** | Abierta | **Elevar**: sin ella, la anulación de Q1 deja un agujero de observabilidad. |
| `DEBT-INJECTOR-PROTO-MIX-001` | P2 | Abierta | Depende de DELIVERY-METRIC para validar ausencia. |
| `DEBT-INJECTOR-SEQWINDOW-001` | P2 | Abierta | Considerar transporte de `seq_in_window`. |
| `DEBT-LIB-001` | P1 | Diferida | Traer a pasada futura. |

---

## §9. Referencias — **COMPLETO**

Sin objeciones. La trazabilidad a ADR-052, ADR-051, ADR-046 es correcta.

---

## Resumen de voto de Kimi

| Sección | Voto | Nota |
|---|---|---|
| §0 Principio ordenador | ✅ APOYO | Con matiz: fidelidad al contrato observable, no a la implementación letra por letra. |
| §3.1 node_id | ✅ RATIFICO | 8/8. |
| §3.2 Dos perillas | ✅ RATIFICO | 8/8. Semilla fija es clave. |
| §3.3 Entrega (Q1) | ⚠️ **OBJECIÓN** | La anulación de árbitro es defensible pero no por §0. Argumento: el injector no reproduce las condiciones operativas del sniffer (tasa). (b) es más barato que instrumentar. Acepto bajo protesta si DELIVERY-METRIC sube a P1. |
| §3.4 col 17 string | ✅ RATIFICO | 8/8. |
| §3.5 Divergence | ✅ RATIFICO | 8/8. |
| Q4 DEBT proto | ✅ RATIFICO | 8/8 (corregir tabla: Claude no votó sí). |
| Q3 ADR-055 absorbe | ✅ RATIFICO | 8/8. |

---

## Recomendaciones al borrador v2

1. **§0:** Añadir distinción entre fidelidad de contrato y fidelidad de condiciones operativas.
2. **§3.3:** Reconsiderar la anulación, o al menos elevar `DEBT-INJECTOR-DELIVERY-METRIC-001` a P1 con compromiso de implementación inmediata.
3. **§5 Q4:** Corregir "Claude votó sí" → "8/8 no".
4. **§8:** Elevar DELIVERY-METRIC a P1; formalizar SEQWINDOW como P2.
5. **§3.2:** Vincular PROTO-MIX con DELIVERY-METRIC en la descripción de deuda.

El ADR es sólido en conjunto. La única fisura real es §3.3, donde la coherencia interna con §0 es más aparente que real. El resto es trabajo de calidad.

FDO

KIMI
