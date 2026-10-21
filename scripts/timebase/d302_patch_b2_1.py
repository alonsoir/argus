#!/usr/bin/env python3
# DAY302 tanda b2-1 [DDOS-MITIGACION-B2-D302] + [DRYRUN-ADD-BATCH-D302].
# API por episodio en BatchProcessor (bloquear/renovar, escalon_vigente, barrera de protegidos en dos puertas,
# latido flush_si_toca), dry_run de add_batch sin kernel ni fichero temporal, test H6 con fallo provocado y
# tests nuevos. Atomico: comprueba todas las anclas (unicas) antes de escribir nada. Uso: --check | --apply
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "firewall-acl-agent"
MARCA = "[DDOS-MITIGACION-B2-D302]"
MARCA_DRY = "[DRYRUN-ADD-BATCH-D302]"

P_WRAP = FW / "src/core/ipset_wrapper.cpp"
P_HPP = FW / "include/firewall/batch_processor.hpp"
P_CPP = FW / "src/core/batch_processor.cpp"
P_TREC = FW / "tests/unit/test_batch_processor_recidivism.cpp"
P_CMAKE = FW / "CMakeLists.txt"
P_TNEW = FW / "tests/unit/test_batch_processor_episodio.cpp"

# ---------------------------------------------------------------- ipset_wrapper.cpp
W1_OLD = r'''    if (!set_exists_unlocked(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::SET_NOT_FOUND,
            "Set '" + set_name + "' does not exist"
        });
    }

    // Validate and build restore input
'''
W1_NEW = r'''    // [DRYRUN-ADD-BATCH-D302] en dry_run no se consulta el kernel: el set no se crea en dry_run, y antes
    // esto hacia fallar TODO flush en dry_run (SET_NOT_FOUND) aunque la validacion fuera correcta.
    if (!m_dry_run && !set_exists_unlocked(set_name)) {
        return IPSetResult<void>(IPSetError{
            IPSetErrorCode::SET_NOT_FOUND,
            "Set '" + set_name + "' does not exist"
        });
    }

    // Validate and build restore input
'''
W2_OLD = r'''            "Some comments rejected (CWE-93 ipset restore newline/quote injection)",
            failed_comments
        });
    }
'''
W2_NEW = W2_OLD + r'''
    // [DRYRUN-ADD-BATCH-D302] dry_run: validacion ya hecha (set, IPs, comentarios, timeout). No se escribe el
    // fichero temporal (/run/argus/irp puede no existir o no ser escribible) ni se toca el kernel: se imprimen
    // las ordenes y se devuelve exito. Limite de detalle de log (no de comportamiento).
    if (m_dry_run) {
        constexpr size_t kDryRunDetalleMax = 20;
        std::cout << "[DRY-RUN] Would execute: " << kIpsetBin << " restore -exist (" << entries.size()
                  << " entradas, set " << set_name << ")" << std::endl;
        std::istringstream ordenes(restore_input.str());
        std::string linea;
        size_t n = 0;
        while (std::getline(ordenes, linea)) {
            if (n++ < kDryRunDetalleMax) {
                std::cout << "[DRY-RUN]   " << linea << std::endl;
            }
        }
        if (n > kDryRunDetalleMax) {
            std::cout << "[DRY-RUN]   ... (+" << (n - kDryRunDetalleMax) << " ordenes)" << std::endl;
        }
        return IPSetResult<void>();
    }
'''

# ---------------------------------------------------------------- batch_processor.hpp
H_INCLUDE = '#include "firewall/ddos_protegidos.hpp"  // [DDOS-MITIGACION-B2-D302] barrera de protegidos\n'

H1_OLD = "class BatchProcessor {\npublic:\n"
H1_NEW = r'''/// [DDOS-MITIGACION-B2-D302] Resultado de encolar un origen de ddos_v2 por episodio
/// (BLOQUEAR = un strike; RENOVAR = escalon vigente sin strike).
struct ResultadoEpisodio {
    enum class Estado : uint8_t { ENCOLADO = 0, PROTEGIDO = 1, IP_INVALIDA = 2 };
    Estado estado = Estado::ENCOLADO;
    std::optional<uint32_t> timeout_sec;  ///< nullopt = timeout por defecto del set (reincidencia deshabilitada)
    uint32_t strikes = 0;                 ///< strikes del origen tras la operacion
};

''' + H1_OLD

