#pragma once
// correlation-engine/include/correlation_engine/bronze_dir_watcher.hpp
// DAY 203 — DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001
//
// Vigila un directorio por segmentos bronce COMPLETOS. Semantica: IN_MOVED_TO
// sobre *.csv -- el writer (CorrelationWriter) cierra <basename>.csv.tmp y hace
// rename atomico (mismo filesystem) a <basename>.csv. El nombre final SOLO
// aparece en el directorio cuando el fichero ya es inmutable; nunca se ve un
// fichero a medio escribir.
//
// Sintaxis syscall pura (inotify_init1/poll/read), sin dependencias externas.
// Patron calcado de rag-ingester/CsvDirWatcher (DAY 69), reescrito aqui para no
// acoplar correlation-engine a un componente marcado para deprecar -- la logica
// en si (syscalls de inotify) no se deprecia, solo el binario de rag-ingester.
#include <string>
#include <functional>
#include <atomic>
#include <cstdint>

namespace argus::correlation {

class BronzeDirWatcher {
public:
    using SegmentCallback = std::function<void(const std::string& path)>;

    explicit BronzeDirWatcher(std::string dir_path, SegmentCallback callback);
    ~BronzeDirWatcher();

    BronzeDirWatcher(const BronzeDirWatcher&) = delete;
    BronzeDirWatcher& operator=(const BronzeDirWatcher&) = delete;

    // Bloqueante -- corre el loop en el hilo llamante hasta stop() (o Ctrl-C).
    // Lanza std::runtime_error si inotify_init1/inotify_add_watch fallan.
    void run();
    void stop();

    uint64_t segments_detected() const noexcept;

private:
    std::string       dir_path_;
    SegmentCallback    callback_;
    std::atomic<bool>  running_{false};
    std::atomic<uint64_t> segments_detected_{0};
    int inotify_fd_{-1};
};

} // namespace argus::correlation
