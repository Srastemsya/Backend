import hashlib
import secrets
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

private_dir = Path("/private")
public_dir = Path("/public")
private_path = private_dir / "private.pem"
if not private_path.exists():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                               serialization.NoEncryption()))
    private_path.chmod(0o600)
else:
    key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
public_pem = key.public_key().public_bytes(serialization.Encoding.PEM,
                                           serialization.PublicFormat.SubjectPublicKeyInfo)
for directory in [private_dir, public_dir]:
    (directory / "public.pem").write_bytes(public_pem)
secret_path = private_dir / "identity-secret"
if not secret_path.exists():
    secret_path.write_bytes(os.urandom(32))
    secret_path.chmod(0o600)


acl = ["user default off", "user health on nopass +ping"]
acl_rules = {
    "identity": "~auth:* ~otp:* +ping +get +set +del +multi +exec +client|setinfo",
    "catalog": "%R~auth:* ~cache:catalog:* +ping +get +set +del +client|setinfo",
    "swipes": "%R~auth:* ~cache:swipes:* ~room:* +ping +get +set +del +publish +client|setinfo",
}
for role, rules in acl_rules.items():
    password_dir = private_dir if role == "identity" else Path(f"/{role}")
    password_file = password_dir / "redis-password"
    if not password_file.exists():
        password_file.write_text(secrets.token_urlsafe(32))
        password_file.chmod(0o600)
    verifier = hashlib.sha256(password_file.read_bytes()).hexdigest()
    acl.append(f"user {role} on #{verifier} {rules}")
Path("/acl/users.acl").write_text("\n".join(acl) + "\n")
