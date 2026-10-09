# Consejo de Sabios — DAY292: cabeza DDoS de aRGus NDR, reentrenamiento en régimen caliente

## Contexto (para quien no conoce el proyecto)
aRGus es un NDR open source en C++20 para infraestructura crítica (hospitales). Un sniffer eBPF/XDP emite un evento por paquete
con rasgos; un ml-detector ejecuta "cabezas" (bosques aleatorios embebidos como C++ generado) y la decisión final irá al
firewall. Estamos reparando la cabeza DDoS: contrato de rasgos único entre entrenamiento y servicio, calculado UNA vez en el
sniffer. Decisión POR PAQUETE.

Rasgos (contrato v2): syn_ack_ratio, mean_packet_size, reflection_signature (puerto de servicio conocido → puerto alto),
packet_size_entropy, flow_packet_count, flow_completion_rate (del flujo), y dos de víctima por clave {IP destino, protocolo}
calculados en el kernel en ventanas de 1 s: victim_pps y victim_rate_ratio = pps / EWMA (suelo 10 pps). La EWMA tiene
histéresis: entra en "bajo presión" con ratio ≥ 3 (clave con ≥ 30 ventanas), sale con ratio < 1,5; bajo presión absorbe con
τ = 3600 s, fuera con α = 0,1. Sin histéresis, un ataque sostenido se absorbía en ~20 s.

## Lo que hicimos (DAY292)
Laboratorio de 3 VMs. Atacante .50 y origen inocente .51 contra la misma víctima .1. El inocente mantiene ~10 pps durante 210 s;
el ataque dura 90 s desde el segundo 90. Familias: reflexión NTP y DNS y SYN flood (generadores propios sembrados), dos bloques
UDP de CICDDoS2019 (udpA, udpB fragmentado), a 30/60/100 pps; contrastes benignos desde .50 (DNS pequeño 10 pps, DNS grande
5/10/20 pps). 19 corridas, 0 pérdidas. Etiqueta por origen (la IP no es rasgo). Ambiente y otros orígenes hacia .1: benignos.
Pesos: clases 50/50, cada rol y cada corrida con el mismo peso. Test = corridas enteras de 60 pps + DNS grande 10 pps.
Las corridas en frío de días anteriores (víctima sin historia, otro código) solo se usan para evaluar.

## Resultados: tres modelos (RF 100 árboles, random_state 42)
- A: todas las filas. Recall test 99,45 %. FP contraste 0,78 % (6 filas en el primer 0,5 s + 1 respuesta DNS legítima de
  1442 B, tamaño exacto del ataque DNS). Todos los fallos de recall en el primer 1,4 s.
- B: fuera del entrenamiento los 2 primeros segundos de cada ataque (el rasgo de víctima aún es de la ventana anterior; esas
  filas son indistinguibles de lo benigno). Recall 100 % fuera del arranque, FP 0 %. Sonda: aprendió un UMBRAL ABSOLUTO de
  victim_pps de ~30-40 pps (hueco entre el contraste más alto y el ataque más flojo del lab). Frío: 30 pps ~0 %, 60/100 ~97 %.
- B sin victim_pps (7 rasgos): recall 100 % fuera del arranque, FP 0 %, latencia de detección 0,5-1,5 s; decide por el ratio
  (relativo). Frío: 30 pps ~0 %, 60 pps ~8 %, 100 pps ~13 %. Bosque más pequeño (3714 nodos, profundidad 14).
- Los TRES, dejando una familia fuera del entrenamiento: sin NTP recall ~0 %; sin SYN marca ~99 % del tráfico TCP inocente
  (sin SYN no hay TCP benigno en el entrenamiento). Permutación: mean_packet_size y reflection_signature dominan junto al rasgo
  de víctima. Conclusión nuestra: aprende las FIRMAS de nuestros generadores (tamaño fijo por familia), no el comportamiento.
- Línea base: el bosque anterior marcaba el 100 % de una subida TCP legítima de 10 KB/s y el 0 % del SYN flood.

## Inclinación actual
Candidato = B sin victim_pps: relativo a la historia de cada víctima (para eso se diseñó la EWMA con histéresis); su fallo
(víctima fría) es explicable y acotado, frente al umbral absoluto de B, que depende de las tasas elegidas en el lab y fallaría
en silencio con otra escala de tráfico.

## Preguntas al Consejo
1. ¿B sin victim_pps es el candidato correcto, o el umbral absoluto de B tiene un valor que no vemos (víctima fría)?
   ¿Un híbrido (regla absoluta solo mientras la clave está fría)?
2. Dependencia de la firma: ¿basta con diversificar los generadores (tamaños aleatorios, benigno con tamaños que solapen los
   del ataque, base mixta UDP+TCP, bases de 10/50/200 pps), o hace falta otra cosa? ¿Qué diseño de dataset propondríais?
3. ¿Cablear ya el candidato (pasar puertas: paridad Python/C++, umbrales crudos, tamaño/latencia, cero bloqueos E2E) e iterar
   el dataset después, o iterar el dataset antes de cablear?
4. Decisión por paquete: ¿qué política de agregación antes de que el firewall bloquee (k de n paquetes, por víctima y ventana,
   por origen)? Cero falsos bloqueos es puerta innegociable (hospital).
5. ¿Un árbol poco profundo o una regla explícita (ratio > K y firma) frente al bosque? ¿Cómo lo mediríais?
6. ¿Es correcto sacar el arranque del entrenamiento y publicarlo como latencia, o enmascara algo?
7. ¿Qué se nos ha pasado? Cualquier sesgo de método, etiqueta o métrica que veáis.

Responded con argumentos medibles: nosotros medimos, no votamos.
