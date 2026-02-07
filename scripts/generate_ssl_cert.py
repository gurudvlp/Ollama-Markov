#!/usr/bin/env python3
"""
Generate self-signed SSL certificate for Ollama-Markov server.

This creates a self-signed certificate for testing HTTPS locally.
For production use, obtain proper certificates from a CA (Let's Encrypt, etc.).
"""

import sys
from pathlib import Path


def generate_certificate(cert_path: str = "cert.pem", key_path: str = "key.pem"):
    """
    Generate a self-signed SSL certificate.

    Args:
        cert_path: Path where certificate will be saved
        key_path: Path where private key will be saved
    """
    try:
        from OpenSSL import crypto
    except ImportError:
        print("ERROR: pyOpenSSL not installed. Install with: pip install pyOpenSSL")
        sys.exit(1)

    # Generate RSA key
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    # Generate certificate
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "State"
    cert.get_subject().L = "City"
    cert.get_subject().O = "Ollama-Markov"
    cert.get_subject().OU = "Development"
    cert.get_subject().CN = "localhost"

    # Set serial number and validity
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # Valid for 1 year

    # Set issuer (self-signed)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)

    # Sign certificate
    cert.sign(key, 'sha256')

    # Save certificate
    cert_path_obj = Path(cert_path)
    with open(cert_path_obj, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    print(f"✓ Certificate saved to: {cert_path_obj.absolute()}")

    # Save private key
    key_path_obj = Path(key_path)
    with open(key_path_obj, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
    print(f"✓ Private key saved to: {key_path_obj.absolute()}")

    print("\nTo use these certificates, set these environment variables:")
    print(f"  export SSL_ENABLED=true")
    print(f"  export SSL_CERT={cert_path_obj.absolute()}")
    print(f"  export SSL_KEY={key_path_obj.absolute()}")
    print("\nOr add to your .env file:")
    print(f"  SSL_ENABLED=true")
    print(f"  SSL_CERT={cert_path_obj.absolute()}")
    print(f"  SSL_KEY={key_path_obj.absolute()}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate self-signed SSL certificate")
    parser.add_argument("--cert", default="cert.pem", help="Certificate output path (default: cert.pem)")
    parser.add_argument("--key", default="key.pem", help="Private key output path (default: key.pem)")

    args = parser.parse_args()

    print("Generating self-signed SSL certificate...")
    generate_certificate(args.cert, args.key)
    print("\n⚠️  WARNING: This is a self-signed certificate for development only.")
    print("   Clients will show security warnings. For production, use proper CA-signed certificates.")
