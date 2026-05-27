@startuml
!define RECTANGLE class
skinparam rectangle {
BackgroundColor LightBlue
BorderColor Black
}

RECTANGLE NIC {
Network NIC
}

RECTANGLE Kernel {
Kernel Space
eBPF/XDP
Features:
- IP / Ports
- Flags
- Packet Stats
  }

RECTANGLE RingBuffer {
Ring Buffer
}

RECTANGLE UserSpace {
User Space
C++ Feature Aggregation
Threads
}

RECTANGLE ZeroMQ {
ZeroMQ Pipeline
}

RECTANGLE NextStage {
Next Stage
GeoIP / ML
}

' Flow
NIC --> Kernel
Kernel --> RingBuffer
RingBuffer --> UserSpace
UserSpace --> ZeroMQ
ZeroMQ --> NextStage

' Riesgos
Kernel -.- Kernel : Riesgo 1: eBPF dependiente
Kernel -.- Kernel : Riesgo 2: Kernel >=6.12
Kernel -.- Kernel : Riesgo 5: Hardware desconocido
UserSpace -.- UserSpace : Riesgo 4: ZeroMQ saturado
UserSpace -.- UserSpace : Riesgo 6: Auto-tuner prematuro
NIC -.- NIC : Riesgo 3: Multiplicidad interfaces
@enduml
