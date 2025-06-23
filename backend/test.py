from transformers import AutoTokenizer

model_id = "mistral/mistral-7b-instruct-v0.3"
tokenizer = AutoTokenizer.from_pretrained(model_id)

print(tokenizer.chat_template)
