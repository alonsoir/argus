# Dictamen del Consejo — Modo Adversario

**Postura:** Ningún hallazgo del informe se rebate. Los tres defectos están medidos, las líneas cuadran, y la distinción (A) cableado vs (B) cabezas es el marco correcto. Lo que sigue no es refutación sino *tensión adversaria* sobre las respuestas propuestas y lagunas que el informe no cubre.

---

## Bloque 1 — Las cabezas rotas

### P1 — Ransomware y Traffic: ¿recuperables o irrecuperables?

**Ransomware: irrecuperable por reentrenamiento. Razón técnica explícita.**

El defecto no es que el modelo esté mal entrenado. Es que la feature `entropy` no es Shannon entropy — es varianza de longitud de paquete dividida entre 100.000. Pero incluso si corrigieras la fórmula para calcular Shannon entropy *de la distribución de tamaños de paquete*, seguiría sin discriminar ransomware: el tamaño de los paquetes de tráfico cifrado (TLS) tiene entropía *baja* (los registros TLS tienden a ~16 KB, distribución estrecha), no alta. La Shannon entropy que discrimina ransomware es la de los *bytes de payload* (datos cifrados vs datos estructurados), no la de los tamaños.

El `NetworkFeatures` que recibe el extractor **no contiene bytes de payload** — contiene agregados de flujo (byte counts, flag counts, IAT). No hay camino desde el contrato de entrada del extractor hasta la feature que el nombre promete. Esto no se arregla reentrenando: se arregla rediseñando el conjunto de features para señales de flujo que sí discriminan comportamiento ransomware (volumen anómalo a puertos SMB/445, ratio petición/respuesta asimétrico, conexiones a rangos C2 conocidos), o aceptando que la detección de ransomware a nivel de flujo requiere un extractor con acceso a payload.

**Veredicto:** Cabeza irrecuperable *en su forma actual*. Podría existir una cabeza ransomware diferente con features de flujo rediseñadas, pero eso es construir una cabeza nueva, no arreglar esta. Hasta que exista, peso 0 o retirada.

**Traffic: irrecuperable por error de granularidad de entrada, no por error de entrenamiento.**

Las cinco features constantes (`source_ip_entropy`, `dst_ip_concentration`, `protocol_variety` y sus variantes) son conceptualmente imposibles de calcular sobre un *único* `NetworkFeatures`. Un flujo tiene exactamente 1 IP origen, 1 IP destino y 1 protocolo. La entropía de una distribución de un elemento es siempre 0 (o la constante en la que está normalizada). No es que la implementación sea perezosa — es que la feature no tiene sentido matemático en la granularidad de entrada que recibe.

Para que esas features fueran reales, el extractor necesitaría recibir un *agregado de N flujos* del mismo origen, no un flujo individual. Eso es un cambio de contrato de entrada, no un reentrenamiento.

Las features que sí son reales (IAT std, duración de flujo, y las 3 restantes) podrían discriminar *algo*, pero no lo que el nombre "Traffic" promete (clasificación de dominio interno vs internet). La duración de un flujo no dice si el destino es interno o externo — eso lo dice la tabla de rutas o el rango IP.

**Veredicto:** Cabeza irrecuperable como clasificador de dominio. Las features reales que tiene podrían reutilizarse en otra cabeza con otro propósito, pero el Traffic detector tal como está definido no debe existir como puerta de dominio.

### P2 — Cabeza con peso 0 vs cabeza ausente

**Peso 0 documentado, no cabeza ausente. Razón:**

La cabeza ausente crea una ambigüedad que la cabeza con peso 0 no crea. Si el paper dice "tricapa" y el código tiene 2 cabezas, un revisor pregunta "¿dónde está la tercera?". Si el código tiene 4 cabezas pero 2 tienen peso 0 con `reason: "features not validated, see DEBT-..."`, la respuesta está en el código y es inequívoca.

