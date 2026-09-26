# -*- coding: utf-8 -*-
"""
backend/transliteration/romanizer.py
------------------------------------
Rule-based Devanagari to Roman script transliterator with schwa deletion rules,
common word preservation, and English script pass-through.
"""

from __future__ import annotations

import re

import unicodedata

# Independent Vowels
_VOWELS: dict[str, str] = {
    "\u0905": "a",   # अ
    "\u0906": "aa",  # आ
    "\u0907": "i",   # इ
    "\u0908": "ee",  # ई
    "\u0909": "u",   # उ
    "\u090a": "oo",  # ऊ
    "\u090b": "ri",  # ऋ
    "\u090f": "e",   # ए
    "\u0910": "ai",  # ऐ
    "\u0913": "o",   # ओ
    "\u0914": "au",  # औ
}

# Consonants (with default inherent 'a' sound)
_CONSONANTS: dict[str, str] = {
    "\u0915": "k",   # क
    "\u0916": "kh",  # ख
    "\u0917": "g",   # ग
    "\u0918": "gh",  # घ
    "\u0919": "n",   # ङ
    "\u091a": "ch",  # च
    "\u091b": "chh", # छ
    "\u091c": "j",   # ज
    "\u091d": "jh",  # झ
    "\u091e": "n",   # ञ
    "\u091f": "t",   # ट
    "\u0920": "th",  # ठ
    "\u0921": "d",   # ड
    "\u0922": "dh",  # ढ
    "\u0923": "n",   # ण
    "\u0924": "t",   # त
    "\u0925": "th",  # थ
    "\u0926": "d",   # द
    "\u0927": "dh",  # ध
    "\u0928": "n",   # न
    "\u092a": "p",   # प
    "\u092b": "ph",  # फ
    "\u092c": "b",   # ब
    "\u092d": "bh",  # भ
    "\u092e": "m",   # म
    "\u092f": "y",   # य
    "\u0930": "r",   # र
    "\u0932": "l",   # ल
    "\u0935": "v",   # व
    "\u0936": "sh",  # श
    "\u0937": "sh",  # ष
    "\u0938": "s",   # स
    "\u0939": "h",   # ह
    "\u0958": "q",   # क़
    "\u0959": "kh",  # ख़
    "\u095a": "gh",  # ग़
    "\u095b": "z",   # ज़
    "\u095c": "r",   # ड़
    "\u095d": "rh",  # ढ़
    "\u095e": "f",   # फ़
}

# Vowel Signs (Matras)
_MATRAS: dict[str, str] = {
    "\u093e": "aa",  # ा
    "\u093f": "i",   # ि
    "\u0940": "ee",  # ी
    "\u0941": "u",   # ु
    "\u0942": "oo",  # ू
    "\u0943": "ri",  # ृ
    "\u0947": "e",   # े
    "\u0948": "ai",  # ै
    "\u094b": "o",   # ो
    "\u094c": "au",  # ौ
    "\u0945": "e",   # ॅ
    "\u0949": "o",   # ॉ
}

# Common High-Frequency Words (mapped for natural Hinglish spelling)
_WORD_MAP: dict[str, str] = {
    "मैं": "mai",
    "में": "mein",
    "मे": "me",
    "मुझे": "mujhe",
    "मेरा": "mera",
    "मेरी": "meri",
    "मेरे": "mere",
    "नाम": "naam",
    "युवराज": "yuvraj",
    "तुम": "tum",
    "आप": "aap",
    "आपका": "aapka",
    "आपकी": "aapki",
    "हम": "hum",
    "हमारा": "hamara",
    "कल": "kal",
    "आज": "aaj",
    "अभी": "abhi",
    "फिर": "phir",
    "यहाँ": "yahan",
    "वहाँ": "wahan",
    "नहीं": "nahi",
    "नही": "nahi",
    "न": "na",
    "हाँ": "haan",
    "हां": "haan",
    "आऊंगा": "aunga",
    "आऊंगी": "aungi",
    "आएगा": "aayega",
    "आना": "aana",
    "आता": "aata",
    "आती": "aati",
    "जाऊंगा": "jaunga",
    "जाएगा": "jayega",
    "जाना": "jaana",
    "ऑफिस": "office",
    "मीटिंग": "meeting",
    "काम": "kaam",
    "घर": "ghar",
    "स्कूल": "school",
    "कॉलेज": "college",
    "बाजार": "bazaar",
    "के": "ke",
    "की": "ki",
    "का": "ka",
    "को": "ko",
    "से": "se",
    "पर": "par",
    "लिए": "liye",
    "और": "aur",
    "या": "ya",
    "भी": "bhi",
    "तो": "to",
    "लेकिन": "lekin",
    "क्योंकि": "kyunki",
    "एक": "ek",
    "दो": "two",
    "दिन": "din",
    "देंगे": "denge",
    "चाहिए": "chahiye",
    "बताओ": "batao",
    "क्या": "kya",
    "कैसे": "kaise",
    "कहा": "kaha",
    "कहां": "kahan",
    "कब": "kab",
    "है": "hai",
    "हैं": "hain",
    "था": "tha",
    "थी": "thi",
    "थे": "the",
    "होगा": "hoga",
    "होगी": "hogi",
    "करना": "karna",
    "करेंगे": "karenge",
    "करूंगा": "karunga",
    "करूंगी": "karungi",
    "कर": "kar",
    "करने": "karne",
    "लगेंगे": "lagenge",
    "कितने": "kitne",
    "बजे": "baje",
    "सर": "Sir",
    "प्रोजेक्ट": "project",
    "कंप्लीट": "complete",
    "डेज": "days",
    "टू": "two",
}

