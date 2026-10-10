import io
import unittest
from pathlib import Path

from PIL import Image
from streamlit.testing.v1 import AppTest

from images import FORMATS, convert_image, output_name


def fixture(mode="RGBA", size=(80, 40), color=(255, 0, 0, 0)):
    buffer = io.BytesIO()
    Image.new(mode, size, color).save(buffer, format="PNG")
    return buffer.getvalue()


class ImageTests(unittest.TestCase):
    def test_all_formats_and_aspect_ratio(self):
        for format_name in FORMATS:
            with self.subTest(format=format_name):
                data, size = convert_image(fixture(), format_name, (20, 20))
                self.assertEqual(size, (20, 10))
                with Image.open(io.BytesIO(data)) as image:
                    self.assertEqual(image.format, format_name)
                    self.assertEqual(image.size, size)
        _, size = convert_image(fixture(), "PNG", (20, 20), False)
        self.assertEqual(size, (20, 20))

    def test_jpeg_flattens_transparency_onto_white(self):
        data, _ = convert_image(fixture(), "JPEG")
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.mode, "RGB")
            self.assertTrue(all(value >= 250 for value in image.getpixel((0, 0))))

    def test_exif_orientation(self):
        source = Image.new("RGB", (20, 40), "red")
        exif = source.getexif()
        exif[274] = 6
        stream = io.BytesIO()
        source.save(stream, format="JPEG", exif=exif)
        data, size = convert_image(stream.getvalue(), "PNG")
        self.assertEqual(size, (40, 20))
        with Image.open(io.BytesIO(data)) as image:
            self.assertNotIn(274, image.getexif())

    def test_invalid_files_and_sizes(self):
        for data, format_name, size in [
            (b"bad", "PNG", None),
            (fixture(), "BAD", None),
            (fixture(), "PNG", (0, 20)),
            (fixture(), "PNG", (5000, 20)),
        ]:
            with self.assertRaises(ValueError):
                convert_image(data, format_name, size)
        self.assertEqual(output_name("../../photo.png", "JPEG", 2), "02-photo.jpg")

    def test_empty_upload_is_a_readable_error(self):
        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=15
        ).run()
        self.assertFalse(app.exception)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn("Choose at least one image", app.error[0].value)


if __name__ == "__main__":
    unittest.main()