**Pero — contrapartida adversaria — hay una trampa:** una cabeza con peso 0 que *ejecuta* y escribe en `provenance` genera ruido. Si Ransomware ejecuta `predict()` con features rotas, el score que produce es basura. Esa basura aparece en el veredicto coleccionado, en los logs, en el RAG. Un analista que lea el provenance verá "ransomware_head: 0.73 confidence" y pensará que significa algo, aunque el peso en el noisy-OR sea 0.

**Resolución:** Peso 0 **solo si** el verdict de esa cabeza se marca explícitamente como `status: DISABLED_UNRELIABLE` en el provenance, y el score brudo se omite o se reemplaza por `-1`. No se escribe basura al wire con un "peso 0" que el humano no ve. Si eso no se hace, mejor ausencia con documentación.

### P3 — La cascada Traffic → Internal: debe morir

**El Internal debe correr desacoplado de la decisión de dominio de Traffic.** Las razones se apilan:

1. **Traffic es 5/10 constante** — no puede decidir dominio fiablemente. Gatear Internal tras Traffic es gatear una señal posible tras una señal imposible.
2. **El gate crea un punto ciego medible:** cualquier flujo que Traffic clasifique como "internet" pero que sea movimiento lateral real (ej: exfiltración a IP externa que es realmente un tunel) nunca llega a Internal. Internal tiene una feature de exfiltración (`[7]`) diseñada exactamente para eso.
3. **La clasificación de dominio no necesita ML.** "¿Es esta IP interna?" es una lookup en tabla de rangos (RFC1918 + rangos org). No es un problema de clasificación. Meterlo como salida de un head ML fue un error de diseño original.

**Propuesta concreta:** Eliminar la cascada L748. Internal corre en todo flujo. La información de dominio (interno/interno) se obtiene por lookup determinista en la tabla de rangos del sniffer, se inyecta como metadata en `NetworkFeatures` (campo nuevo o repurposing), y Internal puede *leerla* como feature contextual — pero no es su gate.

**Contrapartida adversaria que el plan debe anticipar:** Internal corriendo sobre tráfico de internet producirá falsos positivos en la feature `[7]` (exfiltration: `outbound_ratio > 2.0`). Cualquier descarga grande (streaming, actualización de OS) tiene forward >> backward. Si Internal pesa en el noisy-OR sobre tráfico de internet, se generarán bloqueos espurios.

**Mitigación:** El peso de Internal en el noisy-OR debe estar condicionado al dominio. No como gate (si/no), sino como modulación: `peso_internal = peso_base × factor_dominio`, donde `factor_dominio = 1.0` si el flujo es interno, `0.3` (o el que la medición dicte) si es externo. Esto preserva la señal de exfiltración sin crear puntos ciegos ni falsos masivos.

---

## Bloque 2 — El cableado

### P4 — Ratificación del noisy-OR: SÍ, con una advertencia de saturación documentada

El operador `P = 1 − ∏(1 − pᵢ)` con `pᵢ = fiabilidad_i × score_i` es el correcto para este caso por las razones que el informe da (monotonía, no dilución, corroboración, siempre ≥ max).

**Advertencia cuantificada que debe ir en el ADR:**

Con 3 cabezas a fiabilidad 0.8, score 0.7 cada una → `pᵢ = 0.56`:
```
1 cabeza: P = 0.56
2 cabezas: P = 0.806
3 cabezas: P = 0.915
4 cabezas: P = 0.963
```

A partir de 3 cabezas de alta fiabilidad coincidiendo, el score satura cerca de 1.0 y el threshold se vuelve un knife-edge: un cambio de 0.01 en cualquier cabeza voltea el veredicto.

**Esto no es un defecto del operador — es una propiedad.** Cuando 3 cabezas fiables coinciden en "malicioso", quererás que el score sea alto. El knife-edge solo es peligroso si las fiabilidades están mal calibradas. Por eso el Paso 1 (medir F1 por cabeza) no es opcional: es el input que hace que el noisy-OR sea determinista o arbitrario.

**No se requiere damping factor** si las fiabilidades se miden honestamente y las cabezas rotas están en peso 0. Con la configuración realista inicial (Internal=0.5, DDoS=0.4, Ransomware=0.0, Traffic=0.0), la saturación no se alcanza.

