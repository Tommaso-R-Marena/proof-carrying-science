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


const cryptoPayload = { z: "é", a: 1.0, nested: { b: 2, a: 1 } };
const cryptoVectors = [
  ["pcs-jcs-sha256-v1", "pcs-certificate-semantic-sha256-v2", "835f1ca3a9f2c64356a1a36e4d713f2f229618fb6fc0a6a51bb19c449645bdf8"],
  ["pcs-jcs-sha256-v1", "pcs-certificate-integrity-sha256-v2", "6f0032e60db4b03f69f0f78ff52a24596597ff4f8e0c08abf39f2997c3534fe8"],
  ["pcs-jcs-sha256-v1", "pcs-runtime-semantic-sha256-v2", "829e8c9e07d587ff5dfe1837bab087c73aeac678b47a5365d8cbc576db259fc6"],
  ["pcs-jcs-sha256-v1", "pcs-intake-semantic-sha256-v2", "f9e9b66c4f051d14247265e611b64c7c1bf415e7185a83a09ebea6a46fa7622d"],
  ["pcs-jcs-sha256-v1", "pcs-predicate-sha256-v2", "509c32f9f26b92ff1c3f5d3800a940fea55d02ce1a2f265820d86df870289131"],
  ["pcs-jcs-sha256-v1", "pcs-normalized-decision-sha256-v2", "e2d3054b205ee218fa6358a7da8d0b9979900a753ce034a558ec0e1694726879"],
  ["pcs-jcs-sha256-v1", "pcs-normalized-index-sha256-v2", "c5a3d915f9ab4f85427c8b050cb4b25db3de19fd6b820fd01df6cfdddb319c91"],
  ["pcs-jcs-ed25519-payload-v1", "pcs-certificate-signature-v2", "66b2b707526c28e7bb311ac05203712b133ed883fdc1158fd823b33205d04cd5"],
  ["pcs-jcs-ed25519-payload-v1", "pcs-package-signature-v2", "cc81ab71e8ab901985fe8601bbd34b016be02d31c2c23fb8b8b5b0968c1a41cd"],
  ["pcs-jcs-ed25519-payload-v1", "pcs-external-validator-receipt-signature-v1", "2d1d5ef25c49078024246c77137809261589ead1ee278a98aaee6fb135847103"],
];

for (const [format, domain, expectedDigest] of cryptoVectors) {
  const canonical = canonicalizeJcs({ format, domain, payload: cryptoPayload });
  const digest = crypto.createHash("sha256").update(Buffer.from(canonical, "utf8")).digest("hex");
  if (digest !== expectedDigest) {
    failures++;
    console.error("FAIL crypto domain vector", domain, { canonical, digest, expectedDigest });
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
  "JCS cross-language check PASS: " + vectors.vectors.length + " golden vector(s), " + cryptoVectors.length + " crypto domain vector(s)"
);
