# Diseño DAY298 — etapa 1 con histéresis, EWMA congelada y arranque sin ventana ciega

Rama: fix/ddos-etapa1-histeresis. Deudas: DEBT-DDOS-COLDSTART-ETAPA1-001, DEBT-DDOS-V2-LONG-ATTACK-001.
Decisiones de Alonso DAY297-298: un DDoS puede durar días o meses y hay que pararlo en cuanto se detecta;
lo más peligroso es el DDoS como cortina para lateralizar ransomware; política de arranque 2+3 (umbral
absoluto para víctimas sin historia + estado persistido entre arranques), nunca ventana ciega.

## 0. Estado medido (antes)

- A5 offline (DAY297) y en vivo (DAY298, logs/lab/day298/a5_antes): con tau_s=3600 y K=3 la etapa 1
  deja de marcar un ataque sostenido a t = tau·ln(3(r−1)/(2r)), con r el ratio inicial. En vivo r=6,786
  → 885,7 s predichos, 888,6 ± 0,5 s medidos (+0,3 %); FIN de la sombra a +918,2 s; 132 s de ataque
  sin marcar hasta el final; 0 DROP del .51 legítimo.
- Causa (sniffer/include/ddos_contract_v2.hpp:93-110): dentro de bajo_presion la EWMA aprende con
  alfa lento (1/tau_s), así que el ratio crudo cae; la etapa 1 (ml-detector, ddos_v2_head.hpp:39)
  compara ese ratio crudo con K y no consume bajo_presion. Aunque lo consumiera, bajo_presion sale con
  ratio < k_out a los ~3400 s: el ataque se absorbe igual, solo más tarde.
- Frío (DAY297, anexo 9.4): con seen=0 el ratio es pps/floor (floor=10); warm_windows solo condiciona
  ENTRAR en bajo_presion. 32 DROP en el primer segundo (.12 Wazuh → .1 TCP, ratio 14, p1 0,86).
- Hallazgo de diseño DAY298: un ataque que empieza con la víctima en frío se aprende como base durante
  el calentamiento (alfa 0,1, 30 ventanas): al calentarse, ratio ≈ 1 y nunca entra en bajo_presion.

## 1. Estado de la víctima en el evento

Campo nuevo en el proto (DdosEmbedded): victim_state, enum {DESCONOCIDO=0, FRIO=1, NORMAL=2,
BAJO_PRESION=3}. Lo rellena el sniffer donde ya rellena victim_rate_ratio (ring_consumer.cpp:1417-1419,
desde ddos_victim_board.hpp:82). Regeneración con `make proto`. DESCONOCIDO (evento sin el campo,
o sentinel) → el ml-detector aplica la etapa 1 antigua (ratio >= k_ratio) con aviso periódico.

## 2. Etapa 1 (ml-detector)

stage1 = (victim_state == BAJO_PRESION) || (victim_state == NORMAL && ratio >= k_ratio).
En FRIO la etapa 1 no pasa por ratio (el ratio en frío no significa nada); la protección en frío la da
el sniffer metiendo la víctima en BAJO_PRESION (apartado 3). La decisión de umbrales vive en un solo
sitio: el sniffer. k_ratio queda en el JSON del ml-detector como hasta ahora.

## 3. Histéresis y EWMA en el sniffer (victim_ewma_step)

- NORMAL: como hoy (alfa por ventana).
- Entrada en BAJO_PRESION:
  a) clave caliente (seen >= warm_windows) y ratio >= k_in (como hoy);
  b) clave FRIA y pps >= P_abs (NUEVO, ddos_victim_abs_pps en sniffer.json; [CONFIG-DEFAULT] si falta o
     es inválido). Sin esto un ataque presente al arrancar se aprende como base. [D298-ALONSO] No hay
     valor óptimo universal: depende de cada instalación (pipeline en una o varias máquinas, su
     capacidad, el tráfico legítimo normal de cada víctima). El _doc presenta el rango de actuación
     medido en el laboratorio y el defecto es SEGURO, no óptimo; lo calibra cada instalación. El
     defecto concreto sale de la medida del apartado 6.
- Dentro de BAJO_PRESION la EWMA se CONGELA (no aprende del tráfico clasificado como presión). Se
  sustituye alpha_slow/tau_s por la congelación; tau_s queda sin uso (se retira del JSON con aviso).
