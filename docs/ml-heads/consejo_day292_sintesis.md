# Consejo DAY292 — síntesis y decisiones de Alonso (árbitro)

Respuestas: ChatGPT, Meta, Mistral, DeepSeek, Grok, Gemini. Pregunta: docs/ml-heads/consejo_day292.md.

## Consenso (6/6)
- Candidato de la familia RELATIVA (sin victim_pps); el umbral absoluto aprendido por B se descarta (artefacto del lab).
- Víctima fría: el modelo NUNCA bloquea con la clave fría; cualquier regla fría va fuera del modelo, como política declarada.
- Diversificar el dataset es necesario pero no suficiente: solapar tamaños, base mixta UDP+TCP, varias escalas, tasas no
  vistas, perfiles temporales. Criterio de aceptación: dejar una familia fuera.
- El firewall nunca actúa por paquete: agregación (estado de víctima, k de n, ventanas consecutivas), mitigación reversible
  antes de bloqueo duro. Métrica: FP por EVENTO de bloqueo, no por fila.
- Comparar árbol poco profundo y regla explícita con el bosque en las mismas particiones; quedarse con lo más simple que
  pase las puertas.

## Discrepancias y resolución
- Cablear ya (5) vs dataset antes (Grok): se cablea en SOMBRA, después de decidir la forma del modelo (bloque 1b).
- Arranque (DeepSeek: error; 5: válido si se evalúa aparte): fuera del entrenamiento, DENTRO del test; recall@t y latencia
  en caliente y en frío por separado.

## No adoptado (contradice lo medido)
- Meta: el FP del bosque viejo venía de flow_completion_rate → FALSO; DAY281 midió que decidía por escalation
  (bytes/s del flujo con umbrales MinMax frente a valores crudos).
- Gemini: la respuesta DNS de 1442 B era error de etiqueta → FALSO; era benigna (corrida de contraste), FP genuino.
  Gemini sitúa la inferencia en eBPF → es en el ml-detector.
- DeepSeek: τ=3600 s deja la EWMA alta una hora → REFUTADO para ataques de 90 s (tramo 10: ratio 0,98-1,0, sale del estado
  y vuelve a α rápido). Vale para ataques LARGOS → batería v3.
- ChatGPT: auditar causalidad temporal de rasgos → ya cubierto por diseño: el dataset lo escribe el código de servicio con la
  foto en el instante del paquete (DAY290); sin información futura ni skew train/serve. Se dirá en el paper.

## Lo que se nos había pasado (adoptado)
1. Víctima fría con ataque SOSTENIDO: la EWMA lo absorbe con α rápido antes de llegar a 30 ventanas ⇒ hipótesis: no se
   detecta nunca. SE MIDE (bloque 1d) y se publica.
2. En reflexión el origen visible es un reflector (a menudo legítimo): la mitigación (drop temporal) es POR VÍCTIMA, no por
   origen. Choca con el firewall-acl-agent actual (bloqueo por IP de origen con reincidencia) → diseño en el PR del firewall.
3. Una semilla y un split no bastan: repetir con varias semillas y varios splits por corrida, con intervalos.
4. Tasas no vistas por interpolación (45/75/150), inocente ruidoso durante el ataque, varias víctimas → batería v3.

## Decisiones de Alonso (DAY292)
- D5 Forma del modelo: la decide la medida del bloque 1b (árbol de profundidad 2-4, regla explícita, bosque 10-100 árboles
  y profundidad 4-14), sobre las mismas particiones; candidato de partida B sin victim_pps.
- D6 El modelo no bloquea mientras la clave esté fría.
- D7 Orden: bloque 1 offline → bloque 2 cablear en sombra (el cableado se irá actualizando al añadir cabezas) → bloque 3
  batería v3 (propuesta en docs/ml-heads/bateria_v3_propuesta.md).
- D8 El PR cierra con el firewall en SOMBRA: registra final_decision y lo que habría bloqueado, sin bloquear.
- D9 Arranque fuera del entrenamiento, dentro del test; latencia caliente y fría publicadas por separado.
- No se adopta nada que contradiga lo ya medido.

## Adenda: GLM (7.ª respuesta)
Aporta (adoptado, a medir):
- Aritmética del frío: la EWMA absorbe el ataque con α rápido; techo de recall ~4-5 % (medido 8-13 %, código antiguo).
  PREDICCIÓN GLM: EWMA congelada en el suelo hasta 30 ventanas ⇒ recall frío 60/100 pps ~90-100 % sin tocar el modelo.
  ⇒ bloque 1d: simulación offline primero; después re-captura del frío con el binario actual (las corridas frías son de DAY288,
  anteriores a la foto DAY290 y a la histéresis DAY291) + subida legítima en clave joven para medir el coste de congelar.
- Modelo FACTORIZADO: etapa 1 = estado de presión (regla sobre la EWMA); etapa 2 = clasificador entrenado solo con filas en
  presión (atacante frente a inocente). PREDICCIÓN GLM: regla de ratio sola ⇒ colateral ~100 %. ⇒ bloque 1b (plano frente a
  factorizado).
- AUC por rasgo (stump) como salud del dataset: ningún rasgo solo > 0,9. ⇒ bloque 1b.
- Rampas lentas: ratio ≈ 1 + 1/(αT); T ≥ 10 s nunca entra en presión ⇒ medir en v3 o declarar fuera de alcance.
- Disyuntor de saturación (> 20 % marcado > 10 s ⇒ alarma y solo modo suave). ⇒ bloque 1c y E2E.
- Puertas de cableado: determinismo, umbrales con precisión completa, política de valores degenerados; sonda de encapsulación
  (+4/+24/+78 B en mean_packet_size).
- Rasgo victim_src_newness (contrato v2.1): necesita ataques multi-origen que el lab no tiene hoy ⇒ BACKLOG.
- Alcance declarado: cabeza volumétrica/reflexión; slowloris y baja tasa aplicacional fuera.
No adoptado / matizado:
- "Falta el colateral": ya se mide en todas las evaluaciones (FP inocente durante, también en familia fuera).
- "Flujos de ataque 5-9·10³ paquetes": falso (ntp/dns/syn ~1, udpA ~50; lo largo es la base TCP inocente). El riesgo real es
  el inverso: "flujo largo = benigno".
- log1p de flow_packet_count: sin efecto en árboles (invariantes a transformaciones monótonas); se cruza en el dataset.
- Tier duro por par origen→víctima: se evalúa en 1c; la mitigación decidida sigue siendo POR VÍCTIMA (D de Alonso).
