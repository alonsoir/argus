# Protocolo de replay — DAY 86.md
# Experimento 1
(.venv) aironman@MacBook-Pro-de-Alonso argus % make up
Bringing machine 'defender' up with 'virtualbox' provider...
Bringing machine 'client' up with 'virtualbox' provider...
...
(.venv) aironman@MacBook-Pro-de-Alonso argus % make pipeline-stop
🛑 Stopping all pipeline components...
✅ Pipeline stopped
(.venv) aironman@MacBook-Pro-de-Alonso argus % make pipeline-start

...
╔════════════════════════════════════════════════════════════╗
║  ✅ FULL PIPELINE STARTED (Day 74)                        ║
╚════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════╗
║  📊 ML Defender Pipeline Status (via TMUX)                ║
╚════════════════════════════════════════════════════════════╝
✅ etcd-server:   RUNNING
✅ rag-security:  RUNNING
✅ rag-ingester:  RUNNING
✅ ml-detector:   RUNNING
✅ sniffer:       RUNNING
✅ firewall:      RUNNING
╚════════════════════════════════════════════════════════════╝
(.venv) aironman@MacBook-Pro-de-Alonso argus % sleep 15
(.venv) aironman@MacBook-Pro-de-Alonso argus % make test-replay-small
🧪 Replaying CTU-13 smallFlows.pcap...
Test start: 2026-03-14 07:16:23.730783 ...
Actual: 3624 packets (2500833 bytes) sent in 2.00 seconds
Rated: 1249959.0 Bps, 9.99 Mbps, 1811.33 pps
Actual: 8176 packets (5000865 bytes) sent in 4.00 seconds
Rated: 1249941.2 Bps, 9.99 Mbps, 2043.55 pps
Actual: 11931 packets (7501596 bytes) sent in 6.00 seconds
Rated: 1249840.8 Bps, 9.99 Mbps, 1987.82 pps
Test complete: 2026-03-14 07:16:31.104044
Actual: 14261 packets (9216531 bytes) sent in 7.37 seconds
Rated: 1249993.8 Bps, 9.99 Mbps, 1934.15 pps
Flows: 1209 flows, 163.97 fps, 14243 unique flow packets, 18 unique non-flow packets
Statistics for network device: eth1
Successful packets:        14261
Failed packets:            0
Truncated packets:         0
Retried packets (ENOBUFS): 0
Retried packets (EAGAIN):  0
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 07:16:12.434] [ml-detector] [info] 📊 Stats: received=18, processed=18, sent=18, attacks=0, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "cat /vagrant/logs/lab/sniffer.log" > /tmp/sniffer_small.log

(.venv) aironman@MacBook-Pro-de-Alonso argus % python3 scripts/calculate_f1_neris.py /tmp/sniffer_small.log --total-events XXXX --day "DAY86_small"

usage: calculate_f1_neris.py [-h] --total-events TOTAL_EVENTS [--day DAY] [--thresholds THRESHOLDS] sniffer_log
calculate_f1_neris.py: error: argument --total-events: invalid int value: 'XXXX'
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:17:12.443] [ml-detector] [info] 📊 Stats: received=1030, processed=1030, sent=1030, attacks=0, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:18:12.461] [ml-detector] [info] 📊 Stats: received=3370, processed=3370, sent=3370, attacks=0, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % echo "Es obvio que hacer el grep lleva tiempo. Esperamos un poco."
Es obvio que hacer el grep lleva tiempo. Esperamos un poco.
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:18:12.461] [ml-detector] [info] 📊 Stats: received=3370, processed=3370, sent=3370, attacks=0, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:19:12.464] [ml-detector] [info] 📊 Stats: received=7435, processed=7435, sent=7435, attacks=1, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:19:12.464] [ml-detector] [info] 📊 Stats: received=7435, processed=7435, sent=7435, attacks=1, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:19:12.464] [ml-detector] [info] 📊 Stats: received=7435, processed=7435, sent=7435, attacks=1, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:20:12.466] [ml-detector] [info] 📊 Stats: received=7441, processed=7441, sent=7441, attacks=1, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:21:12.467] [ml-detector] [info] 📊 Stats: received=7447, processed=7447, sent=7447, attacks=1, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:22:12.467] [ml-detector] [info] 📊 Stats: received=7457, processed=7457, sent=7457, attacks=1, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % wc -l /vagrant/logs/lab/ml-detector.log
wc: /vagrant/logs/lab/ml-detector.log: open: No such file or directory
(.venv) aironman@MacBook-Pro-de-Alonso argus % wc -l logs/lab/ml-detector.log
55474 logs/lab/ml-detector.log
(.venv) aironman@MacBook-Pro-de-Alonso argus % Cuando puedo sacar el número para el script python3 scripts/calculate_f1_neris.py /tmp/sniffer_small.log --total-events XXXX --day "DAY86_small"
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:26:12.470] [ml-detector] [info] 📊 Stats: received=7481, processed=7481, sent=7481, attacks=1, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:26:12.470] [ml-detector] [info] 📊 Stats: received=7481, processed=7481, sent=7481, attacks=1, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:26:12.470] [ml-detector] [info] 📊 Stats: received=7481, processed=7481, sent=7481, attacks=1, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 07:26:12.470] [ml-detector] [info] 📊 Stats: received=7481, processed=7481, sent=7481, attacks=1, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % python3 scripts/calculate_f1_neris.py /tmp/sniffer_small.log --total-events 7481 --day "DAY86_small"

