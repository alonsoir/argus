# Prompt de continuidad — aRGus NDR, DAY292 → DAY293 (v1, antes del feedback del Consejo)

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; si algo no da lo esperado, PARAR.
Comandos separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (`git grep` o el fichero concreto);
scripts como bloque `cat > f <<'EOF'`; `LC_ALL=C` en todo awk con aritmética; `set -e` sin `pipefail` junto a `| head`.
Comandos EXACTOS y COMPLETOS, en orden, diciendo dónde va cada uno (Mac / defender / client). Patchers atómicos,
todo-o-nada, con `--check` / `--apply` y marca. Compilar y probar con el MISMO perfil: `make pipeline-build PROFILE=production`
y `make test-components PROFILE=production`. Configuración: el JSON manda; defecto validado + `[CONFIG-DEFAULT]` y el proceso arranca.

**Foco único: la cabeza DDoS.** Orden: (1) observabilidad ✅, (2) contrato v2 ✅, (3) reentrenar y medir ✅ batería caliente
+ 3 modelos [falta: elegir candidato tras el Consejo y pasar las puertas], (4) fast-alert como entrada propia (FUERA del
firewall en este PR), (5) fusión + firewall por `final_decision` solo con la cabeza DDoS.

## 0. Estado de git
Rama `feat/ddos-head-contract`, NO mergeada. DAY292 pusheado: `2808233d` (inventario de pcaps + syn_flood_10k en el MANIFEST),
herramientas de la batería caliente, y consolidación/entrenamientos A/B/B-sinpps + análisis de fallos.
Comprobar: `git log --oneline -8 origin/feat/ddos-head-contract`.
Evidencia (NO trackear): `/vagrant/logs/lab/day292/` (predicciones, decisiones, medidas por corrida, consolidado, modelos).

## 1. Operativa de la batería caliente (DAY292)
- Client: `/vagrant/day292_bateria_client.sh FAM PPS`. Base .51→.1 a ~10 pps durante 210 s (UDP: pcap src51;
  `syn`: subida TCP viva a 10 KB/s). Ataque/contraste .50→.1 a PPS durante 90 s desde los 90 s. Aborta si falta el alias .51
  o si el pcap no da para PPS×90. Alias: `sudo ip addr add 192.168.100.51/24 dev eth1` (NO persiste al reiniciar la VM).
- Solo `syn`: sink en el defender DESPUÉS del ESTABLE y ANTES del client
  (`nohup python3 /vagrant/scripts/d281_tcp_sink.py 192.168.100.1 9000 > …/syn_R_sink.txt 2>&1 &`), y `pkill -f d281_tcp_sink.py`
  tras `make pipeline-stop`.
- Por corrida: truncate de logs → `make pipeline-start PROFILE=production FORCE_ALL_HEADS=1` → `/vagrant/day288_esperar_estable.sh`
  → client → (esperar a las dos líneas `Failed packets`) → `make pipeline-stop` → `/vagrant/day292_post.sh FAM PPS`
  (mide primero y registra en `runs_caliente.tsv` solo si encuentra el ataque).
- Medida: `/vagrant/day292_medir.py [CSV]` (kind=0, dst .1, tramos de 10 s desde la 1.ª fila de .50; BASE/ATQ/otro por proto).
- Consolidación: `python3 /vagrant/day292_consolidar.py 2.0` (roles atacante/contraste/inocente/ambiente_victima/ambiente,
  fase pre/durante/post, split D2, columna `arranque`) → `consolidado_caliente.csv` (sha f3d6b261…) + `manifiesto_caliente.sha256`.
- Entrenamientos: `day292_entrenar.py` (A), `day292_entrenar_b.py` (B), `day292_entrenar_b_sinpps.py` (B sin victim_pps).
  Fallos: `day292_fallos.py`.
- pcap SYN para la batería: `syn_flood_10k_lab.pcap` (sha 65b590c7…; sus 5000 primeros = el de 5k byte a byte).

## 2. Lo que DAY292 dejó MEDIDO
- Batería caliente COMPLETA: 19 corridas (ntp/dns/syn/udpA/udpB × 30/60/100 + bdns_small_10, bdns_large_5/10/20), 0 Failed,
  0 pérdidas en el anillo hasta 110 pps. BASE = ATQ en ratio en todos los tramos. Pendiente de α lento cumplida
  (ratio tramo 1→8: 30 pps ~3,7-4,0→3,6-3,7; 60 pps 6,85→6,15; 100 pps 10,6→8,95).
- Fase de entrada: si el ataque empieza al final de una ventana, la ventana parcial (< K_in) se absorbe con α rápido;
  EWMA implícita 11-11,6 frente a 10,1. Cota: ratio hasta ~17 % más bajo. udpB_60 explicado así (no es el pcap).
