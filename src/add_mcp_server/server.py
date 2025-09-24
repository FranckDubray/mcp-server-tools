#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import logging
import importlib
import pkgutil
import time
from hashlib import sha1
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Development mode: add src to path
if os.path.isdir('src') and 'src' not in sys.path:
    sys.path.insert(0, 'src')

# Logging setup
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
MCP_HOST = os.getenv('MCP_HOST', '127.0.0.1')
MCP_PORT = int(os.getenv('MCP_PORT', '8000'))
EXECUTE_TIMEOUT_SEC = int(os.getenv('EXECUTE_TIMEOUT_SEC', '30'))
RELOAD_ENV = os.getenv('RELOAD', '').strip() == '1'
AUTO_RELOAD_TOOLS = os.getenv('AUTO_RELOAD_TOOLS', '1').strip() == '1'  # New: auto-reload by default

# Global registry and cache
registry: Dict[str, Dict[str, Any]] = {}
_tool_id_counter = 10000  # Start tool IDs at 10000
_last_scan_time = 0
_tools_dir_mtime = 0
_tools_file_set: Set[str] = set()  # Track tool files for change detection

app = FastAPI(
    title="MCP Server",
    description="Minimal MCP Server Implementation",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True
)


from fastapi.exceptions import RequestValidationError
from fastapi import status

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"❌ Validation error: {exc.errors()}")
    body = await request.body()
    logger.error(f"❌ Request body: {body}")
    return Response(
        content=json.dumps({
            "detail": "Validation error",
            "errors": exc.errors(),
            "body": body.decode() if body else "empty"
        }),
        status_code=422,
        media_type="application/json"
    )


class ExecuteRequest(BaseModel):
    tool_reg: Optional[str] = None
    tool: Optional[str] = None  # Accept both formats from interface
    params: Dict[str, Any]
    
    def get_tool_name(self) -> str:
        """Get tool name from either field"""
        return self.tool_reg or self.tool or ""


def get_tools_directory_info() -> Dict[str, Any]:
    """Get comprehensive information about tools directory for change detection."""
    try:
        import add_mcp_server.tools as tools_package
        tools_path = Path(tools_package.__path__[0])
        
        if not tools_path.exists():
            return {"mtime": 0, "file_set": set(), "file_count": 0}
        
        # Get all .py files in tools directory
        tool_files = set()
        max_mtime = tools_path.stat().st_mtime
        
        for py_file in tools_path.glob("*.py"):
            if py_file.name != "__init__.py":  # Skip __init__.py
                tool_files.add(py_file.name)
                max_mtime = max(max_mtime, py_file.stat().st_mtime)
        
        return {
            "mtime": max_mtime,
            "file_set": tool_files,
            "file_count": len(tool_files),
            "directory_exists": True
        }
    except Exception as e:
        logger.warning(f"Could not get tools directory info: {e}")
        return {"mtime": 0, "file_set": set(), "file_count": 0, "directory_exists": False}


