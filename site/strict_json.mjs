// Small strict JSON parser for the PCS v0.6 canonicalization boundary.
// It preserves ordinary ECMAScript JSON values while rejecting duplicate object
// names before they can be collapsed by JSON.parse.

export class StrictJSONError extends Error {}

export function parseStrictJson(text) {
  if (typeof text !== "string") {
    throw new StrictJSONError("JSON input must be text");
  }

  let i = 0;
  const length = text.length;

  function fail(message) {
    throw new StrictJSONError(message + " at offset " + i);
  }

  function skipWhitespace() {
    while (
      i < length &&
      (text[i] === " " || text[i] === "\n" || text[i] === "\r" || text[i] === "\t")
    ) {
      i++;
    }
  }

  function parseString() {
    if (text[i] !== '"') fail("expected string");
    const start = i++;
    while (i < length) {
      const code = text.charCodeAt(i);
      if (code === 0x22) {
        i++;
        const token = text.slice(start, i);
        try {
          return JSON.parse(token);
        } catch {
          fail("invalid JSON string");
        }
      }
      if (code < 0x20) fail("unescaped control character in string");
      if (code === 0x5c) {
        i++;
        if (i >= length) fail("unterminated escape");
        const escape = text[i];
        if (escape === "u") {
          if (i + 4 >= length) fail("short Unicode escape");
          const hex = text.slice(i + 1, i + 5);
          if (!/^[0-9a-fA-F]{4}$/.test(hex)) fail("invalid Unicode escape");
          i += 5;
          continue;
        }
        if (!'"\\/bfnrt'.includes(escape)) fail("invalid escape");
        i++;
        continue;
      }
      i++;
    }
    fail("unterminated string");
  }

  function parseNumber() {
    const match = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(text.slice(i));
    if (!match) fail("invalid number");
    const token = match[0];
    i += token.length;
    const value = Number(token);
    if (!Number.isFinite(value)) fail("non-finite number is not permitted");
    return value;
  }

  function parseArray() {
    i++;
    const out = [];
    skipWhitespace();
    if (text[i] === "]") {
      i++;
      return out;
    }
    while (true) {
      out.push(parseValue());
      skipWhitespace();
      if (text[i] === ",") {
        i++;
        skipWhitespace();
        continue;
      }
      if (text[i] === "]") {
        i++;
        return out;
      }
      fail("expected ',' or ']'");
    }
  }

  function parseObject() {
    i++;
    const out = Object.create(null);
    const seen = new Set();
    skipWhitespace();
    if (text[i] === "}") {
      i++;
      return out;
    }
    while (true) {
      if (text[i] !== '"') fail("object key must be a string");
      const key = parseString();
      if (seen.has(key)) fail("duplicate JSON object key");
      seen.add(key);
      skipWhitespace();
      if (text[i] !== ":") fail("expected ':'");
      i++;
      skipWhitespace();
      out[key] = parseValue();
      skipWhitespace();
      if (text[i] === ",") {
        i++;
        skipWhitespace();
        continue;
      }
      if (text[i] === "}") {
        i++;
        return out;
      }
      fail("expected ',' or '}'");
    }
  }

  function parseValue() {
    skipWhitespace();
    if (i >= length) fail("unexpected end of input");
    const ch = text[i];
    if (ch === '"') return parseString();
    if (ch === "{") return parseObject();
    if (ch === "[") return parseArray();
    if (ch === "-" || (ch >= "0" && ch <= "9")) return parseNumber();
    if (text.startsWith("true", i)) {
      i += 4;
      return true;
    }
    if (text.startsWith("false", i)) {
      i += 5;
      return false;
    }
    if (text.startsWith("null", i)) {
      i += 4;
      return null;
    }
    fail("unexpected token");
  }

  skipWhitespace();
  const value = parseValue();
  skipWhitespace();
  if (i !== length) fail("trailing data");
  return value;
}
