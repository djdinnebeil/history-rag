# langgraph_agent.py
import streamlit as st
from typing_extensions import TypedDict
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
try:
    from langchain_tavily import TavilySearchResults
except ImportError:
    from langchain_community.tools.tavily_search import TavilySearchResults
from core.retriever_chain import load_chain
from typing import Annotated
from langgraph.graph.message import add_messages
import config
from config import using_cohere, get_logger

logger = get_logger(__name__)

# ✅ Cache the chain so it reuses the same Qdrant client
@st.cache_resource
def get_chains(project_name: str, collection_name: str, source_types: list = None, year_range: tuple = None):
    return load_chain(project_name, collection_name, source_types, year_range)

# Remove the global chain initialization since it will be called from the component
# qa_chain, naive_retriever = get_chains(
#     st.session_state["selected_project"],
#     st.session_state["collection_name"]
# )


llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0)
tavily_tool = TavilySearchResults(max_results=5)

@tool
def tavily_search_tool(query: str) -> str:
    """Use this tool to search the web for recent, current, or external information not present in the historical documents. 
    This complements the historical document search by providing modern context, current events, or additional perspectives."""
    results = tavily_tool.invoke(query)

    if isinstance(results, list) and results:
        formatted = "\n\n".join(
            f"{i+1}. {r.get('title', 'No title')} — {r.get('url', 'No URL')}"
            for i, r in enumerate(results)
        )
        return f"Web search results:\n\n{formatted}"
    else:
        return "No web search results found."

@tool
def historical_rag_tool(question: str, project_name: str = None, collection_name: str = None, 
                        source_types: list = None, year_range: tuple = None) -> str:
    """Search and retrieve information from uploaded historical documents. 
    Use this tool first for any question to check what historical information is available, 
    then consider using web search to supplement with current information.
    
    Args:
        question: The question to search for
        project_name: Name of the project to search in
        collection_name: Name of the collection to search in
        source_types: Optional list of source types to filter by (e.g., ['book', 'journal'])
        year_range: Optional tuple of (start_year, end_year) for filtering
    """
    
    # Try to get project and collection from parameters first, then fall back to session state
    if project_name is None or collection_name is None:
        logger.debug("Parameters not provided, trying session state...")
        if "selected_project" in st.session_state and "collection_name" in st.session_state:
            project_name = st.session_state["selected_project"]
            collection_name = st.session_state["collection_name"]
            logger.debug(f"Got from session state: {project_name}, {collection_name}")
        else:
            logger.error("No project/collection found in session state")
            return "Error: No project selected or collection name not found."
    else:
        logger.debug(f"Using provided parameters: {project_name}, {collection_name}")
    
    if project_name and collection_name:
        logger.debug(f"Querying project: {project_name}, collection: {collection_name}")
        logger.debug(f"Source types filter: {source_types}")
        logger.debug(f"Year range filter: {year_range}")
        
        if using_cohere:
            qa_chain, naive_retriever, compression_retriever = get_chains(project_name, collection_name, source_types, year_range)
        else:
            qa_chain, naive_retriever = get_chains(project_name, collection_name, source_types, year_range)
            
        # qa_chain, naive_retriever = get_chains(project_name, collection_name, source_types, year_range)
        response = qa_chain.invoke(question)
        
        # Extract result and source documents
        result = response.get('result', '')
        source_docs = response.get('source_documents', [])
        
        logger.debug(f"Query: '{question}'")
        logger.debug(f"Response keys: {list(response.keys())}")
        logger.debug(f"Result length: {len(result)}")
        logger.debug(f"Source docs count: {len(source_docs)}")
        
        # Return a structured response that includes both result and source information
        if source_docs:
            # Format source documents for inclusion in the response
            source_info = []
            for i, doc in enumerate(source_docs, 1):
                citation = "Unknown source"
                source_type = "Unknown"
                date = "Unknown"
                
                if hasattr(doc, 'metadata') and doc.metadata:
                    citation = doc.metadata.get('citation', 'Unknown source')
                    source_type = doc.metadata.get('source_type', 'Unknown')
                    date = doc.metadata.get('date', 'Unknown')
                elif hasattr(doc, 'page_content'):
                    content = doc.page_content
                    if 'citation:' in content.lower() or 'source:' in content.lower():
                        lines = content.split('\n')
                        for line in lines:
                            if 'citation:' in line.lower() or 'source:' in line.lower():
                                citation = line.split(':', 1)[1].strip()
                                break
                
                source_info.append(f"Source {i}: {citation} [{source_type}, {date}]")
            
            # Return structured response with source information AND debug info
            filter_info = ""
            if source_types:
                filter_info += f"\nSource types filter: {source_types}"
            if year_range:
                filter_info += f"\nYear range filter: {year_range}"
            
            response_text = f"""Historical documents result:

{result}

--- SOURCE DOCUMENTS ---
{chr(10).join(source_info)}

--- FILTERS APPLIED ---{filter_info}

--- DEBUG INFO ---
Project: {project_name}
Collection: {collection_name}
Query: {question}
Result length: {len(result)}
Source docs found: {len(source_docs)}"""
            
            return response_text
        else:
            # Return debug info even when no source docs found
            filter_info = ""
            if source_types:
                filter_info += f"\nSource types filter: {source_types}"
            if year_range:
                filter_info += f"\nYear range filter: {year_range}"
            
            return f"""Historical documents result:

{result}

--- FILTERS APPLIED ---{filter_info}

--- DEBUG INFO ---
Project: {project_name}
Collection: {collection_name}
Query: {question}
Result length: {len(result)}
Source docs found: 0
WARNING: No source documents found!"""
    else:
        return "Error: No project selected or collection name not found."


