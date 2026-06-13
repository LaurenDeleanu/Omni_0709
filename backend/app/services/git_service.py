import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def parse_github_repo(repo_url: str) -> Optional[str]:
    """
    Extrae el par 'owner/repo' de un URL de GitHub.
    Ejemplo: 'https://github.com/LaurenDeleanu/SAS' -> 'LaurenDeleanu/SAS'
    """
    if not repo_url:
        return None
    url = repo_url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    
    prefixes = ["https://github.com/", "http://github.com/", "git@github.com:"]
    for prefix in prefixes:
        if url.startswith(prefix):
            return url[len(prefix):]
            
    # Fallback si ya es en formato owner/repo
    if "/" in url and not url.startswith("http"):
        return url
    return None

async def create_github_branch(repo_url: str, token: str, base_branch: str, new_branch: str) -> bool:
    """
    Crea una rama en GitHub a partir de una rama base.
    """
    owner_repo = parse_github_repo(repo_url)
    if not owner_repo:
        logger.error(f"Formato de repositorio GitHub inválido: {repo_url}")
        return False
        
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Obtener la referencia (SHA) de la rama base
            ref_url = f"https://api.github.com/repos/{owner_repo}/git/ref/heads/{base_branch}"
            resp = await client.get(ref_url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Error al obtener rama base {base_branch}: {resp.text}")
                return False
                
            sha = resp.json().get("object", {}).get("sha")
            if not sha:
                return False
                
            # 2. Crear la nueva rama
            create_url = f"https://api.github.com/repos/{owner_repo}/git/refs"
            payload = {
                "ref": f"refs/heads/{new_branch}",
                "sha": sha
            }
            create_resp = await client.post(create_url, headers=headers, json=payload)
            if create_resp.status_code == 201:
                return True
            else:
                logger.error(f"Error al crear rama {new_branch}: {create_resp.text}")
                return False
        except Exception as e:
            logger.error(f"Fallo en create_github_branch: {e}")
            return False

async def commit_github_files(
    repo_url: str,
    token: str,
    branch_name: str,
    files: List[Dict[str, str]], # [{path: "src/file.ts", content: "..."}]
    commit_message: str
) -> bool:
    """
    Agrega archivos a una rama de GitHub usando la API de contenidos (adecuado para archivos de tamaño normal).
    """
    owner_repo = parse_github_repo(repo_url)
    if not owner_repo:
        return False
        
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            for f in files:
                path = f["path"]
                content_b64 = base64_encode(f["content"])
                
                # Intentar obtener el archivo para ver si ya existe (necesitamos su SHA para actualizarlo)
                file_url = f"https://api.github.com/repos/{owner_repo}/contents/{path}?ref={branch_name}"
                get_resp = await client.get(file_url, headers=headers)
                sha = None
                if get_resp.status_code == 200:
                    sha = get_resp.json().get("sha")
                    
                # Realizar commit/put
                put_url = f"https://api.github.com/repos/{owner_repo}/contents/{path}"
                payload = {
                    "message": commit_message,
                    "content": content_b64,
                    "branch": branch_name
                }
                if sha:
                    payload["sha"] = sha
                    
                put_resp = await client.put(put_url, headers=headers, json=payload)
                if put_resp.status_code not in (200, 201):
                    logger.error(f"Error al commitear archivo {path}: {put_resp.text}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Fallo en commit_github_files: {e}")
            return False

async def create_github_pr(
    repo_url: str,
    token: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str
) -> Optional[str]:
    """
    Crea un Pull Request en GitHub y retorna la URL del PR generado.
    """
    owner_repo = parse_github_repo(repo_url)
    if not owner_repo:
        return None
        
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    payload = {
        "title": title,
        "body": body,
        "head": head_branch,
        "base": base_branch
    }
    
    async with httpx.AsyncClient() as client:
        try:
            pr_url = f"https://api.github.com/repos/{owner_repo}/pulls"
            resp = await client.post(pr_url, headers=headers, json=payload)
            if resp.status_code == 201:
                return resp.json().get("html_url")
            else:
                logger.error(f"Error al crear PR en GitHub: {resp.text}")
                return None
        except Exception as e:
            logger.error(f"Fallo en create_github_pr: {e}")
            return None

def base64_encode(text: str) -> str:
    """Codifica texto plano a base64 string."""
    import base64
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")
