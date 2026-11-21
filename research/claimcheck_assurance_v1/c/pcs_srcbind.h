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

/* Result of pcs_header_decode.  header == 0 means rejected, and then data == 0. */
typedef struct {
    size_t header; /* size in bytes of the canonical header at the start of buf; 0 if rejected */
    size_t data;   /* number of data bytes stored in out[0..data); 0 if rejected */
} pcs_decoded;

/* Strict decoder, in two passes.
 *
 * Pass 1 reads buf[0..n) and decides, without writing anything, whether buf begins with the
 * canonical header of some data d with |d| <= cap and |d| <= PCS_MAX_DATA.  If it does not, the call
 * returns {0, 0} and out is not written at all.  If it does, pass 2 stores d in out[0..|d|) and the
 * call returns {size of that header, |d|}.  No byte outside out[0..|d|) is ever written.
 *
 * Requires:
 *   - buf readable for n bytes (buf may be anything if n == 0);
 *   - out writable for cap bytes (out may be anything if cap == 0); the decoder never writes more
 *     than min(cap, PCS_MAX_DATA) bytes;
 *   - buf[0..n) and out[0..cap) do not overlap, and neither is modified by anything else during the
 *     call (both live for the whole call, no concurrent access).
 * The only output is out; both lengths come back by value, so there is no length pointer that could
 * alias out (the hazard of the first version, found by Aristotle, see ARISTOTLE_RESULTS.md and
 * aristotle/sim/).  The non-overlap of input and output is the usual condition of a decoder
 * (memcpy has the same one): pass 2 reads two hex digits for each byte it writes, so an out that
 * overlaps the hex digits not yet read would overwrite input before it is decoded, and an out that
 * overlaps the rest of the header would change the bytes the caller later compares with canon(d).
 * In-place decoding is therefore not supported. */
pcs_decoded pcs_header_decode(const uint8_t *buf, size_t n, uint8_t *out, size_t cap);

#endif
