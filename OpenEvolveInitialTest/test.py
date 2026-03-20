from openevolve import run_evolution, evolve_function
from openevolve.config import Config, LLMModelConfig
import time, importlib.util, asyncio
import nest_asyncio
import sys, io, os

def benchmark_fib(program_path):
    # load generated program
    spec = importlib.util.spec_from_file_location("prog", program_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fib = None
    for name in dir(module):
        if "fib" in name.lower():
            fib = getattr(module, name)
            break

    if fib is None:
        return -1e6   # not instant death

    # timing
    start = time.time()
    fib(30)
    duration = time.time() - start

    return -duration  # faster = better

def evaluator_fn(path):
    return {"combined_score": benchmark_fib(path)}

# Evolve Python functions directly
def bubble_sort(arr):
    for i in range(len(arr)):
        for j in range(len(arr)-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j] 
    return arr
if __name__=="__main__":
    try:
        asyncio.get_running_loop()
        asyncio.set_event_loop(asyncio.new_event_loop())
    except RuntimeError:
        pass

    os.environ["PYTHONIOENCODING"] = "utf-8"

    # Safe fix (works in VSCode / Jupyter / normal Python)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass  # fallback if not supported

    nest_asyncio.apply()


    # Step 2: configure OpenEvolve LLM
    config = Config()
    config.llm.models = [LLMModelConfig(
                api_base="https://openrouter.ai/api/v1",
                name="openrouter/free",
                api_key="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"
            )]

    # Evolution with inline code (no files needed!)
    result = run_evolution(
        initial_program='''
        def fibonacci(n):
            if n <= 1: return n
            return fibonacci(n-1) + fibonacci(n-2)
        ''',
        evaluator=evaluator_fn,
        iterations=100,
        config=config
    )
    print(f"Evolved fib algorithm: {result.best_code}")


    result = evolve_function(
        bubble_sort,
        test_cases=[([3,1,2], [1,2,3]), ([5,2,8], [2,5,8])],
        iterations=50,
        config=config
    )
    print(f"Evolved sorting algorithm: {result.best_code}")