H2_OLD = "    std::optional<uint32_t> compute_penalty_timeout(const std::string& ip);\n"
H2_NEW = H2_OLD + r'''
    /// [DDOS-MITIGACION-B2-D302] Escalon vigente de la IP SIN sumar strike: sin estado (o con la calma
    /// cumplida) = escalon 0; nullopt si la reincidencia esta deshabilitada. Misma formula que
    /// compute_penalty_timeout. Requiere mutex_ tomado (encolar_episodio; tests sin concurrencia).
    std::optional<uint32_t> escalon_vigente(const std::string& ip) const;
    /// [DDOS-MITIGACION-B2-D302] BLOQUEAR del episodio: UN strike (compute_penalty_timeout) y a la cola con
    /// ese timeout. Barrera: IP invalida o protegida no entra (sin strike). Toma mutex_.
    ResultadoEpisodio bloquear_episodio(const std::string& ip);
    /// [DDOS-MITIGACION-B2-D302] RENOVAR: escalon vigente SIN strike; actualiza last_seen (decision de Alonso
    /// DAY302: el pipeline ha visto actuar a la IP). Misma barrera. Toma mutex_.
    ResultadoEpisodio renovar_episodio(const std::string& ip);
    /// [DDOS-MITIGACION-B2-D302] Rangos que NUNCA entran en la blacklist (vacio = sin barrera). Toma mutex_.
    void set_rangos_protegidos(const RangosProtegidos& rangos);
    /// [DDOS-MITIGACION-B2-D302] Rechazos de la barrera (entrada + flush) desde el arranque. Toma mutex_.
    uint64_t rechazos_protegidos() const;
    /// [DDOS-MITIGACION-B2-D302] Latido: flush si toca por tamano o por tiempo. Devuelve IPs enviadas.
    size_t flush_si_toca();
'''

H3_OLD = "    std::unordered_map<std::string, std::optional<uint32_t>> pending_penalty_;\n"
H3_NEW = H3_OLD + r'''    RangosProtegidos rangos_protegidos_;     ///< [DDOS-MITIGACION-B2-D302] barrera; guardado por mutex_
    uint64_t rechazos_protegidos_{0};        ///< [DDOS-MITIGACION-B2-D302] guardado por mutex_
    /// [DDOS-MITIGACION-B2-D302] comun a bloquear_episodio / renovar_episodio
    ResultadoEpisodio encolar_episodio(const std::string& ip, bool nuevo_strike);
'''

# ---------------------------------------------------------------- batch_processor.cpp
C1_OLD = r'''    for (const auto& ip : pending_ips_) {
        // RECIDIVISM-D276: timeout variable por reincidencia en vez del fijo del set.
'''
C1_NEW = r'''    for (const auto& ip : pending_ips_) {
        if (rangos_protegidos_.categoria_de(ip) != ::mldefender::firewall::CategoriaProtegida::NINGUNA) {
            // [DDOS-MITIGACION-B2-D302] 2.a puerta de la barrera: NINGUN camino mete un protegido en el ipset
            ++rechazos_protegidos_;
            FIREWALL_LOG_ERROR("[DDOS-MITIGACION] origen protegido en la cola de bloqueo: NO entra en el ipset",
                "ip", ip);
            continue;
        }
        // RECIDIVISM-D276: timeout variable por reincidencia en vez del fijo del set.
'''

