import time
import requests
import json

MODEL = "mistral"

def call_model(prompt: str):
    start = time.perf_counter()

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    end = time.perf_counter()

    data = response.json()

    return {
        "output": data["response"],
        "latency_ms": (end - start) * 1000,
        "model": MODEL
    }

def log(result, prompt):

    entry = {
        "prompt": prompt,
        "output": result["output"],
        "latency_ms": result["latency_ms"],
        "model": result["model"]
    }

    with open("logs.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


if __name__ == "__main__":

    prompt = "write a function that checks if a string is a palindrome."

    result = call_model(prompt)
    log(result, prompt)

    print(result["output"])