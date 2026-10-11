# Consejo de Sabios — DAY294: cabeza DDoS v2 en SOMBRA, medida en vivo

Árbitro humano: Alonso. Regla: medir, no votar. Cada respuesta debe proponer una MEDIDA concreta y una PREDICCIÓN escrita
(número esperado y qué la refutaría). Las opiniones sin medida asociada se registran pero no deciden.

Adjuntos (leer en este orden):
1. `bloque1_day293.md` — análisis offline: intervalos por corrida, formas de modelo, política del firewall, víctima fría.
2. `bloque2_day294.md` — cableado en sombra y medidas en vivo.
3. `bateria_v3_propuesta.md` — propuesta de la siguiente batería.
4. `consejo_day292_sintesis.md` — lo que decidisteis la vez anterior (D5-D9) y cómo se aplicó.

## Qué se ha hecho desde vuestra última revisión (DAY292)

Se aplicó vuestra síntesis: la forma del modelo se decidió por medida, el modelo no bloquea con la clave fría, la
mitigación es POR VÍCTIMA, y el PR cerró con el firewall en SOMBRA. Resultado, mergeado en main con la etiqueta
`pre-release-ddos-only-0.0.3` y EMECAS+++ en verde:

- **Contrato v2 (8 rasgos calculados UNA vez en el sniffer, solo tráfico entrante):** syn_ack_ratio, mean_packet_size,
  reflection_signature, packet_size_entropy, flow_packet_count, flow_completion_rate, victim_rate_ratio, victim_pps.
  victim_rate_ratio = tasa de la víctima / EWMA por víctima con histéresis (K_in=3, K_out=1,5, τ=3600 s, caliente a
  partir de 30 ventanas, suelo 10 pps).
- **Modelo FACTORIZADO** (ganó por medida a la regla, al árbol único y al bosque plano):
  - Etapa 1: victim_rate_ratio >= K (K=3, global, en el JSON del ml-detector).
  - Etapa 2: RandomForest de 100 árboles sobre los 6 rasgos de flujo, entrenado SOLO con filas bajo presión, con el
    arranque del atacante (~2 s) fuera del entrenamiento (se mide aparte como latencia).
  - Exportado a C++ con umbrales crudos. Paridad Python/C++: 127930/127930.
- **Firewall en SOMBRA:** compuerta por final_decision (level1 ya no decide), DdosShadowPolicy POR VÍCTIMA:
  m=5, k/n=3/5, hold=30 s (defectos de LABORATORIO, en el JSON con rangos). Registra INICIO/FIN; no bloquea.

## Medido en vivo (DAY294, relojes de las VMs sincronizados por NTP)

E2E de ataque (reflexión NTP .50 -> .1 a 60 pps durante 90 s, con un inocente concurrente .51 -> .1 a 10 pps):
| Medida | Valor |
|---|---|
| Primer DROP tras el inicio del ataque | ~1,3 s |
| INICIO de la sombra tras el primer DROP | 2 s de reloj de eventos (k=3 ventanas) |
| FIN tras el último DROP | 29,3 s (hold=30) |
| Eventos DROP | 5357, todos de 192.168.100.50 |
| Eventos DROP del inocente concurrente | 0 |
| p1 mínimo / ratio máximo | 0,96 / 7,05 |

Corrida benigna que PRESIONA la etapa 1 con tráfico nunca visto en entrenamiento (base .51 durante 450 s + dnsperf real
contra el resolver del lab a 30 y 100 consultas/s + subida TCP legítima de 50 KB/s):
| Tramo | Filas bajo presión (etapa 1) | Positivos etapa 2 | INICIO |
|---|---|---|---|
| dns 30 q/s | ~3600 | 1 | 0 |
| dns 100 q/s | ~9900 | 1 | 0 |
| TCP 50 KB/s | ~4500 | 0 | 0 |
Los 2 positivos son aislados; la política k=3 de 5 los absorbe. El bosque viejo (antes de esta rama) marcaba como
ataque el 100 % de una subida TCP legítima de 50 KB/s.

## Límites conocidos (medidos, no ocultos)

- La etapa 2 aprende FIRMAS de nuestros generadores (tamaño de paquete + firma de reflexión), no comportamiento. Con una
  familia fuera del entrenamiento: sin ntp detecta ~0 %; sin syn marca ~99 % del TCP inocente.
