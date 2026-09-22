from pathlib import Path
from ollama import chat

MODEL = "qwen3:8b" 
question = """
I changed my university password this morning.
Now my Windows laptop won't connect to campus Wi-Fi,
but my phone still works.
"""
manual_patterns = [
    "*wifi*.txt",
    "*wi-fi*.txt",
    "*wireless*.txt",
    "*password*.txt",
    "*windows*.txt",
]

selected_files = []
for pattern in manual_patterns:
    for file in Path("knowledge").glob(pattern):
        if file not in selected_files:
            selected_files.append(file)

if not selected_files:
    raise FileNotFoundError(
        "No relevant knowledge files were found. "
        "For the strictly manual version, replace manual_patterns with the exact "
        "relevant filenames from your knowledge/ folder."
    )


context = ""


## Write a for loop to go through all the files in selected_files and read their contents into the context variable.
for file in selected_files:
    context += f"\n--- {file.name} ---\n"
    context += file.read_text(encoding="utf-8", errors="ignore")
    context += "\n\n"

## Call Qwen with the student's question and the context you created above.
response = chat(
    model=MODEL,
    messages=[
        {
            "role": "system",
            "content": (
                "You are a university IT support assistant. "
                "Use only the supplied selected context to answer the student's problem."
            ),
        },
        {
            "role": "user",
            "content": f"Student question:\n{question}\n\nSelected context:\n{context}",
        },
    ],
)

print("Selected files:")
for file in selected_files:
    print("-", file)
    
print(
    "Context characters:",
    len(context)
)
print(response.message.content)