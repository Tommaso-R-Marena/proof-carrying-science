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
const normalizedIndex = parseCanonical("normalized/index.json");
if (!Array.isArray(normalizedIndex.value.entries) || normalizedIndex.value.entries.length !== 1) {
  fail("golden normalized index must contain exactly one entry");
}
const normalizedIndexEntry = normalizedIndex.value.entries[0];
const normalized = parseCanonical(normalizedIndexEntry.path);
const artifact = read("artifacts/fixture.bin");

const rawHashes = {
  certificate_byte_sha256: sha256(certificate.raw),
  certificate_signature_record_byte_sha256: sha256(certificateSignature.raw),
  package_manifest_byte_sha256: sha256(manifest.raw),
  package_signature_record_byte_sha256: sha256(packageSignature.raw),
  normalized_wire_byte_sha256: sha256(normalized.raw),
  normalized_index_byte_sha256: sha256(normalizedIndex.raw),
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

const normalizedWire = normalized.value;
const claim = cert.claims.find((item) => item.id === "C1");
if (!claim) fail("golden certificate lacks claim C1");
const evidenceById = new Map(cert.evidence.map((item) => [item.id, item]));
const assumptionById = new Map(cert.assumptions.map((item) => [item.id, item]));

const predicateCommitment =
  "pcs-predicate-sha256-v2:" +
  domainSha256("pcs-predicate-sha256-v2", claim.predicate);
if (predicateCommitment !== metadata.predicate_commitment) {
  fail("predicate commitment golden mismatch");
}

const expectedNormalized = {
  wire_format: "pcs-normalized-decision-v2",
  canonical_json_profile: "pcs-jcs-rfc8785-v1",
  wire_hash_format: "pcs-normalized-decision-sha256-v2",
  predicate_hash_format: "pcs-predicate-sha256-v2",
  source: {
    spec_version: cert.spec_version,
    checker_version: cert.checker_version,
    certificate_semantic_hash: cert.semantic_hash,
    certificate_integrity_hash: cert.integrity_hash,
    claim_id: claim.id,
  },
  context: claim.assumptions.map((id) => ({
    id,
    statement: assumptionById.get(id)?.statement,
  })),
  claim: {
    id: claim.id,
    kind: claim.kind,
    predicate_commitment: predicateCommitment,
    required_evidence: claim.required_evidence,
    assumptions: claim.assumptions,
  },
  evidence: claim.required_evidence.map((id) => {
    const item = evidenceById.get(id);
    if (!item) fail("missing required evidence " + id);
    return {
      id: item.id,
      kind: item.kind,
      outcome: item.outcome,
      predicate_commitment:
        "pcs-predicate-sha256-v2:" +
        domainSha256("pcs-predicate-sha256-v2", item.predicate),
    };
  }),
  decision: claim.assessment.status,
  wire_semantic_hash: "",
};
const normalizedProjection = structuredClone(expectedNormalized);
delete normalizedProjection.wire_semantic_hash;
expectedNormalized.wire_semantic_hash = domainSha256(
  "pcs-normalized-decision-sha256-v2",
  normalizedProjection
);
if (expectedNormalized.wire_semantic_hash !== metadata.normalized_wire_semantic_hash) {
  fail("normalized wire semantic hash golden mismatch");
}
if (!canonicalEqual(expectedNormalized, normalizedWire)) {
  fail("normalized wire does not exactly equal certificate-derived projection");
}

const storageKey = sha256(Buffer.from(claim.id, "utf8"));
const expectedWirePath = "normalized/" + storageKey + ".json";
if (normalizedIndexEntry.path !== expectedWirePath || metadata.normalized_wire_path !== expectedWirePath) {
  fail("normalized wire storage-key path mismatch");
}
const expectedIndex = {
  index_format: "pcs-normalized-decision-index-v2",
  canonical_json_profile: "pcs-jcs-rfc8785-v1",
  index_hash_format: "pcs-normalized-index-sha256-v2",
  certificate_semantic_hash: cert.semantic_hash,
  certificate_integrity_hash: cert.integrity_hash,
  entries: [
    {
      claim_id: claim.id,
      path: expectedWirePath,
      decision: expectedNormalized.decision,
      wire_semantic_hash: expectedNormalized.wire_semantic_hash,
    },
  ],
  index_semantic_hash: "",
};
const indexProjection = structuredClone(expectedIndex);
delete indexProjection.index_semantic_hash;
expectedIndex.index_semantic_hash = domainSha256(
  "pcs-normalized-index-sha256-v2",
  indexProjection
);
if (expectedIndex.index_semantic_hash !== metadata.normalized_index_semantic_hash) {
  fail("normalized index semantic hash golden mismatch");
}
if (!canonicalEqual(expectedIndex, normalizedIndex.value)) {
  fail("normalized index does not exactly equal certificate-derived claim index");
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
  [expectedWirePath]: normalized.raw,
  "normalized/index.json": normalizedIndex.raw,
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
    "2 Ed25519 signatures, exact package member set, normalized wire/index derivation, sizes and SHA-256"
);
