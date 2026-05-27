# Estructura del Proyecto C++20 Sniffer

## Directorio del Proyecto
```
argus/
├── config/
│   └── sniffer.json                    # Tu configuración adaptada
├── src/
│   ├── kernel/
│   │   ├── sniffer.bpf.c              # Programa eBPF/XDP
│   │   └── sniffer.bpf.h              # Headers compartidos
│   ├── userspace/
│   │   ├── main.cpp                   # Entry point del sniffer
│   │   ├── config_manager.hpp/.cpp    # Carga y validación JSON
│   │   ├── sniffer_engine.hpp/.cpp    # Motor principal
│   │   ├── ring_consumer.hpp/.cpp     # Consumer del ring buffer
│   │   ├── feature_aggregator.hpp/.cpp # Calculador features user space
│   │   ├── flow_table.hpp/.cpp        # Gestión de flujos
│   │   ├── event_emitter.hpp/.cpp     # Serialización y envío protobuf
│   │   └── auto_tuner.hpp/.cpp        # Auto-tuner (futuro)
│   ├── proto/
│   │   └── network_security_v31.proto # Tu protobuf existente
│   └── services/
│       └── service3/
│           ├── main.cpp               # Service3 receptor
│           ├── zmq_receiver.hpp/.cpp  # Receptor ZeroMQ
│           └── event_processor.hpp/.cpp # Procesador de eventos
├── build/
├── CMakeLists.txt
├── Vagrantfile                        # Ya actualizado a Debian bookworm64
└── README.md
```

## Arquitectura de Componentes

### 1. Sniffer Principal (src/userspace/)
- **Privilegios**: root (para XDP y captura de red)
- **Ubicación**: Vagrant/Debian nativo
- **Red**: Acceso directo a interfaz wifi
- **Salida**: ZeroMQ PUSH a service3

### 2. Service3 (src/services/service3/)
- **Función**: Receptor dedicado de eventos del sniffer
- **Puerto**: Configurable desde sniffer.json
- **Propósito**: Evitar sobrecarga de colas ZeroMQ
- **Salida**: Reenvío a pipeline existente o almacenamiento

## Flujo de Datos

```
[Interfaz WiFi] 
     ↓
[eBPF/XDP Kernel] → Ring Buffer → [C++20 User Space]
                                       ↓
                               [Feature Aggregation]
                                       ↓
                                [Protobuf Serialization]
                                       ↓
                                [ZeroMQ PUSH] → [Service3]
                                                    ↓
                                            [Pipeline Docker]
```

## Configuración JSON - Validación Estricta

### Principios de Validación
1. **JSON es ley**: Si un campo requerido falta, exit(1)
2. **Sin defaults silenciosos**: Todo debe estar explícito en JSON
3. **Validación temprana**: Al arranque, antes de inicializar eBPF
4. **Logging de errores**: Especificar exactamente qué falta/está mal

### Campos Críticos a Validar
```cpp
struct RequiredConfig {
    // Kernel space
    string ebpf_program_path;
    string interface_name;
    int ring_buffer_size;
    
    // Network
    string output_address;
    int output_port;
    string socket_type; // debe ser "PUSH"
    
    // Features
    vector<string> kernel_features; // debe tener exactamente 25
    vector<string> user_features;   // debe tener 58+
    
    // Performance
    int max_throughput_pps;
    int max_latency_us;
    
    // Time windows
    map<string, TimeWindowConfig> windows;
};
```

## Implementation Plan

### Fase 1: Configuración y Validación
```cpp
// config_manager.cpp
class ConfigManager {
public:
    static SnifferConfig load_and_validate(const string& json_path);
    
private:
    static void validate_kernel_config(const json& config);
    static void validate_network_config(const json& config);
    static void validate_feature_lists(const json& config);
    static void fail_fast(const string& error_msg);
};
```

### Fase 2: eBPF/XDP Kernel Program
```c
// sniffer.bpf.c - 25 features baratas en kernel
SEC("xdp")
int sniffer_main(struct xdp_md *ctx) {
    // Parse headers
    // Update flow maps con 25 features
    // Send event a ring buffer
    return XDP_PASS;
}
```

### Fase 3: User Space Engine
```cpp
// sniffer_engine.cpp
class SnifferEngine {
    void initialize_from_config();
    void load_ebpf_program();
    void attach_to_interface();
    void start_ring_consumer();
    void start_feature_aggregator();
    void start_event_emitter();
};
```

### Fase 4: Service3 Receptor
```cpp
// service3/main.cpp
class Service3 {
    void bind_zmq_socket();     // Puerto desde sniffer.json
    void receive_events_loop(); // Receive protobuf events
    void forward_to_pipeline(); // O almacenar localmente
};
```

## Build System (CMakeLists.txt)

```cmake
cmake_minimum_required(VERSION 3.20)
project(cpp_sniffer CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# eBPF compilation
find_program(CLANG clang REQUIRED)
add_custom_command(
        OUTPUT sniffer.bpf.o
        COMMAND ${CLANG} -O2 -target bpf -c ${CMAKE_SOURCE_DIR}/src/kernel/sniffer.bpf.c -o sniffer.bpf.o
        DEPENDS ../sniffer/src/kernel/sniffer.bpf.c
)

# Dependencies
find_package(../protobuf REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBBPF REQUIRED libbpf)
pkg_check_modules(ZMQ REQUIRED libzmq)

# Main sniffer executable
add_executable(sniffer
        ../sniffer/src/userspace/main.cpp
        ../sniffer/src/userspace/config_manager.cpp
        sniffer/src/userspace/sniffer_engine.cpp
        # ... otros archivos
        sniffer.bpf.o
)

target_link_libraries(sniffer
        ${LIBBPF_LIBRARIES}
        ${Protobuf_LIBRARIES}
        ${ZMQ_LIBRARIES}
        jsoncpp
)

# Service3 executable
add_executable(service3
        sniffer/src/services/service3/main_simple_fixed.cpp
        sniffer/src/services/service3/zmq_receiver.cpp
        sniffer/src/services/service3/event_processor.cpp
)
```

## Comandos de Ejecución

### En Vagrant/Debian (como root):
```bash
# Compilar
cd /vagrant/argus
mkdir build && cd build
cmake ..
make -j4

# Ejecutar sniffer (requiere root para XDP)
sudo ./sniffer --config=/vagrant/config/sniffer.json

# En otra terminal, service3 (puede ejecutarse como usuario normal)
./service3 --config=/vagrant/config/sniffer.json
```

## Validación de Red WiFi

### Test de Conectividad
```bash
# Verificar interfaz WiFi disponible
ip link show

# Test de captura básica
sudo tcpdump -i wlan0 -c 10

# Verificar que eBPF puede cargar
sudo bpftool prog list
```

## Next Steps Inmediatos

1. **Crear estructura de directorios**
2. **Implementar ConfigManager con validación estricta**
3. **Programa eBPF básico con las 25 features de kernel**
4. **Consumer de ring buffer en C++20**
5. **Service3 receptor ZeroMQ**
6. **Test end-to-end con tráfico real en WiFi**

## Consideraciones de Seguridad

### Privilegios Root
- Solo el sniffer principal necesita root
- Service3 puede ejecutarse como usuario normal
- Minimizar superficie de ataque manteniendo componentes separados

### Gestión de Errores
- Fail-fast en configuración inválida
- Logging detallado de errores de eBPF
- Rollback automático si falla carga de programa XDP