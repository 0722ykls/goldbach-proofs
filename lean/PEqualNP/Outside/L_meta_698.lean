import Mathlib
import PEqualNP.Defs

namespace PEqualNP.Outside.L698
open PEqualNP.MetaComplexity

private def step (w : List Bool) (G : BinaryGate) :=
  w ++ [G.op (w.getD G.left false) (w.getD G.right false)]

private def wireList (D : BinaryCircuit) (x : List Bool) (j : ℕ) :=
  (D.gates.take j).foldl step x

private lemma prefix_len (D : BinaryCircuit) (x : List Bool) (j : ℕ) (hj : j ≤ D.gates.length) :
    (wireList D x j).length = x.length+j := by
  induction j with
  | zero => simp [wireList]
  | succ j ih =>
    have h : j < D.gates.length := by omega
    rw [wireList,List.take_succ_eq_append_getElem h,List.foldl_append]
    change (wireList D x j ++ [_]).length = _
    simp [ih (by omega),Nat.add_assoc]

private lemma prefix_next {D : BinaryCircuit} {x : List Bool} {j : ℕ} {G : BinaryGate}
    (hg : D.gates[j]? = some G) : wireList D x (j+1) = step (wireList D x j) G := by
  obtain ⟨hj,rfl⟩ := List.getElem?_eq_some_iff.mp hg
  unfold wireList
  rw [List.take_succ_eq_append_getElem hj,List.foldl_append]
  rfl

private def valAt (D : BinaryCircuit) (x : List Bool) (j i : ℕ) :=
  (wireList D x j).getD i false

private lemma read_step (w : List Bool) (G : BinaryGate) (i : ℕ) :
    (step w G).getD i false = if i = w.length then G.op (w.getD G.left false) (w.getD G.right false)
      else w.getD i false := by
  by_cases h : i < w.length
  · simp [step,List.getD_eq_getElem?_getD,List.getElem?_append,h, Nat.ne_of_lt h]
  · by_cases e : i = w.length
    · subst i
      simp [step,List.getD_eq_getElem?_getD,List.getElem?_append]
    · have lt : 0 < i-w.length := by omega
      simp [step,List.getD_eq_getElem?_getD,List.getElem?_append,h,e,List.getElem?_eq_none (by omega : w.length ≤ i), List.getElem?_eq_none (by simp; omega : [G.op (w.getD G.left false) (w.getD G.right false)].length ≤ i-w.length)]

      rw [List.getElem?_eq_none (by simp only [List.length_cons,List.length_nil]; omega)]
      rfl

private lemma agree {n : ℕ} (D : BinaryCircuit) (x y : List Bool) (hx : x.length = n)
    (hy : y.length = n) (P : ℕ → Prop) (lo hi : ℕ) (hl : lo ≤ hi) (hh : hi ≤ D.gates.length)
    (init : ∀ i, P i → valAt D x lo i = valAt D y lo i)
    (gate : ∀ j G, lo ≤ j → j < hi → D.gates[j]? = some G → P (n+j) →
      (∀ i, P i → valAt D x j i = valAt D y j i) →
      G.op (valAt D x j G.left) (valAt D x j G.right) =
      G.op (valAt D y j G.left) (valAt D y j G.right)) :
    ∀ i, P i → valAt D x hi i = valAt D y hi i := by
  induction hi with
  | zero => simpa [show lo = 0 by omega] using init
  | succ j ih =>
    by_cases h : lo ≤ j
    · have hj : j < D.gates.length := by omega
      have old := ih h (by omega) (fun t G a b => gate t G a (by omega))
      have hg : D.gates[j]? = some D.gates[j] := List.getElem?_eq_getElem hj
      intro i hp
      simp only [valAt,prefix_next hg,read_step,prefix_len D x j (by omega),prefix_len D y j (by omega),hx,hy]
      split
      next he => exact gate j _ h (by omega) hg (he ▸ hp) old
      next => exact old i hp
    · simpa [show lo = j+1 by omega] using init

