# DAY309 — Registro de tests y efecto de la caducidad en ddos_v2, antes y después

Rama `feat/sniffer-flow-expiry`. Commits del día antes de este documento: `f422b96a` (registro de tests en ctest) y
`8f4cd0a3` (BACKLOG). Las secciones 1 a 3 recogen el diseño y las predicciones tal como se escribieron antes de medir;
el resultado va en la sección 4.

## 1. Registro de tests (hecho; detalle en `docs/BACKLOG.md`, DAY309)

El inventario completo de `sniffer/CMakeLists.txt` (cada `add_executable` contra su `add_test`) dio 5 tests sin
registrar, no 3. Se registraron los cuatro que pasan; `test_payload_analyzer` falla 4 de 18 desde `00a67a6a` y va a
DEBT-SNIFFER-PAYLOAD-ANALYZER-001. `make test-components PROFILE=production`: flow_uid 9, sniffer 23 (antes 19),
ml-detector 15, autonomía 3, firewall 82 = 132, 0 fallos.

## 2. Diseño del antes/después (escrito antes de medir)

- **"Antes" = `main` en `57d1d400`.** `git diff main..rama` sin `docs/` ni `scripts/` toca 40 ficheros, todos en
  `sniffer/` (0 fuera). El `sniffer.json` también cambia (sección `flow_table`), así que el "antes" es el árbol entero:
  `git switch --detach 57d1d400` en el mismo árbol y `make pipeline-build PROFILE=production` (las rutas del Makefile
  están fijas en `/vagrant/...`; un `git worktree` aparte no compilaría contra lo suyo).
- **A — `make lab-e2e-mitigacion`** (DAY302-303, dentro de EMECAS) tal cual, con veredicto automático. No ejercita la
  caducidad: su pausa entre ataques es de 120 s (< 300 s de `idle_timeout_s`) y su client usa tuplas disjuntas en el
  segundo ataque precisamente porque la tabla no caducaba.
- **B — batería caliente de DAY292 (ntp, dns y syn a 60 pps) y corrida benigna de DAY294**, cada corrida en su propio
  arranque del pipeline. Los clients son copias que solo cambian el directorio de salida (para no pisar
  `logs/lab/day292` ni `day294`); el envoltorio arranca y para el receptor TCP de `syn` y de la benigna.
- **C — corrida "hueco"**, nueva: base .51 a 10 pps durante 580 s; ataque NTP desde .50 a 60 pps durante 60 s a los
  60 s; 330 s de silencio del atacante; el **mismo** tramo de 3 600 paquetes (3 510 tuplas) a los 450 s.
- **Común a B y C:** escritor del dataset DDoS del ml-detector encendido solo durante la prueba
  (`day289_dataset_writer.py`, JSON restaurado con `cmp`); firewall de serie (sombra); el directorio de la corrida no
  puede existir antes (no se mezclan corridas). Herramientas en `logs/lab/day309/tools/` (ignorado por git) para
  correr igual en los dos árboles; se copian a `scripts/flow_expiry/` con el mismo sha256.
- **Qué ve cada instrumento.** El CSV del escritor DDoS (idéntico en los dos lados) guarda los 6 rasgos más
  `victim_rate_ratio` y `victim_pps` por evento, pero no la decisión ni `victim_state`; las decisiones se leen en los
  registros INICIO/FIN de la sombra y en el resumen `[DDOS-V2] bajo_presion / ataque` del ml-detector.

## 3. Predicciones (escritas antes de medir)

Los `flow_packet_count` (fpk) se calcularon simulando la tabla de flujos (con y sin `idle_timeout_s` 300) sobre las
tuplas reales de los pcaps, regenerados con sus generadores deterministas: `ntp_reflex_10k_lab`, `dns_reflex_10k_lab`,
`syn_flood_10k_lab`, `benign_dns_ntp_small_5k_lab` y `ntp_reflex_63k_disjunto_lab` dieron el sha256 del MANIFEST; la
base `.51` se reprodujo reescribiendo la IP de origen (mismas tuplas y tiempos; sha256 distinto por la reescritura de
checksums de `tcprewrite`).

**A:** PASA en `main` y en la rama.

**B:** las corridas de la batería duran 210 s, así que la caducidad no puede tocar nada; en la benigna (450 s) solo
cambia la base.

| corrida | fpk del ataque (los dos lados) | fpk de la base `main` | fpk de la base rama |
|---|---|---|---|
| ntp 60 | 1,039 · {1: 5200, 2: 189, 3: 11} | 1,013 · {1: 2072, 2: 28} | igual |
| dns 60 | igual que ntp (misma semilla) | igual | igual |
| syn 60 | 1,000 · {1: 5400} | (subida TCP, un flujo) | igual |
| benigna | — | 1,026 · {1: 4384, 2: 114, 3: 2} | 1,023 · {1: 4400, 2: 98, 3: 2} (16 reinicios) |

