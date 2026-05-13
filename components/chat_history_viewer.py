import streamlit as st
import json
from datetime import datetime

def render_chat_history_viewer(con, project_name: str):
    """Render the chat history viewer component."""
    
    st.header("💬 Chat History")
    # st.markdown(f"Viewing chat history for project: **{project_name}**")
    
    # Get chat history from database
    from core.database import get_chat_history, delete_chat_entry, clear_chat_history, get_chat_history_count
    
    chat_entries = get_chat_history(con, project_name)
    chat_count = get_chat_history_count(con, project_name)
    
    if chat_count == 0:
        st.info("No chat history found for this project. Start asking questions to build up your conversation history!")
        return
    
    # Display chat count and clear button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"📊 Total Conversations: {chat_count}")
    with col2:
        if st.button("🗑️ Clear All", type="secondary"):
            if st.button("⚠️ Confirm Clear All", type="primary"):
                clear_chat_history(con, project_name)
                st.success("Chat history cleared!")
                st.rerun()
    
    st.divider()
    
    # Display chat entries
    for i, entry in enumerate(chat_entries):
        # Unpack the database row
        chat_id, question, answer, mode, citations_json, web_sources_json, tools_used_json, timestamp, proj_name = entry
        
        # Parse JSON fields
        citations = json.loads(citations_json) if citations_json else []
        web_sources = json.loads(web_sources_json) if web_sources_json else []
        tools_used = json.loads(tools_used_json) if tools_used_json else []
        
        # Format timestamp
        try:
            dt = datetime.fromisoformat(timestamp)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted_time = timestamp
        
        # Create expander header
        source_count = len(citations) + len(web_sources)
        expander_title = f"Q: {question[:60]}{'...' if len(question) > 60 else ''} ({source_count} sources) [{mode}]"
        
        with st.expander(expander_title, expanded=False):
            # Header with timestamp and delete button
            col1, col2 = st.columns([4, 1])
            with col1:
                st.caption(f"📅 {formatted_time}")
            with col2:
                if st.button("🗑️", key=f"delete_{chat_id}"):
                    delete_chat_entry(con, chat_id)
                    st.success("Chat entry deleted!")
                    st.rerun()
            
            # Question and Answer
            st.markdown(f"**Question:** {question}")
            st.markdown(f"**Answer:** {answer}")
            st.markdown(f"**Mode:** {mode}")
            
            # Display sources if available
            if citations or web_sources:
                st.markdown("**📚 Sources Consulted:**")
                
                # Historical document sources
                if citations:
                    st.markdown("**Historical Documents:**")
                    for j, citation in enumerate(citations, 1):
                        st.markdown(f"{j}. {citation}")
                
                # Web sources (for advanced mode)
                if web_sources:
                    if citations:  # Add spacing if we had historical sources
                        st.markdown("")
                    st.markdown("**Web Sources:**")
                    for j, web_source in enumerate(web_sources, len(citations) + 1):
                        st.markdown(f"{j}. {web_source}")
            
            # Display tools used for advanced mode
            if mode == "Advanced" and tools_used:
                st.markdown("**🔧 Tools Used:**")
                for tool in tools_used:
                    st.markdown(f"- {tool}")
    
    # Add some helpful information
    st.divider()
    st.info(f"""
    **Chat History Features:**
    - All conversations are automatically saved to your project database
    - Chat history persists between sessions
    - You can delete individual conversations or clear all history
    - Each entry shows the mode used, sources consulted, and tools employed
    """)
