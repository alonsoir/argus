# Reconciliación del Consejo de Sabios — auditoría del `ml-detector`

**Entrada:** 8 dictámenes (chatgpt, deepseek, gemini, grok, kimi, glm, mistral, qwen) + el voto adversario de Claude = 9 voces.
**Árbitro final:** Alonso. Este documento no decide; separa lo acordado de lo disputado y pone cada decisión donde corresponde.
**Método:** *medir no votar* aplicado al propio Consejo. Donde hay desacuerdo real, se presenta con las dos caras y —cuando existe— la medición que lo zanja. No se promedian opiniones.

Reconciliación del Consejo de Sabios — auditoría del ml-detector.md

---

## Parte 1 — Consenso (va al ADR sin más discusión)

Lo que las nueve voces sostienen. Esto es suelo firme.

- **Los tres defectos A, B, C están confirmados** por todos los que verificaron el repo (qwen y grok afirman haberlo hecho línea a línea; gemini, deepseek, mistral, glm, kimi lo aceptan como medido y trazable). Ninguno rebate un solo hecho. La auditoría es correcta.
- **P3 — matar la cascada Traffic→Internal: unánime (8/8).** El Internal corre siempre, desacoplado. Una cabeza sana no debe depender de una rota para decidir si se ejecuta. El dominio (interno/internet) se resuelve por **lookup determinista** sobre rangos RFC1918 + subredes configuradas (deepseek, glm), no por ML.
- **P4 — noisy-OR como operador: ratificado (7/8).** `P = 1 − ∏(1 − pᵢ)`, `pᵢ = fiabilidad_i · score_i`. Monótono, incorpora corroboración, no diluye, siempre ≥ max. Media ponderada rechazada por dilución; max-de-N por ignorar corroboración; Dempster-Shafer por complejidad innecesaria. *(La única disidencia, chatgpt, es de raíz y se trata en la Parte 2-D5.)*
- **P5 — inyección en `provenance`: unánime.** Las cabezas entran como `add_verdicts()` homogéneos; el combinador itera `provenance->verdicts()`; `provenance->set_final_decision()` es el punto único de decisión. `authoritative_source` se conserva por compatibilidad del wire pero se redefine a `ENSEMBLE_NOISY_OR` (o "contribuyente dominante"). glm añade: recalcular `discrepancy_score` como desviación estándar de los scores de cabezas activas → discrepancia alta = señal para el SOC.
- **P7 — golden vectors: regenerar, no forzar invarianza (unánime).** El reordenamiento *cambia a propósito* qué se escribe al bronce; si el golden no cambia, el reordenamiento no hizo nada. El contrato es invariante en **esquema**, no en **contenido**. deepseek y glm proponen versionar: congelar `correlation_v1` como legado pre-cabezas (regresión del fast-path) y crear `correlation_v2` post-cabezas con campos nuevos (`specialized_head_scores`, `final_ensemble_score`).
- **P8 — poblar `ml_context` desde las cabezas: unánime.** Y con un regalo: hacerlo **elimina `DEBT-RAG-ATTACKFAMILY-HARDCODED-001` como efecto colateral** (glm, gemini, qwen, mistral). El `attack_family` se deriva de la cabeza dominante; ya no se hardcodea. Una deuda menos, sin fix separado.

---

## Parte 2 — Desacuerdos reales (Alonso decide)

Aquí el Consejo NO es unánime. Presento las dos caras y la medición que zanja, donde la hay. Estas son tuyas.

### D1 🎯 — ¿Es recuperable la cabeza Traffic? El desacuerdo más importante, y es medible.

**Cara A (recuperable ya):** deepseek — las features muertas (entropía de IPs, concentración de destino, variedad de protocolo) se calculan con datos que *ya están* en `NetworkFeatures`. Es feature engineering, no carencia de datos.

