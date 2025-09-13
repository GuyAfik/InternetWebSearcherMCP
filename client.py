import os
import gradio as gr
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient


async def web_crawler_demo(query: str):
    config = {
        "mcpServers": {
            "playwright": {
                "command": "python",
                "args": ["main.py"],
                "cwd": os.getenv("MCP_CWD"),
                "env": {"SERPER_API_KEY": os.getenv("SERPER_API_KEY")},
            }
        }
    }
    client = MCPClient(config)
    llm = ChatOpenAI(model_name="gpt-4o-mini")
    agent = MCPAgent(client=client, llm=llm, max_steps=20)
    return await agent.run(query)


def main():
    with gr.Blocks() as demo:
        gr.Markdown("## 🌐 Web Search Interface")
        search_box = gr.Textbox(label="Enter your query")
        output_box = gr.Markdown(label="Results")
        search_box.submit(web_crawler_demo, search_box, output_box)
    demo.launch()


if __name__ == "__main__":
    main()
