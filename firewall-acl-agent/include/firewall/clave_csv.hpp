#pragma once
// firewall-acl-agent/include/firewall/clave_csv.hpp — [FW-CSV-CLAVE-B2-D316] DEBT-FW-HMAC-KEY-ALARM-001, commit B2 del
// paso 5 de DEBT-ETCD-HA-TLS-RAFT-001 (decisión G4 de Alonso, DAY316). El firewall pide su clave HMAC del CSV como el
// ml-detector la del bronce: cada hmac_key.check_interval_seconds, en un hilo propio (nunca en el que procesa eventos).
//   - Sin clave: no se escribe CSV (nunca filas sin firma) y se avisa en cada intento: [FW-CSV-SIN-CLAVE], desde cuándo y
//     cuántas filas no se han escrito.
//   - Con clave y sin respuesta del etcd-server: se sigue firmando con la vigente: [FW-CSV-CLAVE-SIN-CONFIRMAR].
//   - Vuelve: [FW-CSV-CLAVE-CONFIRMADA]. Otra clave: [FW-CSV-CLAVE-CAMBIADA] (huella vieja -> nueva). La primera tras un
//     hueco: [FW-CSV-CLAVE-RECUPERADA]. En el log solo la huella (4 primeros bytes del SHA-256 de la clave, como el
//     etcd-server y el ml-detector).
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <ctime>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

namespace mldefender::firewall {

using Clave = std::vector<uint8_t>;

// Huella de una clave: 8 hex (SHA-256, 4 primeros bytes)
std::string huella_clave(const Clave& clave);

class ClaveCsv {
public:
    using Proveedor = std::function<std::optional<Clave>()>;   // nullopt = sin clave o sin respuesta
    using Sumidero = std::function<void(const std::string&)>;  // una línea de log
    using Reloj = std::function<std::time_t()>;

    ClaveCsv(Proveedor proveedor, int intervalo_s, Sumidero log, Reloj reloj = [] { return std::time(nullptr); });
    ~ClaveCsv();
    ClaveCsv(const ClaveCsv&) = delete;
    ClaveCsv& operator=(const ClaveCsv&) = delete;

    // Hilo propio: primera comprobación enseguida (sin hacer esperar al arranque), luego cada intervalo_s.
    void arrancar();
    void parar();

    // Una comprobación (la usa el hilo; pública para los tests)
    void comprobar();

    // La clave vigente (copia); nullopt = no escribir CSV
    std::optional<Clave> clave() const;
    // Una fila que no se escribe por falta de clave
    void fila_sin_clave() { ++filas_sin_clave_; }
    uint64_t filas_sin_clave() const { return filas_sin_clave_.load(); }

private:
    static std::string hora_utc(std::time_t t);

    Proveedor proveedor_;
    int intervalo_s_;
    Sumidero log_;
    Reloj reloj_;

    mutable std::mutex m_;
    std::optional<Clave> clave_;
    std::string huella_;
    bool sin_clave_ = false;      // hueco abierto (nunca hubo clave o se arrancó sin ella)
    std::time_t sin_clave_desde_ = 0;
    uint64_t filas_base_ = 0;
    bool sin_confirmar_ = false;  // hay clave pero el etcd-server no responde
    std::time_t sin_confirmar_desde_ = 0;
    bool primera_ = true;

    std::atomic<uint64_t> filas_sin_clave_{0};
    std::thread hilo_;
    std::atomic<bool> en_marcha_{false};
    std::mutex hm_;
    std::condition_variable cv_;
};

}  // namespace mldefender::firewall
