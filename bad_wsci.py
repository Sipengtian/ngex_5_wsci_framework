## This file is a bad way of managing context. 

from pathlib import Path
from ollama import chat

MODEL = "qwen3:8b"
question = """
I changed my university password this morning.
Now my Windows laptop won't connect to campus Wi-Fi,
but my phone still wor
"""


context = ""

for file in Path("knowledge").glob("*.txt"):
    context += f"\n--- {file.name} ---\n"
    context += file.read_text(encoding="utf-8", errors="ignore")
    context += "\n\n"

## Make a call to Qwen with student's question and the context from the knowledge base.
response = chat(
    model=MODEL,
    messages=[
        {
            "role": "system",
            "content": (
                "You are a university IT support assistant. "
                "Answer the student's problem using the supplied knowledge-base context. "
                "Do not invent facts that are not supported by the context."
            ),
        },
        {
            "role": "user",
            "content": f"Student question:\n{question}\n\nKnowledge-base context:\n{context}",
        },
    ],
)


## Just for fun, print the total length of the context
print(
    "Context characters:",
    len(context)
)

## Print the response from Qwen
print(response.message.content)