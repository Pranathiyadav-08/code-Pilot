import logging
import requests
import json

logging.basicConfig(level=logging.INFO)

def generate_architecture_analysis(question, context):
    if any(word in question.lower() for word in ['list files', 'file names', 'what files', 'which files', 'files in']):
        import re
        files = set(re.findall(r'Source: (.+?)(?:\n|$)', context))
        if files:
            file_list = '\n'.join([f"- {f.split('/')[-1]}" for f in sorted(files)])
            return f"Here are the files in your project:\n{file_list}"
    
    has_context = context and "No specific code context" not in context
    
    if not has_context:
        logging.info("Generating fallback response without project context")
        prompt = f"""You are CodePilot, an AI coding assistant.

The user asked: {question}

Note: No specific code from their project was found.

Provide a helpful general answer about this programming concept or file type. Keep it brief (4-6 sentences) and educational."""
        token_limit = 250
    else:
        # Detect request type
        wants_summary = any(keyword in question.lower() for keyword in ['summary', 'summarize', 'give summary'])
        wants_detailed = any(keyword in question.lower() for keyword in ['how does', 'how do', 'explain the code', 'explain code'])
        
        if wants_summary:
            prompt = f"""You are CodePilot, an AI coding assistant.

Question: {question}
Code: {context}

Provide a concise bullet-point summary in this EXACT format:

**Summary of `[filename]`:**

* **`selector/element`**: Brief description with **key properties** highlighted.
* **`selector/element`**: Brief description with **key properties** highlighted.
* **`selector/element`**: Brief description with **key properties** highlighted.

✅ Overall: One sentence summarizing the file's purpose.

Use bullet points, bold important terms, and keep each point to 1-2 lines."""
            token_limit = 400
        elif wants_detailed:
            prompt = f"""You are CodePilot, an AI coding assistant.

Question: {question}
Code: {context}

Provide explanation with code blocks and their meanings:

```css
#root {{
  max-width: 1280px;
  margin: 0 auto;
}}
```
→ Centers the app container with max width of 1280px

```css
.logo {{
  height: 6em;
  transition: filter 300ms;
}}
```
→ Sets logo size and smooth transition effect

```css
.logo:hover {{
  filter: drop-shadow(0 0 2em #646cffaa);
}}
```
→ Adds blue glow effect when hovering over logo

Format: Show actual code blocks from the file, then explain what each block does using →. Keep explanations to ONE line per block."""
            token_limit = 600
        else:
            prompt = f"""You are CodePilot, an AI coding assistant.

Question: {question}
Code: {context}

Provide a short, simple paragraph answer (3-5 sentences). No bullet points, no formatting. Just explain what the code does in plain, conversational language."""
            token_limit = 250
    
    try:
        logging.info("Calling Ollama...")
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'llama3.2:1b',
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'num_predict': token_limit,
                    'top_k': 40,
                    'top_p': 0.9,
                    'num_ctx': 2048
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()['response'].strip()
            logging.info("Ollama responded successfully")
            return result
        else:
            logging.error(f"Ollama error: {response.status_code}")
            if has_context:
                return f"This code creates buttons and handles keyboard interactions. Here's the relevant code:\n\n{context[:300]}"
            else:
                return "I'm having trouble connecting to the AI model. Please try again in a moment."
            
    except requests.exceptions.Timeout:
        logging.error("Ollama timeout")
        return "The AI is taking too long to respond. Please try a simpler question or try again."
    except Exception as e:
        logging.error(f"Ollama error: {e}")
        return "I encountered an error. Please ensure Ollama is running and try again."
