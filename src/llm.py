from config.config import SEED
from config.runtime import MODELS, N_CTX

EMPTY_THINK = "<think>\n\n</think>\n\n"


class LLM:
    def __init__(self, name):
        from llama_cpp import Llama

        if name not in MODELS:
            raise ValueError(f"Невідома модель '{name}'. Доступні: {list(MODELS)}")
        spec = MODELS[name]
        self.name, self.spec = name, spec
        opts = dict(n_ctx=N_CTX, seed=SEED, verbose=False)
        if spec.get("path"):
            self._llm = Llama(model_path=spec["path"], **opts)
        else:
            self._llm = Llama.from_pretrained(repo_id=spec["repo_id"], filename=spec["filename"], **opts)
        self._grammars = {}

    def chat(self, messages, max_tokens=256, stop=None):
        out = self._llm.create_chat_completion(
            messages=messages, max_tokens=max_tokens, temperature=0.0, stop=stop
        )
        return out["choices"][0]["message"]["content"]

    def choose(self, messages, choices):
        from llama_cpp import LlamaGrammar

        prefix = EMPTY_THINK if self.spec.get("empty_think") else ""
        key = (tuple(choices), prefix)
        if key not in self._grammars:
            alternatives = " | ".join(f'"{c}"' for c in choices)
            head = f'"{prefix.replace(chr(10), chr(92) + "n")}" ' if prefix else ""
            self._grammars[key] = LlamaGrammar.from_string(f"root ::= {head}({alternatives})")
        out = self._llm.create_chat_completion(
            messages=messages, max_tokens=12 + (12 if prefix else 0), temperature=0.0, grammar=self._grammars[key]
        )
        text = out["choices"][0]["message"]["content"]
        return text.split("</think>")[-1].strip().lower()
