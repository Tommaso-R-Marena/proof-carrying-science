# V7 formal-source preservation audit

V7 authoritative archive SHA-256: `e98448c4d9493c54b88c876ea715c4c66d653565bf60d553c9627b14b7a5f8f8`.

Compared Git blob hashes for **every pre-existing `PCS/V2/ProofGated*.lean` module** in the V7 release against GitHub research V6 commit `c09bb32c4e82ef667f917eade1a2cd25654a969e`, path prefix `formal/PCS/V2/`. All 29 matched byte-for-byte. The eight new V7 modules and regenerated full audit are excluded from this pre-existing-module identity check.

This is a file identity check, **not** a fresh V7 Lean build, runtime proof, or compatibility audit of packaging scripts.

| Formal module | Git blob SHA-1 (both sources) |
|---|---|
| `ProofGatedArtifacts.lean` | `5332de68e13b2c43b9653d610bed442c19e70ac6` |
| `ProofGatedAudit.lean` | `be735108f2497c784590241c3761b30f45c6bbaf` |
| `ProofGatedBytes.lean` | `68f2398c06fbe04a1a472575f142c78fc3067204` |
| `ProofGatedCertCodec.lean` | `568d4f626c2ce20fbd14cfb51b80a33b95f77e79` |
| `ProofGatedCertificate.lean` | `75d366db045296e1400cfd86eae509f7ea5221b6` |
| `ProofGatedCodec.lean` | `9e92029a84d6d14fdd1d9342cb039191bf300cf4` |
| `ProofGatedDeep.lean` | `07db8fe1754c7d8b06903e80d98cf0b4a8922813` |
| `ProofGatedDeepCert.lean` | `b6701f5c39e9d58846e61c0be7b0d20ec376adb6` |
| `ProofGatedDeepCertGen.lean` | `ad3219d34abc7bced1021a94c24179f0a97c7775` |
| `ProofGatedGeneric.lean` | `c1b7ca7a8c0ce585bb15d41d2cc8146267e26298` |
| `ProofGatedInference.lean` | `d190fb6ee6d73290e36f307184a1aaf4cfdf6db1` |
| `ProofGatedInterpreter.lean` | `53ee62acc50649ae07184cd5fa8e0bfcae6d4502` |
| `ProofGatedLimits.lean` | `62cd9896ce41e982e04ba0fc1707e5edfafc437c` |
| `ProofGatedMultilayer.lean` | `75a6e6e799533d1ba2ab75f13b62590bb291f746` |
| `ProofGatedNetArtifacts.lean` | `21f6af46db0937bf247cc4f292d73ee98f300284` |
| `ProofGatedNoForget.lean` | `c2ed48fadc4642e0760a0a7bfbf0ad657fa3c157` |
| `ProofGatedNoForgetAudit.lean` | `18a557b5c94f6c67e3d69a5b8679966702fdbc46` |
| `ProofGatedPromotion.lean` | `37c095be03230b77514f9469ff56d3da87da3347` |
| `ProofGatedProtocol.lean` | `75d752d025bc6905f5c60e1712742dabdcdb1909` |
| `ProofGatedRobust.lean` | `5cbda6c16d7f074620ac972b9eaa710116b9d14f` |
| `ProofGatedSelfImprovement.lean` | `4388f794c5633affd0e23b3e0aa7aad3b4d88cd6` |
| `ProofGatedStrongArtifacts.lean` | `98930c6e93a8625e4df927bb3e2742041c644f4b` |
| `ProofGatedStrongAudit.lean` | `a8a71dcd4ae1805b55c7816ca947d444a482ae4d` |
| `ProofGatedStrongGate.lean` | `8f3c89b56775d78b6e35275fba3ce60bda1fa776` |
| `ProofGatedSymbolic.lean` | `495c730fede01038be24b99c9fb9f89d26a252fe` |
| `ProofGatedV1Analysis.lean` | `7ca4a9310f155480bc0bd4f8b0e79ca758670440` |
| `ProofGatedV6EndToEnd.lean` | `ee654054bc0b838df9347fee402bc7a457e2196a` |
| `ProofGatedV6Limits.lean` | `00a20823a2759487490d51ae83a51e4825f2a6d7` |
| `ProofGatedWide.lean` | `445996b49892ba1ff72250c29051bda4798d3040` |

Do not substitute these Git-object SHA-1s for the V7 release's SHA-256 manifest verification. They serve different purposes.
