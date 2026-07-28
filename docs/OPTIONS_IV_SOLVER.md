# Options IV Solver

`lib/options_iv_solver.py` uses bracketed bisection. It expands the upper volatility bound when needed and returns explicit error reasons instead of fabricating a value.

Failure reasons include missing premium, non-positive target price, target below lower model bound, target above upper model bound, pricing failure, and max iterations reached.

Options and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, or execution instructions.