====================================================================
ML DEFENDER - F1 SCORE CALCULATOR
Day: DAY86_small  |  Thresholds:
Ground truth: CTU-13 Neris (3 malicious IPs)
====================================================================
Malicious IPs: 147.32.84.165, 147.32.84.191, 147.32.84.192

====================================================================
FAST DETECTOR — deduplicated alerts vs ground truth
====================================================================
Raw [FAST ALERT] lines:      10064
Deduplicated alert events:   916
Total events (ml-detector):  7481

TP  (malicious, detected):   766
FP  (benign, false alarm):   150
FN  (malicious, missed):     0
TN  (benign, correct):       6565

Precision:  0.8362
Recall:     1.0000
F1-Score:   0.9108  ← paper metric
FPR:        0.0223
Accuracy:   0.9799

NOTE: FN estimated as 0 — [FAST ALERT] only fires on detected flows. True FN requires per-event IP table. Recall=1.0 is an upper bound, not confirmed.
====================================================================

DETECTED IPs breakdown:
147.32.84.165  →  766 flow(s) detected  [MALICIOUS ✓]

FALSE POSITIVE IPs (sample, max 5):
src=192.168.3.131  dst=65.55.5.232
src=72.14.213.147  dst=192.168.3.131
src=66.235.139.121  dst=192.168.3.131
src=65.55.239.163  dst=192.168.3.131
src=192.168.3.131  dst=65.55.239.163

CSV line for f1_replay_log.csv:
DAYDAY86_small,,7481,766,150,0,6565,0.9108,0.8362,1.0000,0.0223

# Experimento 2 — neris (el principal)
(.venv) aironman@MacBook-Pro-de-Alonso argus % make pipeline-stop && make logs-lab-clean && make pipeline-start && sleep 15

🛑 Stopping all pipeline components...
✅ Pipeline stopped
🧹 Rotating pipeline logs...
✅ Logs rotated to /vagrant/logs/lab/archive/

...
(.venv) aironman@MacBook-Pro-de-Alonso argus % make pipeline-status

╔════════════════════════════════════════════════════════════╗
║  📊 ML Defender Pipeline Status (via TMUX)                ║
╚════════════════════════════════════════════════════════════╝
✅ etcd-server:   RUNNING
✅ rag-security:  RUNNING
❌ rag-ingester:  STOPPED
✅ ml-detector:   RUNNING
✅ sniffer:       RUNNING
✅ firewall:      RUNNING
╚════════════════════════════════════════════════════════════╝
(.venv) aironman@MacBook-Pro-de-Alonso argus % make pipeline-health

╔══════════════════════════════════════════════════════════════╗
║      ML Defender — Pipeline Health Monitor                  ║
╚══════════════════════════════════════════════════════════════╝

🖥  VM Status:
defender: running
client:   running

📦 Pipeline Components:
Component              Status     PID        Log Activity
---------              ------     ---        ------------
etcd-server            ✅ UP     2760       ❓ no log
rag-security           ✅ UP     2817       ❓ no log
rag-ingester           ❌ DOWN   -          -         
ml-detector            ✅ UP     2936       ❓ no log
sniffer                ✅ UP     3170       ❓ no log
firewall               ✅ UP     3039       ❓ no log

📊 ML-Detector last stats:
received=16, processed=16, sent=16, attacks=0, errors=(deser:0, feat:0, inf:0)

⚠️  VM 'client' ya está RUNNING — no ejecutar 'vagrant up client'

╚══════════════════════════════════════════════════════════════╝

Me estoy dando cuenta que en el Makefile no tenemos una tarea para arrancar rag-ingester, por eso está parado.

(.venv) aironman@MacBook-Pro-de-Alonso argus % make rag-ingester-start
🚀 Starting RAG Ingester (Full Context)...
Ejecución desde la raíz del componente para resolver paths relativos del config...

