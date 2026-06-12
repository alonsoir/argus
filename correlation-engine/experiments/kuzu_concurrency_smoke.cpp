// kuzu_concurrency_smoke.cpp — ADR-057 Fase 0 · DEBT-KUZU-CONCURRENCY-SMOKE-001
// aRGus NDR — DAY 182. Authors: Alonso Isidoro Roman + Claude (Anthropic).
//
// "Medir, no votar". Escenario NDR real: grafo inicial + RIADA DE UPSERTS write-heavy,
// lecturas esporadicas (ratio 10/100/1000+). Mide UPSERTS/s y aisla la palanca REAL:
//
//   batch = filas por query() via UNWIND (1 = MERGE por fila = sink ACTUAL; K = UNWIND de K).
//   Una sola query() con UNWIND de K filas = 1 plan + 1 commit para K upserts. Mata el
//   overhead por-query() (parse/plan) Y el fsync por fila. Es la estrategia de produccion.
//   writers = 1 vs N (Kuzu serializa escrituras; multi-writer NO deberia escalar -> Vela).
//
//   [A] writers (upsert UNWIND, particion disjunta) + 1 lector acoplado a ratio. SIEMPRE corre.
//   [B] Lock: (b1) 2o PROCESO debe FALLAR; (b2) in-process ABRE (footgun).
//   [C] MONOTONIA del reloj de ingesta.
//
// INVARIANTE: BD en fs NATIVO del guest. NUNCA /vagrant (vboxsf rompe mmap).
// Uso: <dur_s> <n_writers> <batch> <writes_per_read> <init_nodes> <db_path>
//      defaults: 5 1 1000 100 100000 /tmp/argus_kuzu_smoke.kuzu
//      --try-open <db_path>   -> exit 0 si abre, 2 si lock
#include "correlation_engine/ingest_clock.hpp"

#include <kuzu.hpp>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <exception>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include <sys/wait.h>
#include <sys/resource.h>

using namespace std::chrono;
using kuzu::main::Connection;
using kuzu::main::Database;
using kuzu::main::SystemConfig;
using argus::correlation::ingest_now_ns;