**Veredicto: ratificado.** Añadir al ADR: tabla de saturación por configuración de cabezas, y la regla "si añadimos una 5ª cabeza con fiabilidad >0.7, reevaluar saturación".

### P5 — Injertar en provenance como N fuentes homogéneas

**Opción A (injertar):** Todas las cabezas son `add_verdicts()` con `engine_name` distintivo. El noisy-OR se calcula iterando `provenance->verdicts()`. `authoritative_source` se deprecia o se recalcula como "dominant contributor" post-hoc.

**Opción B (conservar eje):** `authoritative_source` sigue existiendo como fast-vs-ml, y el noisy-OR se calcula en una estructura paralela.

**Veredicto: Opción A, sin duda.** Razones:

1. `provenance` (ADR-002) ya existe con semántica de N fuentes. No inventar una segunda estructura para lo mismo.
2. `authoritative_source` hoy distingue 4 casos (DIVERGENCE|CONSENSUS|FAST_PRIORITY|ML_PRIORITY) entre 2 fuentes. Con 6 fuentes, esos 4 casos no cubren el espacio. El eje fast-vs-ml se vuelve irrelevante cuando el ensemble es el que decide.
3. La auditoría de un evento futuro necesita leer "qué dijo cada cabeza" — eso es `provenance->verdicts()`. Un cálculo paralelo que no se escribe al wire es invisible para la auditoría.

**Acción concreta:** `authoritative_source` se mantiene por compatibilidad del wire (no romper protobuf), pero su valor pasa a ser `ENSEMBLE_NOISY_OR` fijo. El campo `discrepancy_score` en provenance se recalcula como desviación estándar de los scores de las cabezas activas — alto discrepancy = cabezas en desacuerdo = señal para SOC.

### P6 — Coordinación del des-gateo dual: dos PRs secuenciales, NO atómicos

Hacer un PR que toque `ml-detector` Y `firewall-acl-agent` simultáneamente es irresponsable: si el despliegue falla a mitad, quedas con un estado inconsistente que no puedes revertir limpiamente.

**Secuencia segura:**

**PR1 (ml-detector):**
- Reconectar cabezas al veredicto (noisy-OR sobre provenance)
- Mover persistencia después de cabezas
- **MANTENER `attack_detected_level1()` mapeado a L1** (sin cambiar el campo del wire)
- Añadir campo NUEVO `attack_detected_ensemble()` = resultado del noisy-OR
- El ZMQ emite ambos campos. El firewall sigue leyendo el viejo. Nada cambia aguas abajo.

**PR2 (firewall-acl-agent):**
- Cambiar el gate de `attack_detected_level1()` a `attack_detected_ensemble() || attack_detected_level1()`
- El `||` es belt-and-suspenders: durante la transición, si el ensemble falla, L1 sigue protegiendo. Si L1 se equivoca, el ensemble puede corregir.
- Una vez validado en producción N días, PR3 elimina el fallback a `attack_detected_level1()`.

**Invariantes entre PRs:**
- Entre PR1 y PR2: el ml-detector emite datos completos pero el firewall los ignora. Estado seguro, sin regresión.
- Entre PR2 y PR3: el firewall usa ensemble con fallback L1. Estado más seguro que el actual (más señales, ninguna suprimida).

**Lo que NO se hace:** un solo PR que cambie ambos componentes a la vez. Lo que NO se hace: cambiar el significado de `attack_detected_level1()` en el ml-detector sin que el firewall lo sepa.

---

## Bloque 3 — Persistencia y grafo

### P7 — Golden vectors: regenerar, no intentar invarianza

La pregunta contiene una trampa: "¿el contrato debe ser invariante al reordenamiento?". La respuesta es **no, y no debería serlo**. El reordenamiento cambia *intencionalmente* qué se escribe — si el golden vector no cambia, el reordenamiento no hizo nada.