def discover_tools():
    """Discover and register all tools dynamically using pkgutil."""
    global registry, _last_scan_time, _tools_dir_mtime, _tool_id_counter, _tools_file_set
    
    _last_scan_time = time.time()
    
    # Get current tools directory info
    tools_info = get_tools_directory_info()
    _tools_dir_mtime = tools_info["mtime"]
    current_file_set = tools_info["file_set"]
    
    # Detect changes
    added_files = current_file_set - _tools_file_set
    removed_files = _tools_file_set - current_file_set
    _tools_file_set = current_file_set
    
    if added_files:
        logger.info(f"🆕 New tool files detected: {added_files}")
    if removed_files:
        logger.info(f"🗑️ Removed tool files detected: {removed_files}")
    
    old_count = len(registry)
    registry.clear()
    _tool_id_counter = 10000  # Reset counter when clearing registry
    
    try:
        # Import the tools package
        import add_mcp_server.tools as tools_package
        
        # Get the tools directory path
        tools_path = tools_package.__path__
        
        # Discover all modules in the tools directory
        modules = []
        for finder, name, ispkg in pkgutil.iter_modules(tools_path):
            # Skip packages and __init__.py, only load .py files
            if not ispkg and name != '__init__':
                try:
                    module_name = f'add_mcp_server.tools.{name}'
                    logger.info(f"🔍 Discovering tool module: {name}")
                    
                    # Reload if already imported (for hot reload)
                    if module_name in sys.modules:
                        logger.info(f"♻️ Reloading existing module: {name}")
                        importlib.reload(sys.modules[module_name])
                        module = sys.modules[module_name]
                    else:
                        logger.info(f"📥 Importing new module: {name}")
                        module = importlib.import_module(module_name)
                    
                    modules.append((name, module))
                    
                except Exception as e:
                    logger.error(f"❌ Failed to import tool module {name}: {e}")
        
        logger.info(f"🔍 Found {len(modules)} potential tool modules")
        
        # Register each valid tool
        for module_name, module in modules:
            if hasattr(module, 'run') and hasattr(module, 'spec'):
                try:
                    spec = module.spec()
                    tool_name = spec['function']['name']
                    
                    # Generate numeric ID starting from 10000
                    tool_id = _tool_id_counter
                    _tool_id_counter += 1
                    
                    registry[tool_name] = {
                        "id": tool_id,  # ✅ NUMERIC ID
                        "name": tool_name,
                        "regName": tool_name,
                        "displayName": spec['function']['name'],
                        "description": spec['function']['description'],
                        "json": json.dumps(spec, separators=(",", ":"), ensure_ascii=False),
                        "func": module.run
                    }
                    logger.info(f"✅ Registered tool: {tool_name} (ID: {tool_id}) (from {module_name}.py)")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to register tool from {module_name}: {e}")
            else:
                logger.warning(f"⚠️ Module {module_name} missing run() or spec() functions")
    
    except ImportError as e:
        logger.error(f"❌ Failed to import tools package: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error during tool discovery: {e}")
    
    new_count = len(registry)
    if new_count != old_count:
        logger.info(f"🔄 Tool count changed: {old_count} → {new_count}")
        if new_count > old_count:
            logger.info(f"🎉 {new_count - old_count} new tool(s) discovered!")
        elif new_count < old_count:
            logger.info(f"🧹 {old_count - new_count} tool(s) removed")
    
    logger.info(f"🔧 Tool discovery complete. Registered {new_count} tools: {list(registry.keys())}")


def should_reload(request: Request) -> bool:
    """Enhanced: Check if we should reload tools based on file changes, explicit request, or auto-reload."""
    global _last_scan_time, _tools_dir_mtime, _tools_file_set
    
    # Force reload if explicitly requested
    if RELOAD_ENV or request.query_params.get('reload') == '1':
        logger.info("🔄 Force reload requested")
        return True
    
    # Force reload if no tools registered
    if len(registry) == 0:
        logger.info("🔄 No tools registered, reloading")
        return True
    
    # Auto-reload if enabled (default)
    if AUTO_RELOAD_TOOLS:
        tools_info = get_tools_directory_info()
        current_mtime = tools_info["mtime"]
        current_file_set = tools_info["file_set"]
        
        # Check for file modifications
        if current_mtime > _tools_dir_mtime:
            logger.info(f"🔄 Tools directory modified (mtime: {_tools_dir_mtime} → {current_mtime})")
            return True
        
        # Check for new or removed files
        if current_file_set != _tools_file_set:
            added = current_file_set - _tools_file_set
            removed = _tools_file_set - current_file_set
            if added:
                logger.info(f"🔄 New tools detected: {added}")
                return True
            if removed:
                logger.info(f"🔄 Tools removed: {removed}")
                return True
    
    return False


@app.options("/tools")
async def tools_options():
    return Response(status_code=204)

@app.get("/tools")
async def get_tools(request: Request):
    """Return list of available tools with ETag support and auto-reload."""
    if should_reload(request):
        logger.info("🔄 Auto-reloading tools...")
        discover_tools()
    
    # Build response items (exclude 'func' from response)
    items = []
    for tool in registry.values():
        item = {k: v for k, v in tool.items() if k != 'func'}
        items.append(item)
    
    # Sort for deterministic order
    items.sort(key=lambda x: x.get("name", ""))
    
    # Generate payload and ETag
    payload = json.dumps(items, separators=(",", ":"), ensure_ascii=False)
    etag = sha1(payload.encode("utf-8")).hexdigest()
    
    # Check If-None-Match for 304
    if request.headers.get("If-None-Match") == etag:
        return Response(status_code=304)
    
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Cache-Control": "no-cache",
            "ETag": etag
        }
    )

@app.options("/execute")
async def execute_options():
    return Response(status_code=204)


