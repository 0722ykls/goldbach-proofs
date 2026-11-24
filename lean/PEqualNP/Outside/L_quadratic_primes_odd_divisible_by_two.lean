import Mathlib

theorem PEqualNP.Outside.L_quadratic_primes_odd_divisible_by_two :
    ∀ n : ℕ, Odd n → 2 ∣ n ^ 2 + 1 := by
  rintro n ⟨k, hk⟩
  refine ⟨2 * k * k + 2 * k + 1, ?_⟩
  rw [hk]
  ring
