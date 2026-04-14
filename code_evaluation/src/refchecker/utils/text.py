"""Text normalization utilities for reference checking."""

import re
import unicodedata

# LaTeX commands that wrap content in braces
_LATEX_COMMANDS = re.compile(
    r"\\(?:textbf|textit|emph|textrm|textsc|textsf|texttt"
    r"|mathrm|mathbf|mathit)\{([^}]*)\}"
)

# LaTeX accent patterns: {\"o}, {\v{c}}, \'{e}, etc.
_LATEX_ACCENT_BRACED = re.compile(r"\{\\[`'^\"~=.vcuHtdbrk]\{?(\w)\}?\}")
_LATEX_ACCENT_BARE = re.compile(r"\\[`'^\"~=.vcuHtdbrk]\{(\w)\}")
_LATEX_ACCENT_SIMPLE = re.compile(r"\\[`'^\"~=.vcuHtdbrk](\w)")

_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
_DOI_INLINE = re.compile(r"\bdoi:\s*\S+", re.IGNORECASE)
_MULTI_SPACE = re.compile(r"\s+")

# Common academic abbreviations (lowercase key -> expansion)
_ABBREVIATIONS: dict[str, str] = {
    "trans.": "transactions",
    "conf.": "conference",
    "int.": "international",
    "proc.": "proceedings",
    "j.": "journal",
    "symp.": "symposium",
    "assoc.": "association",
    "comput.": "computing",
    "sci.": "science",
    "eng.": "engineering",
    "technol.": "technology",
    "lett.": "letters",
    "rev.": "review",
    "res.": "research",
    "syst.": "systems",
    "appl.": "applied",
    "natl.": "national",
    "eur.": "european",
    "vol.": "volume",
    "no.": "number",
    "dept.": "department",
    "univ.": "university",
    "inst.": "institute",
    "lab.": "laboratory",
    "annu.": "annual",
    "adv.": "advances",
    "commun.": "communications",
    "inf.": "information",
    "intell.": "intelligence",
    "artif.": "artificial",
    "mach.": "machine",
    "learn.": "learning",
    "stat.": "statistics",
    "optim.": "optimization",
    "netw.": "networks",
    "autom.": "automation",
    "rob.": "robotics",
    "med.": "medicine",
    "biol.": "biology",
    "chem.": "chemistry",
    "phys.": "physics",
    "math.": "mathematics",
    "electr.": "electrical",
    "electron.": "electronic",
    "softw.": "software",
    "program.": "programming",
    "lang.": "language",
    "ling.": "linguistics",
    "acoust.": "acoustics",
    "signal": "signal",
    "process.": "processing",
    "vis.": "vision",
    "graph.": "graphics",
    "interact.": "interaction",
    "multimed.": "multimedia",
}

# Smart quotes and special dash replacements
_SMART_QUOTES = str.maketrans({
    "\u2018": "'", "\u2019": "'",  # single smart quotes
    "\u201c": '"', "\u201d": '"',  # double smart quotes
    "\u2013": "-", "\u2014": "-",  # en/em dashes
})

_APOSTROPHE_VARIANTS = str.maketrans({
    "\u2019": "'",  # right single quotation mark
    "\u02bc": "'",  # modifier letter apostrophe
    "\u2018": "'",  # left single quotation mark
    "\u0060": "'",  # grave accent
    "\u00b4": "'",  # acute accent
})


def normalize_apostrophes(text: str) -> str:
    """Normalize all apostrophe variants to ASCII."""
    return text.translate(_APOSTROPHE_VARIANTS)


def strip_latex_commands(text: str) -> str:
    """Remove LaTeX commands but keep the content inside braces.

    Handles \\textbf{}, \\emph{}, etc., nested braces,
    and LaTeX accents like {\\\"o} -> o.
    """
    # Strip accent patterns first
    result = _LATEX_ACCENT_BRACED.sub(r"\1", text)
    result = _LATEX_ACCENT_BARE.sub(r"\1", result)
    result = _LATEX_ACCENT_SIMPLE.sub(r"\1", result)
    # Iteratively strip commands (handles nesting)
    prev = None
    while prev != result:
        prev = result
        result = _LATEX_COMMANDS.sub(r"\1", result)
    # Remove stray backslashes from remaining LaTeX
    result = re.sub(r"\\(?=[a-zA-Z])", "", result)
    # Remove leftover empty braces
    result = result.replace("{}", "")
    return result


def expand_abbreviations(text: str) -> str:
    """Expand common academic abbreviations."""
    words = text.split()
    expanded = []
    for word in words:
        lower = word.lower()
        if lower in _ABBREVIATIONS:
            expanded.append(_ABBREVIATIONS[lower])
        else:
            expanded.append(word)
    return " ".join(expanded)


def normalize_text(text: str) -> str:
    """Normalize text for comparison.

    Applies: NFKD decomposition, diacritic removal, smart-quote
    normalization, non-word char removal (keeps apostrophes),
    whitespace normalization, and lowercasing.
    """
    # Translate smart quotes / dashes first
    text = text.translate(_SMART_QUOTES)
    # NFKD decomposition and strip combining marks (diacritics)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Remove non-word chars except apostrophes and whitespace
    text = re.sub(r"[^\w\s']", " ", text)
    # Normalize whitespace and lowercase
    text = _MULTI_SPACE.sub(" ", text).strip().lower()
    return text


def clean_title(title: str) -> str:
    """Clean a reference title: strip LaTeX, remove URLs/DOIs, normalize."""
    title = strip_latex_commands(title)
    title = _URL_PATTERN.sub("", title)
    title = _DOI_INLINE.sub("", title)
    title = _MULTI_SPACE.sub(" ", title).strip()
    return title


def clean_title_basic(title: str) -> str:
    """Minimal title cleaning: strip and normalize whitespace."""
    return _MULTI_SPACE.sub(" ", title.strip())


def clean_author_name(name: str) -> str:
    """Clean an individual author name.

    Strips LaTeX, normalizes whitespace, removes trailing
    punctuation and numeric suffixes.
    """
    name = strip_latex_commands(name)
    name = _MULTI_SPACE.sub(" ", name).strip()
    # Remove trailing punctuation artifacts
    name = name.strip(".,;:")
    # Remove numeric suffixes like "1" or "*1"
    name = re.sub(r"[\s*]*\d+$", "", name).strip()
    return name
