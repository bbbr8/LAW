from mfese.fusion import exact_sum_solver


def test_exact_sum_solver():
    rows = [("a", 10.00), ("b", 15.50), ("c", 4.50)]
    solutions = exact_sum_solver(rows, 20.00)
    assert any(set(solution["keys"]) == {"b", "c"} for solution in solutions)
