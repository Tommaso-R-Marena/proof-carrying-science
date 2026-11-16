/* Canonical source header of a ClaimCheck proof file.  Research code, no PCS v0.6 authority.
 *
 * A ClaimCheck proof file is   CHECKER || MARKER || TAIL .  TAIL begins with the header that binds
 * the data file's bytes into the Lean statement:
 *
 *     open PCS.ClaimCheck\n
 *     \n
 *     def pcs_src : Source := <0xHEX, DEC>\n        (the brackets are U+27E8 and U+27E9)
 *     \n
 *
 * For data d[0..m) the canonical header is the byte string
 *
 *     PREAMBLE || "0x" || HEX(d, m) || ", " || DEC(m) || SUFFIX
 *
 *   PREAMBLE = "open PCS.ClaimCheck\n\ndef pcs_src : Source := " followed by E2 9F A8
 *   HEX(d,m) = two lowercase hexadecimal digits per byte, first byte first; the one digit "0" if m = 0
 *   DEC(m)   = the decimal digits of m with no leading zero ("0" if m = 0)
 *   SUFFIX   = E2 9F A9 0A 0A
 *
 * This is exactly what research/claimcheck_v1/lean.py (batch_tail) writes.  Every data length up to
 * PCS_MAX_DATA has exactly one header, and nothing else is accepted by the decoder.
 */
#ifndef PCS_SRCBIND_H
#define PCS_SRCBIND_H

#include <stddef.h>
#include <stdint.h>

#define PCS_MAX_DATA 65536u

/* Size in bytes of the canonical header for m data bytes; 0 if m > PCS_MAX_DATA. */
size_t pcs_header_size(size_t m);

/* Writes the canonical header for d[0..m) into out[0..cap).
 * Returns its size.  Returns 0, and writes nothing, if m > PCS_MAX_DATA or the size exceeds cap.
 * Requires: d readable for m bytes, out writable for cap bytes. */
size_t pcs_header_encode(uint8_t *out, size_t cap, const uint8_t *d, size_t m);

/* Strict decoder.  If buf[0..n) begins with the canonical header of some data of at most cap bytes
 * (and at most PCS_MAX_DATA bytes), stores that data in out[0..*m), sets *m, and returns the header
 * size (> 0).  Otherwise returns 0; *m is then unspecified and out may have been partly written
 * (never beyond cap).
 * Requires: buf readable for n bytes, out writable for cap bytes, m a valid pointer, and the three
 * objects buf[0..n), out[0..cap) and *m pairwise disjoint.  The last condition matters: if m points
 * into out, the final store to *m overwrites decoded bytes and the call still succeeds (found by
 * Aristotle, see ARISTOTLE_RESULTS.md and aristotle/sim/). */
size_t pcs_header_decode(const uint8_t *buf, size_t n, uint8_t *out, size_t cap, size_t *m);

#endif
