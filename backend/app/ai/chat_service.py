import re
import logging
from typing import Any, Dict, List, Optional, Tuple, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import (
    Project,
    CodeEntity,
    APIEndpoint,
    DatabaseModel,
    Document,
    SequenceDiagram,
    KnowledgeEdge,
    KnowledgeNode,
)
from app.ai.llm_provider import llm_provider
from app.ai.vector_store import vector_store, SearchResult
from app.services.indexer_service import project_indexer_service

logger = logging.getLogger("docpilot")


class IntentDetector:
    """Detects technical user intent from natural language questions."""

    PATTERNS: Dict[str, List[str]] = {
        "AUTHENTICATION": [
            r"\bauth\w*", r"\blogin\w*", r"\bregister\w*", r"\bsignup\w*", r"\bsign[- ]in\b",
            r"\bjwt\b", r"\btoken\w*", r"\bpassword\w*", r"\bcredential\w*", r"\boauth\w*",
            r"\bsession\w*", r"\bbearer\b",
        ],
        "ARCHITECTURE": [
            r"\barchitect\w*", r"\boverview\b", r"\bstructure\b", r"\btech[- ]stack\b",
            r"\bframework\w*", r"\blayer\w*", r"\bhigh[- ]level\b", r"\bcomponent\w*",
            r"\bdesign\b", r"\bsystem\b",
        ],
        "API_USAGE": [
            r"\bwhich apis?\b", r"\bapis? use\b", r"\bendpoint\w*", r"\broute\w*",
            r"\bhandler\w*", r"\bcontroller\w*", r"\bhttp\b", r"\brest\b",
            r"\bapi\b", r"\brequest\w*", r"\bresponse\w*",
        ],
        "DATABASE": [
            r"\bdatabas\w*", r"\bdb\b", r"\bmodel\w*", r"\bschema\w*",
            r"\btable\w*", r"\bcolumn\w*", r"\bforeign key\w*", r"\brelationship\w*",
            r"\borm\b", r"\bsql\b", r"\bentity\b", r"\bentities\b",
        ],
        "FLOW_TRACE": [
            r"\bwhat happens when\b", r"\bhow does .* work\b", r"\bflow\w*",
            r"\bprocess\w*", r"\border of\b", r"\bsequence\w*", r"\blifecycle\b",
            r"\bstep by step\b", r"\btrace\b", r"\bcheckout\b", r"\bexecution\b",
        ],
        "CODE_SEARCH": [
            r"\bwhere is\b", r"\bwhere are\b", r"\bimplemented\b", r"\bimplement\w*",
            r"\bdefined\b", r"\blocation\b", r"\bwhich file\b", r"\bfind\b", r"\bsource code\b",
        ],
    }

    @classmethod
    def detect(cls, query: str) -> Dict[str, Any]:
        lower_q = query.lower()
        scores: Dict[str, int] = {}

        for intent, patterns in cls.PATTERNS.items():
            count = 0
            for pat in patterns:
                if re.search(pat, lower_q):
                    count += 1
            if count > 0:
                scores[intent] = count

        # Extract capitalized or quoted terms (e.g. UserService, UserModel, /login)
        target_terms: List[str] = []
        words = re.findall(r"\b[A-Za-z0-9_/-]{3,}\b", query)
        for w in words:
            # Check camelCase or PascalCase or path-like
            if any(c.isupper() for c in w[1:]) or "/" in w or "_" in w:
                target_terms.append(w)
            elif w.lower() in ("login", "auth", "order", "payment", "user", "checkout"):
                target_terms.append(w)

        if not scores:
            primary_intent = "GENERAL_QA"
        else:
            primary_intent = max(scores.items(), key=lambda x: x[1])[0]

        return {
            "intent": primary_intent,
            "all_scores": scores,
            "target_terms": list(set(target_terms)),
        }