namespace {

constexpr const char* kSchema =
    "CREATE NODE TABLE IF NOT EXISTS NetworkFlow ("
    "flow_uid STRING, node_id STRING, community_id STRING, flow_start_window UINT64, "
    "seq_in_window UINT32 DEFAULT 0, ingested_at UINT64, temporal_anomaly BOOLEAN DEFAULT false, "
    "PRIMARY KEY (flow_uid));";

uint64_t mono_ns() {
    return static_cast<uint64_t>(
        duration_cast<nanoseconds>(steady_clock::now().time_since_epoch()).count());
}
double pct(std::vector<uint64_t>& v, double p) {
    if (v.empty()) return 0.0;
    std::sort(v.begin(), v.end());
    return static_cast<double>(v[static_cast<size_t>((v.size() - 1) * p)]);
}
double meanv(const std::vector<uint64_t>& v) {
    if (v.empty()) return 0.0;
    long double s = 0; for (auto x : v) s += x; return static_cast<double>(s / v.size());
}
bool try_open(const std::string& path, std::string& err) {
    try { SystemConfig cfg; Database probe(path, cfg); return true; }
    catch (const std::exception& e) { err = e.what(); return false; }
}
// Limpia TODOS los artefactos de Kuzu (no solo el .kuzu): un Ctrl-C deja un WAL
// huerfano que al reabrir revienta con 'unordered_map::at'. Kuzu 0.11.3 = BD single-file.
void cleanup_db(const std::string& p) {
    for (const char* sfx : {"", ".wal", ".wal.shadow", ".shadow", ".lock", ".tmp"})
        std::remove((p + sfx).c_str());
}
// 1 fila: MERGE por fila (= sink ACTUAL). Baseline de overhead por-query().
std::string merge_one(uint64_t key, uint64_t now) {
    const std::string k = std::to_string(key), n = std::to_string(now);
    return "MERGE (f:NetworkFlow {flow_uid:'init-" + k + "'}) "
           "ON CREATE SET f.node_id='n', f.community_id='c', f.flow_start_window=" + k +
           ", f.seq_in_window=0, f.ingested_at=" + n + ", f.temporal_anomaly=false "
           "ON MATCH SET f.ingested_at=" + n + ", f.temporal_anomaly=false, f.seq_in_window=f.seq_in_window+1";
}
// K filas: UNWIND [...] AS fid MERGE. 1 query() = K upserts. Estrategia de produccion.
std::string merge_unwind(const std::vector<uint64_t>& keys, uint64_t now) {
    const std::string n = std::to_string(now);
    std::string q = "UNWIND [";
    for (size_t i = 0; i < keys.size(); ++i) { if (i) q += ","; q += "'init-" + std::to_string(keys[i]) + "'"; }
    q += "] AS fid MERGE (f:NetworkFlow {flow_uid: fid}) "
         "ON CREATE SET f.node_id='n', f.community_id='c', f.flow_start_window=0, "
         "f.seq_in_window=0, f.ingested_at=" + n + ", f.temporal_anomaly=false "
         "ON MATCH SET f.ingested_at=" + n + ", f.temporal_anomaly=false, f.seq_in_window=f.seq_in_window+1";
    return q;
}

int run_smoke(int dur_s, int nw, int batch, int wpr, int init_nodes,
              const std::string& db_path, const char* self) {
    std::printf("=== KUZU UPSERT SMOKE — ADR-057 Fase 0 (DAY 182) ===\n");
    std::printf("db_path: %s  (fs NATIVO del guest, NO vboxsf)\n", db_path.c_str());
    std::printf("config : dur=%ds writers=%d batch=%d(rows/query) writes_per_read=%d init_nodes=%d (~%d:1)\n\n",
                dur_s, nw, batch, wpr, init_nodes, wpr);
    cleanup_db(db_path);

    // ── [C] Monotonia ────────────────────────────────────────────────────────
    {
        const int N = 2'000'000;
        uint64_t prev = ingest_now_ns(), back = 0, worst = 0;
        for (int i = 0; i < N; ++i) { const uint64_t now = ingest_now_ns();
            if (now < prev) { ++back; worst = std::max(worst, prev - now); } prev = now; }
        std::printf("[C] Monotonia NTP: muestras=%d retrocesos=%llu max_ns=%llu -> %s\n\n",
                    N, (unsigned long long)back, (unsigned long long)worst,
                    back == 0 ? "monotono en reposo" : "OJO retroceso (NTP step)");
    }

    SystemConfig cfg;
    Database db(db_path, cfg);
    { Connection ddl(&db); auto r = ddl.query(kSchema);
      if (!r->isSuccess()) { std::printf("DDL fallo: %s\n", r->getErrorMessage().c_str()); return 1; } }

    // ── [B] Lock ──────────────────────────────────────────────────────────────
    std::printf("[B] Lock de fichero (Kuzu: lock de PROCESO):\n");
    bool cross_rejected = false, cross_inconclusive = false; int cross_code = -1;
    {
        const std::string cmd = std::string(self) + " --try-open " + db_path + " >/dev/null 2>&1";
        const int rc = std::system(cmd.c_str());
        if (rc == -1) cross_inconclusive = true;
        else { cross_code = WIFEXITED(rc) ? WEXITSTATUS(rc) : -1; cross_rejected = (cross_code == 2); }
        std::printf("    (b1) 2o PROCESO: %s (exit=%d)\n",
                    cross_inconclusive ? "INCONCLUSO" : cross_rejected ? "RECHAZADO (esperado)"
                    : cross_code == 0 ? "ABRIO (!!)" : "inconcluso", cross_code);
    }
    { std::string err; const bool in_op = try_open(db_path, err);
      std::printf("    (b2) 2o Database in-process: %s\n",
                  in_op ? "ABRIO -> footgun (un Database, N Connections)" : ("RECHAZADO: " + err).c_str()); }
    if (cross_inconclusive) std::printf("    -> cross-proceso INCONCLUSO.\n\n");
    else if (!cross_rejected) { std::printf("    -> FALLO DURO: sin lock cross-proceso. PARAR.\n\n"); return 3; }
    else std::printf("    -> CONFIRMA: lock CROSS-PROCESO. Multi-proceso => servicio in-process unico.\n\n");

    // ── Fase 0: GRAFO INICIAL via UNWIND (rapido; en prod = COPY FROM gold.parquet) ──
    {
        Connection c(&db);
        const auto t0 = steady_clock::now();
        const uint64_t CH = 10000;
        std::vector<uint64_t> keys; keys.reserve(CH);
        for (uint64_t k = 0; k < (uint64_t)init_nodes; ) {
            keys.clear();
            for (uint64_t j = 0; j < CH && k < (uint64_t)init_nodes; ++j, ++k) keys.push_back(k);
            auto r = c.query(merge_unwind(keys, ingest_now_ns()));
            if (!r->isSuccess()) { std::printf("init fallo: %s\n", r->getErrorMessage().c_str()); return 1; }
        }
        const double s = duration_cast<milliseconds>(steady_clock::now() - t0).count() / 1000.0;
        int64_t n0 = -1; auto r = c.query("MATCH (n:NetworkFlow) RETURN count(*)");
        if (r->isSuccess() && r->hasNext()) n0 = std::stoll(r->getNext()->toString());
        std::printf("graph inicial: %lld nodos en %.2fs (UNWIND; prod = COPY FROM)\n\n", (long long)n0, s);
    }

    // ── [A] baseline lectura ──────────────────────────────────────────────────
    std::vector<uint64_t> base_lat;
    { Connection c(&db); const auto until = steady_clock::now() + milliseconds(500);
      while (steady_clock::now() < until) { const uint64_t t0 = mono_ns();
          auto r = c.query("MATCH (n:NetworkFlow) RETURN count(*)"); const uint64_t t1 = mono_ns();
          if (r->isSuccess()) base_lat.push_back(t1 - t0); } }

    // ── [A] RIADA DE UPSERTS ──────────────────────────────────────────────────
    std::atomic<bool> stop{false};
    std::atomic<uint64_t> ups{0}, w_err{0}, reads{0}, r_err{0};
    std::vector<uint64_t> load_lat;
    std::vector<std::vector<uint64_t>> w_lat(nw);  // lat por query() de cada writer
    std::vector<std::string> w_sample(nw);          // 1er mensaje de error por writer
    const uint64_t chunk = std::max<uint64_t>(1, (uint64_t)init_nodes / (uint64_t)nw);

    std::vector<std::thread> wts;
    for (int t = 0; t < nw; ++t) {
        wts.emplace_back([&, t] {
            const uint64_t base = (uint64_t)t * chunk;
            if (base >= (uint64_t)init_nodes) return;
            const uint64_t span = (t == nw - 1) ? ((uint64_t)init_nodes - base) : chunk;
            Connection c(&db);
            uint64_t j = 0;
            std::vector<uint64_t> keys; keys.reserve(batch);
            auto& wl = w_lat[t];
            while (!stop.load(std::memory_order_relaxed)) {
                keys.clear();
                for (int k = 0; k < batch; ++k) { keys.push_back(base + (j % span)); ++j; }
                const std::string stmt = (batch == 1) ? merge_one(keys[0], ingest_now_ns())
                                                       : merge_unwind(keys, ingest_now_ns());
                const uint64_t qt0 = mono_ns();
                auto r = c.query(stmt);
                const uint64_t qt1 = mono_ns();
                if (r->isSuccess()) { ups.fetch_add(keys.size(), std::memory_order_relaxed); wl.push_back(qt1 - qt0); }
                else { w_err.fetch_add(keys.size(), std::memory_order_relaxed);
                       if (w_sample[t].empty()) w_sample[t] = r->getErrorMessage(); }
            }
        });
    }

    std::thread reader([&] {
        Connection c(&db); uint64_t last = 0;
        while (!stop.load(std::memory_order_relaxed)) {
            const uint64_t u = ups.load(std::memory_order_relaxed);
            if (u - last >= (uint64_t)wpr) {
                const uint64_t t0 = mono_ns();
                auto r = c.query("MATCH (n:NetworkFlow) RETURN count(*)");
                const uint64_t t1 = mono_ns();
                if (r->isSuccess()) { reads.fetch_add(1, std::memory_order_relaxed); load_lat.push_back(t1 - t0); }
                else                  r_err.fetch_add(1, std::memory_order_relaxed);
                last = u;
            } else std::this_thread::sleep_for(microseconds(200));
        }
    });

    std::this_thread::sleep_for(seconds(dur_s));
    stop.store(true);
    for (auto& th : wts) th.join();
    reader.join();

    int64_t nodes = -1;
    { Connection c(&db); auto r = c.query("MATCH (n:NetworkFlow) RETURN count(*)");
      if (r->isSuccess() && r->hasNext()) nodes = std::stoll(r->getNext()->toString()); }

    const double bp50 = pct(base_lat, 0.50), bp99 = pct(base_lat, 0.99);
    const double lp50 = pct(load_lat, 0.50), lp99 = pct(load_lat, 0.99);
    const uint64_t U = ups.load(), R = reads.load();
    const double ratio = R ? (double)U / (double)R : 0.0;
    const bool node_count_ok = ((uint64_t)nodes == (uint64_t)init_nodes);

    std::printf("[A] RIADA UPSERTS: %d writers (batch=%d rows/query) + 1 reader (ratio %d:1):\n", nw, batch, wpr);
    std::printf("    UPSERTS commit=%llu (%.0f/s)  errores=%llu\n",
                (unsigned long long)U, (double)U / dur_s, (unsigned long long)w_err.load());
    std::string w_smpl; for (auto& s : w_sample) if (!s.empty()) { w_smpl = s; break; }
    if (w_err.load() > 0)
        std::printf("    %s: %llu  (ejemplo: %.140s)\n",
                    (nw > 1) ? "rechazos por conflicto write-tx (ESPERADO con N>1; Kuzu=1 write-tx)"
                             : "ERRORES de escritura (1 writer => fallo REAL)",
                    (unsigned long long)w_err.load(), w_smpl.c_str());
    std::vector<uint64_t> all_w; for (auto& v : w_lat) all_w.insert(all_w.end(), v.begin(), v.end());
    const double wp50 = pct(all_w, 0.50), wp99 = pct(all_w, 0.99), wp999 = pct(all_w, 0.999), wmean = meanv(all_w);
    std::printf("    query()-lat escritura: p50=%.0fns p99=%.0fns p999=%.0fns mean=%.0fns (%zu queries)\n",
                wp50, wp99, wp999, wmean, all_w.size());
    std::printf("    por upsert (amortizado = lat/batch): p50=%.0fns mean=%.0fns\n",
                wp50 / batch, wmean / batch);
    std::printf("    reads          =%llu (%.0f/s)  errores=%llu  ratio_real = %.0f:1\n",
                (unsigned long long)R, (double)R / dur_s, (unsigned long long)r_err.load(), ratio);
    std::printf("    lat lectura baseline: p50=%.0fns p99=%.0fns\n", bp50, bp99);
    std::printf("    lat lectura carga   : p50=%.0fns p99=%.0fns\n", lp50, lp99);
    if (bp50 > 0 && bp99 > 0)
        std::printf("    contencion          : p50 x%.2f  p99 x%.2f\n", lp50 / bp50, lp99 / bp99);
    std::printf("    upsert real (no insert): nodos==init_nodes (%lld==%d) %s\n",
                (long long)nodes, init_nodes, node_count_ok ? "OK" : "MISMATCH");

    struct rusage ru; getrusage(RUSAGE_SELF, &ru);
    std::printf("    pico de memoria (maxRSS): %.1f MB\n", ru.ru_maxrss / 1024.0);

    const bool w_ok = (nw > 1) ? true : (w_err.load() == 0);  // N>1: conflictos write-tx esperados
    const bool ok = (r_err.load() == 0) && w_ok && node_count_ok;
    std::printf("\nVEREDICTO [A]: %s\n", ok
        ? ((nw > 1)
           ? "consistente; multi-writer NO escala (rechazos por single write-tx). UNWIND+1 writer es el patron."
           : "upsert consistente; compara UPSERTS/s batch=1 vs batch=K (UNWIND) para la decision Vela.")
        : "FALLO: r_err, w_err(1 writer), o nodos!=init -> revisar.");
    cleanup_db(db_path);
    return ok ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc >= 3 && std::string(argv[1]) == "--try-open") {
        std::string err; const bool opened = try_open(argv[2], err);
        std::printf("--try-open %s -> %s%s\n", argv[2],
                    opened ? "ABRIO (sin lock)" : "RECHAZADO (lock): ", opened ? "" : err.c_str());
        return opened ? 0 : 2;
    }
    const int dur   = argc > 1 ? std::atoi(argv[1]) : 5;
    const int nw    = argc > 2 ? std::max(1, std::atoi(argv[2])) : 1;
    const int batch = argc > 3 ? std::max(1, std::atoi(argv[3])) : 1000;
    const int wpr   = argc > 4 ? std::max(1, std::atoi(argv[4])) : 100;
    const int init  = argc > 5 ? std::max(1, std::atoi(argv[5])) : 100000;
    const std::string path = argc > 6 ? argv[6] : "/tmp/argus_kuzu_smoke.kuzu";
    try { return run_smoke(dur, nw, batch, wpr, init, path, argv[0]); }
    catch (const std::exception& e) { std::printf("SMOKE EXCEPCION: %s\n", e.what()); return 1; }
}