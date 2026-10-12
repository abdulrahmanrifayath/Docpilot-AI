from typing import Any, Dict, List, Tuple

from app.ai.llm_provider import llm_provider
from app.ai.vector_store import vector_store


class ChatService:
    async def ask(
        self,
        query: str,
        repository_id: str,
        repo_name: str,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Executes a RAG query against repository vectors and generates a grounded response.
        Returns: (answer_markdown, list_of_citations)
        """
        # Step 1: Retrieve relevant chunks
        search_results = await vector_store.search(query=query, repository_id=repository_id, top_k=5)

        citations: List[Dict[str, Any]] = []
        context_parts: List[str] = []

        for res in search_results:
            chunk = res.chunk
            citation = {
                "file": chunk.file_path,
                "lines": f"{chunk.start_line}-{chunk.end_line}" if chunk.end_line > chunk.start_line else str(chunk.start_line),
                "title": chunk.title,
                "type": chunk.chunk_type,
                "relevance": round(res.score, 3),
            }
            citations.append(citation)

            context_parts.append(
                f"### [{chunk.chunk_type.upper()}] {chunk.title} (`{chunk.file_path}:{citation['lines']}`)\n"
                f"```\n{chunk.content}\n```"
            )

        context_str = "\n\n".join(context_parts) if context_parts else "No specific code chunks matched."

        # Step 2: Check if LLM provider is configured
        if not llm_provider.is_configured():
            answer = (
                f"ℹ️ **Local Intelligence Mode (No LLM API Key Configured)**\n\n"
                f"You asked: *\"{query}\"*\n\n"
                f"To generate natural language generative responses, please add your OpenAI API key or Ollama configuration in the **Settings** tab.\n\n"
                f"In the meantime, DocPilot AI's static semantic search retrieved the top **{len(citations)}** relevant code references from **{repo_name}**:\n\n"
            )
            for c, res in zip(citations, search_results):
                answer += (
                    f"#### 📄 `{c['file']}` (Lines {c['lines']}) — *{c['title']}*\n"
                    f"```\n{res.chunk.content[:400]}{'...' if len(res.chunk.content) > 400 else ''}\n```\n\n"
                )
            return answer, citations

        # Step 3: LLM is configured: synthesize response using RAG
        system_prompt = (
            f"You are DocPilot AI Assistant, an intelligent software engineering companion for repository '{repo_name}'.\n"
            "Answer the developer's question directly, clearly, and concisely using the provided context.\n"
            "Cite exact file paths, class names, functions, and line ranges wherever relevant.\n"
            "If the context does not contain enough information, explain what is known from the repository structure."
        )

        user_prompt = (
            f"Developer Question: {query}\n\n"
            f"Repository Context:\n{context_str}\n\n"
            "Provide a comprehensive, accurate technical explanation:"
        )

        try:
            answer = await llm_provider.generate(prompt=user_prompt, system_prompt=system_prompt)
        except Exception as e:
            answer = (
                f"⚠️ Error communicating with configured LLM Provider: {str(e)}\n\n"
                "Retrieved context references are listed below."
            )

        return answer, citations


chat_service = ChatService()
