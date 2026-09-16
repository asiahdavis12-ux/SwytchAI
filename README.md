
# 🔀 SwytchAI

### AI-Powered Network Configuration Management Platform

🌐 **Live:** [https://swytchai.net](https://swytchai.net)
📦 **Version:** 3.1
📄 **License:** Proprietary

---

## 🚀 What is SwytchAI?

SwytchAI is an enterprise-grade, AI-powered platform that automates network configuration management across multi-vendor environments. Built for network engineers and IT teams who need to manage Cisco, Juniper, and Arista devices from a single, secure dashboard.

Instead of manually SSHing into every switch, writing vendor-specific commands, and hoping nobody made a typo — SwytchAI handles it all with an intelligent approval workflow, version tracking, and an AI assistant that writes configs in plain English.

---

## ⚡ Key Features

| Feature | Description |
|---|---|
| **🤖 AI Config Assistant** | Describe what you need in plain English — "create VLAN 200" — and SwytchAI generates vendor-specific configs automatically |
| **🔀 Multi-Vendor Support** | Manage Cisco IOS, Juniper JunOS, and Arista EOS devices from one platform using NAPALM |
| **✅ Approval Workflow** | No config touches your network without review. Propose → Approve → Push with full accountability |
| **📜 Version Tracking & Diff** | Every config is timestamped and versioned. Compare any two versions side-by-side |
| **👥 Role-Based Access Control** | 4 levels — Technician, Team Lead, Manager, Admin — each with scoped permissions |
| **🔔 Real-Time Notifications** | Instant alerts when changes are proposed, approved, or rejected |
| **🔌 REST API** | Integrate SwytchAI into your existing tools with API key authentication |
| **📊 Audit Trail** | Complete logging of every action — who did what, when, and to which device |
| **🗄️ Production Database** | SQLite backend with structured storage, fast queries, and concurrent access |

---

## 🔐 Security

SwytchAI is built with enterprise-grade security as a first-class feature:

- ✅ **Bcrypt** password hashing (industry standard)
- ✅ **Role-Based Access Control** (4 permission levels)
- ✅ **Session timeouts** (auto-logout after inactivity)
- ✅ **Rate limiting** (brute force protection)
- ✅ **Security headers** (XSS, clickjacking, content-type protection)
- ✅ **API key authentication** (secure programmatic access)
- ✅ **HTTPS/TLS encryption** (SSL certificate via Let's Encrypt)
- ✅ **Input sanitization** (XSS and injection prevention)
- ✅ **Dangerous command blocking** (prevents reload, erase, format)
- ✅ **Credential separation** (.env for secrets management)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | HTML5, CSS3, Jinja2 Templates |
| **Backend** | Python 3, Flask |
| **Database** | SQLite |
| **Network Automation** | NAPALM, Netmiko |
| **Production Server** | Gunicorn + Nginx |
| **Hosting** | AWS EC2 (Ubuntu) |
| **DNS & SSL** | AWS Route 53, Let's Encrypt (Certbot) |
| **Version Control** | Git + GitHub |

---

## 📋 How It Works

### 1. Connect Your Devices
Add your network switches and routers. SwytchAI supports Cisco, Juniper, and Arista out of the box.

### 2. Manage with AI
Pull configs, track versions, and use the AI assistant to generate changes in plain English.

### 3. Review & Push
Changes go through your approval workflow before touching the network. Full audit trail included.

---

## 💼 Subscription Plans

SwytchAI is available as a monthly SaaS subscription:

| Plan | Price | Devices | Users | Support |
|---|---|---|---|---|
| **Starter** | $49/month | Up to 10 | Up to 5 | Email |
| **Professional** | $149/month | Up to 50 | Up to 25 | Priority Email |
| **Enterprise** | Custom | Unlimited | Unlimited | Dedicated + SLA |

All plans include: AI Config Assistant, Approval Workflows, Version Tracking, Audit Logs, REST API, and HTTPS encryption.

**[Request Early Access →](https://swytchai.net)**

---

## 🏗️ Roadmap

- [x] Multi-vendor config management (NAPALM)
- [x] AI Config Assistant
- [x] Approval workflow with RBAC
- [x] Version tracking and diff comparison
- [x] Web dashboard (Flask)
- [x] Notification system
- [x] Audit logging
- [x] REST API with key auth
- [x] SQLite database migration
- [x] Security hardening
- [x] AWS EC2 deployment with HTTPS
- [ ] Multi-tenant architecture (organization accounts)
- [ ] Stripe payment integration
- [ ] Team management dashboard
- [ ] Scheduled config backups
- [ ] Compliance reporting (SOC 2)
- [ ] Mobile-responsive dashboard
- [ ] Webhook integrations (Slack, Teams)

---

## 👤 About the Builder

**SwytchAI** was built by **Asiah Davis**, a Network  Technician who saw a real problem in the field — managing network configurations across multi-vendor environments was slow, error-prone, and lacked automation.

Instead of waiting for someone else to solve it, Asiah learned Python from scratch and built SwytchAI — a full-stack, AI-powered platform that automates what used to take hours.

---

## 📬 Contact

- 🌐 **Website:** [https://swytchai.net](https://swytchai.net)
- 💻 **GitHub:** [github.com/asiahdavis12-ux/SwytchAI](https://github.com/asiahdavis12-ux/SwytchAI)

---

© 2026 SwytchAI — All Rights Reserved

