import re

annotation_pattern = re.compile(r"""
^(?:(?P<analyte_reference>[^/\s]+)@)?
   (?:(?:(?P<series>[axbycz]\.?)(?P<ordinal>\d+))|
   (?P<series_internal>[m](?P<internal_start>\d+):(?P<internal_end>\d+))|
   (?P<precursor>p)|
   (:?I(?P<immonium>[ARNDCEQGHKMFPSTWYVIL])(?:\[(?P<immonium_modification>(?:[^\]]+))\])?)|
   (?P<reporter>r(?:
    (?:\[
        (?P<reporter_label>[^\]]+)
    \])
   ))|
   (?:_(?P<external_ion>[^\s,/]+))
)
(?P<neutral_loss>(?:[+-]\d*
    (?:(?:[A-Z][A-Za-z0-9]*)|
        (?:\[
            (?:
                (?:[A-Za-z0-9:\.]+)
            )
            \])
    )
)+)?
(?:(?P<isotope>[+-]\d*)i)?
(?:\[M(?P<adduct>(:?[+-]\d*[A-Z][A-Za-z0-9]*)+)\])?
(?:\^(?P<charge>[+-]?\d+))?
(?:/(?P<mass_error>[+-]?\d+(?:\.\d+)?)(?P<mass_error_unit>ppm)?)?
""", re.X)

# At the time of first writing, this pattern could be translated into the equivalent
# ECMAScript compliant regex:
# ^(?:(?:(?<series>[axbycz]\.?)(?<ordinal>\d+))|(?<series_internal>[m](?<internal_start>\d+):(?<internal_end>\d+))|(?<precursor>p)|(:?I(?<immonium>[ARNDCEQGHKMFPSTWYVIL]))|(?<reporter>r(?<reporter_mass>\d+(?:\.\d+)))|(?:_(?<external_ion>[^\s,/]+)))(?<neutral_loss>(?:[+-]\d*(?:(?:[A-Z][A-Za-z0-9]*)|(?:\[(?:(?:[A-Za-z0-9:\.]+)|(?:\d+(?:\.\d+)?))\])))+)?(?:(?<isotope>[+-]\d*)i)?(?:\[M(?<adduct>(:?[+-]\d*[A-Z][A-Za-z0-9]*)+)\])?(?:\^(?<charge>[+-]?\d+))?(?:@(?<analyte_reference>[^/\s]+))?(?:/(?<mass_error>[+-]?\d+(?:\.\d+)?)(?<mass_error_unit>ppm)?)?
# Line breaks not introduced to preserve syntactic correctness.

def _sre_to_ecma(pattern):
    return pattern.replace("?P<", "?<").replace("\n", '')


class MassError(object):
    _DEFAULT_UNIT = "Da"

    def __init__(self, mass_error, unit=None):
        if unit is None:
            unit = self._DEFAULT_UNIT
        self.mass_error = float(mass_error)
        self.unit = unit

    def serialize(self):
        unit = self.unit
        if unit == self._DEFAULT_UNIT:
            unit = ''
        return f"{self.mass_error}{unit}"

    def __eq__(self, other):
        return self.mass_error == other.mass_error and self.unit == other.unit

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return self.serialize()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.mass_error}, {self.unit})"


class IonAnnotationBase(object):
    __slots__ = ("series", "neutral_loss", "isotope", "adduct", "charge", "analyte_reference",
                 "mass_error", "rest")

    def __init__(self, series, neutral_loss=None, isotope=None, adduct=None, charge=None,
                 analyte_reference=None,
                 mass_error=None, rest=None):
       if isotope is None:
            isotope = 0
       if charge is None:
            charge = 1
       self.series = series
       self.neutral_loss = neutral_loss
       self.isotope = isotope
       self.adduct = adduct
       self.charge = charge
       self.analyte_reference = analyte_reference
       self.mass_error = mass_error
       self.rest = rest

    def __hash__(self):
        return hash(self.serialize())

    def __eq__(self, other):
        return self.serialize() == str(other)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return self.serialize()

    def _format_ion(self):
        raise NotImplementedError()

    def serialize(self):
        parts = []
        if self.analyte_reference is not None:
            parts.append(f"{self.analyte_reference}@")
        parts.append(self._format_ion())
        if self.neutral_loss is not None:
            parts.append(str(self.neutral_loss))
        if self.isotope != 0:
            sign = "+" if self.isotope > 0 else "-"
            isotope = abs(self.isotope)
            if isotope == 1:
                isotope = ''
            parts.append(f"{sign}{isotope}i")
        if self.adduct is not None:
            parts.append(self.adduct)
        if self.charge != 0 and self.charge != 1:
            charge = abs(self.charge)
            parts.append(f"^{charge}")
        if self.mass_error is not None:
            parts.append("/")
            parts.append(self.mass_error.serialize())
        if self.rest is not None:
            parts.append("/")
            parts.append(self.rest)
        return ''.join(parts)

    def __str__(self):
        return self.serialize()


