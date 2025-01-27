import fitz  # PyMuPDF
import openai
import streamlit as st
from datetime import datetime
import json
import random
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Initialize OpenAI API key

openai.api_key = "OpenAI KEY"
# Metadata template
metadata_template = {
    "catalog_name": "MeData",
    "file_name": "",
    "file_directory": [],
    "file_type": [],
    "page_count": [],
    "storage_type": ["local"],
    "last_modified": [],
    "chunks": {}
}

# Function to extract text from PDF
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    pages_content = []
    for page_num in range(doc.page_count):
        page = doc[page_num]
        pages_content.append(page.get_text())
    return pages_content

# Function to create metadata template
def create_metadata_template(file_name):
    metadata = metadata_template.copy()
    metadata["file_name"] = file_name
    metadata["last_modified"] = [datetime.now().isoformat()]
    return metadata

# Function to detect tags using OpenAI API
def detect_tags_with_openai(text):
    prompt = (
        "Extract key information as JSON format where each key has a 'value' and 'evidence'. "
        f"Text: {text}"
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts structured data."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0
    )

    response_text = response.choices[0].message['content'].strip()
    try:
        extracted_tags = json.loads(response_text)
    except json.JSONDecodeError:
        st.error("Error: Unable to parse JSON response from OpenAI")
        extracted_tags = {}

    return extracted_tags

# Parse PDF and generate metadata
def parse_to_metadata(file, file_name):
    metadata = create_metadata_template(file_name)

    if file_name.endswith(".pdf"):
        pages_content = extract_text_from_pdf(file)
        metadata["page_count"] = [len(pages_content)]

        for i, page_text in enumerate(pages_content):
            chunk_key = f"{i}"
            metadata["chunks"][chunk_key] = {"page_range": [str(i + 1)]}
            extracted_tags = detect_tags_with_openai(page_text)

            for tag, tag_data in extracted_tags.items():
                metadata["chunks"][chunk_key][tag] = tag_data

                if tag not in metadata:
                    metadata[tag] = []
                metadata[tag].append(tag_data.get("value", ""))

    return metadata

# Generate random color
def random_color():
    return (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))

# Generate image with colored tag wrappers
def generate_colored_tags_image(metadata):
    img_width, img_height = 800, 1000
    img = Image.new("RGB", (img_width, img_height), "white")
    draw = ImageDraw.Draw(img)

    font = ImageFont.load_default()
    y_position = 20

    for chunk in metadata["chunks"].values():
        for tag, tag_data in chunk.items():
            if "value" in tag_data:
                value = tag_data["value"]
                color = random_color()
                text = f"{tag}: {value}"

                text_bbox = draw.textbbox((20, y_position), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                draw.rectangle(
                    [(20, y_position), (20 + text_width + 10, y_position + text_height + 10)],
                    fill=color
                )

                draw.text((25, y_position + 5), text, fill="black", font=font)
                y_position += text_height + 20

                if y_position > img_height - 40:
                    img = img.resize((img_width, y_position + 40))
                    draw = ImageDraw.Draw(img)

    return img

# Streamlit UI
st.title("Metadata Generator Tool")

uploaded_file = st.file_uploader("Upload a PDF or Image", type=["pdf", "jpg", "png"])

if uploaded_file:
    file_name = uploaded_file.name
    file_type = file_name.split(".")[-1]

    st.write(f"**File Name:** {file_name}")
    st.write(f"**File Type:** {file_type}")

    if file_type == "pdf":
        metadata = parse_to_metadata(uploaded_file, file_name)

        # Save metadata as JSON
        output_json = json.dumps(metadata, indent=4)
        st.download_button(
            label="Download Metadata as JSON",
            data=output_json,
            file_name="metadata.json",
            mime="application/json"
        )

        # Display metadata
        st.subheader("Extracted Metadata:")
        st.json(metadata)

        # Generate and display image with tags
        st.subheader("Visualized Tags:")
        tag_image = generate_colored_tags_image(metadata)
        img_bytes = BytesIO()
        tag_image.save(img_bytes, format="PNG")
        st.image(tag_image, caption="Tags Visualization")

        # Download tag image
        st.download_button(
            label="Download Tag Visualization Image",
            data=img_bytes.getvalue(),
            file_name="tag_visualization.png",
            mime="image/png"
        )
    else:
        st.error("Currently, only PDF files are supported for metadata generation.")