private lemma missing {D : BinaryCircuit} {n j i : ℕ} {x : List Bool} (hx : x.length = n)
    (hj : j ≤ D.gates.length) (hi : n+j ≤ i) : valAt D x j i = false := by
  have h : (wireList D x j).length ≤ i := by rw [prefix_len _ _ _ hj,hx]; exact hi
  simp [valAt,List.getD_eq_getElem?_getD,List.getElem?_eq_none h]




private def input {n : ℕ} (x : Fin n → Bool) (v u : Fin n) (a b : Bool) :=
  List.ofFn (n := n) (Function.update (Function.update x v a) u b)

private def Reads (G : BinaryGate) (i : ℕ) := G.left = i ∨ G.right = i

private def Channels (D : BinaryCircuit) (n v u g h k : ℕ) :=
  ∀ j G, D.gates[j]? = some G →
    (Reads G v → j = g) ∧ (Reads G u → j = h) ∧
    (Reads G (n+g) → g < j → j = k) ∧ (Reads G (n+h) → h < j → j = k)

private def keep (n v u g h i : ℕ) (a b c d : Bool) :=
  ((i = v ∨ i = n+g) → a = c) ∧ ((i = u ∨ i = n+h) → b = d)

private lemma before {n : ℕ} (D : BinaryCircuit) (x : Fin n → Bool) (v u : Fin n)
    (g h k : ℕ) (ch : Channels D n v u g h k) (hk : k ≤ D.gates.length)
    (a b c d : Bool) :
    ∀ i, keep n v u g h i a b c d →
      valAt D (input x v u a b) k i = valAt D (input x v u c d) k i := by
  apply agree (n := n) D _ _ (by simp [input]) (by simp [input]) _ 0 k (by omega) hk
  · intro i hp
    simp only [valAt,wireList,List.take_zero,List.foldl_nil,input,List.getD_eq_getElem?_getD,List.getElem?_ofFn]
    split
    next hi =>
      by_cases hu : (⟨i,hi⟩ : Fin n) = u
      · simpa [hu] using hp.2 (Or.inl (congrArg Fin.val hu))
      · by_cases hv : (⟨i,hi⟩ : Fin n) = v
        · have hvu : v ≠ u := hv ▸ hu
          simpa [hv,Function.update_of_ne hvu] using hp.1 (Or.inl (congrArg Fin.val hv))
        · simp [Function.update_of_ne hu,Function.update_of_ne hv]
    next => rfl
  · intro j G _ hj hG hp old
    obtain ⟨cv,cu,cg,ck⟩ := ch j G hG
    have arg (i : ℕ) (r : Reads G i) :
        valAt D (input x v u a b) j i = valAt D (input x v u c d) j i := by
      by_cases hl : i < n+j
      · apply old
        constructor
        · rintro (e|e)
          · have eq := cv (e ▸ r)
            exact hp.1 (Or.inr (by omega))
          · have eq := cg (e ▸ r) (by omega)
            omega
        · rintro (e|e)
          · have eq := cu (e ▸ r)
            exact hp.2 (Or.inr (by omega))
          · have eq := ck (e ▸ r) (by omega)
            omega
      · rw [missing (n := n) (by simp [input]) (by omega) (by omega),
            missing (n := n) (by simp [input]) (by omega) (by omega)]
    rw [arg G.left (Or.inl rfl), arg G.right (Or.inr rfl)]



private def normal (n v u g h i : ℕ) := i ≠ v ∧ i ≠ u ∧ i ≠ n+g ∧ i ≠ n+h

