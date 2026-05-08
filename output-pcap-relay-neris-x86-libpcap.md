(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % vagrant ssh client -c "cat /vagrant/logs/lab/tcpreplay-libpcap-10mbps.log"

Warning in send_packets.c:send_packets() line 489:
Unable to send packet: Error with PF_PACKET send() [126]: Message too long (errno = 90)
...
Test complete: 2026-05-08 05:38:18.008934
Actual: 320524 packets (44200259 bytes) sent in 35.36 seconds
Rated: 1249999.7 Bps, 9.99 Mbps, 9064.53 pps
Flows: 19135 flows, 541.14 fps, 322242 unique flow packets, 906 unique non-flow packets
Statistics for network device: eth1
Successful packets:        320524
Failed packets:            2630
Truncated packets:         0
Retried packets (ENOBUFS): 0
Retried packets (EAGAIN):  0
exit=0

(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % vagrant ssh client -c "cat /vagrant/logs/lab/tcpreplay-libpcap-50mbps.log"

Warning in send_packets.c:send_packets() line 489:
Unable to send packet: Error with PF_PACKET send() [126]: Message too long (errno = 90)
...
Test complete: 2026-05-08 05:38:38.916796
Actual: 320524 packets (44200259 bytes) sent in 18.19 seconds
Rated: 2429071.8 Bps, 19.43 Mbps, 17614.73 pps
Flows: 19135 flows, 1051.58 fps, 322242 unique flow packets, 906 unique non-flow packets
Statistics for network device: eth1
Successful packets:        320524
Failed packets:            2630
Truncated packets:         0
Retried packets (ENOBUFS): 0
Retried packets (EAGAIN):  0
exit=0

(.venv) aironman@MacBook-Pro-de-Alonso test-zeromq-docker % vagrant ssh client -c "cat /vagrant/logs/lab/tcpreplay-libpcap-100mbps.log"

Warning in send_packets.c:send_packets() line 489:
Unable to send packet: Error with PF_PACKET send() [126]: Message too long (errno = 90)
...
Test complete: 2026-05-08 05:39:00.497824
Actual: 320524 packets (44200259 bytes) sent in 18.78 seconds
Rated: 2353440.1 Bps, 18.82 Mbps, 17066.28 pps
Flows: 19135 flows, 1018.84 fps, 322242 unique flow packets, 906 unique non-flow packets
Statistics for network device: eth1
Successful packets:        320524
Failed packets:            2630
Truncated packets:         0
Retried packets (ENOBUFS): 0
Retried packets (EAGAIN):  0
exit=0