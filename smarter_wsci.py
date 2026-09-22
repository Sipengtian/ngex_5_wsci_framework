from pathlib import Path
from ollama import chat
import json
import re

MODEL = "qwen3:8b"
STATE_FILE = Path("state.json")


question = """
I changed my university password this morning.
Now my Windows laptop won't connect to campus Wi-Fi,
but my phone still works.
"""

## WRITE ##
service_status = {
    "wifi": "operational"
}

state = {
    "diagnostic_context": {
        "problem": question.strip(),
        "device": "Windows laptop",
        "wifi_status": service_status["wifi"]
    },

    "service_context": {
        "wifi": service_status["wifi"]
    }
}

with open("state.json", "w", encoding="utf-8") as file:
    json.dump(
        state,
        file,
        indent=2,
        ensure_ascii=False
    )

with open("state.json", "r") as file:
    state = json.load(file)

print(state)


## SELECT CONTEXT FILES BASED ON QUESTION
## Create the function that takes the student's question, takes some keywords and chooses the relevant files from the knowledge base. Return a list of the selected files.
## For example, if the question has the kyeword "print" or "printer", then the function should return the file "knowledge/printer_setup.txt" in a list.
def select_context(question):
    """Return a short list of knowledge files relevant to the student's question."""

    question_lower = question.lower()

    topic_groups = {
        "wifi": ["wifi", "wi-fi", "wireless", "network", "campus"],
        "password": ["password", "credential", "login", "account"],
        "windows": ["windows", "laptop", "pc"],
    }

    active_terms = set()
    for terms in topic_groups.values():
        if any(term in question_lower for term in terms):
            active_terms.update(terms)

    # If no predefined topic is detected, fall back to meaningful words from the question.
    if not active_terms:
        active_terms = {
            word
            for word in re.findall(r"[a-zA-Z-]+", question_lower)
            if len(word) >= 4
        }

    scored_files = []
    for path in Path("knowledge").glob("*.txt"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        searchable = f"{path.stem} {text}".lower()
        score = sum(1 for term in active_terms if term in searchable)
        if score > 0:
            scored_files.append((score, path))

    # Highest-scoring files first; keep context small.
    scored_files.sort(key=lambda item: (-item[0], item[1].name.lower()))
    return [path for _, path in scored_files[:4]]

selected_files = select_context(question)

if not selected_files:
    raise FileNotFoundError(
        "No relevant knowledge files were selected from knowledge/. "
        "Check the folder contents and keyword rules in select_context()."
    )

## READ SELECTED FILES and add their contents to the context variable.
context = ""
for file in selected_files:
    context += f"\n--- {file.name} ---\n"
    context += file.read_text(encoding="utf-8", errors="ignore")
    context += "\n\n"

## 
## COMPRESS CONTEXT
## Add logic to compress the context from above by calling Qwen with "context" and the "question" as the parameter
## The response from Qwen should be the compressed context. Store it in a variable called "compressed_context" 

def compress_context(context, question):
    compression_response = chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Compress the supplied knowledge-base context for a university IT support task. "
                    "Keep only facts and troubleshooting steps that are relevant to the student's question. "
                    "Do not answer the student yet and do not add new facts."
                ),
            },
            {
                "role": "user",
                "content": f"Student question:\n{question}\n\nContext to compress:\n{context}",
            },
        ],
    )
    return compression_response.message.content.strip()


compressed_context = compress_context(context, question)

print("Selected files:")
for file in selected_files:
    print("-", file)
print("Original context characters:", len(context))
print("Compressed context characters:", len(compressed_context))



## Print the length of the compressed context
print(len(compressed_context))

## Now, call Qwen again with the compressed context and the student's question. Store the response in a variable called "response" and print the response from Qwen.
## Ensure the model produces a structured output 
response = chat(
    model="qwen3:8b",
    format="json",
    messages=[
        {
            "role": "system",
            "content": """
You are a university IT support assistant.

Use only the provided context to answer the student's problem.

Return the answer as JSON with these fields:
- problem
- likely_cause
- solution_steps
"""
        },
        {
            "role": "user",
            "content": f"""
Student problem:

{question}

Relevant compressed context:

{compressed_context}
"""
        }
    ]
)




print(response.message.content)

## WRITE the above output in an artifact called "state"
with STATE_FILE.open("r", encoding="utf-8") as file:
    state = json.load(file)

state["diagnostic_context"].update(
    {
        "selected_files": [str(path) for path in selected_files],
        "compressed_context": compressed_context,
    }
)

with STATE_FILE.open("w", encoding="utf-8") as file:
    json.dump(state, file, indent=2, ensure_ascii=False)

## Update the rest of the code so that it uses the "state" artifact as part of the context. 
## It is important to ensure that the model uses only the relevant parts from the "state" artifact and not the entire artifact.
## For this, you may have to think of a good structure for the "state" artifact and how to use it in the context.
def isolate_state(state, task):
    if task == "diagnostic":
        return state["diagnostic_context"]
    if task == "service_status":
        return state["service_context"]
    raise ValueError(f"Unknown task: {task}")


# Re-read the artifact to demonstrate that the program actually uses state.json.
with STATE_FILE.open("r", encoding="utf-8") as file:
    stored_state = json.load(file)

relevant_state = isolate_state(stored_state, "diagnostic")

response = chat(
    model=MODEL,
    format="json",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a university IT support assistant. "
                "Use only the supplied diagnostic state and compressed knowledge context. "
                "Return valid JSON with exactly these keys: "
                "problem_summary, likely_cause, troubleshooting_steps, escalation. "
                "troubleshooting_steps must be a JSON array of strings. "
                "Do not invent unsupported facts."
            ),
        },
        {
            "role": "user",
            "content": (
                "Relevant diagnostic state:\n"
                f"{json.dumps(relevant_state, indent=2, ensure_ascii=False)}\n\n"
                "Student question:\n"
                f"{question}"
            ),
        },
    ],
)

# Keep a structured Python object whenever Qwen returns valid JSON.
try:
    structured_output = json.loads(response.message.content)
except json.JSONDecodeError:
    structured_output = {
        "raw_model_output": response.message.content
    }

print(json.dumps(structured_output, indent=2, ensure_ascii=False))

with STATE_FILE.open("r", encoding="utf-8") as file:
    state = json.load(file)

state["diagnostic_context"]["model_output"] = structured_output

with STATE_FILE.open("w", encoding="utf-8") as file:
    json.dump(state, file, indent=2, ensure_ascii=False)
