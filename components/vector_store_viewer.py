import streamlit as st
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from core.vector_store import get_qdrant_client, clear_qdrant_cache
import json
from config import get_logger

logger = get_logger(__name__)


def render_vector_store_viewer(proj_dir, qdrant_path, collection_name):
    st.subheader("🔍 Vector Store Viewer")
    logger.debug(f"render_vector_store_viewer")
    try:
        # Get Qdrant client
        project_name = proj_dir.name
        client = get_qdrant_client(project_name)
        
        # Check if collection exists
        if not client.collection_exists(collection_name):
            st.warning(f"Collection '{collection_name}' does not exist yet. Upload and process some documents first.")
            return
        
        # Get collection info
        collection_info = client.get_collection(collection_name)
        st.subheader("📊 Collection Information")
        
        # Display basic collection stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Vector Count", collection_info.vectors_count)
        with col2:
            st.metric("Points Count", collection_info.points_count)
        with col3:
            st.metric("Segments Count", collection_info.segments_count)
        
        # Debug information
        logger.debug("🔍 Debug Information")
        col1, col2 = st.columns(2)
        with col1:
            logger.debug("**Collection Name:**", collection_name)
            logger.debug("**Qdrant Path:**", str(qdrant_path))
            logger.debug("**Project Name:**", project_name)
        with col2:
            logger.debug("**Client ID:**", id(client))
            logger.debug("**Cache Status:**", "Cached" if hasattr(client, '_cached') else "Fresh")
            logger.debug("**Connection Active:**", "✅ Yes" if client.collection_exists(collection_name) else "❌ No")
        
        # Display collection configuration
        st.subheader("⚙️ Collection Configuration")
        config = collection_info.config
        st.json({
            "name": collection_name,
            "vector_size": config.params.vectors.size,
            "distance": str(config.params.vectors.distance),
            "on_disk": config.params.vectors.on_disk
        })
        
        # Search functionality
        st.subheader("🔎 Search Vector Store")
        
        # Initialize embeddings and vector store
        embeddings = OpenAIEmbeddings()
        vectorstore = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings
        )
        
        # Search interface
        search_query = st.text_input("Enter search query:", placeholder="e.g., historical event, person, or topic")
        k_results = st.slider("Number of results:", min_value=1, max_value=20, value=5)
        
        if search_query and st.button("🔍 Search"):
            with st.spinner("Searching..."):
                try:
                    # Perform similarity search
                    results = vectorstore.similarity_search(search_query, k=k_results)
                    
                    st.subheader(f"📋 Search Results for: '{search_query}'")
                    
                    for i, doc in enumerate(results, 1):
                        with st.expander(f"Result {i}: {doc.page_content[:100]}..."):
                            st.write("**Content:**")
                            st.write(doc.page_content)
                            
                            if doc.metadata:
                                st.write("**Metadata:**")
                                st.json(doc.metadata)
                            
                            # Show similarity score if available
                            if hasattr(doc, 'metadata') and 'score' in doc.metadata:
                                st.write(f"**Similarity Score:** {doc.metadata['score']:.4f}")
                
                except Exception as e:
                    st.error(f"Search failed: {str(e)}")
        
        # Sample documents from collection
        st.subheader("📚 Sample Documents")
        
        try:
            # Get a sample of points from the collection
            sample_points = client.scroll(
                collection_name=collection_name,
                limit=min(10, collection_info.points_count),
                with_payload=True,
                with_vectors=False
            )
            
            if sample_points[0]:  # points are in the first element
                st.write(f"Showing {len(sample_points[0])} sample documents:")
                
                for i, point in enumerate(sample_points[0]):
                    with st.expander(f"Document {i+1} (ID: {point.id})"):
                        if point.payload:
                            # Try to extract content and metadata
                            content = point.payload.get('page_content', 'No content available')
                            metadata = {k: v for k, v in point.payload.items() if k != 'page_content'}
                            
                            st.write("**Content:**")
                            st.write(content[:500] + "..." if len(content) > 500 else content)
                            
                            if metadata:
                                st.write("**Metadata:**")
                                st.json(metadata)
            else:
                st.info("No documents found in collection.")
                
        except Exception as e:
            st.error(f"Failed to retrieve sample documents: {str(e)}")
        
        # Collection management
        st.subheader("🗑️ Collection Management")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Collection Info"):
                st.rerun()
        
        with col2:
            if st.button("🗑️ Delete Collection", type="secondary"):
                # TODO: Implement this
                logger.debug('This is not implemented yet.')
                # if st.checkbox("I understand this will permanently delete all vectors"):
                    # try:
                    #     client.delete_collection(collection_name)
                    #     st.success(f"Collection '{collection_name}' deleted successfully!")
                    #     st.rerun()
                    # except Exception as e:
                    #     st.error(f"Failed to delete collection: {str(e)}")
        
        with col3:
            if st.button("🧹 Clear Cache"):
                try:
                    clear_qdrant_cache()
                    st.success("✅ Qdrant cache cleared successfully!")
                    st.info("🔄 Refreshing connection...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to clear cache: {str(e)}")
        
    except Exception as e:
        st.error(f"Failed to connect to vector store: {str(e)}")
        st.info("Make sure you have processed some documents first.")
