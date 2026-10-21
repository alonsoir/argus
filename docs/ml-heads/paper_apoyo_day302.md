# Apoyo para el paper — DAY302: de la sombra a la mitigación real

## 1. Qué se construyó
- Decidir por víctima, actuar por origen. La política por víctima (DdosShadowPolicy, k/n = 3/5, hold de 30
  ventanas) abre y cierra el episodio; la mitigación (DdosMitigacion) decide por cada origen de los DROP de ddos_v2
  dentro del episodio: BLOQUEAR (primer bloqueo del episodio, un strike de reincidencia) o RENOVAR (ya bloqueado:
  se re-añade con el escalón vigente, sin strike).
- Un episodio = un strike. Mientras el origen sigue atacando, cada DROP renueva la condena; tras su último DROP
  corre el escalón entero; la reincidencia solo sube con un episodio nuevo. Escalera de producción 1 h / 1 d / 7 d /
  24 d, nunca permanente.
- Doble llave: operation.dry_run y ddos_mitigacion.habilitada (defecto false).
- Barrera de protegidos en tres puertas: el suscriptor (ALERTA_PROTEGIDO, nunca entra en el episodio), la entrada
  de la API por episodio y el flush hacia el ipset (cubre cualquier camino). En el kernel, la whitelist es RETURN
  dentro de una cadena propia, nunca ACCEPT.

## 2. Resultado medido (E2E real en el lab, m3)
| | Ataque 1 | Ataque 2 |
|---|---|---|
| Entrada del origen en el set | 4,9 s | 4,5 s |
| Strike y timeout al entrar | 1, 60 s | 2, 120 s |
| Paquetes tirados por la regla DROP | 3312 de 3600 | 3348 de 3600 |
| Salida tras el fin del ataque | 61,2 s | 121,7 s |
El host protegido (.61, 3533 alertas) y la base inocente (.51) no entraron nunca. 2 BLOQUEAR y 6701 RENOVAR.
La cabeza marcó DROP en el 98 % de los paquetes del ataque; el firewall tiró el 92 %: la diferencia es el tiempo de
reacción, no paquetes sin procesar.

## 3. Tiempo de reacción
~4,8 s del inicio del ataque al bloqueo en el kernel: detección (~1-2 s, la etapa 1 llena su ventana), confirmación
del episodio (~2 s, k/n 3/5, elegida contra positivos aislados), siguiente DROP del origen (~1 s) y lote hacia el
ipset (<= 1-2 s). La vía rápida en XDP es la que debe cerrar esa ventana.

## 4. El sensor ve lo que el filtro tira
XDP va antes que netfilter: el sniffer sigue viendo los paquetes de un origen ya bloqueado, y cada uno renueva su
condena. Es la propiedad que mantiene fuera a un atacante persistente sin subirle de escalón dentro del mismo
episodio.

## 5. Lecciones de método
- El modo sombra no ejercita la aplicación: en dry_run el lote hacia el ipset fallaba SIEMPRE (comprobaba el kernel
  antes de simular) y un test de regresión pasaba gracias a ese fallo accidental.
- Los pcaps del lab llevaban MACs ajenas: el kernel los descartaba antes de netfilter. Toda medida anterior de
  "aplicación" en el lab habría sido vacía; la detección no se ve afectada. Se descubrió porque un criterio pedía
  ver subir el contador de la regla DROP, no solo la IP en el set.
- Nadie hacía flush por tiempo: el umbral existía, pero solo se evaluaba al llegar otra IP.
- Tests de rendimiento heredados con umbrales nunca comprobados (siempre saltados sin root): uno de ellos medía un
  fork de proceso contra un objetivo de microsegundos.

## 6. Predicciones fallidas, explicadas
- Q1: se supuso un flush periódico; no existía.
- R5/S3: se supuso que dry_run simulaba el lote; fallaba, y un test dependía de ello.
- V5: dos líneas CRASH en el arranque eran el volcado periódico de métricas, con un nivel de log engañoso.
- P3: se sospechó la caché de la carpeta compartida; el proceso de muestreo ni siquiera arrancaba (lanzado sin
  sleep tras &).
- m2/C2: la IP estaba en el set y el contador de DROP seguía a 0; causa medida: MACs del pcap.

## 7. Limitaciones
Un solo origen atacante (sin distribución por origen para fijar min_drops_origen); VirtualBox con XDP genérico (sin
medidas de rendimiento válidas); escalera de prueba [60, 120] s; volumen de log en modo activo sin medir a escala.