Decisiones iguales en las cuatro: mismos INICIO y FIN, y suma de `ataque` y de `bajo_presion` a ≤ 5 % relativo (el ruido
medido en A y C fue del 0,1-0,4 %).

**C:** en el ataque todas las tramas miden 482 B, así que lo único que la caducidad puede cambiar es fpk.

| fpk | ataque 1 | ataque 2 | base .51 |
|---|---|---|---|
| `main` | 1,027 · {1: 3510, 2: 84, 3: 6} | 2,080 · {2: 3426, 3: 78, 4: 84, 5: 6, 6: 6} | 1,026 |
| rama | 1,027 · igual | igual que el ataque 1 | 1,023 · {1: 5673, 2: 123, 3: 4} (22 reinicios) |

Rama: `caducados` ≥ 3 510; sombra con 2 INICIO y 2 FIN. Lo que decide la cabeza en el ataque 2 de `main`, con flujos
que heredan el ataque 1: no se predijo, es lo que se mide.

## 4. Resultado (escrito después de medir)

### 4.1 A — E2E de mitigación

| Criterio | `main` | rama |
|---|---|---|
| C1 .50 entra tras el ataque 1 | 4,2 s | 5,3 s |
| C2 contador DROP en el ataque 1 | 33 → 3 388 | 62 → 3 376 |
| C3 protegido .61 / base .51 en el set | 0 / 0 | 0 / 0 |
| C4 .50 sale tras el ataque 1 | 61,3 s | 61,4 s |
| C5 entra / sale en el ataque 2 | 3,8 s / 121,2 s | 4,6 s / 121,6 s |
| RENOVAR de .50 | 6 775 | 6 749 |
| Resultado | **PASA** | **PASA** |

### 4.2 B — batería caliente y benigna

| corrida | predicción de fpk (`main` / rama) | INICIO / FIN | `ataque` | `bajo_presion` | resultado |
|---|---|---|---|---|---|
| ntp 60 | 2 de 2 / 2 de 2 | 1/1 · 1/1 | 5 364 · 5 379 (0,28 %) | 6 274 · 6 289 | iguales |
| dns 60 | 2 de 2 / 2 de 2 | 1/1 · 1/1 | 5 371 · 5 362 (0,17 %) | 6 281 · 6 272 | iguales |
| syn 60 | 1 de 1 / 1 de 1 | 1/1 · 1/1 | 5 378 · 5 334 (0,82 %) | 6 293 · 6 240 | iguales |
| benigna | 1 de 1 / 1 de 1 | 0/0 · 0/0 | **0 · 8** | 17 785 · 17 872 (0,49 %) | ver 4.3 |

En la benigna, la base dio 1,026 (`main`) y 1,023 (rama), lo predicho. La tabla de flujos de la rama, en la batería:
`caducados` 0, `desalojos_lru` 0, `marcas_futuras` 0 (corridas de 210 s); en la benigna, 1 728 caducados.

### 4.3 La benigna: 0 frente a 8 positivos

El comparador la marcó DISTINTA porque el criterio relativo no sirve con base 0 (0 frente a 8 es siempre un 100 %).
Se investigó antes de concluir, con dos hipótesis escritas antes de mirar (H1: la subida TCP legítima, cuya
segmentación varía entre corridas; H2: flujos de la base reiniciados por la caducidad) y un evaluador fuera de línea
(`d309_p1_filas.cpp`) que recalcula la etapa 2 con el mismo bosque del ml-detector (`ddos_v2_head.hpp`) sobre cada fila
del dataset; comprobado contra la muestra de paridad de DAY293 (2 556 de 3 000, igual que sklearn).

- **Los 8 positivos de la rama están todos en la subida TCP legítima de .50** (un solo flujo, activo los 90 s, que la
  caducidad no toca); la base `.51` da 0 positivos en los dos lados. H1 se confirma; H2 queda descartada.
- **El bosque da exactamente 67 positivos en ese flujo en los dos lados:** sus primeros eventos (fpk 1 a 68, el
  arranque de la conexión), con p1 entre 0,53 y 0,99.
- **La diferencia está en la etapa 1:** en los eventos con fpk 61-68, `victim_rate_ratio` valía 5,0 en la rama y 2,814
  en `main`, justo por debajo de K = 3. El ratio sale del agregador por víctima del kernel (presión sobre .1 tras el
  tramo dnsperf a 100 q/s), no de la tabla de flujos.
- Ningún INICIO en ninguno de los dos lados: positivos aislados absorbidos por la política k = 3/5, como los 2 que
  DAY294 midió en esta misma corrida.

