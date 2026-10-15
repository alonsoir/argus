# DAY298 — La etapa 1 de la cabeza DDoS con histéresis: antes y después medidos

Rama `fix/ddos-etapa1-histeresis`. Diseño: `docs/ml-heads/diseno_etapa1_histeresis_day298.md`.
Commits: 2866f4cc (antes y herramientas), 2085d708 (proto), 2be4a54c (sniffer), 0523b79a (ml-detector).

## 1. El problema

La cabeza DDoS v2 tiene dos etapas. La etapa 1 decide si una víctima está bajo presión comparando su tasa
con una base aprendida por EWMA (ratio = pps / max(EWMA, suelo) >= K = 3). La etapa 2 (RandomForest sobre
6 rasgos de flujo) solo juzga los flujos que pasan la etapa 1.

Medimos dos fallos de la etapa 1:

1. **Ataque sostenido absorbido.** Dentro de un episodio la EWMA seguía aprendiendo (alfa lento, tau = 3600 s),
   así que el ratio caía y la etapa 1 dejaba de pasar a t = tau·ln(3(r−1)/(2r)), con r el ratio inicial.
2. **Arranque en frío.** Con la EWMA vacía el ratio vale pps / suelo: cualquier tráfico de más de 30 pps pasa
   la etapa 1 (falsos pases), y un ataque presente al arrancar se aprende como base en unos segundos.

## 2. El arreglo

- El sniffer exporta el estado de la víctima en cada evento (FRÍO / NORMAL / BAJO_PRESIÓN; campo 16 del proto).
- Bajo presión la EWMA se congela: no aprende del tráfico del ataque. Una ventana sin tráfico cuenta como
  pps 0 y termina el episodio.
- Una víctima fría entra en presión si su tasa supera un umbral absoluto (abs_pps, defecto 200 pps).
- La etapa 1 del ml-detector usa el estado: presión pasa siempre, frío nunca, normal con ratio >= K.

## 3. Método

Laboratorio Vagrant (defender con el pipeline, client como origen). Reloj alineado (< 1 ms) antes de cada
corrida. Cada corrida desde un arranque limpio del pipeline (perfil production), captura en el cable,
contabilidad cable → eventos → decisiones con identidad exacta (diferencia 0 en todas). El firewall en
sombra registra los DROP que haría sin bloquear. Predicción escrita antes de cada medida.

Tráfico: reflexión NTP sintética desde .50 (482 B, puerto origen 123) y base legítima DNS/NTP desde .51.
Los flujos del sniffer no caducan por inactividad (deuda conocida), así que las corridas largas usan pcaps
generados sin ninguna 5-tupla repetida (`scripts/dataset_lab/gen_disjunto.py`, verificados con un contador
independiente; MANIFEST con SHA256).

## 4. Resultados

| Escenario | Antes | Después |
|---|---|---|
| Ataque sostenido 60 pps sobre base 10 pps, 1050 s (A5) | etapa 1 corta a 888,6 s (modelo: 885,7 s); 84,3 % marcado | sin corte; 99,97 % marcado (62978/63000); fin del episodio 30 s después del ataque |
| Base legítima durante el ataque | 0 DROP | 0 DROP (10510 flujos pasan la etapa 1; el RF los rechaza todos) |
| Frío, tráfico legítimo 50 pps | 200 pases indebidos de la etapa 1 | 0 |
| Frío, ataque 300 pps | (modelo: ~4 ventanas marcadas y luego aprendido) | 13373 pases = 13373 marcados, todo el ataque visible |
| Frío, ataque 60 pps | 1,2 % marcado, luego aprendido | 0 % (precio documentado: por debajo de abs_pps) |

Tests unitarios: `test_ddos_victim_board` (62 comprobaciones; 13a reproduce A5 durante 2 h) y
`test_ddos_v2_parity` (7 casos de la etapa 1 con estado; paridad Python/C++ exacta en 4000 filas).

## 5. Limitaciones (para decirlas en voz alta)

- abs_pps es un defecto seguro, no óptimo. En el laboratorio el tráfico legítimo de arranque llega a 14 pps
  (5 arranques) y una vez a 140 pps. Un ataque por debajo de abs_pps contra una víctima sin historia se
  aprende como base. Cada instalación debe calibrarlo.
- Hasta que el estado se persista entre arranques (pendiente), cada reinicio deja todas las víctimas en frío.
- Toda la reflexión viene de un único origen; en la realidad llega de miles de reflectores.
- Un solo laboratorio virtual; tasas modestas (hasta 300 pps).
- La etapa 2 sigue siendo el juez: con la víctima en presión, todos sus flujos pasan al RF, y un error del RF
  sería un falso positivo (un caso real: TCP de Wazuh, p1 = 0,86, DAY297).

## 6. Reproducir

Pcaps: `scripts/dataset_lab/MANIFEST.md` (sección DAY298). Corridas desde el Mac:
`DIA=day298 bash scripts/timebase/lab_corrida.sh NOMBRE 'DIA=day298 bash /vagrant/scripts/timebase/a5_vivo_client.sh NOMBRE'`
y `DIA=day298 bash scripts/timebase/lab_frio.sh NOMBRE 'comando del client' 120`. Análisis:
`d298_etapa1_resumen.sh`, `d298_alinear_sombra.sh`, `d298_frio_analisis.sh`.
