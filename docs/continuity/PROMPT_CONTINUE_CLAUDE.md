# Prompt de continuidad — aRGus NDR, DAY296 -> DAY297

Reglas (sin cambios): medir, no votar; prediccion escrita antes de medir; si algo no da lo esperado, PARAR.
Comandos EXACTOS y COMPLETOS, en orden, diciendo donde va cada uno (Mac / defender / client). Comandos separados o cada
salida a su fichero, y con `; cat` del fichero al final. Nunca `grep -rn` desde la raiz (`git grep` o el fichero concreto;
excluir ':!*.pb.cc' ':!*.pb.h' ':!*_pb2.py'). Scripts como bloque `cat > f <<'EOF'`; `LC_ALL=C` en todo awk con
aritmetica. Patchers atomicos, todo-o-nada, con `--check` / `--apply` y marca. Compilar, probar Y ARRANCAR con el MISMO
perfil: `make pipeline-build PROFILE=production`, `make test-components PROFILE=production`,
`make pipeline-start PROFILE=production` (sin PROFILE arranca DEBUG). Configuracion: el JSON manda; defecto validado +
`[CONFIG-DEFAULT]`. Antes de pipeline-start: `make pipeline-stop` y comprobar que no hay nada vivo
(vagrant ssh defender -c "tmux ls; pgrep -a -f 'sniffer|ml-detector|firewall-acl-agent'").
Relojes: tras suspender el Mac, en el Mac `make lab-clock-step` justo al despertar (chrony puede tardar ~2 min en ver el
desfase). La VM esta en UTC. En el client, lanzar scripts de /vagrant con `bash script.sh` (Permission denied si no).
Medidas de retraso: `bash /vagrant/scripts/timebase/tramos_identidad.sh N` (ultimos N resumenes [TIMEBASE]).

## 0. Estado
- main = bc73b831 (PR #143), etiqueta pre-release-ddos-only-0.0.3.
- Rama fix/event-timestamp-timebase. LEER PRIMERO: docs/timebase/contrato_temporal_day295.md (§7 y §8 = DAY296) y
  docs/ml-heads/consejo_day294_sintesis.md (D15-D22).
- Hecho DAY296: lab-clock-step; D17 tramos (ml-detector sella mld_recv/mld_send; firewall 3 tramos, causas 8 y 9);
  logging.level del firewall conectado (retraso medio 3,3-5,9 ms en reposo); perfil production en el lab; validador de
  Parquet sobre todas las filas; fast-alerts fuera del bronce (correlation_writer.include_fast_alerts=false); aceptados
  saltos +-5 s en ataque (FIN = ultimo DROP + 30 ventanas exacto), correccion gradual provocada y suspension real.

## 1. DAY297, en orden
1. D15 A1 contabilidad: tcpdump en .1 frente a eventos DROP durante ntp 60 pps (bash /vagrant/day291_piloto_client.sh 60).
   DAY294: 5357 DROP; DAY296: 5364 DROP para 5400 paquetes enviados. producer_seq no se ve en logs: decidir si basta
   event_id o hay que registrarlo.
2. D15 A2 gemelo .61 a 10 y 60 pps (tcprewrite del pcap; comprobar que el client puede emitir como .61).
3. D15 A5 ataque largo: PRIMERO offline (¿la EWMA absorbe el ataque y la sombra da FIN a mitad?), luego en vivo si procede.
4. EMECAS+++, PR, merge.

## 2. Despues de esta rama
- Rama de estandarizacion (DEBT-LAB-RUNTIME-STANDARD-001): perfil, config y nivel de log iguales en todos los componentes.
- Rama DEBT-FW-IPSET-TESTS-SKIPPED-001 (21 IPSetWrapperTest saltadas).
- PR de limpieza de scripts de la raiz + README (incluir firewall-acl-agent/proto/ y avisos de graphify sobre day287/288).
- DEBT-FLOWUID-TIMEBASE-VERIFY-001; Variant B y herramientas sinteticas al contrato v1.
- Rama de medidas y modelo (D18, D19, D21, luego D20). D22 cuando haya cliente.
- Antes de publicar el post de DAY294 en LinkedIn: corregir "~1.3 s" por "~1-2 s".
- Imagen endurecida y Falco (en algun momento, idealmente en la rama de estandarizacion): verificar el estado REAL antes
  de afirmar nada en el README. Hay 11 reglas de Falco en vagrant/hardened-{x86,arm64}/scripts/setup-falco.sh (se
  acordaron 13 en DAY133: ver cuales faltan), 7 perfiles AppArmor en security/apparmor/ y otro juego antiguo de 6 en
  tools/apparmor/ (¿cual se instala?), targets hardened-full / hardened-redeploy / prod-full-x86 / check-prod-all
  (incluye check-prod-falco). Ultimo verde conocido: abril 2026 (DAY134). Primero: `make hardened-full` desde VM
  destruida, con prediccion escrita. Falco detecta pero no responde (no hay capa de respuesta). Despues, la seccion
  "Runtime hardening" del README (borrador en el chat del DAY296).
