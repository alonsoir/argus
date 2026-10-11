# Notas para el paper — DAY290 (cabeza DDoS, sniffer)

## 1. Skew train/serve inducido por la cola (hallazgo de método)
- En el diseño original, los rasgos de flujo se fotografiaban en un hilo de rasgos situado DETRÁS de una
  cola sin límite. Bajo carga, la foto incluía paquetes posteriores al evento juzgado: el valor de
  `flow_packet_count`, de la media y de `victim_*` dependía de la carga del sensor, no solo del tráfico.
- Consecuencia: un dataset generado a baja tasa y un despliegue bajo flood fotografían en instantes
  distintos ⇒ skew silencioso, de la misma familia que el skew de geo (DAY255), pero temporal.
- Arreglo: foto en el hilo de captura en el instante del paquete, con estadísticos incrementales.
  Verificación: 2135 comparaciones, igualdad BIT A BIT con la extracción de lote de producción
  (media por suma exacta; entropía con el mismo std::map y la misma acumulación float).
- Principio: "más tarde" no es "más real"; el valor de un evento es el estado en su instante.

## 2. La unidad de emisión no reduce los floods realistas
Filas por flujo en el dataset DAY289 (syn/dns/ntp): 98–100 % de flujos de un paquete. Emitir una vez por
flujo reduce el volumen 0–2 % en esas familias (97,8 % en udpA, que concentra el ataque en 198 tuplas).
La firma de un flood con puertos aleatorios vive en el agregado por víctima; la reducción de volumen,
si se busca, tiene que ser por víctima (contrato distinto), no por flujo.

## 3. Cuello del consumidor: contención, no trabajo propio
- perf (cpu-clock, DWARF) + contadores del kernel por hilo (/proc): a 1000 pps el hilo de rasgos ocupa
  ≈1 núcleo haciendo una pasada O(ventana) bajo el mutex de un agregador compartido; el hilo que vacía el
  anillo gasta <5 % y se bloquea esperando ese mutex.
- El vector DDoS v2 no lee ese agregador: el coste lo imponen rasgos de otras cabezas. Lección: compartir
  un agregador entre cabezas acopla sus fallos de rendimiento.

## 4. Variabilidad cerca de la saturación (honestidad de las cifras)
- RESERVE_FAIL a 1000 pps con el MISMO binario: 43,3 % y 28,7 % en dos corridas. A 100 pps: 0 % y 0 %.
- Cerca del límite de capacidad, el sistema amplifica el ruido de planificación de la VM: una corrida
  aislada no permite atribuir causas. Cifras de techo solo con ≥3 corridas, dispersión, y en hardware real.

## 5. Herramientas que discrepan
- `top -H -p PID` atribuyó 41–67 % de CPU al hilo principal; perf no tenía muestras suyas; el kernel
  (/proc/PID/task/TID/stat) dio 0,0 %. Regla adoptada: ante discrepancia entre herramientas, árbitro =
  contadores del kernel por hilo.
- El gate de tests usaba por defecto otro perfil de build: un "100 % passed" sobre un binario que no
  contenía el cambio. Regla: compilar y probar con el mismo perfil.

## 6. Memoria por flujo
1,7–2,2 kB por flujo de un paquete (RSS medido con 5000 y ~9800 flujos), sin liberación (no hay
expiración). Con la LRU de 160 000 flujos, techo ~270–350 MB; bajo flood la LRU expulsa estado legítimo.
