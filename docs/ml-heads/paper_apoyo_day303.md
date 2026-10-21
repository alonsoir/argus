# Apoyo para el paper — DAY303

## Un gate "desde cero" que no lo era

El gate de calidad de aRGus (EMECAS: `vagrant destroy` → `vagrant up` → bootstrap → tests) se presentaba como
reconstrucción desde cero. Medido DAY303: no lo era. La carpeta del repositorio en el anfitrión se monta en las
VMs (`/vagrant`) y sobrevive a `vagrant destroy`, y con ella todos los directorios de compilación. Consecuencias
medidas, cada una con su fecha de fichero:

- los inyectores del E2E sintético llevaban sin recompilarse desde junio (el objetivo de compilación no los
  incluía): el E2E sintético probaba binarios de cuatro meses antes;
- el componente rag-security arrancaba un binario de perfil debug de abril, aunque la compilación producía otro
  en otro directorio;
- los enlaces del perfil activo (`build-active`) apuntaban a debug desde hacía seis días, aunque se compilaba en
  producción;
- el aprovisionamiento compilaba cuatro librerías sobre directorios de compilación anteriores, uno de ellos
  incluso versionado en git.

Ningún test fallaba: todo "funcionaba". La lección metodológica es que un gate verde no demuestra qué binario se
probó. DAY303 añade una comprobación explícita de frescura: un sello escrito tras crear las VMs y, tras compilar,
la comprobación de que cada binario del pipeline es más nuevo que el sello y es el que apunta el perfil activo.
Se validó en negativo antes de usarla: con un sello posterior a la compilación, 8/8 binarios FALLA.

## Dependencias ocultas del entorno

Los E2E de laboratorio de DAY300/302 esperaban a que el lector del kernel estuviera "estable" (≥ 10 sondeos en
30 s). El lector solo escribe las claves con paquetes en la ventana. En las corridas manuales, con cinco VMs, el
tráfico de fondo de los agentes Wazuh y de Zeek cumplía esa condición sin que nadie lo supiera; en el gate, con
tres VMs, el laboratorio estaba casi mudo (6 filas en 120 s) y la espera agotaba sus 15 minutos. Se sustituye el
fondo accidental por uno explícito y controlado (ICMP a 2 pps, otra víctima del agregador, solo durante la
espera). Una reconstrucción desde cero de verdad es lo que destapó la dependencia.

## Criterios PASA/FALLA del diseño, no del reloj

Los E2E pasan a puerta del gate con criterios derivados del diseño:
- identidad exacta, diferencia 0, entre lo que marca el ml-detector y los DROP del firewall (transporte sin
  pérdidas), y DROP_resúmenes = DROP_FIN + alertas en los rangos protegidos;
- restauración del estado según el modo de reinicio (sin estado / parada ordenada / `kill -9`);
- continuidad del marcado tras el reinicio como frontera entre los dos regímenes posibles (con estado ≈ 1,2-1,5;
  sin estado 0), no una banda temporal: la banda medida en DAY300 (1,15-1,40) depende de cuánto tarda la parada y
  una corrida correcta de DAY303 dio 1,487.

Los veredictos se validaron contra corridas ya juzgadas: aprueban las cuatro que DAY300 aceptó y rechazan la que
DAY300 rechazó (control negativo).

## Números de la corrida que certifica la rama

EMECAS+++ `PROFILE=production` desde cero: 2h32m, rc=0 (2026-10-21 08:40:20 → 2026-10-21 11:13:12).

    [VEREDICTO] PASA  R1 identidad: ml marcados 8260+0=8260 = firewall DROP_resumenes 8260
    [VEREDICTO] PASA  R2 restauracion: sin_estado_previo=2 restauradas=0 (1_bajo_presion=0) volcados_antes_de_restaurar=2 (1_bajo_presion=1)
    [VEREDICTO] PASA  R3 marcado: antes=8260 despues=0 (en frio, 0 tras el reinicio)
    [VEREDICTO] dato (no decide): razon despues/antes=0.000; banda DAY300 para ordenada/kill9 1,15-1,40
    [VEREDICTO] RESULTADO PASA (reinicio antes)
    [VEREDICTO] PASA  R1 identidad: ml marcados 8463+11827=20290 = firewall DROP_resumenes 20290
    [VEREDICTO] PASA  R2 restauracion: sin_estado_previo=1 restauradas=1 (1_bajo_presion=1) volcados_antes_de_restaurar=1 (1_bajo_presion=1)
    [VEREDICTO] PASA  R3 marcado: antes=8463 despues=11827 razon=1.397 (frontera 0,5)
    [VEREDICTO] dato (no decide): razon despues/antes=1.397; banda DAY300 para ordenada/kill9 1,15-1,40
    [VEREDICTO] RESULTADO PASA (reinicio ordenada)
    [VEREDICTO] PASA  R1 identidad: ml marcados 8525+11747=20272 = firewall DROP_resumenes 20272
    [VEREDICTO] PASA  R2 restauracion: sin_estado_previo=1 restauradas=1 (1_bajo_presion=1) volcados_antes_de_restaurar=0 (1_bajo_presion=0)
    [VEREDICTO] PASA  R3 marcado: antes=8525 despues=11747 razon=1.378 (frontera 0,5)
    [VEREDICTO] dato (no decide): razon despues/antes=1.378; banda DAY300 para ordenada/kill9 1,15-1,40
    [VEREDICTO] RESULTADO PASA (reinicio kill9)
    [VEREDICTO] PASA  P1 configuracion: intranet .61 del JSON (1), CONFIG-DEFAULT ddos_protegidos=0
    [VEREDICTO] PASA  P2 episodio: 1 FIN, origenes=192.168.100.50:10787
    [VEREDICTO] PASA  P3 alertas: alertas=5393 intranet=5393 dmz=0 externos_criticos=0 por_defecto=0
    [VEREDICTO] PASA  P4 identidad: DROP_resumenes 16180 = DROP_FIN 10787 + alertas 5393
    [VEREDICTO] PASA  P5 volumen: DROP_FIN 10787 en [10584, 10800], alertas 5393 en [5292, 5400]
    [VEREDICTO] RESULTADO PASA (protegidos)
    RESULTADO PASA
    === [11:00:38] HECHO: logs/lab/day303/lab_mitigacion/ (analisis rc=0)
