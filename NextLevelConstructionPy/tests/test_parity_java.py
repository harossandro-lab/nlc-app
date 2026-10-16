"""Differential test: the Python calc and the Java CalcEngine must agree on thousands of inputs.

It compiles tests/parity/QtyParity.java against ../NextLevelConstruction/bin and runs both sides on the same cases.
Skipped when javac/java or the compiled Java classes are not available.
"""
import itertools
import math
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from nlc import calc
from nlc.models import TakeoffItem

HERE = Path(__file__).resolve().parent
JAVA_BIN = HERE.parent.parent / "NextLevelConstruction" / "bin"

PURPOSES = ["Stud", "End Studs", "Roof Sheathing", "Floor Sheathing", "Header", "Roof sheathing end stud", "Bottom Plate", ""]
LENGTHS = ["", "N/A", "n/a", "8'", "12'", "16'", '104 5/8"', '92 5/8"', "32SF", "36SF", "0'", "1/2", "3/0", "7 1/0",
           "abc", "1e2", "12d", "5f", "NaN", "Infinity", "-5'", " 10' ", "10 sf", "1_0", "0.5'"]
NUMS = ["", "0", "1", "3", "7.5", "10", "24", "100.5", "650", "-4"]
SPS = ["", "16", '16"', "24", "4'", "6'", "8'", '8"', "2 Ply", "3 Ply", "2.5 ply", "0", "abc", "12 ft", "6 in", "10'", "1 ply 16", "-3"]
MATERIALS = ["", "2X4", " 2x6 ", "HANGER"]
SPECIES = ["", "DF.No2", "HANGERS_CLIPS", "df.no2"]


def _tool(name):
    return shutil.which(name)


# LENGTH texts that Java's Double.parseDouble accepts but the workbook's VALUE() rejects ("12d", "5f" are float
# suffixes; "NaN"/"Infinity" are words). The Python port is strict (None), which matches Excel; the web app's
# parseFloat differs again ("5f" -> 5). Kept out of the comparison on purpose; see test_strict_length_quirks.
JAVA_ONLY_QUIRKS = {"12d", "5f", "NaN", "Infinity"}


def _cases(n_random=6000, seed=20261016):
    rng = random.Random(seed)
    cases = []
    # a deterministic grid over the rule-driving fields
    for purpose, length, lf, sp, ea in itertools.product(PURPOSES[:6], LENGTHS[:12], NUMS[:8], SPS[:12], NUMS[:6]):
        cases.append((purpose, length, lf, "", sp, ea, "2X4", "DF.No2"))
    for _ in range(n_random):
        cases.append((rng.choice(PURPOSES), rng.choice(LENGTHS), rng.choice(NUMS), rng.choice(NUMS), rng.choice(SPS),
                      rng.choice(NUMS), rng.choice(MATERIALS), rng.choice(SPECIES)))
    return cases


@unittest.skipUnless(_tool("javac") and _tool("java") and (JAVA_BIN / "com").exists(),
                     "javac/java or compiled Java classes (NextLevelConstruction/bin) not available")
class JavaParity(unittest.TestCase):
    def test_qty_length_and_item_key_match_java(self):
        cases = [c for c in _cases() if c[1] not in JAVA_ONLY_QUIRKS]
        self.assertGreater(len(cases), 30000)
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["javac", "--release", "17", "-encoding", "UTF-8", "-cp", str(JAVA_BIN), "-d", tmp,
                            str(HERE / "parity" / "QtyParity.java")], check=True, capture_output=True)
            stdin = "\n".join("\t".join(c) for c in cases) + "\n"
            res = subprocess.run(["java", "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-cp", f"{tmp}{';' if _is_windows() else ':'}{JAVA_BIN}",
                                  "QtyParity"], input=stdin, capture_output=True, text=True, encoding="utf-8", check=True)
        rows = res.stdout.split("\n")[:-1]
        self.assertEqual(len(rows), len(cases))
        mismatches = []
        for c, row in zip(cases, rows):
            j_qty, j_len, j_key = row.split("\t")
            purpose, length, lf, sf, sp, ea, material, species = c
            item = TakeoffItem(purpose=purpose, length=length, lf=_num(lf), sf=_num(sf), sp=sp, ea=_num(ea),
                               material=material, species=species)
            p_qty = calc.compute_qty(item)
            p_len = calc.parse_length(length)
            p_key = calc.item_key_of(item)
            if not (_same_qty(p_qty, j_qty) and _same_len(p_len, j_len) and p_key == j_key):
                mismatches.append((c, f"py=({p_qty},{p_len},{p_key!r}) java=({j_qty},{j_len},{j_key!r})"))
        self.assertEqual(mismatches[:15], [], f"{len(mismatches)} of {len(cases)} cases differ")


class StrictLengthQuirks(unittest.TestCase):
    """Runs without Java: the Python port rejects what Excel's VALUE() rejects."""

    def test_strict_length_quirks(self):
        for text in JAVA_ONLY_QUIRKS | {"1_0", "abc", "12 abc"}:
            self.assertIsNone(calc.parse_length(text), text)
        self.assertEqual(calc.parse_length("1e2"), 100.0)


def _is_windows():
    import os
    return os.name == "nt"


def _num(s):
    return None if s == "" else float(s)


def _same_qty(py, java):
    return (py is None and java == "null") or (py is not None and java != "null" and py == int(java))


def _same_len(py, java):
    if py is None or java == "null":
        return py is None and java == "null"
    j = float(java)
    if math.isnan(py) or math.isnan(j):
        return math.isnan(py) and math.isnan(j)
    return py == j


if __name__ == "__main__":
    unittest.main()
