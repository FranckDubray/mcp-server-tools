"""
call_llm tool - simple version
"""
from typing import Any, Dict, List, Optional
import os
import json
import requests
import logging

LOG = logging.getLogger(__name__)
if os.getenv("LLM_DEBUG") == "1":
    LOG.setLevel(logging.DEBUG)
    if not LOG.handlers:
        h = logging.StreamHandler()
        h.setLevel(logging.DEBUG)
        h.setFormatter(logging.Formatter("%(asctime)s [call_llm] %(message)s"))
        LOG.addHandler(h)


def run(
    messages: List[Dict[str, Any]],
    model: str = "gpt-5",
    max_tokens: Optional[int] = None,
    tool_names: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    
    if LOG.isEnabledFor(logging.DEBUG):
        LOG.debug(f"=== CALL_LLM START ===")
        LOG.debug(f"ALL RECEIVED PARAMS:")
        LOG.debug(f"  messages: {len(messages) if messages else 'None'}")
        LOG.debug(f"  model: {model}")
        LOG.debug(f"  max_tokens: {max_tokens}")
        LOG.debug(f"  tool_names: {tool_names}")
        LOG.debug(f"  **kwargs: {kwargs}")
        
    token = os.getenv("AI_PORTAL_TOKEN")
    if not token:
        return {"error": "AI_PORTAL_TOKEN required"}
    
    if not messages:
        return {"error": "messages required"}

    endpoint = os.getenv("LLM_ENDPOINT", "https://dev-ai.dragonflygroup.fr/api/v1/chat/completions")
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 1,  # ✅ Fixed to 1 for gpt-5 compatibility
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens

    # Check if tools are requested
    if tool_names:
        if LOG.isEnabledFor(logging.DEBUG):
            LOG.debug(f"=== MCP TOOLS MODE ===")
            LOG.debug(f"Requested tools: {tool_names}")
        
        try:
            # Get tools from MCP
            mcp_url = os.getenv("MCP_URL", "http://127.0.0.1:8000")
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"Fetching tools from MCP: {mcp_url}/tools")
            
            resp = requests.get(f"{mcp_url}/tools", timeout=10)
            resp.raise_for_status()
            all_tools = resp.json()
            
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"MCP returned {len(all_tools)} total tools")
                tool_names_available = [item.get("name") for item in all_tools if item.get("name")]
                LOG.debug(f"Available tool names: {tool_names_available}")
            
            # Filter tools and convert to OpenAI functions format
            functions = []
            name_to_reg = {}
            found_tools = []
            
            for item in all_tools:
                item_name = item.get("name")
                if item_name in tool_names:
                    spec_str = item.get("json")
                    reg_name = item.get("regName", item_name)
                    
                    if LOG.isEnabledFor(logging.DEBUG):
                        LOG.debug(f"Found requested tool: {item_name} (regName: {reg_name})")
                    
                    if spec_str:
                        try:
                            spec = json.loads(spec_str)
                            # Convert from OpenAI tools format to functions format
                            if "function" in spec:
                                func_spec = spec["function"]
                                functions.append(func_spec)  # Just the function part, not the wrapper
                                fname = func_spec.get("name")
                                if fname:
                                    name_to_reg[fname] = reg_name
                                    found_tools.append(fname)
                                if LOG.isEnabledFor(logging.DEBUG):
                                    LOG.debug(f"Tool {item_name} converted to function format")
                        except Exception as e:
                            if LOG.isEnabledFor(logging.DEBUG):
                                LOG.debug(f"Failed to parse spec for tool {item_name}: {e}")
            
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"Found {len(found_tools)} matching tools: {found_tools}")
                LOG.debug(f"Name to reg mapping: {name_to_reg}")
                missing_tools = set(tool_names) - set(found_tools)
                if missing_tools:
                    LOG.debug(f"Missing tools: {missing_tools}")
            
            if not functions:
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug("No matching functions found - falling back to simple LLM call")
                # Fallback to simple call
                tool_names = None
            else:
                payload["functions"] = functions  # Use functions, not tools
                payload["function_call"] = "auto"  # Use function_call, not tool_choice
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug(f"Added {len(functions)} functions to LLM payload")
                    LOG.debug(f"Functions in payload: {json.dumps(functions, indent=2)}")
            
        except Exception as e:
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"MCP tools fetch failed: {e} - falling back to simple call")
            return {"error": f"Failed to get MCP tools: {e}"}

    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Simple streaming mode (no tools)
        if not tool_names:
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"=== STREAMING MODE ===")
                LOG.debug(f"→ POST {endpoint}")
                LOG.debug(f"→ PAYLOAD: {json.dumps(payload, indent=2)}")
            
            payload["stream"] = True  # JSON boolean, not Python
            resp = requests.post(endpoint, headers=headers, json=payload, stream=True, verify=False)
            
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"← HTTP {resp.status_code}")
            
            resp.raise_for_status()
            
            # Recompose chunks
            content = ""
            finish_reason = None
            usage = None
            chunk_count = 0
            
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8').strip()
                if line.startswith(''):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data_str)
                        
                        # ✅ UNWRAP RESPONSE IF NEEDED
                        if "response" in chunk and "choices" not in chunk:
                            chunk = chunk["response"]
                        
                        chunk_count += 1
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                content += delta["content"]
                                if LOG.isEnabledFor(logging.DEBUG) and chunk_count <= 3:
                                    LOG.debug(f"Chunk {chunk_count}: +'{delta['content']}'")
                            if "finish_reason" in choices[0] and choices[0]["finish_reason"]:
                                finish_reason = choices[0]["finish_reason"]
                        if "usage" in chunk:
                            usage = chunk["usage"]
                    except:
                        continue
            
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"← Streaming complete: {chunk_count} chunks, content_len={len(content)}, finish_reason={finish_reason}")
            
            return {
                "success": True,
                "content": content,
                "finish_reason": finish_reason or "stop",
                "usage": usage
            }
        
        # Functions mode
        else:
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"=== FUNCTIONS MODE ===")
                LOG.debug(f"→ POST {endpoint} (JSON for function_calls)")
                LOG.debug(f"→ PAYLOAD: {json.dumps(payload, indent=2)}")
            
            resp = requests.post(endpoint, headers=headers, json=payload, verify=False)
            
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"← HTTP {resp.status_code}")
                LOG.debug(f"← Response: {resp.text[:1000]}")
            
            resp.raise_for_status()
            
            data = resp.json()
            
            # ✅ UNWRAP RESPONSE IF NEEDED
            if "response" in data and "choices" not in data:
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug("← Detected wrapped response, unwrapping...")
                data = data["response"]
            
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            function_call = message.get("function_call")  # Check function_call, not tool_calls
            
            if LOG.isEnabledFor(logging.DEBUG):
                if function_call:
                    func_name = function_call.get("name")
                    func_args = function_call.get("arguments")
                    LOG.debug(f"← LLM returned function_call: {func_name} with args {func_args}")
                else:
                    LOG.debug("← No function_call - LLM responded directly")
                    LOG.debug(f"← Direct response: '{message.get('content', '')}'")
            
            # Handle function call
            if function_call:
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug(f"=== EXECUTING FUNCTION ===")
                
                # Add assistant message to conversation
                payload["messages"].append(message)
                
                # Execute function
                fname = function_call.get("name")
                args_str = function_call.get("arguments", "{}")
                
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug(f"→ Function: {fname}")
                
                try:
                    args = json.loads(args_str)
                except Exception as e:
                    args = {}
                    if LOG.isEnabledFor(logging.DEBUG):
                        LOG.debug(f"  Failed to parse args '{args_str}': {e}")
                
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug(f"  Args: {args}")
                
                reg_name = name_to_reg.get(fname, fname)
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug(f"  Mapped to MCP tool: {reg_name}")
                
                # Call MCP
                mcp_payload = {"tool_reg": reg_name, "params": args}
                
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug(f"  → POST {mcp_url}/execute")
                    LOG.debug(f"  → MCP payload: {json.dumps(mcp_payload)}")
                
                try:
                    mcp_resp = requests.post(
                        f"{mcp_url}/execute",
                        json=mcp_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=30
                    )
                    
                    if LOG.isEnabledFor(logging.DEBUG):
                        LOG.debug(f"  ← MCP HTTP {mcp_resp.status_code}")
                        LOG.debug(f"  ← MCP Response: {mcp_resp.text}")
                    
                    if mcp_resp.status_code == 200:
                        mcp_data = mcp_resp.json()
                        result = mcp_data.get("result", {})
                        if LOG.isEnabledFor(logging.DEBUG):
                            LOG.debug(f"  ← MCP result: {result}")
                    else:
                        result = {"error": f"MCP error {mcp_resp.status_code}: {mcp_resp.text}"}
                        if LOG.isEnabledFor(logging.DEBUG):
                            LOG.debug(f"  ← MCP error: {mcp_resp.text}")
                    
                except Exception as e:
                    result = {"error": f"MCP call failed: {e}"}
                    if LOG.isEnabledFor(logging.DEBUG):
                        LOG.debug(f"  ← MCP exception: {e}")
                
                # Add function response to conversation
                function_response = {
                    "role": "function",  # Use function role, not tool
                    "name": fname,
                    "content": json.dumps(result)
                }
                payload["messages"].append(function_response)
                
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug(f"  Added function response to conversation")
                
                # Call LLM again with function results (streaming)
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug(f"=== FINAL LLM CALL (streaming) ===")
                    LOG.debug(f"→ POST {endpoint} with {len(payload['messages'])} messages")
                
                payload["stream"] = True  # JSON boolean
                resp = requests.post(endpoint, headers=headers, json=payload, stream=True, verify=False)
                
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug(f"← HTTP {resp.status_code}")
                
                resp.raise_for_status()
                
                # Recompose final response
                content = ""
                finish_reason = None
                usage = None
                chunk_count = 0
                
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line = line.decode('utf-8').strip()
                    if line.startswith(''):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data_str)
                            
                            # ✅ UNWRAP RESPONSE IF NEEDED
                            if "response" in chunk and "choices" not in chunk:
                                chunk = chunk["response"]
                            
                            chunk_count += 1
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    content += delta["content"]
                                    if LOG.isEnabledFor(logging.DEBUG) and chunk_count <= 3:
                                        LOG.debug(f"Final chunk {chunk_count}: +'{delta['content']}'")
                                if "finish_reason" in choices[0] and choices[0]["finish_reason"]:
                                    finish_reason = choices[0]["finish_reason"]
                            if "usage" in chunk:
                                usage = chunk["usage"]
                        except:
                            continue
                
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug(f"← Final streaming complete: {chunk_count} chunks, content='{content}', finish_reason={finish_reason}")
                
                return {
                    "success": True,
                    "content": content,
                    "finish_reason": finish_reason or "stop",
                    "usage": usage
                }
            
            else:
                # No function call, return direct response
                content = message.get("content", "")
                finish_reason = choice.get("finish_reason", "stop")
                usage = data.get("usage")
                
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug(f"← Direct response: '{content}'")
                
                return {
                    "success": True,
                    "content": content,
                    "finish_reason": finish_reason,
                    "usage": usage
                }
        
    except Exception as e:
        if LOG.isEnabledFor(logging.DEBUG):
            LOG.exception("LLM call failed")
        return {
            "error": str(e)
        }


def spec() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "call_llm",
            "description": "Call LLM with streaming and optional MCP tools",
            "parameters": {
                "type": "object",
                "properties": {
                    "messages": {"type": "array", "items": {"type": "object"}},
                    "model": {"type": "string", "default": "gpt-5"},
                    "max_tokens": {"type": "number"},
                    "tool_names": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["messages"]
            }
        }
    }