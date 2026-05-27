Lo que el modelo actual probablemente captura de WannaCry:
unique_dst_ports_count + connection_rate + syn_flag_count son la señal más fuerte — el scanning masivo a puerto 445 genera exactamente eso. rst_ratio (cuando esté implementado) sería la señal más discriminante: WannaCry recibe RST de casi todo host que no sea Windows XP/7 sin parchear.
Lo que no captura:
El killswitch DNS es invisible en capa 3/4 sin DPI — solo verías un paquete UDP al puerto 53, indistinguible de cualquier query legítima. Esto hay que documentarlo como limitación honesta en el paper.
Mi voto sobre las 4 decisiones:

rst_ratio → P1 absoluto. Es la firma más limpia de ransomware SMB-propagating.
Ventana 10s → suficiente para WannaCry (escanea rápido), insuficiente para NotPetya (lateral movement lento puede durar minutos).
dns_query_count sin DPI → valor limitado, pero el volumen de queries a puerto 53 sí aporta señal de killswitch lookup.
Killswitch DNS → no detectable con la arquitectura actual. Limitación honesta.