import fs from "node:fs";
import crypto from "node:crypto";
import { TextDecoder } from "node:util";

import { canonicalizeJcs } from "../site/jcs.mjs";
import { parseStrictJson } from "../site/strict_json.mjs";


const ROOT = new URL("../", import.meta.url);
const GOLDEN = new URL("../tests/v06_golden/", import.meta.url);
const decoder = new TextDecoder("utf-8", { fatal: true });

function fail(message) {
  throw new Error(message);
}

function read(rel) {
  return fs.readFileSync(new URL(rel, GOLDEN));
}

function sha256(raw) {
  return crypto.createHash("sha256").update(raw).digest("hex");
}

function parseCanonical(rel) {
  const raw = read(rel);
  if (raw.length >= 3 && raw[0] === 0xef && raw[1] === 0xbb && raw[2] === 0xbf) {
    fail(rel + ": UTF-8 BOM is forbidden");
  }
  let text;
  try {
    text = decoder.decode(raw);
  } catch (error) {
    fail(rel + ": invalid UTF-8: " + error);
  }
  const value = parseStrictJson(text);
  const canonical = Buffer.from(canonicalizeJcs(value), "utf8");
  if (!canonical.equals(raw)) {
    fail(rel + ": committed bytes are not exact JCS canonical bytes");
  }
  return { raw, value };
}

function canonicalEqual(left, right) {
  return canonicalizeJcs(left) === canonicalizeJcs(right);
}

function hashEnvelope(domain, payload) {
  return {
    format: "pcs-jcs-sha256-v1",
    domain,
    payload,
  };
}

function domainSha256(domain, payload) {
  return sha256(Buffer.from(canonicalizeJcs(hashEnvelope(domain, payload)), "utf8"));
}

function verifySignatureRecord(record, expectedDomain, expectedPayload, publicKey, fingerprint) {
  if (record.signature_format !== "pcs-ed25519-jcs-v2") {
    fail("unexpected signature record format");
  }
  if (record.algorithm !== "Ed25519") {
    fail("unexpected signature algorithm");
  }
  if (record.public_key_fingerprint !== fingerprint) {
    fail("signature record fingerprint mismatch");
  }
  if (
    record.payload?.format !== "pcs-jcs-ed25519-payload-v1" ||
    record.payload?.domain !== expectedDomain
  ) {
    fail("signature domain/format mismatch");
  }
  if (!canonicalEqual(record.payload.payload, expectedPayload)) {
    fail("signature payload does not match expected object");
  }

  const payloadBytes = Buffer.from(canonicalizeJcs(record.payload), "utf8");
  if (record.payload_sha256 !== sha256(payloadBytes)) {
    fail("signature payload SHA-256 mismatch");
  }
  const signature = Buffer.from(record.signature, "base64");
  if (signature.length !== 64) {
    fail("Ed25519 signature has wrong length");
  }
  if (!crypto.verify(null, payloadBytes, publicKey, signature)) {
    fail("Ed25519 verification failed");
  }
}

const metadata = JSON.parse(read("metadata.json").toString("utf8"));
if (metadata.format !== "pcs-v06-byte-contract-v1" || metadata.test_vector_only !== true) {
  fail("unexpected golden metadata format");
}

const certificate = parseCanonical("certificate.json");
const certificateSignature = parseCanonical("certificate_signature.json");
const manifest = parseCanonical("package_manifest.json");
const packageSignature = parseCanonical("package_signature.json");
const artifact = read("artifacts/fixture.bin");

const rawHashes = {
  certificate_byte_sha256: sha256(certificate.raw),
  certificate_signature_record_byte_sha256: sha256(certificateSignature.raw),
  package_manifest_byte_sha256: sha256(manifest.raw),
  package_signature_record_byte_sha256: sha256(packageSignature.raw),
  artifact_sha256: sha256(artifact),
};
for (const [field, actual] of Object.entries(rawHashes)) {
  if (metadata[field] !== actual) {
    fail(field + " mismatch: expected=" + metadata[field] + " actual=" + actual);
  }
}