@app.post("/debug")
async def debug_execute(request: Request):
    """Debug endpoint to see what's received"""
    try:
        body = await request.body()
        logger.info(f"🐛 Debug - Raw body: {body}")
        
        json_data = json.loads(body)
        logger.info(f"🐛 Debug - Parsed JSON: {json_data}")
        
        # Try to create ExecuteRequest
        exec_req = ExecuteRequest(**json_data)
        logger.info(f"🐛 Debug - ExecuteRequest created: {exec_req}")
        
        return {"status": "ok", "received": json_data}
        
    except Exception as e:
        logger.error(f"🐛 Debug error: {e}")
        return {"error": str(e)}


@app.post("/execute")
async def execute_tool(request: ExecuteRequest):
    """Execute a tool with given parameters."""
    # Auto-reload check before execution
    if AUTO_RELOAD_TOOLS and should_reload(Request(scope={"type": "http", "method": "POST", "query_string": b""})):
        logger.info("🔄 Auto-reloading tools before execution...")
        discover_tools()
    
    if len(registry) == 0:
        discover_tools()
    
    tool_name = request.get_tool_name()  # Use the method that handles both formats
    params = request.params
    
    logger.info(f"🔧 Executing tool: {tool_name} with params: {params}")
    
    if tool_name not in registry:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    tool = registry[tool_name]
    func = tool['func']
    
    try:
        # Execute with timeout
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: func(**params)),
            timeout=EXECUTE_TIMEOUT_SEC
        )
        
        return {"result": result}
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Tool execution timed out")
    except TypeError as e:
        if "unexpected keyword argument" in str(e) or "missing" in str(e):
            raise HTTPException(status_code=400, detail=f"Invalid parameters: {e}")
        raise HTTPException(status_code=500, detail=f"Execution error: {e}")
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Execution error: {e}")

