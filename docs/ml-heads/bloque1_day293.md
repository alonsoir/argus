# Bloque 1 (offline) — DAY293: cabeza DDoS, contrato v2 + histéresis D291

Datos: logs/lab/day292/consolidado_caliente.csv (sha f3d6b261…, 19 corridas calientes) y logs/lab/ddos_windows.csv
(contadores del kernel; corridas frías DAY288 = arranques 46-52 y 54-65 del 2026-10-05; los ficheros DAY288 van en UTC).
Evidencia y predicciones escritas antes de medir: logs/lab/day293/ (no trackeado). Scripts: scripts/d293_*.py.

## 1d — víctima fría (d293_frio_offline.py)
- Pizarra actual (D291): 0 ventanas en presión en las 15 corridas de ataque frías (30/50/100 s de ataque). Un ataque constante
  que empieza sobre una víctima sin historia es INVISIBLE para el estado de presión, dure lo que dure: la EWMA lo absorbe antes
  de que la clave cumpla `warm` ventanas.
- EWMA congelada hasta `warm` (propuesta GLM): presión en 70-76 % (30 pps), 40-48 % (60), 3-16 % (100) de las ventanas de
  ataque; los primeros 30 s se pierden siempre. Equivale a la regla absoluta "≥ K_in × suelo = 30 pps en clave joven"
  (ataques a 30 pps entran con rmax 3,00-3,12). Coste: benigno a 50 pps en clave joven 57 % en falsa presión (0 % con la
  pizarra actual). Predicción GLM 90-100 % NO cumplida. NO SE ADOPTA (D10).
- Un reinicio con la pizarra actual NO produce falsos positivos (ambiente: 0 episodios): produce una ventana CIEGA.
- El estado (EWMA, presión, ventanas vistas) vive en la pizarra de espacio de usuario (ddos_victim_board), no en el mapa
  ddos_victims (16 B = contadores de ventana); fijar el mapa en bpffs no conserva nada útil.

## 1a — intervalos (d293_intervalos.py, d293_detalle.py)
- 61 splits POR CORRIDA (D2 + 60 aleatorios: una tasa por familia y un contraste a test) × semillas 42/7/1234.
  Paridad: el split D2 reproduce DAY292 exacto (nodos 7168/4500/3714, FP contraste A 0,78 %, arranque B-sinpps 67,94 %).
- Mediana 100 % en los tres modelos, pero mínimos: B-sinpps 84,41 %, B 92,78 %, A 99,99 % (A con FP contraste hasta 4,5 %,
  siempre con bdns_large20 en test).
- Causa medida: el bosque plano aprende un umbral de victim_rate_ratio POR REGIÓN DE FIRMA (ratio × mean_packet_size).
  Contraste benigno de train ≤ 2,60; ataques a 30 pps 3,22-4,01. Si la tasa de 30 pps de una familia no está en train, la
  frontera cae en el hueco 2,6-6 y la SEMILLA decide (S7/B-sinpps: syn30 19 % con semilla 7, 100 % con 42).
  No se cura con más semillas: es la forma del modelo.

## 1b — forma del modelo (d293_formas.py, d293_formas_ii.py)
- Salud (AUC de un rasgo solo): victim_rate_ratio 0,907 y victim_pps 0,906 (la señal de diseño; < 1 porque el inocente
  comparte el ratio); mean_packet_size 0,69; el resto 0,51-0,62.
- 61 splits: regla sola (ratio ≥ 3) 100 % recall pero FP inocente durante 82,6 % (confirma a GLM). Árboles planos d2/d3
  FP inocente durante 66 %; d4 pasa 48/61. FACTORIZADO (etapa 1 ratio ≥ K=3 global; etapa 2 sin ratio, entrenada solo con
  filas bajo presión): fact_rf 183/183 pasan la puerta; fact_arbol_d2/3/4 61/61 (recall 99,69-99,99 %).
- Árbol fact d2 abierto: parte por bandas de tamaño del lab (≤ 72 B ataque SYN; 72-251 B benigno; > 251 B con
  flow_completion_rate ≤ 0,25 ataque de reflexión).
