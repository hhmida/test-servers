
#huggingface-cli
pip install -U "huggingface_hub[cli]"

huggingface-cli login --token "" --add-to-git-credential
# Use a pipeline as a high-level helper
from transformers import pipeline

messages = [
    {"role": "user", "content": "Who are you?"},
]
pipe = pipeline("image-text-to-text", model="meta-llama/Llama-4-Scout-17B-16E")
pipe(messages)     
# Load model directly
from transformers import AutoProcessor, AutoModelForImageTextToText

processor = AutoProcessor.from_pretrained("meta-llama/Llama-4-Scout-17B-16E")
model = AutoModelForImageTextToText.from_pretrained("meta-llama/Llama-4-Scout-17B-16E")