# Apoyo para el paper — DAY299

Material para la reescritura honesta del paper. Todo lo que sigue está medido en el laboratorio
(VirtualBox, XDP genérico, build production). Las cifras absolutas dependen de la máquina; las relaciones
y los mecanismos, no.

## 1. La ceguera de arranque es física, y hay que nombrarla

Un detector basado en tasas por víctima no puede ver un ataque hasta que ha medido al menos una ventana
completa. En aRGus, la primera foto del agregador del kernel llega a ~1,0 s del arranque (1015 y 1035 ms,
dos arranques). Durante ese intervalo, el tráfico se sella como víctima fría y no puede pasar la etapa 1.

Antes de DAY299 ese intervalo existía igual, pero sin nombre: los eventos salían «sin estado» y disparaban
un aviso genérico en cada arranque. Ahora tiene nombre, número y línea de log. La lección: **una
limitación física no se elimina, se mide y se declara**; una alarma que salta en cada arranque normal
acaba ignorándose y deja de servir para lo que existe.

## 2. Una alarma se prueba en los dos sentidos

Probar que un aviso calla cuando todo va bien no prueba nada sobre si salta cuando debe. Se midió el caso
contrario apagando el agregador: 12 avisos, ~17 900 de 18 000 paquetes de ataque sin estado, 0 bloqueos.
La cabeza queda ciega y la única defensa es que el administrador lo vea. Se midió también que el AVISO del
sniffer aparece una sola vez al arrancar, para que el diagnóstico no dependa de la ausencia de una línea.

## 3. Persistir estado no es solo guardarlo: el tiempo cambia de significado

Restaurar el estado por víctima tras un reinicio parecía trivial. No lo es: el contador de ventanas del
lector vuelve a empezar, y una víctima restaurada «bajo presión» aparece con un hueco artificial que el
modelo interpreta como «el ataque terminó». Para ataques fuertes no importa (vuelven a entrar en la misma
ventana); para ataques moderados, en la banda de histéresis, se perdería la detección justo tras el
reinicio. El test se diseñó primero con un ataque fuerte y **falló porque el contrafactual estaba mal
escogido**: el fallo del test reveló dónde importa de verdad el arreglo.

## 4. Gates que parecen medir y no miden (tercera aparición)

- `pipeline-stop` mataba los componentes con SIGHUP y ninguno lo trataba: **ningún componente del
  laboratorio había ejecutado nunca su parada ordenada** (0 líneas de limpieza en el log). Cualquier
  persistencia «en la parada» habría sido código muerto en el lab.
- Los 21 tests del ipset se saltan siempre en el gate, porque exigen root; el target que los ejecuta con
  root no forma parte de ningún gate.
- Misma familia que DEBT-MAKEFILE-TEST-GATE-MASKED-001 (DAY222): un verde que no mide lo que dice.

## 5. El método: predicciones que fallan y se explican

Tres predicciones del día fallaron y las tres enseñaron algo:
- N sellados en el arranque: predicho ~300, medido 648. El sniffer emite dos eventos por paquete (flujo y
  fast alert); el ml-detector solo evalúa el de flujo.
- Eventos sin estado con el agregador apagado: predicho ~1 500 por 10 s, medido ~3 000. Un evento de flujo
  por paquete, porque cada tupla del pcap es un flujo nuevo.
- Primera corrida fría: 0 paquetes del ataque vistos. El ataque (210 s) acabó antes de que arrancara el
  sniffer; el arranque del sniffer varía entre ~140 y >215 s. Se corrigió la herramienta (RETRASO_S), no
  la conclusión.
Escribir la predicción antes de medir es lo que convierte cada sorpresa en un dato y no en una excusa.
