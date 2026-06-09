// i_graph_sink.hpp — destino del grafo (Cypher). Backend intercambiable tras la interfaz.
// aRGus NDR — DAY 179. Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// El correlation-engine NO calcula features ni veredicto: lee bronce verificado,
// calcula flow_uid (server-side) y materializa :NetworkFlow + :Alert via este sink.
// Backend de hoy: LoggingGraphSink. Backend de manana: Kuzu embebido (misma interfaz).
#pragma once
#include "correlation_engine/correlation_record.hpp"
#include <string_view>

namespace argus::correlation {

class IGraphSink {
public:
    virtual ~IGraphSink() = default;

    // Materializa :NetworkFlow + :Alert para un registro de bronce ya verificado.
    // flow_uid se calcula en el engine (server-side) antes de llamar.
    // Devuelve false ante error de escritura (el loop lo cuenta, no aborta).
    virtual bool write(const CorrelationRecord& record, std::string_view flow_uid) = 0;

    // Volcado/cierre. Backends con buffer lo redefinen; por defecto no-op.
    virtual void flush() {}
};

}  // namespace argus::correlation
