import fs from "node:fs";
import crypto from "node:crypto";
import { canonicalizeJcs } from "../site/jcs.mjs";
import { parseStrictJson } from "../site/strict_json.mjs";

const vectors = JSON.parse(
  fs.readFileSync(new URL("../tests/canonical_json_vectors.json", import.meta.url), "utf8")
);

let failures = 0;
for (const vector of vectors.vectors) {
  const value = parseStrictJson(vector.input_json);
  const canonical = canonicalizeJcs(value);
  const digest = crypto
    .createHash("sha256")
    .update(Buffer.from(canonical, "utf8"))
    .digest("hex");
  if (canonical !== vector.canonical || digest !== vector.sha256) {
    failures++;
    console.error("FAIL", vector.name, { canonical, digest });
  }
}

for (const raw of ['{"a":1,"a":2}', '{"a":1,"\\u0061":2}', "01", "1.", "1e", "1e400"]) {
  let rejected = false;
  try {
    parseStrictJson(raw);
  } catch {
    rejected = true;
  }
  if (!rejected) {
    failures++;
    console.error("FAIL expected strict parse rejection", raw);
  }
}

for (const value of [NaN, Infinity, -Infinity, "\ud800", "\ufdd0"]) {
  let rejected = false;
  try {
    canonicalizeJcs(value);
  } catch {
    rejected = true;
  }
  if (!rejected) {
    failures++;
    console.error("FAIL expected rejection", value);
  }
}

if (failures) {
  console.error("JCS cross-language check failed: " + failures + " failure(s)");
  process.exit(1);
}
console.log(
  "JCS cross-language check PASS: " + vectors.vectors.length + " golden vector(s)"
);
