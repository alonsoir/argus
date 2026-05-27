#pragma once
// ============================================================================
// etcd_registrar.h — IEtcdRegistrar  (ADR-045, DAY 154)
// ============================================================================
// Extrae la responsabilidad de registro etcd de VaultClient.
//
// Implementación canónica: StubEtcdRegistrar (stub — DAY 154)
// Implementación futura:   HttpEtcdRegistrar (DEBT-AUTONOMY-ZMQ-EVENTS-001)
//
// Referencia: ADR-044, ADR-045
// ============================================================================
#include "vault_types.h"
#include <string>

namespace ml_defender {

class IEtcdRegistrar {
public:
    virtual ~IEtcdRegistrar() = default;
    virtual bool register_status(const CryptoMaterial& material,
                                  const std::string&    component_name,
                                  bool started_with_cache = false) = 0;
    virtual void start_keepalive() = 0;
    virtual void stop_keepalive()  = 0;
};

// Stub — logs a stderr, sin conexión real a etcd
// Implementación real: DEBT-AUTONOMY-ZMQ-EVENTS-001
class StubEtcdRegistrar : public IEtcdRegistrar {
public:
    bool register_status(const CryptoMaterial& material,
                          const std::string&    component_name,
                          bool started_with_cache = false) override;
    void start_keepalive() override;
    void stop_keepalive()  override;
private:
    bool keepalive_running_{false};
};

} // namespace ml_defender
