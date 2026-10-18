# Apoyo para el paper — DAY301: de detectar a actuar (mitigación real de ddos_v2, preparación)

Estado honesto: el camino ddos_v2 -> ipset está diseñado, configurado y con su base en el kernel probada con
root. El bloqueo real de punta a punta (E2E con dry_run apagado) aún NO se ha medido.

## 1. Actuar por origen, decidir por víctima

La cabeza DDoS decide por víctima {dst, proto} (episodio INICIO..FIN de la política en sombra). El firewall
bloquea orígenes. El puente: un origen solo se bloquea si su víctima está en episodio. Un DROP aislado fuera
de episodio no bloquea nada; así se absorben los positivos aislados medidos en la corrida benigna de DAY294.

## 2. Un episodio = un strike

El sniffer captura con XDP, antes de netfilter: con el origen ya bloqueado, aRGus sigue viendo su tráfico
(predicción, a medir en el E2E). Un diseño ingenuo re-encolaría el origen en cada lote (1 s) y cada lote
sumaría un strike: un bot insistente llegaría al castigo máximo (24 días) en unos 6 s, por un solo ataque. El
código heredado tenía exactamente ese comportamiento (deduplicación solo dentro del lote pendiente).
Diseño adoptado: el primer DROP del origen en el episodio cuenta un strike; los siguientes renuevan el bloqueo
con el escalón vigente sin sumar; tras su último DROP corre el escalón entero. La reincidencia solo cuenta por
episodio nuevo. Con memoria acotada: por encima del límite, un origen nuevo se bloquea sin sumar strike.

## 3. El castigo: caro, nunca permanente

Escalera de producción 1 h / 1 d / 7 d / 24 d. Criterio del autor: el castigo debe durar más que la ráfaga y
dar tiempo al administrador, e incluso a las autoridades, para investigar; cada reincidencia debe costar más
al atacante. Nunca permanente: las IPs de botnets suelen ser víctimas (equipos comprometidos, CGNAT); el bloqueo
permanente queda como acción manual. Los castigos cortos solo se admiten en pruebas y el arranque los avisa.

## 4. Qué significa "protegido"

"Protegido" significa que aRGus nunca lo bloquea, no que el host lo acepte todo. La implementación heredada
ponía la whitelist como ACCEPT en la primera posición de INPUT: cargada con la intranet, habría anulado las
reglas propias del administrador para todo el tráfico interno. Ahora aRGus vive en su propia cadena con un único
salto desde INPUT; dentro, la whitelist hace RETURN (vuelve a INPUT y siguen las reglas del admin) y la
blacklist hace DROP.

## 5. Amenaza a la validez: el modo sombra no ejercita la aplicación

Meses de pruebas en dry_run ocultaron cuatro defectos de la capa de aplicación, que solo se ven fuera de él:
(1) la whitelist como ACCEPT en INPUT; (2) un rate limiting cuya primera regla aceptaba toda conexión TCP nueva y
que se creaba aunque estuviera desactivado; (3) la creación de la whitelist hash:net con una opción que ipset
7.17 rechaza (medido: rc 2), lo que habría tumbado el arranque; (4) una simulación que salía en el primer paso
y no imprimía ninguna regla. Lección: validar la detección en sombra no valida la mitigación; hacen falta
pruebas contra el kernel real.

## 6. Tests que pasaban sin ejecutarse

Tres tests de integración con ipset salían como "Passed" sin root porque se saltaban dentro de un único
binario de gtest y ctest solo ve el código de salida. La duración los delataba: 0,01-0,02 s sin root frente a
0,13-0,17 s cuando por fin corrieron con root (DAY301, 4/4). El test nuevo de la cadena sale con el código 77
sin root, que ctest marca honestamente como Skipped. Con root: 32/32 comprobaciones (salto único en INPUT,
RETURN antes que DROP, sin ACCEPT, idempotencia en dos llamadas, timeout real de 29 s sobre 30).

## 7. Predicciones fallidas, explicadas

- La víctima del lab: primero la di por el propio defender (acierto); después la confundí con el Mac al ver
  192.168.100.1 como fuente NTP del client; la medida de las interfaces lo deshizo (es la eth2 del defender).
- Supuse que el enum de destinos de iptables no tenía RETURN; ya existía.
- La primera verificación del arranque arrancó el binario equivocado: firewall-start sin perfil lanza la
  compilación de depuración, anterior a DAY300. Regla nueva: probar siempre con el mismo perfil que se compila.
