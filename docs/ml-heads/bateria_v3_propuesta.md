# Batería v3 — propuesta (borrador para cerrar tras el bloque 1 y llevar al Consejo)

## Objetivos (cada uno ataca un fallo medido en DAY292)
O1 Romper el atajo de tamaño (familia fuera: sin ntp ~0 %).
O2 TCP benigno fuera de las corridas SYN (sin syn: 99 % FP sobre el inocente TCP).
O3 Romper la colinealidad ratio/pps (base siempre 10 pps).
O4 Interpolación de tasas no vistas (45/75/150).
O5 Latencia y recall@t en caliente y en frío; víctima fría con ataque sostenido.
O6 Perfiles temporales: rampa, intermitencia, ataque largo y segundo ataque.
O7 Benigno que SÍ eleva el ratio (subida legítima ≥4×) e inocente ruidoso durante el ataque.

## Restricción del lab
Consumidor del anillo ~305 eventos/s (DAY289) ⇒ total por corrida ≤ ~250 pps; QA de pérdidas en CADA corrida (contadores del
kernel frente a filas), y corrida rechazada si hay pérdida. Escalas reales (miles de pps): hardware real, fuera de esta batería.

## Generadores (todos sembrados, sha256 en MANIFEST)
- Reflexión NTP/DNS: tamaño ALEATORIO por paquete en rangos amplios y solapados (p. ej. 100-1450 B), no constante.
- SYN: 54-74 B con opciones TCP reales aleatorias (MSS, WS, SACK, TS) y puertos de origen aleatorios.
- Benigno UDP de respuesta (DNS/NTP legítimo) con los MISMOS rangos de tamaño que el ataque.
- Benigno UDP de volumen (tipo iperf, 1000-1450 B).
- Benigno TCP: subidas a varios caudales y ráfagas de conexiones cortas legítimas (handshake completo + datos).
- Segunda implementación para al menos una familia (p. ej. UDP: CIC udpA/udpB frente al generador propio) ⇒ hold-out por generador.

## Diseño (fases; cada corrida reinicia el pipeline, régimen caliente salvo donde se indica)
A Núcleo: base mixta UDP+TCP desde .51 ⇒ las dos claves calientes. Bases 10 y 40 pps.
  Familias ntp/dns/syn/udp × tasas 30/45/60/75/100/150 (45/75/150 SOLO test). ~2 bases × 4 familias × 6 tasas = 48 corridas.
B Benigno difícil: subida legítima 4-6× la base (entra en presión) con rasgos de flujo benignos; ráfaga de conexiones cortas;
  DNS/NTP legítimo de tamaños solapados; inocente que pasa a 10× durante un ataque. ~12 corridas.
C Temporal: rampa 0→R en 30 s; intermitente 10 s on / 10 s off ×4; ataque de 10 min + pausa 2 min + segundo ataque. ~8 corridas.
D Frío: ataque sostenido 3 min a víctima sin historia (base ausente); y reinicio del pipeline a mitad de ataque. ~4 corridas.
E (opcional) Segunda víctima (alias en el defender, comprobar antes que el sniffer la captura). ~4 corridas.

## Evaluación
- Splits por corrida (nunca por fila); varias semillas y varios splits, con intervalos.
- Test bloqueado: tasas 45/75/150, un generador entero y una familia entera por turno (familia fuera como criterio).
- Métricas: recall@t (0-0,5 / 0,5-1 / 1-2 / >2 s), latencia caliente y fría por separado, FP por evento de bloqueo (con la
  política del bloque 1c), FP por víctima-hora, tamaño/latencia del modelo.
- Aceptación propuesta (a discutir): familia fuera ≥ 90 % de recall fuera del arranque, 0 eventos de bloqueo en todo el
  benigno (incluida la fase B), tasas no vistas ≥ 95 %.

## Operativa
~75 corridas × ~6 min ≈ 7,5 h de lab: hace falta un ejecutor desatendido en el Mac (make + vagrant ssh) que encadene
pre/estable/client/stop/post y pare en el primer QA rechazado. Se diseña y se prueba con 2-3 corridas antes de lanzarlo.

## Preguntas abiertas para el Consejo (cuando esté cerrada)
Rangos de tamaño realistas por familia; si la subida legítima de 4-6× es el benigno difícil correcto; criterios de aceptación.
