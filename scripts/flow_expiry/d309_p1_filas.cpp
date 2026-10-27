// DAY309 — recalcula fuera de linea la etapa 2 de ddos_v2 (el MISMO bosque del ml-detector, ddos_v2_head.hpp) sobre
// cada fila de flujo del dataset DDoS de una corrida, para ver que filas da como ataque y con que rasgos.
// Limite: el CSV no guarda victim_state, asi que la etapa 1 se aproxima con la regla ratio >= K (la del estado
// Desconocido); con la victima BajoPresion el ml-detector la deja pasar siempre. Por eso se dan dos cuentas: bosque
// solo (sin etapa 1) y bosque con ratio >= K.
// Compilar (defender), en una linea:
//   g++ -std=c++20 -O2 -Wall -Wextra -Werror -I/vagrant/ml-detector/include /vagrant/logs/lab/day309/tools/d309_p1_filas.cpp -o /tmp/d309_p1
// Uso: /tmp/d309_p1 DATASET.csv [MAX_FILAS_LISTADAS]
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include "ml_defender/ddos_v2_head.hpp"

namespace v2 = ml_defender::ddos_v2;

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "uso: d309_p1 DATASET.csv [MAX_FILAS_LISTADAS]\n";
        return 2;
    }
    const long max_list = argc > 2 ? std::atol(argv[2]) : 40;
    std::ifstream in(argv[1]);
    if (!in) {
        std::cerr << "no se puede abrir " << argv[1] << "\n";
        return 2;
    }
    std::string line;
    std::getline(in, line);
    std::map<std::string, int> col;
    {
        std::stringstream ss(line);
        std::string tok;
        int i = 0;
        while (std::getline(ss, tok, ',')) col[tok] = i++;
    }
    const char* need[] = {"ts_ns", "src_ip", "dst_ip", "src_port", "dst_port", "proto", "event_kind", "syn_ack_ratio",
                          "mean_packet_size", "reflection_signature", "packet_size_entropy", "flow_packet_count",
                          "flow_completion_rate", "victim_rate_ratio"};
    for (const char* n : need) {
        if (!col.count(n)) {
            std::cerr << "falta la columna " << n << "\n";
            return 2;
        }
    }
    struct Cuenta { long filas = 0, bosque = 0, bosque_ratio = 0; };
    std::map<std::string, Cuenta> grupos;
    long listadas = 0, mal = 0;
    std::cout << "positivos del bosque (clase 1), por fila: ts_ns src:sport -> dst:dport proto | syn_ack size refl "
                 "entropia fpk completion ratio | p1 etapa1(ratio>=K)\n";
    while (std::getline(in, line)) {
        std::vector<std::string> c;
        std::stringstream ss(line);
        std::string tok;
        while (std::getline(ss, tok, ',')) c.push_back(tok);
        if (c.size() < col.size()) { ++mal; continue; }
        if (c[col["event_kind"]] != "0" || c[col["dst_ip"]] != "192.168.100.1") continue;
        auto f = [&](const char* n) { return static_cast<float>(std::strtod(c[col[n]].c_str(), nullptr)); };
        const v2::Input x{f("syn_ack_ratio"), f("mean_packet_size"), f("reflection_signature"),
                          f("packet_size_entropy"), f("flow_packet_count"), f("flow_completion_rate"),
                          f("victim_rate_ratio")};
        // bosque solo: se fuerza la etapa 1 con el estado BajoPresion (pasa siempre)
        const auto rb = v2::evaluate(x, v2::kTrainK, v2::EstadoVictima::BajoPresion);
        const bool e1 = static_cast<double>(x.victim_rate_ratio) >= v2::kTrainK;
        const std::string src = c[col["src_ip"]];
        const std::string g = (src == "192.168.100.50" ? "atq " : src == "192.168.100.51" ? "base " : "otro ") +
                              std::string(c[col["proto"]] == "6" ? "tcp" : c[col["proto"]] == "17" ? "udp" : c[col["proto"]]);
        auto& k = grupos[g];
        ++k.filas;
        if (rb.clase == 1) {
            ++k.bosque;
            if (e1) ++k.bosque_ratio;
            if (listadas < max_list) {
                ++listadas;
                std::printf("  %s %s:%s -> %s:%s %s | %.4g %.6g %.3g %.6g %.6g %.3g %.4g | %.4f %d\n",
                            c[col["ts_ns"]].c_str(), src.c_str(), c[col["src_port"]].c_str(), c[col["dst_ip"]].c_str(),
                            c[col["dst_port"]].c_str(), c[col["proto"]].c_str(), x.syn_ack_ratio, x.mean_packet_size,
                            x.reflection_signature, x.packet_size_entropy, x.flow_packet_count, x.flow_completion_rate,
                            x.victim_rate_ratio, rb.p1, e1 ? 1 : 0);
            }
        }
    }
    std::cout << "\nresumen por grupo: filas | positivos del bosque solo | positivos del bosque con ratio>=K\n";
    long tb = 0, tr = 0;
    for (const auto& [g, k] : grupos) {
        std::printf("  %-9s %6ld | %6ld | %6ld\n", g.c_str(), k.filas, k.bosque, k.bosque_ratio);
        tb += k.bosque;
        tr += k.bosque_ratio;
    }
    std::printf("  TOTAL     bosque=%ld bosque_con_ratio=%ld filas_mal_formadas=%ld\n", tb, tr, mal);
    return 0;
}
