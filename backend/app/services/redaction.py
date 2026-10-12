import re
from typing import Tuple

class RedactionService:
    # Pattern for Bearer tokens
    BEARER_PATTERN = re.compile(r'(?i)bearer\s+([a-zA-Z0-9_\-\.]{15,})')
    
    # Pattern for API keys and secrets in key=value or json format
    SECRET_KEY_VALUE_PATTERN = re.compile(
        r'(?i)(api[_-]?key|secret|password|passwd|auth[_-]?token|access[_-]?token|client[_-]?secret)\s*[:=]\s*["\']?([^"\'\s,;]{4,})["\']?'
    )

    # Pattern for Credit Card / PAN numbers (13 to 19 digits with optional spaces or dashes)
    CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,19}\b')

    # Pattern for Emails
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')

    # Pattern for IPv4 addresses (optional)
    IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

    def __init__(self, mask_ips: bool = False):
        self.mask_ips = mask_ips

    def redact(self, text: str) -> Tuple[str, bool]:
        if not text:
            return text, False

        original_text = text
        redacted = False

        # 1. Redact Bearer tokens
        if self.BEARER_PATTERN.search(text):
            text = self.BEARER_PATTERN.sub(r'Bearer [REDACTED_TOKEN]', text)
            redacted = True

        # 2. Redact key-value / JSON credentials
        def replace_kv(match):
            key = match.group(1)
            return f'{key}=[REDACTED_SECRET]'
        
        if self.SECRET_KEY_VALUE_PATTERN.search(text):
            text = self.SECRET_KEY_VALUE_PATTERN.sub(replace_kv, text)
            redacted = True

        # 3. Redact Credit Card / PAN like numbers
        if self.CREDIT_CARD_PATTERN.search(text):
            # Check length to avoid masking short pure integers like ports
            def mask_cc(match):
                digits = re.sub(r'\D', '', match.group(0))
                if 13 <= len(digits) <= 19:
                    return '[REDACTED_CARD]'
                return match.group(0)
            text = self.CREDIT_CARD_PATTERN.sub(mask_cc, text)
            if text != original_text:
                redacted = True

        # 4. Redact Emails
        if self.EMAIL_PATTERN.search(text):
            text = self.EMAIL_PATTERN.sub('[REDACTED_EMAIL]', text)
            redacted = True

        # 5. Redact IPs if configured
        if self.mask_ips and self.IP_PATTERN.search(text):
            text = self.IP_PATTERN.sub('[REDACTED_IP]', text)
            redacted = True

        return text, redacted or (text != original_text)

redaction_service = RedactionService()