- K_in=3 en la práctica: 3× NO entra (bdns_large_20), 4× SÍ (syn_30). Contrastes vuelven a ≈1 en ~20 s.
- udpB: victim_pps = PPS+10 con ~35 % de filas → el kernel cuenta los fragmentos.
- TCP de ambiente SÍ comparte la clave {.1,TCP} (4-10 filas por corrida SYN); corrige el piloto TCP.
- Bosque viejo: subida TCP inocente 10 KB/s .51 marcada 100 %, SYN flood 0 %.
- Consolidado: atacante 74447 (train 50930 / test 23517), inocente 39911, contraste 4050, ambiente 7757, ambiente_victima 1765.
- Tres modelos (RF random_state=42, sin scaler, pesos jerárquicos):
  · A (con arranque, 8 rasgos): recall test 99,45 %; FP contraste 0,78 % (6 en arranque + 1 respuesta DNS legítima de 1442 B
    = tamaño exacto del ataque dns). Los 129 FN, todos en el arranque (≤1,4 s). 7168 nodos.
  · B (arranque del atacante fuera, 8 rasgos): 100 % fuera del arranque, FP 0 %; sonda ⇒ UMBRAL ABSOLUTO victim_pps ~30-40 pps
    (lo fijan las tasas del lab). Frío: 30 pps 0-2 %, 60/100 ~97 %. 4500 nodos.
  · B sin victim_pps (7 rasgos): 100 % fuera del arranque, FP 0 %, arranque 67,9 %, latencia 0,5-1,5 s; decide por ratio
    (relativo). Frío: 30 pps 0-1 %, 60 ~8 %, 100 ~13 %. 3714 nodos, profundidad 14.
  · Los TRES fallan con familia fuera: sin ntp ~0 %; sin syn marca ~99 % del inocente TCP ⇒ el modelo aprende FIRMAS de los
    generadores (tamaño + reflexión), no comportamiento.

## 3. Decisiones de Alonso DAY292
D1 entrenar con régimen CALIENTE (frío DAY288 solo evaluación). D2 test = corridas enteras de 60 pps + bdns_large_10.
D3 ambiente y otros orígenes hacia .1 benignos en entrenamiento. D4 arranque del atacante (2 s) fuera del entrenamiento y
medido aparte como latencia; el arranque del contraste se queda. Pesos jerárquicos aceptados.
Inclinación de Alonso: candidato = B SIN victim_pps, PENDIENTE del Consejo (docs/ml-heads/consejo_day292.md).
Plan: construir la cabeza tal como se ha trabajado y presentar al Consejo lo construido.

## 4. Siguiente (DAY293)
1. Leer el feedback del Consejo y decidir: candidato (B-sinpps / B / otro) y si se itera el dataset antes de cablear
   (generadores con tamaños aleatorios, base mixta UDP+TCP, bases de distinto volumen) o se cablea y se itera después.
2. Si se cablea: generador del `.hpp` con umbrales CRUDOS (sin MinMax; el viejo GenerateDDOSCPPForest normaliza) y vector en
   el orden exacto de FEATS; si B-sinpps, el ml-detector consume 7 rasgos de ddos_embedded (el sniffer sigue emitiendo el
   campo 15 para observabilidad).
3. Puertas (no se negocian): paridad Python/C++; tamaño/latencia del bosque frente a acierto; cero bloqueos en corridas
   benignas E2E. Política del firewall: no bloquear por un paquete aislado (k de n o por víctima) — decidir con el Consejo.
4. Cablear firewall por `final_decision` (solo DDoS), medir E2E, PR, merge, etiqueta `pre-release-ddos-only-0.0.3`.

## v2 — tras el Consejo (MANDA sobre las secciones 3 y 4 de arriba)
Síntesis y decisiones D5-D9: docs/ml-heads/consejo_day292_sintesis.md. Propuesta de batería: docs/ml-heads/bateria_v3_propuesta.md.
- D5 forma del modelo decidida por medida (bloque 1b); partida = B sin victim_pps. D6 el modelo no bloquea con la clave fría.
- D7 orden: bloque 1 → bloque 2 → bloque 3. D8 el PR cierra con el firewall en SOMBRA. D9 arranque fuera del entrenamiento,
  dentro del test; latencia caliente y fría por separado. No se adopta nada que contradiga lo ya medido.

### Siguiente (DAY293) — bloque 1, offline, sin tocar el lab (datos: logs/lab/day292/consolidado_caliente.csv, sha f3d6b261…)
a. Intervalos: A, B y B-sinpps con varias semillas y varios splits POR CORRIDA (no por fila).
b. Forma: árbol único profundidad 2-4, regla explícita (ratio > K y firma; K barrido en validación), bosque 10-100 árboles ×
   profundidad 4-14; mismas particiones; recall fuera del arranque, recall@t, FP, familia fuera, nodos. Ganador = el más simple
   que pase las puertas.