- Familia fuera: ntp fuera → plano_rf 0 %, árboles 0 %, fact_rf 100 %; dns fuera → árbol d2 0 %, resto 100 %;
  syn fuera → TODOS marcan ~99 % del inocente TCP durante (nunca vieron inocente TCP bajo presión).
- Encapsulación (+4/+24/+78 B en mean_packet_size): plano_rf inmune; factorizado FP inocente durante 0,9 / 7 / 24 %;
  árboles pierden 23 % de recall desde +24 B.
- Decisión (D13): estructura factorizada; etapa 2 = fact_rf (~1800 nodos, menos de la mitad que el plano); árboles
  descartados (ntp fuera 0 %). Limitaciones aceptadas y declaradas: syn fuera y encapsulación (la etapa 2 separa por firmas
  de tamaño de los generadores del lab) ⇒ batería v3 y Consejo.

## 1c — política del firewall por víctima, en sombra (d293_politica.py)
- Predicción por fila fact_rf leave-one-run-out: recall fuera del arranque 100 %, arranque 61,17 %, FP 0 en todos los roles.
- Víctima {dst_ip, proto}, ventanas de 1 s; ventana positiva si marcadas ≥ m; bloqueo si k de las últimas n; suelta tras hold.
- Rejilla m ∈ {1,2,5,10} × k/n ∈ {1/1,2/3,3/3,3/5,5/5} × hold ∈ {5,30}: 15/15 ataques detectados y 0 eventos de bloqueo
  falsos en TODA la rejilla, también con +78 B (FP de fila inocente 22 %, pero bajo ataque real sobre la misma víctima).
  time_to_block (±1 s): 2 s (1/1), 3 s (2/3), 4 s (3/3, 3/5), 6 s (5/5); cobertura 93-99 %. m apenas influye (K=3 con suelo
  10 ⇒ la etapa 1 solo actúa sobre ~30 filas/ventana o más).
- LÍMITE: la política NO queda validada frente a falsos positivos; el dataset no tiene subidas benignas ≥ 3× (contraste
  máximo 2,6). Exige la v3 (benigno 4-6×).
- No simulados: disyuntor de saturación (tal como se propuso saltaría en todo ataque real: hay que redefinirlo) y nivel
  duro por par origen→víctima.

## Decisiones de Alonso (DAY293)
- D10 La EWMA congelada no se adopta (medida en 1d).
- D11 Foto de la pizarra por víctima al parar, recargada al arrancar: en disco, firmada y cifrada con una clave guardada en
  Vault y aprovisionada en `make provision-crypto` (scripts/jenkins/provision_crypto.sh, ADR-044), sin rotación por ahora;
  antigüedad máxima en el JSON. Si falta, no valida o es vieja: arranque en frío con aviso claro en el log.
  Un reinicio o una rotación de claves no puede verse nunca como ataque.
- D12 Víctima fría de verdad: regla fría declarada por el admin en el JSON, fuera del modelo (humano en el bucle).
  Clave fría = menos de `warm` ventanas vistas.
- D13 Estructura factorizada con K global en el JSON (defecto 3, alineado con K_in); etapa 2 = fact_rf.
- D14 Política del firewall por víctima en el JSON del firewall, con rangos y formato documentados, valor por defecto validado y
  aviso al admin si un campo falta o es inválido. Defectos de LABORATORIO: m=5, k/n=3/5, hold=30 s. Validados solo en latencia;
  frente a FP, pendientes de la v3. Para un despliegue real, los valores por defecto se consensúan con el personal profesional
  de la instalación: nosotros damos los que nos sirven para nuestras pruebas.

## Preguntas para el Consejo (con la propuesta v3)
1. Etapa 2 por comportamiento y no por firma: cuota del origen en los pps de la víctima, novedad del origen
   (victim_src_newness). ¿Otros rasgos por origen que conozcáis?
2. Syn fuera y encapsulación: ¿basta con diversificar el dataset (base mixta UDP+TCP, tamaños solapados, encapsulación como
   aumento), o la etapa 2 debe dejar de usar el tamaño absoluto?
3. Valores por defecto de la política (m, k/n, hold) y de K: ¿qué criterios usaríais, y qué rangos son sensatos en una red
   hospitalaria?
4. Disyuntor de saturación: ¿cómo definirlo para que distinga un fallo del modelo de un ataque real?