class PeptideFragmentIonAnnotation(IonAnnotationBase):
    def __init__(self, series, position, neutral_loss=None, isotope=None, adduct=None, charge=None,
                 analyte_reference=None, mass_error=None, rest=None):
        super(PeptideFragmentIonAnnotation, self).__init__(
            series, neutral_loss, isotope, adduct, charge, analyte_reference, mass_error, rest)
        self.position = position

    def _format_ion(self):
        return f"{self.series}{self.position}"


class InternalPeptideFragmentIonAnnotation(IonAnnotationBase):
    series = "internal"

    def __init__(self, series, start_position, end_position, neutral_loss=None, isotope=None,
                 adduct=None, charge=None, analyte_reference=None, mass_error=None, rest=None):
        super(InternalPeptideFragmentIonAnnotation, self).__init__(
            series, neutral_loss, isotope, adduct, charge, analyte_reference, mass_error, rest)
        self.start_position = start_position
        self.end_position = end_position

    def _format_ion(self):
        return f"m{self.start_position}:{self.end_position}"


class PrecursorIonAnnotation(IonAnnotationBase):
    series = "precursor"

    def __init__(self, series, neutral_loss=None, isotope=None, adduct=None, charge=None,
                 analyte_reference=None, mass_error=None, rest=None):
        super(PrecursorIonAnnotation, self).__init__(
            series, neutral_loss, isotope, adduct, charge, analyte_reference, mass_error, rest)

    def _format_ion(self):
        return "p"


class ImmoniumIonAnnotation(IonAnnotationBase):
    series = "immonium"

    def __init__(self, series, amino_acids, modification=None, neutral_loss=None, isotope=None, adduct=None, charge=None,
                 analyte_reference=None, mass_error=None, rest=None):
        super(ImmoniumIonAnnotation, self).__init__(
            series, neutral_loss, isotope, adduct, charge, analyte_reference, mass_error, rest)
        self.amino_acids = amino_acids
        self.modification = modification

    def _format_ion(self):
        if self.modification is not None:
            modification = f"[{self.modification}]"
        else:
            modification = ''
        return f"I{self.amino_acids}{modification}"


class ReporterIonAnnotation(IonAnnotationBase):
    series = "reporter"

    def __init__(self, series, reporter_label, neutral_loss=None, isotope=None, adduct=None, charge=None,
                 analyte_reference=None, mass_error=None, rest=None):
        super(ReporterIonAnnotation, self).__init__(
            series, neutral_loss, isotope, adduct, charge, analyte_reference, mass_error, rest)
        self.reporter_label = reporter_label

    def _format_ion(self):
        return f"r[{self.reporter_label}]"


class ExternalIonAnnotation(IonAnnotationBase):
    series = "external"

    def __init__(self, series, label, neutral_loss=None, isotope=None, adduct=None, charge=None,
                 analyte_reference=None, mass_error=None, rest=None):
        super(ExternalIonAnnotation, self).__init__(
            series, neutral_loss, isotope, adduct, charge, analyte_reference, mass_error, rest)
        self.label = label

    def _format_ion(self):
        return f"_{self.label}"


def int_or_sign(string):
    if string == "+":
        return 1
    elif string == '-':
        return -1
    else:
        return int(string)



