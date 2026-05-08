(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % vagrant ssh client -c "cat /vagrant/logs/lab/tcpreplay-ebpf-100mbps.log"
Warning in send_packets.c:send_packets() line 489:
Unable to send packet: Error with PF_PACKET send() [126]: Message too long (errno = 90)
...
El anterior Warning y el mensaje se repite muchísimas veces.
Test complete: 2026-05-08 05:21:11.326062
Actual: 320524 packets (44200259 bytes) sent in 34.92 seconds
Rated: 1265696.9 Bps, 10.12 Mbps, 9178.36 pps
Flows: 19135 flows, 547.94 fps, 322242 unique flow packets, 906 unique non-flow packets
Statistics for network device: eth1
Successful packets:        320524
Failed packets:            2630
Truncated packets:         0
Retried packets (ENOBUFS): 0
Retried packets (EAGAIN):  0
(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % 

(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % vagrant ssh client -c "cat /vagrant/logs/lab/tcpreplay-ebpf-10mbps.log"

Warning in send_packets.c:send_packets() line 489:
Unable to send packet: Error with PF_PACKET send() [126]: Message too long (errno = 90)
...
Test complete: 2026-05-08 05:19:50.758935
Actual: 320524 packets (44200259 bytes) sent in 39.86 seconds
Rated: 1108723.3 Bps, 8.86 Mbps, 8040.05 pps
Flows: 19135 flows, 479.98 fps, 322242 unique flow packets, 906 unique non-flow packets
Statistics for network device: eth1
Successful packets:        320524
Failed packets:            2630
Truncated packets:         0
Retried packets (ENOBUFS): 0
Retried packets (EAGAIN):  0

(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % vagrant ssh client -c "cat /vagrant/logs/lab/tcpreplay-ebpf-50mbps.log"

Warning in send_packets.c:send_packets() line 489:
Unable to send packet: Error with PF_PACKET send() [126]: Message too long (errno = 90)
...
Test complete: 2026-05-08 05:20:32.124412
Actual: 320524 packets (44200259 bytes) sent in 36.14 seconds
Rated: 1222803.1 Bps, 9.78 Mbps, 8867.31 pps
Flows: 19135 flows, 529.37 fps, 322242 unique flow packets, 906 unique non-flow packets
Statistics for network device: eth1
Successful packets:        320524
Failed packets:            2630
Truncated packets:         0
Retried packets (ENOBUFS): 0
Retried packets (EAGAIN):  0