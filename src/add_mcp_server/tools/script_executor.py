"""
Script Executor Tool - Execute multi-tool scripts with orchestration
Allows users to create complex research workflows by scripting MCP tool calls
SECURITY: Sandboxed execution with strict limitations
"""

import requests
import os
import time
import json
import threading
from typing import Dict, Any, Optional, Set
import traceback
from io import StringIO
import sys
import ast


class RestrictedNodeVisitor(ast.NodeVisitor):
    """AST visitor to check for dangerous operations"""
    
    FORBIDDEN_NODES = {
        ast.Import: "Import statements are forbidden for security",
        ast.ImportFrom: "Import statements are forbidden for security", 
        ast.FunctionDef: "Function definitions are forbidden",
        ast.ClassDef: "Class definitions are forbidden",
        ast.AsyncFunctionDef: "Async function definitions are forbidden",
        ast.Global: "Global statements are forbidden",
        ast.Nonlocal: "Nonlocal statements are forbidden",
    }
    
    FORBIDDEN_FUNCTIONS = {
        'open', 'file', 'input', 'raw_input', 'execfile', 'reload',
        '__import__', 'eval', 'exec', 'compile', 'exit', 'quit',
        'help', 'license', 'copyright', 'credits', 'dir', 'vars',
        'locals', 'globals', 'delattr', 'setattr'
    }
    
    FORBIDDEN_ATTRIBUTES = {
        '__class__', '__bases__', '__subclasses__', '__mro__',
        '__globals__', '__code__', '__closure__', '__defaults__',
        '__dict__', '__weakref__', '__module__', '__file__',
        '__builtins__', '__import__'
    }
    
    def __init__(self):
        self.violations = []
    
    def visit(self, node):
        # Check forbidden node types
        for forbidden_type, message in self.FORBIDDEN_NODES.items():
            if isinstance(node, forbidden_type):
                self.violations.append(f"Line {node.lineno}: {message}")
                return
        
        # Check function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.FORBIDDEN_FUNCTIONS:
                self.violations.append(f"Line {node.lineno}: Function '{node.func.id}' is forbidden for security")
        
        # Check attribute access
        if isinstance(node, ast.Attribute):
            if node.attr in self.FORBIDDEN_ATTRIBUTES:
                self.violations.append(f"Line {node.lineno}: Attribute '{node.attr}' access is forbidden")
        
        # Continue traversing
        self.generic_visit(node)


