import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


def generate_key():
    """Generates a 256-bit AES key"""
    return AESGCM.generate_key(bit_length=256)


def pad_data(data: bytes, block_size: int = 16) -> bytes:
    """Add PKCS7 padding to data"""
    if isinstance(data, str):
        data = data.encode()
    
    padding_length = block_size - (len(data) % block_size)
    padding = bytes([padding_length] * padding_length)
    return data + padding


def unpad_data(data: bytes, block_size: int = 16) -> bytes:
    """Remove PKCS7 padding from data"""
    if not data:
        return data
    
    padding_length = data[-1]
    # Validate padding to prevent errors
    if padding_length > block_size or padding_length == 0:
        return data
    
    return data[:-padding_length]


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
    
    # Pad the data before encryption
    data = pad_data(data)
    
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
    decrypted = aes.decrypt(nonce, ciphertext, None)
    
    # Remove padding after decryption
    return unpad_data(decrypted)


def get_master_key():
    """Return the MASTER_KEY from Django settings"""
    return base64.urlsafe_b64decode(settings.MASTER_KEY)