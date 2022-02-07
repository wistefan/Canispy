import secrets


secrets = "No-settngs"
try:
    from secrets import secret_settings
except Exception as e:
    print(f"Not found: {e}")
print(secrets)