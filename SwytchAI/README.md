

\# 🔀 SwytchAI — AI-Powered Multi-Vendor Network Config Manager



SwytchAI is an intelligent network configuration management tool that lets you manage, track, and deploy configurations across multi-vendor network environments — powered by AI.



\*\*Tell SwytchAI what you need in plain English, and it generates the correct config for your vendor — Cisco, Juniper, Arista, and more.\*\*



\---



\## ✨ Features



\### 🤖 AI Config Assistant

\- Type in plain English: \*"create VLAN 200"\* or \*"set IP on GigabitEthernet1"\*

\- SwytchAI generates the correct vendor-specific config automatically

\- Supports Cisco IOS, NX-OS, Juniper Junos, and Arista EOS



\### 📋 Config Version Tracking

\- Automatically saves every config pull as a new version

\- Full version history with timestamps

\- \*\*Diff comparison\*\* — see exactly what changed between any two versions



\### ✅ Change Approval Workflow

\- \*\*Propose\*\* a config change

\- \*\*Review \& preview\*\* before pushing

\- \*\*Approve or reject\*\* with full audit trail

\- \*\*Rollback\*\* if something goes wrong

\- All changes logged with who, what, and when



\### 🔐 Role-Based Access Control (RBAC)

\- \*\*Technician\*\* — can propose changes, pull configs, view history

\- \*\*Team Lead\*\* — can approve/reject changes

\- \*\*Manager\*\* — full access including rollback and user management

\- \*\*Admin\*\* — emergency push capability



\### 🔑 Secure Authentication

\- SHA-256 password hashing (never stored in plain text)

\- 3-attempt login lockout

\- Forced password change on first login

\- Secure credential management via environment variables



\### 🌐 Multi-Vendor Support (NAPALM)

\- Unified interface across all vendors — same commands, any device

\- Device facts, interface status, LLDP neighbors, ARP table

\- Device health monitoring (CPU, memory, temperature, fans, power)

\- Dry-run config preview — see what WOULD change before applying



\---



\## 🚀 Quick Start



\### Prerequisites

\- Python 3.8 or higher

\- Network devices accessible via SSH (or use Cisco DevNet Sandbox for free)



\### Installation



```bash

\# Clone the repo

git clone https://github.com/yourusername/SwytchAI.git

cd SwytchAI



\# Install dependencies

pip install -r requirements.txt



\# Set up your credentials

cp .env.example .env

\# Edit .env with your device credentials



\# Run SwytchAI

python main.py



