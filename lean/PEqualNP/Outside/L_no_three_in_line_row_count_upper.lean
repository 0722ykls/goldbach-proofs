import Mathlib

theorem PEqualNP.Outside.L_no_three_in_line_row_count_upper :
    ∀ (n : ℕ) (counts : ℕ → ℕ), (∀ i < n, counts i ≤ 2) → Finset.sum (Finset.range n) counts ≤ 2 * n := by
  intro n counts h
  calc
    Finset.sum (Finset.range n) counts ≤ Finset.sum (Finset.range n) (fun _ => 2) :=
      Finset.sum_le_sum fun i hi => h i (Finset.mem_range.mp hi)
    _ = 2 * n := by simp [nsmul_eq_mul, Nat.mul_comm]
