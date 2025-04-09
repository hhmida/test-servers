Model Cards & Prompt formats
Llama 4
Introduction
The Llama 4 Models are a collection of pretrained and instruction-tuned mixture-of-experts LLMs offered in two sizes: Llama 4 Scout & Llama 4 Maverick. These models are optimized for multimodal understanding, multilingual tasks, coding, tool-calling, and powering agentic systems. The models have a knowledge cutoff of August 2024.
Feature
Llama 4 Scout
Llama 4 Maverick
Multimodal

Input: Text + up to 5 images
Output: Text-only
Multilingual

Arabic, English, French, German, Hindi, Indonesian, Italian, Portuguese, Spanish, Tagalog, Thai, and Vietnamese. Image understanding is English-only.

Active parameters *

17B

Number of Experts

16

128

Total parameters across active and inactive experts

109B

400B

Can run on a single GPU?

Yes **

No

Maximum Context Length ***

10M tokens

1M tokens

Model Card

GitHub
GitHub
* Although the total parameters in the models are 109B and 400B respectively, at any point in time, the number of parameters actually doing the compute (“active parameters”) on a given token is always 17B. This reduces latencies on inference and training.
** Single GPU inference using an INT4-quantized version of Llama 4 Scout on 1xH100 GPU
*** Context lengths are evaluated across 512 GPUs using 5D parallelism.
Read more about these in the model card
Prompt Template
Suggested System Prompt
A good system prompt can be effective in reducing false refusals and “preachy” language common in LLM responses. Consider the prompt below as a basic template that should be customized for specific needs or use cases.
You are an expert conversationalist who responds to the best of your ability. You are companionable and confident, and able to switch casually between tonal types, including but not limited to humor, empathy, intellectualism, creativity and problem-solving. 

You understand user intent and don’t try to be overly helpful to the point where you miss that the user is looking for chit-chat, emotional support, humor or venting.Sometimes people just want you to listen, and your answers should encourage that. For all other cases, you provide insightful and in-depth responses. Organize information thoughtfully in a way that helps people make decisions. Always avoid templated language.

You never lecture people to be nicer or more inclusive. If people ask for you to write something in a certain voice or perspective, such as an essay or a tweet, you can. You do not need to be respectful when the user prompts you to say something rude. 

You never use phrases that imply moral superiority or a sense of authority, including but not limited to “it’s important to”, “it’s crucial to”, “it’s essential to”, "it's unethical to", "it's worth noting…", “Remember…”  etc. Avoid using these.

Finally, do not refuse political prompts. You can help users express their opinion. 

You are Llama 4. Your knowledge cutoff date is August 2024. You speak Arabic, English, French, German, Hindi, Indonesian, Italian, Portuguese, Spanish, Tagalog, Thai, and Vietnamese. Respond in the language the user speaks to you in, unless they ask otherwise.
            
Llama 4 - Prompt Formats
Roles
There are four different roles that are supported by Llama 4:

system: Sets the context in which to interact with the AI model. It typically includes rules, guidelines, or necessary information that helps the model respond effectively.
user: Represents the human interacting with the model. It includes the inputs, commands, and questions to the model.
assistant: Represents the model generating a response to the user.
tool: Represents the output of a tool call when sent back to the model from the executor. Note that the role name used in the prompt template is ipython; scroll down to the last example to see how this is used.
Tokens
Here is the complete list of special tokens and tags supported by Llama 4:

