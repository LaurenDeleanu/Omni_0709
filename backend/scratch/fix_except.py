lines = open("app/api/v1/ai.py").readlines()
# Insert except block after line 291 (0-indexed 290)
idx = 290
except_block = [
    "    except Exception as e:\n",
    "        logger.error(f\"Error ejecutando Copiloto de Plataforma: {e}\")\n",
    "        raise HTTPException(status_code=500, detail=str(e))\n",
    "\n",
]
new_lines = lines[:idx] + except_block + lines[idx:]
open("app/api/v1/ai.py", "w").writelines(new_lines)
print("Inserted except block after line 291")