# Tool belt
tool_belt = [tavily_search_tool, historical_rag_tool]
model_with_tools  = llm.bind_tools(tool_belt)

# Define AgentState
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    context: list[Document]

# Model call
def call_model(state: AgentState) -> AgentState:
    messages = state["messages"]

    # Enhanced system message to encourage using both tools when appropriate
    system_message = """You are a comprehensive research assistant. You MUST use BOTH available tools for EVERY question to provide a complete answer:

1. FIRST: Call historical_rag_tool to check your historical document knowledge base
2. SECOND: Call tavily_search_tool to find current information, additional context, or verification
3. THEN: Combine insights from both sources in your final answer
4. ALWAYS be explicit about which information comes from historical documents vs. web search

IMPORTANT: When calling historical_rag_tool, you MUST provide the project_name and collection_name parameters. These are required for the tool to access the correct historical documents.

FILTERING CAPABILITIES: The historical_rag_tool now supports source type and year filtering:
- source_types: List of source types to include (e.g., ['book', 'journal', 'newspaper', 'report', 'web_article', 'misc', 'unsorted'])
- year_range: Tuple of (start_year, end_year) for filtering by date

CRITICAL: You are NOT allowed to answer the question until you have called BOTH tools. This is a requirement for comprehensive research.

MANDATORY WORKFLOW - You MUST follow this exact sequence:
1. Call historical_rag_tool(question="...", project_name="...", collection_name="...")
2. Call tavily_search_tool(query="...")
3. Only after BOTH tools have been called, provide your comprehensive answer combining both sources.

If you try to answer without calling both tools, you will be forced to call them first.

REMEMBER: Even if the question seems purely historical, you MUST still call tavily_search_tool to check for current context, verification, or additional information. This is non-negotiable."""

    # Add system message if not already present
    if not any(msg.type == "system" for msg in messages):
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=system_message)] + messages

    response = model_with_tools.invoke(messages)
    return {
        "messages": [response],
        "context": state.get("context", [])
    }

# ToolNode
tool_node = ToolNode(tool_belt)

# Should continue logic
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message has tool calls, continue to action
    if last_message.tool_calls:
        return "action"
    else:
        return "end"

# Build graph
def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("action", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"action": "action", "end": END})
    graph.add_edge("action", "agent")

    return graph.compile()
