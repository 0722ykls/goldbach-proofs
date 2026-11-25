import Mathlib

/-- Step vector `(28, 5)` on the full grid: the starting cells of length-3 lines with
`x`-step 28 and `y`-step 5 are counted by `(n - 56) * (n - 10)`. -/
theorem PEqualNP.Outside.L_no_three_in_line_cert_28_5 :
    ∀ n : ℕ, (((Finset.range n).product (Finset.range n)).filter
      (fun z => z.1 + 56 < n ∧ z.2 + 10 < n)).card = (n - 56) * (n - 10) := by
  intro n
  have hx : (Finset.range n).filter (fun a => a + 56 < n) = Finset.range (n - 56) := by
    ext a
    simp only [Finset.mem_filter, Finset.mem_range]
    omega
  have hy : (Finset.range n).filter (fun a => a + 10 < n) = Finset.range (n - 10) := by
    ext a
    simp only [Finset.mem_filter, Finset.mem_range]
    omega
  have hprod : ((Finset.range n).product (Finset.range n)).filter
      (fun z => z.1 + 56 < n ∧ z.2 + 10 < n)
      = ((Finset.range n).filter (fun a => a + 56 < n)).product
          ((Finset.range n).filter (fun a => a + 10 < n)) := by
    ext z
    simp only [Finset.mem_filter, Finset.mem_product]
    omega
  rw [hprod, hx, hy, Finset.card_product, Finset.card_range]
