import os
import re
from cryptography.fernet import Fernet
from dotenv import load_dotenv
load_dotenv()

# In a real production environment, this key should be stored in a secure secret manager
# (e.g., AWS Secrets Manager, HashiCorp Vault). For this simulation, we'll use an env var 
# or a fallback generated key.
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise RuntimeError("ENCRYPTION_KEY environment variable is not set")
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_secret(secret: str) -> str:
    """Encrypts a string secret."""
    if not secret:
        return ""
    return cipher_suite.encrypt(secret.encode()).decode()

def decrypt_secret(encrypted_secret: str) -> str:
    """Decrypts an encrypted string secret."""
    if not encrypted_secret:
        return ""
    try:
        return cipher_suite.decrypt(encrypted_secret.encode()).decode()
    except Exception:
        # If decryption fails (e.g., already decrypted or wrong key), return as is or handle error
        return encrypted_secret

def sanitize_pii(text: str) -> str:
    """
    Scrubs common PII from text before sending to LLM.
    Redacts: Email addresses, Phone numbers, Social Security Numbers (simulation).
    """
    if not text:
        return ""
    
    # Redact Email
    text = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[EMAIL_REDACTED]', text)
    
    # Redact Phone Numbers (Basic pattern for US/International)
    # Refined to avoid matching SSN-like patterns
    text = re.sub(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{3,4}[-.\s]?\d{4,9}', '[PHONE_REDACTED]', text)
    
    # Redact SSN-like patterns (3-2-4 digits)
    text = re.sub(r'\d{3}-\d{2}-\d{4}', '[SSN_REDACTED]', text)
    
    return text