C2_OLD = r'''    std::lock_guard<std::mutex> lock(mutex_);
    recidivism_config_ = std::move(c);
}
'''
C2_NEW = C2_OLD + r'''
//===----------------------------------------------------------------------===//
// [DDOS-MITIGACION-B2-D302] API por episodio de ddos_v2 (DAY302, tanda b2-1)
//===----------------------------------------------------------------------===//

std::optional<uint32_t> BatchProcessor::escalon_vigente(const std::string& ip) const {
    if (!recidivism_config_.enabled) {
        return std::nullopt;
    }
    uint32_t strikes = 0;
    if (auto it = strike_states_.find(ip); it != strike_states_.end()) {
        strikes = it->second.strikes;
        if (strikes > 0 &&
            (std::chrono::steady_clock::now() - it->second.last_seen) > recidivism_config_.quiet_period_reset) {
            strikes = 0;
        }
    }
    if (recidivism_config_.max_penalty_after_strikes == 0 ||
        (strikes > 0 && strikes >= recidivism_config_.max_penalty_after_strikes)) {
        return recidivism_config_.max_penalty_sec;
    }
    const auto& esc = recidivism_config_.strike_durations_sec;
    if (esc.empty()) {
        return recidivism_config_.max_penalty_sec;
    }
    const size_t idx = (strikes == 0) ? 0 : std::min<size_t>(strikes - 1, esc.size() - 1);
    return std::min(esc[idx], recidivism_config_.max_penalty_sec);
}

ResultadoEpisodio BatchProcessor::encolar_episodio(const std::string& ip, bool nuevo_strike) {
    ResultadoEpisodio r;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        bool v6 = false;
        std::array<uint8_t, 16> b{};
        if (!::mldefender::firewall::detalle_protegidos::a_bytes(ip, v6, b)) {
            r.estado = ResultadoEpisodio::Estado::IP_INVALIDA;
            return r;
        }
        if (rangos_protegidos_.categoria_de(ip) != ::mldefender::firewall::CategoriaProtegida::NINGUNA) {
            ++rechazos_protegidos_;
            r.estado = ResultadoEpisodio::Estado::PROTEGIDO;
            return r;
        }
        if (nuevo_strike) {
            r.timeout_sec = compute_penalty_timeout(ip);
        } else {
            auto it = strike_states_.find(ip);
            if (recidivism_config_.enabled && it != strike_states_.end()) {
                const auto now = std::chrono::steady_clock::now();
                if (it->second.strikes > 0 && (now - it->second.last_seen) > recidivism_config_.quiet_period_reset) {
                    it->second.strikes = 0;  // misma regla de calma que compute_penalty_timeout
                }
                it->second.last_seen = now;  // decision de Alonso DAY302: RENOVAR = el pipeline la ha visto actuar
            }
            r.timeout_sec = escalon_vigente(ip);
        }
        if (auto it = strike_states_.find(ip); it != strike_states_.end()) {
            r.strikes = it->second.strikes;
        }
        if (!pending_ips_.insert(ip).second) {
            metrics_.ips_deduplicated.fetch_add(1, std::memory_order_relaxed);
        }
        auto pp = pending_penalty_.find(ip);
        if (pp == pending_penalty_.end()) {
            pending_penalty_.emplace(ip, r.timeout_sec);
        } else if (pp->second && r.timeout_sec && *r.timeout_sec > *pp->second) {
            pp->second = r.timeout_sec;  // nunca se acorta un castigo ya encolado
        }
        metrics_.pending_ips_current.store(pending_ips_.size(), std::memory_order_relaxed);
        check_backpressure();
    }
    if (should_flush()) {
        flush();
    }
    return r;
}

ResultadoEpisodio BatchProcessor::bloquear_episodio(const std::string& ip) {
    return encolar_episodio(ip, true);
}

ResultadoEpisodio BatchProcessor::renovar_episodio(const std::string& ip) {
    return encolar_episodio(ip, false);
}

void BatchProcessor::set_rangos_protegidos(const RangosProtegidos& rangos) {
    std::lock_guard<std::mutex> lock(mutex_);
    rangos_protegidos_ = rangos;
}

uint64_t BatchProcessor::rechazos_protegidos() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return rechazos_protegidos_;
}

size_t BatchProcessor::flush_si_toca() {
    if (!should_flush()) {
        return 0;
    }
    return flush();
}
'''

