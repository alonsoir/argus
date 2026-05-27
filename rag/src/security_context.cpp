// /vagrant/rag/src/security_context.cpp
#include "rag/security_context.hpp"

namespace Rag {

    // Implementación mínima del constructor
    SecurityContext::SecurityContext() :
        user_id("anonymous"),
        session_id("default"),
        environment("production"),
        privilege_level(1),
        source_ip("127.0.0.1")
    {}

} // namespace Rag