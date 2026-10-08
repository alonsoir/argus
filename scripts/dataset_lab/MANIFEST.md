# Pcaps de ataque del laboratorio (DDoS, contrato v2)

Los pcaps NO se trackean (`datasets/` está en .gitignore). Se regeneran byte a byte
(semilla 42; verificado DAY288 regenerando a /tmp: sha256 idéntico en los tres) con estos
comandos, ejecutados en el defender:

    python3 /vagrant/scripts/dataset_lab/gen_syn_flood.py 5000 /vagrant/datasets/lab/syn_flood_5k_lab.pcap
    python3 /vagrant/scripts/dataset_lab/gen_reflection.py 10000 123 440 /vagrant/datasets/lab/ntp_reflex_10k_lab.pcap
    python3 /vagrant/scripts/dataset_lab/gen_reflection.py 10000 53 1400 /vagrant/datasets/lab/dns_reflex_10k_lab.pcap

Topología: 192.168.100.50 (client eth1, 08:00:27:07:8c:2f) -> 192.168.100.1 (defender eth2,
08:00:27:6f:63:da). Sin tcprewrite. Reproducir desde el client con `tcpreplay --limit N --pps R`.

| pcap | paquetes | trama | firma | sha256 |
|------|----------|-------|-------|--------|
| syn_flood_5k_lab.pcap | 5000 | 54 B | TCP SYN, sport 49152+i (uno por paquete) -> dport 80 | 41b489e395678bcbac8269967381f359faaf70d3b69ee7fda4b745ce7bf7904d |
| ntp_reflex_10k_lab.pcap | 10000 | 482 B | UDP sport 123 -> dport aleatorio 1024-65535 | 3b2b5f63fce2dbc8ebd71ea1ce20f482c655f38536ca12e2c0b418ac3b3cef5d |
| dns_reflex_10k_lab.pcap | 10000 | 1442 B | UDP sport 53 -> dport aleatorio 1024-65535, sin fragmentar | 0caae6eb418b3676e04c8d69bd428015da61877f5e8364aff43e45799ad5646e |

Limitación (paper): toda la reflexión viene de un único origen (.50); en la realidad llega
de miles de reflectores. No afecta al contrato v2 (source_ip_dispersion fuera del vector).
NTP y DNS comparten semilla y por tanto la secuencia de puertos destino; cada corrida va
en su propio arranque del pipeline.

## DAY289 — contraste benigno de reflexión (respuestas DNS/NTP legítimas hacia .1)

Mismo origen (.50) y topología que el ataque, para que solo cambien tamaño y tasa:

    python3 /vagrant/scripts/dataset_lab/gen_benign_dns_ntp.py small 5000 /vagrant/datasets/lab/benign_dns_ntp_small_5k_lab.pcap
    python3 /vagrant/scripts/dataset_lab/gen_benign_dns_ntp.py large 5000 /vagrant/datasets/lab/benign_dns_large_5k_lab.pcap

| pcap | paquetes | trama | firma | sha256 |
|------|----------|-------|-------|--------|
| benign_dns_ntp_small_5k_lab.pcap | 5000 | 80–250 B (media 151,9) | 80 % UDP sport 53 + 20 % sport 123 (90 B) -> dport aleatorio | dbf6adebf1d4e0d4c1750a94815b75a5086ad39db5dc75557eae21a9bf79b365 |
| benign_dns_large_5k_lab.pcap | 5000 | 1200–1442 B (media 1320,7) | UDP sport 53 (DNSSEC/TXT legítimos) -> dport aleatorio | be45b9e75743a974b708c026dbca2bec0361f71969d2b62d246976bda5f861f3 |

Regenerados a /tmp DAY289: sha256 idéntico en los dos.

## DAY291 — línea base caliente desde .51 (derivado, regenerable)

Derivado de `benign_dns_ntp_small_5k_lab.pcap` reescribiendo SOLO la IP de origen (MACs intactas),
en el client, para etiquetar la línea base por construcción (.51) frente al ataque (.50):

    tcprewrite --infile=/vagrant/datasets/lab/benign_dns_ntp_small_5k_lab.pcap --outfile=/vagrant/datasets/lab/benign_dns_ntp_small_5k_lab_src51.pcap --srcipmap=192.168.100.50/32:192.168.100.51/32 --fixcsum

| pcap | paquetes | origen | sha256 |
|------|----------|--------|--------|
| benign_dns_ntp_small_5k_lab_src51.pcap | 5000 | 192.168.100.51 | 1ae61b36009e7cac694389cb5fd8b2d7376087bb2444e9ba9bc265310e61dd56 |

Requiere el alias `sudo ip addr add 192.168.100.51/24 dev eth1` en el client (no persiste al reiniciar la VM).
La línea base TCP desde .51 es tráfico vivo: `scripts/d281_tcp_upload.py HOST PORT KB_S SEG 192.168.100.51`.