# ---------------------------------------------------------------- test H6
T1_OLD = r'''// DAY277-H6: reintentos de un flush fallido NO suman strikes.
// En dry_run el set no existe -> add_batch devuelve SET_NOT_FOUND (medido en
// ipset_wrapper.cpp: set_exists_unlocked va antes del dry_run) -> flush falla
// y la IP sigue pendiente. Con el bug: 5 flushes = 5 strikes -> siguiente = 3600.
'''
T1_NEW = r'''// DAY277-H6: reintentos de un flush fallido NO suman strikes.
// [DRYRUN-ADD-BATCH-D302] el fallo ya no es accidental (antes: SET_NOT_FOUND porque set_exists_unlocked
// iba antes del dry_run). Ahora se PROVOCA: una IP mal formada en el lote -> INVALID_IP_FORMAT (validacion,
// tambien en dry_run) -> flush falla y el lote sigue pendiente. Con el bug: 5 flushes = 5 strikes -> 3600.
'''
T2_OLD = r'''    processor_->add_ip("198.51.100.77");
    for (int i = 0; i < 5; ++i) {
'''
T2_NEW = r'''    processor_->add_ip("198.51.100.77");
    processor_->add_ip("no-es-una-ip");  // [DRYRUN-ADD-BATCH-D302] fallo provocado (DEBT-FW-BATCH-INVALID-IP-POISON-001)
    for (int i = 0; i < 5; ++i) {
'''
T3_OLD = r'''    ASSERT_EQ(processor_->get_pending_count(), 1u)
        << "el flush no fallo: el test no reproduce el reintento";
'''
T3_NEW = r'''    ASSERT_EQ(processor_->get_pending_count(), 2u)
        << "el flush no fallo: el test no reproduce el reintento";
'''

# ---------------------------------------------------------------- CMake
K1_OLD = "            tests/unit/test_batch_processor_recidivism.cpp   # ← RECIDIVISM-D276\n"
K1_NEW = K1_OLD + "            tests/unit/test_batch_processor_episodio.cpp     # ← [DDOS-MITIGACION-B2-D302]\n"

