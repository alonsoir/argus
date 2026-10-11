# Notas para el paper — DAY289 (cabeza DDoS, contrato v2)

Laboratorio: VirtualBox, una VM defender, XDP genérico, build de producción, FORCE_ALL_HEADS=1.
Todas las cifras salen de scripts commiteados (`day289_*`); los pcaps se regeneran byte a byte
(sha256 en `scripts/dataset_lab/MANIFEST.md`); los CSV de corridas viven en logs de laboratorio, no en git.

## 1. Un 100/0 en test mide la facilidad del dataset, no el detector
- 19 corridas frías, 58 564 filas, split temporal dentro de cada corrida. Test: recall 100 %, FP 0 %.
  Bosque viejo sobre las mismas filas: 18,8 % / 71,1 % (y 48,6 % FP sobre el ambiente).
- Dejar una familia fuera: SYN pasa a 0 % de recall. El modelo separa por firma, no por agregado.
- Importancias por impureza y por permutación discrepan por redundancia: ninguna de las dos sirve
  sola para decidir qué rasgo sobra.

## 2. Un conjunto de contraste destapa lo que el test no ve
- Respuestas DNS/NTP legítimas hacia el host protegido (generadas, reproducibles). Modelo nuevo:
  74 % (pequeñas, fuera de distribución, prob ~0,56) y 100 % (grandes) de FP. Bosque viejo: 0 %.
- Mensaje: evaluar solo con las familias que se entrenaron oculta los fallos frente a benignos que
  comparten firma con un ataque.

## 3. Reentrenar con el contraste reduce la reflexión a un umbral de tasa fijado por el dataset
- Con el contraste en train vuelve el 100/0, pero la sonda de victim_pps salta en el mismo punto
  (20→25 pps) en todas las familias UDP con puerto de servicio. Con la tasa benigna de 20 pps fuera de
  train: 90,6 % FP y la frontera se mueve a 10–15 pps.
- El rasgo relativo (victim_rate_ratio) no aporta en régimen frío (≈1 para benigno y ataque).
- Lectura honesta: el solapamiento ataque/benigno (30–100 frente a 5–20 pps) lo fabrica el
  laboratorio; un flood real va órdenes de magnitud por encima. Las tasas de ataque del laboratorio
  estaban acotadas por el consumidor del sniffer (sección 4).

## 4. El techo de tasa era algorítmico, no del anillo
- A 100 pps el anillo eBPF entrega todo (RESERVE_FAIL = 0). A 1000 pps: 82,7 % de reserve fallidos;
  consumidor ~175 ev/s.
- perf: el hilo consumidor reconstruía una ventana de 30 s (conjuntos hash de IPs y puertos) 9 veces
  por evento, O(N) cada vez. Calculándola una vez por evento: techo ~305 ev/s; RESERVE_FAIL a 1000 pps
  69,0 %. Sin cambiar el comportamiento de ninguna cabeza.
- Límite que declarar: estas cifras son de una instancia en VirtualBox con driver de prueba. No dicen
  cuántas instancias necesita una instalación real; eso exige hardware y carga distribuida reales.

## 5. Topología: el sensor de ingreso LAN no ve respuestas
- El XDP en la cara LAN ve las consultas DNS/NTP salientes y nunca las respuestas (entran por la WAN).
  Un benigno con firma de reflexión no aparece de forma natural en esta topología: hubo que generarlo.

## Siguiente (para el texto)
Emisión por flujo en el sniffer, regeneración del dataset con ataques sobre una línea base benigna
sostenida (régimen caliente), misma batería de evaluación (dejar familia fuera, tasa reservada,
sonda, contraste) antes de cablear el modelo.
