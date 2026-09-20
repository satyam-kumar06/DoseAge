"""Hindi and English reminder lines, and Polly synthesis with caching.

Hindi is written in Devanagari for Polly (Aditi/Kajal read it correctly) and
mirrored in Roman Hindi for the on-screen caption, because many caregivers
read Roman faster than Devanagari.
"""
import hashlib
from typing import Any, Dict, Optional

from . import config

SLOT_HI = {"MORNING": "सुबह", "AFTERNOON": "दोपहर", "NIGHT": "रात"}
SLOT_EN = {"MORNING": "morning", "AFTERNOON": "afternoon", "NIGHT": "night"}
SLOT_ROMAN = {"MORNING": "subah", "AFTERNOON": "dopahar", "NIGHT": "raat"}
FOOD_HI = {"before": "खाने से पहले", "after": "खाने के बाद", "any": ""}
FOOD_EN = {"before": "before food", "after": "after food", "any": ""}


# Said out loud to the same person three times a day, every day. An identical
# sentence becomes wallpaper within a week, so the opening rotates on the day
# of the month: predictable enough to be familiar, varied enough to be heard.
_OPENERS_HI = [
    "{who}{time} की दवा का समय हो गया है।",
    "{who}अब {time} की दवा ले लीजिए।",
    "{who}{time} हो गई, दवा का समय है।",
    "{who}दवा का समय, {time} वाली।",
]
_OPENERS_EN = [
    "{who}it is time for your {time} medicine.",
    "{who}your {time} medicine is due now.",
    "{who}time for the {time} tablets.",
    "{who}please take the {time} medicine now.",
]

_FOOD_LINE_HI = {
    "before": "ये खाने से पहले लेनी है।",
    "after": "ये खाने के बाद लेनी है।",
}
_FOOD_LINE_EN = {
    "before": "Take these before food.",
    "after": "Take these after food.",
}

_CLOSERS_HI = ["ले लीजिए।", "धीरे-धीरे, पानी के साथ।", "एक बार देख लीजिए, फिर ले लीजिए।"]
_CLOSERS_EN = ["Please take them now.", "Slowly, with water.", "Check them once, then take them."]


def _variant(seed_len: int, day: Optional[int] = None) -> int:
    """Rotate by day of month, so a line is stable for a whole day."""
    import datetime as _dt

    day = day if day is not None else _dt.date.today().day
    return day % seed_len


def reminder_text(
    slot: str,
    medicines: list,
    parent_name: str = "",
    language: str = "hi",
    day: Optional[int] = None,
) -> Dict[str, str]:
    """The line Polly speaks and the caption shown under it.

    Names each medicine with its count, says whether it goes before or after
    food when every medicine in the slot agrees, and varies its phrasing.
    """
    names = [m.get("brand", "") for m in medicines if m.get("brand")]
    count = sum(int(m.get("count", 1)) for m in medicines) or len(names)

    # a food instruction only if it is the same for the whole slot
    foods = {m.get("food", "any") for m in medicines}
    food = foods.pop() if len(foods) == 1 else "any"

    index = _variant(len(_OPENERS_HI), day)

    if language.startswith("en"):
        who = f"{parent_name}, " if parent_name else ""
        opener = _OPENERS_EN[index].format(who=who, time=SLOT_EN.get(slot, ""))
        body = f"{count} tablet{'s' if count != 1 else ''}: {', '.join(names)}."
        parts = [opener, body]
        if food in _FOOD_LINE_EN:
            parts.append(_FOOD_LINE_EN[food])
        parts.append(_CLOSERS_EN[index % len(_CLOSERS_EN)])
        spoken = " ".join(parts)
        return {"spoken": spoken, "caption": spoken, "language": language}

    who_hi = f"{parent_name} जी, " if parent_name else ""
    opener_hi = _OPENERS_HI[index].format(who=who_hi, time=SLOT_HI.get(slot, ""))
    body_hi = f"{count} गोली: {', '.join(names)}।"
    parts_hi = [opener_hi, body_hi]
    if food in _FOOD_LINE_HI:
        parts_hi.append(_FOOD_LINE_HI[food])
    parts_hi.append(_CLOSERS_HI[index % len(_CLOSERS_HI)])
    spoken = " ".join(parts_hi)

    # Roman Hindi caption, because many caregivers read it faster than Devanagari
    who_ro = f"{parent_name} ji, " if parent_name else ""
    opener_ro = [
        f"{who_ro}{SLOT_ROMAN.get(slot, '')} ki dawa ka samay ho gaya hai.",
        f"{who_ro}ab {SLOT_ROMAN.get(slot, '')} ki dawa le lijiye.",
        f"{who_ro}{SLOT_ROMAN.get(slot, '')} ho gayi, dawa ka samay hai.",
        f"{who_ro}dawa ka samay, {SLOT_ROMAN.get(slot, '')} wali.",
    ][index]
    food_ro = {"before": "Ye khane se pehle leni hai.", "after": "Ye khane ke baad leni hai."}
    closer_ro = ["Le lijiye.", "Dheere-dheere, paani ke saath.", "Ek baar dekh lijiye, phir le lijiye."]
    caption_parts = [opener_ro, f"{count} goli: {', '.join(names)}."]
    if food in food_ro:
        caption_parts.append(food_ro[food])
    caption_parts.append(closer_ro[index % len(closer_ro)])

    return {"spoken": spoken, "caption": " ".join(caption_parts), "language": language}


