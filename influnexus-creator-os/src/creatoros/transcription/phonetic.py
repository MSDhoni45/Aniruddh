"""Script-independent phonetic keys.

Hinglish is spoken in one language and written in two scripts. Whisper returns
Devanagari while the approved script is Roman, so both are reduced to a rough
consonant skeleton ("critical" and "क्रिटिकल" both become "krtkl") before matching.
"""
from __future__ import annotations

import re
import unicodedata

_DEV = {
    "क": "k", "ख": "k", "ग": "g", "घ": "g", "ङ": "n", "च": "c", "छ": "c", "ज": "j", "झ": "j", "ञ": "n",
    "ट": "t", "ठ": "t", "ड": "d", "ढ": "d", "ण": "n", "त": "t", "थ": "t", "द": "d", "ध": "d", "न": "n",
    "प": "p", "फ": "f", "ब": "b", "भ": "b", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "s", "ष": "s", "स": "s", "ह": "h", "ं": "n", "ँ": "n", "ऩ": "n", "ऱ": "r", "ळ": "l",
    "क़": "k", "ख़": "k", "ग़": "g", "ज़": "j", "ड़": "r", "ढ़": "r", "फ़": "f", "य़": "y",
}
_NUKTA = "़"
_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Split into spoken words. Digits become separate words; combining marks stay attached."""
    text = re.sub(r"(\d+)", r" \1 ", text)
    text = re.sub(r"[^\w\s'’ऀ-ॿ]", " ", text, flags=re.UNICODE)
    return [w for w in text.split() if any(ch.isalnum() or "ऀ" <= ch <= "ॿ" for ch in w)]


def key(word: str) -> str:
    w = unicodedata.normalize("NFC", word.lower())
    if w.isdigit():
        return "_"      # numbers are read aloud differently in Hindi and English, so they match anything
    out = []
    i = 0
    while i < len(w):
        ch = w[i]
        if "ऀ" <= ch <= "ॿ":
            if i + 1 < len(w) and w[i + 1] == _NUKTA:
                out.append("r" if ch in "डढ" else _DEV.get(ch, ""))
                i += 2
                continue
            out.append(_DEV.get(ch, ""))
            i += 1
            continue
        i += 1
        out.append(ch)
    s = "".join(out)
    if not re.search(r"[\u0900-\u097f]", w):          # Roman spelling rules; Devanagari is already phonetic
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        s = s.replace("tch", "ch").replace("ph", "f").replace("ch", "C").replace("sh", "s").replace("ck", "k")
        s = s.replace("q", "k").replace("x", "ks").replace("w", "v").replace("z", "j")
        s = re.sub(r"c(?=[eiy])", "s", s).replace("c", "k").replace("C", "c")
        s = re.sub(r"(?<=[bcdgjkpt])h", "", s)        # aspirates: bh -> b
        s = re.sub(r"[aeiou']", "", s)
    s = re.sub(r"(?<!^)y", "", s)                      # y is a glide/vowel except word-initially
    s = re.sub(r"[^a-z]", "", s)
    s = re.sub(r"(.)\1+", r"\1", s)
    return s or "_"


def keys(words: list[str]) -> list[str]:
    return [key(w) for w in words]
