#!/usr/bin/env python3
"""
patch_d277_never_permanent.py -- aRGus NDR, DAY277

Corrige, en un solo paso atomico (o se aplica todo o no se escribe nada):

  H4  (regresion de RECIDIVISM-D276): compute_penalty_timeout() devolvia 0 tanto
      para "reincidencia deshabilitada" como para "permanente". add_batch()
      emitia 'timeout 0' (std::optional con valor 0 es truthy) => con
      enabled=false TODA IP detectada quedaba bloqueada PARA SIEMPRE.
      Decision DAY277: NUNCA bloqueo permanente automatico. Tope = max_penalty_sec.
  H2  flush_internal(): strike_states_[ip] (operator[]) insertaba entradas
      {strikes=0} saltandose max_tracked_ips. Ahora find() de solo lectura.
  H5  strike_durations_sec vacio => size()-1 da la vuelta => acceso fuera de rango.
  +   Techo del kernel MEDIDO (ipset v7.17): 2147483 s. Por encima, ipset
      rechaza y tumba el 'restore' entero. Validacion en arranque + cinturon
      en add_batch().

Uso (desde la raiz del repo, en la VM):
    python3 patch_d277_never_permanent.py            # aplica
    python3 patch_d277_never_permanent.py --dry-run  # solo comprueba anclas

Backups: <fichero>.orig_d277 (solo si no existe ya).
"""
import pathlib
import sys

MARKER = "DAY277-NEVER-PERMANENT"
DRY = "--dry-run" in sys.argv
ROOT = pathlib.Path(".").resolve()

F_BP_HPP = "firewall-acl-agent/include/firewall/batch_processor.hpp"
F_BP_CPP = "firewall-acl-agent/src/core/batch_processor.cpp"
F_IPS_HPP = "firewall-acl-agent/include/firewall/ipset_wrapper.hpp"
F_IPS_CPP = "firewall-acl-agent/src/core/ipset_wrapper.cpp"
F_CL_HPP = "firewall-acl-agent/include/firewall/config_loader.hpp"
F_CL_CPP = "firewall-acl-agent/src/core/config_loader.cpp"
F_MAIN = "firewall-acl-agent/src/main.cpp"
F_JSON = "firewall-acl-agent/config/firewall.json"
F_BACKLOG = "firewall-acl-agent/docs/BACKLOG.md"
F_UT = "firewall-acl-agent/tests/unit/test_batch_processor_recidivism.cpp"
F_E2E = "firewall-acl-agent/tests/test_recidivism_e2e.cpp"

edits = {}
errors = []


def load(rel):
    p = ROOT / rel
    if p not in edits:
        if not p.exists():
            errors.append(f"[{rel}] no existe (¿estas en la raiz del repo?)")
            edits[p] = ""
        else:
            edits[p] = p.read_text()
    return p


def replace_once(rel, old, new):
    p = load(rel)
    n = edits[p].count(old)
    if n != 1:
        errors.append(f"[{rel}] ancla encontrada {n} veces (se esperaba 1):\n---\n{old[:300]}\n---")
        return
    edits[p] = edits[p].replace(old, new, 1)


def replace_block(rel, start, end, new):
    """Sustituye desde 'start' (incluido) hasta 'end' (incluido)."""
    p = load(rel)
    t = edits[p]
    if t.count(start) != 1:
        errors.append(f"[{rel}] inicio de bloque encontrado {t.count(start)} veces:\n{start}")
        return
    i = t.index(start)
    j = t.find(end, i)
    if j < 0:
        errors.append(f"[{rel}] fin de bloque no encontrado tras el inicio:\n{end}")
        return
    edits[p] = t[:i] + new + t[j + len(end):]


def rewrite_whole(rel, must_contain, new):
    p = load(rel)
    for s in must_contain:
        if s not in edits[p]:
            errors.append(f"[{rel}] no contiene '{s}' -- el fichero no es el esperado, no lo reescribo")
            return
    edits[p] = new


# --------------------------------------------------------------------------
# Idempotencia
# --------------------------------------------------------------------------
_bp_cpp_path = ROOT / F_BP_CPP
if _bp_cpp_path.exists() and MARKER in _bp_cpp_path.read_text():
    print(f"{MARKER} ya aplicado en {F_BP_CPP}. Nada que hacer.")
    sys.exit(0)

