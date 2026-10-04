# Notas para el paper — material generado en DAY287

Para integrar cuando se retome la escritura (arXiv:2604.04952). Todo MEDIDO, con ruta de reproducción.

## A. Método: dataset recogido por el mismo código de inferencia (contribución de método)
En vez de entrenar sobre columnas precalculadas de un dataset externo, aRGus recoge el vector de
rasgos EXACTO que el detector consume en serving, una fila por evento, en el propio ml-detector
(escritor de laboratorio header-only, apagado en producción). Cada fila lleva además el veredicto del
modelo anterior sobre esa misma fila, como línea base incorporada. Esto cierra el lazo train/serve por
construcción: cualquier divergencia de contrato aparece en el dataset, no en producción.
Verificación de integridad: cruce 1:1 con el bronce correlation_v1 por community_id+timestamp.

## B. Realismo de la replicación de un dataset de flujo en un NDR vivo (limitación honesta)
Replicar CICDDoS2019 a través del pipeline revela supuestos que un dataset de flujo oculta:
1. Solo está el día de entrenamiento (01-12); los chunks cubren ~2 h de las ~6,75 del día, con solo
   dos familias de ataque disponibles, ambas UDP volumétricas (flood 440 B y flood fragmentado ~4 KB).
2. El tráfico de ataque de CIC NO lleva el puerto de servicio como origen. Consecuencia: un rasgo de
   firma de reflexión (puerto de servicio conocido → puerto alto) NO puede activarse nunca sobre CIC,
   aunque en una reflexión real (NTP sport 123, DNS sport 53) sí lo hace. Entrenar solo con CIC
   enseñaría al modelo que ese rasgo es irrelevante. Se cubre generando reflexiones reales en el lab.
3. Alineación necesaria para que el tráfico llegue al hook: DLT, IP destino a la interfaz vigilada,
   subred enrutable, entrega L2 (MAC) a la NIC, y tasa por debajo de la saturación del ring (medido
   DAY270: ~14 % a 1000 pps, ~95 % a 100 pps).
   Conclusión para el paper: un dataset de flujo no se replica trivialmente a un NDR en línea; el método
   de replicación es en sí un resultado.

## C. Un fallo de parseo latente, visible solo bajo fragmentación (resultado de ingeniería)
El sniffer XDP parseaba la carga de los fragmentos IPv4 no-primeros como si fuera cabecera L4,
generando flujos fantasma con puertos inventados (63 % de las filas del bloque fragmentado de CIC).
Latente durante meses porque ningún tráfico fragmentado había llegado al pipeline. Corrección: en el
kernel, comprobar el offset de fragmento antes de tocar L4; contar el paquete en el agregado por
víctima pero no emitir flujo. Lección Vía Appia: un extractor de rasgos que no distingue fragmentos
produce ruido estructurado (flujos coherentes pero falsos), peor que ruido aleatorio para un bosque.

## D. Evidencia de que el contrato nuevo es necesario, no cosmético (motivación cuantitativa)
Línea base del modelo anterior (entrenado casi solo sobre el flood UDP volumétrico) sobre cada familia,
medida con la compuerta forzada (FORCE_ALL_HEADS) para aislar la cabeza del veto de level1:

| Familia de ataque        | % marcado como DDoS por el modelo viejo |
|--------------------------|------------------------------------------|
| UDP flood volumétrico 440 B | 72–75 %                               |
| UDP flood fragmentado ~4 KB | ~92 %                                 |
| SYN flood                   | 0 %                                   |
| Reflexión NTP               | ~35 %                                 |
| Reflexión DNS               | 3,6 %                                 |

El modelo viejo es casi ciego a todo lo que no sea su forma de entrenamiento. Justifica el contrato v2
con syn_ack_ratio, reflection_signature y los rasgos agregados por víctima del kernel
(victim_pps, victim_rate_ratio).

## E. Pendiente antes de reclamar números de detección
- El split train/test debe ser por flujo o por ventana temporal, nunca por filas (el sniffer emite
  una fila por paquete; las filas de un flujo están correladas).
- Reentrenar sin scaler, medir importancias, y solo entonces decidir quitar rasgos.
- Reportar FP sobre benigno real (ambiente + subida TCP 50 KB/s) por familia.