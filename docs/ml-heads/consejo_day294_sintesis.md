# Síntesis del Consejo DAY294 y decisiones del árbitro

Respuestas: ChatGPT, DeepSeek (Gauss), Gemini, Grok, Meta, Mistral, z (Mireia/Bruno/Yasmin/Teo), "gpai".
Calidad: 4 de 8 no recibieron los adjuntos (respondieron solo sobre el texto); la próxima vez, pegarlos en el mensaje.
La más sólida, z; después DeepSeek. Gemini, sin auditoría y con P5 (TAI) refutada por z.

## Auditoría aceptada (lo que nos tumban)
- A2 (6/8): el "0 del inocente" no prueba discriminación por origen: la etapa 2 decide por tipo de tráfico. Un gemelo
  del atacante (mismos paquetes, otra IP) debería salir marcado (predicción de Claude: > 90 % de sus filas bajo presión).
  Afirmación correcta: "discrimina el tipo de tráfico, no el comportamiento del origen".
- A1 (z): contabilidad. CORRECCIÓN: el primer DROP llega 0,8-1,8 s tras el inicio del ataque (el "~1,3 s" se calculó con
  ts_s truncado; el id del evento da 5124,461 s). Máximo de DROP posibles 5292-5352; medidos 5357: posibles duplicados.
- A5 (z): con un ataque largo la EWMA podría absorberlo, el ratio bajar de K=3 y la sombra dar FIN en mitad del ataque.
  Solo hay ataques de 90 s medidos.
- A6 (z): el lab solo mide víctimas en el suelo de 10 pps; la latencia no se traslada a bases calientes altas.
- A4 (casi todos): el 0,55x del reloj de eventos y los 37 eventos/s exigen medir retraso de cola y eventos por tipo.

## Decisiones (Alonso: se hace todo)
- D15 Medidas de auditoría: A1 (pcap en .1 frente a eventos DROP), A2 (gemelo .61 a 10 y 60 pps), A5 (ataque largo,
  primero offline con d291_histeresis_offline.py). Se ejecutan al FINAL de fix/event-timestamp-timebase, ya con relojes
  fiables, como prueba de aceptación.
- D16 P5 = (b): reloj monotónico (MONOTONIC o BOOTTIME, se decide midiendo la suspensión del portátil) como única base
  para ventanas, hold, time_to_block y orden; epoch solo en los bordes (Parquet, logs, UI) vía ancla por nodo; re-anclaje
  y evento CLOCK_STEP al detectar un salto de pared; boot_id, node_id, secuencia por productor y versión del contrato.
  (c) TAI descartada: TAI = realtime + desfase, salta igual con makestep. Prueba: saltos de pared de +-5 s en mitad de
  un ataque; hold 30 +- 0,1 s, orden intacto, Parquet 100 % en rango.
- D17 En el mismo PR: retraso enq/deq en los eventos y contadores por tipo de evento (explica el 0,55x y los 37/s);
  la secuencia por productor detecta duplicados (A1).
- D18 Batería v3 + ejes: gemelo, distribuido (N orígenes), borde (base caliente 30 pps), saturación medida aparte,
  familia fuera estricta. Rama nueva, después de D16-D17.
- D19 P1: rasgos por víctima y por origen al cerrar la ventana (cardinalidad de orígenes por víctima, cuota del origen
  principal, delta del origen frente a su EWMA, orígenes nuevos), memoria acotada; source_ip_dispersion redefinido por
  víctima. Asimetría petición/respuesta descartada (el contrato v2 solo ve tráfico entrante).
- D20 P4 aplazado hasta familia fuera > 60 %; después comparar en el lab (b) descarte por origen, limitación jerárquica
  (cupo por víctima + por origen) y (a), con gemelo e inocente. (c) firma descartada.
- D21 P6: degradar y avisar; umbral por retraso de cola o pérdida del anillo (no pps); escalera de carga medida; modo
  degradado = etapa 1 + regla barata por víctima (nunca marcarlo todo).
- D22 P3: método de calibración preparado ya (14 días en sombra, K por víctima desde p99,9, replay con adjudicación
  humana, configuración versionada con aprobación; nada cambia solo en producción). Los números, con el cliente.

## Orden
1. fix/event-timestamp-timebase: D16 + D17, y al final D15 como aceptación.
2. Rama nueva de medidas y modelo: D18, D19, D21; D20 al final.
3. D22 en paralelo cuando haya cliente.