**Cara B (irrecuperable a la granularidad actual):** glm y qwen, con un argumento técnico que deepseek no contempla. **Un `NetworkFeatures` es UN flujo: tiene exactamente 1 IP origen, 1 IP destino, 1 protocolo.** La entropía de una distribución de un solo elemento es 0 (o la constante en que se normaliza). Las features no son constantes por pereza — **son matemáticamente imposibles a la granularidad de entrada.** Para que "entropía de IPs origen" tenga sentido, el extractor necesita un *agregado de N flujos*, no un flujo. Eso es un cambio de contrato de entrada (glm) o de telemetría del sniffer con ventanas temporales (qwen), no un reentrenamiento.

**La medición que zanja D1 (y que nadie ha hecho todavía):** *¿qué granularidad tiene `NetworkFeatures` — un flujo individual o un agregado en ventana?* Si es un flujo, glm/qwen tienen razón y Traffic no es recuperable sin tocar el contrato de entrada. Si el sniffer ya agrega por ventana, deepseek podría tener razón. **Esta es la única medición que decide si Traffic vive, muere o renace con otro contrato.** Mi lectura se inclina a glm/qwen (un `NetworkFeatures` parece un flujo, no un agregado), pero es testable y no lo he verificado — no lo voto.

### D2 — ¿Es recuperable la cabeza Ransomware?

**Cara A (recuperable con trabajo):** kimi, mistral, qwen — corregir el extractor para calcular entropía de Shannon real + reentrenar contra ground-truth de ransomware. El concepto existe; el extractor miente.

**Cara B (irrecuperable en su forma actual):** deepseek, gemini, grok, y sobre todo **glm con el argumento decisivo:** aunque corrigieras la fórmula a Shannon real *sobre tamaños de paquete*, seguiría sin discriminar — el tráfico cifrado (TLS) tiene tamaños de registro estrechos (~16 KB), entropía **baja**, no alta. La entropía que discrimina ransomware es la de los **bytes de payload** (cifrado vs estructurado), y **`NetworkFeatures` no contiene payload** — contiene agregados de flujo. No hay camino desde el contrato de entrada hasta la feature que el nombre promete. Arreglarla es construir una cabeza nueva con otras features (volumen a puertos SMB/445, ratio petición/respuesta asimétrico, conexiones a C2 conocido), no reparar esta.

**Mi lectura:** glm gana el argumento técnico. "Corregir a Shannon" es un espejismo si la señal vive en un dato que el contrato no transporta. Pero, como en D1, la pregunta de fondo es medible: *¿qué transporta `NetworkFeatures`?* La misma medición de granularidad de D1 informa esto.

### D3 — Cabeza con peso 0 vs. cabeza ausente

**Peso 0 documentado:** deepseek, kimi, mistral. **Ausente:** gemini, grok, qwen (código muerto que consume ciclos y confunde).

**La síntesis que reconcilia (glm), y que recomiendo:** el peligro del peso 0 no es el peso — es que la cabeza **siga ejecutando `predict()`** y escriba un score basura en `provenance`/RAG. Un analista que lea "ransomware_head: 0.73 confidence" creerá que significa algo, aunque el peso en el noisy-OR sea 0. **Resolución:** peso 0 **solo si** el veredicto de esa cabeza se marca `status: DISABLED_UNRELIABLE` en el provenance y su score crudo se omite o se pone a `-1`. Nunca basura al wire con un "peso 0" que el humano no ve. Si eso no se garantiza, mejor la ausencia. Esto une los dos bandos: honestidad de arquitectura (la cabeza figura) sin ruido semántico (no escribe un número mentiroso).

### D4 — Des-gateo de dos componentes: ¿PR atómico o secuenciado?

**Atómico:** deepseek, gemini, mistral (garantiza consistencia; el ml-detector pasa a ser la única fuente de verdad de la decisión de bloqueo, el firewall un mero ejecutor de `provenance.final_decision`).

**Secuenciado (mayoría, 4):** grok, kimi, glm, qwen. Argumento de seguridad, más fuerte: un rollback de un PR atómico deja dos componentes en estado inconsistente e irrevertible. Entre PR1 y PR2, el sistema es **más restrictivo**, nunca roto.