╔════════════════════════════════════════════════════════════╗
║  📊 ML Defender Pipeline Status (via TMUX)                ║
╚════════════════════════════════════════════════════════════╝
✅ etcd-server:   RUNNING
✅ rag-security:  RUNNING
✅ rag-ingester:  RUNNING
✅ ml-detector:   RUNNING
✅ sniffer:       RUNNING
✅ firewall:      RUNNING
╚════════════════════════════════════════════════════════════╝
(.venv) aironman@MacBook-Pro-de-Alonso argus % make pipeline-health

╔══════════════════════════════════════════════════════════════╗
║      ML Defender — Pipeline Health Monitor                  ║
╚══════════════════════════════════════════════════════════════╝

🖥  VM Status:
defender: running
client:   running

📦 Pipeline Components:
Component              Status     PID        Log Activity
---------              ------     ---        ------------
etcd-server            ✅ UP     2760       ❓ no log
rag-security           ✅ UP     2817       ❓ no log
rag-ingester           ✅ UP     3679       ❓ no log
ml-detector            ✅ UP     2936       ❓ no log
sniffer                ✅ UP     3170       ❓ no log
firewall               ✅ UP     3039       ❓ no log

📊 ML-Detector last stats:
received=52, processed=52, sent=52, attacks=0, errors=(deser:0, feat:0, inf:0)

⚠️  VM 'client' ya está RUNNING — no ejecutar 'vagrant up client'

╚══════════════════════════════════════════════════════════════╝

Por qué ha fallado levantar rag-ingester antes?

(.venv) aironman@MacBook-Pro-de-Alonso argus % make test-replay-neris
🧪 Replaying CTU-13 Neris botnet (492K events)...
...
Test complete: 2026-03-14 07:43:41.718741
Actual: 320524 packets (44200259 bytes) sent in 39.68 seconds
Rated: 1113850.3 Bps, 8.91 Mbps, 8077.23 pps
Flows: 19135 flows, 482.20 fps, 322242 unique flow packets, 906 unique non-flow packets
Statistics for network device: eth1
Successful packets:        320524
Failed packets:            2630
Truncated packets:         0
Retried packets (ENOBUFS): 0
Retried packets (EAGAIN):  0
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 07:45:24.961] [ml-detector] [info] 📊 Stats: received=5941, processed=5941, sent=5941, attacks=0, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 07:47:24.962] [ml-detector] [info] 📊 Stats: received=11904, processed=11904, sent=11904, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 07:50:24.972] [ml-detector] [info] 📊 Stats: received=12046, processed=12046, sent=12046, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 07:50:24.972] [ml-detector] [info] 📊 Stats: received=12046, processed=12046, sent=12046, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 07:54:24.975] [ml-detector] [info] 📊 Stats: received=12214, processed=12214, sent=12214, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 07:54:24.975] [ml-detector] [info] 📊 Stats: received=12214, processed=12214, sent=12214, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 07:54:24.975] [ml-detector] [info] 📊 Stats: received=12214, processed=12214, sent=12214, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 07:57:25.012] [ml-detector] [info] 📊 Stats: received=12332, processed=12332, sent=12332, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "cat /vagrant/logs/lab/sniffer.log" > /tmp/sniffer_neris.log

(.venv) aironman@MacBook-Pro-de-Alonso argus % wc -l /tmp/sniffer_neris.log
38277 /tmp/sniffer_neris.log
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 07:59:25.012] [ml-detector] [info] 📊 Stats: received=12444, processed=12444, sent=12444, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 07:59:25.012] [ml-detector] [info] 📊 Stats: received=12444, processed=12444, sent=12444, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 08:00:25.012] [ml-detector] [info] 📊 Stats: received=12517, processed=12517, sent=12517, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 08:01:25.015] [ml-detector] [info] 📊 Stats: received=12563, processed=12563, sent=12563, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 08:01:25.015] [ml-detector] [info] 📊 Stats: received=12563, processed=12563, sent=12563, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % echo "Es suficiente?"
Es suficiente?
(.venv) aironman@MacBook-Pro-de-Alonso argus % python3 scripts/calculate_f1_neris.py /tmp/sniffer_neris.log --total-events 12563 --day "DAY86_neris"


====================================================================
ML DEFENDER - F1 SCORE CALCULATOR
Day: DAY86_neris  |  Thresholds:
Ground truth: CTU-13 Neris (3 malicious IPs)
====================================================================
Malicious IPs: 147.32.84.165, 147.32.84.191, 147.32.84.192

====================================================================
FAST DETECTOR — deduplicated alerts vs ground truth
====================================================================
Raw [FAST ALERT] lines:      5662
Deduplicated alert events:   648
Total events (ml-detector):  12563

TP  (malicious, detected):   646
FP  (benign, false alarm):   2
FN  (malicious, missed):     0
TN  (benign, correct):       11915