# --------------------------------------------------------------------------
# ipset_wrapper.hpp -- techo medido del kernel
# --------------------------------------------------------------------------
replace_once(F_IPS_HPP, "struct IPSetEntry {", """/// DAY277-NEVER-PERMANENT: techo del timeout por entrada, MEDIDO en la VM
/// (ipset v7.17): 'timeout 2147484' -> "out of range 0-2147483". Un valor
/// mayor NO se recorta: ipset lo rechaza y tumba el 'restore' entero.
inline constexpr uint32_t kIpsetMaxTimeoutSec = 2147483;

struct IPSetEntry {""")

# --------------------------------------------------------------------------
# ipset_wrapper.cpp -- cinturon en add_batch()
# --------------------------------------------------------------------------
# Medido DAY277: ipset_wrapper.cpp no usa FIREWALL_LOG_*; su convencion es
# <iostream> directo (ya incluido, ver '[DRY-RUN] Would execute'). Se respeta.
ips_cpp = load(F_IPS_CPP)
if "#include <iostream>" not in edits[ips_cpp]:
    errors.append(f"[{F_IPS_CPP}] no incluye <iostream> -- revisar a mano antes de parchear")
replace_once(F_IPS_CPP, """        if (entry.timeout) {
            restore_input << " timeout " << *entry.timeout;
        }
""", """        if (entry.timeout) {
            // DAY277-NEVER-PERMANENT: 'timeout 0' = PERMANENTE en ipset, y un
            // valor > kIpsetMaxTimeoutSec tumba el 'restore' entero. Cinturon:
            // ningun camino automatico deja una IP bloqueada para siempre.
            // El drop permanente es una accion MANUAL del admin, por otro camino.
            uint32_t t = *entry.timeout;
            if (t == 0 || t > kIpsetMaxTimeoutSec) {
                std::cerr << "[WARN][ipset_wrapper] add_batch: timeout fuera de [1, "
                          << kIpsetMaxTimeoutSec << "] (nunca permanente) ip=" << entry.ip
                          << " requested=" << *entry.timeout
                          << " applied=" << kIpsetMaxTimeoutSec << std::endl;
                t = kIpsetMaxTimeoutSec;
            }
            restore_input << " timeout " << t;
        }
""")

# --------------------------------------------------------------------------
# batch_processor.hpp
# --------------------------------------------------------------------------
replace_once(F_BP_HPP, "namespace mldefender::firewall {",
             "#include <optional>  // DAY277-NEVER-PERMANENT\n\nnamespace mldefender::firewall {")

replace_once(F_BP_HPP, """    /// A partir de este numero de reincidencias, bloqueo permanente (timeout=0)
    uint32_t permanent_after_strikes{6};
""", """    /// A partir de este numero de reincidencias se aplica max_penalty_sec.
    /// NUNCA bloqueo permanente (DAY277-NEVER-PERMANENT): las IPs de botnets
    /// suelen ser victimas (equipos comprometidos, CGNAT compartido). El drop
    /// permanente es una accion manual del admin, fuera de este camino.
    uint32_t max_penalty_after_strikes{6};
    /// Castigo maximo en segundos. Rango valido [1, kIpsetMaxTimeoutSec].
    uint32_t max_penalty_sec{2073600};  // 24 dias
""")

replace_once(F_BP_HPP, """    void set_recidivism_config(const RecidivismConfig& cfg) { recidivism_config_ = cfg; }  // RECIDIVISM-D276
    /// RECIDIVISM-D276: publico a proposito -- testeable sin IPSetWrapper real ni
    /// kernel, igual que should_auto_isolate. Calcula el timeout a aplicar a
    /// esta IP y actualiza su contador de reincidencia.
    uint32_t compute_penalty_timeout(const std::string& ip);
""", """    /// RECIDIVISM-D276 + DAY277-NEVER-PERMANENT: valida y sanea la config
    /// (ningun timeout puede ser 0 = permanente ni superar kIpsetMaxTimeoutSec;
    /// escalera vacia -> escalera por defecto). Loguea cada correccion. Toma mutex_.
    void set_recidivism_config(const RecidivismConfig& cfg);
    /// RECIDIVISM-D276: publico a proposito -- testeable sin IPSetWrapper real ni
    /// kernel, igual que should_auto_isolate. Calcula el timeout a aplicar a
    /// esta IP y actualiza su contador de reincidencia.
    /// DAY277-NEVER-PERMANENT: nullopt = reincidencia deshabilitada (se aplica
    /// el timeout por defecto del set, comportamiento pre-D276). Con valor,
    /// SIEMPRE en [1, max_penalty_sec]. Nunca 0.
    /// Requiere mutex_ tomado (lo llama flush_internal); los tests unitarios
    /// lo llaman sin concurrencia.
    std::optional<uint32_t> compute_penalty_timeout(const std::string& ip);
""")