class ScriptExecutor:
    """Execute scripts that can call other MCP tools"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or f"http://127.0.0.1:{os.getenv('MCP_PORT', '8000')}"
        self.timeout = int(os.getenv('SCRIPT_TIMEOUT_SEC', '60'))
        self.max_tool_calls = int(os.getenv('MAX_TOOL_CALLS_PER_SCRIPT', '50'))
        self.call_count = 0
        self.available_tools = self._get_available_tools()
        
    def _get_available_tools(self) -> Set[str]:
        """Get list of available MCP tools"""
        try:
            response = requests.get(f"{self.base_url}/tools", timeout=5)
            if response.status_code == 200:
                tools_data = response.json()
                return {tool.get('regName', tool.get('name', '')) for tool in tools_data if tool.get('regName') or tool.get('name')}
        except Exception:
            pass
        return set()
    
    def validate_script_security(self, script: str) -> Optional[str]:
        """Validate script for security violations"""
        try:
            tree = ast.parse(script)
            visitor = RestrictedNodeVisitor()
            visitor.visit(tree)
            
            if visitor.violations:
                return "SECURITY VIOLATIONS DETECTED:\n" + "\n".join(visitor.violations)
            
            return None
            
        except SyntaxError as e:
            return f"SYNTAX ERROR: Line {e.lineno}: {e.msg}"
        except Exception as e:
            return f"SCRIPT PARSING ERROR: {str(e)}"
    
    def call_tool(self, tool_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call another MCP tool via HTTP API"""
        
        # Check tool call limit
        if self.call_count >= self.max_tool_calls:
            error_msg = f"❌ TOOL CALL LIMIT EXCEEDED: Script tried to make {self.call_count + 1} tool calls but limit is {self.max_tool_calls}"
            raise Exception(error_msg)
        
        # Check if tool exists
        if tool_name not in self.available_tools:
            available_list = sorted(list(self.available_tools))
            error_msg = f"❌ UNKNOWN TOOL: '{tool_name}' is not available.\n📋 Available MCP tools: {available_list}"
            raise Exception(error_msg)
        
        self.call_count += 1
        
        if params is None:
            params = {}
        
        try:
            response = requests.post(
                f"{self.base_url}/execute",
                json={
                    "tool_reg": tool_name,
                    "params": params
                },
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('result', result)
            else:
                error_msg = f"❌ TOOL EXECUTION FAILED: {tool_name} returned status {response.status_code}\n🔍 Error: {response.text}"
                return {"error": error_msg, "tool": tool_name, "params": params}
                
        except requests.exceptions.Timeout:
            error_msg = f"⏱️ TIMEOUT: Tool '{tool_name}' took more than 30 seconds to respond"
            return {"error": error_msg, "tool": tool_name, "params": params}
        except Exception as e:
            error_msg = f"❌ NETWORK ERROR: Failed to call tool '{tool_name}': {str(e)}"
            return {"error": error_msg, "tool": tool_name, "params": params}
    
    def get_safe_globals(self) -> Dict[str, Any]:
        """Create safe global namespace for script execution"""
        
        # Extremely limited set of safe built-ins
        safe_builtins = {
            # Basic data types
            'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
            'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
            
            # Safe operations
            'min': min, 'max': max, 'sum': sum, 'abs': abs, 'round': round,
            'sorted': sorted, 'reversed': reversed, 'enumerate': enumerate,
            'zip': zip, 'range': range, 'any': any, 'all': all,
            
            # Type checking (safe)
            'isinstance': isinstance, 'type': type,
            
            # Safe output
            'print': print,
        }
        
        # Very limited modules
        safe_modules = {
            'json': json,  # For data manipulation
            'time': type('time', (), {'time': time.time, 'sleep': time.sleep}),  # Limited time functions
        }
        
        return {
            '__builtins__': safe_builtins,
            'call_tool': self.call_tool,
            'tools': ToolsProxy(self),
            **safe_modules
        }
    
    def execute_script(self, script: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a Python script in a secure environment"""
        
        if not script or not script.strip():
            return {
                "success": False,
                "error": "❌ EMPTY SCRIPT: No script code provided",
                "help": "Please provide a valid Python script that uses call_tool() or tools.tool_name() to interact with MCP tools"
            }
        
        # Security validation
        security_error = self.validate_script_security(script)
        if security_error:
            return {
                "success": False,
                "error": security_error,
                "help": "Scripts must only contain basic Python operations and calls to MCP tools via call_tool() or tools.tool_name()"
            }
        
        # Reset call counter
        self.call_count = 0
        
        # Prepare execution namespace
        namespace = self.get_safe_globals()
        
        # Add user variables
        if variables:
            namespace.update(variables)
        
        # Capture stdout
        old_stdout = sys.stdout
        captured_output = StringIO()
        
        try:
            # Redirect stdout to capture print statements
            sys.stdout = captured_output
            
            # Execute script with timeout
            result = self._execute_with_timeout(script, namespace)
            
            # Get captured output
            output = captured_output.getvalue()
            
            return {
                "success": True,
                "result": result,
                "output": output.strip() if output.strip() else None,
                "tool_calls_made": self.call_count,
                "execution_time_seconds": round(getattr(self, '_execution_time', 0), 2),
                "available_tools": sorted(list(self.available_tools))
            }
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Format nice error message for LLMs
            formatted_error = f"🚨 {error_type.upper()}: {error_msg}"
            
            # Add context for common errors
            help_msg = None
            if "TOOL CALL LIMIT" in error_msg:
                help_msg = f"Reduce the number of tool calls in your script (current limit: {self.max_tool_calls})"
            elif "UNKNOWN TOOL" in error_msg:
                help_msg = "Check the available_tools list in the response to see what tools are available"
            elif "TIMEOUT" in error_msg or "timed out" in error_msg.lower():
                help_msg = f"Script execution exceeded {self.timeout} seconds. Simplify your script or reduce tool calls"
            elif "SyntaxError" in error_type:
                help_msg = "Check your Python syntax. Remember: no imports, no function definitions, only basic operations and tool calls"
            
            return {
                "success": False,
                "error": formatted_error,
                "help": help_msg,
                "tool_calls_made": self.call_count,
                "output": captured_output.getvalue().strip() if captured_output.getvalue().strip() else None,
                "traceback": traceback.format_exc(),
                "available_tools": sorted(list(self.available_tools))
            }
            
        finally:
            # Restore stdout
            sys.stdout = old_stdout
    
    def _execute_with_timeout(self, script: str, namespace: Dict[str, Any]) -> Any:
        """Execute script with timeout using threading"""
        result = []
        exception = []
        
        def target():
            try:
                start_time = time.time()
                
                # Execute the script
                exec(script, namespace)
                
                # Look for result in common variable names
                result_vars = ['result', 'results', 'output', 'data', 'return_value', 'final_result']
                script_result = None
                
                for var_name in result_vars:
                    if var_name in namespace and not var_name.startswith('_'):
                        script_result = namespace[var_name]
                        break
                
                # If no explicit result variable, return all user-defined variables
                if script_result is None:
                    builtin_vars = set(self.get_safe_globals().keys())
                    script_result = {
                        k: v for k, v in namespace.items() 
                        if not k.startswith('_') and k not in builtin_vars
                    }
                
                self._execution_time = time.time() - start_time
                result.append(script_result)
                
            except Exception as e:
                exception.append(e)
        
        # Execute in thread with timeout
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            # Thread is still running - timeout occurred
            raise TimeoutError(f"Script execution timed out after {self.timeout} seconds")
        
        if exception:
            raise exception[0]
        
        return result[0] if result else None


class ToolsProxy:
    """Proxy class to allow tools.tool_name() syntax"""
    
    def __init__(self, executor: ScriptExecutor):
        self.executor = executor
    
    def __getattr__(self, tool_name: str):
        """Return a function that calls the specified tool"""
        def tool_function(**params):
            return self.executor.call_tool(tool_name, params)
        return tool_function


def run(script: str, variables: Dict[str, Any] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
    """Execute a multi-tool script
    
    Args:
        script: Python script code to execute
        variables: Optional dictionary of variables to make available in script
        timeout: Optional timeout in seconds (overrides default)
    """
    
    if not script:
        return {
            "success": False,
            "error": "❌ MISSING SCRIPT: The 'script' parameter is required",
            "help": "Provide a Python script that uses call_tool() or tools.tool_name() to orchestrate MCP tools"
        }
    
    # Create executor
    executor = ScriptExecutor()
    
    # Override timeout if specified
    if timeout:
        executor.timeout = min(max(timeout, 1), 300)  # Between 1 and 300 seconds
    
    # Execute script
    result = executor.execute_script(script, variables)
    
    return result


def spec() -> Dict[str, Any]:
    """Return the MCP function specification for Script Executor"""
    
    return {
        "type": "function",
        "function": {
            "name": "script_executor",
            "description": """🎭 SCRIPT EXECUTOR: Execute Python scripts that orchestrate multiple MCP tools

🔧 HOW IT WORKS:
- Write Python scripts that call other MCP tools
- Use call_tool('tool_name', {params}) or tools.tool_name(params=value)
- Scripts run in a secure sandbox (no file access, no imports, no network except MCP tools)
- Perfect for complex research workflows and multi-step automation

⚠️ LIMITATIONS:
- Only works with LOCAL MCP tools (not browser tools like Perplexity)
- No file system access, no imports, no network requests
- Maximum 50 tool calls per script
- 60 second execution timeout (configurable)

🎯 AVAILABLE MCP TOOLS: academic_research_super, git_github, reddit_intelligence, universal_doc_scraper, gitbook, script_executor (self)

💡 EXAMPLES:
1. Multi-source research:
   papers = tools.academic_research_super(query='AI', max_results=3)
   for paper in papers.get('results', []):
       code = tools.git_github(action='search', query=paper['title'])
   result = {'papers': papers, 'code': code}

2. Documentation analysis:
   docs = tools.universal_doc_scraper(operation='discover_docs', base_url='https://fastapi.tiangolo.com/')
   results = tools.universal_doc_scraper(operation='search_across_sites', sites=[base_url], query='authentication')
   result = {'documentation': docs, 'search_results': results}

3. Social intelligence:
   reddit_data = tools.reddit_intelligence(operation='search', query='python best practices')
   result = reddit_data""",
            
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": """Python script to execute. RULES:
- Use call_tool('tool_name', {params}) or tools.tool_name(params) to call MCP tools
- Store final result in 'result' variable or use print() for output
- Only basic Python: variables, loops, conditions, basic functions (len, str, etc.)
- NO imports, NO function definitions, NO file operations, NO network requests
- Available tools: academic_research_super, git_github, reddit_intelligence, universal_doc_scraper, gitbook

EXAMPLE:
papers = tools.academic_research_super(query='machine learning', max_results=3)
print(f'Found {len(papers.get("results", []))} papers')
result = papers"""
                    },
                    "variables": {
                        "type": "object", 
                        "description": "Optional variables to inject into script namespace (e.g., {'topic': 'AI', 'max_results': 5})",
                        "additionalProperties": True
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Execution timeout in seconds (1-300, default: 60)",
                        "minimum": 1,
                        "maximum": 300
                    }
                },
                "required": ["script"],
                "additionalProperties": False
            }
        }
    }