Precision:  0.9969
Recall:     1.0000
F1-Score:   0.9985  ← paper metric
FPR:        0.0002
Accuracy:   0.9998

NOTE: FN estimated as 0 — [FAST ALERT] only fires on detected flows. True FN requires per-event IP table. Recall=1.0 is an upper bound, not confirmed.
====================================================================

DETECTED IPs breakdown:
147.32.84.165  →  646 flow(s) detected  [MALICIOUS ✓]

FALSE POSITIVE IPs (sample, max 5):
src=192.168.56.1  dst=224.0.0.251
src=192.168.56.1  dst=192.168.56.255

CSV line for f1_replay_log.csv:
DAYDAY86_neris,,12563,646,2,0,11915,0.9985,0.9969,1.0000,0.0002

(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 08:02:25.023] [ml-detector] [info] 📊 Stats: received=12605, processed=12605, sent=12605, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % python3 scripts/calculate_f1_neris.py /tmp/sniffer_neris.log --total-events 12605 --day "DAY86_neris"


====================================================================
ML DEFENDER - F1 SCORE CALCULATOR
Day: DAY86_neris  |  Thresholds:
Ground truth: CTU-13 Neris (3 malicious IPs)
====================================================================
Malicious IPs: 147.32.84.165, 147.32.84.191, 147.32.84.192

====================================================================
FAST DETECTOR — deduplicated alerts vs ground truth
====================================================================
Raw [FAST ALERT] lines:      5662
Deduplicated alert events:   648
Total events (ml-detector):  12605

TP  (malicious, detected):   646
FP  (benign, false alarm):   2
FN  (malicious, missed):     0
TN  (benign, correct):       11957

Precision:  0.9969
Recall:     1.0000
F1-Score:   0.9985  ← paper metric
FPR:        0.0002
Accuracy:   0.9998

NOTE: FN estimated as 0 — [FAST ALERT] only fires on detected flows. True FN requires per-event IP table. Recall=1.0 is an upper bound, not confirmed.
====================================================================

DETECTED IPs breakdown:
147.32.84.165  →  646 flow(s) detected  [MALICIOUS ✓]

FALSE POSITIVE IPs (sample, max 5):
src=192.168.56.1  dst=224.0.0.251
src=192.168.56.1  dst=192.168.56.255

CSV line for f1_replay_log.csv:
DAYDAY86_neris,,12605,646,2,0,11957,0.9985,0.9969,1.0000,0.0002

(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 08:04:25.069] [ml-detector] [info] 📊 Stats: received=12685, processed=12685, sent=12685, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 08:04:25.069] [ml-detector] [info] 📊 Stats: received=12685, processed=12685, sent=12685, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 08:05:25.073] [ml-detector] [info] 📊 Stats: received=12723, processed=12723, sent=12723, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % python3 scripts/calculate_f1_neris.py /tmp/sniffer_neris.log --total-events 12723 --day "DAY86_neris"


====================================================================
ML DEFENDER - F1 SCORE CALCULATOR
Day: DAY86_neris  |  Thresholds:
Ground truth: CTU-13 Neris (3 malicious IPs)
====================================================================
Malicious IPs: 147.32.84.165, 147.32.84.191, 147.32.84.192

====================================================================
FAST DETECTOR — deduplicated alerts vs ground truth
====================================================================
Raw [FAST ALERT] lines:      5662
Deduplicated alert events:   648
Total events (ml-detector):  12723

TP  (malicious, detected):   646
FP  (benign, false alarm):   2
FN  (malicious, missed):     0
TN  (benign, correct):       12075

Precision:  0.9969
Recall:     1.0000
F1-Score:   0.9985  ← paper metric
FPR:        0.0002
Accuracy:   0.9998

NOTE: FN estimated as 0 — [FAST ALERT] only fires on detected flows. True FN requires per-event IP table. Recall=1.0 is an upper bound, not confirmed.
====================================================================

DETECTED IPs breakdown:
147.32.84.165  →  646 flow(s) detected  [MALICIOUS ✓]

FALSE POSITIVE IPs (sample, max 5):
src=192.168.56.1  dst=224.0.0.251
src=192.168.56.1  dst=192.168.56.255

CSV line for f1_replay_log.csv:
DAYDAY86_neris,,12723,646,2,0,12075,0.9985,0.9969,1.0000,0.0002

(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 08:16:25.086] [ml-detector] [info] 📊 Stats: received=13034, processed=13034, sent=13034, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 08:48:25.345] [ml-detector] [info] 📊 Stats: received=13930, processed=13930, sent=13930, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 08:48:25.345] [ml-detector] [info] 📊 Stats: received=13930, processed=13930, sent=13930, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % python3 scripts/calculate_f1_neris.py /tmp/sniffer_neris.log --total-events 13930 --day "DAY86_neris"


