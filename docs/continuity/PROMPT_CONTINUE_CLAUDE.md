# Prompt de continuidad — aRGus NDR, DAY297 -> DAY298

Reglas (sin cambios): medir, no votar; prediccion escrita antes de medir; si algo no da lo esperado, PARAR.
Comandos EXACTOS y COMPLETOS, en orden, diciendo donde va cada uno (Mac / defender / client). Comandos separados o cada
salida a su fichero, y con `; cat` del fichero al final. Nunca `grep -rn` desde la raiz (`git grep` o el fichero concreto;
excluir ':!*.pb.cc' ':!*.pb.h' ':!*_pb2.py'). Scripts como bloque `cat > f <<'EOF'`; `LC_ALL=C` en todo awk con
aritmetica. Tras pegar un heredoc, comprobar que la terminal vuelve al prompt y no queda en `heredoc>` (en DAY295 un
heredoc mal cerrado duplico la seccion 7 del contrato). Patchers atomicos, todo-o-nada, con `--check` / `--apply` y
marca. Compilar, probar Y ARRANCAR con el MISMO perfil: `make pipeline-build PROFILE=production`,
`make test-components PROFILE=production`, `make pipeline-start PROFILE=production`. Configuracion: el JSON manda;
defecto validado + `[CONFIG-DEFAULT]`. Relojes: tras suspender el Mac, `make lab-clock-step` justo al despertar.
Corridas de lab: `bash scripts/timebase/lab_corrida.sh NOMBRE 'comando del client'` desde el Mac (hace relojes,
parada, nada vivo, logs a cero, arranque production, ESTABLE, tcpdump en eth2, client, parada y contabilidad; para al
primer fallo; resultados en logs/lab/day297/NOMBRE/). Anotar en cada medida que VMs estaban levantadas.

## 0. Estado
- fix/event-timestamp-timebase: EMECAS+++ VERDE en DAY297 (rc=0, sobre 38a77aea); PR y merge a main al cierre de DAY297.
  Comprobar al empezar: `git log --oneline -3 origin/main` y que no quedan PR abiertos.
- LEER PRIMERO: docs/timebase/contrato_temporal_day295.md (sec. 9 = DAY297), docs/carta_reyes_magos_caceres.md
  (que no se puede medir en el lab virtual y que equipo haria falta) y docs/ml-heads/consejo_day294_sintesis.md.
- Hecho DAY297: contadores de producer_seq en el firewall (0 duplicados y 0 huecos en 15262/17129/26110 eventos);
  orquestador de corridas; A1 aceptada (cable = DROP = sombra al evento); A2 (gemelo .61 marcado 0,9956 / 0,9917,
  igual que el atacante; NTP legitimo de .51 0 DROP); A5 confirmada offline contra victim_ewma_step de produccion
  (la etapa 1 deja de marcar un ataque sostenido a los 15-25 min); seccion 7 duplicada del contrato eliminada.

## 1. DAY298: rama nueva fix/ddos-etapa1-histeresis (DEBT-DDOS-COLDSTART-ETAPA1-001 + DEBT-DDOS-V2-LONG-ATTACK-001)
Causa comun medida: la etapa 1 (ddos_v2_head.hpp:39) compara el ratio crudo con K = 3 y nadie consume bajo_presion;
warm_windows solo condiciona la entrada en el estado (ddos_contract_v2.hpp:103); la EWMA aprende del propio ataque.
Postura de Alonso: un DDoS puede durar dias, semanas o meses; hay que pararlo de raiz en cuanto se detecta y la
insistencia debe salir cada vez mas cara; lo mas peligroso es el DDoS como cortina para lateralizar ransomware.
1. ANTES (medir, con prediccion escrita):
   a. A5 en vivo, ~20 min de ntp a 60 pps. El pcap tiene 10000 paquetes (166 s a 60 pps): medir primero si --loop
      (5-tuplas repetidas) cambia flow_packet_count u otros rasgos; si cambia, generar un pcap largo reproducible.
      Prediccion: FIN de la sombra a ~15,6 min del inicio (base 10) .
   b. Arranque en frio PROVOCADO: trafico hacia una victima en los primeros segundos tras pipeline-start.
2. DISENO (doc corto antes de patchers):
   - La etapa 1 consume el estado de histeresis (llevar bajo_presion en el evento: campo nuevo en el proto -> `make proto`).
   - EWMA de la victima congelada mientras dure un episodio (no aprender de trafico clasificado como ataque); el episodio
     acaba cuando el trafico vuelve a la base; aviso periodico al administrador si dura mas de X horas (X en el JSON).
   - Rangos protegidos en el JSON: DMZ e intranet nunca se banean automaticamente (solo alerta); lista de externos
     criticos que tampoco (resolvedores, NTP usados, operador, socios).
3. DESPUES: mismas corridas con el orquestador (A5 en vivo, frio provocado, A1, A2) y comparacion antes/despues.
4. EMECAS+++, PR, merge.

## 2. Rama siguiente: via rapida en XDP (decision de Alonso: drop inmediato ante un ataque claro, antes de
clasificacion, firewall y grafo; actuar primero, informar despues)
- Empezar por "respuestas sin pregunta" (NTP/DNS/memcached/SSDP entrantes sin consulta saliente previa; el defender es
  el gateway y ve la salida): drop en XDP sin umbral; sin falsos positivos por construccion y no utilizable con
  origenes falsificados.
- Volumetrico no reflejado: limitacion de tasa por victima en XDP.
- Ban por origen con escalada (dias a meses, reutilizando RECIDIVISM-D276) solo con evidencia por origen (D19 o TCP con
  handshake), fuera de los rangos protegidos; agregacion por subred externa con N origenes confirmados y caducidad.
- Cada regla cuenta lo que tira, muestrea y manda resumen del episodio aguas abajo (grafo); configuracion en el JSON.
- Correlacion: DDoS activo + anomalia interna = maxima severidad. Modo degradado (D21) protege primero la deteccion de
  ransomware.
- Limite del lab: VirtualBox ejecuta XDP generico -> solo validacion funcional; rendimiento y defensa del ancho de banda
  (FlowSpec/RTBH aguas arriba) requieren el equipo de la carta.

## 3. Despues
- DEBT-TIMEBASE-SEQ-DELIVERY-ORDER-001: flujo adelantado por la fast-alert siguiente (12 casos a 120 pps); anadir
  mld_recv/mld_send a la linea [TIMEBASE-SEQ].
- DEBT-SNIFFER-EVENT-ID-NOT-UNIQUE-001 (event_id = ts_ns + "_" + src XOR dst; tambien correlation_id).
- Rama de estandarizacion (DEBT-LAB-RUNTIME-STANDARD-001); rama DEBT-FW-IPSET-TESTS-SKIPPED-001 (21 saltadas).
- PR de limpieza de scripts de la raiz + README (firewall-acl-agent/proto/ muerta; avisos de graphify day287/288).
- DEBT-FLOWUID-TIMEBASE-VERIFY-001; Variant B y herramientas sinteticas al contrato v1.
- Rama de medidas y modelo (D18, D19, D21, luego D20). D22 cuando haya cliente.
- Imagen endurecida y Falco: verificar el estado REAL antes de afirmar nada (11 reglas frente a 13 acordadas; perfiles
  AppArmor en security/apparmor/ y tools/apparmor/; ultimo hardened-full verde en abril). Primero `make hardened-full`
  desde VM destruida, con prediccion escrita.
- Antes de publicar el post de DAY294 en LinkedIn: corregir "~1.3 s" por "~1-2 s".
- Carta de los Reyes Magos de Cáceres: si se envia a Andres, version compartible del documento.
