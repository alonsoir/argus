// i_graph_sink.hpp — destino del grafo (Cypher). Backend intercambiable tras la interfaz.
// aRGus NDR — DAY 179 / contrato flush()->estado DAY 184. Authors: Alonso + Claude.
#pragma once
#include "correlation_engine/correlation_record.hpp"

#include <cstdint>
#include <string_view>

namespace argus::correlation {

// Resultado de flush(): exterioriza la durabilidad que el 'void' antiguo OCULTABA.
// POD trivial (sin asignaciones): el mensaje de error (Kuzu) lo loguea el propio sink;
// aqui SOLO lo maquina-accionable, para que el caller decida politica.
//
//   ok == true  -> batch committeado DURABLEMENTE; buffer vaciado.
//                  rows_flushed = filas de ESTE flush; rows_pending = 0.
//   ok == false -> ROLLBACK (o fallo pre-commit): nada durable en este flush.
//                  buffer RETENIDO (reintento, nunca drop silencioso).
//                  rows_pending = filas que SIGUEN en buffer (>0 => riesgo de perdida).
//
// [[nodiscard]] en el TIPO (no en cada flush): el fallo de durabilidad NO se puede
// descartar en silencio desde NINGUN sink, presente o futuro. Enforcement estructural,
// igual que H-1 se cierra por param tipado y no por recordar llamar a esc().
struct [[nodiscard]] FlushResult {
    bool     ok           = false;
    uint64_t rows_flushed = 0;  // committeadas en ESTE flush (0 si rollback)
    uint64_t rows_pending = 0;  // aun en buffer tras este flush (>0 => no durable)

    // 'if (!sink->flush())' sigue siendo legal y NO descarta (se USA el valor).
    // explicit => no se cuela en aritmetica ni comparaciones implicitas.
    explicit operator bool() const noexcept { return ok; }
};

class IGraphSink {
public:
    virtual ~IGraphSink() = default;

    // Materializa :NetworkFlow + :Alert para un registro de bronce ya verificado.
    // flow_uid se calcula en el engine (server-side) antes de llamar.
    // Devuelve false ante error de escritura (el loop lo cuenta, no aborta).
    virtual bool write(const CorrelationRecord& record, std::string_view flow_uid) = 0;

    // Volcado/cierre. Backends con buffer redefinen y reportan durabilidad real.
    // Por defecto (sin buffer): no hay nada que volcar -> exito trivial.
    virtual FlushResult flush() { return FlushResult{true, 0, 0}; }
};

}  // namespace argus::correlation