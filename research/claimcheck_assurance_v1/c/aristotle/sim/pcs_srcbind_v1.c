/* See pcs_srcbind.h.  Portable C99, no library calls, no dynamic memory, no global state. */
#include "pcs_srcbind.h"

#define PRE_LEN 49u
#define SUF_LEN 5u

/* "open PCS.ClaimCheck\n\ndef pcs_src : Source := " (45 bytes), U+27E8 (E2 9F A8), and the '0' of "0x" */
static const uint8_t PRE[PRE_LEN] = {
    'o', 'p', 'e', 'n', ' ', 'P', 'C', 'S', '.', 'C', 'l', 'a', 'i', 'm', 'C', 'h', 'e', 'c', 'k', '\n',
    '\n',
    'd', 'e', 'f', ' ', 'p', 'c', 's', '_', 's', 'r', 'c', ' ', ':', ' ', 'S', 'o', 'u', 'r', 'c', 'e', ' ', ':', '=', ' ',
    0xE2, 0x9F, 0xA8, '0'};
/* The last byte of PRE is the '0' of "0x"; the 'x' is written and checked separately. */

/* U+27E9 (E2 9F A9), newline, newline */
static const uint8_t SUF[SUF_LEN] = {0xE2, 0x9F, 0xA9, '\n', '\n'};

static const uint8_t HEXDIGIT[16] = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'};

/* Number of decimal digits of m (1 for m = 0).  m <= PCS_MAX_DATA, so at most 5. */
static size_t dec_digits(size_t m) {
    size_t k = 1;
    while (m >= 10) {
        m /= 10;
        k++;
    }
    return k;
}

/* Value of a lowercase hexadecimal digit, or 16 if c is not one. */
static unsigned hex_value(uint8_t c) {
    if (c >= '0' && c <= '9') return (unsigned)(c - '0');
    if (c >= 'a' && c <= 'f') return (unsigned)(c - 'a') + 10u;
    return 16u;
}

size_t pcs_header_size(size_t m) {
    size_t hex;
    if (m > PCS_MAX_DATA) return 0;
    hex = (m == 0) ? 1 : 2 * m;
    /* PRE (ends with '0') + 'x' + hex digits + ", " + decimal length + SUF */
    return PRE_LEN + 1 + hex + 2 + dec_digits(m) + SUF_LEN;
}

size_t pcs_header_encode(uint8_t *out, size_t cap, const uint8_t *d, size_t m) {
    size_t size = pcs_header_size(m);
    size_t i, p, k, v;
    if (size == 0 || size > cap) return 0;
    for (i = 0; i < PRE_LEN; i++) out[i] = PRE[i];
    p = PRE_LEN;
    out[p++] = 'x';
    if (m == 0) {
        out[p++] = '0';
    } else {
        for (i = 0; i < m; i++) {
            out[p++] = HEXDIGIT[d[i] >> 4];
            out[p++] = HEXDIGIT[d[i] & 15];
        }
    }
    out[p++] = ',';
    out[p++] = ' ';
    k = dec_digits(m);
    v = m;
    for (i = k; i > 0; i--) {
        out[p + i - 1] = (uint8_t)('0' + (v % 10));
        v /= 10;
    }
    p += k;
    for (i = 0; i < SUF_LEN; i++) out[p++] = SUF[i];
    return p;
}

size_t pcs_header_decode(const uint8_t *buf, size_t n, uint8_t *out, size_t cap, size_t *m) {
    size_t i, p, k, len, value, digits;
    unsigned hi, lo;

    if (n < PRE_LEN + 1) return 0;
    for (i = 0; i < PRE_LEN; i++) {
        if (buf[i] != PRE[i]) return 0;
    }
    p = PRE_LEN;
    if (buf[p] != 'x') return 0;
    p++;

    /* k = number of consecutive lowercase hexadecimal digits starting at p */
    k = 0;
    while (p + k < n && hex_value(buf[p + k]) < 16u) k++;

    if (k == 1) {
        if (buf[p] != '0') return 0; /* one digit is canonical only for the empty file */
        len = 0;
    } else {
        if (k == 0 || (k & 1u) != 0) return 0; /* two digits per byte, at least one byte */
        len = k / 2;
        if (len > PCS_MAX_DATA || len > cap) return 0;
        for (i = 0; i < len; i++) {
            hi = hex_value(buf[p + 2 * i]);
            lo = hex_value(buf[p + 2 * i + 1]);
            out[i] = (uint8_t)((hi << 4) | lo);
        }
    }
    p += k;

    if (n - p < 2) return 0;
    if (buf[p] != ',' || buf[p + 1] != ' ') return 0;
    p += 2;

    /* decimal length: no leading zero, value bounded while it is read, must equal len */
    value = 0;
    digits = 0;
    while (p < n && buf[p] >= '0' && buf[p] <= '9') {
        if (digits == 1 && value == 0) return 0; /* a leading zero */
        value = value * 10 + (size_t)(buf[p] - '0');
        if (value > PCS_MAX_DATA) return 0;
        digits++;
        p++;
    }
    if (digits == 0 || value != len) return 0;

    if (n - p < SUF_LEN) return 0;
    for (i = 0; i < SUF_LEN; i++) {
        if (buf[p + i] != SUF[i]) return 0;
    }
    p += SUF_LEN;

    *m = len;
    return p;
}
