import fs from "node:fs";
import crypto from "node:crypto";
import { canonicalizeJcs } from "../site/jcs.mjs";

const vectors = JSON.parse(
  fs.readFileSync(new URL("../tests/canonical_json_vectors.json", import.meta.url), "utf8")
);

let failures = 0;
for (const vector of vectors.vectors) {
  const value = JSON.parse(vector.input_json);
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