private lemma afterK {n : ℕ} (D : BinaryCircuit) (x : Fin n → Bool) (v u : Fin n)
    (g h k : ℕ) (ch : Channels D n v u g h k) (hg : g < k) (hh : h < k)
    (K : BinaryGate) (hK : D.gates[k]? = some K) (out : normal n v u g h D.output)
    (a b c d : Bool)
    (eq : K.op (valAt D (input x v u a b) k K.left) (valAt D (input x v u a b) k K.right) =
          K.op (valAt D (input x v u c d) k K.left) (valAt D (input x v u c d) k K.right)) :
    D.eval (input x v u a b) = D.eval (input x v u c d) := by
  have hk := (List.getElem?_eq_some_iff.mp hK).1
  have result := agree (n := n) D (input x v u a b) (input x v u c d)
    (by simp [input]) (by simp [input]) (normal n v u g h) k D.gates.length (by omega) le_rfl
  suffices H : valAt D (input x v u a b) D.gates.length D.output =
      valAt D (input x v u c d) D.gates.length D.output by
    unfold valAt wireList at H
    rw [List.take_length] at H
    exact H
  apply result _ _ D.output out
  · intro i hi
    apply before D x v u g h k ch (by omega) a b c d
    unfold keep normal at *
    tauto
  · intro j G hkj hj hG _ old
    by_cases e : j = k
    · subst j
      have eG : G = K := Option.some.inj (hG.symm.trans hK)
      subst G
      exact eq
    · obtain ⟨cv,cu,cg,ct⟩ := ch j G hG
      have arg (i : ℕ) (r : Reads G i) : normal n v u g h i := by
        refine ⟨fun ei => ?_, fun ei => ?_, fun ei => ?_, fun ei => ?_⟩
        · have := cv (ei ▸ r)
          omega
        · have := cu (ei ▸ r)
          omega
        · exact e (cg (ei ▸ r) (by omega))
        · exact e (ct (ei ▸ r) (by omega))
      rw [old _ (arg G.left (Or.inl rfl)),old _ (arg G.right (Or.inr rfl))]

private def parity (K : BinaryGate) :=
  (K.op false false = false ∧ K.op false true = true ∧ K.op true false = true ∧ K.op true true = false) ∨
  (K.op false false = true ∧ K.op false true = false ∧ K.op true false = false ∧ K.op true true = true)

private def pattern (f : Bool → Bool → Bool) :=
  f false false = f true true ∨ (∀ a b : Bool, f a b = f (!a) b) ∨ (∀ a b : Bool, f a b = f a (!b))

private lemma unary_pair (A B : Bool → Bool) (K : BinaryGate) (hk : parity K)
    (f : Bool → Bool → Bool) (tr : ∀ a b c d, K.op (A a) (B b) = K.op (A c) (B d) → f a b = f c d) :
    pattern f := by
  by_cases ha : A false = A true
  · right; left
    intro a b
    apply tr
    cases a <;> simp [ha]
  by_cases hb : B false = B true
  · right; right
    intro a b
    apply tr
    cases b <;> simp [hb]
  left
  apply tr
  rcases hk with hk|hk <;> obtain ⟨p,q,r,s⟩ := hk <;>
    cases h₀ : A false <;> cases h₁ : A true <;> cases h₂ : B false <;> cases h₃ : B true <;> simp_all



private lemma symmetric (K : BinaryGate) (hk : parity K) (l r : Bool) : K.op l r = K.op r l := by
  rcases hk with hk|hk <;> obtain ⟨p,q,s,t⟩ := hk <;> cases l <;> cases r <;> simp_all

