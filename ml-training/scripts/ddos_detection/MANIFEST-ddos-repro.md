# Manifiesto de reproducibilidad — artefacto DDoS (DAY256)

## Qué reproduce
`ml-detector/include/ml_defender/ddos_trees_inline.hpp`
sha256: 56f0c5ae8640cde93c213130cc26752500c4affa72a455f8d9b1fb468cf9bc68

## Cómo
Cadena canónica en `ml-training/scripts/ddos_detection/`, CWD = scratch limpio:
1. SyntheticDDOSGenerator.py   → ddos_detection_dataset.json (semilla np.random.seed(42))
2. DDosModelTrainer.py         → ddos_detection_model.pkl + ddos_scaler.pkl (random_state=42)
3. GenerateDDOSCPPForest.py <pkl> <hpp> → el .hpp
   Automatizado: `make ddos-regen` (corre dentro de la VM defender).

## Entorno MEDIDO que produce este sha
VM Vagrant `defender`, Debian bookworm, aprovisionada con:
numpy==2.4.6   scikit-learn==1.9.0   pandas==3.0.5

## Alcance del claim (honesto)
- MEDIDO: dentro de ESTA VM, con estas tres versiones, la cadena reproduce el sha
  byte a byte (verificado 2×, DAY255 y DAY256).
- MEDIDO y PORTABLE: el censo (`census_ddos_splits.py --sentinel geographical_concentration`)
  confirma la propiedad semántica —geo ausente, 9 features, 240 nodos internos / 340 hojas
  / 580 totales— con independencia de la versión. Este es el invariante que viaja.
- NO medido (por tanto NO afirmado): que una VM recién aprovisionada reproduzca el sha.
  El provisioning (Vagrantfile:440) instala numpy/sklearn/pandas SIN pin de versión → un
  `vagrant up` futuro puede traer otras versiones y otro sha. Clavar el pin + probar con
  `vagrant destroy && up` es la batalla siguiente (DEUDA-DDOS-REPRO-PIN).
- NO afirmado: que el detector sea útil sobre tráfico real. El modelo se entrena sobre
  Betas sintéticas; accuracy 1.0 es sobre sintético. Utilidad sobre Neris = Fase 2.

## Censo de referencia (GO)
splits por feature: syn_ack_ratio=1 packet_symmetry=12 source_ip_dispersion=3
protocol_anomaly_score=29 packet_size_entropy=58 traffic_amplification_factor=14
flow_completion_rate=22 traffic_escalation_rate=64 resource_saturation_score=37
geographical_concentration=0  ← GO