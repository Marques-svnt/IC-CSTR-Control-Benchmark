"""Overleaf synchronization utility for the IC research project.

Handles two-way synchronization between local LaTeX files and Overleaf projects
using the Overleaf web API and session cookies.
"""

import argparse
import io
import json
import logging
import pickle
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.overleaf.com"
PROJECT_URL = f"{BASE_URL}/project"
DOWNLOAD_URL = f"{BASE_URL}/project/{{}}/download/zip"


def load_cookie_store(cookie_path: Path) -> Dict[str, Any]:
    """Loads the persisted Overleaf cookie session.

    Args:
        cookie_path: Path to the .olauth cookie file.

    Returns:
        Dict containing the session cookie and CSRF token.

    Raises:
        FileNotFoundError: If the cookie file does not exist.
        ValueError: If the cookie store is malformed.
    """
    if not cookie_path.exists():
        raise FileNotFoundError(
            f"Arquivo de autenticacao nao encontrado em '{cookie_path}'. "
            "Execute 'overleaf_setup.ps1' para fazer login no Overleaf."
        )

    with open(cookie_path, "rb") as f:
        store = pickle.load(f)

    if not isinstance(store, dict) or "cookie" not in store:
        raise ValueError("Estrutura do cookie de autenticacao invalida.")

    return store


def list_projects(cookies: Dict[str, str]) -> List[Dict[str, Any]]:
    """Retrieves all active Overleaf projects for the authenticated account.

    Args:
        cookies: Cookie dictionary containing session tokens.

    Returns:
        List of project metadata dictionaries.

    Raises:
        requests.HTTPError: If the request to Overleaf fails.
        ValueError: If project metadata cannot be parsed from the page.
    """
    logger.info("Consultando projetos no Overleaf...")
    response = requests.get(PROJECT_URL, cookies=cookies)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    meta_tag = soup.find("meta", {"name": "ol-prefetchedProjectsBlob"}) or soup.find(
        "meta", {"name": "ol-projects"}
    )

    if not meta_tag:
        raise ValueError(
            "Nao foi possivel localizar a lista de projetos na pagina do Overleaf. "
            "O cookie pode ter expirado."
        )

    raw_data = json.loads(meta_tag.get("content", "{}"))
    projects_list = (
        raw_data.get("projects", []) if isinstance(raw_data, dict) else raw_data
    )

    active_projects = [
        p
        for p in projects_list
        if not p.get("archived", False) and not p.get("trashed", False)
    ]
    return active_projects


def find_project(
    projects: List[Dict[str, Any]], query: str
) -> Optional[Dict[str, Any]]:
    """Finds a project by exact ID or case-insensitive name match.

    Args:
        projects: List of project metadata.
        query: Project ID or project name string.

    Returns:
        Matched project dictionary or None.
    """
    for p in projects:
        if p.get("id") == query:
            return p
        if p.get("name", "").strip().lower() == query.strip().lower():
            return p

    # Fallback to substring matching if exact match is not found
    for p in projects:
        if query.strip().lower() in p.get("name", "").strip().lower():
            return p

    return None


def download_project_source(
    project_id: str, cookies: Dict[str, str], dest_dir: Path
) -> List[str]:
    """Downloads the full source ZIP archive of an Overleaf project and extracts it.

    Args:
        project_id: Overleaf project identifier.
        cookies: Session cookies.
        dest_dir: Local destination directory to extract files into.

    Returns:
        List of relative paths of extracted files.
    """
    url = DOWNLOAD_URL.format(project_id)
    logger.info("Baixando arquivo ZIP do projeto %s...", project_id)
    response = requests.get(url, cookies=cookies)
    response.raise_for_status()

    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_buffer = io.BytesIO(response.content)

    extracted_files: List[str] = []
    with zipfile.ZipFile(zip_buffer) as z:
        for member in z.infolist():
            # Skip pure directory entries
            if member.filename.endswith("/"):
                continue
            z.extract(member, dest_dir)
            extracted_files.append(member.filename)
            logger.info("  -> Extraido: %s (%d bytes)", member.filename, member.file_size)

    return extracted_files


def main() -> None:
    """CLI entrypoint for Overleaf synchronization."""
    parser = argparse.ArgumentParser(
        description="Sincronizacao bidirecional com Overleaf (plano gratuito)"
    )
    parser.add_argument(
        "--list", action="store_true", help="Lista todos os projetos na conta do Overleaf"
    )
    parser.add_argument(
        "--pull",
        type=str,
        help="Baixa o codigo-fonte (ZIP) de um projeto por Nome ou ID",
    )
    parser.add_argument(
        "--dest",
        type=str,
        default="Artigos_Rascunhos/Artigo_01_Classic_Methods/overleaf",
        help="Diretorio de destino local para os arquivos baixados",
    )
    parser.add_argument(
        "--cookie-path",
        type=str,
        default=".olauth",
        help="Caminho para o arquivo de sessao (.olauth)",
    )

    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    cookie_file = base_dir / args.cookie_path

    try:
        store = load_cookie_store(cookie_file)
        cookies = store["cookie"]

        if args.list:
            projects = list_projects(cookies)
            print("\n=== PROJETOS NO OVERLEAF ===")
            for idx, p in enumerate(projects, 1):
                print(f"[{idx}] ID: {p.get('id')} | Nome: {p.get('name')}")
            print()
            return

        if args.pull:
            projects = list_projects(cookies)
            target = find_project(projects, args.pull)
            if not target:
                logger.error(
                    "Projeto '%s' nao encontrado. Use '--list' para ver os projetos disponiveis.",
                    args.pull,
                )
                sys.exit(1)

            logger.info(
                "Projeto localizado: '%s' (ID: %s)", target.get("name"), target.get("id")
            )
            dest_path = base_dir / args.dest
            extracted = download_project_source(target["id"], cookies, dest_path)
            logger.info(
                "Sucesso! %d arquivos extraidos para '%s'.", len(extracted), dest_path
            )
            return

        parser.print_help()

    except Exception as e:
        logger.error("Erro durante a execucao: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