# --------------------------------------------------------------------------
# batch_processor.cpp
# --------------------------------------------------------------------------
replace_once(F_BP_CPP,
             "#include <fstream>  // RECIDIVISM-D276: volcado de strike_states_ a disco\n",
             "#include <fstream>  // RECIDIVISM-D276: volcado de strike_states_ a disco\n"
             "#include \"firewall/ipset_wrapper.hpp\"  // DAY277-NEVER-PERMANENT: kIpsetMaxTimeoutSec\n")

replace_once(F_BP_CPP, """    for (const auto& ip : pending_ips_) {
        // RECIDIVISM-D276: timeout variable por reincidencia en vez del fijo del set
        uint32_t penalty = compute_penalty_timeout(ip);
        std::string reason = "strikes=" + std::to_string(strike_states_[ip].strikes);
        entries.push_back(IPSetEntry{ip, penalty, reason});
    }
""", """    for (const auto& ip : pending_ips_) {
        // RECIDIVISM-D276: timeout variable por reincidencia en vez del fijo del set.
        // DAY277-NEVER-PERMANENT: nullopt (deshabilitado) -> IPSetEntry SIN
        // timeout -> timeout por defecto del set, igual que antes de D276.
        std::optional<uint32_t> penalty = compute_penalty_timeout(ip);
        IPSetEntry entry{ip};
        entry.timeout = penalty;
        if (penalty) {
            // H2-D277: find() de solo lectura. operator[] insertaba {strikes=0}
            // saltandose max_tracked_ips (mapa sin cota con enabled=false).
            auto it = strike_states_.find(ip);
            uint32_t strikes = (it != strike_states_.end()) ? it->second.strikes : 0;
            entry.comment = "strikes=" + std::to_string(strikes);
        }
        entries.push_back(std::move(entry));
    }
""")

replace_block(F_BP_CPP,
              "uint32_t BatchProcessor::compute_penalty_timeout(const std::string& ip) {",
              "    return recidivism_config_.strike_durations_sec[idx];\n}\n",
              """std::optional<uint32_t> BatchProcessor::compute_penalty_timeout(const std::string& ip) {
    if (!recidivism_config_.enabled) {
        // DAY277-NEVER-PERMANENT: antes devolvia 0, que add_batch() emitia
        // como 'timeout 0' = PERMANENTE para toda IP. nullopt = timeout del set.
        return std::nullopt;
    }

    // Chequeo de overflow ANTES de tocar el mapa para esta IP: si hicieramos
    // esto despues de state = strike_states_[ip], un clear() posterior
    // invalidaria la referencia 'state' y seria UB escribir en ella.
    if (strike_states_.size() >= recidivism_config_.max_tracked_ips &&
        strike_states_.find(ip) == strike_states_.end()) {
        dump_and_reset_strike_states();
    }

    auto now = std::chrono::steady_clock::now();
    auto& state = strike_states_[ip];

    if (state.strikes > 0 &&
        (now - state.last_seen) > recidivism_config_.quiet_period_reset) {
        FIREWALL_LOG_INFO("Recidivism counter reset by quiet period",
            "ip", ip, "previous_strikes", state.strikes);
        state.strikes = 0;
    }

    state.strikes++;
    state.last_seen = now;

    if (state.strikes >= recidivism_config_.max_penalty_after_strikes) {
        FIREWALL_LOG_WARN("IP alcanza el castigo maximo (nunca permanente)",
            "ip", ip, "strikes", state.strikes,
            "max_penalty_sec", recidivism_config_.max_penalty_sec);
        return recidivism_config_.max_penalty_sec;
    }

    // H5-D277: set_recidivism_config() garantiza escalera no vacia y sin 0;
    // esta guarda cubre cualquier camino que se lo salte.
    if (recidivism_config_.strike_durations_sec.empty()) {
        return recidivism_config_.max_penalty_sec;
    }
    size_t idx = std::min<size_t>(state.strikes - 1,
        recidivism_config_.strike_durations_sec.size() - 1);
    return std::min(recidivism_config_.strike_durations_sec[idx],
                    recidivism_config_.max_penalty_sec);
}

// DAY277-NEVER-PERMANENT: validacion + saneado de la config de reincidencia.
// Politica: el sistema ARRANCA siempre; cada valor corregido deja un ERROR/WARN
// visible en el log de arranque para que el admin lo vea.
void BatchProcessor::set_recidivism_config(const RecidivismConfig& cfg) {
    RecidivismConfig c = cfg;
    constexpr uint32_t kDefaultMaxPenaltySec = 2073600;  // 24 dias

    if (c.max_penalty_sec == 0 || c.max_penalty_sec > kIpsetMaxTimeoutSec) {
        uint32_t fixed = (c.max_penalty_sec == 0)
            ? std::min(kDefaultMaxPenaltySec, kIpsetMaxTimeoutSec)
            : kIpsetMaxTimeoutSec;
        FIREWALL_LOG_ERROR("recidivism.max_penalty_sec fuera de [1, techo ipset] -- se corrige",
            "configured", c.max_penalty_sec,
            "applied", fixed,
            "kernel_max", kIpsetMaxTimeoutSec);
        c.max_penalty_sec = fixed;
    }

    if (c.strike_durations_sec.empty()) {
        FIREWALL_LOG_ERROR("recidivism.strike_durations_sec vacio -- se usa la escalera por defecto");
        c.strike_durations_sec = RecidivismConfig{}.strike_durations_sec;
    }

    for (size_t i = 0; i < c.strike_durations_sec.size(); ++i) {
        uint32_t& d = c.strike_durations_sec[i];
        if (d == 0) {
            FIREWALL_LOG_ERROR("recidivism.strike_durations_sec contiene 0 (= permanente en ipset) -- se sustituye por max_penalty_sec",
                "index", i, "applied", c.max_penalty_sec);
            d = c.max_penalty_sec;
        } else if (d > c.max_penalty_sec) {
            FIREWALL_LOG_WARN("recidivism.strike_durations_sec supera max_penalty_sec -- se recorta",
                "index", i, "configured", d, "applied", c.max_penalty_sec);
            d = c.max_penalty_sec;
        }
    }

    if (c.max_penalty_after_strikes == 0) {
        FIREWALL_LOG_WARN("recidivism.max_penalty_after_strikes=0: toda IP recibe max_penalty_sec desde el 1er strike");
    }

    FIREWALL_LOG_INFO("Recidivism config aplicada (nunca permanente)",
        "enabled", c.enabled,
        "steps", c.strike_durations_sec.size(),
        "max_penalty_after_strikes", c.max_penalty_after_strikes,
        "max_penalty_sec", c.max_penalty_sec,
        "max_tracked_ips", c.max_tracked_ips);

    std::lock_guard<std::mutex> lock(mutex_);
    recidivism_config_ = std::move(c);
}
""")