def praise_text(slot: str, next_slot_time: str = "", language: str = "hi") -> Dict[str, str]:
    if language.startswith("en"):
        line = "Well done! Next medicine at " + (next_slot_time or "the next slot") + "."
        return {"spoken": line, "caption": line, "language": language}
    spoken = "शाबाश! अगली गोली " + (next_slot_time or "अगले समय") + " बजे।"
    caption = "Shabash! Agli goli " + (next_slot_time or "agle samay") + " baje."
    return {"spoken": spoken, "caption": caption, "language": language}


def duplicate_text(salt: str, brands: list, language: str = "hi") -> Dict[str, str]:
    joined_en = " and ".join(brands)
    if language.startswith("en"):
        line = f"{joined_en} both contain {salt}. Ask your doctor before taking both."
        return {"spoken": line, "caption": line, "language": language}
    joined_hi = " और ".join(brands)
    spoken = f"{joined_hi} दोनों में {salt} है। दोनों लेने से पहले डॉक्टर से पूछें।"
    caption = f"{' aur '.join(brands)} dono mein {salt} hai. Dono lene se pehle doctor se poochhein."
    return {"spoken": spoken, "caption": caption, "language": language}


VOICE_BY_LANGUAGE = {"hi": "Aditi", "hi-IN": "Aditi", "en": "Raveena", "en-IN": "Raveena"}


def cache_key(text: str, voice: str) -> str:
    digest = hashlib.sha256(f"{voice}|{text}".encode("utf-8")).hexdigest()[:24]
    return f"voice/{digest}.mp3"


def synthesize(text: str, language: str = "hi") -> Dict[str, Any]:
    """Return {key, url, cached, engine}. Falls back to browser speech
    synthesis when Polly is off, so voice still works with no AWS account."""
    voice = VOICE_BY_LANGUAGE.get(language, "Aditi")
    key = cache_key(text, voice)

    if not config.POLLY_ENABLED:
        return {
            "key": key,
            "url": None,
            "cached": False,
            "engine": "browser",
            "text": text,
            "language": language,
            "voice": voice,
        }

    from botocore.exceptions import ClientError

    from .storage import s3_client

    s3 = s3_client()
    try:  # already generated for this exact line?
        s3.head_object(Bucket=config.BUCKET_NAME, Key=key)
        cached = True
    except ClientError:
        cached = False
        import boto3

        polly = boto3.client("polly", region_name=config.REGION)
        audio = polly.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=voice,
            LanguageCode="hi-IN" if language.startswith("hi") else "en-IN",
        )
        s3.put_object(
            Bucket=config.BUCKET_NAME,
            Key=key,
            Body=audio["AudioStream"].read(),
            ContentType="audio/mpeg",
        )

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": config.BUCKET_NAME, "Key": key},
        ExpiresIn=3600,
    )
    return {
        "key": key,
        "url": url,
        "cached": cached,
        "engine": "polly",
        "text": text,
        "language": language,
        "voice": voice,
    }
