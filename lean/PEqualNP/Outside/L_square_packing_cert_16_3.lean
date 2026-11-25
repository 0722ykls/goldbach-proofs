import Mathlib

/-!
# Rotation certificate for slope 96/247

A rotated unit square with rational rotation matrix `(247, 96; -96, 247)/265` fits inside the
axis-aligned square `[0, L] × [0, L]` with centre `(x, y)` exactly when both coordinates stay
`(a + b)/(2n) = 343` away from the boundary: the four corner instances give the lower bound in
both coordinates, and the bounds `|u|, |v| ≤ 1/2` give the converse.
-/

theorem PEqualNP.Outside.L_square_packing_cert_16_3 :
    ∀ x y L:ℝ, (∀ u v:ℝ, |u|≤1/2 → |v|≤1/2 → 0≤x+(247*u-96*v)/265 ∧ x+(247*u-96*v)/265≤L ∧ 0≤y+(96*u+247*v)/265 ∧ y+(96*u+247*v)/265≤L) ↔ (343:ℝ)/(2*265)≤x ∧ x≤L-(343:ℝ)/(2*265) ∧ (343:ℝ)/(2*265)≤y ∧ y≤L-(343:ℝ)/(2*265) := by
  intro x y L
  constructor
  · intro h
    have e1 := h (1/2) (1/2) (by norm_num) (by norm_num)
    have e2 := h (1/2) (-(1/2)) (by norm_num) (by norm_num)
    have e3 := h (-(1/2)) (1/2) (by norm_num) (by norm_num)
    have e4 := h (-(1/2)) (-(1/2)) (by norm_num) (by norm_num)
    norm_num at e1 e2 e3 e4
    refine ⟨?_, ?_, ?_, ?_⟩ <;> linarith
  · rintro ⟨hx1, hx2, hy1, hy2⟩ u v hu hv
    rw [abs_le] at hu hv
    refine ⟨?_, ?_, ?_, ?_⟩ <;> linarith [hu.1, hu.2, hv.1, hv.2]
