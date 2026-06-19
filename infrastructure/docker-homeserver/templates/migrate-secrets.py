#!/usr/bin/env python3
"""Migrate secrets from monolithic .env to per-service SOPS-encrypted files."""
import os
import subprocess
import sys
from pathlib import Path

# --- CONFIGURE THESE ---
HOMESERVER = Path(os.environ.get("HOMESERVER_DIR", os.getcwd()))
SECRETS_DIR=*** / "secrets"
SOPS = os.path.expanduser("~/.local/bin/sops")

# Per-service secret files mapping
# Each creates an env file with the variable definitions the service needs
SERVICE_SECRETS=***    "mc.env": {
        "vars": ["MC_RCON_PASSWORD"],
        "services": ["minecraft-vanilla", "minecraft-modded"],
    },
    "zennotes.env": {
        "vars": ["ZENNOTES_AUTH_TOKEN"],
        "services": ["zennotes"],
    },
    "tailscale.env": {
        "vars": ["TAILSCALE_AUTHKEY"],
        "services": ["tailscale"],
    },
}


def load_env(path: Path) -> dict:
    """Load .env, skipping comments and blanks."""
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            val = val.strip().strip("'").strip('"')
            env[key] = val
    return env


def main():
    env_path = HOMESERVER / ".env"
    if not env_path.exists():
        print(f"ERROR: .env not found at {env_path}")
        sys.exit(1)

    env = load_env(env_path)
    print(f"Loaded {len(env)} variables from .env")

    SECRETS_DIR.mkdir(exist_ok=True)
    print(f"Creating secret files in {SECRETS_DIR}/\n")

    # Create plaintext per-service env files
    for filename, cfg in SERVICE_SECRETS.items():
        filepath = SECRETS_DIR / filename
        with open(filepath, "w") as f:
            for var in cfg["vars"]:
                if var in env:
                    f.write(f"{var}={env[var]}\n")
                else:
                    print(f"  WARNING: {var} not found in .env")
                    f.write(f"# {var}=<add your key here when needed>\n")
        filepath.chmod(0o600)
        print(f"  ✓ {filename} → {', '.join(cfg['services'])}")

    # Encrypt with SOPS
    print("\nEncrypting with SOPS...")
    for filename in SERVICE_SECRETS:
        filepath = SECRETS_DIR / filename
        if not filepath.exists():
            continue
        sops_file = SECRETS_DIR / (filename + ".sops")
        result = subprocess.run(
            [SOPS, "--input-type", "dotenv", "--output-type", "dotenv", "--encrypt", str(filepath)],
            capture_output=True, text=True,
            cwd=HOMESERVER,
        )
        if result.returncode != 0:
            print(f"  ERROR encrypting {filename}: {result.stderr}")
            continue
        with open(sops_file, "w") as f:
            f.write(result.stdout)
        os.chmod(sops_file, 0o644)
        print(f"  ✓ {filename}.sops")

    # Remove plaintext — only .sops remains
    print("\nRemoving plaintext files...")
    for filename in SERVICE_SECRETS:
        (SECRETS_DIR / filename).unlink(missing_ok=True)
    print("  ✓ done")

    # Create .env.example with placeholders
    print("\nCreating .env.example...")
    all_secret_vars = set()
    for cfg in SERVICE_SECRETS.values():
        all_secret_vars.update(cfg["vars"])

    example_path = HOMESERVER / ".env.example"
    with open(env_path) as src, open(example_path, "w") as dst:
        for line in src:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                dst.write(line if line.endswith("\n") else line + "\n")
                continue
            if "=" in stripped:
                key = stripped.split("=", 1)[0]
                if key in all_secret_vars:
                    dst.write(f"# {key}=<see secrets/ directory>\n")
                else:
                    dst.write(line if line.endswith("\n") else line + "\n")
            else:
                dst.write(line if line.endswith("\n") else line + "\n")
    print(f"  ✓ {example_path}")

    print("\n✅ Migration complete!")
    print(f"\n🔑 BACK UP YOUR AGE KEY:")
    print(f"   cat ~/.config/sops/age/keys.txt")
    print(f"\n   Copy the entire file to a secure location (password manager, USB drive).")
    print(f"   Without this key, you cannot decrypt any secrets.")


if __name__ == "__main__":
    main()
