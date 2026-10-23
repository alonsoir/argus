# DAY305 — Interruptor de cabezas (DEBT-HEADS-SWITCH-001)

Rama `feat/heads-switch` (desde main `a0ba1d62`). Decisiones de Alonso: DAY300 (BACKLOG) y DAY305.

## Modelo resultante (decisión de Alonso, DAY305)

- **El sniffer recoge rasgos siempre y su única cabeza es el fast-path** (`fast_detector.enabled`): capa 1, la
  alerta rápida por paquete, y capa 2, las ventanas de ransomware con su puntuación. En el sniffer no hay ninguna
  otra cabeza activable, para que un admin no pueda duplicar trabajo por error.
- **La inferencia de las cabezas vive en el ml-detector**, cada una con su `enabled`. Hoy solo ddos_v2 está
  certificada; las demás se entrenarán una a una.
- **Regla de `enabled`** (todos los componentes): booleano JSON o texto `"true"`/`"false"` sin distinguir
  mayúsculas. Si falta o tiene otro valor, `false` (apagada) con `[CONFIG-DEFAULT]`, y el proceso arranca igual.
- **Enteros de configuración:** si faltan, no son enteros (`60.0` y `"60"` tampoco valen) o están fuera de rango,
  se aplica el defecto con `[CONFIG-DEFAULT]`, que nombra el campo, el formato y los límites. Los valores efectivos
  se registran al arrancar.
- **Laboratorio** (DAY300, mientras se trabaja DDoS): ddos_v2 encendida; level1, ddos_v1, ransomware, traffic,
  internal y fast-path apagados.
- **Autoridad futura:** el JSON da los valores por defecto. El que manda será el mensaje del etcd-server de la
  instalación, enviado por un admin autorizado: es la administración remota (DEBT-ETCD-REMOTE-ADMIN-001), que se
  diseña aparte y con calma. Apagar cabezas es una acción de seguridad crítica: el mensaje irá firmado y quedará
  registrado.

## Inventario medido (antes de tocar nada)

| Pieza | Proceso | Antes de la rama |
|---|---|---|
| fast-path (FastDetector) | sniffer | `fast_detector.enabled` decorativo: ingería siempre |
| procesador de ransomware | sniffer | se creaba siempre; dos intervalos de 30 s escritos a fuego |
| `run_ml_detection` | sniffer | ejecutaba en cada evento las 4 cabezas del ml-detector (mismas fuentes) y su resultado se sobrescribía antes de enviar |
| level1 | ml-detector | `enabled=false` hacía `return 1` |
| ddos_v1, ransomware, traffic, internal | ml-detector | flags obligatorios, solo al arrancar |
| ddos_v2 | ml-detector | flag por evento, defecto `true` |
| firewall | firewall | solo actúa con `final_decision == "DROP"` (ddos_v2) |

## Hecho (commits en `feat/heads-switch`)

| Commit | Qué |
|---|---|
| `57466e12` | ml-detector: level1 apagada no mata el proceso (`l1_on` gobierna rasgos, inferencia, predicción, veredicto, `ml_score` y autoridad); 5 `enabled` con defecto y aviso; línea `[HEADS]` |
| `802b000a` | JSON del laboratorio: solo ddos_v2 encendida |
| `12883c0a` | `monitoring.heads_log_interval_seconds` ([10, 3600], 60), con temporizador propio |
| `030c78bf` | Regla de Alonso: `enabled` ausente o inválido → apagada (también ddos_v2) |
| `ec0f3c4e` | Retirada la inferencia duplicada del sniffer: `run_ml_detection`, 4 detectores, umbrales `ml_defender`, 5 scripts d283/d284 (−715 líneas) |
| `01bcadb8` | Sniffer: el fast-path es su única cabeza; procesador de ransomware siempre (recogida de rasgos), emisión de ventanas solo con el fast-path; `fast_detector.ransomware.window_interval_seconds` ([5, 3600], 30); `[HEADS]`; parada ordenada (cierra DEBT-SNIFFER-RANSOMWARE-STOP-RACE-001) |
| `70e1c23b` | `heads_config.hpp` en cada componente y `test_heads_config` (71 comprobaciones por componente) |

## Medido

- **Coste retirado del sniffer:** unos 20 µs por evento de flujo (`[ML-TIME] calls=553 sum_ns=11188840`, máximo
  875 µs), que se iban en un resultado que se tiraba.
- **En vivo:**
  - ml-detector: `[HEADS] level1=OFF ddos_v2=ON …`, `inf:0`.
  - sniffer: `[HEADS] fast_path=OFF ventanas_ransomware=OFF procesador_ransomware=INICIALIZADO recogida_rasgos=SIEMPRE`,
    sin alertas ni ventanas; parada limpia, y las estadísticas finales ya no dicen "DISABLED".
- **Regresión de ddos_v2** (`make lab-e2e-protegidos LAB_E2E_DIA=day305`): PASA 5/5. DROP del FIN 10 770 (99,7 %),
  solo de .50; 5384 alertas de .61 protegido; identidad exacta (16 154 = 10 770 + 5384); 0 DROP del inocente .51;
  INICIO 2 s tras el primer DROP; secuencia sin huecos. DAY300 dio 10 742 / 5371.
- **Pruebas:** `test-components PROFILE=production` al 100 % en las cinco suites, con las dos `test_heads_config`
  nuevas.

## Pendiente antes de la PR

- **EMECAS+++ `PROFILE=production` desde cero.** Incluye los cinco E2E del laboratorio.
- **Medida de herramienta** (no bloquea la PR): CPU de sniffer y ml-detector con todo apagado frente a solo
  ddos_v2, coste de `populate` por evento y tamaño del protobuf. Alimenta la decisión de la recogida selectiva
  de rasgos.

## Deudas que salen de esta rama (en el BACKLOG, sección "Cierre DAY305")

DEBT-ETCD-REMOTE-ADMIN-001, DEBT-DDOS-V1-RETIRE-001 (rama siguiente), DEBT-FW-MITIGACION-ATADA-A-SOMBRA-001,
DEBT-SNIFFER-RANSOMWARE-PARAMS-001 y DEBT-SNIFFER-STOP-PROCESSING-QUEUE-001. Se amplía DEBT-REPO-RESIDUOS-001.
