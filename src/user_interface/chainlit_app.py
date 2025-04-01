import os
import json
import yaml
import chainlit as cl
from chainlit.input_widget import TextInput, Slider, Select, NumberInput
from src.langgraphs.workflow import create_graph, compile_workflow

author = "Assistant"  # Default author name

def update_config(serper_api_key, openai_llm_api_key):
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
    
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    # Update config with API keys
    config['SERPER_API_KEY'] = serper_api_key
    config['OPENAI_API_KEY'] = openai_llm_api_key
    
    # Update environment
    if serper_api_key:
        os.environ['SERPER_API_KEY'] = serper_api_key
    if openai_llm_api_key:
        os.environ['OPENAI_API_KEY'] = openai_llm_api_key
    
    with open(config_path, 'w') as file:
        yaml.safe_dump(config, file)

class ChatWorkflow:
    def __init__(self):
        self.workflow = None
        self.recursion_limit = 40

    def build_workflow(self, server, model, model_endpoint, temperature, recursion_limit=40, stop=None):
        graph = create_graph(
            server=server,
            model=model,
            model_endpoint=model_endpoint,
            temperature=temperature,
            stop=stop
        )
        self.workflow = compile_workflow(graph)
        self.recursion_limit = recursion_limit

    def invoke_workflow(self, message):
        if not self.workflow:
            return "Workflow has not been built yet. Please update settings first."
        
        dict_inputs = {"research_question": message.content}
        limit = {"recursion_limit": self.recursion_limit}

        for event in self.workflow.stream(dict_inputs, limit):
            if "final_response" in event:
                return event["final_response"]

        return "Workflow did not complete successfully"

chat_workflow = ChatWorkflow()

@cl.on_chat_start
async def start():
    global author
    await cl.ChatSettings(
        [
            Select(
                id="server",
                label="Select the server you want to use:",
                values=["ollama", "openai"],
                initial="ollama"
            ),
            TextInput(
                id='llm_model',
                label='Model Name:',
                description="The name of the model to use",
                initial="llama3.1"
            ),
            TextInput(
                id='server_endpoint',
                label='Server endpoint:',
                description="Only needed for custom server setups",
                initial=""
            ),
            TextInput(
                id='stop_token',
                label='Stop token:',
                description="Token to stop generation",
                initial="<|end_of_text|>"
            ),
            Slider(
                id='temperature',
                label='Temperature:',
                initial=0,
                max=1,
                step=0.05,
                description="Controls response randomness"
            ),
            NumberInput(
                id="recursion_limit",
                label="Recursion limit:",
                description="Maximum workflow steps",
                initial=40
            ),
            TextInput(
                id="serper_api_key",
                label="Serper API Key:",
                description="For web search capability"
            ),
            TextInput(
                id='openai_api_key',
                label='OpenAI API Key:',
                description="Only if using OpenAI"
            )
        ]
    ).send()
    
    chat_workflow.build_workflow("ollama", "llama3.1", None, 0)
    await cl.Message(content="🚀 System initialized!").send()

@cl.on_settings_update
async def update_settings(settings):
    global author
    try:
        # Update API keys
        update_config(
            settings["serper_api_key"],
            settings["openai_api_key"]
        )
        
        # Update workflow
        server = settings["server"]
        model = settings["llm_model"]
        endpoint = settings["server_endpoint"]
        temp = settings["temperature"]
        limit = settings["recursion_limit"]
        stop = settings["stop_token"]
        
        author = settings["llm_model"]
        
        await cl.Message(content="⚙️ Updating configuration...").send()
        chat_workflow.build_workflow(
            server, model, endpoint, temp, limit, stop
        )
        await cl.Message(content="✅ Configuration updated!").send()
        
    except Exception as e:
        await cl.Message(
            content=f"⚠️ Settings update failed: {str(e)}", 
            author="System"
        ).send()

@cl.on_message
async def main(message: cl.Message):
    global author
    try:
        response = await cl.make_async(chat_workflow.invoke_workflow)(message)
        if not response:
            response = "No response generated. Check settings."
        await cl.Message(content=response, author=author).send()
    except Exception as e:
        await cl.Message(
            content=f"❌ Error: {str(e)}", 
            author="System"
        ).send() 