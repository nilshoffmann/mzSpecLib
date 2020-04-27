import os
import unittest

from mzlib.annotation import parse_annotation, MassError

class TestAnnotationParser(unittest.TestCase):
    def test_parse_failfast(self):
        assert parse_annotation("?") == []

    def test_parse_annotation_complex(self):
        base = "b14"
        parsed = parse_annotation(base)[0]
        assert parsed.series == 'b'
        assert parsed.position == 14

        base += "-H2O-NH3"

        parsed = parse_annotation(base)[0]
        assert parsed.series == 'b'
        assert parsed.position == 14
        assert parsed.neutral_loss == "-H2O-NH3"

        base += "+2i"

        parsed = parse_annotation(base)[0]
        assert parsed.series == 'b'
        assert parsed.position == 14
        assert parsed.neutral_loss == "-H2O-NH3"
        assert parsed.isotope == 2

        base += "^2"
        parsed = parse_annotation(base)[0]
        assert parsed.series == 'b'
        assert parsed.position == 14
        assert parsed.neutral_loss == "-H2O-NH3"
        assert parsed.isotope == 2
        assert parsed.charge == 2

        base += "/0.5ppm"

        parsed = parse_annotation(base)[0]
        assert parsed.series == 'b'
        assert parsed.position == 14
        assert parsed.neutral_loss == "-H2O-NH3"
        assert parsed.isotope == 2
        assert parsed.charge == 2
        assert parsed.mass_error == MassError(0.5, 'ppm')
