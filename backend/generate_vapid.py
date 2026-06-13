import os
from pywebpush import WebPusher

def generate_keys():
    import ecdsa
    import base64
    from ecdsa.util import sigencode_der, sigdecode_der

    # Generamos una keypair SECP256R1 (P-256)
    sk = ecdsa.SigningKey.generate(curve=ecdsa.NIST256p)
    vk = sk.get_verifying_key()

    private_key_der = sk.to_der()
    public_key_der = vk.to_der()

    # The format required for webpush is a urlsafe base64 string
    # Actually, let's just use the vapid tool directly:
    os.system("venv\\Scripts\\vapid --generate")

generate_keys()
