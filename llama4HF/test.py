from transformers import pipeline

messages = [
    {"role": "user", "content": "Who are you?"},
]
pipe = pipeline("image-text-to-text", model="meta-llama/Llama-4-Scout-17B-16E")
pipe(messages)     