@app.get("/control", response_class=HTMLResponse)
async def control_dashboard():
    """Serve the control dashboard HTML with dropdown support."""
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Server Control</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .tool-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }
        .tool-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .tool-title { font-size: 1.2em; font-weight: bold; margin-bottom: 10px; color: #333; }
        .tool-description { color: #666; margin-bottom: 15px; font-size: 0.9em; }
        .param-group { margin-bottom: 15px; }
        .param-label { display: block; margin-bottom: 5px; font-weight: bold; color: #555; font-size: 0.9em; }
        .param-input, .param-select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; font-size: 0.9em; }
        .param-select { background: white; cursor: pointer; }
        .param-select:focus, .param-input:focus { border-color: #007bff; outline: none; box-shadow: 0 0 0 2px rgba(0,123,255,0.25); }
        .param-help { font-size: 0.8em; color: #888; margin-top: 2px; line-height: 1.3; }
        .execute-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 1em; margin-top: 10px; }
        .execute-btn:hover { background: #0056b3; }
        .result-area { margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 4px; min-height: 20px; border: 1px solid #e9ecef; font-family: monospace; font-size: 0.85em; white-space: pre-wrap; max-height: 300px; overflow-y: auto; }
        .error { background: #f8d7da; border-color: #f5c6cb; color: #721c24; }
        .success { background: #d4edda; border-color: #c3e6cb; color: #155724; }
        .status { margin-bottom: 20px; padding: 10px; border-radius: 4px; }
        .loading { opacity: 0.6; pointer-events: none; }
        .enum-options { font-size: 0.75em; color: #007bff; margin-top: 2px; font-style: italic; }
        .required-mark { color: #dc3545; font-weight: bold; }
        .reload-notice { background: #d1ecf1; border-color: #bee5eb; color: #0c5460; margin-bottom: 10px; padding: 8px 12px; border-radius: 4px; font-size: 0.85em; }
        .auto-reload-status { background: #d4edda; border-color: #c3e6cb; color: #155724; margin-bottom: 10px; padding: 8px 12px; border-radius: 4px; font-size: 0.85em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 MCP Server Control Panel</h1>
            <div id="status" class="status">Loading tools...</div>
            <div class="auto-reload-status">🔄 Auto-reload enabled - New tools detected automatically!</div>
            <button onclick="reloadTools()" class="execute-btn">🔄 Force Reload Tools</button>
            <div class="reload-notice">💡 Form values are preserved when reloading tools</div>
        </div>
        <div id="toolGrid" class="tool-grid">
            <!-- Tools will be loaded here -->
        </div>
    </div>
    <script src="/control.js"></script>
</body>
</html>'''
    return HTMLResponse(content=html)

@app.get("/control.js")
async def control_js(request: Request):
    """Serve the control panel JavaScript with form preservation and auto-reload."""
    js = '''
let tools = [];

// Save form values before reload
function saveFormValues() {
    const formData = {};
    const inputs = document.querySelectorAll('.param-input, .param-select');
    inputs.forEach(input => {
        if (input.value) {
            formData[input.id] = input.value;
        }
    });
    return formData;
}

// Restore form values after reload
function restoreFormValues(formData) {
    Object.keys(formData).forEach(inputId => {
        const input = document.getElementById(inputId);
        if (input) {
            input.value = formData[inputId];
        }
    });
}

async function loadTools(preserveValues = false) {
    let formData = {};
    if (preserveValues) {
        formData = saveFormValues();
    }
    
    try {
        const response = await fetch('/tools');
        if (response.ok) {
            tools = await response.json();
            renderTools();
            
            if (preserveValues && Object.keys(formData).length > 0) {
                // Restore form values after a small delay to ensure DOM is rendered
                setTimeout(() => restoreFormValues(formData), 100);
                updateStatus(`✅ Reloaded ${tools.length} tools (form values preserved): ${tools.map(t => t.name).join(', ')}`, 'success');
            } else {
                updateStatus(`Loaded ${tools.length} tools: ${tools.map(t => t.name).join(', ')}`, 'success');
            }
        } else {
            updateStatus(`Failed to load tools: ${response.statusText}`, 'error');
        }
    } catch (error) {
        updateStatus(`Error loading tools: ${error.message}`, 'error');
    }
}

async function reloadTools() {
    updateStatus('🔄 Force reloading tools (preserving form values)...', '');
    try {
        const response = await fetch('/tools?reload=1');
        if (response.ok) {
            // Save current form values
            const formData = saveFormValues();
            
            tools = await response.json();
            renderTools();
            
            // Restore form values
            if (Object.keys(formData).length > 0) {
                setTimeout(() => restoreFormValues(formData), 100);
                updateStatus(`✅ Force reloaded ${tools.length} tools (✅ form values preserved): ${tools.map(t => t.name).join(', ')}`, 'success');
            } else {
                updateStatus(`✅ Force reloaded ${tools.length} tools: ${tools.map(t => t.name).join(', ')}`, 'success');
            }
        } else {
            updateStatus(`❌ Failed to reload tools: ${response.statusText}`, 'error');
        }
    } catch (error) {
        updateStatus(`❌ Error reloading tools: ${error.message}`, 'error');
    }
}

function updateStatus(message, type) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = 'status ' + type;
}

function renderTools() {
    const grid = document.getElementById('toolGrid');
    grid.innerHTML = '';
    
    tools.forEach(tool => {
        const card = createToolCard(tool);
        grid.appendChild(card);
    });
}

function createToolCard(tool) {
    const card = document.createElement('div');
    card.className = 'tool-card';
    
    let spec;
    try {
        spec = JSON.parse(tool.json);
    } catch (e) {
        card.innerHTML = '<div class="tool-title">❌ Error</div><div class="error">Invalid tool spec</div>';
        return card;
    }
    
    const params = spec.function.parameters.properties || {};
    const required = spec.function.parameters.required || [];
    
    let html = `
        <div class="tool-title">🔧 ${tool.displayName} (ID: ${tool.id})</div>
        <div class="tool-description">${tool.description}</div>
    `;
    
    // Create input fields for parameters
    Object.keys(params).forEach(paramName => {
        const param = params[paramName];
        const isRequired = required.includes(paramName);
        
        html += `
            <div class="param-group">
                <label class="param-label">
                    ${paramName}${isRequired ? '<span class="required-mark"> *</span>' : ''}
                </label>
        `;
        
        // Create dropdown for enum fields, regular input for others
        if (param.enum && param.enum.length > 0) {
            html += `
                <select id="${tool.name}_${paramName}" class="param-select" ${isRequired ? 'required' : ''}>
                    <option value="">-- Select ${paramName} --</option>
            `;
            param.enum.forEach(option => {
                html += `<option value="${option}">${option}</option>`;
            });
            html += `</select>`;
            html += `<div class="enum-options">Available: ${param.enum.join(', ')}</div>`;
        } else {
            // Regular input field
            const placeholder = param.type === 'number' ? 'Enter number' : 
                              param.enum ? param.enum[0] : 'Enter value';
            html += `
                <input type="text" 
                       id="${tool.name}_${paramName}" 
                       class="param-input"
                       placeholder="${placeholder}"
                       ${isRequired ? 'required' : ''}>
            `;
        }
        
        if (param.description) {
            html += `<div class="param-help">${param.description}</div>`;
        }
        
        html += `</div>`;
    });
    
    html += `
        <button class="execute-btn" onclick="executeTool('${tool.name}')">
            ▶️ Execute ${tool.displayName}
        </button>
        <div id="${tool.name}_result" class="result-area">Ready to execute...</div>
    `;
    
    card.innerHTML = html;
    return card;
}

async function executeTool(toolName) {
    const tool = tools.find(t => t.name === toolName);
    if (!tool) return;
    
    const resultDiv = document.getElementById(toolName + '_result');
    const card = resultDiv.closest('.tool-card');
    
    try {
        card.classList.add('loading');
        resultDiv.textContent = '⏳ Executing...';
        resultDiv.className = 'result-area';
        
        // Collect parameters
        const spec = JSON.parse(tool.json);
        const params = {};
        const paramDefs = spec.function.parameters.properties || {};
        
        for (const paramName of Object.keys(paramDefs)) {
            const input = document.getElementById(`${toolName}_${paramName}`);
            if (input && input.value.trim()) {
                let value = input.value.trim();
                
                // Convert to appropriate type
                if (paramDefs[paramName].type === 'number') {
                    const num = parseFloat(value);
                    if (isNaN(num)) {
                        throw new Error(`Parameter "${paramName}" must be a valid number`);
                    }
                    params[paramName] = num;
                } else {
                    params[paramName] = value;
                }
            }
        }
        
        // Check required parameters
        const required = spec.function.parameters.required || [];
        for (const reqParam of required) {
            if (!(reqParam in params)) {
                throw new Error(`Required parameter "${reqParam}" is missing`);
            }
        }
        
        // Execute with tool_reg (CORRECTED!)
        const response = await fetch('/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tool_reg: toolName,  // ✅ CORRECT FIELD NAME
                params: params
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            resultDiv.textContent = `✅ Result:\\n${JSON.stringify(result.result, null, 2)}`;
            resultDiv.className = 'result-area success';
        } else {
            const error = await response.json();
            resultDiv.textContent = `❌ Error: ${error.detail}`;
            resultDiv.className = 'result-area error';
        }
        
    } catch (error) {
        resultDiv.textContent = `❌ Error: ${error.message}`;
        resultDiv.className = 'result-area error';
    } finally {
        card.classList.remove('loading');
    }
}

// Auto-reload tools every 5 seconds (silent check)
setInterval(async function() {
    try {
        const response = await fetch('/tools', { method: 'HEAD' });
        if (response.headers.get('ETag') !== currentETag) {
            // ETag changed, reload tools silently
            const formData = saveFormValues();
            const loadResponse = await fetch('/tools');
            if (loadResponse.ok) {
                const newTools = await loadResponse.json();
                if (newTools.length !== tools.length || 
                    JSON.stringify(newTools.map(t => t.name).sort()) !== JSON.stringify(tools.map(t => t.name).sort())) {
                    tools = newTools;
                    renderTools();
                    setTimeout(() => restoreFormValues(formData), 100);
                    updateStatus(`🔄 Auto-detected ${tools.length} tools: ${tools.map(t => t.name).join(', ')}`, 'success');
                }
            }
            currentETag = response.headers.get('ETag');
        }
    } catch (error) {
        // Silent fail for auto-reload
    }
}, 5000);

let currentETag = null;

// Load tools on page load with auto-reload enabled
document.addEventListener('DOMContentLoaded', () => loadTools(false));
'''
    return Response(
        content=js,
        media_type="application/javascript"
    )

# Initialize tools on startup
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting MCP Server with Auto-Reload...")
    discover_tools()
    logger.info(f"🔧 Server ready with {len(registry)} tools")
    if AUTO_RELOAD_TOOLS:
        logger.info("🔄 Auto-reload enabled - New tools will be detected automatically")
    else:
        logger.info("📌 Auto-reload disabled - Use ?reload=1 or restart server for new tools")

if __name__ == "__main__":
    uvicorn.run(
        "add_mcp_server.server:app",
        host=MCP_HOST,
        port=MCP_PORT,
        reload=False,
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )