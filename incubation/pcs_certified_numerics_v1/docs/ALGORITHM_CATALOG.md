# Algorithm catalog

| Algorithm | Location | Soundness basis |
|---|---|---|
| Moore interval arithmetic | Lean + Python | `mem_*` theorems / differential tests |
| Natural interval extension | `expr/eval.py` | Structural induction on AST (Lean pending) |
| Mean-value form | `expr/eval.py` | Gradient interval + MVT (classical; Lean pending) |
| Forward AD | `ad/forward.py` | Symbolic rules for +,-,*,/,pow |
| Root isolation (bisection + sign + derivative) | `root/isolation.py` | IVT + strict monotonicity |
| Global BnB | `opt/branch_bound.py` | Enclosure lowers + coverage leaves |
| Certified exp | `ode/exp_enclosure.py` | Taylor + geometric tail |
| Linear scalar ODE | `ode/euler.py` | Closed form + exp enclosure |
| Gershgorin | `linalg/basic.py` | Classical disk theorem |
| Markov exact arithmetic | `stochastic/markov.py` | Rational row-stochastic algebra |
| Thermo Z enum/bins | `thermo/partition.py` | Monotone exp in energy for β≥0 |
