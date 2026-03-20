from openevolve import run_evolution # main function that runs evolutionary algorithm
from openevolve.config import Config, LLMModelConfig # used to configure which LLM is used
import time, importlib.util # time is used to measure performance, importlib.util is used to dynamically load python files

"""
initiate a configuration
"""
config = Config() 
config.llm.models = [LLMModelConfig( # Use a LLM
            api_base="https://openrouter.ai/api/v1", # the LLM is from OpenRouter
            name="openrouter/free", # Name
            api_key="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" # API key used to access LLM
        )]

def benchmark_fib(path): 
    """
    Fitness function-evolution depends entirely on this. Measures how long it takes for function to work
    """
    spec = importlib.util.spec_from_file_location("candidate", path) # path is file containing generated code
    module = importlib.util.module_from_spec(spec) # load the generated code
    spec.loader.exec_module(module) # execute the module

    start = time.time()
    for _ in range(3):   # 👈 run  multiple times
        result = module.fibonacci(30) # run the fibonacci code and measure performance
    end = time.time()

    if result != 6765:
        return -1e9 # check accuracy of code output, if wrong its error

    return 1 / (end - start + 1e-6) # convert time to a score

def evaluator(path):
    """
    Wraps benchmark function into format understandable by OpenEvolve
    """
    try:
        return {"combined_score": benchmark_fib(path)} # must return dictionary containing "combined_score"
    except:
        return {"combined_score": -1e9}

if __name__ == "__main__": 
    """
    Execution Block
    """
    result = run_evolution( # run the evolution
        # starting point-slow fibonacci - O(2^n)
        initial_program=""" 
def fibonacci(n):
    if n <= 1: return n
    return fibonacci(n-1) + fibonacci(n-2)
""",
        evaluator=evaluator, # defines what good means
        iterations=20, # number of evolution steps-each step, mutate code, evaluate, keep best
        config=config # passes LLM settings
    )

    print("Best evolved code:\n", result.best_code) # prints best program found