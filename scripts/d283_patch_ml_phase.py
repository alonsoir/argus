#!/usr/bin/env python3
# DAY283 D2 — [ML-PHASE]: desglose del coste de run_ml_detection por fase (solo observacion).
import sys, shutil, pathlib

p = pathlib.Path("/vagrant/sniffer/src/userspace/ring_consumer.cpp")
src = p.read_text()

if "[ML-PHASE]" in src:
    print("YA PARCHEADO: nada que hacer"); sys.exit(0)
if "[ML-TIME]" not in src:
    print("PARAR: falta [ML-TIME] (aplicar antes d283_patch_ml_time.py)"); sys.exit(1)

stamps = [
    ("    auto internal_features = extract_internal_features(proto_event);\n", "mlt_t1"),
    ("    auto ddos_pred = ddos_detector_.predict(ddos_features);\n", "mlt_t2"),
    ("    auto ransomware_pred = ransomware_detector_.predict(ransomware_features);\n", "mlt_t3"),
    ("    auto traffic_pred = traffic_detector_.predict(traffic_features);\n", "mlt_t4"),
    ("    auto internal_pred = internal_detector_.predict(internal_features);\n", "mlt_t5"),
]
for anchor, _ in stamps:
    n = src.count(anchor)
    if n != 1:
        print(f"PARAR: ancla encontrada {n} veces (esperado 1):\n{anchor}"); sys.exit(1)

tail_anchor = "    stats_.ml_detection_time_us += duration.count();\n"
if src.count(tail_anchor) != 1:
    print("PARAR: ancla de fin no unica"); sys.exit(1)

for anchor, var in stamps:
    src = src.replace(anchor,
        anchor + f"    auto {var} = std::chrono::high_resolution_clock::now();  // DAY283 ML-PHASE\n", 1)

block = tail_anchor + r'''
    // DAY283 D2 — [ML-PHASE] (solo observacion): extract | ddos | ransom | traffic | internal | post
    {
        static std::atomic<uint64_t> mph_calls{0};
        static std::atomic<uint64_t> mph_sum[6];
        static std::atomic<uint64_t> mph_hist[6][40];
        static std::atomic<int64_t>  mph_last_print_ns{0};
        static const char* const mph_names[6] =
            {"extract", "ddos", "ransom", "traffic", "internal", "post"};
        const std::chrono::high_resolution_clock::time_point mph_t[7] =
            {start, mlt_t1, mlt_t2, mlt_t3, mlt_t4, mlt_t5, end};

        mph_calls.fetch_add(1, std::memory_order_relaxed);
        for (int k = 0; k < 6; ++k) {
            const uint64_t ns = static_cast<uint64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(mph_t[k + 1] - mph_t[k]).count());
            mph_sum[k].fetch_add(ns, std::memory_order_relaxed);
            int b = 0; uint64_t v = ns;
            while (v > 1 && b < 39) { v >>= 1; ++b; }
            mph_hist[k][b].fetch_add(1, std::memory_order_relaxed);
        }

        const int64_t now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        int64_t last = mph_last_print_ns.load(std::memory_order_relaxed);
        if (now_ns - last >= 10000000000LL &&
            mph_last_print_ns.compare_exchange_strong(last, now_ns)) {
            std::ostringstream os;
            os << "[ML-PHASE] calls=" << mph_calls.load();
            for (int k = 0; k < 6; ++k) {
                os << " " << mph_names[k] << "=" << mph_sum[k].load() << "|";
                bool first = true;
                for (int i = 0; i < 40; ++i) {
                    const uint64_t c = mph_hist[k][i].load(std::memory_order_relaxed);
                    if (c == 0) continue;
                    os << (first ? "" : ",") << i << ":" << c;
                    first = false;
                }
            }
            std::cout << os.str() << std::endl;
        }
    }
'''
src = src.replace(tail_anchor, block, 1)

shutil.copy(p, str(p) + ".bak_d283_phase")
p.write_text(src)
print("OK: [ML-PHASE] aplicado; copia en ring_consumer.cpp.bak_d283_phase")
