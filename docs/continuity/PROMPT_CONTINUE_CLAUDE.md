# Prompt de continuidad — aRGus NDR, DAY294 -> DAY295

Reglas (sin cambios): medir, no votar; predicción escrita antes de medir; si algo no da lo esperado, PARAR.
Comandos EXACTOS y COMPLETOS, en orden, diciendo dónde va cada uno (Mac / defender / client). Comandos separados o cada
salida a su fichero, y con `; cat` del fichero al final. Nunca `grep -rn` desde la raíz (`git grep` o el fichero concreto).
Scripts como bloque `cat > f <<'EOF'`; `LC_ALL=C` en todo awk con aritmética. Patchers atómicos, todo-o-nada, con
`--check` / `--apply` y marca. Compilar y probar con el MISMO perfil: `make pipeline-build PROFILE=production` y
`make test-components PROFILE=production`. Configuración: el JSON manda; defecto validado + `[CONFIG-DEFAULT]`.
Antes de pipeline-start: comprobar que no hay nada vivo (vagrant ssh defender -c "tmux ls; pgrep -a -f ...").

## 0. Estado
- main = bc73b831 (Merge PR #143), etiqueta `pre-release-ddos-only-0.0.3`: cabeza DDoS v2 factorizada en SOMBRA.
- Rama actual: `fix/event-timestamp-timebase` (desde main). Lleva: consejo_day294.md, paper_apoyo_ddos_v2.md,
  consejo_day294_sintesis.md (DECISIONES D15-D22, leer primero), BACKLOG y este prompt.
- Lab: chrony sirve la hora desde el defender a la red interna; client ^* 192.168.100.1 (verificado tras EMECAS).
  Monotónico del defender a epoch: time.time() - time.monotonic().

## 1. Objetivo de la rama (D16 + D17, y D15 como aceptación)
Una sola base de tiempo: monotónico para ventanas, hold, time_to_block y orden; epoch solo en los bordes (Parquet,
logs) vía ancla por nodo; CLOCK_STEP y re-anclaje al detectar un salto de pared; boot_id, node_id, secuencia por
productor y versión del contrato. Más retraso enq/deq y contadores por tipo de evento. TAI descartado (salta con makestep).

## 2. DAY295, en orden
1. MEDIR antes de diseñar: inventario de quién escribe event_timestamp / timestamp_utc_ns y con qué reloj (sniffer:
   eventos de flujo, ventanas, fast-alert; ml-detector: CSV y eventos; firewall: sombra y CSV; Parquet; bronce).
   Con `git grep`, tabla productor -> reloj -> consumidores. Predicción escrita antes.
2. Prueba de suspensión: registrar MONOTONIC y BOOTTIME en el defender antes y después de suspender el portátil;
   decide MONOTONIC frente a BOOTTIME.
3. Diseño del contrato temporal (doc corto) y, después, patchers por componente.
4. Pruebas: saltos de pared +-5 s inyectados en mitad de un ataque (hold 30 +- 0,1 s, orden intacto); validador de
   Parquet sobre TODAS las filas; Parquet 100 % en rango.
5. Aceptación D15: contabilidad A1 (tcpdump en .1 frente a eventos DROP), gemelo A2 (.61 a 10 y 60 pps), ataque largo A5
   (primero offline).
6. EMECAS+++, PR, merge.

## 3. Pendiente fuera de esta rama
- Semana: PR de limpieza de scripts de la raíz + README.
- Después: rama de medidas y modelo (D18, D19, D21, luego D20). D22 cuando haya cliente.
- Antes de publicar en LinkedIn: corregir "~1.3 s" por "~1–2 s".