# ---------------------------------------------------------------- test nuevo
TNEW = r'''// [DDOS-MITIGACION-B2-D302] DAY302 tanda b2-1: API por episodio de BatchProcessor.
// Todo en dry_run (sin root ni kernel). Un episodio = un strike; RENOVAR = escalon vigente sin strike y
// refresca last_seen; barrera de protegidos a la entrada y en el flush; latido flush_si_toca.
#include <gtest/gtest.h>
#include <chrono>
#include <memory>
#include <sstream>
#include <thread>
#include "firewall/batch_processor.hpp"
#include "firewall/ipset_wrapper.hpp"
#include "firewall/ddos_protegidos.hpp"

using namespace mldefender::firewall;
using Estado = ResultadoEpisodio::Estado;

namespace {
RecidivismConfig escalera_prueba() {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300, 3600};
    cfg.max_penalty_after_strikes = 10;
    cfg.quiet_period_reset = std::chrono::hours(999);
    return cfg;
}

RangosProtegidos intranet_lab() {
    std::ostringstream log;
    return construir_rangos_protegidos({}, {"192.168.100.0/24"}, {}, log);
}
}  // namespace

class EpisodioTest : public ::testing::Test {
protected:
    void SetUp() override { crear(BatchProcessorConfig{}); }
    void crear(const BatchProcessorConfig& bc) {
        processor_.reset();
        ipset_ = std::make_unique<IPSetWrapper>();
        ipset_->set_dry_run(true);  // nunca tocamos el kernel en estos tests
        processor_ = std::make_unique<BatchProcessor>(*ipset_, bc);
        processor_->set_recidivism_config(escalera_prueba());
    }
    std::unique_ptr<IPSetWrapper> ipset_;
    std::unique_ptr<BatchProcessor> processor_;
};

TEST_F(EpisodioTest, BloquearSumaUnStrikeYRenovarNo) {
    auto r = processor_->bloquear_episodio("198.51.100.50");
    EXPECT_EQ(r.estado, Estado::ENCOLADO);
    EXPECT_EQ(r.timeout_sec, std::optional<uint32_t>(60u));
    EXPECT_EQ(r.strikes, 1u);
    for (int i = 0; i < 3; ++i) {
        auto rr = processor_->renovar_episodio("198.51.100.50");
        EXPECT_EQ(rr.estado, Estado::ENCOLADO);
        EXPECT_EQ(rr.timeout_sec, std::optional<uint32_t>(60u)) << "RENOVAR no debe subir de escalon";
        EXPECT_EQ(rr.strikes, 1u) << "RENOVAR no debe sumar strike";
    }
    auto r2 = processor_->bloquear_episodio("198.51.100.50");  // episodio nuevo
    EXPECT_EQ(r2.timeout_sec, std::optional<uint32_t>(300u));
    EXPECT_EQ(r2.strikes, 2u);
    auto r3 = processor_->renovar_episodio("198.51.100.50");
    EXPECT_EQ(r3.timeout_sec, std::optional<uint32_t>(300u));
    EXPECT_EQ(r3.strikes, 2u);
}

TEST_F(EpisodioTest, RenovarSinEstadoUsaPrimerEscalonSinStrike) {
    auto r = processor_->renovar_episodio("198.51.100.9");  // desborde de max_origenes: nunca bloqueado
    EXPECT_EQ(r.estado, Estado::ENCOLADO);
    EXPECT_EQ(r.timeout_sec, std::optional<uint32_t>(60u));
    EXPECT_EQ(r.strikes, 0u);
    auto r2 = processor_->bloquear_episodio("198.51.100.9");
    EXPECT_EQ(r2.timeout_sec, std::optional<uint32_t>(60u));
    EXPECT_EQ(r2.strikes, 1u);
}

TEST_F(EpisodioTest, BarreraProtegidosALaEntrada) {
    processor_->set_rangos_protegidos(intranet_lab());
    auto r = processor_->bloquear_episodio("192.168.100.61");
    EXPECT_EQ(r.estado, Estado::PROTEGIDO);
    EXPECT_FALSE(r.timeout_sec.has_value());
    EXPECT_EQ(r.strikes, 0u);
    auto r2 = processor_->renovar_episodio("192.168.100.61");
    EXPECT_EQ(r2.estado, Estado::PROTEGIDO);
    EXPECT_EQ(processor_->rechazos_protegidos(), 2u);
    EXPECT_EQ(processor_->get_pending_count(), 0u) << "un protegido entro en la cola";
    auto r3 = processor_->bloquear_episodio("198.51.100.50");  // el atacante externo si entra
    EXPECT_EQ(r3.estado, Estado::ENCOLADO);
    EXPECT_EQ(r3.timeout_sec, std::optional<uint32_t>(60u));
}

TEST_F(EpisodioTest, IpInvalidaNoEntra) {
    auto r = processor_->bloquear_episodio("no-es-una-ip");
    EXPECT_EQ(r.estado, Estado::IP_INVALIDA);
    EXPECT_FALSE(r.timeout_sec.has_value());
    EXPECT_EQ(processor_->get_pending_count(), 0u);
}

TEST_F(EpisodioTest, BarreraEnElFlushCaminoViejo) {
    processor_->set_rangos_protegidos(intranet_lab());
    processor_->add_ip("192.168.100.61");  // camino viejo, sin barrera a la entrada
    processor_->add_ip("198.51.100.50");
    processor_->flush();
    EXPECT_EQ(processor_->get_pending_count(), 0u);
    EXPECT_EQ(processor_->rechazos_protegidos(), 1u) << "la 2.a puerta no paro al protegido";
}

TEST_F(EpisodioTest, DryRunFlushVaciaLaCola) {
    processor_->add_ip("198.51.100.20");
    processor_->flush();
    EXPECT_EQ(processor_->get_pending_count(), 0u)
        << "en dry_run el flush debe tener exito sin kernel ([DRYRUN-ADD-BATCH-D302])";
}

TEST_F(EpisodioTest, RenovarActualizaLastSeen) {
    auto cfg = escalera_prueba();
    cfg.quiet_period_reset = std::chrono::seconds(2);
    processor_->set_recidivism_config(cfg);
    EXPECT_EQ(processor_->bloquear_episodio("198.51.100.60").strikes, 1u);
    std::this_thread::sleep_for(std::chrono::milliseconds(1300));
    auto rr = processor_->renovar_episodio("198.51.100.60");
    EXPECT_EQ(rr.strikes, 1u);
    std::this_thread::sleep_for(std::chrono::milliseconds(1300));
    // 2,6 s desde el BLOQUEAR (> calma de 2 s) pero 1,3 s desde el RENOVAR: sin refresco seria escalon 0.
    auto r2 = processor_->bloquear_episodio("198.51.100.60");
    EXPECT_EQ(r2.strikes, 2u) << "RENOVAR no refresco last_seen: la calma conto desde el BLOQUEAR";
    EXPECT_EQ(r2.timeout_sec, std::optional<uint32_t>(300u));
}

TEST_F(EpisodioTest, FlushSiTocaPorTiempo) {
    BatchProcessorConfig bc;
    bc.batch_size_threshold = 1000;
    bc.batch_time_threshold = std::chrono::milliseconds(500);
    crear(bc);
    EXPECT_EQ(processor_->flush_si_toca(), 0u) << "cola vacia: no debe hacer nada";
    processor_->bloquear_episodio("198.51.100.30");
    ASSERT_EQ(processor_->get_pending_count(), 1u) << "se vacio antes de tiempo";
    std::this_thread::sleep_for(std::chrono::milliseconds(600));
    processor_->flush_si_toca();
    EXPECT_EQ(processor_->get_pending_count(), 0u) << "el latido no vacio la cola vencido el plazo";
}
'''

