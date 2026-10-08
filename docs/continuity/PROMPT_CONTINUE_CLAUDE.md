# Prompt de continuidad — aRGus NDR, DAY291 → DAY292

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; si algo no da lo
esperado, PARAR. Comandos separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (`git grep`
o el fichero concreto); scripts como bloque `cat > f <<'EOF'`; `LC_ALL=C` en todo awk con aritmética;
`set -e` sin `pipefail` junto a `| head`. Comandos EXACTOS y COMPLETOS, en orden, diciendo dónde va cada
uno (Mac / defender / client). Patchers atómicos, todo-o-nada, con `--check` / `--apply` y marca.
Compilar y probar con el MISMO perfil: `make pipeline-build PROFILE=production` y
`make test-components PROFILE=production` (sin PROFILE los tests corren sobre build-debug). ctest oculta
la salida de los tests que pasan: para ver valores, `ctest -R <test> -V` en `/vagrant/sniffer/build-production`.

**Configuración — política REVISADA DAY291 (Alonso):** el JSON manda; nada hardcodeado salvo el DEFECTO
validado. Campo ausente, de tipo erróneo o fuera de rango ⇒ se usa el defecto validado, se avisa con
`[CONFIG-DEFAULT] campo=… valor=… rango=…` y el proceso ARRANCA igual: el pipeline nunca se para (el
hospital no puede quedar desprotegido semanas porque nadie lea un aviso). Cada campo documentado en el JSON
(`_doc_*`: tipo, rango, defecto, significado). Recordatorio periódico, `--check-config` y auditoría del
resto del JSON → PR de configuración, justo después de la cabeza DDoS.

**Foco único: la cabeza DDoS.** Orden: (1) observabilidad ✅, (2) contrato v2 ✅, (3) reentrenar y medir
[falta la batería en régimen CALIENTE], (4) fast-alert como entrada propia (FUERA del firewall en este PR),
(5) fusión + firewall por `final_decision` solo con la cabeza DDoS.

Operativa: targets del Makefile en el **Mac**; scripts en el **defender** desde `/vagrant`; tráfico en el
**client** (`eth1`, .50 → defender .1). Logs `/vagrant/logs/lab/{sniffer,ml-detector}.log` (rotar con
`sudo truncate -s 0`). Escritor de dataset: `python3 /vagrant/day289_dataset_writer.py on|off|estado`
(APAGADO); CSV por arranque en `/vagrant/logs/lab/ddos_dataset/`. Arranque de medida:
`make pipeline-start PROFILE=production FORCE_ALL_HEADS=1` + `/vagrant/day288_esperar_estable.sh`.
Reiniciar el pipeline antes de CADA corrida (tabla de flujos y EWMA vacías).
**Línea base desde .51:** en el client `sudo ip addr add 192.168.100.51/24 dev eth1` (NO persiste al
reiniciar la VM; comprobar con `ip -4 addr show eth1`). UDP: `benign_dns_ntp_small_5k_lab_src51.pcap`.
TCP: receptor en el defender `nohup python3 /vagrant/scripts/d281_tcp_sink.py 192.168.100.1 9000 >
/vagrant/logs/lab/day291_sink.txt 2>&1 &` + en el client
`python3 /vagrant/scripts/d281_tcp_upload.py 192.168.100.1 9000 KB_S SEG 192.168.100.51`.
**Medir siempre con `event_kind=0`:** `kind=1` son fast alerts con el vector entero en centinela −9999.

## 0. Estado de git
Rama `feat/ddos-head-contract`, NO mergeada. DAY291 (pusheado):
- `bfff6dd5` feat(sniffer) histéresis en la EWMA por víctima + parámetros en sniffer.json [DDOS-HYST-D291]
- `538d79af` tools(day291) pilotos en régimen caliente, medida por tramos, arnés offline, MANIFEST src51
- + `scripts/d291_paridad.py` y docs de cierre DAY291 (este prompt, BACKLOG DAY291, paper_notes_day291.md)
Comprobar: `git log --oneline -6 origin/feat/ddos-head-contract`.

## 1. Lo que DAY291 dejó MEDIDO

### 1.1 Piloto caliente (línea base .51 a 10 pps + ntp .50, misma clave {.1, UDP})
- .50 y .51 comparten clave: `victim_pps` y `victim_rate_ratio` idénticos tramo a tramo.
- El tráfico propio del client (1.1.1.1, 8.8.8.8, .12) no toca la clave.
- 1 fila `kind=0` por paquete, 0 pérdidas a 40–70 pps.

### 1.2 Fallo de diseño destapado: la EWMA absorbía los ataques
Código DAY286: `hot = caliente && ratio_de_ESTA_ventana >= 5`, SIN estado.
- 30 pps sobre 10 (4×): nunca entra en α lento; señal del ratio ~15 s; después ≈ 1.
- 60 pps (7×): ventana parcial del inicio 4,78 (<5, α rápido, la EWMA sube a 13,8) → entra al filo
  (5,07 / 5,03 / 5,07) → UNA ventana de jitter a 69,86 pps da 4,95 < 5 → α rápido → colapso a ≈ 1 en ~20 s.
  Que un flood de 7× existiera o no dependía de 0,2 pps de jitter.

