// RFC 8785 JCS reference canonicalizer for the PCS v0.6 research branch.
// This module operates on ordinary parsed JSON values. Raw JSON duplicate-key
// rejection remains a parser responsibility.

export const JCS_PROFILE = "pcs-jcs-rfc8785-v1";

export class CanonicalJSONError extends Error {}

function validateUnicodeString(value) {
  for (let i = 0; i < value.length; i++) {
    const unit = value.charCodeAt(i);
    let cp;
    if (unit >= 0xd800 && unit <= 0xdbff) {
      if (i + 1 >= value.length) {
        throw new CanonicalJSONError("lone Unicode surrogate is not permitted by I-JSON/JCS");
      }
      const low = value.charCodeAt(i + 1);
      if (low < 0xdc00 || low > 0xdfff) {
        throw new CanonicalJSONError("lone Unicode surrogate is not permitted by I-JSON/JCS");
      }
      cp = 0x10000 + ((unit - 0xd800) << 10) + (low - 0xdc00);
      i++;
    } else if (unit >= 0xdc00 && unit <= 0xdfff) {
      throw new CanonicalJSONError("lone Unicode surrogate is not permitted by I-JSON/JCS");
    } else {
      cp = unit;
    }
    if ((cp >= 0xfdd0 && cp <= 0xfdef) || (cp & 0xffff) === 0xfffe || (cp & 0xffff) === 0xffff) {
      throw new CanonicalJSONError("Unicode noncharacter is not permitted by the PCS I-JSON profile");
    }
  }
}

function serialize(value) {
  if (value === null) return "null";
  if (value === true) return "true";
  if (value === false) return "false";

  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new CanonicalJSONError("NaN and Infinity are not permitted by JCS");
    }
    return JSON.stringify(value);
  }

  if (typeof value === "string") {
    validateUnicodeString(value);
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    return "[" + value.map(serialize).join(",") + "]";
  }

  if (typeof value === "object") {
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null) {
      throw new CanonicalJSONError("only plain JSON objects are supported");
    }
    if (Object.prototype.hasOwnProperty.call(value, "toJSON")) {
      throw new CanonicalJSONError("toJSON hooks are not permitted at the canonicalization boundary");
    }
    const keys = Object.keys(value);
    for (const key of keys) validateUnicodeString(key);
    keys.sort();
    return "{" + keys.map((key) => JSON.stringify(key) + ":" + serialize(value[key])).join(",") + "}";
  }

  throw new CanonicalJSONError("unsupported JSON value type: " + typeof value);
}

export function canonicalizeJcs(value) {
  return serialize(value);
}

export function canonicalizeJcsBytes(value) {
  return new TextEncoder().encode(canonicalizeJcs(value));
}
