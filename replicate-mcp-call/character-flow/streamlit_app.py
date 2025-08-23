import streamlit as st
import cloudinary
import cloudinary.uploader
import os
import re
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="🎬 UGC Generator", page_icon="🎬", layout="wide"
)

# Configure Cloudinary with environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# Predefined character URLs
PREDEFINED_CHARACTERS = [
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2PZps4l7vwC1fd4pMXytmhRAYDBUcu3HZNSFo",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2q22n4wMQ9MY3OVAuxjS8dZ04DkcXICptv7Ll",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2FKFMHVtDcfnuGL3wbEeCWSgjrohs1AdYBmRp",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2W5lYjcVc9b4PZyL0KhkgSNCqQzuA2xRfs76F",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2wPrOReDfEB1Ku65aICqL0MmlbczDjp2W47h9",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2OPkTFqCT6b0p92cYIEwxLVH4ay3XtMPFsgDk",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2qFhSZAMQ9MY3OVAuxjS8dZ04DkcXICptv7Ll",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2wMnYa8DfEB1Ku65aICqL0MmlbczDjp2W47h9",
    "https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2KUEdHyYhTCsONcWmwFvkrLVfYU43P5AoGMEj"
]

# Initialize session state
if "flow_data" not in st.session_state:
    st.session_state.flow_data = {}
if "current_step" not in st.session_state:
    st.session_state.current_step = "character_selection"
if "flow_completed" not in st.session_state:
    st.session_state.flow_completed = False

