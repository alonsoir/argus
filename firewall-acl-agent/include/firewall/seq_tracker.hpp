#pragma once
// [TIMEBASE-SEQ-D297] D15 A1 / D17: contabilidad de la secuencia por productor (TimeContext.producer_seq).
// Clave = (originating_node_id, boot_id, producer_start_mono_ns): un reinicio del productor es otra clave.
// Contadores ACUMULADOS desde el arranque del firewall, no por periodo: un hueco puede rellenarse en un periodo
// posterior y un contador por periodo saldria negativo. Invariante: seq_hueco >= 0 por productor; un relleno que no
// encuentra hueco que descontar se cuenta en seq_invariante (fallo del propio contador; no deberia pasar nunca).
//   seq_dup        el mismo seq otra vez, dentro de la ventana
//   seq_hueco      secuencias saltadas y aun no recibidas (neto de rellenos tardios)
//   seq_desorden   seq menor que el maximo, dentro de la ventana y no visto antes (relleno tardio)
//   seq_viejo      seq anterior a maximo - ventana: no se puede distinguir duplicado de retraso
//   seq_cero       producer_seq = 0 (productor sin contrato v1)
// La primera secuencia de cada clave es su inicio: las anteriores NO son hueco (el firewall pudo arrancar despues).
// producer_seq garantiza unicidad y deteccion de perdidas; NO garantiza orden de entrega (medido DAY297: 1 desorden
// en 15262 eventos, sin huecos ni duplicados).
// [TIMEBASE-SEQ-DET-D297] observe() devuelve que ha pasado (SeqObservacion) y, para desorden/dup/viejo, el maximo
// previo de la clave con su mono_ns y su etiqueta (event_kind), para detallarlo en el log sin protobuf aqui.
// Cabecera pura (sin protobuf ni E/S), probada en tests/unit/test_seq_tracker.cpp. Solo hilo receptor.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <map>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace mldefender::firewall {

enum class SeqResultado { kInicio = 0, kOrden, kHueco, kDesorden, kDup, kViejo, kCero };

inline const char* seq_resultado_nombre(SeqResultado r) {
    switch (r) {
        case SeqResultado::kInicio:
            return "inicio";
        case SeqResultado::kOrden:
            return "orden";
        case SeqResultado::kHueco:
            return "hueco";
        case SeqResultado::kDesorden:
            return "desorden";
        case SeqResultado::kDup:
            return "dup";
        case SeqResultado::kViejo:
            return "viejo";
        case SeqResultado::kCero:
            return "cero";
    }
    return "desconocido";
}

struct SeqObservacion {
    SeqResultado r = SeqResultado::kOrden;
    uint64_t max_previo = 0;    // maximo de la clave ANTES de este evento
    uint64_t mono_max = 0;      // mono_ns del evento que fijo ese maximo
    uint32_t etiqueta_max = 0;  // etiqueta (event_kind) del evento que fijo ese maximo
};

class SeqTracker {
public:
    static constexpr uint64_t kVentanaMin = 64;  // = minimo del rango de ddos_shadow.seq_ventana en el JSON

    explicit SeqTracker(uint64_t ventana) : w_(ventana < kVentanaMin ? kVentanaMin : ventana) {}

    SeqObservacion observe(const std::string& clave, uint64_t seq, uint64_t mono_ns = 0, uint32_t etiqueta = 0) {
        SeqObservacion o;
        if (seq == 0) {
            ++cero_;
            o.r = SeqResultado::kCero;
            return o;
        }
        ++recibidos_;
        auto it = st_.find(clave);
        if (it == st_.end()) {
            Estado e;
            e.bits.assign(static_cast<std::size_t>(w_), false);
            e.max = seq;
            e.mono_max = mono_ns;
            e.etiqueta_max = etiqueta;
            e.bits[slot(seq)] = true;
            st_.emplace(clave, std::move(e));
            o.r = SeqResultado::kInicio;
            return o;
        }
        Estado& e = it->second;
        o.max_previo = e.max;
        o.mono_max = e.mono_max;
        o.etiqueta_max = e.etiqueta_max;
        if (seq > e.max) {
            const uint64_t salto = seq - e.max;
            if (salto >= w_) {
                std::fill(e.bits.begin(), e.bits.end(), false);
            } else {
                for (uint64_t s = e.max + 1; s < seq; ++s) e.bits[slot(s)] = false;
            }
            e.hueco += salto - 1;
            hueco_ += salto - 1;
            e.max = seq;
            e.mono_max = mono_ns;
            e.etiqueta_max = etiqueta;
            e.bits[slot(seq)] = true;
            o.r = salto > 1 ? SeqResultado::kHueco : SeqResultado::kOrden;
            return o;
        }
        if (e.max - seq >= w_) {
            ++viejo_;
            o.r = SeqResultado::kViejo;
            return o;
        }
        if (e.bits[slot(seq)]) {
            ++dup_;
            o.r = SeqResultado::kDup;
            return o;
        }
        e.bits[slot(seq)] = true;
        ++desorden_;
        if (e.hueco > 0) {
            --e.hueco;
            --hueco_;
        } else {
            ++invariante_;
        }
        o.r = SeqResultado::kDesorden;
        return o;
    }

    uint64_t claves() const { return static_cast<uint64_t>(st_.size()); }
    uint64_t recibidos() const { return recibidos_; }
    uint64_t dup() const { return dup_; }
    uint64_t hueco() const { return hueco_; }
    uint64_t desorden() const { return desorden_; }
    uint64_t viejo() const { return viejo_; }
    uint64_t cero() const { return cero_; }
    uint64_t invariante() const { return invariante_; }
    uint64_t ventana() const { return w_; }

    std::string resumen() const {
        std::ostringstream o;
        o << "seq_claves=" << st_.size() << " seq_recibidos=" << recibidos_ << " seq_dup=" << dup_
          << " seq_hueco=" << hueco_ << " seq_desorden=" << desorden_ << " seq_viejo=" << viejo_
          << " seq_cero=" << cero_ << " seq_invariante=" << invariante_ << " seq_ventana=" << w_;
        return o.str();
    }

private:
    struct Estado {
        uint64_t max = 0;
        uint64_t hueco = 0;
        uint64_t mono_max = 0;
        uint32_t etiqueta_max = 0;
        std::vector<bool> bits;
    };
    std::size_t slot(uint64_t s) const { return static_cast<std::size_t>(s % w_); }

    uint64_t w_;
    std::map<std::string, Estado> st_;
    uint64_t recibidos_ = 0;
    uint64_t dup_ = 0;
    uint64_t hueco_ = 0;
    uint64_t desorden_ = 0;
    uint64_t viejo_ = 0;
    uint64_t cero_ = 0;
    uint64_t invariante_ = 0;
};

}  // namespace mldefender::firewall