**La propuesta más rigurosa (glm), que recomiendo porque desarma la objeción del bando atómico:**
- **PR1 (ml-detector):** reconecta cabezas + noisy-OR + mueve persistencia. **Mantiene `attack_detected_level1()` con su significado viejo** y **añade un campo NUEVO** `attack_detected_ensemble()`. El firewall sigue leyendo el viejo. Nada aguas abajo cambia.
- **PR2 (firewall):** cambia el gate a `attack_detected_ensemble() || attack_detected_level1()` — cinturón y tirantes: si el ensemble falla, L1 sigue protegiendo; si L1 se equivoca, el ensemble corrige.
- **PR3 (más tarde, validado N días):** elimina el fallback a L1.

El campo aditivo hace que el bando atómico tenga su consistencia (el campo viejo nunca cambia de significado hasta PR3) sin el riesgo de rollback dual. **Secuenciado con campo aditivo domina a ambas posturas originales.**

### D5 ⚠️ — La disidencia de raíz de chatgpt sobre el noisy-OR (no la despachemos)

Siete ratifican noisy-OR. chatgpt lo ataca en la raíz, y el punto es serio: **las cabezas no estiman la misma variable aleatoria.** L1 estima P(ataque); Internal estima P(movimiento lateral); Traffic estima P(es interno); DDoS estima P(ddos). El noisy-OR es matemáticamente correcto solo si todas estiman `P(mismo evento)`. Combinarlas directamente mezcla probabilidades de eventos distintos.

**Cómo lo reconcilio, y por qué refuerza el resto del plan:** el noisy-OR es válido si cada cabeza que entra estima `P(este flujo es malicioso vía mi especialidad)` — entonces "lateral OR ddos OR exfil OR..." ≈ "malicioso" es una unión legítima. Pero **Traffic NO estima eso** — estima P(dominio interno), que no es una probabilidad de amenaza. Aplicando el punto de chatgpt: **Traffic nunca debe entrar en el noisy-OR**, porque responde otra pregunta. Eso, lejos de romper el plan, **confirma D1/P3**: Traffic sale del veredicto (a lo sumo aporta contexto de dominio, mejor por lookup determinista). La lección de chatgpt para el ADR: **el combinador solo agrega cabezas que estiman probabilidad-de-malicioso; las que estiman otra cosa (dominio) son contexto, no votos.** Y su propuesta arquitectónica de fondo (separar *Detectores* de *Clasificadores*, combinador que opere sobre contratos/metadatos y no conozca nombres de cabezas) es la dirección correcta a medio plazo, aunque no bloquee el cableado inmediato.

---

## Parte 3 — Lo que el Consejo encontró y la auditoría NO vio (los hallazgos valiosos)

Estos son el oro del método: puntos ciegos de la auditoría, cazados por el Consejo.

### 🔴 HALLAZGO CRÍTICO — el `backward_bytes = 0` es un DEBT P1 que el arreglo de fase 2 DETONARÍA (glm, corroborado por qwen)

La auditoría marcó el doble camino de `backward_bytes` como "nota, no-DEBT aún, medir cuál domina". **glm y qwen dicen, independientemente, que eso está mal**, y glm da el razonamiento que lo convierte en el hallazgo más importante de toda la ronda:

Hoy `ring_consumer.cpp:908` (`set_total_backward_bytes(0)`) es inofensivo **porque el Internal nunca corre en flujos fast-path** (doble gate: L1 + Traffic). **Pero fase 2 des-gatea el Internal para que corra en TODO flujo.** En el momento del des-gateo, cualquier flujo que pase por ese camino tendrá `backward_bytes = 0` → la feature `[7]` del Internal (exfiltración: `forward/backward > 2.0`) dispara con **ratio infinito** → **cada flujo fast-path se convierte en un falso positivo de exfiltración.**