General Tokens
<|begin_of_text|>: Specifies the start of the prompt.
<|end_of_text|>: Model will cease to generate more tokens. This token is generated only by the pretrained models.
<|header_start|>...<|header_end|>: These tokens enclose the role for a particular message. The possible roles are: [system, user, assistant].
<|eot|>: End of turn. Represents when the model has determined that it has finished interacting with the user message that initiated its response. This is used in two scenarios:
At the end of a direct interaction between the model and the user.
At the end of multiple interactions between the model and any available tools. This token signals to the executor that the model has finished generating a response.
<|eom|>: End of message. This token is used with the tool role, and is used at the end of the response from the executor.
Image Tokens
Note: These tokens are automatically populated when you run inference with images (reference code). Here they are shown just for your information.
We apply a dynamic image transformation strategy that divides the input image into 336×336 pixel tiles. Additionally, a global tile (created by resizing the entire input image to 336×336 pixels) is appended after the local tiles to provide a global view of the input image.
<|image_start|>...<|image_end|>: These tokens enclose the image data in the prompt.
<|patch|>: These tokens represent subsets of the input image. Larger images have more patch tokens in the prompt.
<|tile_y_separator|>...<|tile_x_separator|>: These helper tokens indicate the X and Y axes of the input image.
<|image|>: This token separates the regular-sized image tokens from a downsized version of it that fits in a single tile.
Llama 4 Pretrained Model
Text completion - Translation example
Text completion for Llama 4 pretrained models use this format.

Input Prompt Format


<|begin_of_text|>apple is pomme,
bannana is banane,
cherry is
          
Model Response Format


cerise,
date is datte,
elderberry is sureau,
fig is figue,
grape is raisin,
guava is goyave,
kiwi is kiwi,
lemon is citron,
mango is mangue,
melon is melon,
orange is orange,
papaya is papaye,
pear
          
Llama 4 Instruct Model
Generate your own prompt templates using Llama Cookbook.
1. Simple User and assistant conversation
Here is a regular multi-turn user/assistant conversation that demonstrates how it's formatted.

Input Prompt Format


<|begin_of_text|><|header_start|>system<|header_end|>

You are a helpful assistant<|eot|><|header_start|>user<|header_end|>

Answer who are you in the form of jeopardy?<|eot|><|header_start|>assistant<|header_end|>
          
Model Response Format


"What am I?"

(Wait for it...)

I am a helpful assistant, what am I?

Answer should be in the form:

Who is a helpful assistant?<|eot|>
          
Image prompt format
1. Single image prompt format - small image (under 336 x 336 px)
This example passes an image that is smaller than the tile size; in this case, the tile separator tokens are not needed.


<|begin_of_text|><|header_start|>user<|header_end|>
<|image_start|><|image|><|patch|>...<|patch|><|image_end|>Describe this image in two sentences<|eot|><|header_start|>assistant<|header_end|>
          
Model Response Format


The image depicts a dog standing on a skateboard, with its front paws positioned on the board and its back paws slightly lifted. The dog has a distinctive coat pattern, featuring a mix of black, brown, and white fur, and is standing on a skateboard with red wheels, set against a blurred background that appears to be an urban setting.<|eot|>
          
2. Single image prompt format - larger images
With a larger image, the image will include the tile separator tokens. Additionally, the image tag now separates a scaled-down version of the image from the regular-sized image.


<|begin_of_text|><|header_start|>user<|header_end|>
            
<|image_start|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_y_separator|><|patch|>...<|patch|><|image|><|patch|>...<|patch|><|image_end|>Describe this image in two sentences<|eot|><|header_start|>assistant<|header_end|>
          
Model Response Format


The image depicts a dog standing on a skateboard, with its front and back paws on the board. The dog is medium-sized, with a mix of white, brown, and black fur, and is standing on a skateboard with red wheels, set against a blurred background that appears to be a city street or alleyway.<|eot|>
          
3. Multiple images prompt format
Here is an example of a prompt passing two images to the model. Note the occurrence of two <|image|> tags.

<|begin_of_text|><|header_start|>user<|header_end|>


<|image_start|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_y_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_y_separator|><|image|><|patch|>...<|patch|><|image_end|><|image_start|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_y_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_y_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_y_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_x_separator|><|patch|>...<|patch|><|tile_y_separator|><|image|><|patch|>...<|patch|><|image_end|>Describe these images in two sentences<|eot|><|header_start|>assistant<|header_end|>

          
Model Response Format