class ChatResponse(tuple):
    """
    Dual-compatibility chat response:
    - Unpacks as a 2-tuple: `answer, citations = response`
    - Has rich attributes: `.answer`, `.citations`, `.confidence`, `.intent`, `.relevant_components`
    """
    answer: str
    citations: List[Dict[str, Any]]
    confidence: str
    intent: str
    relevant_components: List[str]

    def __new__(
        cls,
        answer: str,
        citations: List[Dict[str, Any]],
        confidence: str = "",
        intent: str = "GENERAL_QA",
        relevant_components: Optional[List[str]] = None,
    ):
        inst = super().__new__(cls, (answer, citations))
        inst.answer = answer
        inst.citations = citations
        inst.confidence = confidence
        inst.intent = intent
        inst.relevant_components = relevant_components or []
        return inst


class ChatService:
    """
    Repository-Aware AI Assistant.
    Follows Phase 12 RAG Architecture:
    User Question
    → Intent Detection
    → Retrieve Relevant Knowledge
    → Retrieve Relevant Documentation
    → Retrieve Relevant Source Code Chunks
    → Include Graph Relationships
    → LLM
    → Grounded Answer
    """

    async def ask(
        self,
        query: str,
        project_id: Optional[str] = None,
        project_name: Optional[str] = None,
        repository_id: Optional[str] = None,
        repo_name: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> ChatResponse:
        """
        Executes repository-aware RAG query.
        Returns ChatResponse which unpacks as (answer, citations) and has .confidence, .intent, .relevant_components.
        """
        pid = project_id or repository_id or ""
        pname = project_name or repo_name or "the repository"

        # Step 1: Detect Intent
        intent_info = IntentDetector.detect(query)
        intent = intent_info["intent"]
        target_terms = intent_info["target_terms"]

        # Step 2: Ensure Project Vector Knowledge Base is Indexed
        if db is not None and pid:
            existing_chunks = vector_store.load_index(pid)
            if not existing_chunks:
                try:
                    await project_indexer_service.index_project(pid, db)
                except Exception as ie:
                    logger.warning(f"Auto-indexing failed for project {pid}: {ie}")

        # Step 3: Vector Search (Strictly scoped by project_id)
        search_results: List[SearchResult] = await vector_store.search(
            query=query,
            project_id=pid,
            top_k=8,
        )

        # Step 4: Structured Knowledge Retrieval from Database (if session provided)
        relevant_components: Set[str] = set()
        matched_apis: List[APIEndpoint] = []
        matched_models: List[DatabaseModel] = []
        matched_sequences: List[SequenceDiagram] = []
        matched_docs: List[Document] = []
        matched_entities: List[CodeEntity] = []
        graph_relationships: List[str] = []

        if db is not None and pid:
            # Query APIs matching intent or terms
            api_stmt = select(APIEndpoint).where(APIEndpoint.project_id == pid)
            api_res = await db.execute(api_stmt)
            all_apis = api_res.scalars().all()
            for a in all_apis:
                text_to_check = f"{a.path} {a.handler_name} {' '.join(a.tags)}".lower()
                if any(t.lower() in text_to_check for t in target_terms) or \
                   (intent == "AUTHENTICATION" and ("auth" in text_to_check or "login" in text_to_check or "register" in text_to_check)) or \
                   (intent == "FLOW_TRACE" and any(k in text_to_check for k in ["order", "payment", "login", "checkout"])):
                    matched_apis.append(a)
                    relevant_components.add(f"API: {a.method} {a.path}")
                    relevant_components.add(a.handler_name)

            # Query Models matching intent or terms
            model_stmt = select(DatabaseModel).where(DatabaseModel.project_id == pid)
            model_res = await db.execute(model_stmt)
            all_models = model_res.scalars().all()
            for m in all_models:
                m_text = f"{m.name} {m.table_name}".lower()
                if any(t.lower() in m_text for t in target_terms) or \
                   (intent == "DATABASE") or \
                   (intent == "AUTHENTICATION" and "user" in m_text):
                    matched_models.append(m)
                    relevant_components.add(f"Model: {m.name} ({m.table_name})")

            # Query Sequence Diagrams matching intent or terms
            seq_stmt = select(SequenceDiagram).where(SequenceDiagram.project_id == pid)
            seq_res = await db.execute(seq_stmt)
            all_seqs = seq_res.scalars().all()
            for s in all_seqs:
                s_text = f"{s.name} {s.flow_category} {s.trigger_endpoint}".lower()
                if any(t.lower() in s_text for t in target_terms) or \
                   (intent == "AUTHENTICATION" and s.flow_category in ("AUTHENTICATION", "REGISTRATION")) or \
                   (intent == "FLOW_TRACE" and s.flow_category in ("ORDER", "PAYMENT", "AUTHENTICATION")):
                    matched_sequences.append(s)
                    relevant_components.add(f"Sequence: {s.name}")
                    for comp in s.involved_components or []:
                        relevant_components.add(comp)

            # Query Documents (Phase 9)
            doc_stmt = select(Document).where(Document.project_id == pid)
            doc_res = await db.execute(doc_stmt)
            all_docs = doc_res.scalars().all()
            for d in all_docs:
                d_text = f"{d.title} {d.document_type}".lower()
                if intent == "ARCHITECTURE" and d.document_type in ("PROJECT_OVERVIEW", "ARCHITECTURE_OVERVIEW"):
                    matched_docs.append(d)
                elif intent == "API_USAGE" and d.document_type == "API_DOCS":
                    matched_docs.append(d)
                elif intent == "DATABASE" and d.document_type == "DATABASE_DOCS":
                    matched_docs.append(d)
                elif any(t.lower() in d_text for t in target_terms):
                    matched_docs.append(d)

            # Query Code Entities matching target terms
            if target_terms:
                ent_stmt = select(CodeEntity).where(CodeEntity.project_id == pid)
                ent_res = await db.execute(ent_stmt)
                all_ents = ent_res.scalars().all()
                for e in all_ents:
                    for t in target_terms:
                        if t.lower() in e.name.lower():
                            matched_entities.append(e)
                            relevant_components.add(f"{e.entity_type}: {e.name}")

            # Query Knowledge Graph relationships
            edge_stmt = select(KnowledgeEdge).where(KnowledgeEdge.project_id == pid)
            edge_res = await db.execute(edge_stmt)
            all_edges = edge_res.scalars().all()
            for edge in all_edges:
                edge_text = f"{edge.source_name} {edge.target_name}".lower()
                if any(t.lower() in edge_text for t in target_terms) or \
                   any(c.lower() in edge_text for c in list(relevant_components)[:5]):
                    rel_desc = f"{edge.source_name} --({edge.relationship_type})--> {edge.target_name}"
                    graph_relationships.append(rel_desc)

        # Step 5: Build Citations List with grounded term relevance filtering
        citations: List[Dict[str, Any]] = []
        seen_citations: Set[str] = set()

        stop_words = {
            "where", "is", "are", "the", "a", "an", "and", "or", "in", "on", "at", "to",
            "for", "of", "with", "by", "what", "how", "does", "do", "did", "can", "could",
            "would", "which", "when", "why", "implemented", "work", "works", "working",
            "explain", "project", "code", "repo", "repository", "system", "file", "files",
            "about", "show", "tell", "me", "used", "uses", "using", "defined", "find",
            "handler", "handlers", "service", "services", "function", "functions", "method", "methods",
            "class", "classes", "endpoint", "endpoints", "api", "apis", "route", "routes",
            "model", "models", "component", "components", "implementation", "implementations",
        }
        unique_terms = list(set([w.lower() for w in re.findall(r"\b[a-zA-Z0-9_]{3,}\b", query) if w.lower() not in stop_words]))
        min_required = 2 if len(unique_terms) >= 3 else (1 if unique_terms else 0)

        valid_vector_results: List[SearchResult] = []
        for res in search_results:
            chunk = res.chunk
            # Strip template structural labels so query words like 'signature' or 'docstring' don't falsely match
            clean_content = re.sub(r"\b(Signature|Docstring|Methods|Fields|Columns|Parameters|Parent|Security):", "", chunk.content, flags=re.IGNORECASE)
            chunk_text = f"{chunk.title} {chunk.file_path} {clean_content}".lower()
            matched_count = sum(1 for t in unique_terms if t in chunk_text)
            term_match = matched_count >= min_required if unique_terms else True
            # For architecture queries, allow general overview chunks; for specific questions, require term match or high similarity
            if intent in ("ARCHITECTURE", "GENERAL_QA"):
                if term_match or chunk.chunk_type in ("file", "class") or res.score >= 0.35:
                    valid_vector_results.append(res)
            elif term_match:
                valid_vector_results.append(res)

        # From filtered vector chunks
        for res in valid_vector_results:
            chunk = res.chunk
            cite_key = f"{chunk.file_path}:{chunk.start_line}"
            if cite_key not in seen_citations:
                seen_citations.add(cite_key)
                citations.append({
                    "file": chunk.file_path,
                    "lines": f"{chunk.start_line}-{chunk.end_line}" if chunk.end_line > chunk.start_line else str(chunk.start_line),
                    "title": chunk.title,
                    "type": chunk.chunk_type,
                    "relevance": round(res.score, 3),
                })
                # Add component from title if applicable
                if chunk.chunk_type in ("class", "function", "api", "model"):
                    relevant_components.add(chunk.title)

        # From matched APIs
        for a in matched_apis[:3]:
            cite_key = f"{a.file_path}:1"
            if cite_key not in seen_citations:
                seen_citations.add(cite_key)
                citations.append({
                    "file": a.file_path,
                    "lines": "1-30",
                    "title": f"Route: {a.method} {a.path}",
                    "type": "api",
                    "relevance": 0.95,
                })

        # From matched Models
        for m in matched_models[:3]:
            cite_key = f"{m.file_path}:1"
            if cite_key not in seen_citations:
                seen_citations.add(cite_key)
                citations.append({
                    "file": m.file_path,
                    "lines": "1-40",
                    "title": f"Model: {m.name}",
                    "type": "model",
                    "relevance": 0.92,
                })

        # From matched Entities
        for e in matched_entities[:4]:
            cite_key = f"{e.file_path}:{e.start_line}"
            if cite_key not in seen_citations:
                seen_citations.add(cite_key)
                citations.append({
                    "file": e.file_path,
                    "lines": f"{e.start_line}-{e.end_line}",
                    "title": f"{e.entity_type} {e.name}",
                    "type": "code",
                    "relevance": 0.90,
                })

        # Clean components list
        clean_components = sorted(list(relevant_components))[:8]

        # Step 6: Negative Constraint Check & Confidence Evaluation
        # If no citations or no direct DB entities matched
        max_score = max([r.score for r in valid_vector_results], default=0.0)
        has_direct_evidence = (
            len(matched_apis) > 0 or
            len(matched_models) > 0 or
            len(matched_entities) > 0 or
            len(matched_sequences) > 0 or
            (len(valid_vector_results) > 0 and max_score >= 0.28)
        )

        if not has_direct_evidence or len(citations) == 0:
            confidence = "Low Confidence (No matching components found)"
            answer = (
                f"### Repository Analysis: Insufficient Evidence\n\n"
                f"Based on the static analysis and repository index of **{pname}**, "
                f"no matching code entities, API endpoints, or database models were found for:\n\n"
                f"> *\"{query}\"*\n\n"
                f"The repository does not appear to implement or reference this functionality. "
                f"DocPilot AI does not generate unverified claims for components not present in the analyzed codebase."
            )
            return ChatResponse(answer, [], confidence, intent, [])

        # Determine confidence score string
        if max_score >= 0.60 or len(matched_apis) + len(matched_models) + len(matched_entities) >= 2:
            confidence = f"High Confidence ({len(citations)} source citations, {len(clean_components)} components verified)"
        elif max_score >= 0.35 or len(citations) >= 2:
            confidence = f"Medium Confidence ({len(citations)} relevant references identified)"
        else:
            confidence = "Moderate Confidence (Inferred from general repository structure)"

        # Step 7: Build Context Str for Response Generation
        context_sections: List[str] = []

        if matched_apis:
            api_lines = [f"- `{a.method} {a.path}` -> handler: `{a.handler_name}` ({a.file_path})" for a in matched_apis[:5]]
            context_sections.append("#### Detected APIs:\n" + "\n".join(api_lines))

        if matched_models:
            model_lines = [f"- `{m.name}` (table: `{m.table_name}`) in `{m.file_path}`" for m in matched_models[:5]]
            context_sections.append("#### Database Models:\n" + "\n".join(model_lines))

        if matched_sequences:
            seq_lines = [f"- **{s.name}** ({s.flow_category}): trigger `{s.trigger_method} {s.trigger_endpoint}`, steps: {len(s.steps or [])}" for s in matched_sequences[:3]]
            context_sections.append("#### Discovered Sequence Flows:\n" + "\n".join(seq_lines))

        if graph_relationships:
            context_sections.append("#### Knowledge Graph Relationships:\n" + "\n".join([f"- {r}" for r in graph_relationships[:6]]))

        if valid_vector_results:
            chunk_snippets = []
            for r in valid_vector_results[:5]:
                chunk_snippets.append(
                    f"**[{r.chunk.chunk_type.upper()}] {r.chunk.title}** (`{r.chunk.file_path}:{r.chunk.start_line}`):\n"
                    f"```\n{r.chunk.content[:450]}\n```"
                )
            context_sections.append("#### Code & Knowledge Chunks:\n" + "\n\n".join(chunk_snippets))

        full_context = "\n\n".join(context_sections)

        # Step 8: LLM Generation (if configured)
        if llm_provider.is_configured():
            system_prompt = (
                f"You are DocPilot AI Assistant, an expert codebase engineering companion for project '{pname}'.\n"
                "Your answers MUST adhere to these strict rules:\n"
                "1. Answer the developer's question directly, accurately, and comprehensively using ONLY the provided repository context.\n"
                "2. Explicitly cite exact file paths, function names, classes, endpoints, and line numbers.\n"
                "3. Never invent or hallucinate libraries, endpoints, or files that do not appear in the context.\n"
                "4. If information about a requested feature is absent or incomplete, state clearly that it was not found in the codebase.\n"
                "5. Provide clean markdown with headings, bullet points, and code snippets where appropriate."
            )

            user_prompt = (
                f"Developer Question: {query}\n"
                f"Detected Technical Intent: {intent}\n\n"
                f"Repository Grounded Context:\n{full_context}\n\n"
                "Provide a detailed, grounded technical explanation:"
            )

            try:
                answer = await llm_provider.generate(prompt=user_prompt, system_prompt=system_prompt)
                return ChatResponse(answer, citations, confidence, intent, clean_components)
            except Exception as e:
                logger.warning(f"LLM Provider error: {e}, falling back to deterministic synthesis.")

        # Step 9: Local Intelligence Mode (Deterministic Structured Response)
        answer = self._generate_deterministic_response(
            query=query,
            intent=intent,
            project_name=pname,
            components=clean_components,
            citations=citations,
            matched_apis=matched_apis,
            matched_models=matched_models,
            matched_sequences=matched_sequences,
            graph_relationships=graph_relationships,
            search_results=valid_vector_results,
            confidence=confidence,
        )

        return ChatResponse(answer, citations, confidence, intent, clean_components)

    def _generate_deterministic_response(
        self,
        query: str,
        intent: str,
        project_name: str,
        components: List[str],
        citations: List[Dict[str, Any]],
        matched_apis: List[APIEndpoint],
        matched_models: List[DatabaseModel],
        matched_sequences: List[SequenceDiagram],
        graph_relationships: List[str],
        search_results: List[SearchResult],
        confidence: str,
    ) -> str:
        """
        Synthesizes a grounded, highly structured technical answer from AST,
        dependencies, APIs, schemas, and sequence flows.
        """
        lines: List[str] = []

        # Header & Summary
        if intent == "AUTHENTICATION":
            lines.append(f"### Authentication & Authorization in `{project_name}`\n")
            lines.append("Authentication is implemented through dedicated endpoints and handler services:")
            for a in matched_apis:
                lines.append(f"- **Endpoint**: `{a.method} {a.path}` (handler: `{a.handler_name}` in `{a.file_path}`)")
            if matched_models:
                lines.append(f"- **User Model**: `{matched_models[0].name}` in `{matched_models[0].file_path}` (table `{matched_models[0].table_name}`)")
            if matched_sequences:
                lines.append(f"- **Inferred Flow**: {matched_sequences[0].name} (Category: `{matched_sequences[0].flow_category}`)")

        elif intent == "ARCHITECTURE":
            lines.append(f"### System Architecture & Components for `{project_name}`\n")
            lines.append(f"The project architecture consists of structured layers connecting clients to APIs, business logic, and databases:")
            if matched_apis:
                lines.append(f"- **API Layer**: {len(matched_apis)} exposed endpoints managing request handling and validation.")
            if matched_models:
                lines.append(f"- **Persistence Layer**: Models like `{', '.join([m.name for m in matched_models[:4]])}` mapping relational schemas.")
            if graph_relationships:
                lines.append("- **Component Dependencies**:")
                for r in graph_relationships[:4]:
                    lines.append(f"  - `{r}`")

        elif intent == "API_USAGE":
            lines.append(f"### API Routing & Service Integration\n")
            if matched_apis:
                lines.append(f"Found **{len(matched_apis)}** matching API endpoints:")
                for a in matched_apis:
                    auth_label = "[Authenticated]" if a.authentication_required else "[Public]"
                    lines.append(f"- `{a.method} {a.path}` {auth_label}")
                    lines.append(f"  - Handler: `{a.handler_name}` in `{a.file_path}`")
                    if a.tags:
                        lines.append(f"  - Tags: {', '.join(a.tags)}")
            else:
                lines.append("No specific API endpoints matched the search terms directly.")

        elif intent == "DATABASE":
            lines.append(f"### Database Architecture & Models\n")
            if matched_models:
                lines.append(f"Found **{len(matched_models)}** database model definitions:")
                for m in matched_models:
                    fields = [f.name for f in getattr(m, "fields", []) or [] if hasattr(f, "name")]
                    lines.append(f"- **Model `{m.name}`** (Table: `{m.table_name}`) in `{m.file_path}`")
                    if fields:
                        lines.append(f"  - Fields: `{', '.join(fields[:8])}`")
            else:
                lines.append("No specific database models matched the search query.")

        elif intent == "FLOW_TRACE":
            lines.append(f"### Execution Flow & Sequence Analysis\n")
            if matched_sequences:
                seq = matched_sequences[0]
                lines.append(f"**Flow**: {seq.name}")
                lines.append(f"- **Trigger Route**: `{seq.trigger_method} {seq.trigger_endpoint}`")
                inv = [c if isinstance(c, str) else str(c.get("name", c)) for c in (seq.involved_components or [])]
                lines.append(f"- **Involved Participants**: {', '.join(inv)}")
                lines.append("\n**Step-by-Step Execution Sequence**:")
                for s in (seq.steps or [])[:6]:
                    lines.append(f"  {s.get('step_number')}. `{s.get('source')}` -> `{s.get('target')}`: {s.get('action')}")
            else:
                lines.append(f"Probable execution sequence traced across {len(matched_apis)} endpoints and related services:")
                for a in matched_apis[:3]:
                    lines.append(f"- User request -> `{a.method} {a.path}` -> `{a.handler_name}`")

        else:
            lines.append(f"### Analysis for: *\"{query}\"*\n")
            lines.append(f"Retrieved **{len(citations)}** grounded references from repository static analysis:")

        # Verified Components Section
        if components:
            lines.append("\n#### Verified Components")
            for c in components:
                lines.append(f"- `{c}`")

        # Code Excerpts
        if search_results:
            lines.append("\n#### Verified Source Code References")
            for r in search_results[:3]:
                c = r.chunk
                lines.append(f"- **`{c.file_path}:{c.start_line}`** - *{c.title}*")
                lines.append(f"```\n{c.content[:280]}{'...' if len(c.content) > 280 else ''}\n```")

        # Graph Relationships
        if graph_relationships:
            lines.append("\n#### Discovered Architecture Graph Edges")
            for rel in graph_relationships[:4]:
                lines.append(f"- `{rel}`")

        # Confidence Note
        lines.append(f"\n> **Evidence**: {confidence}")

        return "\n".join(lines)


chat_service = ChatService()
