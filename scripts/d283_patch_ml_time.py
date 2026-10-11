#!/usr/bin/env python3
# DAY283 D2 — [ML-TIME]: coste por llamada de run_ml_detection (solo observacion).
import sys, shutil, pathlib

p = pathlib.Path("/vagrant/sniffer/src/userspace/ring_consumer.cpp")
src = p.read_text()

if "[ML-TIME]" in src:
    print("YA PARCHEADO: nada que hacer"); sys.exit(0)

anchor = "    stats_.ml_detection_time_us += duration.count();\n"
n = src.count(anchor)
if n != 1:
    print(f"PARAR: ancla encontrada {n} veces (esperado 1)"); sys.exit(1)

block = anchor + r'''
    // DAY283 D2 — [ML-TIME] (solo observacion): llamadas, ns, max, histograma log2
    {
        static std::atomic<uint64_t> mlt_calls{0};
        static std::atomic<uint64_t> mlt_sum_ns{0};
        static std::atomic<uint64_t> mlt_max_ns{0};
        static std::atomic<uint64_t> mlt_hist[40];
        static std::atomic<int64_t>  mlt_last_print_ns{0};

        const uint64_t ns = static_cast<uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count());
        mlt_calls.fetch_add(1, std::memory_order_relaxed);
        mlt_sum_ns.fetch_add(ns, std::memory_order_relaxed);
        uint64_t prev_max = mlt_max_ns.load(std::memory_order_relaxed);
        while (ns > prev_max &&
               !mlt_max_ns.compare_exchange_weak(prev_max, ns, std::memory_order_relaxed)) {}
        int b = 0; uint64_t v = ns;
        while (v > 1 && b < 39) { v >>= 1; ++b; }
        mlt_hist[b].fetch_add(1, std::memory_order_relaxed);

        const int64_t now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        int64_t last = mlt_last_print_ns.load(std::memory_order_relaxed);
        if (now_ns - last >= 10000000000LL &&
            mlt_last_print_ns.compare_exchange_strong(last, now_ns)) {
            std::ostringstream os;
            os << "[ML-TIME] calls=" << mlt_calls.load()
               << " sum_ns=" << mlt_sum_ns.load()
               << " max_ns=" << mlt_max_ns.load() << " hist=";
            bool first = true;
            for (int i = 0; i < 40; ++i) {
                const uint64_t c = mlt_hist[i].load(std::memory_order_relaxed);
                if (c == 0) continue;
                os << (first ? "" : ",") << i << ":" << c;
                first = false;
            }
            std::cout << os.str() << std::endl;
        }
    }
'''
src = src.replace(anchor, block, 1)

if "#include <sstream>" not in src:
    first_inc = src.index("#include")
    src = src[:first_inc] + "#include <sstream>\n" + src[first_inc:]

shutil.copy(p, str(p) + ".bak_d283")
p.write_text(src)
print("OK: parche [ML-TIME] aplicado; copia en ring_consumer.cpp.bak_d283")
