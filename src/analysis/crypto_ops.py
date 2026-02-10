"""
Cryptographic Operations

Encryption, decryption, key management, and secure secret storage.
Uses Fernet (AES-128-CBC) from the cryptography library, with fallback
to base64 obfuscation if cryptography is not installed.
"""

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class CryptoOps:
    """Encryption, signing, and secret management."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent.parent.parent / "data" / "pltm_mcp.db"
        self._fernet = None
        self._ensure_tables()
    
    def _ensure_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                encrypted INTEGER DEFAULT 1,
                category TEXT DEFAULT 'general',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crypto_keys (
                key_id TEXT PRIMARY KEY,
                key_type TEXT NOT NULL,
                key_data TEXT NOT NULL,
                created_at REAL NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.commit()
        conn.close()
    
    def _get_fernet(self, password: Optional[str] = None):
        """Get or create Fernet cipher"""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            if password:
                # Derive key from password
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b"pltm_salt_v1",  # Fixed salt for reproducibility
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            else:
                # Use or create a stored key
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.execute("SELECT key_data FROM crypto_keys WHERE key_id = 'default_fernet'")
                row = cursor.fetchone()
                if row:
                    key = row[0].encode()
                else:
                    key = Fernet.generate_key()
                    conn.execute(
                        "INSERT INTO crypto_keys (key_id, key_type, key_data, created_at) VALUES (?,?,?,?)",
                        ("default_fernet", "fernet", key.decode(), time.time())
                    )
                    conn.commit()
                conn.close()
            
            return Fernet(key)
        except ImportError:
            return None
    
    def encrypt(self, data: str, password: Optional[str] = None) -> Dict:
        """Encrypt data. Uses Fernet if available, base64 fallback."""
        fernet = self._get_fernet(password)
        
        if fernet:
            encrypted = fernet.encrypt(data.encode()).decode()
            return {"ok": True, "encrypted": encrypted, "method": "fernet_aes128"}
        else:
            # Fallback: base64 + XOR with key hash (not cryptographically secure)
            key_bytes = hashlib.sha256((password or "pltm_default").encode()).digest()
            data_bytes = data.encode()
            xored = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data_bytes))
            encoded = base64.b64encode(xored).decode()
            return {"ok": True, "encrypted": encoded, "method": "base64_xor",
                    "warning": "Install 'cryptography' package for real encryption"}
    
    def decrypt(self, encrypted_data: str, password: Optional[str] = None,
                method: str = "fernet_aes128") -> Dict:
        """Decrypt data."""
        if method == "fernet_aes128":
            fernet = self._get_fernet(password)
            if not fernet:
                return {"ok": False, "err": "cryptography package not installed"}
            try:
                decrypted = fernet.decrypt(encrypted_data.encode()).decode()
                return {"ok": True, "decrypted": decrypted}
            except Exception as e:
                return {"ok": False, "err": f"Decryption failed: {str(e)[:100]}"}
        elif method == "base64_xor":
            try:
                key_bytes = hashlib.sha256((password or "pltm_default").encode()).digest()
                xored = base64.b64decode(encrypted_data)
                data_bytes = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(xored))
                return {"ok": True, "decrypted": data_bytes.decode()}
            except Exception as e:
                return {"ok": False, "err": f"Decryption failed: {str(e)[:100]}"}
        else:
            return {"ok": False, "err": f"Unknown method: {method}"}
    
    def store_secret(self, name: str, value: str, category: str = "general",
                     password: Optional[str] = None) -> Dict:
        """Store a secret (encrypted)"""
        result = self.encrypt(value, password)
        if not result["ok"]:
            return result
        
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT OR REPLACE INTO secrets (name, value, encrypted, category, created_at, updated_at, metadata) VALUES (?,?,?,?,?,?,?)",
            (name, result["encrypted"], 1, category, now, now,
             json.dumps({"method": result["method"]}))
        )
        conn.commit()
        conn.close()
        
        return {"ok": True, "name": name, "method": result["method"]}
    
    def get_secret(self, name: str, password: Optional[str] = None) -> Dict:
        """Retrieve and decrypt a secret"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT value, metadata FROM secrets WHERE name = ?", (name,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {"ok": False, "err": f"Secret '{name}' not found"}
        
        meta = json.loads(row[1]) if row[1] else {}
        method = meta.get("method", "fernet_aes128")
        
        return self.decrypt(row[0], password, method)
    
    def list_secrets(self, category: Optional[str] = None) -> Dict:
        """List stored secrets (names only, not values)"""
        conn = sqlite3.connect(str(self.db_path))
        if category:
            cursor = conn.execute(
                "SELECT name, category, updated_at FROM secrets WHERE category = ? ORDER BY name",
                (category,)
            )
        else:
            cursor = conn.execute("SELECT name, category, updated_at FROM secrets ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        
        return {"ok": True, "n": len(rows),
                "secrets": [{"name": r[0], "category": r[1], "updated": r[2]} for r in rows]}
    
    def delete_secret(self, name: str) -> Dict:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM secrets WHERE name = ?", (name,))
        conn.commit()
        conn.close()
        return {"ok": True, "deleted": name}
    
    def hash_data(self, data: str, algorithm: str = "sha256") -> Dict:
        """Hash data with specified algorithm"""
        algos = {
            "sha256": hashlib.sha256,
            "sha512": hashlib.sha512,
            "md5": hashlib.md5,
            "sha1": hashlib.sha1,
        }
        if algorithm not in algos:
            return {"ok": False, "err": f"Unknown algorithm. Available: {list(algos.keys())}"}
        
        h = algos[algorithm](data.encode()).hexdigest()
        return {"ok": True, "hash": h, "algorithm": algorithm}
    
    def hmac_sign(self, message: str, key: str, algorithm: str = "sha256") -> Dict:
        """Create HMAC signature"""
        h = hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()
        return {"ok": True, "signature": h, "algorithm": f"hmac_{algorithm}"}
    
    def hmac_verify(self, message: str, key: str, signature: str) -> Dict:
        """Verify HMAC signature"""
        expected = hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()
        valid = hmac.compare_digest(expected, signature)
        return {"ok": True, "valid": valid}
