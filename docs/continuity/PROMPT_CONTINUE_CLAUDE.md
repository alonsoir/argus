# Prompt de continuidad — aRGus NDR, DAY295 -> DAY296

Reglas (sin cambios): medir, no votar; predicción escrita antes de medir; si algo no da lo esperado, PARAR.
Comandos EXACTOS y COMPLETOS, en orden, diciendo dónde va cada uno (Mac / defender / client). Comandos separados o cada
salida a su fichero, y con `; cat` del fichero al final. Nunca `grep -rn` desde la raíz (`git grep` o el fichero concreto;
excluir ':!*.pb.cc' ':!*.pb.h' ':!*_pb2.py'). Scripts como bloque `cat > f <<'EOF'`; `LC_ALL=C` en todo awk con
aritmética. Patchers atómicos, todo-o-nada, con `--check` / `--apply` y marca. Compilar y probar con el MISMO perfil:
`make pipeline-build PROFILE=production` y `make test-components PROFILE=production`. Configuración: el JSON manda;
defecto validado + `[CONFIG-DEFAULT]`. Antes de pipeline-start: comprobar que no hay nada vivo
(vagrant ssh defender -c "tmux ls; pgrep -a -f 'sniffer|ml-detector|firewall-acl-agent'").
Regla del lab (hasta que exista lab-clock-step): tras suspender el Mac, en el Mac:
vagrant ssh defender -c "sudo chronyc makestep" y después vagrant ssh client -c "sudo chronyc makestep", antes de medir.

## 0. Estado
- main = bc73b831 (PR #143), etiqueta pre-release-ddos-only-0.0.3.
- Rama fix/event-timestamp-timebase, último commit df376a42 + docs DAY295. LEER PRIMERO:
  docs/timebase/contrato_temporal_day295.md (contrato v1 + anexo §7) y docs/ml-heads/consejo_day294_sintesis.md (D15-D22).
- Hecho y verificado E2E: proto (TimeContext = 38); sniffer Variant A (timebase.hpp + test_timebase 33/33, sección
  timebase en sniffer.json, hilo del reloj, stamp en flujo/fast-alert/ventana, event_timestamp, flow_start_time y
  window_start en epoch derivado, schema_version 32); firewall (sombra sobre mono_ns, hold_windows, 8 causas de
  anomalía fuera de las ventanas, retraso sniffer->firewall en [TIMEBASE] resumen). test-components en verde.
- Medido en reposo: retraso sniffer->firewall media 12-26 ms, máx 22-90 ms; 0 anomalías.

## 1. DAY296, en orden
1. Target `lab-clock-step` en el Makefile: chronyc makestep en defender y después en client; verificar DENTRO de las
   VMs con chronyc (desfase < 1 ms), no con date por vagrant ssh (cada vagrant ssh tarda ~14 s).
2. ml-detector: sellos mld_recv_mono_ns / mld_send_mono_ns (D17) para partir el retraso en dos tramos; el firewall los
   añade a su resumen. Mismo criterio de anomalías.
3. Validador de Parquet sobre TODAS las filas (DEBT-PARQUET-VALIDATOR-FIRST-ROW-001).
4. Aceptación: salto `sudo date -s "+5 seconds"` y `-5` en el defender en mitad de un ataque ntp 60 pps: [CLOCK-STEP]
   en el log del sniffer, hold = hold_windows ventanas (29-30 s en mono_ns) sin cambio, orden por (boot_id, producer_seq)
   intacto, bronce en epoch. Corrección gradual real: suspensión ~3 min SIN makestep -> [CLOCK-SLEW] y clock_state
   SLEWING; luego lab-clock-step y vuelta a OK.
5. Aceptación D15: A1 contabilidad (tcpdump en .1 frente a eventos DROP, duplicados con producer_seq), A2 gemelo .61 a
   10 y 60 pps, A5 ataque largo (primero offline).
6. EMECAS+++, PR, merge.

## 2. Pendiente fuera de esta rama
- Semana: PR de limpieza de scripts de la raíz + README (incluir la copia muerta firewall-acl-agent/proto/ y los avisos
  de graphify sobre day287/288_*.sh).
- DEBT-FLOWUID-TIMEBASE-VERIFY-001: verificar en el grafo si flow_uid de aRGus convergía con Suricata/Zeek.
- Variant B y herramientas sintéticas al contrato v1 (BACKLOG DAY295).
- Después: rama de medidas y modelo (D18, D19, D21, luego D20). D22 cuando haya cliente.
- Antes de publicar el post de DAY294 en LinkedIn: corregir "~1.3 s" por "~1–2 s".
