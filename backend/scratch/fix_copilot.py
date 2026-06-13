lines = open("app/api/v1/ai.py").readlines()

# Find the broken /copilot endpoint (line 157-297)
# Replace it entirely with a clean working version

clean_copilot = '''    
    except Exception as e:
        logger.error(f"Error ejecutando Copiloto de Plataforma: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Session API endpoints ---
'''

# Find all lines from line 157 to line 297 and replace
# Actually: keep lines 1-156, replace 157-297, keep 298+
before = lines[:156]  # lines 1-156
after = lines[297:]   # lines 298+

# The issue is line 287 has a return StreamingResponse at wrong indent
# and line 291 has except at wrong indent
# Let me find what got broken and patch it specifically
# Actually let me just read lines 280-295 and patch

patch_lines = [
    "                yield f\"event: {event['event']}\\ndata: {_json.dumps(event['data'], ensure_ascii=False)}\\n\\n\"\n",
    "                if event.get(\"event\") == \"delta\" and event.get(\"data\", {}).get(\"content\"):\n",
    "                    full_response.append(event[\"data\"][\"content\"])\n",
    "\n",
    "            if full_response:\n",
    "                await save_conversation_turn(session.id, \"assistant\", \"\".join(full_response), db)\n",
    "\n",
    "        return StreamingResponse(\n",
    "            generate(),\n",
    "            media_type=\"text/event-stream\",\n",
    '            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},\n',
    "        )\n",
    "\n",
    "    except Exception as e:\n",
    "        logger.error(f\"Error ejecutando Copiloto de Plataforma: {e}\")\n",
    "        raise HTTPException(status_code=500, detail=str(e))\n",
    "\n",
    "\n",
    "# --- Session API endpoints ---\n",
]

new_lines = lines[:279] + patch_lines + lines[300:]
open("app/api/v1/ai.py", "w").writelines(new_lines)
print("Fixed /copilot endpoint")