EDITS = [
    (P_WRAP, W1_OLD, W1_NEW, "W1 add_batch: set_exists solo fuera de dry_run"),
    (P_WRAP, W2_OLD, W2_NEW, "W2 add_batch: dry_run antes del fichero temporal"),
    (P_HPP, H1_OLD, H1_NEW, "H1 struct ResultadoEpisodio"),
    (P_HPP, H2_OLD, H2_NEW, "H2 API publica por episodio"),
    (P_HPP, H3_OLD, H3_NEW, "H3 miembros privados"),
    (P_CPP, C1_OLD, C1_NEW, "C1 barrera en flush_internal"),
    (P_CPP, C2_OLD, C2_NEW, "C2 implementacion"),
    (P_TREC, T1_OLD, T1_NEW, "T1 H6 comentario"),
    (P_TREC, T2_OLD, T2_NEW, "T2 H6 fallo provocado"),
    (P_TREC, T3_OLD, T3_NEW, "T3 H6 pendientes = 2"),
    (P_CMAKE, K1_OLD, K1_NEW, "K1 fuente de firewall_tests"),
]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d302_patch_b2_1.py --check | --apply")
        return 2
    apply = sys.argv[1] == "--apply"
    files = {p: p.read_text(encoding="utf-8") for p in (P_WRAP, P_HPP, P_CPP, P_TREC, P_CMAKE)}
    errores = []
    for p, txt in files.items():
        if MARCA in txt or MARCA_DRY in txt:
            errores.append(f"YA APLICADO: marca presente en {p.relative_to(ROOT)}")
    if P_TNEW.exists():
        errores.append(f"YA EXISTE: {P_TNEW.relative_to(ROOT)}")
    for p, old, _, nombre in EDITS:
        n = files[p].count(old)
        print(f"{nombre}: {n} coincidencia(s) en {p.relative_to(ROOT)}")
        if n != 1:
            errores.append(f"ancla no unica ({n}): {nombre}")
    # include: tras el ultimo #include anterior al primer 'namespace'
    hpp = files[P_HPP]
    lineas = hpp.splitlines(keepends=True)
    ult = -1
    for i, l in enumerate(lineas):
        if l.startswith("namespace"):
            break
        if l.startswith("#include"):
            ult = i
    if ult < 0:
        errores.append("no se encontro ningun #include antes de 'namespace' en batch_processor.hpp")
    else:
        print(f"include: se inserta tras la linea {ult + 1}: {lineas[ult].rstrip()}")
    if errores:
        print("CHECK FALLA:")
        for e in errores:
            print("  - " + e)
        return 1
    nuevos = dict(files)
    lin = nuevos[P_HPP].splitlines(keepends=True)
    lin.insert(ult + 1, H_INCLUDE)
    nuevos[P_HPP] = "".join(lin)
    for p, old, new, _ in EDITS:
        nuevos[p] = nuevos[p].replace(old, new, 1)
    if not apply:
        print("CHECK OK: anclas unicas; nada escrito")
        return 0
    for p, txt in nuevos.items():
        p.write_text(txt, encoding="utf-8")
        print(f"escrito {p}")
    P_TNEW.write_text(TNEW, encoding="utf-8")
    print(f"escrito {P_TNEW}")
    print("APPLY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
