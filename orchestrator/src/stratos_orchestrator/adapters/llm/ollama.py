from typing import Any
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from stratos_orchestrator.domain.ports import LLMProvider


class OllamaProvider(LLMProvider):
    """Adapter for Ollama running locally."""

    def __init__(self, model: str = "kimi-k2.5:cloud", base_url: str = "http://host.docker.internal:11434"):
        self.model = model
        self.base_url = base_url
        self._client = ChatOllama(model=model, base_url=base_url, temperature=0.1)

    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        Generate text response.
        """
        return await self.achat(messages)

    async def generate_structured(
        self, messages: list[dict[str, str]], schema: dict, **kwargs: Any
    ) -> dict:
        """
        Generate structured response using JSON mode or output parsers.
        """
        lc_messages = self._convert_messages(messages)
        
        # Method 1: Use strictly JSON mode
        structured_llm = self._client.bind(format="json")
        
        # Log payload for debugging
        print(f"DEBUG: sending to LLM: {lc_messages}")
        
        try:
            response = await structured_llm.ainvoke(lc_messages)
            content = response.content
            print(f"DEBUG: raw LLM content: {content!r}")
            
            # Clean up potential markdown formatting
            cleaned_content = str(content).strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()
            
            # Parse JSON
            import json
            try:
                result = json.loads(cleaned_content)
                if result is None:
                    print("DEBUG: LLM returned 'null', returning empty dict")
                    return {}
                if not isinstance(result, dict):
                    print(f"DEBUG: LLM returned non-dict type {type(result)}, returning empty dict")
                    return {}
                return result
            except json.JSONDecodeError:
                print(f"Failed to parse JSON: {content}")
                
                # Fallback: Attempt to parse MARKDOWN output via Regex
                # Kimi/Ollama often ignores JSON mode for long creative tasks like Memos
                import re
                fallback_data = {}
                
                # Known section headers in the memo for boundary detection
                headers = [
                    "Recommendation", 
                    "Confidence Score", 
                    "Confidence",
                    "Scenario Tree", 
                    "Scenarios",
                    "Worst Case", 
                    "Risk Band",
                    "Risk"
                ]
                
                # Pre-process content to handle potential line-ending issues
                content_str = str(content).strip()
                
                def extract_section(key: str, text: str) -> str | None:
                    # Look for the current key (with bolding or header hashes)
                    # and capture until the next known header or end of string.
                    other_headers = "|".join([re.escape(h) for h in headers if h != key])
                    
                    # More robust regex for multi-style headers:
                    pattern = rf"(?:^|\n)[^a-zA-Z0-9]*{re.escape(key)}[^a-zA-Z0-9]*\n*(.*?)(?=\n\s*[^a-zA-Z0-9]*(?:{other_headers})|$)"
                    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                    if match:
                        return match.group(1).strip()
                    return None

                def normalize_markdown(text: str) -> str:
                    """Ensures internal newlines are preserved but normalized."""
                    if not text: return ""
                    lines = [line.strip() for line in text.split('\n')]
                    return "\n".join(lines)

                def parse_markdown_table(table_text: str) -> list[dict]:
                    """Simple parser for markdown tables."""
                    if not table_text: return []
                    lines = [l.strip() for l in table_text.strip().split('\n') if '|' in l]
                    if len(lines) < 2: return [] # Need at least header and one row
                    
                    header_line = lines[0]
                    headers_found = [h.strip().lower().replace(" ", "_").replace("**", "") for h in header_line.split('|') if h.strip()]
                    
                    rows = []
                    start_idx = 1
                    if len(lines) > 1 and all(c in '|- ' for c in lines[1]):
                        start_idx = 2
                        
                    for line in lines[start_idx:]:
                        values = [v.strip() for v in line.split('|') if v.strip()]
                        if len(values) >= len(headers_found):
                            row = dict(zip(headers_found, values[:len(headers_found)]))
                            rows.append(row)
                    return rows

                # Extract Recommendation
                rec = extract_section("Recommendation", content_str)
                if rec:
                    fallback_data["recommendation"] = normalize_markdown(rec)
                
                # Extract Confidence Score
                conf_str = extract_section("Confidence Score", content_str) or extract_section("Confidence", content_str)
                if conf_str:
                    # Support formats like "85%", "0.85", "**0.85**", or even "0.85 / 1.0"
                    pct_match = re.search(r'([\d\.]+)\s*%', conf_str)
                    if pct_match:
                        try:
                            fallback_data["confidence_score"] = float(pct_match.group(1)) / 100.0
                        except ValueError:
                            pass
                    else:
                        conf_match = re.search(r'([\d\.]+)', conf_str)
                        if conf_match:
                            try:
                                val = float(conf_match.group(1))
                                if val > 1.0: val = val / 100.0
                                fallback_data["confidence_score"] = val
                            except ValueError:
                                fallback_data["confidence_score"] = 0.5
                
                # Extract Risk Band
                risk = extract_section("Risk Band", content_str) or extract_section("Risk", content_str)
                if risk:
                    risk_val = risk.split('\n')[0].replace("**", "").strip()
                    fallback_data["risk_band"] = risk_val

                # Extract Worst Case
                worst = extract_section("Worst Case", content_str)
                if worst:
                    fallback_data["worst_case"] = normalize_markdown(worst)
                
                # Extract and Parse Scenario Tree
                tree_text = extract_section("Scenario Tree", content_str) or extract_section("Scenarios", content_str)
                if tree_text:
                    parsed_tree = parse_markdown_table(tree_text)
                    if parsed_tree:
                        fallback_data["scenario_tree"] = parsed_tree
                
                # Final mapping and cleanup
                # StrategicMemo domain entity and UI expect these specific keys
                final_result = {
                    "recommendation": fallback_data.get("recommendation", "No recommendation generated."),
                    "confidence_score": fallback_data.get("confidence_score", 0.5),
                    "worst_case": fallback_data.get("worst_case", "Unknown"),
                    "risk_band": fallback_data.get("risk_band", "Medium"),
                    "scenario_tree": fallback_data.get("scenario_tree", [])
                }
                
                if fallback_data:
                    print(f"DEBUG: Successfully recovered structured data from Markdown: {list(final_result.keys())}")
                    return final_result
                    
                return {}
        except Exception as e:
            print(f"DEBUG: generate_structured failed: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def chat(self, messages: list[dict[str, str]]) -> str:
        """
        Synchronous chat.
        Converts generic dict messages to LangChain message types.
        """
        lc_messages = self._convert_messages(messages)
        response = self._client.invoke(lc_messages)
        return str(response.content)

    async def astream(self, messages: list[dict[str, str]], **kwargs: Any):
        """
        Stream response token-by-token.
        """
        lc_messages = self._convert_messages(messages)
        async for chunk in self._client.astream(lc_messages):
            yield str(chunk.content)

    def _convert_messages(self, messages: list[dict[str, str]]) -> list[BaseMessage]:
        lc_messages: list[BaseMessage] = []
        for m in messages:
            if m["role"] == "system":
                lc_messages.append(SystemMessage(content=m["content"]))
            elif m["role"] == "user":
                lc_messages.append(HumanMessage(content=m["content"]))
        return lc_messages
