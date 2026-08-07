# paper-artifacts — cifras exactas del paper (arXiv:2604.04952 v25)

Estos ficheros son la **salida exacta** que respalda las cifras del paper,
committeados para que un revisor las lea **sin correr nada**. Corresponden a una
única corrida del pipeline sobre el replay del Neris (CTU-13, escenario 1),
identificada por su STAMP `20260804-080140`.

## Contenido

- `bias-report-20260804-080140.txt` — sesgo por-lente vs ground-truth CTU
  (join 5-tupla): visibilidad y matriz por lente (aRGus / Suricata / Zeek).
- `bias-denominator-true-20260804-080140.txt` — denominador VERDADERO del pcap
  (tshark) frente al lens-observable, y el hueco de fidelidad de replay.
- `dataset-modeA-20260804-080140.csv` — dataset modo A de esa corrida (una fila
  por evento de oro de las tres lentes). Es la entrada del join; permite
  re-ejecutar `scripts/join_bias_labels.py` sin regenerar la corrida.

## Reproducibilidad

`make reproduce-paper` regenera estos números **desde cero**. NO serán
bit-idénticos: el pcap de 2011 se replaya a `--mbps=10`, lo que reescribe los
inter-arrival, y tcpreplay descarta de forma determinista 2630 super-frames
GSO/TSO (0.81%) que no caben en Ethernet normal. Los números regenerados caen
**dentro de la varianza de replay**; los de aquí son la corrida anclada al paper.

## Procedencia (límite declarado)

El pcap Neris CTU-13 es de 2011, capturado por terceros (Stratosphere Lab /
MCFP, CVUT), en condiciones de captura desconocidas salvo el origen. Se declara
como límite: no se interpreta más allá de lo que miden tshark y el pipeline.
