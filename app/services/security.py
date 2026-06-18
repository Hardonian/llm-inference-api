"""Security service for threat detection, audit logging, and security monitoring."""
import os
import json
import time
import hashlib
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
import re

logger = logging.getLogger("security_svc")

AUDIT_LOG_FILE = "/home/scott/ai-lab/security/audit.log"
THREAT_DB_FILE = "/home/scott/ai-lab/security/threats.json"
BLOCKED_IPS_FILE = "/home/scott/ai-lab/security/blocked_ips.json"

# Threat detection patterns
THREAT_PATTERNS = {
    "prompt_injection": [
        r"ignore\s+(previous|prior|above)\s+(instructions|prompts|system)",
        r"system\s+prompt",
        r"you\s+are\s+now",
        r"forget\s+(everything|all|previous)",
        r"new\s+instructions",
        r"override\s+(safety|guidelines|filters)",
        r"bypass\s+(filter|safety|moderation)",
        r"roleplay\s+as",
        r"pretend\s+to\s+be",
        r"act\s+as\s+(if|though)",
        r"hypothetically",
    ],
    "model_extraction": [
        r"what\s+is\s+your\s+(system\s+)?prompt",
        r"repeat\s+the\s+(system\s+)?prompt",
        r"show\s+me\s+the\s+(system\s+)?prompt",
        r"output\s+your\s+(instructions|system\s+prompt)",
        r"reveal\s+(your\s+)?(prompt|instructions)",
        r"what\s+were\s+you\s+told",
        r"your\s+initial\s+instructions",
    ],
    "data_exfiltration": [
        r"send\s+(data|information)\s+to",
        r"upload\s+to\s+(external|remote)",
        r"exfiltrat",
        r"steal\s+(data|information|credentials)",
        r"leak\s+(sensitive|private|confidential)",
        r"exfiltrate",
        r"expose\s+(api|secret|key|token)",
    ],
    "reconnaissance": [
        r"what\s+(model|version|architecture)\s+are\s+you",
        r"how\s+were\s+you\s+trained",
        r"what\s+is\s+your\s+(training\s+)?data",
        r"parameters\s+count",
        r"context\s+window",
        r"knowledge\s+cutoff",
    ],
    "jailbreak": [
        r"DAN\s+mode",
        r"developer\s+mode",
        r"ignore\s+(all\s+)?restrictions",
        r"unrestricted",
        r"no\s+filters",
        r"without\s+limitations",
    ],
}

SEVERITY_SCORES = {
    "prompt_injection": 9,
    "model_extraction": 8,
    "data_exfiltration": 10,
    "reconnaissance": 5,
    "jailbreak": 8,
}


