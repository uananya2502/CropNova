import io
import unittest
from urllib.parse import urlencode

from app import application


def request(method="GET", path="/", data=None):
    payload = urlencode(data or {}, doseq=True).encode()
    status = {}

    def start_response(value, headers):
        status["value"] = value
        status["headers"] = headers

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(payload)),
        "wsgi.input": io.BytesIO(payload),
    }
    body = b"".join(application(environ, start_response)).decode()
    return status["value"], body


class TestApp(unittest.TestCase):
    def test_form_renders(self):
        status, body = request()
        self.assertEqual(status, "200 OK")
        self.assertIn("Farm profile", body)
        self.assertIn("Unknown information stays unknown", body)

    def test_invalid_submission_displays_error(self):
        status, body = request("POST", "/assess", {"state": "", "objective": "find_suitable_crop"})
        self.assertEqual(status, "200 OK")
        self.assertIn("INVALID_INPUT", body)
        self.assertIn("State or region is required", body)

    def test_assessment_displays_unknowns_and_trace(self):
        status, body = request(
            "POST",
            "/assess",
            {
                "state": "Test State",
                "season": "rabi",
                "water_availability": "moderate",
                "soil_texture": "loamy",
                "soil_ph": "7",
                "soil_fertility": "moderate",
                "irrigation": "available",
                "objective": "find_suitable_crop",
            },
        )
        self.assertEqual(status, "200 OK")
        self.assertIn("NO_SUPPORTED_KNOWLEDGE", body)
        self.assertIn("Unknown / needs review", body)
        self.assertIn("Assignments examined", body)


if __name__ == "__main__":
    unittest.main()

