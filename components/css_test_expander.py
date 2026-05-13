import streamlit as st

def render_css_test_expander():
    """A test component with an expander for CSS experimentation."""
    
    st.header("🎨 CSS Test Expander")
    st.markdown("Use this component to test different CSS styles for expanders and text areas.")
    
    # Sample text content for testing
    sample_text = """This is a sample text file content for testing CSS styling.

You can modify the CSS in the expander below to experiment with:
- Font colors
- Background colors
- Borders
- Cursors
- Font weights
- And much more!

Feel free to play around with different color combinations and styles."""

    # CSS Test Expander
    with st.expander("📄 Test File Contents (Click to expand)"):
        # Custom CSS for experimentation
        st.markdown(sample_text)
        
    
    # Additional styling options
    st.subheader("🔧 Quick Style Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Current Styles:**")
        st.markdown("- Font: Courier New, monospace")
        st.markdown("- Border: Blue with rounded corners")
        st.markdown("- Background: Light gray")
        st.markdown("- Hover effects enabled")
    
    with col2:
        st.markdown("**Try These Colors:**")
        st.markdown("- `#dc3545` (Red)")
        st.markdown("- `#28a745` (Green)")
        st.markdown("- `#ffc107` (Yellow)")
        st.markdown("- `#6f42c1` (Purple)")
    
    st.info("💡 **Tip:** Edit the CSS in the expander above to see real-time changes. You can modify colors, borders, fonts, and more!")

if __name__ == "__main__":
    render_css_test_expander()
