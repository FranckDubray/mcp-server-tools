"""
call_llm tool - with streaming, optional MCP tools, and image (OCR/vision) support.
- Supports passing local image files (paths) or remote image URLs to the LLM using OpenAI-style message format.
- Images are embedded as data URLs (base64) for local files.

Usage patterns:
1) Plain chat (no tools)
2) With MCP tools (functions)
3) Vision/OCR: provide image(s) via 'image' (str), 'images' (list[str]) and/or 'image_urls' (list[str])
   - The images are attached to the last user message as content parts [{type:"text"},{type:"image_url"}...]
   - You can also provide an optional 'ocr_instructions' string prepended to the user's text for better OCR extraction
"""
from typing import Any, Dict, List, Optional
import os
import json
import base64
import mimetypes
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


def _guess_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        # default fallback
        return "image/png"
    return mime


def _file_to_data_url(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("ascii")
    mime = _guess_mime(path)
    return f"data:{mime};base64,{b64}"


def _ensure_user_message(messages: List[Dict[str, Any]]) -> None:
    if not messages:
        raise ValueError("messages required")
    # Ensure last message is a user message so we can attach images
    if messages[-1].get("role") != "user":
        # If not, append a dummy user message to host the images
        messages.append({"role": "user", "content": ""})


def _attach_images_to_last_user_message(messages: List[Dict[str, Any]], image_parts: List[Dict[str, Any]], ocr_instructions: Optional[str] = None) -> None:
    if not image_parts:
        return
    _ensure_user_message(messages)
    last = messages[-1]
    content = last.get("content", "")
    # Normalize to array format
    new_parts: List[Dict[str, Any]] = []
    # Prepend OCR instructions if provided
    if ocr_instructions:
        new_parts.append({"type": "text", "text": ocr_instructions})
    if isinstance(content, str):
        if content:
            new_parts.append({"type": "text", "text": content})
    elif isinstance(content, list):
        # Keep existing parts
        for part in content:
            new_parts.append(part)
    else:
        # unexpected content type -> coerce
        new_parts.append({"type": "text", "text": str(content)})
    # Append images
    new_parts.extend(image_parts)
    last["content"] = new_parts


def run(
    messages: List[Dict[str, Any]],
    model: str = "gpt-5",
    max_tokens: Optional[int] = None,
    tool_names: Optional[List[str]] = None,
    # Vision/OCR additions
    image: Optional[str] = None,
    images: Optional[List[str]] = None,
    image_urls: Optional[List[str]] = None,
    ocr_instructions: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    
    if LOG.isEnabledFor(logging.DEBUG):
        LOG.debug(f"=== CALL_LLM START ===")
        LOG.debug(f"ALL RECEIVED PARAMS:")
        LOG.debug(f"  messages: {len(messages) if messages else 'None'}")
        LOG.debug(f"  model: {model}")
        LOG.debug(f"  max_tokens: {max_tokens}")
        LOG.debug(f"  tool_names: {tool_names}")
        LOG.debug(f"  image: {image}")
        LOG.debug(f"  images: {images}")
        LOG.debug(f"  image_urls: {image_urls}")
        LOG.debug(f"  ocr_instructions: {bool(ocr_instructions)}")
        LOG.debug(f"  **kwargs: {kwargs}")
        
    token = os.getenv("AI_PORTAL_TOKEN")
    if not token:
        return {"error": "AI_PORTAL_TOKEN required"}
    
    if not messages:
        return {"error": "messages required"}

    # Build image parts (OpenAI-style vision: content parts)
    image_parts: List[Dict[str, Any]] = []
    local_files: List[str] = []
    if image:
        local_files.append(image)
    if images:
        local_files.extend([p for p in images if isinstance(p, str)])

    # Convert local files to data URLs
    for p in local_files:
        try:
            data_url = _file_to_data_url(p)
            image_parts.append({
                "type": "image_url",
                "image_url": {"url": data_url}
            })
        except Exception as e:
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"Failed to encode image '{p}': {e}")
            # add a note to messages to avoid silent failure
            image_parts.append({"type": "text", "text": f"[Attachment failed: {p} - {e}]"})

    # Remote URLs (no base64, directly passed)
    if image_urls:
        for url in image_urls:
            if isinstance(url, str) and url.strip():
                image_parts.append({
                    "type": "image_url",
                    "image_url": {"url": url.strip()}
                })

    # Attach images to last user message if any provided
    if image_parts:
        try:
            _attach_images_to_last_user_message(messages, image_parts, ocr_instructions=ocr_instructions)
        except Exception as e:
            return {"error": f"Failed to attach images to message: {e}"}

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
                                functions.append(func_spec)
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
                tool_names = None
            else:
                payload["functions"] = functions
                payload["function_call"] = "auto"
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
                LOG.debug(f"→ PAYLOAD: {json.dumps(payload)[:1000]}…")
            
            payload["stream"] = True
            resp = requests.post(endpoint, headers=headers, json=payload, stream=True, verify=False)
            
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"← HTTP {resp.status_code}")
            
            resp.raise_for_status()
            
            content = ""
            finish_reason = None
            usage = None
            chunk_count = 0
            
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8').strip()
                if line.startswith('data:'):
                    data_str = line[5:].strip()
                    if data_str == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data_str)
                        if "response" in chunk and "choices" not in chunk:
                            chunk = chunk["response"]
                        chunk_count += 1
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                content += delta["content"]
                            if "finish_reason" in choices[0] and choices[0]["finish_reason"]:
                                finish_reason = choices[0]["finish_reason"]
                        if "usage" in chunk:
                            usage = chunk["usage"]
                    except Exception:
                        continue
            
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
                LOG.debug(f"→ PAYLOAD: {json.dumps(payload)[:1000]}…")
            
            resp = requests.post(endpoint, headers=headers, json=payload, verify=False)
            
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug(f"← HTTP {resp.status_code}")
                LOG.debug(f"← Response: {resp.text[:1000]}")
            
            resp.raise_for_status()
            
            data = resp.json()
            if "response" in data and "choices" not in data:
                data = data["response"]
            
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            function_call = message.get("function_call")
            
            if function_call:
                # Continue as before (execute MCP tool and stream final answer)
                mcp_url = os.getenv("MCP_URL", "http://127.0.0.1:8000")
                payload["messages"].append(message)
                fname = function_call.get("name")
                args_str = function_call.get("arguments", "{}")
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = {}
                reg_name = name_to_reg.get(fname, fname)  # type: ignore[name-defined]
                mcp_payload = {"tool_reg": reg_name, "params": args}
                try:
                    mcp_resp = requests.post(
                        f"{mcp_url}/execute",
                        json=mcp_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=30
                    )
                    if mcp_resp.status_code == 200:
                        mcp_data = mcp_resp.json()
                        result = mcp_data.get("result", {})
                    else:
                        result = {"error": f"MCP error {mcp_resp.status_code}: {mcp_resp.text}"}
                except Exception as e:
                    result = {"error": f"MCP call failed: {e}"}
                function_response = {
                    "role": "function",
                    "name": fname,
                    "content": json.dumps(result)
                }
                payload["messages"].append(function_response)
                payload["stream"] = True
                resp = requests.post(endpoint, headers=headers, json=payload, stream=True, verify=False)
                resp.raise_for_status()
                content = ""
                finish_reason = None
                usage = None
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line = line.decode('utf-8').strip()
                    if line.startswith('data:'):
                        data_str = line[5:].strip()
                        if data_str == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data_str)
                            if "response" in chunk and "choices" not in chunk:
                                chunk = chunk["response"]
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    content += delta["content"]
                                if "finish_reason" in choices[0] and choices[0]["finish_reason"]:
                                    finish_reason = choices[0]["finish_reason"]
                            if "usage" in chunk:
                                usage = chunk["usage"]
                        except Exception:
                            continue
                return {"success": True, "content": content, "finish_reason": finish_reason or "stop", "usage": usage}
            else:
                content = message.get("content", "")
                finish_reason = choice.get("finish_reason", "stop")
                usage = data.get("usage")
                return {"success": True, "content": content, "finish_reason": finish_reason, "usage": usage}
        
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
            "description": "Call LLM with streaming, optional MCP tools, and image (OCR/vision) support. Attach local images (base64 data URLs) or remote image URLs to the last user message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "messages": {"type": "array", "items": {"type": "object"}},
                    "model": {"type": "string", "default": "gpt-5"},
                    "max_tokens": {"type": "number"},
                    "tool_names": {"type": "array", "items": {"type": "string"}},
                    "image": {"type": "string", "description": "Chemin vers une image locale à attacher (OCR/vision)"},
                    "images": {"type": "array", "items": {"type": "string"}, "description": "Liste de chemins d'images locales"},
                    "image_urls": {"type": "array", "items": {"type": "string"}, "description": "Liste d'URLs d'images distantes"},
                    "ocr_instructions": {"type": "string", "description": "Instructions à insérer avant les images (ex: 'Transcris tout le texte et les tableaux, conserve la structure.')."}
                },
                "required": ["messages"]
            }
        }
    }