====================================================================
ML DEFENDER - F1 SCORE CALCULATOR
Day: DAY86_neris  |  Thresholds:
Ground truth: CTU-13 Neris (3 malicious IPs)
====================================================================
Malicious IPs: 147.32.84.165, 147.32.84.191, 147.32.84.192

====================================================================
FAST DETECTOR — deduplicated alerts vs ground truth
====================================================================
Raw [FAST ALERT] lines:      5662
Deduplicated alert events:   648
Total events (ml-detector):  13930

TP  (malicious, detected):   646
FP  (benign, false alarm):   2
FN  (malicious, missed):     0
TN  (benign, correct):       13282

Precision:  0.9969
Recall:     1.0000
F1-Score:   0.9985  ← paper metric
FPR:        0.0002
Accuracy:   0.9999

NOTE: FN estimated as 0 — [FAST ALERT] only fires on detected flows. True FN requires per-event IP table. Recall=1.0 is an upper bound, not confirmed.
====================================================================

DETECTED IPs breakdown:
147.32.84.165  →  646 flow(s) detected  [MALICIOUS ✓]

FALSE POSITIVE IPs (sample, max 5):
src=192.168.56.1  dst=224.0.0.251
src=192.168.56.1  dst=192.168.56.255

CSV line for f1_replay_log.csv:
DAYDAY86_neris,,13930,646,2,0,13282,0.9985,0.9969,1.0000,0.0002

Un par de horas más tarde, o algo más...

(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 12:04:26.613] [ml-detector] [info] 📊 Stats: received=17866, processed=17866, sent=17866, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 12:04:26.613] [ml-detector] [info] 📊 Stats: received=17866, processed=17866, sent=17866, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"

[2026-03-14 12:04:26.613] [ml-detector] [info] 📊 Stats: received=17866, processed=17866, sent=17866, attacks=12, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % python3 scripts/calculate_f1_neris.py /tmp/sniffer_neris.log --total-events 17866 --day "DAY86_neris"


====================================================================
ML DEFENDER - F1 SCORE CALCULATOR
Day: DAY86_neris  |  Thresholds:
Ground truth: CTU-13 Neris (3 malicious IPs)
====================================================================
Malicious IPs: 147.32.84.165, 147.32.84.191, 147.32.84.192

====================================================================
FAST DETECTOR — deduplicated alerts vs ground truth
====================================================================
Raw [FAST ALERT] lines:      5662
Deduplicated alert events:   648
Total events (ml-detector):  17866

TP  (malicious, detected):   646
FP  (benign, false alarm):   2
FN  (malicious, missed):     0
TN  (benign, correct):       17218

Precision:  0.9969
Recall:     1.0000
F1-Score:   0.9985  ← paper metric
FPR:        0.0001
Accuracy:   0.9999

NOTE: FN estimated as 0 — [FAST ALERT] only fires on detected flows. True FN requires per-event IP table. Recall=1.0 is an upper bound, not confirmed.
====================================================================

DETECTED IPs breakdown:
147.32.84.165  →  646 flow(s) detected  [MALICIOUS ✓]

FALSE POSITIVE IPs (sample, max 5):
src=192.168.56.1  dst=224.0.0.251
src=192.168.56.1  dst=192.168.56.255

CSV line for f1_replay_log.csv:
DAYDAY86_neris,,17866,646,2,0,17218,0.9985,0.9969,1.0000,0.0001

(.venv) aironman@MacBook-Pro-de-Alonso argus %

# Experimento 3: bigFlows + CPU/RAM (30 min)

(.venv) aironman@MacBook-Pro-de-Alonso argus % make pipeline-stop && make logs-lab-clean && make pipeline-start && sleep 15

🛑 Stopping all pipeline components...
✅ Pipeline stopped
🧹 Rotating pipeline logs...
✅ Logs rotated to /vagrant/logs/lab/archive/
...
╔════════════════════════════════════════════════════════════╗
║  📊 ML Defender Pipeline Status (via TMUX)                ║
╚════════════════════════════════════════════════════════════╝
✅ etcd-server:   RUNNING
✅ rag-security:  RUNNING
✅ rag-ingester:  RUNNING
✅ ml-detector:   RUNNING
✅ sniffer:       RUNNING
✅ firewall:      RUNNING
╚════════════════════════════════════════════════════════════╝