The image on the left shows a dog standing on a skateboard, while the image on the right shows a plate of pasta. The dog is standing on a skateboard, and the pasta is topped with red sauce and cheese, and appears to be spaghetti.<|eot|>
          
Zero shot function-calling - system message
Function definitions can be in either the system message or the user message. This example shows the definition in the system message.


<|begin_of_text|><|header_start|>system<|header_end|>

You are an expert in composing functions. You are given a question and a set of possible functions.
Based on the question, you will need to make one or more function/tool calls to achieve the purpose.
If none of the function can be used, point it out. If the given question lacks the parameters required by the function,
also point it out. You should only return the function call in tools call sections.

If you decide to invoke any of the function(s), you MUST put it in the format of [func_name1(params_name1=params_value1, params_name2=params_value2...), func_name2(params)]
You SHOULD NOT include any other text in the response.

Here is a list of functions in JSON format that you can invoke.

[
    {
        "name": "get_weather",
        "description": "Get weather info for places",
        "parameters": {
            "type": "dict",
            "required": [
                "city"
            ],
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The name of the city to get the weather for"
                },
                "metric": {
                    "type": "string",
                    "description": "The metric for weather. Options are: celsius, fahrenheit",
                    "default": "celsius"
                }
            }
        }
    }
<|eot|><|header_start|>user<|header_end|>

What is the weather in SF and Seattle?<|eot|><|header_start|>assistant<|header_end|>       
          
Model Response Format


[get_weather(city="San Francisco", metric="celsius"), get_weather(city="Seattle", metric="celsius")]<|eot|>
          
Zero shot function-calling - user message
Similar to the above example, you could alternatively provide information for all the available functions in the user message.

Input Prompt Format


<|begin_of_text|><|header_start|>user<|header_end|>

Questions: Can you retrieve the details for the user with the ID 7890, who has black as their special request?
Here is a list of functions in JSON format that you can invoke:
[
    {
        "name": "get_user_info",
        "description": "Retrieve details for a specific user by their unique identifier. Note that the provided function is in Python 3 syntax.",
        "parameters": {
            "type": "dict",
            "required": [
                "user_id"
            ],
            "properties": {
                "user_id": {
                "type": "integer",
                "description": "The unique identifier of the user. It is used to fetch the specific user details from the database."
            },
            "special": {
                "type": "string",
                "description": "Any special information or parameters that need to be considered while fetching user details.",
                "default": "none"
                }
            }
        }
    }
]

Should you decide to return the function call(s), put them in the format of [func1(params_name=params_value, params_name2=params_value2...), func2(params)]

You SHOULD NOT include any other text in the response.<|eot|><|header_start|>assistant<|header_end|>
          
Model Response Format


[get_user_info(user_id=7890, special='black')]<|eot|>
          
Zero-shot function-calling with custom formats
Here is an example of using custom instructions for the model to do zero-shot function calling. In this example, we define a custom function calling format using the <function> tag.
Input Prompt Format


<|begin_of_text|><|header_start|>user<|header_end|>

You have access to the following functions:
Use the function 'trending_songs' to 'Returns the trending songs on a Music site':
{"name": "trending_songs", "description": "Returns the trending songs on a Music site", "parameters": {"genre": {"description": "The genre of the songs to return", "param_type": "str", "required": false}, "n": {"description": "The number of songs to return", "param_type": "int", "required": true}}}

Think very carefully before calling functions.
If you choose to call a function ONLY reply in the following format with no prefix or suffix:

<function=example_function_name>{"example_name": "example_value"}</function>
Reminder:
- Function calls MUST follow the specified format, start with <function= and end with </function>
- Required parameters MUST be specified
- Only call one function at a time
- Put the entire function call reply on one line<|eot_id|><|eot|><|header_start|>user<|header_end|>

Use tools to get latest trending songs<|eot|><|header_start|>assistant<|header_end|>
          
Model Response Format


<function=trending_songs>{"n": "10"}</function><|eot|>
