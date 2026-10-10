"""Upload, preview, convert, and download single images or a ZIP batch."""

import io
import zipfile

import streamlit as st

from images import FORMATS, convert_image, output_name

st.set_page_config(page_title="Image Conversion", page_icon="▧", layout="centered")
st.title("Image Conversion")
st.write("Change the format or size of your images, one at a time or as a batch.")
files = st.file_uploader(
    "Choose images",
    type=["png", "jpg", "jpeg", "webp", "tif", "tiff", "gif", "bmp"],
    accept_multiple_files=True,
)
with st.form("image_options"):
    output_format = st.selectbox("Output format", list(FORMATS))
    resize = st.checkbox("Resize images")
    left, right = st.columns(2)
    width = left.number_input("Maximum width", min_value=1, max_value=4096, value=1200)
    height = right.number_input(
        "Maximum height", min_value=1, max_value=4096, value=1200
    )
    keep_aspect = st.checkbox("Keep proportions", value=True)
    quality = st.slider("JPEG / WEBP quality", 1, 100, 90)
    submitted = st.form_submit_button("Convert images", type="primary")
if submitted:
    st.session_state.pop("converted_images", None)
    if not files:
        st.error("Choose at least one image first.")
    elif len(files) > 20 or sum(file.size for file in files) > 50 * 1024 * 1024:
        st.error("Use at most 20 images and 50 MB per batch.")
    else:
        converted = []
        for index, file in enumerate(files, 1):
            try:
                data, dimensions = convert_image(
                    file.getvalue(),
                    output_format,
                    (int(width), int(height)) if resize else None,
                    keep_aspect,
                    quality,
                )
                if (
                    sum(len(item[1]) for item in converted) + len(data)
                    > 50 * 1024 * 1024
                ):
                    raise ValueError(
                        (
                            "The converted batch exceeds 50 MB. Resize images or use a "
                            "smaller batch."
                        )
                    )
                converted.append(
                    (output_name(file.name, output_format, index), data, dimensions)
                )
            except ValueError as error:
                st.error(f"{file.name}: {error}")
        st.session_state.converted_images = (output_format, converted)
if "converted_images" in st.session_state:
    saved_format, converted = st.session_state.converted_images
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for name, data, dimensions in converted:
            zip_file.writestr(name, data)
            st.subheader(name)
            st.caption(
                f"{dimensions[0]} × {dimensions[1]} pixels · {len(data) / 1024:.1f} KB"
            )
            if saved_format != "TIFF":
                st.image(data, width=350)
            st.download_button(
                "Download image", data, name, FORMATS[saved_format][1], key=name
            )
    if len(converted) > 1:
        st.download_button(
            "Download all as ZIP",
            archive.getvalue(),
            "converted-images.zip",
            "application/zip",
        )
st.caption(
    (
        "Files stay in memory for this session. JPEG uses a white "
        "background for transparency. Animated files use their first "
        "frame."
    )
)