(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "top -b -n 60 -d 10 > /vagrant/logs/lab/top_bigflows.log &"

(.venv) aironman@MacBook-Pro-de-Alonso argus % make test-replay-big

🧪 Replaying CTU-13 bigFlows.pcap...
Test start: 2026-03-14 12:15:07.978917 ...
Actual: 32623 packets (12499674 bytes) sent in 10.00 seconds
Rated: 1249952.4 Bps, 9.99 Mbps, 3262.26 pps
Actual: 61886 packets (25000292 bytes) sent in 20.00 seconds
Rated: 1249967.2 Bps, 9.99 Mbps, 3094.18 pps
Actual: 87964 packets (37501041 bytes) sent in 30.00 seconds
Rated: 1249979.5 Bps, 9.99 Mbps, 2932.00 pps
Actual: 112482 packets (50002423 bytes) sent in 40.00 seconds
Rated: 1249988.2 Bps, 9.99 Mbps, 2811.88 pps
Actual: 139077 packets (62503278 bytes) sent in 50.00 seconds
Rated: 1249999.1 Bps, 9.99 Mbps, 2781.39 pps
Actual: 171078 packets (75003815 bytes) sent in 60.00 seconds
Rated: 1249998.3 Bps, 9.99 Mbps, 2851.15 pps
Actual: 201974 packets (87504863 bytes) sent in 70.00 seconds
Rated: 1249998.8 Bps, 9.99 Mbps, 2885.17 pps
Actual: 226644 packets (100005853 bytes) sent in 80.00 seconds
Rated: 1249998.8 Bps, 9.99 Mbps, 2832.88 pps
Actual: 251491 packets (112507007 bytes) sent in 90.00 seconds
Rated: 1249998.2 Bps, 9.99 Mbps, 2794.16 pps
Actual: 281457 packets (125007132 bytes) sent in 100.00 seconds
Rated: 1249997.9 Bps, 9.99 Mbps, 2814.40 pps
Actual: 311510 packets (137507592 bytes) sent in 110.00 seconds
Rated: 1249994.8 Bps, 9.99 Mbps, 2831.74 pps
Actual: 336340 packets (150008829 bytes) sent in 120.00 seconds
Rated: 1249996.2 Bps, 9.99 Mbps, 2802.65 pps
Actual: 362757 packets (162508791 bytes) sent in 130.00 seconds
Rated: 1249996.2 Bps, 9.99 Mbps, 2790.27 pps
Actual: 389070 packets (175010159 bytes) sent in 140.00 seconds
Rated: 1249999.9 Bps, 9.99 Mbps, 2778.91 pps
Actual: 415171 packets (187510235 bytes) sent in 150.00 seconds
Rated: 1249999.7 Bps, 9.99 Mbps, 2767.65 pps
Actual: 437370 packets (200010649 bytes) sent in 160.00 seconds
Rated: 1249996.6 Bps, 9.99 Mbps, 2733.40 pps
Actual: 467434 packets (212511211 bytes) sent in 170.00 seconds
Rated: 1249999.9 Bps, 9.99 Mbps, 2749.46 pps
Actual: 493401 packets (225010621 bytes) sent in 180.00 seconds
Rated: 1249995.7 Bps, 9.99 Mbps, 2740.97 pps
Actual: 524772 packets (237512299 bytes) sent in 190.01 seconds
Rated: 1249997.1 Bps, 9.99 Mbps, 2761.80 pps
Actual: 557267 packets (250012751 bytes) sent in 200.01 seconds
Rated: 1249996.8 Bps, 9.99 Mbps, 2786.18 pps
Actual: 591386 packets (262513534 bytes) sent in 210.01 seconds
Rated: 1249999.9 Bps, 9.99 Mbps, 2815.97 pps
Actual: 621439 packets (275012753 bytes) sent in 220.01 seconds
Rated: 1249995.1 Bps, 9.99 Mbps, 2824.58 pps
Actual: 650894 packets (287513675 bytes) sent in 230.01 seconds
Rated: 1249997.9 Bps, 9.99 Mbps, 2829.83 pps
Actual: 678794 packets (300014719 bytes) sent in 240.01 seconds
Rated: 1249999.3 Bps, 9.99 Mbps, 2828.16 pps
Actual: 709331 packets (312515918 bytes) sent in 250.01 seconds
Rated: 1249999.9 Bps, 9.99 Mbps, 2837.17 pps
Actual: 734226 packets (325015760 bytes) sent in 260.01 seconds
Rated: 1249999.3 Bps, 9.99 Mbps, 2823.80 pps
Actual: 756748 packets (337515328 bytes) sent in 270.01 seconds
Rated: 1249997.1 Bps, 9.99 Mbps, 2802.63 pps
Actual: 783620 packets (350016381 bytes) sent in 280.01 seconds
Rated: 1249997.1 Bps, 9.99 Mbps, 2798.50 pps
Test complete: 2026-03-14 12:19:52.313313
Actual: 791615 packets (355417784 bytes) sent in 284.33 seconds
Rated: 1249999.2 Bps, 9.99 Mbps, 2784.09 pps
Flows: 40467 flows, 142.32 fps, 790934 unique flow packets, 436 unique non-flow packets
Statistics for network device: eth1
Successful packets:        791615
Failed packets:            0
Truncated packets:         0
Retried packets (ENOBUFS): 0
Retried packets (EAGAIN):  0
(.venv) aironman@MacBook-Pro-de-Alonso argus % wc -l logs/lab/sniffer.log
230013 logs/lab/sniffer.log
(.venv) aironman@MacBook-Pro-de-Alonso argus % wc -l logs/lab/sniffer.log
230025 logs/lab/sniffer.log
(.venv) aironman@MacBook-Pro-de-Alonso argus % echo "Si, está creciendo el log..."
Si, está creciendo el log...
(.venv) aironman@MacBook-Pro-de-Alonso argus % ls -ltah logs/lab/sniffer.log
-rw-r--r--@ 1 aironman  staff    11M Mar 14 13:28 logs/lab/sniffer.log
(.venv) aironman@MacBook-Pro-de-Alonso argus % ls -ltah logs/lab/sniffer.log
-rw-r--r--@ 1 aironman  staff    11M Mar 14 13:28 logs/lab/sniffer.log
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "cat /vagrant/logs/lab/sniffer.log" > /tmp/sniffer_big.log

Cual es --total-events?
(.venv) aironman@MacBook-Pro-de-Alonso argus % python3 scripts/calculate_f1_neris.py /tmp/sniffer_big.log --total-events XXXX --day "DAY87_big"

(.venv) aironman@MacBook-Pro-de-Alonso argus % wc -l /logs/lab/sniffer.log
wc: /logs/lab/sniffer.log: open: No such file or directory
(.venv) aironman@MacBook-Pro-de-Alonso argus % wc -l logs/lab/sniffer.log
230013 logs/lab/sniffer.log
(.venv) aironman@MacBook-Pro-de-Alonso argus % wc -l logs/lab/sniffer.log
230025 logs/lab/sniffer.log
(.venv) aironman@MacBook-Pro-de-Alonso argus % echo "Si, está creciendo el log..."
Si, está creciendo el log...
(.venv) aironman@MacBook-Pro-de-Alonso argus % ls -ltah /logs/lab/sniffer.log
ls: /logs/lab/sniffer.log: No such file or directory
(.venv) aironman@MacBook-Pro-de-Alonso argus % ls -ltah logs/lab/sniffer.log
-rw-r--r--@ 1 aironman  staff    11M Mar 14 13:28 logs/lab/sniffer.log
(.venv) aironman@MacBook-Pro-de-Alonso argus % ls -ltah logs/lab/sniffer.log
-rw-r--r--@ 1 aironman  staff    11M Mar 14 13:28 logs/lab/sniffer.log
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "cat /vagrant/logs/lab/sniffer.log" > /tmp/sniffer_big.log

(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 12:33:57.778] [ml-detector] [info] 📊 Stats: received=37668, processed=37668, sent=37668, attacks=5, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 12:33:57.778] [ml-detector] [info] 📊 Stats: received=37668, processed=37668, sent=37668, attacks=5, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % sleep 60
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 12:34:57.778] [ml-detector] [info] 📊 Stats: received=37674, processed=37674, sent=37674, attacks=5, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % echo "sigue creciendo, espero un par de horas..."
sigue creciendo, espero un par de horas...
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 12:54:57.880] [ml-detector] [info] 📊 Stats: received=37982, processed=37982, sent=37982, attacks=5, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"
[2026-03-14 12:54:57.880] [ml-detector] [info] 📊 Stats: received=37982, processed=37982, sent=37982, attacks=5, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % ls -ltah logs/lab/top_bigflows.log
ls: logs/lab/top_bigflows.log: No such file or directory
(.venv) aironman@MacBook-Pro-de-Alonso argus % echo "amos, no me digas que no se ha creado el fichero que mide el consumo de ram..."
amos, no me digas que no se ha creado el fichero que mide el consumo de ram...
(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "ls -ltah /vagrant/logs/lab/top_bigflows.log"  
ls: no se puede acceder a '/vagrant/logs/lab/top_bigflows.log': No existe el fichero o el directorio

(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep 'Stats:' /vagrant/logs/lab/ml-detector.log | tail -1"  
[2026-03-14 13:01:57.962] [ml-detector] [info] 📊 Stats: received=38064, processed=38064, sent=38064, attacks=5, errors=(deser:0, feat:0, inf:0)
(.venv) aironman@MacBook-Pro-de-Alonso argus % python3 scripts/calculate_f1_neris.py /tmp/sniffer_big.log --total-events 38064 --day "DAY87_big"


====================================================================
ML DEFENDER - F1 SCORE CALCULATOR
Day: DAY87_big  |  Thresholds:
Ground truth: CTU-13 Neris (3 malicious IPs)
====================================================================
Malicious IPs: 147.32.84.165, 147.32.84.191, 147.32.84.192

====================================================================
FAST DETECTOR — deduplicated alerts vs ground truth
====================================================================
Raw [FAST ALERT] lines:      32400
Deduplicated alert events:   2517
Total events (ml-detector):  38064

TP  (malicious, detected):   0
FP  (benign, false alarm):   2517
FN  (malicious, missed):     0
TN  (benign, correct):       35547

Precision:  0.0000
Recall:     0.0000
F1-Score:   0.0000  ← paper metric
FPR:        0.0661
Accuracy:   0.9339

NOTE: FN estimated as 0 — [FAST ALERT] only fires on detected flows. True FN requires per-event IP table. Recall=1.0 is an upper bound, not confirmed.
====================================================================

DETECTED IPs breakdown:
No malicious IPs detected in alerts.

FALSE POSITIVE IPs (sample, max 5):
src=67.217.94.204  dst=172.16.133.114
src=172.16.133.53  dst=172.16.139.250
src=157.56.242.198  dst=172.16.133.57
src=172.16.133.114  dst=67.217.65.49
src=172.16.133.43  dst=172.16.139.250

CSV line for f1_replay_log.csv:
DAYDAY87_big,,38064,0,2517,0,35547,0.0000,0.0000,0.0000,0.0661

(.venv) aironman@MacBook-Pro-de-Alonso argus % vagrant ssh defender -c "grep -i 'attack\|ATTACK' /vagrant/logs/lab/ml-detector.log | grep -v '147\.32\.84\.' | head -20"

- Level 1 (Attack): ✅
  Level 1: ✅ attack_detector (23 features)
  [2026-03-14 12:12:57.308] [ml-detector] [info] 📦 Loading Level 1 model: level1/level1_attack_detector.onnx
  [2026-03-14 12:12:57.308] [ml-detector] [info]    Name: attack_detector
  [2026-03-14 12:12:57.308] [ml-detector] [info] Loading ONNX model: models/production/level1/level1_attack_detector.onnx
  [2026-03-14 12:12:57.560] [ml-detector] [info]      Level 1: General Attack (ONNX)
  [2026-03-14 12:12:57.562] [ml-detector] [info]    Level 1: General Attack (ONNX)
  [2026-03-14 12:13:57.562] [ml-detector] [info] 📊 Stats: received=0, processed=0, sent=0, attacks=0, errors=(deser:0, feat:0, inf:0)
  [2026-03-14 12:14:57.565] [ml-detector] [info] 📊 Stats: received=1, processed=1, sent=1, attacks=0, errors=(deser:0, feat:0, inf:0)
  [2026-03-14 12:15:57.591] [ml-detector] [info] 📊 Stats: received=772, processed=772, sent=772, attacks=0, errors=(deser:0, feat:0, inf:0)
  [2026-03-14 12:16:57.612] [ml-detector] [info] 📊 Stats: received=2956, processed=2956, sent=2956, attacks=0, errors=(deser:0, feat:0, inf:0)
  [2026-03-14 12:17:57.616] [ml-detector] [info] 📊 Stats: received=5152, processed=5152, sent=5152, attacks=0, errors=(deser:0, feat:0, inf:0)
  [2026-03-14 12:18:57.633] [ml-detector] [info] 📊 Stats: received=7085, processed=7085, sent=7085, attacks=0, errors=(deser:0, feat:0, inf:0)
  [2026-03-14 12:19:36.832] [ml-detector] [info] 🚨 ATTACK: event=18346460942505_1408203495, L1_conf=68.97%, processing=56.42ms
  [2026-03-14 12:19:37.242] [ml-detector] [info] 🚨 ATTACK: event=18346461613105_1408203513, L1_conf=68.97%, processing=54.26ms
  [2026-03-14 12:19:57.659] [ml-detector] [info] 📊 Stats: received=8881, processed=8881, sent=8881, attacks=2, errors=(deser:0, feat:0, inf:0)
  [2026-03-14 12:19:59.015] [ml-detector] [info] 🚨 ATTACK: event=18346792711219_3760030506, L1_conf=60.04%, processing=34.09ms
  [2026-03-14 12:20:19.538] [ml-detector] [info] 🚨 ATTACK: event=18347294214112_3466237660, L1_conf=59.04%, processing=32.68ms
  [2026-03-14 12:20:48.734] [ml-detector] [info] 🚨 ATTACK: event=18348610893760_341342910, L1_conf=52.52%, processing=14.12ms
  [2026-03-14 12:20:57.683] [ml-detector] [info] 📊 Stats: received=11367, processed=11367, sent=11367, attacks=2, errors=(deser:0, feat:0, inf:0)

