Consejo convocado. Día 292 es el día donde dejáis de hacer un clasificador y empezáis a hacer un detector de régimen. Lo que tenéis es bueno, pero está aprendiendo mal por razones correctas.

Voy punto por punto, con qué medir para decidir, no con voto.

### 1. B vs B sin victim_pps vs híbrido

**Tenéis razón: B sin victim_pps es el candidato correcto para hospital.**

Por qué B es peligroso:
B aprendió `victim_pps > 35`. Eso es un artefacto de vuestro lab: benigno máximo 20 pps, ataque mínimo 30 pps. En producción un hospital a las 09:00 puede tener `victim_pps = 200` benigno hacia un PACS. B bloquearía todo. El fallo es silencioso y no acotable. El umbral absoluto depende de la escala absoluta de tráfico que pongáis en el lab, que nunca será la de producción.

Por qué B sin victim_pps es defendible:
Aprendió `victim_rate_ratio > K` + firma. Eso es **relativo a la historia de esa víctima**. Eso es exactamente para lo que diseñasteis la EWMA con histéresis. Su fallo en frío es explicable, acotable y medible: si la clave `{IP, proto}` tiene <30 ventanas, está en frío, no puedes usar ratio. No es un fallo silencioso, es un estado del sistema.

**Propuesta híbrida que sí vale para frío:**

No es `victim_pps > 35`. Es una regla de admisión para régimen frío:

```
if key.windows_seen < 30:
  # No hay historia, no uses ratio
  decision = ALLOW # nunca BLOCK por paquete
  alert_level = SUSPECT if (reflection_signature && mean_packet_size in [firma]) else 0
else:
  decision = forest_B_sin_victim_pps(packet)
```

En frío nunca bloqueas, solo observas. Eso cumple "cero falsos bloqueos". Cuando la víctima entre en presión, ya tienes historia.

Medid esto:
- `cold_duration = tiempo hasta windows_seen >= 30` para cada víctima real del hospital en 7 días de espejo (sin bloqueo). Si es <5 min, el híbrido es suficiente.
- Si necesitáis detectar en frío sí o sí, la segunda regla fría debe ser `flow_packet_count + syn_ack_ratio + packet_size_entropy`, nunca `victim_pps` solo.

Conclusión: **Cablead B sin victim_pps + puerta de frío en ALLOW.**

### 2. Dependencia de firma: estáis aprendiendo los generadores

El dato demoledor es: `sin NTP recall ~0%`. Eso es overfitting de generador, no de DDoS. Y `mean_packet_size` dominando lo confirma.

Vuestro dataset actual tiene:

* Ataque: `size = const por familia` (NTP=~500, DNS=~1420, etc)
* Benigno: `size = distinto` (DNS pequeño, DNS grande)

El bosque hace lo óptimo: `if packet_size == 1420 -> DDoS`. Es un clasificador de tamaño.

**Dataset que rompe eso:**

Necesitáis solapar las distribuciones a propósito.

1. **Randomizar tamaños en ataque:** no 1420 fijo. `size ~ Uniform(1200, 1450)` + jitter por fragmentación real. Para SYN: `size ~ 60 +- 20` con opciones TCP reales.
2. **Benigno con mismos tamaños:** Generad tráfico benigno que ocupe exactamente los mismos buckets de tamaño que el ataque. iPerf UDP de 1400B a 20 pps, backups DNS de 1420B, transferencias NTP legítimas. Si no solapa, no aprende comportamiento.
3. **Base mixta obligatoria:** Vuestra base benigna actual es pobre. Necesitáis:
    - TCP benigno con SYN/ACK real (subidas de 10KB/s, 100KB/s, 1MB/s). Ahora mismo sin SYN no tenéis TCP benigno, por eso marca 99% TCP inocente como SYN flood. Grave.
    - UDP benigno a 10/50/200 pps hacia la misma víctima. No solo 10 pps. El bosque debe ver 200 pps benigno y decir ALLOW.
    - Tráfico cruzado:.50 atacando,.51 benigno alto al mismo tiempo hacia.1. Ya lo hacéis, mantenedlo.
4. **Etiqueta por paquete, no por IP:** Ahora mismo si.50 es atacante, todo lo de.50 es ataque, aunque.50 haga DNS pequeño benigno de contraste. Eso contamina. Etiquetad por `(IP origen, flujo 5-tupla, tiempo)` con ventana de ataque exacta.

Experimento para medirlo:
Haced `permutation importance` por familia dejada fuera + `partial dependence` de `mean_packet_size`. Objetivo: cuando dejáis una familia fuera, recall >80% y la importancia de `mean_packet_size` debe caer de #1 a #3 o #4, subiendo `syn_ack_ratio` y `flow_completion_rate`.

Si no, no cableéis familia nueva hasta que eso pase.

### 3. ¿Cablear ya o iterar dataset antes?

**Cablead ya, pero detrás de feature flag y con puertas.**

Razón: vuestro contrato de rasgos v2 + histéresis EWMA + cálculo una vez en eBPF es lo más difícil y lo tenéis bien. El bosque B sin victim_pps es pequeño (3714 nodos, profundidad 14) -> cabe en L1, latencia predecible. Si no lo cableáis ahora, no vais a medir paridad Python/C++ real ni latencia por paquete E2E con XDP.

Puertas que propongo, en orden:

1. Paridad: mismo vector de rasgos en Python y C++ para 10k paquetes de pcap hospital. `diff < 1e-6`. Si falla, no hay modelo que valga.
2. Umbrales crudos: loguead `victim_rate_ratio`, `flow_completion_rate` crudos sin bosque durante 24h en hospital espejo. Verificad que benigno no llega a 3 de forma sostenida.
3. Tamaño/latencia: `ml-detector < 500ns p99 por paquete`, bosque < 50KB generado.
4. Cero bloqueos E2E en laboratorio con vuestros 19 corridas + TCP benigno de 10KB/s que antes daba 100% FP.

Una vez pase puertas, iterad dataset en rama `dataset-v3`. No bloqueéis el pipeline de integración por dataset.

### 4. Política de agregación por paquete -> bloqueo

Decisión por paquete no puede ir directa a firewall en hospital. Necesitáis dos acumuladores desacoplados:

**Nivel víctima (¿estamos bajo ataque?):**
`victim_ratio >=3` durante `T_victim = 1s` (3 ventanas seguidas) -> estado `VICTIM_UNDER_PRESSURE`. Esto ya lo tenéis con histéresis. Publicadlo como métrica, no como bloqueo.

**Nivel origen (¿quién atacá?):**
Solo si `VICTIM_UNDER_PRESSURE == true`:
Contador por `{victim, attacker_ip}` deslizante de 1s: `k de n`. Ej: `n=50 paquetes, k=35 marcados por bosque`. Si supera, `BLOCK attacker_ip -> victim_ip` por 60s, con decaimiento exponencial.

Esto os da:
- Un benigno.51 a 10 pps nunca llega a k=35, aunque haya 1 FP por bosque (0.78% de antes).
- Un atacante a 30 pps llega en ~1.2s. Latencia medida, no teórica.
- Cero bloqueos si víctima no está bajo presión.

Métrica a reportar: `time_to_block` distribución + `FP_block = 0` en 7 días de tráfico hospital espejo. Si `FP_block >0`, subid k o exigid `VICTIM_UNDER_PRESSURE` durante 2s.

### 5. ¿Árbol poco profundo o regla explícita?

Sí, probadlo. Bosque de 100 árboles para esto es overkill y oscurece.

Experimento:

* Regla explícita: `if victim_ratio > 4.0 AND (reflection_signature OR syn_ack_ratio > 0.8) AND flow_completion_rate < 0.2 -> SUSPECT`
* Árbol de profundidad 3 entrenado solo con `victim_rate_ratio, syn_ack_ratio, reflection_signature, flow_completion_rate` (sacad los de tamaño).

Comparad en:
- Recall fuera de arranque en test (el mismo que usáis)
- FP por millón de paquetes benignos hospital
- Explicabilidad: ¿podéis escribir en 1 párrafo por qué bloquea?

Si la regla explícita está a <2% del bosque en recall con 0 FP block, **quedaos con la regla**. En crítico, un árbol de 8 nodos auditable vale más que 3714 nodos. Vosotros queréis certificar esto algún día.

### 6. ¿Sacar los 2 primeros segundos del entrenamiento?

**Sí, es correcto, pero publicadlo como lo que es: latencia de calentamiento del rasgo, no latencia del modelo.**

Esas filas son indistinguibles porque `victim_pps` y `victim_rate_ratio` aún miran a la ventana anterior. Entrenar con ellas obliga al modelo a inventar. Quitarlas es honesto.

Lo que debéis hacer:

* En la ficha del modelo: `detection_latency = max(ventana_rasgo, k_de_n) = 1s + 0.5-1.5s = 1.5-2.5s`. No digáis "recall 100%".
* En eval frío: reportad `recall@t` para `t = 0-0.5s, 0.5-1s, 1-2s, >2s` por separado. Ahora todos vuestros fallos están en 0-1.4s, es informativo.

No enmascara nada si lo medís así.

### 7. ¿Qué se os ha pasado?

Tres sesgos gordos:

1. **Fuga por escala temporal:** Entrenáis y testeáis con mismas tasas (30/60/100). El modelo aprende esas tasas. Testeáis con 60 pps (visto) y el frío falla en 30 pps. Test debe ser con tasas NO vistas: 45, 75, 150 pps. Si no, no sabéis si generaliza.
2. **Etiqueta por IP origen = fuga de identidad:** Si.50 siempre es malo en ventana de ataque, el modelo puede aprender patrones de.50 (TTL, puerto efímero) aunque IP no sea rasgo. Aleatorizad puertos origen y aseguraos de que.50 también genera benigno en la misma corrida.
3. **Métrica de FP mal contada:** Contáis filas, no eventos de bloqueo. 6 FPs en 0.5s suenan poco, pero si esos 6 hacen `k de n` -> bloqueáis IP inocente. Medid `FP_block_event`, no `FP_row`.

Y una última: el bosque anterior que marcaba 100% de subida TCP legítima y 0% SYN flood es síntoma de que `flow_completion_rate` no estaba bien calculado en kernel vs Python. Revisad paridad de ese rasgo en concreto antes de nada.

Resumen ejecutivo para cablear:

**Candidato: B sin victim_pps + puerta fría en ALLOW + agregación `k=35/n=50` solo bajo `VICTIM_UNDER_PRESSURE`. No cableéis B con `victim_pps`. Iterad dataset-v3 con tamaños solapados y TCP benigno real.**

Si queréis, os genero el script de evaluación `recall@t` y `FP_block` para vuestras 19 corridas.