const publicRaw = Buffer.from(metadata.public_key_raw_base64, "base64");
if (publicRaw.length !== 32) {
  fail("golden Ed25519 public key must be 32 raw bytes");
}
const fingerprint = sha256(publicRaw);
if (fingerprint !== metadata.public_key_fingerprint) {
  fail("golden public-key fingerprint mismatch");
}
const spkiPrefix = Buffer.from("302a300506032b6570032100", "hex");
const publicKey = crypto.createPublicKey({
  key: Buffer.concat([spkiPrefix, publicRaw]),
  format: "der",
  type: "spki",
});

const cert = certificate.value;
const semanticProjection = structuredClone(cert);
delete semanticProjection.generated_at;
delete semanticProjection.semantic_hash;
delete semanticProjection.integrity_hash;
const semantic = domainSha256(
  "pcs-certificate-semantic-sha256-v2",
  semanticProjection
);
if (semantic !== cert.semantic_hash || semantic !== metadata.certificate_semantic_hash) {
  fail("certificate semantic hash mismatch");
}

const integrityProjection = structuredClone(cert);
delete integrityProjection.integrity_hash;
const integrity = domainSha256(
  "pcs-certificate-integrity-sha256-v2",
  integrityProjection
);
if (integrity !== cert.integrity_hash || integrity !== metadata.certificate_integrity_hash) {
  fail("certificate integrity hash mismatch");
}

const certificateSignaturePayload = {
  spec_version: cert.spec_version,
  checker_version: cert.checker_version,
  canonical_json_profile: cert.canonical_json_profile,
  semantic_hash_format: cert.semantic_hash_format,
  integrity_hash_format: cert.integrity_hash_format,
  subject: cert.subject,
  semantic_hash: cert.semantic_hash,
  integrity_hash: cert.integrity_hash,
};
verifySignatureRecord(
  certificateSignature.value,
  "pcs-certificate-signature-v2",
  certificateSignaturePayload,
  publicKey,
  fingerprint
);
if (
  certificateSignature.value.payload_sha256 !==
  metadata.certificate_signature_payload_sha256
) {
  fail("certificate signature payload golden digest mismatch");
}

const packageManifest = manifest.value;
if (packageManifest.package_format !== "pcs-package-v2") {
  fail("unexpected package format");
}
if (packageManifest.canonical_json_profile !== "pcs-jcs-rfc8785-v1") {
  fail("unexpected package canonicalization profile");
}
if (
  packageManifest.certificate_semantic_hash !== cert.semantic_hash ||
  packageManifest.certificate_integrity_hash !== cert.integrity_hash
) {
  fail("package manifest does not bind certificate hashes");
}

const signedMembers = {
  "certificate.json": certificate.raw,
  "artifacts/fixture.bin": artifact,
};
const expectedNames = Object.keys(packageManifest.files).sort();
const actualNames = Object.keys(signedMembers).sort();
if (JSON.stringify(expectedNames) !== JSON.stringify(actualNames)) {
  fail("package signed-member set mismatch");
}
for (const name of expectedNames) {
  const raw = signedMembers[name];
  const meta = packageManifest.files[name];
  if (raw.length !== meta.size) {
    fail(name + ": package member size mismatch");
  }
  if (sha256(raw) !== meta.sha256) {
    fail(name + ": package member SHA-256 mismatch");
  }
}

verifySignatureRecord(
  packageSignature.value,
  "pcs-package-signature-v2",
  packageManifest,
  publicKey,
  fingerprint
);
if (
  packageSignature.value.payload_sha256 !==
  metadata.package_signature_payload_sha256
) {
  fail("package signature payload golden digest mismatch");
}

console.log(
  "PASS v0.6 Node golden byte contract: canonical JSON, certificate domain hashes, " +
    "2 Ed25519 signatures, exact package member set, sizes and SHA-256"
);
