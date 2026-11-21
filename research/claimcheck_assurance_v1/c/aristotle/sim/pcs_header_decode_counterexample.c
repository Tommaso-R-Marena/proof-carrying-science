/* Counterexample for P2 and P3 of pcs_header_decode when `m` aliases `out`.
 *
 * The stated preconditions require that `out` does not overlap the *input* buffers,
 * and that `m` points to a valid size_t; they do not require `*m` to be disjoint from `out`.
 * Here `out` is the object representation of a real size_t object (cap = 8 = sizeof(size_t)
 * on x86-64), and `m` points to that same object.  Accessing a size_t object through
 * uint8_t lvalues is allowed by C's character-type aliasing rule, so no undefined behaviour
 * is involved.  `buf` is a separate array that holds the canonical header of eight 0xFF bytes.
 *
 * The decoder accepts the header, stores eight 0xFF bytes into out[0..8), then executes
 * `*m = len;`, which overwrites those same bytes with the representation of 8.
 * Result: return value L > 0 and *m = 8, but out[0..8) = 08 00 00 00 00 00 00 00 (little endian),
 * so buf[0..L) is NOT canon(out[0..*m)) (violates P2), and out[0..8) does not hold the data
 * d = FF x 8 that P3 requires.
 *
 * Build and run (from the project root, sources unchanged):
 *   cc -std=c99 -Wall -Wextra -fsanitize=address,undefined -I. sim/pcs_header_decode_counterexample.c pcs_srcbind.c -o /tmp/cex && /tmp/cex
 * Observed output (x86-64 Linux, gcc):
 *   returned L = 74, *m = 8
 *   out[0..8) = 08 00 00 00 00 00 00 00
 *   expected out[0..8) (P3) = ff ff ff ff ff ff ff ff
 *   P2/P3 VIOLATED: buf[0..L) is the canonical header of ff x 8, not of the final out bytes
 * Exit status 1; no sanitizer reports.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include "../../pcs_srcbind.h"

int main(void) {
    static const uint8_t pre[] = "open PCS.ClaimCheck\n\ndef pcs_src : Source := \xE2\x9F\xA8";
    static const uint8_t mid[] = "0xffffffffffffffff, 8";
    static const uint8_t suf[] = "\xE2\x9F\xA9\n\n";
    uint8_t buf[128];
    size_t n = 0;
    memcpy(buf + n, pre, sizeof pre - 1); n += sizeof pre - 1;   /* 48 bytes */
    memcpy(buf + n, mid, sizeof mid - 1); n += sizeof mid - 1;   /* "0x" + 16 hex + ", 8" */
    memcpy(buf + n, suf, sizeof suf - 1); n += sizeof suf - 1;   /* 5 bytes */

    size_t obj = 12345;                       /* a real, writable size_t object */
    uint8_t *out = (uint8_t *)&obj;           /* out: its 8 bytes, cap = 8 */
    size_t *m = &obj;                         /* m: the same object */

    size_t L = pcs_header_decode(buf, n, out, sizeof obj, m);
    size_t mv = obj;                          /* *m after the call */
    printf("returned L = %zu, *m = %zu\n", L, mv);
    printf("out[0..8) =");
    for (int i = 0; i < 8; i++) printf(" %02x", out[i]);
    printf("\nexpected out[0..8) (P3) = ff ff ff ff ff ff ff ff\n");

    int all_ff = 1;
    for (int i = 0; i < 8; i++) if (out[i] != 0xff) all_ff = 0;
    if (L > 0 && L == n && mv == 8 && !all_ff) {
        printf("P2/P3 VIOLATED: buf[0..L) is the canonical header of ff x 8, not of the final out bytes\n");
        return 1;
    }
    printf("no violation observed\n");
    return 0;
}
