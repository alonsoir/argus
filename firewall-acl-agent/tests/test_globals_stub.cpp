// test_globals_stub.cpp — stubs para g_logger y g_system_state en tests
#include <memory>
#include <iostream>
#include "firewall_observability_logger.hpp"
#include "crash_diagnostics.hpp"

namespace mldefender::firewall::observability {
    std::unique_ptr<ObservabilityLogger> g_logger = nullptr;
}
namespace mldefender::firewall::diagnostics {
    std::unique_ptr<SystemState> g_system_state = nullptr;
}
