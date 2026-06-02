import networkx as nx
from rapidfuzz import fuzz
from typing import Tuple, Optional
from app.db.repository import Repository
from google import genai
from app.config import settings
import structlog
import asyncio

logger = structlog.get_logger()
client = genai.Client(api_key=settings.GEMINI_API_KEY)

_cache_lock = asyncio.Lock()
_graph_cache: Optional[nx.Graph] = None
_author_cache: Optional[list] = None

class IdentityResolver:
    def __init__(self, repo: Repository):
        self.repo = repo

    def _normalize(self, text: str) -> str:
        return "".join(c for c in str(text).lower() if c.isalnum())

    async def _get_graph(self) -> nx.Graph:
        global _graph_cache, _author_cache
        if _graph_cache is not None:
            return _graph_cache
        
        async with _cache_lock:
            if _graph_cache is not None:
                return _graph_cache

            graph: nx.Graph = nx.Graph()
            all_authors = await self.repo.get_all_authors()
            all_identifiers = await self.repo.get_all_platform_identifiers()
            _author_cache = all_authors

            for author in all_authors:
                graph.add_node(f"author:{author.id}", type="author", name=author.name)
            for ident in all_identifiers:
                if ident.author_id:
                    node_id = f"{ident.platform}:{ident.identifier}"
                    graph.add_node(node_id, type="identifier")
                    graph.add_edge(
                        f"author:{ident.author_id}", node_id,
                        confidence=ident.confidence, source="deterministic",
                    )

            _graph_cache = graph
            return graph

    async def resolve(self, platform: str, identifier: str) -> Tuple[Optional[str], float]:
        await self._get_graph()

        author = await self.repo.get_author_by_identifier(platform, identifier)
        if author:
            logger.info("identity_matched_exact", platform=platform)
            return str(author.id), 1.0

        global _author_cache
        all_authors = _author_cache or await self.repo.get_all_authors()
        best_match_id = None
        best_score = 0.0
        normalized_id = self._normalize(identifier)

        for author in all_authors:
            scores = [
                fuzz.WRatio(normalized_id, self._normalize(str(author.name))),
                fuzz.WRatio(normalized_id, self._normalize(str(author.email).split("@")[0])),
                fuzz.WRatio(normalized_id, self._normalize(str(author.instagram or ""))),
            ]
            max_score = max(scores) / 100.0
            if max_score > best_score:
                best_score = max_score
                best_match_id = str(author.id)

        if best_score >= 0.85:
            logger.info("identity_matched_fuzzy", score=best_score)
            return best_match_id, round(best_score * 0.92, 3)

        if best_match_id and best_score >= 0.60:
            target = next((a for a in all_authors if str(a.id) == best_match_id), None)
            if target:
                llm_score = await self._llm_semantic_match(
                    identifier, str(target.name), str(target.email)
                )
                if llm_score >= 0.75:
                    logger.info("identity_matched_llm", llm_score=llm_score)
                    return best_match_id, round(llm_score * 0.85, 3)

        logger.info("identity_unresolved", platform=platform)
        return None, 0.0

    async def _llm_semantic_match(self, identifier: str, name: str, email: str) -> float:
        try:
            prompt = (
                f"Does the identifier '{identifier}' likely belong to the user "
                f"named '{name}' with email '{email}'? "
                f"Respond with ONLY a number between 0.0 and 1.0. No other text."
            )
            response = client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt,
                config=genai.types.GenerateContentConfig(temperature=0.0),
            )
            if response.text:
                raw = response.text.strip().strip("`").strip()
                return max(0.0, min(1.0, float(raw)))
            return 0.0
        except (ValueError, TypeError):
            logger.warning("llm_identity_parse_failed", raw=getattr(response, "text", ""))
            return 0.0
        except Exception:
            return 0.0
