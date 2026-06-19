// test_set_name_validator.cpp
// H-2 mov2: valida la allowlist standalone que protege add_batch/delete_batch.
// Unit (sin root) → entra en test-all → gatea EMECAS.
#include <gtest/gtest.h>
#include "firewall/set_name_validator.hpp"
using mldefender::firewall::is_valid_set_name;

TEST(SetNameValidator, AcceptsLegitimate) {
    EXPECT_TRUE(is_valid_set_name("blacklist"));
    EXPECT_TRUE(is_valid_set_name("argus-v1_2025"));
    EXPECT_TRUE(is_valid_set_name(std::string(31, 'a')));  // límite exacto
}
TEST(SetNameValidator, RejectsNewlineInjection) {
    EXPECT_FALSE(is_valid_set_name("x\nadd evil 6.6.6.6"));
    EXPECT_FALSE(is_valid_set_name("x\n"));
}
TEST(SetNameValidator, RejectsLeadingDash) {  // CWE-88
    EXPECT_FALSE(is_valid_set_name("-X"));
    EXPECT_FALSE(is_valid_set_name("-exist"));
    EXPECT_TRUE(is_valid_set_name("a-b"));      // '-' interior OK
}
TEST(SetNameValidator, RejectsEmptyAndTooLong) {
    EXPECT_FALSE(is_valid_set_name(""));
    EXPECT_FALSE(is_valid_set_name(std::string(32, 'a')));
}
TEST(SetNameValidator, RejectsShellAndControlChars) {
    EXPECT_FALSE(is_valid_set_name("set name"));
    EXPECT_FALSE(is_valid_set_name("a;b"));
    EXPECT_FALSE(is_valid_set_name(std::string("a\0b", 3)));  // NUL embebido
}
