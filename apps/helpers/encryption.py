import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


def generate_key():
    """Generates a 256-bit AES key"""
    return AESGCM.generate_key(bit_length=256)


def encrypt_with_key(key: bytes, data: bytes) -> bytes:
    """Encrypt input bytes using a key, returning bytes"""
    # Convert inputs to bytes if they're memoryview or other types
    if isinstance(key, memoryview):
        key = key.tobytes()
    elif isinstance(key, str):
        key = key.encode()
    
    if isinstance(data, memoryview):
        data = data.tobytes()
    elif isinstance(data, str):
        data = data.encode()
    
    aes = AESGCM(key)
    nonce = os.urandom(12)
    encrypted = aes.encrypt(nonce, data, None)
    return nonce + encrypted


def decrypt_with_key(key: bytes, encrypted: bytes) -> bytes:
    """Decrypt input bytes using a key, returning bytes"""
    # Convert inputs to bytes if they're memoryview or other types
    if isinstance(key, memoryview):
        key = key.tobytes()
    elif isinstance(key, str):
        key = key.encode()
    
    if isinstance(encrypted, memoryview):
        encrypted = encrypted.tobytes()
    elif isinstance(encrypted, str):
        encrypted = encrypted.encode()
    
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]
    aes = AESGCM(key)
    return aes.decrypt(nonce, ciphertext, None)


def get_master_key():
    """Return the MASTER_KEY from Django settings"""
    return base64.urlsafe_b64decode(settings.MASTER_KEY)
