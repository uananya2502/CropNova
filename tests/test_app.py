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
    if status["value"] == "303 See Other":
        location = dict(status["headers"])["Location"]
        return request("GET", location)
    return status["value"], body


class TestApp(unittest.TestCase):
    def test_form_renders(self):
        status, body = request("GET", "/assess")
        self.assertEqual(status, "200 OK")
        self.assertIn("Your next crop.", body)
        self.assertIn("Where is your field?", body)
        self.assertIn('name="water_budget_mm"', body)

    def test_invalid_submission_displays_error(self):
        status, body = request("POST", "/assess", {"state": "", "objective": "find_suitable_crop"})
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertIn("Please check these details", body)
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
        self.assertIn("A few details need a closer look", body)
        self.assertIn("Needs more information", body)
        self.assertIn("Published reference", body)


if __name__ == "__main__":
    unittest.main()