# --------------------------------------------------------------------------
# config_loader.hpp / .cpp
# --------------------------------------------------------------------------
replace_once(F_CL_HPP, "    int permanent_after_strikes = 6;\n",
             "    int max_penalty_after_strikes = 6;   // DAY277-NEVER-PERMANENT (antes permanent_after_strikes)\n"
             "    int max_penalty_sec = 2073600;       // 24 dias; techo ipset medido 2147483\n")

replace_once(F_CL_CPP,
             "    config.permanent_after_strikes = get_optional<int>(json, \"permanent_after_strikes\", 6);\n",
             """    // DAY277-NEVER-PERMANENT: clave renombrada (ya no existe bloqueo permanente).
    // La antigua se acepta como fallback para no romper configs desplegadas.
    config.max_penalty_after_strikes = get_optional<int>(json, "max_penalty_after_strikes",
        get_optional<int>(json, "permanent_after_strikes", 6));
    config.max_penalty_sec = get_optional<int>(json, "max_penalty_sec", 2073600);
""")

# --------------------------------------------------------------------------
# main.cpp -- conversion sin static_cast de negativos
# --------------------------------------------------------------------------
replace_once(F_MAIN, """    recidivism_config.strike_durations_sec.assign(
        config.recidivism.strike_durations_sec.begin(),
        config.recidivism.strike_durations_sec.end());
""", """    // DAY277-NEVER-PERMANENT: un negativo en el JSON pasaba por static_cast a
    // ~4.29e9 y tumbaba el 'ipset restore'. Ahora negativo -> 0 -> saneado con
    // ERROR visible en set_recidivism_config().
    recidivism_config.strike_durations_sec.clear();
    for (int d : config.recidivism.strike_durations_sec) {
        recidivism_config.strike_durations_sec.push_back(d < 0 ? 0u : static_cast<uint32_t>(d));
    }
""")

replace_once(F_MAIN, """    recidivism_config.permanent_after_strikes =
        static_cast<uint32_t>(config.recidivism.permanent_after_strikes);
""", """    recidivism_config.max_penalty_after_strikes =
        config.recidivism.max_penalty_after_strikes < 0 ? 0u
            : static_cast<uint32_t>(config.recidivism.max_penalty_after_strikes);
    recidivism_config.max_penalty_sec =
        config.recidivism.max_penalty_sec < 0 ? 0u
            : static_cast<uint32_t>(config.recidivism.max_penalty_sec);
""")