**Plan:**
1. Renombrar los golden vectors actuales a `correlation_v1_pre_heads` — no se borran, sirven como regresión del camino raw capture.
2. Generar `correlation_v2_post_heads` con el nuevo orden. Estos vectores tendrán `threat_category` values como `ATTACK`, `SUSPICIOUS_INTERNAL` en lugar de `RAW_CAPTURE`.
3. El test `test_correlation_roundtrip` prueba contra v2. Un test separado `test_correlation_v1_backward_compat` verifica que el camino fast-path (sin cabezas) sigue produciendo salida válida.
4. Si el schema de bronce cambia (nuevas columnas para head outputs), versionar el schema: `correlation_v2`.

**No hay atajo.** Intentar hacer los golden vectors "invariantes" significa definir un contrato tan vago que no prueba nada.

### P8 — ml_context: SÍ, debe poblarse con la salida de las cabezas

Si mueves las escrituras después de las cabezas pero dejas `ml_context` con `level_2_category = "UNKNOWN"`, has arreglado el *cuándo* pero no el *qué*. El grafo recibiría una fila escrita después de las cabezas pero sin información de las cabezas. Es el defecto C parcialmente arreglado.

**Poblado concreto:**

```cpp
// Después de cada cabeza, antes de las escrituras:
if (ddos_fired)     ml_context.level_2_category = "DDOS";
if (ransomware_fired) ml_context.level_2_category = "RANSOMWARE";  // cuando exista
if (internal_fired) ml_context.level_2_category = "SUSPICIOUS_INTERNAL";
                     ml_context.level_3_subcategory = internal.subcategory(); // "LATERAL_MOVEMENT" | "DATA_EXFILTRATION"

// attack_family se deriva de la cabeza dominante, NO hardcodeado:
ml_context.attack_family = derive_attack_family(dominant_head);
```

Esto elimina `DEBT-RAG-ATTACKFAMILY-HARDCODED-001` como efecto colateral del reordenamiento — no necesita fix separado.

---

## Hallazgo adicional del modo adversario — no estaba en el informe

### GAP-ADVERSARIO-001: `ring_consumer.cpp:908` zeroing de `backward_bytes` es DEBT, no "flank"

El informe lo marca como "flank, no-DEBT" y dice "medir cuál domina". **Elevar a DEBT P1.** Razón:

Hoy, el fast-path zeroing no causa daño porque Internal nunca corre en flujos fast-path (doble gate: L1 + Traffic). Pero el plan de fase 2 **desgatea Internal para que corra en todo flujo**. En el momento del des-gateo, cualquier flujo que pase por `ring_consumer.cpp:908` tendrá `backward_bytes = 0`, lo que hace que la feature `[7]` de Internal (exfiltration: `forward/backward > 2.0`) dispare con ratio infinito. **Cada flujo fast-path se convertiría en falso positivo de exfiltración.**

Esto no es teórico — es un bug que se activa exactamente cuando el arreglo de fase 2 se despliegue. Debe corregirse ANTES del des-gateo, no después.

**Fix:** `ring_consumer.cpp:908` debe usar `flow.dbytes` real (como hace `ml_defender_features.cpp:753`), o el campo debe marcarse como "unavailable" y el extractor Internal debe tratar `backward_bytes=0` como "dato ausente" (skip feature, no ratio infinito).

### GAP-ADVERSARIO-002: el fast_score no tiene fiabilidad medible

El informe propone noisy-OR sobre las cabezas ML, y menciona que `final_score = max(fast_score, noisy_or_ml_score)`. Pero `fast_score` no es una cabeza ML — es un heurístico del sniffer. No tiene F1, no tiene fiabilidad medible, no entra en `provenance->verdicts()`.

**Pregunta que el ADR debe responder:** ¿Es `fast_score` un miembro más del ensemble (con fiabilidad asignada por estimación, no medición), o sigue siendo un pre-filtro con rol especial?