- Sensibilidad a la encapsulación (sonda +4/+24/+78 B en mean_packet_size): ver bloque1_day293.md.
- Víctima fría (menos de 30 ventanas de historia): el modelo NO bloquea por diseño; queda para una regla fría del admin.
- Fast-alert fuera de la decisión. El firewall no bloquea: la mitigación real es otro PR.
- Lab: VirtualBox en un portátil, tasas <= ~110 pps sin pérdidas en el anillo. Nada de esto es hardware real.

## Hallazgos nuevos de DAY294 que afectan a lo siguiente

- **Dos bases de tiempo en event_timestamp:** los eventos de flujo llevan reloj MONOTÓNICO (desde el arranque, el de
  eBPF) y otros eventos llevan epoch. Ya ha mordido tres veces: congeló el reloj de la sombra (corregido usando solo
  eventos de flujo), dejó el 99 % de las filas de un día de logs fuera de rango en Parquet, y bajo dns100 el reloj de
  eventos de la sombra avanzó ~0,55 s por segundo de pared y luego recuperó de golpe (¿cola o semántica?).
- Hoy hemos activado `makestep 1 -1` en chrony (salto de reloj de pared si el desfase pasa de 1 s). Eso protege los
  logs, pero hace que el reloj de PARED pueda saltar en cualquier momento.
- Bajo carga DNS el firewall recibe ~37 eventos/s que no son de flujo (antes ~1 cada 30 s). Tipo aún sin identificar.

## Preguntas

**P1. Etapa 2 por comportamiento.** ¿Qué rasgos POR VÍCTIMA o POR ORIGEN harían que la etapa 2 generalice a familias no
vistas, en vez de memorizar tamaños? Candidatos nuestros: número de orígenes distintos por víctima en la ventana
(source_ip_dispersion redefinido por víctima), cuota del origen sobre la tasa de la víctima, asimetría petición/respuesta.
Pedimos: qué rasgo, cómo se calcularía en el sniffer sin coste por paquete, y qué resultado de "familia fuera" predecís.

**P2. Batería v3.** ¿Basta `bateria_v3_propuesta.md` (generadores con tamaños aleatorios, base mixta UDP+TCP, bases de
distinto volumen, tasas no vistas 45/75/150) para medir P1, o falta un eje? ¿Qué corrida concreta la refutaría?

**P3. Valores por defecto para un cliente real.** K=3 y m=5, k/n=3/5, hold=30 s son de laboratorio. ¿Cómo se fijan con
el personal de un hospital? ¿Qué medida previa en su red (cuánto tiempo, qué percentiles de victim_rate_ratio) y qué
criterio de aceptación? ¿Defectos fijos documentados o calibración inicial automática con aprobación humana?

**P4. Mitigación real por víctima.** La sombra dice CUÁNDO una víctima está bajo ataque. ¿Qué se hace entonces sin
castigar al inocente concurrente? Opciones: (a) limitar la tasa total hacia la víctima; (b) descartar solo los flujos que
la etapa 2 marca, por origen y durante el hold; (c) filtrar por firma (puerto origen de servicio + tamaño) mientras dure el
estado. ¿Cuál, y qué medida en el lab demostraría que el inocente .51 sigue pasando?

**P5. Base de tiempo única (siguiente PR).** Opciones: (a) epoch en todo, convirtiendo en espacio de usuario con un
ancla realtime-monotonic; (b) monotónico para ordenar y medir duraciones + ancla de arranque para cruzar nodos;
(c) bpf_ktime_get_tai_ns en el kernel (Debian 12, kernel 6.1). Con `makestep 1 -1` el reloj de pared puede saltar: ¿cuál
elegís para que `time_to_block`, los hold y el grafo no se rompan con un salto, y qué prueba lo demostraría?

**P6. Disyuntor de saturación.** Si la tasa supera lo que una instancia procesa sin pérdidas (en el lab ~110 pps sin
pérdida en el anillo), ¿qué debe hacer el sistema: degradar a una regla barata por víctima, avisar, o ambas? ¿Con qué
umbral y medido cómo?

## Formato de respuesta

Por pregunta: recomendación en una línea; medida propuesta; predicción numérica; qué la refutaría. Máximo una página por
pregunta. Si algo de lo medido os parece mal medido, decid cómo lo mediríais vosotros.
