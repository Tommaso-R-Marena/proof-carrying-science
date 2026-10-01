import PCS.V2.SHA256

/-!
# SHA-256 padding is unambiguous

FIPS 180-4 §5.1.1 padding is only meaningful because it is injective on the message
space (messages shorter than 2^64 bits): two different messages never yield the same
padded block sequence.  This file proves that property for the Lean SHA-256 used by
the v0.6 checker, together with the block-level corollary.

* `be64_injective`        — the big-endian 64-bit length field is injective below 2^64;
* `pad_suffix`            — the last eight padded bytes are the bit-length field;
* `pad_injective`         — padding is injective for messages of < 2^61 bytes;
* `chunks_pad_injective`  — so is the parsed 512-bit block sequence.

These are implementation facts about `PCS.V2.SHA256.sha256`; they say nothing about
collision resistance of the compression function, which remains the explicit
`Sha256Collision` boundary.
-/

namespace PCS.V2.SHA256

theorem be64_eq (n : Nat) : be64 n =
    [UInt8.ofNat (n / 256 ^ 7), UInt8.ofNat (n / 256 ^ 6), UInt8.ofNat (n / 256 ^ 5),
     UInt8.ofNat (n / 256 ^ 4), UInt8.ofNat (n / 256 ^ 3), UInt8.ofNat (n / 256 ^ 2),
     UInt8.ofNat (n / 256 ^ 1), UInt8.ofNat (n / 256 ^ 0)] := by
  simp [be64, List.range_succ]

theorem uint8_ofNat_eq {a b : Nat} (h : UInt8.ofNat a = UInt8.ofNat b) : a % 256 = b % 256 := by
  have := congrArg UInt8.toNat h
  simpa [UInt8.toNat_ofNat] using this

/-- The FIPS 180-4 length field is injective on lengths below 2^64. -/
theorem be64_injective {n m : Nat} (hn : n < 2 ^ 64) (hm : m < 2 ^ 64) (h : be64 n = be64 m) :
    n = m := by
  rw [be64_eq, be64_eq] at h
  simp only [List.cons.injEq, and_true] at h
  obtain ⟨h7, h6, h5, h4, h3, h2, h1, h0⟩ := h
  have e7 := uint8_ofNat_eq h7
  have e6 := uint8_ofNat_eq h6
  have e5 := uint8_ofNat_eq h5
  have e4 := uint8_ofNat_eq h4
  have e3 := uint8_ofNat_eq h3
  have e2 := uint8_ofNat_eq h2
  have e1 := uint8_ofNat_eq h1
  have e0 := uint8_ofNat_eq h0
  simp only [Nat.reducePow, Nat.div_one] at e7 e6 e5 e4 e3 e2 e1 e0 hn hm
  omega

/-- The last eight padded bytes are the big-endian bit length. -/
theorem pad_suffix (msg : List UInt8) :
    (pad msg).drop ((pad msg).length - 8) = be64 (8 * msg.length) := by
  have h := pad_length_field msg
  rw [pad_length]
  have : msg.length + 1 + padZeros msg.length + 8 - 8 = msg.length + 1 + padZeros msg.length := by
    omega
  rw [this, h]

/-- Padding is injective on every message the standard admits (< 2^61 bytes). -/
theorem pad_injective {m₁ m₂ : List UInt8} (h₁ : m₁.length < 2 ^ 61) (h₂ : m₂.length < 2 ^ 61)
    (h : pad m₁ = pad m₂) : m₁ = m₂ := by
  have hs := pad_suffix m₁
  rw [h, pad_suffix m₂] at hs
  have hl : m₂.length = m₁.length := by
    have := be64_injective (by omega) (by omega) hs
    omega
  have hp₁ := pad_prefix m₁
  have hp₂ := pad_prefix m₂
  rw [h, ← hl, hp₂] at hp₁
  exact hp₁.symm

/-- Block parsing of the padded message is injective too. -/
theorem chunks_pad_injective {m₁ m₂ : List UInt8} (h₁ : m₁.length < 2 ^ 61)
    (h₂ : m₂.length < 2 ^ 61) (h : chunks (pad m₁) = chunks (pad m₂)) : m₁ = m₂ := by
  apply pad_injective h₁ h₂
  rw [← chunks_join (pad m₁), ← chunks_join (pad m₂), h]

/-- Consequently a SHA-256 collision between two admissible messages is a collision of
    the iterated compression function on two *distinct* block sequences. -/
theorem sha256_collision_is_block_collision {m₁ m₂ : List UInt8} (h₁ : m₁.length < 2 ^ 61)
    (h₂ : m₂.length < 2 ^ 61) (hne : m₁ ≠ m₂) (h : sha256 m₁ = sha256 m₂) :
    chunks (pad m₁) ≠ chunks (pad m₂) ∧
      ((chunks (pad m₁)).foldl compress H0).flatMap wordBytes =
        ((chunks (pad m₂)).foldl compress H0).flatMap wordBytes := by
  have hblocks := h
  unfold sha256 at hblocks
  rw [compressBlocks_eq_chunks_foldl, compressBlocks_eq_chunks_foldl] at hblocks
  exact ⟨fun hc => hne (chunks_pad_injective h₁ h₂ hc), hblocks⟩

/-! ## Block parsing and message schedule -/

theorem words_length : ∀ l : List UInt8, (words l).length = l.length / 4
  | a :: b :: c :: d :: rest => by simp [words, words_length rest]; omega
  | [] => by simp [words]
  | [_] => by simp [words]
  | [_, _] => by simp [words]
  | [_, _, _] => by simp [words]

theorem foldl_push_size (l : List Nat) (f : Array UInt32 → Nat → UInt32) (w : Array UInt32) :
    (l.foldl (fun w t => w.push (f w t)) w).size = w.size + l.length := by
  induction l generalizing w with
  | nil => simp
  | cons x xs ih => simp [ih]; omega

/-- A 64-byte block yields exactly 64 schedule words W₀..W₆₃, so every `w[t]!` access
    of the compression function is in bounds (the default value is never used). -/
theorem schedule_size {block : List UInt8} (h : block.length = 64) : (schedule block).size = 64 := by
  have hw : (words block).length = 16 := by rw [words_length, h]
  unfold schedule
  simp only [Std.Legacy.Range.forIn_eq_forIn_range', Id.run, bind_pure_comp, map_pure]
  simp only [List.forIn_pure_yield_eq_foldl, pure_bind]
  show Array.size (List.foldl _ _ _) = 64
  rw [foldl_push_size]
  simp [hw, Std.Legacy.Range.size]

/-- Every block of every padded message has a full 64-word schedule. -/
theorem pad_schedule_size (msg : List UInt8) : ∀ c ∈ chunks (pad msg), (schedule c).size = 64 :=
  fun c hc => schedule_size (pad_blocks_64 msg c hc)

end PCS.V2.SHA256