- Salida: ratio contra la EWMA congelada < k_out, es decir, cuando el tráfico vuelve a la base.
- Aviso periódico al administrador ([DDOS-HYST] WARN, cada aviso_s) si un episodio dura más de
  episodio_max_horas (sniffer.json). No cambia el estado: lo decide un humano. Cubre el caso legítimo
  de una base que crece de verdad durante un episodio, o una víctima nueva con tráfico legítimo alto.

## 4. Persistencia del estado entre arranques

- El sniffer guarda por víctima {ip, ewma, seen, bajo_presion, instante de pared} en un fichero
  (ruta en sniffer.json) cada snapshot_s segundos y en la parada si llega a ejecutarse. Periódico y no
  solo en la parada: pipeline-stop no garantiza destructores (DAY287 P11). Escritura atómica (tmp +
  rename).
- Al arrancar restaura las víctimas con antigüedad < estado_max_edad_s (sniffer.json); las restauradas
  cuentan como calientes (seen = max(seen, warm_windows)) y conservan bajo_presion con su EWMA
  congelada: un reinicio en mitad de un ataque no lo olvida.
- Si no puede leer o escribir: aviso claro y arranca igual (regla JSON DAY291).
- Riesgo y deuda: un fichero manipulado podría precargar una base alta y cegar la detección. Integridad
  con HMAC cuando exista la provisión de claves (areas/hmac-secrets-provisioning). DEBT nueva.

## 5. Rangos protegidos (firewall-acl-agent)

Listas en el JSON del firewall: DMZ e intranet (CIDR) y externos críticos (resolvedores, NTP usados,
operador, socios). Un DROP de la cabeza DDoS cuyo origen cae en un rango protegido se registra como
ALERTA_PROTEGIDO y nunca se convierte en bloqueo automático. En sombra: contadores y registro aparte.

## 6. Medida previa (antes de escribir patchers)

Frío provocado con el volcado del dataset activo (day289_dataset_writer.py on): tráfico hacia .1 ya en
marcha antes de pipeline-start. Objetivo: victim_pps y ratio en las primeras ventanas de .1 frente a lo
que hay en el cable. Pregunta abierta de DAY297 (anexo 9.7): ¿los ~140 pps del primer segundo son
tráfico real o un primer delta del agregador del kernel que abarca más de una ventana? Si es artefacto,
se corrige antes de calibrar P_abs (si no, P_abs dispararía en cada arranque).

## 7. Predicciones del después

- A5 offline (a5_ataque_largo.cpp con la función nueva): en ningún escenario la etapa 1 corta durante
  las 2 h de ataque; bajo_presion sale en 1-2 ventanas tras acabar el ataque (ratio ≈ 1 < k_out).
- A5 en vivo: un INICIO a +1-2 s, un FIN a fin_ataque + ~30 s (≈ +1080 s), DROP de .50 ≈ 0,99 de
  63000; .51 legítimo 0 DROP.
- Frío benigno (tráfico legítimo < P_abs al arrancar): 0 eventos con stage1 en las primeras 30
  ventanas; 0 DROP.
- Frío con ataque (>= P_abs al arrancar): BAJO_PRESION desde la primera ventana; marcado igual que
  en caliente; no se aprende como base.
- Reinicio en mitad de un ataque: tras el arranque, BAJO_PRESION restaurado; sin hueco de marcado
  salvo el tiempo de rearranque del pipeline.
- A1 y A2 sin cambios respecto a DAY297.

## 8. Actuación humana y preguntas abiertas [D298-ALONSO]

- Un aviso en un log no es una vía de actuación: el administrador actúa de forma asíncrona desde la
  consola de operación (DAY296, areas/dashboard-export). Hasta que exista, los avisos quedan en el log y
  como contador en el resumen periódico, y figuran como requisito de la consola.
- Actuar sobre una víctima en presión prolongada NO es tocar el ipset (los bans son del firewall,
  temporales y escalados por reincidencia, RECIDIVISM-D276). Es una de dos cosas: aceptar su tráfico
  actual como base nueva (re-sembrar la EWMA) o declararla rango protegido (apartado 5).
- Mientras nadie actúa, el efecto es acotado: la etapa 1 deja pasar todos los flujos de esa víctima al
  RF, que es quien decide; el daño aparece solo si el RF se equivoca (TCP de Wazuh DAY297, p1 0,86).
- Abierta (rama de medidas y modelo): salida automática de presión si en N horas el RF no ha dado ningún
  positivo para la víctima. Requiere realimentación ml-detector -> sniffer; N en el JSON.
- Calibración de P_abs y de los demás umbrales por despliegue (D22): el laboratorio no la decide.