No es teórico: es un bug latente que el propio arreglo de fase 2 despertaría. **Debe corregirse ANTES del des-gateo, no después.** → Nuevo `DEBT-RING-CONSUMER-BACKWARD-ZERO-001` (P1). Fix: usar `flow.dbytes` real (como `ml_defender_features.cpp:753`) o tratar `backward_bytes=0` como "dato ausente" (skip feature, no ratio infinito). Esto refuta directamente mi decisión de la sesión anterior de dejarlo como nota. **Tenían razón; yo lo subestimé.**

### El falso positivo de exfiltración en tráfico de internet (glm)

Consecuencia de desacoplar el Internal (P3): correrá también sobre tráfico de internet, donde la feature `[7]` (outbound_ratio > 2.0) dispara con cualquier descarga grande legítima (streaming, actualización de OS: forward >> backward). Mitigación de glm, elegante: el peso del Internal en el noisy-OR **modulado por dominio**, no gateado — `peso_internal = peso_base × factor_dominio` (1.0 si interno, 0.3 si externo, o lo que la medición dicte). Preserva la señal de exfiltración interna sin bloqueos espurios en internet. **Punto ciego mío y de casi todo el Consejo.**

### El falso positivo del fast-path bajo el gate B (qwen)

`final_score = max(fast, ml)`. Si el sniffer dispara (fast=0.9) y L1 dice BENIGN (ml=0.1), el veredicto es MALICIOUS **sin que ninguna cabeza corra** (gate B las bloquea). Un fast-path ruidoso genera falsos positivos sin corroboración. Recomendación de qwen: si `fast_score > malicious_threshold`, las cabezas **deben** correr aunque L1 diga BENIGN. Yo había mirado solo la dirección de falsos negativos (L1-benigno suprime cabezas); qwen añade la de falsos positivos (fast dispara solo). Buen catch.

### `fast_score` no tiene fiabilidad medible (glm GAP-002)

`fast_score` es un heurístico del sniffer, no una cabeza ML: sin F1, sin fiabilidad, no entra en `provenance->verdicts()`. Pregunta para el ADR: ¿es miembro del ensemble o pre-filtro con rol especial? Recomendación de glm (correcta): **pre-filtro / circuit-breaker.** Mantener `final = max(fast_score, noisy_or_ml)` — el fast-path es un cortacircuitos de <1ms para patrones obvios, no un clasificador probabilístico. No entra en el noisy-OR.

### Calibración de scores (deepseek)

Los scores crudos de las cabezas pueden estar **descalibrados**. El noisy-OR necesita probabilidades reales para tener semántica de probabilidad conjunta. Puede requerir calibración Platt o isotónica por cabeza. La auditoría no mencionó calibración; es un requisito real para que `pᵢ` signifique algo.

### Saturación del noisy-OR y clip de fiabilidad (glm, kimi)

- **glm:** con 3+ cabezas fiables coincidiendo, el score satura cerca de 1.0 y el threshold se vuelve un filo de cuchillo. No es defecto, es propiedad — pero exige fiabilidades bien calibradas. Documentar una **tabla de saturación** en el ADR; regla: "si se añade una 5ª cabeza con fiabilidad >0.7, reevaluar". Con la config realista inicial (Internal 0.5, DDoS 0.4, Ransomware 0, Traffic 0) no se alcanza.
- **kimi:** clip de fiabilidad mínima `pᵢ = clip(fiabilidad, ε, 1−ε) · score`, ε≈0.01, para que una cabeza medida con poquísimos datos ni se anule matemáticamente ni domine. Honesto: "no sabemos si es exactamente 0".

---

## Parte 4 — Mis ocho puntos adversarios, cruzados contra el Consejo

Honestidad simétrica: qué aguantó y qué no.

