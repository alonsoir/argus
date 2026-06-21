// test_comment_validator.cpp — DAY191 · H-2 NÚCLEO 2 (CWE-93 ipset comment injection)
//
// Regresión VERSION-INDEPENDIENTE: prueba la frontera is_valid_comment, NO el parser
// de ipset (cuya indulgencia varía v7.17 vs v7.19). Sin root, sin kernel.
#include <gtest/gtest.h>
#include <string>
#include "firewall/comment_validator.hpp"

using mldefender::firewall::is_valid_comment;

// El payload DEMOSTRADO inyectando 66.66.66.66 en Bookworm ipset v7.17.
TEST(CommentValidator, RejectsDemonstratedBreakoutPayload) {
    EXPECT_FALSE(is_valid_comment("x\"\nadd h2probe 66.66.66.66 comment \"y"));
}
TEST(CommentValidator, RejectsNewlineAndCarriageReturn) {
    EXPECT_FALSE(is_valid_comment("pre\nadd evil 9.9.9.9"));
    EXPECT_FALSE(is_valid_comment("a\rb"));
}
TEST(CommentValidator, RejectsQuoteAndBackslash) {
    EXPECT_FALSE(is_valid_comment("a\"b"));
    EXPECT_FALSE(is_valid_comment("a\\b"));
}
TEST(CommentValidator, RejectsOtherControlChars) {
    EXPECT_FALSE(is_valid_comment(std::string("a\0b", 3)));  // NUL embebido
    EXPECT_FALSE(is_valid_comment("a\tb"));
    EXPECT_FALSE(is_valid_comment("a\x7f""b"));              // DEL
}
TEST(CommentValidator, RejectsOverlong) {
    EXPECT_FALSE(is_valid_comment(std::string(256, 'a')));
    EXPECT_TRUE(is_valid_comment(std::string(255, 'a')));
}
TEST(CommentValidator, AcceptsLegitimate) {
    EXPECT_TRUE(is_valid_comment("blocked by autonomy reactor 2026-06-21"));
    EXPECT_TRUE(is_valid_comment("ASN-1234 :: c2.example -> drop"));
    EXPECT_TRUE(is_valid_comment(""));  // comment vacío opcional: válido
}