private lemma funnel {n : ℕ} (D : BinaryCircuit) (x : Fin n → Bool) (v u : Fin n)
    (g h k : ℕ) (hne : g ≠ h) (ch : Channels D n v u g h k) (hg : g < k) (hh : h < k)
    (K : BinaryGate) (hK : D.gates[k]? = some K) (rG : Reads K (n+g)) (rH : Reads K (n+h))
    (pk : parity K) (out : normal n v u g h D.output) (f : Bool → Bool → Bool)
    (hf : ∀ a b, f a b = D.eval (input x v u a b)) : pattern f := by
  let V := fun a b i => valAt D (input x v u a b) k i
  let A := fun a => V a false (n+g)
  let B := fun b => V false b (n+h)
  have hk := (List.getElem?_eq_some_iff.mp hK).1
  have av (a b : Bool) : V a b (n+g) = A a := by
    apply before D x v u g h k ch (by omega)
    unfold keep
    constructor
    · simp
    · intro e
      rcases e with e|e <;> omega
  have bv (a b : Bool) : V a b (n+h) = B b := by
    apply before D x v u g h k ch (by omega)
    unfold keep
    constructor
    · intro e
      rcases e with e|e <;> omega
    · simp
  have norm (a b : Bool) : K.op (V a b K.left) (V a b K.right) = K.op (A a) (B b) := by
    rcases rG with l|r <;> rcases rH with l'|r'
    · omega
    · rw [l,r',av,bv]
    · rw [l',r,bv,av,symmetric K pk]
    · omega
  apply unary_pair A B K pk f
  intro a b c d e
  rw [hf a b,hf c d]
  apply afterK D x v u g h k ch hg hh K hK out
  exact (norm a b).trans (e.trans (norm c d).symm)

end PEqualNP.Outside.L698

namespace PEqualNP.Outside
open L698
theorem L_meta_698 : ∀ (n : ℕ) (D : PEqualNP.MetaComplexity.BinaryCircuit) (v u : Fin n) (g h k : ℕ), v ≠ u → g ≠ h → (∀ j : ℕ, (∃ G : PEqualNP.MetaComplexity.BinaryGate, D.gates[j]? = some G ∧ (G.left = v.val ∨ G.right = v.val)) ↔ j = g) → (∀ j : ℕ, (∃ G : PEqualNP.MetaComplexity.BinaryGate, D.gates[j]? = some G ∧ (G.left = u.val ∨ G.right = u.val)) ↔ j = h) → (∃ G : PEqualNP.MetaComplexity.BinaryGate, D.gates[g]? = some G ∧ ¬ (G.left = v.val ∧ G.right = v.val)) → (∃ G : PEqualNP.MetaComplexity.BinaryGate, D.gates[h]? = some G ∧ ¬ (G.left = u.val ∧ G.right = u.val)) → (∀ j : ℕ, (∃ G : PEqualNP.MetaComplexity.BinaryGate, D.gates[j]? = some G ∧ (G.left = n + g ∨ G.right = n + g) ∧ g < j) ↔ j = k) → (∀ j : ℕ, (∃ G : PEqualNP.MetaComplexity.BinaryGate, D.gates[j]? = some G ∧ (G.left = n + h ∨ G.right = n + h) ∧ h < j) ↔ j = k) → (∃ G : PEqualNP.MetaComplexity.BinaryGate, D.gates[k]? = some G ∧ ((G.op false false = false ∧ G.op false true = true ∧ G.op true false = true ∧ G.op true true = false) ∨ (G.op false false = true ∧ G.op false true = false ∧ G.op true false = false ∧ G.op true true = true))) → D.output ≠ v.val → D.output ≠ u.val → D.output ≠ n + g → D.output ≠ n + h → ∀ (x : Fin n → Bool) (f : Bool → Bool → Bool), (∀ a b : Bool, f a b = D.eval (List.ofFn (Function.update (Function.update x v a) u b))) → (f false false = f true true ∨ (∀ a b : Bool, f a b = f (!a) b) ∨ (∀ a b : Bool, f a b = f a (!b))) := by
  intro n D v u g h k _ hne rv ru _ _ rg rh hK ov ou og oh x f hf
  obtain ⟨K,found,pk⟩ := hK
  have ch : Channels D n v u g h k := by
    intro j G hG
    exact ⟨fun r => (rv j).mp ⟨G,hG,r⟩,fun r => (ru j).mp ⟨G,hG,r⟩,
      fun r lt => (rg j).mp ⟨G,hG,r,lt⟩,fun r lt => (rh j).mp ⟨G,hG,r,lt⟩⟩
  obtain ⟨G,hG,rG,hg⟩ := (rg k).mpr rfl
  obtain ⟨H,hH,rH,hh⟩ := (rh k).mpr rfl
  have eqG := Option.some.inj (hG.symm.trans found)
  have eqH := Option.some.inj (hH.symm.trans found)
  subst G
  subst H
  exact funnel D x v u g h k hne ch hg hh K found rG rH pk ⟨ov,ou,og,oh⟩ f hf

end PEqualNP.Outside

