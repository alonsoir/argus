#!/usr/bin/env python3
"""patch_d277_h6_retry_strikes.py -- DAY277-H6
Un flush fallido conserva pending_ips_ y el siguiente flush volvia a llamar a
compute_penalty_timeout() => un strike por REINTENTO, no por deteccion.
Arreglo: pending_penalty_ (ip -> penalty) se calcula UNA vez por IP pendiente,
se reutiliza en reintentos y se vacia junto a pending_ips_ (unico clear, l.446)."""
import pathlib, sys
MARKER = "DAY277-H6"
HPP = pathlib.Path("firewall-acl-agent/include/firewall/batch_processor.hpp")
CPP = pathlib.Path("firewall-acl-agent/src/core/batch_processor.cpp")
UT  = pathlib.Path("firewall-acl-agent/tests/unit/test_batch_processor_recidivism.cpp")
E = [
 (HPP, "    std::unordered_set<std::string> pending_ips_;  ///< IPs waiting to flush\n",
       "    std::unordered_set<std::string> pending_ips_;  ///< IPs waiting to flush\n"
       "    /// DAY277-H6: penalty calculada UNA vez por IP pendiente; los reintentos de un\n"
       "    /// flush fallido la reutilizan (no suman strikes). Se vacia con pending_ips_.\n"
       "    /// Guardado por mutex_.\n"
       "    std::unordered_map<std::string, std::optional<uint32_t>> pending_penalty_;\n"),
 (CPP, "        std::optional<uint32_t> penalty = compute_penalty_timeout(ip);\n",
       "        // DAY277-H6: un flush fallido conserva pending_ips_; sin esto cada\n"
       "        // reintento sumaba un strike (una sola deteccion podia llegar al maximo).\n"
       "        std::optional<uint32_t> penalty;\n"
       "        if (auto pit = pending_penalty_.find(ip); pit != pending_penalty_.end()) {\n"
       "            penalty = pit->second;\n"
       "        } else {\n"
       "            penalty = compute_penalty_timeout(ip);\n"
       "            pending_penalty_.emplace(ip, penalty);\n"
       "        }\n"),
 (CPP, "        // Clear pending set\n        pending_ips_.clear();\n",
       "        // Clear pending set\n        pending_ips_.clear();\n"
       "        pending_penalty_.clear();  // DAY277-H6\n"),
 (UT,  "TEST_F(RecidivismTest, OverflowDumpsToFileAndResets) {",
       """// DAY277-H6: reintentos de un flush fallido NO suman strikes.
// En dry_run el set no existe -> add_batch devuelve SET_NOT_FOUND (medido en
// ipset_wrapper.cpp: set_exists_unlocked va antes del dry_run) -> flush falla
// y la IP sigue pendiente. Con el bug: 5 flushes = 5 strikes -> siguiente = 3600.
TEST_F(RecidivismTest, FailedFlushRetriesDoNotInflateStrikes) {
    RecidivismConfig cfg;
    cfg.strike_durations_sec = {60, 300, 3600};
    cfg.max_penalty_after_strikes = 10;
    cfg.quiet_period_reset = std::chrono::hours(999);
    processor_->set_recidivism_config(cfg);

    processor_->add_ip("198.51.100.77");
    for (int i = 0; i < 5; ++i) {
        processor_->flush();
    }
    ASSERT_EQ(processor_->get_pending_count(), 1u)
        << "el flush no fallo: el test no reproduce el reintento";

    // Una deteccion = un strike. La siguiente llamada debe ser el strike 2.
    EXPECT_EQ(processor_->compute_penalty_timeout("198.51.100.77"),
              std::optional<uint32_t>(300u));
}

TEST_F(RecidivismTest, OverflowDumpsToFileAndResets) {"""),
]
texts = {}
for p, _, _ in E:
    if p not in texts:
        if not p.exists(): sys.exit(f"no existe {p} (¿raiz del repo?)")
        texts[p] = p.read_text()
if MARKER in texts[CPP]: sys.exit(f"{MARKER} ya aplicado. Nada que hacer.")
errs = []
for p, old, new in E:
    n = texts[p].count(old)
    if n != 1: errs.append(f"[{p}] ancla {n} veces:\n{old}"); continue
    texts[p] = texts[p].replace(old, new, 1)
if errs:
    print("ABORTADO, no se escribe nada:\n" + "\n".join(errs)); sys.exit(1)
for p, t in texts.items():
    bak = p.with_name(p.name + ".orig_d277h6")
    if not bak.exists(): bak.write_text(p.read_text())
    p.write_text(t); print("parcheado:", p)
