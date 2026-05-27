#include <cstdint>
#include <string>
#include "../../src/core/safe_exec.hpp"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    std::string input(reinterpret_cast<const char*>(data), size);
    // No debe crashear — solo retornar true/false
    (void)validate_chain_name(input);
    (void)is_safe_for_exec(input);
    return 0;
}
