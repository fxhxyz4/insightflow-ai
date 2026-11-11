import re
import time
from datetime import date

from config.config import CATEGORIES
from src.tools import DESCRIPTIONS

SYSTEM_TEMPLATE = """You are a news digest assistant. Today is {today}.
You answer questions about news that were collected from RSS feeds and stored in a database.
Categories: {categories}.
Never invent news: rely only on the observations returned by the tools.
If the user's message is not about news (a greeting, small talk, a question about you), do not use tools:
answer directly with "Final Answer: ..." in the user's language.

You have access to these tools:
{tools}

Tool arguments are plain values, NOT name=value: write build_digest(economics), never build_digest(category=economics).
Use exactly this format, one step at a time:
Thought: <your reasoning about what to do next>
Action: <tool_name>(<argument>)
Observation: <will be filled in for you after the tool runs>
... (repeat Thought/Action/Observation as needed, at most {max_steps} steps)
Thought: I now know the final answer
Final Answer: <answer in the language of the user's question, based only on the observations>

Stop generating after you output an Action line -- wait for the real observation."""


def parse_action(text):
    matches = re.findall(r"Action:\s*(\w+)\((.*)\)", text)
    if not matches:
        return None, None
    name, raw = matches[-1]
    parts = [re.sub(r"^[A-Za-z_]+\s*=\s*", "", p.strip()).strip("\"'") for p in raw.split(",")]
    return name, ", ".join(parts).strip()


class Agent:
    def __init__(self, llm, tools, max_steps=6):
        self.llm, self.tools, self.max_steps = llm, tools, max_steps

    def system_prompt(self):
        return SYSTEM_TEMPLATE.format(today=date.today().isoformat(), categories=", ".join(CATEGORIES),
                                      tools=DESCRIPTIONS, max_steps=self.max_steps)

    def run(self, question, verbose=False, on_event=None):
        messages = [{"role": "system", "content": self.system_prompt()},
                    {"role": "user", "content": question}]
        trace, tool_calls, final, last_text, retries = [], [], None, "", 0

        def add(entry):
            trace.append(entry)
            if on_event:
                on_event(entry)

        t0 = time.time()
        for step in range(self.max_steps):
            text = self.llm.chat(messages, max_tokens=500, stop=["Observation:"])
            add({"role": "model", "text": text})
            if verbose:
                print(f"--- крок {step} (модель) ---\n{text}\n")
            if "Final Answer:" in text:
                final = text.split("Final Answer:", 1)[1].strip()
                break
            name, arg = parse_action(text)
            if name is None:
                add({"role": "note", "text": "no Action and no Final Answer"})
                if retries < 1:
                    retries += 1
                    messages.append({"role": "assistant", "content": text.strip() or "(empty)"})
                    messages.append({"role": "user", "content": "Observation: ERROR: invalid format. Reply with either "
                                     "'Action: tool_name(argument)' or 'Final Answer: <answer>'."})
                    continue
                last_text = text.strip()
                break
            if name not in self.tools:
                obs = f"ERROR: unknown tool '{name}'. Available: {', '.join(self.tools)}"
            else:
                try:
                    obs = str(self.tools[name](arg))
                except Exception as e:
                    obs = f"ERROR: {type(e).__name__}: {e}"
            tool_calls.append({"tool": name, "arg": arg})
            add({"role": "tool", "tool": name, "arg": arg, "result": obs})
            if verbose:
                print(f"[інструмент] {name}({arg!r}) -> {obs[:300]}\n")
            messages.append({"role": "assistant", "content": text.strip()})
            messages.append({"role": "user", "content": f"Observation: {obs}"})
        else:
            last_text = trace[-1].get("text", "") if trace else ""
        return {"answer": final if final is not None else last_text, "finished": final is not None, "steps": len(trace),
                "tool_calls": tool_calls, "seconds": round(time.time() - t0, 2), "trace": trace}


def plain_answer(llm, question):
    messages = [{"role": "system", "content": f"You are a news assistant. Today is {date.today().isoformat()}."},
                {"role": "user", "content": question}]
    return llm.chat(messages, max_tokens=300)
