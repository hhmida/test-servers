# Deploy with docker on Linux:
docker run --runtime nvidia --gpus all --name my_vllm_container -v ~/.cache/huggingface:/root/.cache/huggingface --env HUGGING_FACE_HUB_TOKEN="" -p 8000:8000 --ipc=host vllm/vllm-openai:latest --model meta-llama/Llama-4-Scout-17B-16E

# Load and run the model:
docker exec -it my_vllm_container bash -c "vllm serve meta-llama/Llama-4-Scout-17B-16E"   Copy  # Call the server using curl:
curl -X POST "http://localhost:8000/v1/chat/completions" \
	-H "Content-Type: application/json" \
	--data '{
		"model": "meta-llama/Llama-4-Scout-17B-16E",
		"messages": [
			{
				"role": "user",
				"content": [
					{
						"type": "text",
						"text": "Describe this image in one sentence."
					},
					{
						"type": "image_url",
						"image_url": {
							"url": "https://cdn.britannica.com/61/93061-050-99147DCE/Statue-of-Liberty-Island-New-York-Bay.jpg"
						}
					}
				]
			}
		]
	}'