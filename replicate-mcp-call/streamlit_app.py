import streamlit as st
import cloudinary
import cloudinary.uploader
import os
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="AI Chat with Image Upload", page_icon="💬", layout="wide"
)

# Configure Cloudinary with environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# Sidebar for authentication
with st.sidebar:
    st.header("Authentication")

    # Replicate authentication section
    st.subheader("🔌 Replicate")

    st.button("Authenticate Replicate", type="primary")

# Main chat interface
st.title("💬 AI Chat Interface")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["type"] == "text":
            st.markdown(message["content"])
        elif message["type"] == "image":
            st.image(message["content"], caption="Uploaded Image")

# Image upload section
st.subheader("📷 Upload Image")

uploaded_file = st.file_uploader(
    "Choose an image...",
    type=["png", "jpg", "jpeg", "gif", "bmp", "webp"],
    help="Upload an image to share in the chat",
)

if uploaded_file and st.button("Upload to Cloudinary"):
    try:
        # Check if Cloudinary is configured
        if not all(
            [
                os.getenv("CLOUDINARY_CLOUD_NAME"),
                os.getenv("CLOUDINARY_API_KEY"),
                os.getenv("CLOUDINARY_API_SECRET"),
            ]
        ):
            st.error(
                "❌ Cloudinary credentials not configured. Please check your .env file."
            )
        else:
            # Convert uploaded file to bytes
            bytes_data = uploaded_file.read()

            # Upload to Cloudinary using Python SDK
            with st.spinner("Uploading image..."):
                upload_result = cloudinary.uploader.upload(
                    bytes_data,
                    resource_type="image",
                    unique_filename=True,
                    overwrite=True,
                )

            # Get the secure URL
            image_url = upload_result.get("secure_url")
            public_id = upload_result.get("public_id")

            if image_url:
                st.success(f"✅ Image uploaded successfully!")
                st.info(f"🔗 Cloudinary URL: {image_url}")
                st.info(f"📁 Public ID: {public_id}")

                # Add image to chat
                st.session_state.messages.append(
                    {"role": "user", "type": "image", "content": image_url}
                )

                # Display the uploaded image
                st.image(image_url, caption="Uploaded to Cloudinary", width=300)

                # Display upload details
                with st.expander("📊 Upload Details"):
                    st.json(upload_result)

            else:
                st.error("❌ Failed to get image URL from Cloudinary")

    except Exception as e:
        st.error(f"❌ Error uploading image: {str(e)}")
        st.error("Please check your Cloudinary credentials and try again.")

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    st.session_state.messages.append(
        {"role": "user", "type": "text", "content": prompt}
    )

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        response = f"You said: '{prompt}'. This is a demo response!"
        st.markdown(response)

    # Add assistant response to chat history
    st.session_state.messages.append(
        {"role": "assistant", "type": "text", "content": response}
    )

# Display current session info
with st.expander("ℹ️ Session Information"):
    st.write("**Environment Variables Status:**")
    st.write(
        f"- Cloudinary Cloud Name: {'✅' if os.getenv('CLOUDINARY_CLOUD_NAME') else '❌'}"
    )
    st.write(
        f"- Cloudinary API Key: {'✅' if os.getenv('CLOUDINARY_API_KEY') else '❌'}"
    )
    st.write(
        f"- Cloudinary API Secret: {'✅' if os.getenv('CLOUDINARY_API_SECRET') else '❌'}"
    )
    st.write(f"**Total Messages:** {len(st.session_state.messages)}")

    # Debug: Show actual values (first few characters only for security)
    if st.checkbox("Show credential preview (debug)"):
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")

        st.write("**Credential Preview:**")
        st.write(
            f"- Cloud Name: {cloud_name[:10] + '...' if cloud_name and len(cloud_name) > 10 else cloud_name}"
        )
        st.write(
            f"- API Key: {api_key[:10] + '...' if api_key and len(api_key) > 10 else api_key}"
        )
        st.write(
            f"- API Secret: {api_secret[:10] + '...' if api_secret and len(api_secret) > 10 else api_secret}"
        )
