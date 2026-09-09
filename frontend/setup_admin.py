import getpass
import hashlib
import secrets
import os

print()
print("🔐 BURAK REVIEW ADMIN KURULUMU")
print()

username = input("Admin kullanıcı adı: ").strip()

while not username:
    username = input("Kullanıcı adı boş olamaz: ").strip()

while True:
    password = getpass.getpass("Admin şifresi: ")

    if len(password) < 12:
        print("❌ Şifre en az 12 karakter olmalı.")
        continue

    password2 = getpass.getpass("Şifre tekrar: ")

    if password != password2:
        print("❌ Şifreler eşleşmiyor.")
        continue

    break

salt = secrets.token_bytes(16)
iterations = 310000

password_hash = hashlib.pbkdf2_hmac(
    "sha256",
    password.encode("utf-8"),
    salt,
    iterations
)

value = (
    f"pbkdf2_sha256${iterations}$"
    f"{salt.hex()}${password_hash.hex()}"
)

with open("secrets.env", "w", encoding="utf-8") as file:
    file.write(f"ADMIN_USERNAME={username}\n")
    file.write(f"ADMIN_PASSWORD_HASH={value}\n")

os.chmod("secrets.env", 0o600)

print()
print("✅ Admin bilgileri oluşturuldu.")
print("🔒 secrets.env oluşturuldu.")
print("⚠️ Bu dosyayı GitHub'a göndermeyeceğiz.")
print()
