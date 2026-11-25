import Mathlib

/-!
# Grid triple count for stride (13, 1)

The starting points of all equally spaced triples with step `(13, 1)` inside an `n × n` grid
are counted by separating the two coordinates: a start `(x, y)` is admissible exactly when
`x + 26 < n` and `y + 2 < n`, and these two conditions range independently over
`Finset.range (n - 26)` and `Finset.range (n - 2)`.
-/

theorem PEqualNP.Outside.L_no_three_in_line_cert_13_1 :
    ∀ n : ℕ, (((Finset.range n).product (Finset.range n)).filter (fun z => z.1 + 26 < n ∧ z.2 + 2 < n)).card = (n - 26) * (n - 2) := by
  intro n
  -- Filtering the grid by the two coordinate conditions leaves a product of two initial segments.
  have hgrid : ((Finset.range n).product (Finset.range n)).filter (fun z => z.1 + 26 < n ∧ z.2 + 2 < n)
      = (Finset.range (n - 26)).product (Finset.range (n - 2)) := by
    ext ⟨x, y⟩
    simp only [Finset.mem_filter, Finset.product_eq_sprod, Finset.mem_product, Finset.mem_range]
    omega
  rw [hgrid, Finset.product_eq_sprod, Finset.card_product, Finset.card_range, Finset.card_range]