# --------------------------------------------------------------------------
# firewall.json / BACKLOG.md
# --------------------------------------------------------------------------
replace_once(F_JSON, "    \"permanent_after_strikes\": 6,\n",
             "    \"max_penalty_after_strikes\": 6,\n"
             "    \"max_penalty_sec\": 2073600,\n"
             "    \"_comment_max_penalty\": \"DAY277: NUNCA permanente. 2073600 s = 24 dias; techo ipset medido 2147483 s. Drop permanente = accion manual del admin\",\n")

replace_once(F_BACKLOG, "**Solution**: Track recidivism, auto-promote to permanent block",
             "**Solution**: Track recidivism, escalate up to a capped max penalty -- "
             "NEVER permanent (DAY277-NEVER-PERMANENT: botnet IPs are usually victims; "
             "permanent drop is a manual admin action). Implemented as RECIDIVISM-D276")

# --------------------------------------------------------------------------
# Tests -- reescritura completa (el contenido viejo codificaba "permanente")
# --------------------------------------------------------------------------
UT_NEW = r'''// test_batch_processor_recidivism.cpp — RECIDIVISM-D276 + DAY277-NEVER-PERMANENT
// Unit tests de compute_penalty_timeout / set_recidivism_config /
// dump_and_reset_strike_states. Sin root: IPSetWrapper en dry_run.
#include <gtest/gtest.h>
#include "firewall/batch_processor.hpp"
#include "firewall/ipset_wrapper.hpp"
#include <cstdio>
#include <fstream>
#include <optional>
#include <sstream>
#include <string>

using namespace mldefender::firewall;

namespace {

std::string read_file(const std::string& path) {
    std::ifstream in(path);
    std::stringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

bool file_exists(const std::string& path) {
    std::ifstream f(path);
    return f.good();
}

}  // namespace

class RecidivismTest : public ::testing::Test {
protected:
    void SetUp() override {
        ipset_ = std::make_unique<IPSetWrapper>();
        ipset_->set_dry_run(true);  // nunca tocamos el kernel en estos tests
        processor_ = std::make_unique<BatchProcessor>(*ipset_);
    }

    std::unique_ptr<IPSetWrapper> ipset_;
    std::unique_ptr<BatchProcessor> processor_;
};

TEST_F(RecidivismTest, FirstStrikeUsesFirstDuration) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300, 3600};
    cfg.max_penalty_after_strikes = 10;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), std::optional<uint32_t>(60u));
}

TEST_F(RecidivismTest, EscalatesOnRepeatedStrikes) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300, 3600};
    cfg.max_penalty_after_strikes = 10;
    cfg.quiet_period_reset = std::chrono::hours(999);
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), std::optional<uint32_t>(60u));
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), std::optional<uint32_t>(300u));
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), std::optional<uint32_t>(3600u));
    // Se queda en el ultimo escalon por debajo de max_penalty_after_strikes
    EXPECT_EQ(processor_->compute_penalty_timeout("1.2.3.4"), std::optional<uint32_t>(3600u));
}

TEST_F(RecidivismTest, DifferentIpsTrackedIndependently) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300};
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("1.1.1.1"), std::optional<uint32_t>(60u));
    EXPECT_EQ(processor_->compute_penalty_timeout("2.2.2.2"), std::optional<uint32_t>(60u));
    EXPECT_EQ(processor_->compute_penalty_timeout("1.1.1.1"), std::optional<uint32_t>(300u));
}

// DAY277: sustituye a PermanentAfterThreshold. El umbral da el castigo
// MAXIMO, nunca 0 (= permanente en ipset).
TEST_F(RecidivismTest, MaxPenaltyAfterThresholdIsNeverPermanent) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60};
    cfg.max_penalty_after_strikes = 3;
    cfg.max_penalty_sec = 7200;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("9.9.9.9"), std::optional<uint32_t>(60u));
    EXPECT_EQ(processor_->compute_penalty_timeout("9.9.9.9"), std::optional<uint32_t>(60u));
    auto t3 = processor_->compute_penalty_timeout("9.9.9.9");
    ASSERT_TRUE(t3.has_value());
    EXPECT_EQ(*t3, 7200u);
    // y sigue en el tope, nunca pasa a 0
    auto t4 = processor_->compute_penalty_timeout("9.9.9.9");
    ASSERT_TRUE(t4.has_value());
    EXPECT_EQ(*t4, 7200u);
}

// H4-D277: deshabilitado => nullopt (timeout por defecto del set), NO 0.
TEST_F(RecidivismTest, DisabledReturnsNulloptNotZero) {
    RecidivismConfig cfg;
    cfg.enabled = false;
    processor_->set_recidivism_config(cfg);

    EXPECT_FALSE(processor_->compute_penalty_timeout("5.5.5.5").has_value());
    EXPECT_FALSE(processor_->compute_penalty_timeout("5.5.5.5").has_value());
}

// H2-D277: con reincidencia deshabilitada, flush() NO debe meter nada en
// strike_states_. Observable: si el bug existiera, 3 flushes con
// max_tracked_ips=2 dejarian 3 entradas y la siguiente IP (ya habilitado)
// dispararia el volcado de overflow => existiria el fichero.
TEST_F(RecidivismTest, DisabledFlushDoesNotTrackIps) {
    const std::string overflow_path = "/tmp/test_recidivism_h2_overflow.log";
    std::remove(overflow_path.c_str());

    RecidivismConfig cfg;
    cfg.enabled = false;
    cfg.max_tracked_ips = 2;
    cfg.overflow_log_path = overflow_path;
    processor_->set_recidivism_config(cfg);

    for (const char* ip : {"198.51.100.1", "198.51.100.2", "198.51.100.3"}) {
        processor_->add_ip(ip);
        ASSERT_EQ(processor_->get_pending_count(), 1u)
            << "add_ip no encolo " << ip << " -- el test no estaria probando nada";
        processor_->flush();
    }

    cfg.enabled = true;
    processor_->set_recidivism_config(cfg);
    processor_->compute_penalty_timeout("198.51.100.4");

    EXPECT_FALSE(file_exists(overflow_path))
        << "flush() con enabled=false inserto IPs en strike_states_ (H2)";
    std::remove(overflow_path.c_str());
}

// Validacion: 0 en cualquier duracion => nunca permanente.
TEST_F(RecidivismTest, SanitizeZeroValuesNeverPermanent) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {0, 0};
    cfg.max_penalty_sec = 0;
    cfg.max_penalty_after_strikes = 10;
    processor_->set_recidivism_config(cfg);

    auto t = processor_->compute_penalty_timeout("7.7.7.7");
    ASSERT_TRUE(t.has_value());
    EXPECT_GT(*t, 0u);
    EXPECT_LE(*t, kIpsetMaxTimeoutSec);
}

// Validacion: por encima del techo medido del kernel => se recorta al techo.
TEST_F(RecidivismTest, SanitizeClampsToKernelMax) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {3000000};
    cfg.max_penalty_sec = 3000000;
    cfg.max_penalty_after_strikes = 10;
    processor_->set_recidivism_config(cfg);

    EXPECT_EQ(processor_->compute_penalty_timeout("8.8.4.4"),
              std::optional<uint32_t>(kIpsetMaxTimeoutSec));
}

// H5-D277: escalera vacia no debe provocar acceso fuera de rango.
TEST_F(RecidivismTest, EmptyDurationsDoesNotCrash) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {};
    cfg.max_penalty_after_strikes = 10;
    processor_->set_recidivism_config(cfg);

    auto t = processor_->compute_penalty_timeout("6.6.6.6");
    ASSERT_TRUE(t.has_value());
    EXPECT_GT(*t, 0u);
}

TEST_F(RecidivismTest, OverflowDumpsToFileAndResets) {
    const std::string overflow_path = "/tmp/test_recidivism_overflow.log";
    std::remove(overflow_path.c_str());

    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300};
    cfg.max_tracked_ips = 2;
    cfg.overflow_log_path = overflow_path;
    processor_->set_recidivism_config(cfg);

    processor_->compute_penalty_timeout("10.0.0.1");
    processor_->compute_penalty_timeout("10.0.0.2");
    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.3"), std::optional<uint32_t>(60u));

    std::string dumped = read_file(overflow_path);
    EXPECT_NE(dumped.find("10.0.0.1"), std::string::npos);
    EXPECT_NE(dumped.find("10.0.0.2"), std::string::npos);

    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.1"), std::optional<uint32_t>(60u));

    std::remove(overflow_path.c_str());
}

TEST_F(RecidivismTest, OverflowDoesNotResetIfDumpFails) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300};
    cfg.max_tracked_ips = 2;
    cfg.overflow_log_path = "/ruta/que/no/existe/overflow.log";
    processor_->set_recidivism_config(cfg);

    processor_->compute_penalty_timeout("10.0.0.1");
    processor_->compute_penalty_timeout("10.0.0.2");
    processor_->compute_penalty_timeout("10.0.0.3");
    EXPECT_EQ(processor_->compute_penalty_timeout("10.0.0.1"), std::optional<uint32_t>(300u));
}
'''

