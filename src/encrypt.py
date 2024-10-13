from cryptography.fernet import Fernet

# Generate a key for encryption (needed first time only)
key = Fernet.generate_key()

# Save the key to a file (This file should be stored in cloud secret manager in prod env)
with open("secret.key", "wb") as key_file:
    key_file.write(key)

# Read the config file (I've removed config.ini file as it's needed first time only)
with open("config.ini", "rb") as file:
    config_data = file.read()

# Encrypt the config data
f = Fernet(key)
encrypted_data = f.encrypt(config_data)

# Write the encrypted config to a new file
with open("config.ini.enc", "wb") as enc_file:
    enc_file.write(encrypted_data)

print("Encryption complete. Config file saved as 'config.ini.enc'.")
print("Store the 'secret.key' securely. It is needed for decryption.")