**Recomendación:** Pre-filtro con rol especial. El fast_score existe para dar respuesta en <1ms ante patrones obvios (port scans, known-bad IPs). No debería entrar en el noisy-OR porque no tiene la misma semántica que un score ML (probabilidad condicional de clase). Mantener `final_score = max(fast_score, noisy_or_ml)` es correcto: el fast_path es un circuit breaker, no un clasificador.

---

## Revisión del plan de fase 2 — una reordenación

El plan propone: Precondición → Paso 1 (pulso Internal) → Paso 2 (cableado). **Esto bloquea (A) con (B).** El Paso 1 requiere datos etiquetados internos que no existen (§11). Si esperamos, el cableado no avanza.

**Reordenación propuesta:**

```
Paso 0 — Fix GAP-ADVERSARIO-001 (ring_consumer zeroing)
         Gate: el fix está en main, sin esto el des-gateo genera falsos masivos

Paso 1 — Cableado (Defectos A+B+C) con pesos PROVISIONALES
         - Internal: peso 0.3 ("cable verificado, discriminación no medida")
         - DDoS: peso 0.3 ("degradado pero vivo")
         - Ransomware: peso 0.0 ("features irrecuperables, ver DEBT")
         - Traffic: peso 0.0 ("features irrecuperables, ver DEBT")
         - PR1 (ml-detector) + PR2 (firewall) según secuencia P6
         Gate: tests unitarios del combinador pasan + golden v2 verdes

Paso 2 — Pulso del Internal sobre datos etiquetados (5.2b-i)
         - Generar datos MITRE/Atomic Red Team en entorno controlado
         - Medir F1 real del Internal
         - Ajustar peso del Internal: si F1 > 0.7 → subir a 0.6-0.8; si F1 < 0.5 → bajar a 0.1 o retirar
         Gate: número medido existe

Paso 3 — Stress test + latencia por cabeza
Paso 4 — pcap relay e2e en hardware propio
Paso 5 — Números al paper con config honesta
```

La diferencia clave: el cableado se hace con pesos declarados-provisionales, no con pesos medidos. El Paso 2 los valida o los corrige. El sistema es *honesto desde el día 1 del cableado* porque los pesos provisionales están documentados como tales en el provenance de cada evento. No mentimos diciendo "Internal pesa 0.8" — decimos "Internal pesa 0.3 provisional, pendiente de 5.2b-i".

---

## Resumen de respuestas

| Pregunta | Veredicto |
|----------|-----------|
| **P1** | Ransomware: irrecuperable (feature requiere payload, el contrato no lo tiene). Traffic: irrecuperable (features constantes por error de granularidad, no de entrenamiento). |
| **P2** | Peso 0 con `status: DISABLED_UNRELIABLE` en provenance y score omitido. Nunca basura al wire. |
| **P3** | Cascada debe morir. Internal corre siempre. Dominio por lookup determinista, no ML. Peso de Internal modulado por dominio, no gateado. |
| **P4** | Noisy-OR ratificado. Documentar tabla de saturación en ADR. Sin damping por ahora. |
| **P5** | Injertar como N fuentes homogéneas en provenance. `authoritative_source` deprecado a `ENSEMBLE_NOISY_OR`. |
| **P6** | Dos PRs secuenciales: PR1 (ml-detector, campo nuevo, sin romper viejo) → PR2 (firewall, gate con fallback `||`). Nunca atómico. |
| **P7** | Regenerar golden vectors como v2. No intentar invarianza. Mantener v1 como regresión. |
| **P8** | SÍ. `ml_context` se puebla con salida de cabezas. `attack_family` se deriva, no se harcodea. Elimina DEBT-4 como efecto colateral. |

**Dos GAPs adicionales elevados a DEBT:**
- `DEBT-RING-CONSUMER-BACKWARD-ZERO-001` (P1 — se activa con el des-gateo)
- Documentar en ADR el rol de fast_score como pre-filtro, no miembro del ensemble

---

*El escudo que conoce sus sombras también conoce que una sombra sin nombre es la más peligrosa. GAP-ADVERSARIO-001 es esa sombra: un bug latente que el arreglo de fase 2 despertaría. Corregidlo antes de abrir la puerta.*

fdo glm