E2E_NEW = r'''// test_recidivism_e2e.cpp — RECIDIVISM-D276 + DAY277-NEVER-PERMANENT
// Test de ACEPTACION: requiere root (manipula un ipset real del kernel).
// No usa el ipset de produccion "blacklist" -- crea uno propio de prueba
// y lo destruye al final, para no interferir con nada mas.
//
// Que verifica, de extremo a extremo, sin mocks:
//   1) BatchProcessor::flush() escribe de verdad en el ipset del kernel.
//   2) El timeout de la entrada escala segun strike_durations_sec cuando
//      la misma IP reincide en flushes sucesivos.
//   3) Al alcanzar max_penalty_after_strikes, la entrada lleva max_penalty_sec:
//      NUNCA timeout 0 (= permanente). Decision DAY277.
//   4) Con la reincidencia deshabilitada se aplica el timeout por defecto
//      del set (regresion H4 de D276: antes quedaba permanente).
//
// Ejecucion: `make test-firewall-e2e`, o como root:
//   sudo ./firewall-acl-agent/build-debug/test_recidivism_e2e
#include <gtest/gtest.h>
#include "firewall/batch_processor.hpp"
#include "firewall/ipset_wrapper.hpp"
#include <array>
#include <cstdio>
#include <cstdlib>  // std::system
#include <memory>
#include <regex>
#include <sstream>
#include <string>
#include <thread>
#include <chrono>
#include <unistd.h>  // getuid

using namespace mldefender::firewall;

namespace {

std::string shell(const std::string& cmd) {
    std::array<char, 256> buf{};
    std::string out;
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) return out;
    while (fgets(buf.data(), buf.size(), pipe) != nullptr) {
        out += buf.data();
    }
    pclose(pipe);
    return out;
}

// Devuelve N de "ip timeout N" en `ipset list`, o -1 si no aparece.
// (Medido DAY276: en un set con timeout, una entrada permanente se imprime
// como "timeout 0", asi que 0 aqui significa PERMANENTE.)
int extract_timeout(const std::string& ipset_list_output, const std::string& ip) {
    std::regex re(ip + R"(\s+timeout\s+(\d+))");
    std::smatch m;
    if (std::regex_search(ipset_list_output, m, re)) {
        return std::stoi(m[1].str());
    }
    return -1;
}

bool entry_present(const std::string& ipset_list_output, const std::string& ip) {
    return ipset_list_output.find(ip) != std::string::npos;
}

constexpr const char* TEST_SET_NAME = "argus_test_recidivism_e2e";
// DAY277: timeout por defecto del set de prueba != 0, para que ninguna
// entrada pueda quedar permanente "por accidente" via el default del set.
constexpr int TEST_SET_DEFAULT_TIMEOUT = 600;

}  // namespace

class RecidivismE2ETest : public ::testing::Test {
protected:
    void SetUp() override {
        if (getuid() != 0) {
            GTEST_SKIP() << "requiere root (manipula ipset real) -- "
                            "ejecutar via 'make test-firewall-e2e'";
        }
        shell(std::string("ipset destroy ") + TEST_SET_NAME + " 2>/dev/null");
        int rc = std::system(
            (std::string("ipset create ") + TEST_SET_NAME +
             " hash:ip timeout " + std::to_string(TEST_SET_DEFAULT_TIMEOUT) +
             " comment 2>&1").c_str());
        ASSERT_EQ(rc, 0) << "no se pudo crear el ipset de prueba "
                          << TEST_SET_NAME
                          << " -- ¿ipset instalado? ¿de verdad estamos "
                             "corriendo como root?";

        ipset_ = std::make_unique<IPSetWrapper>();
        ipset_->set_dry_run(false);

        BatchProcessorConfig cfg;
        cfg.batch_size_threshold = 1;
        cfg.max_pending_ips = 10;
        cfg.confidence_threshold = 0.0f;
        cfg.blacklist_ipset = TEST_SET_NAME;
        processor_ = std::make_unique<BatchProcessor>(*ipset_, cfg);

        rcfg_.enabled = true;
        rcfg_.strike_durations_sec = {5, 10, 20};
        rcfg_.max_penalty_after_strikes = 4;
        rcfg_.max_penalty_sec = 30;
        rcfg_.quiet_period_reset = std::chrono::hours(999);
        rcfg_.max_tracked_ips = 1000;
        rcfg_.overflow_log_path = "/tmp/argus_test_recidivism_e2e_overflow.log";
        processor_->set_recidivism_config(rcfg_);
    }

    void TearDown() override {
        if (getuid() != 0) return;
        processor_.reset();
        ipset_.reset();
        shell(std::string("ipset destroy ") + TEST_SET_NAME + " 2>/dev/null");
    }

    std::string list_set() {
        return shell(std::string("ipset list ") + TEST_SET_NAME + " 2>&1");
    }

    RecidivismConfig rcfg_;
    std::unique_ptr<IPSetWrapper> ipset_;
    std::unique_ptr<BatchProcessor> processor_;
};

TEST_F(RecidivismE2ETest, FirstFlushAppliesFirstStrikeDuration) {
    const std::string ip = "203.0.113.11";
    processor_->add_ip(ip);
    processor_->flush();

    auto listing = list_set();
    ASSERT_TRUE(entry_present(listing, ip)) << listing;
    int timeout = extract_timeout(listing, ip);
    ASSERT_GT(timeout, 0);
    EXPECT_LE(timeout, 5);
    EXPECT_GE(timeout, 1);
}

TEST_F(RecidivismE2ETest, RepeatedOffenderEscalatesRealTimeout) {
    const std::string ip = "203.0.113.22";

    processor_->add_ip(ip);
    processor_->flush();
    auto after_strike1 = list_set();
    int t1 = extract_timeout(after_strike1, ip);
    ASSERT_GT(t1, 0) << after_strike1;

    processor_->add_ip(ip);
    processor_->flush();
    auto after_strike2 = list_set();
    int t2 = extract_timeout(after_strike2, ip);
    ASSERT_GT(t2, 0) << after_strike2;

    EXPECT_GT(t2, t1);
}

// DAY277: sustituye a PermanentAfterThresholdHasNoTimeoutInKernel.
TEST_F(RecidivismE2ETest, CappedAfterThresholdNeverPermanentInKernel) {
    const std::string ip = "203.0.113.33";

    for (int i = 0; i < 4; ++i) {
        processor_->add_ip(ip);
        processor_->flush();
    }

    auto listing = list_set();
    ASSERT_TRUE(entry_present(listing, ip)) << listing;
    int t = extract_timeout(listing, ip);
    EXPECT_GT(t, 0) << "timeout 0 en el kernel = PERMANENTE (prohibido DAY277)\n" << listing;
    EXPECT_LE(t, 30) << listing;   // max_penalty_sec
    EXPECT_GT(t, 20) << listing;   // por encima del ultimo escalon (20): es el tope, no el escalon
}

// DAY277 / H4: con la reincidencia deshabilitada, la entrada lleva el timeout
// por defecto del set. Con el bug de D276 aparecia "timeout 0" (permanente).
TEST_F(RecidivismE2ETest, DisabledUsesSetDefaultTimeoutNotPermanent) {
    rcfg_.enabled = false;
    processor_->set_recidivism_config(rcfg_);

    const std::string ip = "203.0.113.44";
    processor_->add_ip(ip);
    processor_->flush();

    auto listing = list_set();
    ASSERT_TRUE(entry_present(listing, ip)) << listing;
    int t = extract_timeout(listing, ip);
    EXPECT_GT(t, 0) << "H4: enabled=false dejo la IP PERMANENTE\n" << listing;
    EXPECT_LE(t, TEST_SET_DEFAULT_TIMEOUT) << listing;
}
'''

rewrite_whole(F_UT, ["PermanentAfterThreshold", "RECIDIVISM-D276"], UT_NEW)
rewrite_whole(F_E2E, ["PermanentAfterThresholdHasNoTimeoutInKernel", "RECIDIVISM-D276"], E2E_NEW)

# --------------------------------------------------------------------------
# Veredicto
# --------------------------------------------------------------------------
if errors:
    print("ABORTADO -- no se ha escrito NINGUN fichero. Anclas que fallan:\n")
    for e in errors:
        print(e, "\n")
    sys.exit(1)

if DRY:
    print(f"--dry-run OK: {len(edits)} ficheros se parchearian:")
    for p in edits:
        print("  ", p.relative_to(ROOT))
    sys.exit(0)

for p, text in edits.items():
    bak = p.with_name(p.name + ".orig_d277")
    if not bak.exists():
        bak.write_text(p.read_text())
    p.write_text(text)
    print("parcheado:", p.relative_to(ROOT))

print(f"\n{MARKER} aplicado en {len(edits)} ficheros. Backups: *.orig_d277")