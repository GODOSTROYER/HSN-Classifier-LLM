import os
import json
import asyncio
from typing import AsyncGenerator
from .base import AgentProvider
from config import LOCAL_AGENT_PATH

class LocalAgentProvider(AgentProvider):
    """
    Provider implementation for a Local Agent executed via a script.
    It passes the prompts to the local script and reads the output.
    """

    async def generate_response(self, system_prompt: str, user_prompt: str, 
                                max_tokens: int = 4096, temperature: float = 0.1) -> str:
        
        if not LOCAL_AGENT_PATH or not os.path.exists(LOCAL_AGENT_PATH):
            raise FileNotFoundError(f"Local agent script not found at: {LOCAL_AGENT_PATH}")

        # Construct input payload to send to the local agent script via stdin
        payload = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # We assume the local agent is an executable or python script
        # In a real scenario, you'd adjust how this is called (e.g. `python local_agent.py`)
        # Here we just run it directly as an executable script
        process = await asyncio.create_subprocess_exec(
            LOCAL_AGENT_PATH,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate(input=json.dumps(payload).encode('utf-8'))
        
        if process.returncode != 0:
            raise Exception(f"Local agent error: {stderr.decode('utf-8')}")
            
        return stdout.decode('utf-8').strip()

    async def generate_streaming_response(self, system_prompt: str, user_prompt: str, 
                                          max_tokens: int = 16384, temperature: float = 0.15) -> AsyncGenerator[str, None]:
        
        if not LOCAL_AGENT_PATH or not os.path.exists(LOCAL_AGENT_PATH):
            raise FileNotFoundError(f"Local agent script not found at: {LOCAL_AGENT_PATH}")

        payload = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        
        process = await asyncio.create_subprocess_exec(
            LOCAL_AGENT_PATH,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        process.stdin.write(json.dumps(payload).encode('utf-8'))
        await process.stdin.drain()
        process.stdin.close()
        
        # Read streaming output line by line
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            line_str = line.decode('utf-8').strip()
            if line_str:
                yield line_str
                
        await process.wait()
        if process.returncode != 0:
            stderr = await process.stderr.read()
            raise Exception(f"Local agent error: {stderr.decode('utf-8')}")
