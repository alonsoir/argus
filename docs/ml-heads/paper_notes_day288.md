# Notas para el paper — DAY288 (dataset DDoS v2 de laboratorio)

## Método: corridas reproducibles y controladas

- **Tráfico de ataque por construcción**: pcaps generados con semilla fija (SYN flood; reflexión NTP
  con puerto origen 123 y 482 B; reflexión DNS con puerto origen 53 y 1442 B), regenerables byte a
  byte (sha256 verificado), más dos tramos reescritos de CICDDoS2019 (UDP 440 B y UDP ~4 KB
  fragmentado). Cada familia a 30, 60 y 100 pps, 3000 tramas por corrida.
- **Benigno por construcción**: subida TCP legítima a 2, 20, 50 y 100 KB/s, solapando a propósito
  el rango de tasas del ataque, para que la tasa por víctima no pueda separar las clases sola.
- **Una corrida = un arranque del pipeline**, con el rasgo de víctima empezando limpio.
- **Compuerta de estabilidad**: el ataque no sale hasta que el lector del agregador del kernel lleva
  ≥30 s con sondeos regulares. **QA por corrida** sobre las ventanas del kernel: pps dentro de
  [0,5R, 1,5R] y ningún sondeo >1,5 s. Las corridas que fallan se descartan y se repiten.
- **Régimen de historia controlado y medido**: cada corrida registra cuántas ventanas tenía la clave
  de víctima antes del ataque. El dataset de entrenamiento es todo régimen FRÍO (<30); las corridas
  CALIENTES se reservan como conjunto de evaluación de desplazamiento de distribución.

## Hallazgos

1. **El detector viejo reacciona al caudal, no a la firma.** Sobre el mismo pcap de flood UDP marca
   36 %, 57 % y 72 % a 30, 60 y 100 pps; 0 % en SYN flood y en reflexiones NTP/DNS; y 99,97–100 %
   de falsos positivos sobre una subida TCP legítima a partir de 20 KB/s.
2. **Un rasgo relativo a la línea base depende de la historia de la víctima.** Con el mismo ataque
   (SYN a 60 pps), el ratio frente a la EWMA de la víctima se queda en ~6 durante todo el ataque si
   la clave tenía historia (137 ventanas previas) y decae a ~1 si no la tenía (4 ventanas). Un
   dataset que no controle cuánto tiempo lleva el sensor arrancado antes de cada ataque mezcla dos
   distribuciones distintas del mismo rasgo.
3. **El falso positivo de la EWMA anti-envenenamiento está acotado.** Con α/60 en régimen anómalo y
   umbral K=5, una carga legítima nueva sobre una víctima con línea base muy inferior sale del
   régimen anómalo tras −ln(1−1/K)/(α/60) ≈ 134 ventanas (≈2,2 min con ventanas de 1 s),
   independientemente de la magnitud de la carga. Medido: ratio 9 → 5,4 en 120 s a 100 KB/s.
4. **El agregador del kernel mide la llegada real.** En un parón del laboratorio, 434 paquetes de
   una corrida "a 30 pps" llegaron en 981 ms; el contador del kernel lo registró exactamente. Las
   ráfagas son reales para el sensor; el QA por corrida las separa de las etiquetas.
5. **Coste observado del pipeline**: a ~200 eventos/s el ml-detector consume ~3,2 núcleos con todas
   las cabezas activas (laboratorio VirtualBox, 6 vCPU, XDP genérico).

## Limitaciones a declarar

- Toda la reflexión del laboratorio procede de un único origen; en la realidad llega de miles de
  reflectores. No afecta al contrato v2 (sin rasgo de dispersión de origen) pero limita la
  generalización.
- Tasas limitadas a ≤100 pps por la saturación del ring XDP→userspace en el laboratorio.
- Benigno principal = un único flujo TCP sintético a caudal constante, más el ambiente del lab.
- Solo el día de entrenamiento de CICDDoS2019 (01-12) está disponible, y en él solo dos familias UDP.