- **A1 (¿la monocapa es deuda o defensa? origen de concurrencia) — NADIE del Consejo lo tocó.** Ni una de las ocho voces preguntó por qué se desconectaron las cabezas ni si reconectarlas amenaza el determinismo. Razón justa: el informe que recibieron no incluía el dato de concurrencia (agosto 2025, 7→4 por condiciones de carrera) — eso vivía solo en mi memorándum adversario, que probablemente no les llegó. **No lo refutaron; no lo tuvieron.** Sigue vivo y **sin validar**. Es un punto ciego *compartido* por todo el Consejo. → Debe entrar en el ADR como **precondición**: establecer por qué existe la monocapa y validar la reconexión bajo TSAN antes de asumir que es puro descuido. Este es el punto que más necesita tu criterio, Alonso, porque las nueve voces lo pasamos por alto o no lo tuvimos.
- **A2 (coste agregado bajo carga, no por-flujo) — corroborado.** grok, qwen, kimi meten gates de latencia end-to-end (<10ms p99) y stress en sus planes. El Consejo confirma que la medición unitaria no basta.
- **A3 (gravedad de C acoplada a B; el bronce prueba mecanismo, no impacto) — parcialmente.** Nadie lo formuló así, pero la reordenación de glm (cablear con pesos provisionales) lo maneja de facto. El matiz evidencial (una fila ATTACK probaría el caso fuerte) sigue siendo mío y en pie.
- **A4 (insumos del noisy-OR sin medir) — fuertemente corroborado y profundizado.** deepseek (calibración), glm (saturación), kimi (clip), qwen (pesos medidos no votados) y chatgpt (¿operación siquiera type-correcta?) golpean todos aquí. Fue un buen punto; el Consejo lo hizo más fuerte.
- **A5 (la traza de `threat_category` paró antes del BatchProcessor) — abierto.** Ningún miembro leyó el BatchProcessor tampoco. Sigue sin cerrar.
- **A6 (frecuencia con que el gate muerde, sin medir) — corroborado.** grok añade el gate "% de eventos donde las cabezas cambian el veredicto vs baseline". Justo esa medición.
- **A7 (sin estrategia de aterrizaje incremental / modo sombra) — fuertemente corroborado.** glm/kimi/grok/qwen proponen PRs secuenciados con invariantes de seguridad; el PR1/PR2/PR3 aditivo de glm es una versión rigurosa de mi modo sombra.
- **A8 (riesgo de lectura parcial) — persiste como meta-riesgo.** kimi no pudo acceder al repo y deliberó sobre el informe a confianza; otros afirman haber verificado. La cobertura de verificación del propio Consejo es desigual.

---

## Parte 5 — Refinamientos al noisy-OR (casi-consenso, para el ADR)

Fusionando deepseek + glm + kimi, la fórmula que va al ADR no es la cruda del informe, sino:

```
pᵢ = clip(fiabilidad_i, ε, 1−ε) · score_calibrado_i        (ε ≈ 0.01)
P  = 1 − ∏(1 − pᵢ)     sobre cabezas que estiman P(malicioso)
final_score = max(fast_score, P)     (fast_score = circuit-breaker, NO entra en el ∏)
```

Con: `score_calibrado` = score crudo pasado por calibración por cabeza (Platt/isotónica) si se demuestra descalibración; `fiabilidad_i` = F1 medido (Internal/DDoS) o 0 declarado (Ransomware/Traffic); Traffic **fuera** del producto (estima dominio, no malicia — D5); tabla de saturación documentada; `discrepancy_score` = desv. típica de scores activos.

---

## Parte 6 — Secuencia de fase 2 reconciliada

Integrando todo. Ninguna fecha; cada paso con gate de medición.