_ARTIFACTS: dict[str, str] = {
    "aaunga": "aunga",
    "nahiin": "nahi",
    "nahii": "nahi",
    "meing": "mein",
    "officee": "office",
    "meetingg": "meeting",
    "haii": "hai",
    "hainn": "hain",
}


def is_devanagari(char: str) -> bool:
    """Return True if character is within Devanagari Unicode block."""
    return "\u0900" <= char <= "\u097f"


def transliterate_word(word: str) -> str:
    """
    Transliterate a single Devanagari word into Roman script.
    Implements character mapping and schwa-deletion heuristics for word-final consonants.
    """
    word = unicodedata.normalize("NFC", word)

    if not any(is_devanagari(c) for c in word):
        return word

    # Clean punctuation surrounding word
    match = re.match(r"^(\W*)([\u0900-\u097f]+)(\W*)$", word)
    if not match:
        prefix, core, suffix = "", word, ""
    else:
        prefix, core, suffix = match.group(1), match.group(2), match.group(3)

    if core in _WORD_MAP:
        return prefix + _WORD_MAP[core] + suffix

    chars = list(core)
    n = len(chars)
    out: list[str] = []
    i = 0

    while i < n:
        ch = chars[i]

        if not is_devanagari(ch):
            out.append(ch)
            i += 1
            continue

        if ch in _VOWELS:
            out.append(_VOWELS[ch])
            i += 1
            continue

        if ch in _CONSONANTS:
            consonant = _CONSONANTS[ch]
            nxt = chars[i + 1] if i + 1 < n else ""

            if nxt == "\u094d":  # virama (्) -> half consonant, no vowel
                out.append(consonant)
                i += 2
            elif nxt in _MATRAS:
                out.append(consonant + _MATRAS[nxt])
                i += 2
            elif nxt in ("\u0902", "\u0901"):  # anusvara / chandrabindu
                out.append(consonant + "n")
                i += 2
            elif nxt == "\u093c":  # nukta
                out.append(consonant)
                i += 2
            else:
                # Schwa deletion rule: Do not append 'a' if at the end of word
                # unless the word is a single consonant.
                if i + 1 == n and n > 1:
                    out.append(consonant)
                else:
                    out.append(consonant + "a")
                i += 1
            continue

        if ch in ("\u0902", "\u0901"):
            out.append("n")
        elif ch == "\u0903":
            out.append("h")
        elif ch == "\u0964":  # Devanagari danda -> full stop
            out.append(".")
        elif ch in ("\u094d", "\u093c"):
            pass
        else:
            # Skip unmapped standalone Devanagari diacritics to avoid raw Unicode leaks
            pass

        i += 1

    res = "".join(out)
    # Strip any remaining untransliterated Devanagari characters
    res = re.sub(r"[\u0900-\u097f]+", "", res)

    for bad, good in _ARTIFACTS.items():
        res = res.replace(bad, good)

    return prefix + res + suffix


def transliterate_text(text: str, mode: str = "roman") -> str:
    """
    Convert text containing Devanagari or mixed script to Roman Hinglish.
    Preserves English words as English.
    """
    text = text.strip()
    if not text or mode == "raw":
        return text

    # Split into words keeping whitespace intact
    words = re.split(r"(\s+)", text)
    result: list[str] = []

    for item in words:
        if item.isspace():
            result.append(item)
        else:
            result.append(transliterate_word(item))

    out_text = "".join(result)
    out_text = re.sub(r"\s+", " ", out_text).strip()
    return out_text
