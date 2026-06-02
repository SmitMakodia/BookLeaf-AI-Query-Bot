from typing import List
from app.db.repository import Repository
from app.schemas.agent import RetrievedContext
from app.rag.retriever import retrieve_from_kb

class AgentTools:
    def __init__(self, repo: Repository):
        self.repo = repo

    async def query_db_tool(self, author_id: str) -> List[RetrievedContext]:
        books = await self.repo.get_books_by_author(author_id)
        contexts = []
        for book in books:
            add_ons = ", ".join(book.add_on_services) if book.add_on_services else "None"
            content = (
                f"Book Title: {book.book_title} | "
                f"ISBN: {book.isbn or 'Not assigned'} | "
                f"Published/Live Date: {book.book_live_date or 'Not yet published'} | "
                f"Submission Date: {book.final_submission_date or 'Not recorded'} | "
                f"Royalty Status: {book.royalty_status or 'Unknown'} | "
                f"Author Copy Status: {book.author_copy_status or 'Unknown'} | "
                f"Add-on Services: {add_ons}"
            )
            contexts.append(RetrievedContext(
                source_id=f"db:book_{book.id}",
                content=content,
                source_type="db",
                score=1.0,
            ))
        return contexts

    async def query_kb_tool(self, query: str) -> List[RetrievedContext]:
        return await retrieve_from_kb(query, top_k=5)