class AnnotationStringParser(object):
    def __init__(self, pattern):
        self.pattern = pattern

    def __call__(self, annotation_string, **kwargs):
        return self.parse_annotation(annotation_string, **kwargs)

    def parse_annotation(self, annotation_string, **kwargs):
        if annotation_string == "?" or not annotation_string:
            return []
        match = self.pattern.search(annotation_string)
        if match is None:
            raise ValueError(f"Invalid annotation string {annotation_string!r}")
        data = match.groupdict()

        adduct = None
        charge = (data.get("charge", 1))
        if charge is None:
            charge = 1
        elif charge == 0:
            raise ValueError(
                f"The charge of an annotation cannot be zero. {annotation_string}")
        else:
            charge = int(charge)
        isotope = int_or_sign(data.get('isotope', 0) or 0)
        neutral_loss = data.get("neutral_loss")
        analyte_reference = data.get("analyte_reference")

        mass_error = data.get("mass_error")
        if mass_error is not None:
            mass_error = MassError(float(mass_error), data.get("mass_error_unit"))
        annotation = self._dispatch(
            annotation_string, data, adduct, charge, isotope, neutral_loss,
            analyte_reference, mass_error, **kwargs)
        rest = annotation_string[match.end():]
        if rest == "":
            return [annotation]
        else:
            if rest[0] != ",":
                raise ValueError(f"Malformed trailing string {rest}, expected ',' for {annotation_string}")
            else:
                rest = rest[1:]
            result = [annotation]
            result.extend(self.parse_annotation(rest, **kwargs))
            return result

    def _dispatch(self, annotation_string, data, adduct, charge, isotope, neutral_loss, analyte_reference, mass_error, **kwargs):
        if data['series']:
            return self._dispatch_peptide_fragment(
                data,
                neutral_loss=neutral_loss, isotope=isotope, adduct=adduct, charge=charge,
                analyte_reference=analyte_reference, mass_error=mass_error, **kwargs)
        elif data['series_internal']:
            return self._dispatch_internal_peptide_fragment(
                data,
                neutral_loss=neutral_loss, isotope=isotope, adduct=adduct, charge=charge,
                analyte_reference=analyte_reference, mass_error=mass_error, **kwargs)
        elif data['precursor']:
            return self._dispatch_precursor(
                data,
                neutral_loss=neutral_loss, isotope=isotope, adduct=adduct, charge=charge,
                analyte_reference=analyte_reference, mass_error=mass_error, **kwargs)
        elif data['immonium']:
            return self._dispatch_immonium(
                data,
                neutral_loss=neutral_loss, isotope=isotope, adduct=adduct, charge=charge,
                analyte_reference=analyte_reference, mass_error=mass_error)
        elif data['reporter']:
            return self._dispatch_reporter(
                data,
                neutral_loss=neutral_loss, isotope=isotope, adduct=adduct, charge=charge,
                analyte_reference=analyte_reference, mass_error=mass_error, **kwargs)
        elif data['external_ion']:
            return self._dispatch_external(
                data,
                neutral_loss=neutral_loss, isotope=isotope, adduct=adduct, charge=charge,
                analyte_reference=analyte_reference, mass_error=mass_error, **kwargs)
        else:
            raise ValueError(f"Could not infer annotation type from {annotation_string}/{data}")

    def _dispatch_peptide_fragment(self, data, adduct, charge, isotope, neutral_loss, analyte_reference, mass_error, **kwargs):
        return PeptideFragmentIonAnnotation(
            data['series'], int(data['ordinal']),
            neutral_loss, isotope, adduct, charge, analyte_reference,
            mass_error)

    def _dispatch_internal_peptide_fragment(self, data, adduct, charge, isotope, neutral_loss, analyte_reference, mass_error, **kwargs):
        return InternalPeptideFragmentIonAnnotation(
            "internal", int(data['internal_start']), int(data['internal_end']),
            neutral_loss, isotope, adduct, charge, analyte_reference,
            mass_error)

    def _dispatch_precursor(self, data, adduct, charge, isotope, neutral_loss, analyte_reference, mass_error, **kwargs):
        return PrecursorIonAnnotation(
            "precursor",
            neutral_loss, isotope, adduct, charge, analyte_reference,
            mass_error)

    def _dispatch_immonium(self, data, adduct, charge, isotope, neutral_loss, analyte_reference, mass_error, **kwargs):
        return ImmoniumIonAnnotation(
            "immonium", data['immonium'], data['immonium_modification'],
            neutral_loss, isotope, adduct, charge, analyte_reference,
            mass_error)

    def _dispatch_reporter(self, data, adduct, charge, isotope, neutral_loss, analyte_reference, mass_error, **kwargs):
        return ReporterIonAnnotation(
            "reporter", (data["reporter_label"]),
            neutral_loss, isotope, adduct, charge, analyte_reference,
            mass_error)

    def _dispatch_external(self, data, adduct, charge, isotope, neutral_loss, analyte_reference, mass_error, **kwargs):
        return ExternalIonAnnotation(
            "external", data['external_ion'],
            neutral_loss, isotope, adduct, charge, analyte_reference,
            mass_error)



parse_annotation = AnnotationStringParser(annotation_pattern)
