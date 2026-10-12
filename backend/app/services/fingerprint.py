import re
import hashlib

class FingerprintService:
    UUID_PATTERN = re.compile(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', re.I)
    HEX_PATTERN = re.compile(r'0x[a-f0-9]+', re.I)
    ID_PATTERN = re.compile(r'\b[a-f0-9]{16,64}\b', re.I)
    IP_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
    DIGIT_PATTERN = re.compile(r'\d+')
    WHITESPACE_PATTERN = re.compile(r'\s+')

    @classmethod
    def generate(cls, message: str) -> str:
        if not message:
            return hashlib.sha256(b"").hexdigest()

        # Normalize the message template
        norm = cls.UUID_PATTERN.sub("<UUID>", message)
        norm = cls.HEX_PATTERN.sub("<HEX>", norm)
        norm = cls.ID_PATTERN.sub("<ID>", norm)
        norm = cls.IP_PATTERN.sub("<IP>", norm)
        norm = cls.DIGIT_PATTERN.sub("<NUM>", norm)
        norm = cls.WHITESPACE_PATTERN.sub(" ", norm).strip().lower()

        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

fingerprint_service = FingerprintService()
