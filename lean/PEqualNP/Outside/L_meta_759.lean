import Mathlib
import PEqualNP.Defs
import PEqualNP.MetaComplexity.L104
import PEqualNP.MetaComplexity.L105

namespace PEqualNP.Outside.L759
open PEqualNP.MetaComplexity

private def links : List (Fin 6 × Fin 6) := [(0,1),(0,2),(0,3),(1,4),(4,5)]
private abbrev tree := SimpleGraph.fromRel (fun i j : Fin 6 => (i,j) ∈ links)


private lemma has_edge : ∃ i j, tree.Adj i j := ⟨0,1,by decide⟩
private lemma edges : tree.edgeFinset.card = 5 := by decide +kernel

private lemma forest : tree.IsAcyclic := by
  have h01 : tree.Adj 0 1 := by decide
  have h02 : tree.Adj 0 2 := by decide
  have h03 : tree.Adj 0 3 := by decide
  have h14 : tree.Adj 1 4 := by decide
  have h45 : tree.Adj 4 5 := by decide
  apply SimpleGraph.IsTree.isAcyclic
  apply SimpleGraph.isTree_iff_connected_and_card.mpr
  constructor
  · rw [SimpleGraph.connected_iff_exists_forall_reachable]
    refine ⟨0,?_⟩
    intro w
    fin_cases w
    · exact SimpleGraph.Reachable.refl _
    · exact h01.reachable
    · exact h02.reachable
    · exact h03.reachable
    · exact h01.reachable.trans h14.reachable
    · exact (h01.reachable.trans h14.reachable).trans h45.reachable
  · rw [Nat.card_eq_fintype_card, ← SimpleGraph.edgeFinset_card,edges,Nat.card_eq_fintype_card,Fintype.card_fin]

private def target (x : Fin 6 → Bool) :=
  (x 0 && x 1) || (x 0 && x 2) || (x 0 && x 3) || (x 1 && x 4) || (x 4 && x 5)

private lemma same : (fun x : Fin 6 → Bool =>
    decide (∃ i j, tree.Adj i j ∧ x i = true ∧ x j = true)) = target := by
  funext x
  exact (by decide +kernel : ∀ z : Fin 6 → Bool, decide (∃ i j, tree.Adj i j ∧ z i = true ∧ z j = true) = target z) x

end PEqualNP.Outside.L759

namespace PEqualNP.Outside
open L759 PEqualNP.MetaComplexity
theorem L_meta_759 : ∀ s : ℕ, PEqualNP.MetaComplexity.HasCircuitSize 6 (fun x : Fin 6 → Bool => (x 0 && x 1) || (x 0 && x 2) || (x 0 && x 3) || (x 1 && x 4) || (x 4 && x 5)) s ↔ 6 ≤ s := by
  intro s
  change HasCircuitSize 6 target s ↔ _
  rw [← same]
  constructor
  · intro h
    have low : ∀ T : Finset (Fin 6), (∀ i j, tree.Adj i j → i ∈ T ∨ j ∈ T) → 2 ≤ T.card := by decide +kernel
    have hn := L104 6 2 s tree forest has_edge low h
    rw [edges] at hn
    omega
  · intro hs
    let T : Finset (Fin 6) := {0,4}
    have cov : ∀ i j, tree.Adj i j → i ∈ T ∨ j ∈ T := by decide +kernel
    have hc : T.card = 2 := by decide
    obtain ⟨C,hC,hsz,he⟩ := L105 6 tree T has_edge cov
    refine ⟨C,hC,?_,he⟩
    rw [edges,hc] at hsz
    omega

end PEqualNP.Outside