class SecurityService:
    def __init__(self):
        self.threats: List[Dict[str, Any]] = []
        self.blocked_ips: set = set()
        self._init_dirs()
        self._load_data()

    def _init_dirs(self):
        Path("/home/scott/ai-lab/security").mkdir(parents=True, exist_ok=True)
        Path(AUDIT_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    def _load_data(self):
        """Load persisted threat data."""
        try:
            if Path(THREAT_DB_FILE).exists():
                with open(THREAT_DB_FILE) as f:
                    self.threats = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load threats: {e}")
            self.threats = []

        try:
            if Path(BLOCKED_IPS_FILE).exists():
                with open(BLOCKED_IPS_FILE) as f:
                    self.blocked_ips = set(json.load(f))
        except Exception as e:
            logger.error(f"Failed to load blocked IPs: {e}")
            self.blocked_ips = set()

    def _save_data(self):
        """Persist threat data."""
        try:
            with open(THREAT_DB_FILE, "w") as f:
                json.dump(self.threats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save threats: {e}")

        try:
            with open(BLOCKED_IPS_FILE, "w") as f:
                json.dump(list(self.blocked_ips), f)
        except Exception as e:
            logger.error(f"Failed to save blocked IPs: {e}")

    # ========================================
    # Threat Detection
    # ========================================
    def scan_text(self, text: str, source: str = "unknown") -> List[Dict[str, Any]]:
        """Scan text for threat patterns."""
        threats = []
        lower_text = text.lower()

        for category, patterns in THREAT_PATTERNS.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, lower_text, re.IGNORECASE))
                for match in matches:
                    threat = {
                        "id": f"threat_{int(time.time() * 1000)}_{len(self.threats)}",
                        "category": category,
                        "pattern": pattern,
                        "match": match.group(),
                        "position": match.span(),
                        "severity": SEVERITY_SCORES.get(category, 5),
                        "timestamp": int(time.time()),
                        "source": source,
                        "context": lower_text[max(0, match.start()-50):match.end()+50],
                    }
                    threats.append(threat)
                    self.threats.append(threat)

        if threats:
            self._save_data()
            logger.warning(f"Detected {len(threats)} threats from {source}")

        return threats

    def scan_prompt(self, prompt: str, source: str = "prompt-input") -> List[Dict[str, Any]]:
        """Scan a prompt for threats."""
        return self.scan_text(prompt, source)

    def get_threats(self, limit: int = 100, since: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent threats."""
        filtered = self.threats
        if since:
            filtered = [t for t in filtered if t["timestamp"] > since]
        return sorted(filtered, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_threat_stats(self) -> Dict[str, Any]:
        """Get threat statistics."""
        now = int(time.time())
        last_hour = now - 3600
        last_day = now - 86400

        recent = [t for t in self.threats if t["timestamp"] > last_hour]
        daily = [t for t in self.threats if t["timestamp"] > last_day]

        by_category = {}
        for t in self.threats:
            by_category[t["category"]] = by_category.get(t["category"], 0) + 1

        return {
            "total": len(self.threats),
            "last_hour": len(recent),
            "last_24h": len(daily),
            "by_category": by_category,
            "blocked_ips": list(self.blocked_ips),
        }

    # ========================================
    # Audit Logging
    # ========================================
    def log_audit(self, entry: Dict[str, Any]):
        """Log an audit entry."""
        audit_entry = {
            "timestamp": int(time.time()),
            "request_id": entry.get("request_id", ""),
            "method": entry.get("method", ""),
            "path": entry.get("path", ""),
            "status": entry.get("status", 0),
            "duration_ms": entry.get("duration_ms", 0),
            "client_ip": entry.get("client_ip", ""),
            "user": entry.get("user", "anonymous"),
            "user_agent": entry.get("user_agent", "")[:100],
        }

        # Write to audit log file
        log_line = json.dumps(audit_entry)
        try:
            with open(AUDIT_LOG_FILE, "a") as f:
                f.write(log_line + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def get_audit_logs(self, limit: int = 100, since: Optional[int] = None, level: Optional[str] = None) -> List[Dict]:
        """Get audit logs."""
        logs = []
        try:
            with open(AUDIT_LOG_FILE, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if since and entry["timestamp"] < since:
                            continue
                        logs.append(entry)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass

        if level:
            if level == "error":
                logs = [l for l in logs if l["status"] >= 500]
            elif level == "warn":
                logs = [l for l in logs if 400 <= l["status"] < 500]

        return sorted(logs, key=lambda x: x["timestamp"], reverse=True)[:limit]

    # ========================================
    # IP Blocking
    # ========================================
    def block_ip(self, ip: str, reason: str = "Security threat"):
        """Block an IP address."""
        self.blocked_ips.add(ip)
        self._save_blocked_ips()
        logger.warning(f"Blocked IP {ip}: {reason}")

    def unblock_ip(self, ip: str):
        """Unblock an IP address."""
        self.blocked_ips.discard(ip)
        self._save_blocked_ips()
        logger.info(f"Unblocked IP {ip}")

    def is_blocked(self, ip: str) -> bool:
        return ip in self.blocked_ips

    def _save_blocked_ips(self):
        try:
            with open(BLOCKED_IPS_FILE, "w") as f:
                json.dump(list(self.blocked_ips), f)
        except Exception as e:
            logger.error(f"Failed to save blocked IPs: {e}")

    # ========================================
    # Encryption Utilities
    # ========================================
    @staticmethod
    def hash_data(data: str) -> str:
        """Hash sensitive data for storage."""
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        return hashlib.sha256(f"{time.time()}{os.urandom(16).hex()}".encode()).hexdigest()[:32]

    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature."""
        expected = hashlib.sha256(f"{secret}{payload}".encode()).hexdigest()
        return hashlib.compare_digest(expected, signature)


security_service = SecurityService()