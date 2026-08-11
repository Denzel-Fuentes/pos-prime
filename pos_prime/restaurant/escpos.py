# Copyright (c) 2026, Ravindu Gajanayaka
# Licensed under GPLv3. See license.txt

"""Pure ESC/POS byte-building — no socket I/O, no Frappe/DB dependency.

EscposBuilder accumulates command + text bytes for one kitchen ticket and
returns them as a single bytes object via build(). Being pure makes it
testable without a real printer: build() output can be asserted against or
dumped to a file and inspected. pos_prime/restaurant/printing.py owns the
actual socket connection and the ticket layout (destination grouping, combo
grouping); this module only knows how to encode text and emit commands.

Code-table numbering is not part of the ESC/POS standard itself — vendors
disagree, especially on cheap thermal clones — so DEFAULT_CODEPAGE_IDS is a
best-effort default (Epson's own numbering) and Restaurant Printer.
escpos_codepage_id always overrides it when set.
"""

import re

_ESC = b"\x1b"
_GS = b"\x1d"

# Escapes understood by raw() — the same ones a Print Format's Raw Commands
# field conventionally uses, so a layout typed in the Desk can emit control
# bytes without needing them to survive the DB as literal control characters.
_RAW_ESCAPE_RE = re.compile(r"\\x([0-9a-fA-F]{2})|\\([nrt\\])")
_RAW_SIMPLE = {"n": b"\n", "r": b"\r", "t": b"\t", "\\": b"\\"}

DEFAULT_CODEPAGE_IDS = {
	"CP437": 0,
	"CP850": 2,
	"CP858": 19,
	"CP1252": 16,
	# UTF-8: no standard ESC/POS code-table id — text is encoded as UTF-8
	# bytes directly and no codepage-select command is sent. Only correct
	# on printers that advertise native UTF-8 support.
	"UTF-8": None,
}

_PYTHON_ENCODINGS = {
	"CP437": "cp437",
	"CP850": "cp850",
	"CP858": "cp858",
	"CP1252": "cp1252",
	"UTF-8": "utf-8",
}

_ALIGN_CODES = {"left": 0, "center": 1, "right": 2}


class EscposBuilder:
	"""Chainable ESC/POS command buffer for one ticket.

	>>> EscposBuilder("CP850").header("MESA").text("1x Milanesa").cut().build()
	"""

	def __init__(self, codepage="CP850", codepage_id_override=None, chars_per_line=32):
		self.codepage = codepage if codepage in _PYTHON_ENCODINGS else "CP437"
		self.encoding = _PYTHON_ENCODINGS[self.codepage]
		self.chars_per_line = chars_per_line or 32
		self._buf = bytearray()
		self._buf += _ESC + b"@"  # initialize printer

		cp_id = (
			codepage_id_override
			if codepage_id_override is not None
			else DEFAULT_CODEPAGE_IDS.get(self.codepage)
		)
		if cp_id is not None:
			self._buf += _ESC + b"t" + bytes([cp_id & 0xFF])

	def _encode(self, value):
		return str(value).encode(self.encoding, errors="replace")

	def text(self, value=""):
		"""One line of plain text, newline-terminated."""
		self._buf += self._encode(value)
		self._buf += b"\n"
		return self

	def raw(self, value):
		"""Append already-laid-out ticket text, as produced by a Print
		Format's Raw Commands. Real control characters (what the template
		helpers emit) pass through the codepage encoding untouched since
		they're all ASCII; typed-out `\\x1b`-style escapes are decoded here
		so both spellings work in a hand-written template."""
		text = str(value)
		pos = 0
		for match in _RAW_ESCAPE_RE.finditer(text):
			self._buf += self._encode(text[pos : match.start()])
			if match.group(1) is not None:
				self._buf += bytes([int(match.group(1), 16)])
			else:
				self._buf += _RAW_SIMPLE[match.group(2)]
			pos = match.end()
		self._buf += self._encode(text[pos:])
		return self

	def bold(self, value):
		self._buf += _ESC + b"E" + b"\x01"
		self._buf += self._encode(value)
		self._buf += b"\n"
		self._buf += _ESC + b"E" + b"\x00"
		return self

	def header(self, value):
		"""Bold, double-width/height line — used for destination banners
		(MESA / PARA LLEVAR) so they're readable across a kitchen pass."""
		self._buf += _GS + b"!" + b"\x11"
		self._buf += _ESC + b"E" + b"\x01"
		self._buf += self._encode(value)
		self._buf += b"\n"
		self._buf += _ESC + b"E" + b"\x00"
		self._buf += _GS + b"!" + b"\x00"
		return self

	def align(self, where):
		if where not in _ALIGN_CODES:
			raise ValueError(f"Unknown alignment: {where!r}")
		self._buf += _ESC + b"a" + bytes([_ALIGN_CODES[where]])
		return self

	def divider(self, char="-"):
		self.text(char * self.chars_per_line)
		return self

	def feed(self, lines=1):
		self._buf += b"\n" * max(0, lines)
		return self

	def cut(self, partial=True):
		self._buf += _GS + b"V" + bytes([1 if partial else 0])
		return self

	def pulse_drawer(self):
		"""Standard pin-2 pulse (m=0), ~50ms on / ~500ms off."""
		self._buf += _ESC + b"p" + bytes([0, 25, 250])
		return self

	def build(self):
		return bytes(self._buf)
