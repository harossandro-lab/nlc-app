"""Date formatting tests (no Qt). Same expectations as the Java Lista checks."""
import unittest
from datetime import timedelta, timezone

from nlc.formatting import DASH, format_created

UTC = timezone.utc


class FormatCreatedTests(unittest.TestCase):
    def test_like_the_web(self):
        self.assertEqual(format_created("2026-10-16T12:00:00Z", UTC), "Oct 16, 2026")
        self.assertEqual(format_created("2026-01-05T00:00:00Z", UTC), "Jan 5, 2026")

    def test_blank_is_a_dash(self):
        self.assertEqual(format_created("", UTC), DASH)
        self.assertEqual(format_created(None, UTC), DASH)

    def test_fraction_lengths_written_by_java_javascript_and_python(self):
        for iso in ("2026-10-16T17:36:28.893633100Z",   # Java Instant.toString (9 digits)
                    "2026-10-16T17:36:28.893Z",         # JavaScript toISOString (3 digits)
                    "2026-10-16T17:36:28.893633Z",      # Python (6 digits)
                    "2026-10-16T17:36:28Z"):            # Java when the nanos are zero
            self.assertEqual(format_created(iso, UTC), "Oct 16, 2026", iso)

    def test_uses_the_given_time_zone(self):
        self.assertEqual(format_created("2026-10-16T01:00:00Z", timezone(timedelta(hours=-3))), "Oct 15, 2026")

    def test_text_that_is_not_a_date_is_shown_as_is(self):
        self.assertEqual(format_created("not a date", UTC), "not a date")


if __name__ == "__main__":
    unittest.main()