### 1.3 Histéresis medida offline (`scripts/d291_histeresis_offline.py`, 18 días, 83 arranques)
| variante | ambiente: episodios / máx | pilotos 30 / 60 pps |
|---|---|---|
| actual (sin histéresis, K=5) | 7 / 4 s | 0 / 3 ventanas |
| K_in=3, K_out=1,5, τ=3600 s, caliente=30 | 33 / 10 s | 89 / 91 ventanas (todo el ataque) |
| ídem SIN condición de caliente | 328 / 69 s | — ⇒ la condición SE QUEDA |
Episodios largos del lab: todos con pps_medio 96–650 (tráfico elevado real); los cierres por histéresis
caen a 14 / 2 / 4 pps (fin del ataque); ninguno se atasca. "Ambiente" del CSV contaminado con destinos de
replays viejos (147.32.x y otros de Neris/CTU): el coste real es aún menor.

### 1.4 Implementado y verificado [DDOS-HYST-D291]
- `ddos_contract_v2.hpp`: `VictimEwmaParams` (defectos), rangos, `victim_ewma_params_ok`, estado
  `bajo_presion`; dentro, α_lento = (intervalo/1000)/τ. Clave que reaparece tras `evict` ⇒ estado a cero.
- 7 campos `ddos_victim_ewma_*` en `kernel_space` de sniffer.json con `_doc_*`; línea `[DDOS-HYST]` al
  arrancar con los valores activos (verificada; 0 `[CONFIG-DEFAULT]`).
- Test 12 (`test_ddos_victim_board`, 46 checks): 12a r_ent=4,8000 r_min=6,1865; 12b r_sal=0,8825
  r_2x=1,0212; 12c clave fría r=1,1369; 12d validación. Todos al 4.º decimal de lo predicho.
- Pilotos con el binario nuevo: 30 pps tramos 1–8 ratio 3,80 → 3,59; 60 pps 6,85 → 6,16 (antes ≈ 1 a los
  20 s). Tras el ataque vuelve a ≈ 1 (antes se hundía a 0,3–0,4 porque la base se había contaminado).
- Paridad offline ↔ vivo (`scripts/d291_paridad.py`, float32 + %g): 0 discrepancias en 184 y 197 ventanas.

### 1.5 Corridas en frío de DAY288
Con < 30 ventanas previas la histéresis no entra: su `victim_rate_ratio` es IDÉNTICO con el código nuevo.

## 2. Decisiones de Alonso DAY291
- El inicio de un ataque no se ignora ("como un ping sofisticado"): histéresis (opción B), con salida lenta
  para no dejar falsos positivos permanentes. Parámetros: K_in=3, K_out=1,5, τ=3600 s, caliente=30 ventanas.
- Etiquetado: la IP no es rasgo; .51 solo sirve para saber la verdad por construcción. Las filas de .51
  durante el ataque van al entrenamiento como BENIGNAS (el modelo debe aprender a no bloquear al inocente)
  y algunas corridas se RESERVAN para medir aparte ese falso positivo (puerta "cero bloqueos benignos").
- Política de configuración (arriba) y visión enterprise al BACKLOG.

## 3. Siguiente (DAY292): la batería caliente
1. Localizar los pcaps de udpA y udpB (bloques de CICDDoS2019, DAY287–288) y su `--limit`, en sesiones
   anteriores o en el MANIFEST/`runs.tsv` de day288; NO suponer rutas.
2. Script de corrida del client con dos modos de línea base: UDP (pcap .51) para ntp/dns/udpA/udpB y TCP
   viva (subida a 10 KB/s desde .51) para syn. Mismo protocolo que el piloto: 90 s de base, ataque 90 s,
   base sigue durante el ataque; reinicio del pipeline por corrida; escritor encendido.
3. Batería: ntp/dns/syn/udpA/udpB × 30/60/100 pps + contrastes bdns_small/bdns_large en caliente +
   pendientes (ráfaga TCP corta legítima; UDP benigno hacia .1). Predicción escrita por familia ANTES.
   Expectativa honesta: syn vs subida TCP y ntp/dns vs bdns_small se separan por rasgos de flujo/tamaño;
   dns vs bdns_large probablemente NO paquete a paquete (límite de la decisión por paquete).
4. Reentrenar: test, familia fuera (¿sube SYN?), tasa reservada, sonda de victim_pps, corridas .51
   reservadas (FP colateral), contraste.
Puertas (no se negocian): paridad Python/C++; `.hpp` con umbrales CRUDOS (sin scaler); tamaño del bosque
medido (latencia/tamaño vs acierto); cero bloqueos en corridas benignas E2E. Luego cablear firewall por
`final_decision` (solo DDoS), medir E2E, PR, merge, etiqueta `pre-release-ddos-only-0.0.3`.

## 4. Herramientas DAY291 (commiteadas)
`day291_patch_ewma_histeresis.py`, `day291_piloto_client.sh PPS`, `day291_piloto_medir.sh [CSV]`,
`day291_piloto_diag.sh CSV`, `day291_ventanas.sh CSV [s]`, `scripts/d291_histeresis_offline.py`,
`scripts/d291_paridad.py`, `scripts/d281_tcp_upload.py` (5.º argumento: IP de origen).
Evidencia (NO trackear): `/vagrant/logs/lab/day291/` (predicciones, medidas, paridad).