**Hallazgo aparte**, sin relación con la caducidad: la etapa 2 da p1 > 0,5 en el arranque de una subida TCP legítima y
en el tráfico del agente Wazuh (.12:1514, p1 hasta 1,0); solo los protege la etapa 1, y cerca de K se escapan positivos
aislados. El "TCP 50 KB/s: 0 positivos" de DAY294 depende, por tanto, de cuándo arranca la subida respecto a la
presión sobre la víctima. Va a deuda (DEBT-DDOS-V2-ETAPA2-FP-BENIGNOS-001).

### 4.4 C — corrida "hueco"

| | `main` (`hueco_antes`) | rama (`hueco_despues`) |
|---|---|---|
| hueco entre ataques | 330,0 s | 329,9 s |
| fpk ataque 1 | 1,027 · {1: 3510, 2: 84, 3: 6} | 1,027 · igual |
| fpk ataque 2 | **2,080** · {2: 3426, 3: 78, 4: 84, 5: 6, 6: 6} | **1,027** · igual que el ataque 1 |
| fpk base .51 | 1,026 · {1: 5651, 2: 145, 3: 4} | 1,023 · {1: 5672, 2: 124, 3: 4} |
| tamaño / entropía del ataque | 482,0 B / 0 | 482,0 B / 0 |
| sombra | 2 INICIO / 2 FIN, 87 s cada uno, p1 = 1,0000 | 2 INICIO / 2 FIN, 87 s cada uno, p1 = 1,0000 |
| eventos DROP (ataque 1 / 2) | 3 575 / 3 573 | 3 580 / 3 573 |
| `[DDOS-V2]` suma ataque / bajo presión | 7 148 / 8 368 | 7 153 / 8 373 |
| `[FLOW-TABLE]` caducados | — | 6 474 (pico de 4 004 en el hueco) |

Predicciones: 3 de 3 en cada lado. Las distribuciones del ataque coinciden fila por fila con la simulación; la base de
la rama, a un flujo (5 672 frente a 5 673).

### 4.5 Lectura

La caducidad cambia exactamente el rasgo de entrada predicho: el ataque que vuelve tras 330 s deja de heredar la
historia (fpk 2,08 de media) y empieza de cero (1,03); en la benigna se reinician los flujos de la base que pasan
300 s inactivos. **En ninguna de las siete corridas de cada lado cambia una decisión por la caducidad:** mitigación
real (A), cuatro corridas de la batería (B) y el ataque que vuelve (C). La única diferencia de decisión (0 frente a 8
positivos aislados en la benigna) se explica por la etapa 1 en el borde de K, en un flujo que la caducidad no toca.

### 4.6 Fallos y correcciones

- **Análisis del "hueco" v1:** el ataque 1 de `main` salió con media 1,056 y tamaño 480,3 B: el ping de fondo de
  "esperar ESTABLE" (ICMP de .50 a .1) caía en el primer grupo. La v2 filtra UDP con sport 123 y dice qué descarta; se
  reanalizaron los datos guardados, sin repetir corridas.
- **A, primer intento:** se saltó el paso que apartaba el directorio del "antes" y el "después" empezó a escribir en
  él. Se interrumpió; el registro limpio del "antes" es su consola (`logs/lab/day309/consola_mitigacion_antes.txt`) y
  el directorio quedó como `lab_mitigacion_antes_mezclado`. B y C se niegan desde el diseño a escribir en un directorio
  existente.
- **B, envoltorio v1:** comprobaba el receptor TCP con `pgrep -f` y lo paraba con `pkill -f`, que se encuentran a sí
  mismos (su línea de comandos contiene el patrón): "no arranca el receptor TCP" en la primera corrida `syn`
  (`b_syn_despues_fallido`). La v2 mira el puerto en `/proc/net/tcp` (`d309_escucha.py`) y para por PID. Al probarla
  apareció otro fallo: un comprobador roto sale con rc 1, igual que "no escucha", y arrancaba un receptor de más; el
  comprobador imprime ahora `ESCUCHA`/`NO_ESCUCHA` y el envoltorio lee el texto, nunca el código de salida.
- **Criterio de B:** la diferencia relativa ≤ 5 % no sirve con base 0; para positivos aislados hay que predecir una
  cuenta absoluta.
- **Instrumentos propios:** el simulador y la reescritura de la base leían los pcaps como little-endian (son
  big-endian); se detectó por una trama de 31 MB y por 239 tuplas del ataque que aparecían en la base, y se corrigió
  antes de escribir la predicción.

### 4.7 Qué no mide

- **Ataques de un solo origen y flujos cortos.** En C solo fpk podía cambiar y la etapa 2 está saturada (p1 = 1,0) para
  esa firma. El efecto del reinicio en flujos largos de tamaños variados, y el de `active_timeout_s`, se miden en el
  barrido de rama propia (con DEBT-DDOS-V2-LONG-ATTACK-001).
- **Una corrida por lado** en cada escenario.