c. Simulación offline de la política del firewall sobre las 19 corridas: estado de la víctima + k de n + ventanas consecutivas,
   mitigación por VÍCTIMA; métricas FP_block_event, time_to_block, recall@t; barrido de parámetros en validación.
d. Víctima fría: recorrer en el tiempo las corridas frías de DAY288 (logs/lab/day289/consolidado.csv y sus CSV) con el modelo
   relativo; ¿se detecta alguna vez un ataque sostenido? Predicción escrita antes.
Después: bloque 2 (cablear el ganador en sombra: .hpp con umbrales crudos en el orden exacto de FEATS, paridad Python/C++ del
modelo, tamaño/latencia, E2E con 0 eventos de bloqueo; el cableado se actualizará al añadir cabezas) y cerrar la propuesta v3
para llevarla sola al Consejo.

### Añadido tras GLM (adenda en consejo_day292_sintesis.md)
- 1b además: AUC por rasgo (stump, ninguno > 0,9), modelo FACTORIZADO (presión + clasificador condicional) frente al plano,
  sonda de encapsulación (+4/+24/+78 B en mean_packet_size).
- 1c además: disyuntor de saturación y tier duro por par origen→víctima solo como evaluación (la mitigación sigue POR VÍCTIMA).
- 1d: PRIMERO simular offline "EWMA congelada hasta 30 ventanas" (d291_histeresis_offline.py sobre ventanas frías),
  predicción GLM: recall frío 60/100 ~90-100 %. Después re-capturar frío con el binario actual (ntp y syn a 60/100 + subida
  legítima en clave joven para el coste de congelar).

## v3 — DAY293: bloque 1 CERRADO (manda sobre la v2)
Resumen, decisiones D10-D14 y preguntas para el Consejo: docs/ml-heads/bloque1_day293.md. Scripts: scripts/d293_*.py.
Modelo: FACTORIZADO (etapa 1 victim_rate_ratio >= K=3 global; etapa 2 RandomForest sobre los 6 rasgos de flujo, entrenado solo
con filas bajo presión, arranque del atacante fuera). Política del firewall por víctima en sombra: m=5, k/n=3/5, hold=30 s
(defectos de laboratorio, en el JSON del firewall).
### Siguiente — bloque 2: cablear en sombra
- Etapa 1 en el ml-detector: K en su JSON (defecto validado + aviso). Etapa 2: .hpp generado con umbrales CRUDOS (sin MinMax)
  en el orden exacto de FLUJO; paridad Python/C++ del modelo con precisión completa; determinismo; tamaño/latencia del bosque.
- Firewall en SOMBRA: registra final_decision y lo que habría bloqueado POR VÍCTIMA con m/k/n/hold del JSON; no bloquea.
- E2E con 0 eventos de bloqueo en corridas benignas; después, PR, merge y etiqueta pre-release-ddos-only-0.0.3.

## v4 — DAY293 cierre: bloque 2 casi cerrado (manda sobre la v3)
Hecho y pusheado: cabeza ddos_v2 factorizada en C++ (paridad 127930/127930), cableada en el ml-detector (cada evento de flujo,
sin compuerta de level1; final_decision y overall_threat_score = solo ddos_v2); firewall en SOMBRA (dry_run true, compuerta por
final_decision, DdosShadowPolicy por víctima, resumen periódico [SOMBRA-DDOS], sin bloqueo por origen).
MEDIDO EN VIVO (ntp 60 + base .51): ml-detector bajo_presion=700 ataque=600 por 10 s (atacante 100 %, inocente 0 %); 0 en benigno;
firewall recibió 5335 DROP solo del atacante. La sombra NO abrió INICIO por los dos relojes de event_timestamp
(DEBT-EVENT-TIMESTAMP-TIMEBASE-001); corregido con el patcher [DDOS-SHADOW-RELOJ-D293] (solo eventos de flujo), compilado,
PENDIENTE DE VERIFICAR EN VIVO.
### Siguiente (DAY294)
1. Repetir E2E ntp 60 (truncate -> pipeline-start -> esperar_estable -> client -> 60 s -> pipeline-stop) y:
   grep -n 'SOMBRA-DDOS' /vagrant/logs/lab/firewall-agent.log | grep -v 'resumen:'
   Predicción: 1 INICIO ~3-4 s tras el primer DROP, 1 FIN ~30 s tras el último, origenes solo 192.168.100.50 (~5335).
2. Si cumple: una corrida benigna más larga (0 INICIO), documentar el bloque 2, cerrar PR feat/ddos-head-contract, EMECAS+++,
   merge y etiqueta pre-release-ddos-only-0.0.3.
3. Llevar al Consejo: bloque1_day293.md + propuesta v3 + preguntas (etapa 2 por comportamiento, valores por defecto, disyuntor).