```
PRECONDICIÓN 0 (nueva, de A1 — el punto que nadie tocó):
  Establecer POR QUÉ existe la monocapa. ¿Descuido, o retirada por concurrencia/latencia?
  Si fue concurrencia: la reconexión es un gate de TSAN, no un refactor cualquiera.
  Gate: causa histórica documentada + plan de validación TSAN.

PASO 0 (nuevo, de glm/qwen — el detonador latente):
  Fix DEBT-RING-CONSUMER-BACKWARD-ZERO-001 (backward_bytes=0 en fast-path).
  SIN esto, el des-gateo del Paso 2 convierte cada flujo fast-path en falso positivo de exfiltración.
  Gate: fix en main + test que verifique que [7] no dispara con backward ausente.

PASO 1 — Decisiones de cabezas (D1, D2, D3):
  MEDICIÓN QUE DECIDE: granularidad de NetworkFeatures (flujo vs agregado en ventana).
    → decide si Traffic/Ransomware son recuperables o requieren nuevo contrato de entrada.
  Ransomware: peso 0 con status DISABLED_UNRELIABLE (glm), score suprimido. No cablear al veredicto.
  Traffic: FUERA del noisy-OR (D5 — estima dominio, no malicia). Dominio por lookup determinista.
  Internal: cablear, peso PROVISIONAL 0.3 declarado ("cable verificado, discriminación no medida").
  Gate: decisión documentada por cabeza con su razón técnica.

PASO 2 — Cableado (Defectos A+B+C), con la secuencia de PRs de glm (D4):
  PR1 (ml-detector): noisy-OR sobre provenance + mover persistencia post-cabezas +
                     poblar ml_context desde cabezas (elimina DEBT-RAG-4) +
                     campo NUEVO attack_detected_ensemble() (no tocar el viejo) +
                     Internal con peso modulado por dominio (glm, evita FP en internet).
  PR2 (firewall): gate = ensemble || L1 (cinturón y tirantes).
  Relajar gate B: si fast_score > threshold, las cabezas corren aunque L1 diga BENIGN (qwen).
  Tests del combinador: (a) una dispara, (b) dos corroboran, (c) fiabilidad-0 no envenena,
                        (d) golden v2 verdes, (e) saturación dentro de tabla.
  Gate: tests verdes + TSAN limpio (precondición 0).

PASO 3 — Pulso del Internal (5.2b-i): F1 real sobre datos MITRE/Atomic etiquetados.
  Ajustar peso 0.3 → F1 medido. Gate: número existe.

PASO 4 — Stress + latencia agregada bajo carga (A2): 4 cabezas × 100% flujos a tasa de línea.
  % de eventos donde las cabezas cambian el veredicto (A6). Gate: p99 < 10ms; sin sobre-bloqueo.

PASO 5 — pcap relay e2e en hardware propio: TTL real. Número de "hardware suelo" para el paper.

PASO 6 — PR3: eliminar fallback a L1 en el firewall (tras validar N días).

PASO 7 — Paper: config honesta (qué cabeza pesa cuánto), Ransomware/Traffic declaradas
          con su razón técnica. Limitación = hueco de cobertura, NO divergencia predicha.
```

---

## Cierre — lo que solo tú puedes decidir ahora

El Consejo convergió en casi todo el cableado (A) y te deja tres decisiones y una medición:

1. **La medición que desbloquea D1 y D2:** ¿qué granularidad tiene `NetworkFeatures` — un flujo o un agregado en ventana? Es un `grep` del proto y del sniffer. Decide si Traffic y Ransomware son reparables o son cabezas nuevas. **Es la próxima medición natural.**
2. **La precondición que nadie del Consejo tuvo (A1):** ¿por qué existe la monocapa? Si la respuesta es "concurrencia", reconectar las cabezas es un gate de TSAN, no un refactor. Ninguna de las nueve voces lo validó — es nuestro punto ciego compartido, y por eso es donde más falta tu criterio.
3. **Las decisiones de política** que el Consejo dejó abiertas: peso-0-con-status vs ausencia (recomiendo la síntesis de glm), atómico vs secuenciado (recomiendo secuenciado-aditivo de glm), y si aceptas la lectura de chatgpt de sacar Traffic del noisy-OR por estimar otra variable.

El acuerdo de fondo de las nueve voces es rotundo y coincide con tu listón: **el cableado (A) se arregla ya, con honestidad; la fiabilidad de las cabezas (B) se persigue con transparencia y datos, declarando cada límite con su razón técnica.** Nadie bajó el listón. Ransomware y Traffic no se maquillan: se declaran rotas con el porqué, y el paper dice la verdad medida.

*Reconciliado por Claude, novena voz — que también tuvo su punto ciego (el `backward_bytes`), cazado por glm y qwen. El escudo conoce mejor sus sombras cuando nueve pares las buscan a la vez.*