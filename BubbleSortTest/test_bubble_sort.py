from openevolve import run_evolution
from openevolve.config import Config, LLMModelConfig


# Initial program: a deliberately slow bubble sort for evolution to improve
INITIAL_PROGRAM = """
# EVOLVE-BLOCK-START
def sort_array(arr):
    \"\"\"Sort an array of numbers in ascending order.\"\"\"
    arr = arr.copy()
    for i in range(len(arr)):
        for j in range(len(arr) - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
# EVOLVE-BLOCK-END
"""

# Self-contained evaluator as a code string so it works in subprocesses.
# Tests correctness on many cases AND measures runtime on large arrays,
# so there is real pressure to discover faster algorithms (quicksort, mergesort, etc.)
EVALUATOR = """
import importlib.util
import time
import random

# Reproducible test data
random.seed(42)
_random_arr = random.sample(range(100), 30)

# Correctness test cases: edge cases + varied inputs
CORRECTNESS_TESTS = [
    # Empty and single element
    ([], []),
    ([1], [1]),
    # Already sorted
    ([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]),
    # Reverse sorted
    ([5, 4, 3, 2, 1], [1, 2, 3, 4, 5]),
    # Duplicates
    ([3, 1, 2, 1, 3], [1, 1, 2, 3, 3]),
    # All same
    ([7, 7, 7, 7], [7, 7, 7, 7]),
    # Negative numbers
    ([-3, -1, -2, 0, 2], [-3, -2, -1, 0, 2]),
    # Two elements
    ([2, 1], [1, 2]),
    # Large range of values
    ([100, -50, 0, 99, -99, 50], [-99, -50, 0, 50, 99, 100]),
    # Medium arrays
    (list(range(20, 0, -1)), list(range(1, 21))),
    ([9, 3, 7, 1, 5, 8, 2, 6, 4, 0], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
    # Random medium array
    (_random_arr, sorted(_random_arr)),
]

# Performance test: large arrays that expose O(n^2) vs O(n log n) difference
random.seed(123)
PERF_ARRAYS = [
    list(range(500, 0, -1)),            # worst case reverse sorted
    random.sample(range(2000), 1000),   # random 1000 elements
    list(range(1000)),                  # best case already sorted
]

def evaluate(program_path):
    spec = importlib.util.spec_from_file_location("evolved", program_path)
    if spec is None or spec.loader is None:
        return {"combined_score": 0.0, "error": "Failed to load"}

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        return {"combined_score": 0.0, "error": str(e)}

    if not hasattr(module, "sort_array"):
        return {"combined_score": 0.0, "error": "sort_array not found"}

    sort_fn = module.sort_array

    # --- Correctness ---
    correct = 0
    total = len(CORRECTNESS_TESTS)
    errors = []
    for inp, expected in CORRECTNESS_TESTS:
        try:
            result = sort_fn(inp[:])  # pass a copy
            if result == expected:
                correct += 1
            else:
                errors.append(f"{inp[:5]}...: got {result[:5]}...")
        except Exception as e:
            errors.append(f"{inp[:5]}...: {e}")

    correctness = correct / total if total > 0 else 0.0

    # If not fully correct, don't bother with performance
    if correctness < 1.0:
        return {
            "combined_score": correctness * 0.5,
            "correctness": correctness,
            "speed_score": 0.0,
            "runtime": 999.0,
            "tests_passed": correct,
            "total_tests": total,
            "errors": errors[:5],
        }

    # --- Performance ---
    total_time = 0.0
    for arr in PERF_ARRAYS:
        start = time.perf_counter()
        try:
            sort_fn(arr[:])
        except Exception:
            return {
                "combined_score": 0.5,
                "correctness": 1.0,
                "speed_score": 0.0,
                "runtime": 999.0,
                "errors": ["crashed on large input"],
            }
        total_time += time.perf_counter() - start

    # Score: correctness (50%) + speed (50%)
    # Bubble sort on these inputs takes ~0.5-2s; quicksort/mergesort ~0.01-0.05s
    # Map runtime to a 0-1 speed score: faster = higher
    speed_score = max(0.0, min(1.0, 1.0 - (total_time / 2.0)))

    return {
        "combined_score": 0.5 * correctness + 0.5 * speed_score,
        "correctness": correctness,
        "speed_score": speed_score,
        "runtime": round(total_time, 4),
        "tests_passed": correct,
        "total_tests": total,
    }
"""


if __name__ == "__main__":
    config = Config()

    # LLM setup - using OpenRouter
    config.llm.models = [
        LLMModelConfig(
            api_base="https://openrouter.ai/api/v1",
            name="openrouter/free",
            api_key="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"
        )
    ]

    # Island-based evolution: 2 islands
    config.database.num_islands = 2
    config.database.migration_interval = 10
    config.database.migration_rate = 0.2

    # Feature dimensions: code complexity + speed score from evaluator
    config.database.feature_dimensions = ["complexity", "speed_score"]
    config.database.feature_bins = {"complexity": 5, "speed_score": 5}

    # Parallel: 2 worker processes
    config.evaluator.parallel_evaluations = 2

    result = run_evolution(
        initial_program=INITIAL_PROGRAM,
        evaluator=EVALUATOR,
        iterations=10,
        config=config,
        output_dir="openevolve_output",
        cleanup=False,
    )
    print(f"\nBest score: {result.best_score}")
    print(f"Metrics: {result.metrics}")
    print(f"\nEvolved sorting algorithm:\n{result.best_code}")
