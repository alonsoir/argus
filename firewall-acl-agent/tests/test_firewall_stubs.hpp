#pragma once
// test_firewall_stubs.hpp — helpers compartidos entre tests del firewall
#include <string>
#include <vector>

struct StubExecutor {
    std::vector<std::string> cmds;
    int ret{0};
    int operator()(const std::string& cmd) {
        cmds.push_back(cmd);
        return ret;
    }
};
