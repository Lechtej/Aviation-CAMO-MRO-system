# Production Server & Deployment (OPS)

## 1. Production environment
- **Provider:** Hetzner
- **OS:** Ubuntu 22.04.5 LTS
- **IPv4:** `65.108.250.169`
- **Daily access:** **SSH only** (no Hetzner web console)

### Why no web console
The Hetzner web console was causing command corruption (line breaks / backslashes), leading to false errors and wasted time.
From now on, production work is done via **normal SSH** from a developer workstation.

> **Emergency exception:** Hetzner panel may be used only for **power on/off** if SSH is unavailable.

## 2. SSH access (target state)
### 2.1 Rules
- ✅ **Public key auth only** (ed25519)
- ❌ Password auth disabled
- ✅ Root login allowed **only** via key (no password)
- ✅ Each person = separate key

### 2.2 Server configuration (sshd)
File:
```
/etc/ssh/sshd_config.d/99-aviationcamo.conf
```

Content:
```conf
PasswordAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
PermitRootLogin prohibit-password
```

Validation / restart:
```bash
sshd -t
systemctl restart ssh
```

## 3. Developer workstation setup (Windows)
### 3.1 Key generation (ed25519)
A dedicated key is generated per project and protected with a passphrase.

Example (PowerShell):
```powershell
ssh-keygen -t ed25519 -a 64 -C "AviationCAMO-MRO <name>" -f $env:USERPROFILE\.ssh\aviationcamo_ed25519
Start-Service ssh-agent
ssh-add $env:USERPROFILE\.ssh\aviationcamo_ed25519
```

### 3.2 SSH alias (required)
Developers connect using:
```powershell
ssh aviationcamo-prod
```

Local file:
```
C:\Users\<user>\.ssh\config
```

Entry:
```sshconfig
Host aviationcamo-prod
    HostName 65.108.250.169
    User root
    IdentityFile ~/.ssh/aviationcamo_ed25519
    IdentitiesOnly yes
```

## 4. Deployment contract (what is allowed where)
### 4.1 Local (repo / GitHub)
Allowed:
- code changes, tests
- commits, PRs, releases
- preparing ZIP releases (`vX.Y.Z`)

Not allowed:
- editing production files manually

### 4.2 SSH (server)
Allowed (and **only** these):
- `git pull`
- `docker compose up -d`
- `docker compose restart`
- `docker compose logs`
- status checks (`docker compose ps`)

Not allowed:
- manual code edits
- hotfixes without repo commit

### 4.3 Browser UI
Allowed:
- Keycloak Admin UI
- Swagger/OpenAPI
- testing the running system

## 5. External tester access (planned)
Target:
- create a dedicated Linux user `tester`
- key-only auth
- no sudo
- limited permissions (read-only logs / access to exposed HTTP endpoints)
