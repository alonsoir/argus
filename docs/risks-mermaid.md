flowchart TD
NIC[Network NIC]
Kernel[Kernel Space<br/>eBPF/XDP<br/>Features: IP, Ports, Flags, Packet Stats]
RingBuffer[Ring Buffer]
UserSpace[User Space<br/>C++ Feature Aggregation<br/>Threads]
ZeroMQ[ZeroMQ Pipeline]
NextStage[Next Stage: GeoIP / ML]

    NIC --> Kernel
    Kernel --> RingBuffer
    RingBuffer --> UserSpace
    UserSpace --> ZeroMQ
    ZeroMQ --> NextStage

    %% Riesgos destacados
    Kernel -.->|Riesgo 1: Dependencia eBPF| Kernel
    Kernel -.->|Riesgo 2: Kernel >=6.12| Kernel
    Kernel -.->|Riesgo 5: Hardware desconocido| Kernel
    UserSpace -.->|Riesgo 4: ZeroMQ saturado| UserSpace
    UserSpace -.->|Riesgo 6: Auto-tuner prematuro| UserSpace
    NIC -.->|Riesgo 3: Multiplicidad de interfaces| NIC
