// test_auto_isolate.cpp — ADR-042 IRP should_auto_isolate() unit tests
// DAY 143 — lógica de decisión pura, sin fork(), sin nftables, sin root
#include <gtest/gtest.h>
#include <fstream>
#include <filesystem>
#include <csignal>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <chrono>
#include <thread>
#include "firewall/batch_processor.hpp"
#include "firewall/config_loader.hpp"
#include "firewall/ipset_wrapper.hpp"

using namespace mldefender::firewall;

namespace {

IrpConfig make_irp(bool auto_isolate = true,
                   double threshold = 0.95,
                   std::vector<std::string> types = {"ransomware","lateral_movement","c2_beacon"}) {
    IrpConfig cfg;
    cfg.auto_isolate             = auto_isolate;
    cfg.threat_score_threshold   = threshold;
    cfg.auto_isolate_event_types = std::move(types);
    cfg.isolate_interface        = "eth1";
    cfg.isolate_binary_path      = "/usr/local/bin/argus-network-isolate";
    cfg.isolate_config_path      = "/etc/ml-defender/firewall-acl-agent/isolate.json";
    return cfg;
}

protobuf::Detection make_detection(protobuf::DetectionType type, float confidence) {
    protobuf::Detection d;
    d.set_type(type);
    d.set_confidence(confidence);
    d.set_src_ip("192.168.1.100");
    return d;
}

class AutoIsolateTest : public ::testing::Test {
protected:
    void SetUp() override {
        BatchProcessorConfig cfg;
        cfg.confidence_threshold = 0.5f;
        processor_ = std::make_unique<BatchProcessor>(ipset_, cfg);
    }
    IPSetWrapper ipset_;
    std::unique_ptr<BatchProcessor> processor_;
};

// ── TEST 1: dispara con score >= threshold y tipo correcto ────────────────
TEST_F(AutoIsolateTest, TriggersOnRansomwareHighScore) {
    processor_->set_irp_config(make_irp());
    auto d = make_detection(protobuf::DetectionType::DETECTION_RANSOMWARE, 0.97f);
    EXPECT_TRUE(processor_->should_auto_isolate(d));
}

TEST_F(AutoIsolateTest, TriggersOnInternalThreatHighScore) {
    processor_->set_irp_config(make_irp());
    auto d = make_detection(protobuf::DetectionType::DETECTION_INTERNAL_THREAT, 0.96f);
    EXPECT_TRUE(processor_->should_auto_isolate(d));
}

TEST_F(AutoIsolateTest, TriggersOnSuspiciousTrafficHighScore) {
    processor_->set_irp_config(make_irp());
    auto d = make_detection(protobuf::DetectionType::DETECTION_SUSPICIOUS_TRAFFIC, 0.95f);
    EXPECT_TRUE(processor_->should_auto_isolate(d));
}

// ── TEST 2: NO dispara con score < threshold ──────────────────────────────
TEST_F(AutoIsolateTest, NoTriggerOnLowScore) {
    processor_->set_irp_config(make_irp());
    auto d = make_detection(protobuf::DetectionType::DETECTION_RANSOMWARE, 0.94f);
    EXPECT_FALSE(processor_->should_auto_isolate(d));
}

TEST_F(AutoIsolateTest, NoTriggerOnScoreExactlyBelowThreshold) {
    processor_->set_irp_config(make_irp(true, 0.95));
    auto d = make_detection(protobuf::DetectionType::DETECTION_RANSOMWARE, 0.9499f);
    EXPECT_FALSE(processor_->should_auto_isolate(d));
}

// ── TEST 3: NO dispara con tipo no mapeado ────────────────────────────────
TEST_F(AutoIsolateTest, NoTriggerOnDDoS) {
    processor_->set_irp_config(make_irp());
    auto d = make_detection(protobuf::DetectionType::DETECTION_DDOS, 0.99f);
    EXPECT_FALSE(processor_->should_auto_isolate(d));
}

TEST_F(AutoIsolateTest, NoTriggerOnUnknown) {
    processor_->set_irp_config(make_irp());
    auto d = make_detection(protobuf::DetectionType::DETECTION_UNKNOWN, 0.99f);
    EXPECT_FALSE(processor_->should_auto_isolate(d));
}

// ── TEST 4: NO dispara cuando auto_isolate=false ──────────────────────────
TEST_F(AutoIsolateTest, NoTriggerWhenDisabled) {
    processor_->set_irp_config(make_irp(false));
    auto d = make_detection(protobuf::DetectionType::DETECTION_RANSOMWARE, 0.99f);
    EXPECT_FALSE(processor_->should_auto_isolate(d));
}

// ── TEST 5: NO dispara cuando lista de tipos vacía ────────────────────────
TEST_F(AutoIsolateTest, NoTriggerOnEmptyEventTypes) {
    processor_->set_irp_config(make_irp(true, 0.95, {}));
    auto d = make_detection(protobuf::DetectionType::DETECTION_RANSOMWARE, 0.99f);
    EXPECT_FALSE(processor_->should_auto_isolate(d));
}

// ── TEST 6: score exactamente en el umbral dispara ────────────────────────
TEST_F(AutoIsolateTest, TriggersOnExactThreshold) {
    processor_->set_irp_config(make_irp(true, 0.95));
    auto d = make_detection(protobuf::DetectionType::DETECTION_RANSOMWARE, 0.95f);
    EXPECT_TRUE(processor_->should_auto_isolate(d));
}

// ── TEST INTEGRACIÓN: fork()+execv() se lanza con evento sintético ──────────
// Usa /bin/true como binario sintético — verifica que el hijo se lanzó
// y terminó con exit 0. No ejecuta argus-network-isolate real.
TEST_F(AutoIsolateTest, IntegrationForkExecOnSyntheticEvent) {
    IrpConfig irp = make_irp();
    irp.isolate_binary_path = "/bin/true";  // binario sintético seguro
    irp.isolate_config_path = "/tmp/test_isolate_synthetic.json";
    processor_->set_irp_config(irp);

    // Evento sintético: score >= 0.95 + ransomware
    auto d = make_detection(protobuf::DetectionType::DETECTION_RANSOMWARE, 0.97f);

    // Registrar PIDs de hijos antes del disparo
    pid_t before = getpid();

    // Disparar — debe hacer fork()+execv(/bin/true)
    processor_->check_auto_isolate(d);

    // Esperar hasta 2 segundos a que el hijo termine
    bool child_exited = false;
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
    while (std::chrono::steady_clock::now() < deadline) {
        int status = 0;
        pid_t result = waitpid(-1, &status, WNOHANG);
        if (result > 0 && WIFEXITED(status) && WEXITSTATUS(status) == 0) {
            child_exited = true;
            break;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    EXPECT_TRUE(child_exited) << "fork()+execv(/bin/true) no lanzó hijo o no terminó con exit 0";
    (void)before;
}

// ── TEST INTEGRACIÓN: NO fork cuando score bajo ───────────────────────────
TEST_F(AutoIsolateTest, IntegrationNoForkOnLowScore) {
    IrpConfig irp = make_irp();
    irp.isolate_binary_path = "/bin/true";
    processor_->set_irp_config(irp);

    auto d = make_detection(protobuf::DetectionType::DETECTION_RANSOMWARE, 0.80f);
    processor_->check_auto_isolate(d);

    // Esperar 200ms — no debe haber hijo
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    int status = 0;
    pid_t result = waitpid(-1, &status, WNOHANG);
    EXPECT_LE(result, 0) << "fork() no debería haberse llamado con score bajo";
}

} // namespace

// ═══════════════════════════════════════════════════════════════════════════
// DEBT-IRP-AUTOISO-FALSE-001 — parse_irp() única fuente de verdad
// DEBT-IRP-SIGCHLD-001       — SA_NOCLDWAIT, cero zombies
// ═══════════════════════════════════════════════════════════════════════════

// ── TEST 13: struct default es false — sin leer ningún JSON ───────────────
TEST(IrpConfigDefaultTest, DefaultStructIsFalse) {
    IrpConfig cfg;
    EXPECT_FALSE(cfg.auto_isolate)
        << "IrpConfig default debe ser false — Consejo 8/8 unanime (DEBT-IRP-AUTOISO-FALSE-001)";
}

// ── TEST 14: fichero ausente → exception con ruta en mensaje ──────────────
TEST(ParseIrpTest, FileMissingThrows) {
    const std::string path = "/tmp/argus_test_nonexistent_isolate.json";
    ::unlink(path.c_str());
    EXPECT_THROW({
        ConfigLoader::parse_irp(path);
    }, std::runtime_error) << "fichero ausente debe lanzar runtime_error";

    try {
        ConfigLoader::parse_irp(path);
    } catch (const std::runtime_error& e) {
        EXPECT_NE(std::string(e.what()).find(path), std::string::npos)
            << "mensaje de error debe contener la ruta";
    } catch (...) {}
}

// ── TEST 15: campo auto_isolate ausente en JSON → exception ───────────────
TEST(ParseIrpTest, MissingFieldThrows) {
    const std::string path = "/tmp/argus_test_missing_field.json";
    {
        std::ofstream f(path);
        f << R"({"nft_path":"/usr/sbin/nft","rollback_timeout_sec":300,)"
          << R"("table_name":"argus_isolate","whitelist_ips":[],"whitelist_ports":[22]})";
    }
    EXPECT_THROW({
        ConfigLoader::parse_irp(path);
    }, std::runtime_error) << "auto_isolate ausente debe lanzar runtime_error";
    ::unlink(path.c_str());
}

// ── TEST 16: auto_isolate: false en JSON → false en struct ────────────────
TEST(ParseIrpTest, ExplicitFalseIsRespected) {
    const std::string path = "/tmp/argus_test_explicit_false.json";
    {
        std::ofstream f(path);
        f << R"({"auto_isolate":false,"nft_path":"/usr/sbin/nft","rollback_timeout_sec":300,)"
          << R"("table_name":"argus_isolate","whitelist_ips":[],"whitelist_ports":[22]})";
    }
    auto cfg = ConfigLoader::parse_irp(path);
    EXPECT_FALSE(cfg.auto_isolate) << "auto_isolate: false en JSON debe producir false";
    ::unlink(path.c_str());
}

// ── TEST 17: auto_isolate: true en JSON → true en struct (opt-in funciona) ─
TEST(ParseIrpTest, ExplicitTrueIsRespected) {
    const std::string path = "/tmp/argus_test_explicit_true.json";
    {
        std::ofstream f(path);
        f << R"({"auto_isolate":true,"nft_path":"/usr/sbin/nft","rollback_timeout_sec":300,)"
          << R"("table_name":"argus_isolate","whitelist_ips":[],"whitelist_ports":[22]})";
    }
    auto cfg = ConfigLoader::parse_irp(path);
    EXPECT_TRUE(cfg.auto_isolate) << "auto_isolate: true en JSON debe producir true — opt-in funciona";
    ::unlink(path.c_str());
}

// ── TEST 18: SA_NOCLDWAIT — N forks con /bin/true → cero zombies ──────────
TEST(SigchldTest, NoZombiesAfterNForks) {
    // SA_NOCLDWAIT ya instalado por setup_signal_handlers() en producción.
    // Aquí lo instalamos explícitamente para aislar el test.
    struct sigaction sa{};
    sa.sa_handler = SIG_DFL;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_NOCLDWAIT;
    sigaction(SIGCHLD, &sa, nullptr);

    constexpr int N = 20;
    for (int i = 0; i < N; ++i) {
        pid_t pid = fork();
        if (pid == 0) {
            // Hijo — ejecutar /bin/true y salir
            char* argv[] = {const_cast<char*>("/bin/true"), nullptr};
            execv("/bin/true", argv);
            _exit(1);
        }
        ASSERT_GT(pid, 0) << "fork() falló en iteración " << i;
    }

    // Esperar a que todos los hijos terminen
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // Verificar cero zombies en /proc
    int zombies = 0;
    for (const auto& entry : std::filesystem::directory_iterator("/proc")) {
        std::string status_path = entry.path().string() + "/status";
        std::ifstream sf(status_path);
        std::string line;
        while (std::getline(sf, line)) {
            if (line.find("State:") != std::string::npos &&
                line.find('Z') != std::string::npos) {
                ++zombies;
            }
        }
    }
    EXPECT_EQ(zombies, 0) << "SA_NOCLDWAIT debe evitar zombies — encontrados: " << zombies;
}
