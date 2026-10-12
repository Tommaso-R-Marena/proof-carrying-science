"""Prospective public mathematical transfer; never includes reference proofs.

Primitive laws are shared foundations, explicitly not disjoint mathematical
universes. Splits separate composed theorem families and alpha-equivalent goals.
"""
from .induction_language import formalize
from .data import structural_fingerprint

STATEMENTS = [
 ('train','length_append','list_length','For all lists of natural numbers xs and ys, the length of (xs appended to ys) equals (the length of xs + the length of ys).'),
 ('train','append_assoc','list_association','For all lists of natural numbers xs, ys and zs, ((xs appended to ys) appended to zs) equals (xs appended to (ys appended to zs)).'),
 ('train','nat_left_cancel','nat_cancellation','For all natural numbers a, b and c, if (a + b) equals (a + c) then b equals c.'),
 ('train','successor_injective','nat_injectivity','For all natural numbers a and b, if the successor of a equals the successor of b then a equals b.'),
 ('train','reverse_length','list_reverse_length','For all lists of natural numbers xs, the length of (the reversal of xs) equals the length of xs.'),
 ('train','reverse_append','list_reverse_append','For all lists of natural numbers xs and ys, the reversal of (xs appended to ys) equals ((the reversal of ys) appended to (the reversal of xs)).'),
 ('train','nat_distribution','nat_distributivity','For all natural numbers a, b and c, a * (b + c) equals ((a * b) + (a * c)).'),
 ('train','logical_rule','logic_transitivity','For all propositions P, Q and R, if ((P implies Q) and (Q implies R)) then (P implies R).'),
 ('train','nat_order_cancel','nat_order_cancellation','For all natural numbers a, b and c, if (a + c) ≤ (b + c) then a ≤ b.'),
 ('train','list_right_cancel','list_cancellation','For all lists of natural numbers xs, ys and zs, if (xs appended to zs) equals (ys appended to zs) then xs equals ys.'),
 ('utility','reverse_append_length','reverse_append_size','For all lists of natural numbers xs and ys, the length of (the reversal of (xs appended to ys)) equals (the length of xs + the length of ys).'),
 ('utility','triple_append_length','triple_size','For all lists of natural numbers xs, ys and zs, the length of ((xs appended to ys) appended to zs) equals ((the length of xs + the length of ys) + the length of zs).'),
 ('utility','cancel_successors','cancel_constructor','For all natural numbers a, b and c, if (a + the successor of b) equals (a + the successor of c) then b equals c.'),
 ('utility','context_distribution','distribution_context','For all natural numbers a, b and c, the successor of (a * (b + c)) equals the successor of ((a * b) + (a * c)).'),
 ('utility','order_successors','order_constructor','For all natural numbers a, b and c, if (the successor of a + c) ≤ (the successor of b + c) then a ≤ b.'),
 ('utility','reverse_append_cancel','reverse_list_cancel','For all lists of natural numbers xs, ys and zs, if ((the reversal of xs) appended to zs) equals ((the reversal of ys) appended to zs) then xs equals ys.'),
 ('selection','double_reverse_append_size','nested_reverse_size','For all lists of natural numbers xs and ys, the length of (the reversal of (the reversal of (xs appended to ys))) equals (the length of xs + the length of ys).'),
 ('selection','cancel_rule_chain','cancellation_chain','For all natural numbers a, b and c, if ((a + b) equals (a + c) and (b equals 0)) then c equals 0.'),
 ('selection','associated_reverse','reverse_association','For all lists of natural numbers xs, ys and zs, the reversal of ((xs appended to ys) appended to zs) equals ((the reversal of zs) appended to ((the reversal of ys) appended to (the reversal of xs))).'),
 ('selection','order_rule_chain','order_cancellation_chain','For all natural numbers a, b and c, if (((a + c) ≤ (b + c)) and (b ≤ a)) then a equals b.'),
 ('selection','false_size','negative_size','For all lists of natural numbers xs, the length of xs equals 0.'),
 ('selection','false_nat','negative_successor','For all natural numbers n, the successor of n equals n.'),
 ('final','reverse_size_bundle','final_reversed_size_bundle','For all lists of natural numbers xs and ys, ((the length of (the reversal of (xs appended to ys)) equals (the length of xs + the length of ys)) and (the reversal of (the reversal of ys) equals ys)).'),
 ('final','four_train_length','final_four_train_size','For all lists of natural numbers xs, ys, zs and ws, the length of ((xs appended to ys) appended to (zs appended to ws)) equals ((the length of xs + the length of ys) + (the length of zs + the length of ws)).'),
 ('final','cancel_under_function','final_cancellation_function','For all functions from natural numbers to natural numbers f, (∀ (a : Nat), ∀ (b : Nat), ∀ (c : Nat), ((a + b) equals (a + c)) implies (f(b) equals f(c))).'),
 ('final','two_cancel_chain','final_nested_cancellation','For all natural numbers a, b, c and d, if (a + (b + c)) equals (a + (b + d)) then c equals d.'),
 ('final','reverse_length_transport','final_reverse_length_transport','For all lists of natural numbers xs and ys, if xs equals ys then the length of (the reversal of xs) equals the length of ys.'),
 ('final','list_double_cancel','final_nested_list_cancellation','For all lists of natural numbers xs, ys, zs and ws, if ((xs appended to ys) appended to zs) equals ((xs appended to ws) appended to zs) then ys equals ws.'),
 ('final','double_distribution','final_two_distributive_contexts','For all natural numbers a, b, c and d, a * ((b + c) + d) equals (((a * b) + (a * c)) + (a * d)).'),
 ('final','order_succ_cancel','final_order_two_constructors','For all natural numbers a, b and c, if (the successor of (the successor of a) + c) ≤ (the successor of (the successor of b) + c) then a ≤ b.'),
 ('final','predicate_cancel','final_predicate_transport','For all predicates on natural numbers P, (∀ (a : Nat), ∀ (b : Nat), ∀ (c : Nat), (((a + b) equals (a + c)) and P(b)) implies P(c)).'),
 ('final','empty_suffix','final_list_empty_suffix','For all lists of natural numbers xs and ys, if (xs appended to ys) equals xs then ys equals the empty list.'),
 ('final','false_reverse','final_negative_reversal','For all lists of natural numbers xs, the reversal of xs equals xs.'),
 ('final','false_order','final_negative_order','For all natural numbers a and b, if a ≤ b then b ≤ a.'),
 ('train','predicate_induction','predicate_induction_principle','For all predicates on natural numbers P, if (P(0) and (∀ (k : Nat), P(k) implies P(the successor of k))) then (∀ (n : Nat), P(n)).'),
 ('train','function_unit_recurrence','unit_recurrence','For all functions from natural numbers to natural numbers f, if (∀ (k : Nat), f(the successor of k) equals (f(k) + 1)) then (∀ (n : Nat), f(n) equals (f(0) + n)).'),
 ('utility','predicate_double_index','predicate_index_transfer','For all predicates on natural numbers P, if (P(0) and (∀ (k : Nat), P(k) implies P(the successor of k))) then (∀ (n : Nat), P(n + n)).'),
 ('utility','function_double_index','recurrence_index_transfer','For all functions from natural numbers to natural numbers f, if (∀ (k : Nat), f(the successor of k) equals (f(k) + 1)) then (∀ (n : Nat), f(n + n) equals (f(0) + (n + n))).'),
 ('selection','predicate_shift_index','predicate_shift','For all predicates on natural numbers P, if (P(0) and (∀ (k : Nat), P(k) implies P(the successor of k))) then (∀ (n : Nat), P(the successor of n)).'),
 ('selection','function_shift_index','recurrence_shift','For all functions from natural numbers to natural numbers f, if (∀ (k : Nat), f(the successor of k) equals (f(k) + 1)) then (∀ (n : Nat), f(the successor of n) equals (f(0) + the successor of n)).'),
 ('final','general_function_recurrence','final_parametric_recurrence','For all functions from natural numbers to natural numbers f, (∀ (d : Nat), (∀ (k : Nat), f(the successor of k) equals (f(k) + d)) implies (∀ (n : Nat), f(n) equals (f(0) + (n * d)))).'),
 ('final','function_zero_invariant','final_function_invariant','For all functions from natural numbers to natural numbers f, if ((f(0) equals 0) and (∀ (k : Nat), (f(k) equals 0) implies (f(the successor of k) equals 0))) then (∀ (n : Nat), f(n) equals 0).'),
 ('final','predicate_square_index','final_polynomial_index','For all predicates on natural numbers P, if (P(0) and (∀ (k : Nat), P(k) implies P(the successor of k))) then (∀ (n : Nat), P(n * n)).'),
 ('final','function_triple_index','final_recurrence_composed_index','For all functions from natural numbers to natural numbers f, if (∀ (k : Nat), f(the successor of k) equals (f(k) + 1)) then (∀ (n : Nat), f((n + n) + n) equals (f(0) + ((n + n) + n))).'),
]

def tasks():
    result=[]
    for split,identity,family,statement in STATEMENTS:
        parsed=formalize(statement)
        if parsed['status']!='supported':
            raise ValueError(f'Unsupported prospective task {identity}: {parsed["status"]}')
        result.append({'id':identity,'family':family,'split':split,'goal':parsed['candidates'][0]['ir'],
                       'original_statement':statement,'license':'Apache-2.0',
                       'source':'PCS authored public verified-memory benchmark'})
    hashes=[structural_fingerprint(t['goal']) for t in result]
    if len(hashes)!=len(set(hashes)):raise ValueError('alpha duplicate across splits')
    return result