# Helper functions
def validate_url(url):
    """Validate URL format"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'  # domain...
        r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # host...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def upload_to_cloudinary(uploaded_file):
    """Upload file to Cloudinary and return URL"""
    try:
        # Check if Cloudinary is configured
        if not all([
            os.getenv("CLOUDINARY_CLOUD_NAME"),
            os.getenv("CLOUDINARY_API_KEY"),
            os.getenv("CLOUDINARY_API_SECRET"),
        ]):
            st.error("❌ Cloudinary credentials not configured. Please check your .env file.")
            return None
        
        # Convert uploaded file to bytes
        bytes_data = uploaded_file.read()
        
        # Upload to Cloudinary
        with st.spinner("Uploading image..."):
            upload_result = cloudinary.uploader.upload(
                bytes_data,
                resource_type="image",
                unique_filename=True,
                overwrite=True,
            )
        
        # Get the secure URL
        image_url = upload_result.get("secure_url")
        
        if image_url:
            st.success(f"✅ Image uploaded successfully!")
            st.info(f"🔗 Cloudinary URL: {image_url}")
            return image_url
        else:
            st.error("❌ Failed to get image URL from Cloudinary")
            return None
            
    except Exception as e:
        st.error(f"❌ Error uploading image: {str(e)}")
        return None

def reset_flow():
    """Reset the entire flow"""
    st.session_state.flow_data = {}
    st.session_state.current_step = "character_selection"
    st.session_state.flow_completed = False
    # Clean up character selection state
    if "selected_character_index" in st.session_state:
        del st.session_state.selected_character_index

# Main title
st.title("🎬 Welcome to UGC Generator!")

# Show progress
steps = ["Character Selection", "Product Image", "Dialog Generation", "Summary"]
current_step_index = {
    "character_selection": 0,
    "product_image": 1,
    "dialog_generation": 2,
    "summary": 3
}.get(st.session_state.current_step, 0)

st.progress((current_step_index + 1) / len(steps))
st.write(f"**Step {current_step_index + 1} of {len(steps)}: {steps[current_step_index]}**")

# Step 1: Character Selection
if st.session_state.current_step == "character_selection":
    st.header("=== Character Selection ===")
    
    character_choice = st.radio(
        "Choose your character option:",
        ["1. Bring your own character", "2. Use prebuild characters"],
        key="character_choice_radio"
    )
    
    if character_choice == "1. Bring your own character":
        st.write("🆕 You chose to bring your own character")
        character_url = st.text_input(
            "Enter the URL of your character:",
            key="custom_character_url",
            placeholder="https://example.com/character.jpg"
        )
        
        if character_url:
            if validate_url(character_url):
                if st.button("Confirm Character URL", type="primary"):
                    st.session_state.flow_data["character_choice"] = "custom"
                    st.session_state.flow_data["character_url"] = character_url
                    st.session_state.current_step = "product_image"
                    st.rerun()
            else:
                st.error("❌ Please enter a valid URL (must start with http:// or https://)")
    
    elif character_choice == "2. Use prebuild characters":
        st.write("🎭 You chose to use prebuild characters")
        st.write("Choose from the following characters:")
        
        # Initialize selected character if not exists
        if "selected_character_index" not in st.session_state:
            st.session_state.selected_character_index = None
        
        # Display character options in a grid
        cols = st.columns(3)  # 3 columns for better layout
        
        for i, url in enumerate(PREDEFINED_CHARACTERS):
            col_index = i % 3
            with cols[col_index]:
                # Check if this character is currently selected
                is_selected = st.session_state.selected_character_index == i
                
                try:
                    st.image(url, caption=f"Character {i+1}", width=150)
                except:
                    st.write(f"Character {i+1}")
                    st.write(f"[Image preview unavailable]")
                    st.write(f"URL: {url}")
                
                # Selection button with visual feedback
                button_type = "primary" if is_selected else "secondary"
                button_label = f"✅ Selected" if is_selected else f"Select Character {i+1}"
                
                if st.button(button_label, key=f"select_char_{i}", type=button_type, use_container_width=True):
                    if not is_selected:  # Only update if not already selected
                        st.session_state.selected_character_index = i
                        st.rerun()
        
        # Show selected character
        if st.session_state.selected_character_index is not None:
            selected_index = st.session_state.selected_character_index
            st.success(f"✅ Selected: Character {selected_index + 1}")
            
            # Show larger preview of selected character
            col1, col2 = st.columns([1, 2])
            with col1:
                try:
                    st.image(PREDEFINED_CHARACTERS[selected_index], caption=f"Selected Character {selected_index + 1}", width=200)
                except:
                    st.write(f"Character {selected_index + 1} Preview")
                    st.write(f"URL: {PREDEFINED_CHARACTERS[selected_index]}")
            
            with col2:
                st.write("**Character Details:**")
                st.write(f"- Character Number: {selected_index + 1}")
                st.write(f"- Character URL: {PREDEFINED_CHARACTERS[selected_index]}")
                st.write("")
                
                if st.button("Confirm Character Selection", type="primary", use_container_width=True):
                    st.session_state.flow_data["character_choice"] = "prebuild"
                    st.session_state.flow_data["character_selection"] = selected_index + 1
                    st.session_state.flow_data["character_url"] = PREDEFINED_CHARACTERS[selected_index]
                    st.session_state.current_step = "product_image"
                    # Clean up selection state
                    if "selected_character_index" in st.session_state:
                        del st.session_state.selected_character_index
                    st.rerun()

# Step 2: Product Image
elif st.session_state.current_step == "product_image":
    st.header("=== Product Image ===")
    st.write("Please provide your product image. You can either upload a file or enter a URL.")
    
    product_option = st.radio(
        "Choose how to provide your product image:",
        ["Upload file (will be uploaded to Cloudinary)", "Enter URL directly"],
        key="product_option_radio"
    )
    
    if product_option == "Upload file (will be uploaded to Cloudinary)":
        uploaded_file = st.file_uploader(
            "Choose a product image...",
            type=["png", "jpg", "jpeg", "gif", "bmp", "webp"],
            key="product_file_upload"
        )
        
        if uploaded_file:
            st.image(uploaded_file, caption="Product Image Preview", width=300)
            
            if st.button("Upload to Cloudinary", type="primary"):
                product_url = upload_to_cloudinary(uploaded_file)
                if product_url:
                    st.session_state.flow_data["product_image_source"] = "upload"
                    st.session_state.flow_data["product_image_url"] = product_url
                    st.session_state.current_step = "dialog_generation"
                    st.rerun()
    
    else:  # Enter URL directly
        product_url = st.text_input(
            "Enter the product image URL:",
            key="product_url_input",
            placeholder="https://example.com/product.jpg"
        )
        
        if product_url:
            if validate_url(product_url):
                st.image(product_url, caption="Product Image Preview", width=300)
                
                if st.button("Confirm Product URL", type="primary"):
                    st.session_state.flow_data["product_image_source"] = "url"
                    st.session_state.flow_data["product_image_url"] = product_url
                    st.session_state.current_step = "dialog_generation"
                    st.rerun()
            else:
                st.error("❌ Please enter a valid URL (must start with http:// or https://)")
    
    if st.button("← Back to Character Selection"):
        st.session_state.current_step = "character_selection"
        st.rerun()

# Step 3: Dialog Generation
elif st.session_state.current_step == "dialog_generation":
    st.header("=== Dialog Generation ===")
    
    dialog_choice = st.radio(
        "Choose your dialog option:",
        ["1. Enter custom dialog", "2. Auto generate dialog"],
        key="dialog_choice_radio"
    )
    
    if dialog_choice == "1. Enter custom dialog":
        st.write("📝 You chose to enter custom dialog")
        custom_dialog = st.text_area(
            "Enter your custom dialog:",
            key="custom_dialog_input",
            placeholder="Enter your dialog here...",
            height=150
        )
        
        if custom_dialog.strip():
            if st.button("Confirm Custom Dialog", type="primary"):
                st.session_state.flow_data["dialog_choice"] = "custom"
                st.session_state.flow_data["dialog_content"] = custom_dialog.strip()
                st.session_state.current_step = "summary"
                st.session_state.flow_completed = True
                st.rerun()
        else:
            st.warning("⚠️ Please enter some dialog content")
    
    elif dialog_choice == "2. Auto generate dialog":
        st.write("🤖 You chose to auto generate dialog")
        
        if st.button("Confirm Auto Generate", type="primary"):
            st.session_state.flow_data["dialog_choice"] = "auto_generate"
            st.session_state.flow_data["dialog_content"] = "[Auto-generated dialog will be created]"
            st.session_state.current_step = "summary"
            st.session_state.flow_completed = True
            st.rerun()
    
    if st.button("← Back to Product Image"):
        st.session_state.current_step = "product_image"
        st.rerun()

# Step 4: Summary
elif st.session_state.current_step == "summary":
    st.header("🎉 Flow Complete! Summary of Your Inputs")
    
    # Display all collected data
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Input Summary")
        
        # Character information
        st.write("**🎭 Character Selection:**")
        if st.session_state.flow_data.get("character_choice") == "custom":
            st.write("- Type: Custom character")
            st.write(f"- URL: {st.session_state.flow_data.get('character_url')}")
        else:
            st.write("- Type: Prebuild character")
            st.write(f"- Selection: Character {st.session_state.flow_data.get('character_selection')}")
            st.write(f"- URL: {st.session_state.flow_data.get('character_url')}")
        
        st.write("")
        
        # Product information
        st.write("**📦 Product Image:**")
        st.write(f"- Source: {st.session_state.flow_data.get('product_image_source', 'Unknown')}")
        st.write(f"- URL: {st.session_state.flow_data.get('product_image_url')}")
        
        st.write("")
        
        # Dialog information
        st.write("**💬 Dialog:**")
        st.write(f"- Type: {st.session_state.flow_data.get('dialog_choice')}")
        if st.session_state.flow_data.get('dialog_choice') == 'custom':
            st.write(f"- Content: {st.session_state.flow_data.get('dialog_content')}")
        else:
            st.write("- Content: Will be auto-generated")
    
    with col2:
        st.subheader("🖼️ Preview")
        
        # Show character image
        if st.session_state.flow_data.get('character_url'):
            st.write("**Character:**")
            try:
                st.image(st.session_state.flow_data['character_url'], caption="Selected Character", width=200)
            except:
                st.write(f"Character URL: {st.session_state.flow_data['character_url']}")
        
        # Show product image
        if st.session_state.flow_data.get('product_image_url'):
            st.write("**Product:**")
            try:
                st.image(st.session_state.flow_data['product_image_url'], caption="Product Image", width=200)
            except:
                st.write(f"Product URL: {st.session_state.flow_data['product_image_url']}")
    
    # JSON output for development
    with st.expander("📊 Raw Data (JSON)"):
        st.json(st.session_state.flow_data)
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Execute Plan (Coming Soon)", type="primary", disabled=True):
            st.info("Plan execution will be implemented later")
    
    with col2:
        if st.button("🔄 Start Over"):
            reset_flow()
            st.rerun()
    
    with col3:
        if st.button("← Back to Dialog"):
            st.session_state.current_step = "dialog_generation"
            st.session_state.flow_completed = False
            st.rerun()

# Sidebar with environment info
with st.sidebar:
    st.header("ℹ️ Environment Status")
    
    st.write("**Cloudinary Configuration:**")
    st.write(f"- Cloud Name: {'✅' if os.getenv('CLOUDINARY_CLOUD_NAME') else '❌'}")
    st.write(f"- API Key: {'✅' if os.getenv('CLOUDINARY_API_KEY') else '❌'}")
    st.write(f"- API Secret: {'✅' if os.getenv('CLOUDINARY_API_SECRET') else '❌'}")
    
    if st.session_state.flow_data:
        st.write("")
        st.write("**Current Flow Data:**")
        st.write(f"- Current Step: {st.session_state.current_step}")
        st.write(f"- Completed: {st.session_state.flow_completed}")
        st.write(f"- Data Keys: {list(st.session_state.flow_data.keys())}")
    
    if st.button("🔄 Reset Everything", type="secondary"):
        reset_flow()
        st.rerun()
