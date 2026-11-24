import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Algebra.Order.BigOperators.Group.Finset

namespace PEqualNP.Outside

theorem L_goldbach_log_correlation_iff :
    ∀ n : ℕ,
      let w : ℕ → ℝ := fun k => if Nat.Prime k then Real.log (k : ℝ) else 0
      0 < Finset.sum (Finset.range (n + 1)) (fun p => w p * w (n - p)) ↔
        (∃ p q : ℕ, Nat.Prime p ∧ Nat.Prime q ∧ p + q = n) := by
  intro n
  let w : ℕ → ℝ := fun k => if Nat.Prime k then Real.log (k : ℝ) else 0
  change 0 < Finset.sum (Finset.range (n + 1)) (fun p => w p * w (n - p)) ↔ _
  have weight_pos {p : ℕ} (hp : Nat.Prime p) : 0 < w p := by
    have hone : (1 : ℝ) < (p : ℝ) := by exact_mod_cast hp.one_lt
    simpa [w, hp] using Real.log_pos hone
  have weight_nonneg (p : ℕ) : 0 ≤ w p := by
    by_cases hp : Nat.Prime p
    · exact (weight_pos hp).le
    · simp [w, hp]
  have term_nonneg : ∀ p ∈ Finset.range (n + 1), 0 ≤ w p * w (n - p) :=
    fun p _ => mul_nonneg (weight_nonneg p) (weight_nonneg (n - p))
  constructor
  · intro hsum
    obtain ⟨p, hmem, hpos⟩ := (Finset.sum_pos_iff_of_nonneg term_nonneg).mp hsum
    have hp : Nat.Prime p := by
      by_contra hp
      simpa [w, hp] using hpos
    have hq : Nat.Prime (n - p) := by
      by_contra hq
      simpa [w, hq] using hpos
    have hbound := Finset.mem_range.mp hmem
    exact ⟨p, n - p, hp, hq, by omega⟩
  · rintro ⟨p, q, hp, hq, hsum⟩
    have hmem : p ∈ Finset.range (n + 1) := Finset.mem_range.mpr (by omega)
    have hsub : n - p = q := by omega
    have hpos : 0 < w p * w (n - p) := by
      rw [hsub]
      exact mul_pos (weight_pos hp) (weight_pos hq)
    exact hpos.trans_le (Finset.single_le_sum term_nonneg hmem)

end PEqualNP.Outside

theorem PEqualNP.Outside.L_goldbach_exception_second_moment :
    ∀ (I F : Finset ℕ) (e : ℕ → ℝ) (B : ℝ), F ⊆ I → 0 < B → (∀ n ∈ F, B ≤ |e n|) → (F.card : ℝ) * B ^ 2 ≤ Finset.sum I (fun n => |e n| ^ 2) := by
  intro I F e B hFI hB hthreshold
  calc
    (F.card : ℝ) * B ^ 2 = Finset.sum F (fun _ => B ^ 2) := by
      simp [nsmul_eq_mul]
    _ ≤ Finset.sum F (fun n => |e n| ^ 2) := by
      apply Finset.sum_le_sum
      intro n hn
      exact pow_le_pow_left₀ hB.le (hthreshold n hn) 2
    _ ≤ Finset.sum I (fun n => |e n| ^ 2) := by
      apply Finset.sum_le_sum_of_subset_of_nonneg hFI
      intro n _ _
      exact sq_nonneg (|e n|)

namespace PEqualNP.Outside
theorem L_goldbach_collab_exception_bound (I F : Finset ℕ) (M : ℕ → ℝ) (B : ℝ)
    (hFI : F ⊆ I) (hB : 0 < B)
    (hNo : ∀ n ∈ F, ¬ (∃ p q : ℕ, Nat.Prime p ∧ Nat.Prime q ∧ p + q = n))
    (hMain : ∀ n ∈ F, B ≤ M n) :
    let w : ℕ → ℝ := fun k => if Nat.Prime k then Real.log (k : ℝ) else 0
    (F.card : ℝ) * B ^ 2 ≤
      Finset.sum I (fun n => |M n - Finset.sum (Finset.range (n + 1)) (fun p => w p * w (n - p))| ^ 2) := by
  let w : ℕ → ℝ := fun k => if Nat.Prime k then Real.log (k : ℝ) else 0
  let R (n : ℕ) : ℝ := Finset.sum (Finset.range (n + 1)) (fun p => w p * w (n - p))
  change (F.card : ℝ) * B ^ 2 ≤ Finset.sum I (fun n => |M n - R n| ^ 2)
  apply L_goldbach_exception_second_moment I F (fun n => M n - R n) B hFI hB
  intro n hn
  have hR : R n ≤ 0 := le_of_not_gt (fun hpos => hNo n hn ((L_goldbach_log_correlation_iff n).mp hpos))
  calc
    B ≤ M n := hMain n hn
    _ ≤ M n - R n := by simpa only [sub_zero] using sub_le_sub_left hR (M n)
    _ ≤ |M n - R n| := le_abs_self _
end PEqualNP.Outside
