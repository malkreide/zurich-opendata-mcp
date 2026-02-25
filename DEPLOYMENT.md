# 🚀 Deployment-Anleitung: Zurich Open Data MCP Server (Remote / Browser)

Diese Anleitung zeigt, wie der MCP-Server so bereitgestellt wird, dass er **direkt über den Browser** (claude.ai) genutzt werden kann – ohne lokale Installation von Claude Desktop, VS Code oder ähnlichem.

## Das Prinzip

```
Vorher (stdio – nur lokal):
  Claude Desktop ←→ MCP Server (auf deinem Rechner)

Nachher (SSE – remote):
  Browser (claude.ai) ←→ Internet ←→ MCP Server (in der Cloud)
```

Der Server wird auf einem Cloud-Dienst bereitgestellt und über eine URL erreichbar gemacht. Diese URL wird in Claude.ai als «Remote MCP Integration» eingetragen.

---

## Option A: Deployment auf Render.com (empfohlen für Demo)

### Schritt 1: Repository auf GitHub pushen

```bash
cd zurich-opendata-mcp
git init
git add .
git commit -m "Initial commit with SSE support"
git remote add origin https://github.com/DEIN-USER/zurich-opendata-mcp.git
git push -u origin main
```

### Schritt 2: Render-Account erstellen

1. Gehe zu [render.com](https://render.com) und erstelle einen Account (kostenlos).
2. Klicke auf **«New» → «Web Service»**.
3. Verbinde dein GitHub-Repository.

### Schritt 3: Einstellungen

| Einstellung | Wert |
|---|---|
| **Name** | `zurich-opendata-mcp` |
| **Runtime** | Python |
| **Build Command** | `pip install .` |
| **Start Command** | `zurich-opendata-mcp` |
| **Plan** | Free |

### Schritt 4: Umgebungsvariablen setzen

Unter **«Environment»** folgende Variablen hinzufügen:

| Variable | Wert |
|---|---|
| `MCP_TRANSPORT` | `sse` |
| `MCP_HOST` | `0.0.0.0` |
| `MCP_PORT` | `10000` |

> **Hinweis:** Render nutzt intern Port 10000. Der Server wird automatisch unter einer URL wie `https://zurich-opendata-mcp.onrender.com` verfügbar.

### Schritt 5: Deploy starten

Klicke **«Create Web Service»**. Das Deployment dauert ca. 2–5 Minuten.

---

## Option B: Deployment auf Railway.app

### Schritt 1: Repository verbinden

1. Gehe zu [railway.app](https://railway.app) und logge dich mit GitHub ein.
2. Klicke auf **«New Project» → «Deploy from GitHub Repo»**.
3. Wähle dein Repository.

### Schritt 2: Umgebungsvariablen

Railway erkennt das `Procfile` automatisch. Setze zusätzlich:

| Variable | Wert |
|---|---|
| `MCP_TRANSPORT` | `sse` |

> Railway setzt `PORT` automatisch. Der Server passt sich an.

### Schritt 3: Domain generieren

Unter **«Settings» → «Networking» → «Generate Domain»** erhältst du eine URL wie `https://zurich-opendata-mcp-production.up.railway.app`.

---

## Option C: Docker (für eigene Server / städtische Infrastruktur)

```bash
# Image bauen
docker build -t zurich-opendata-mcp .

# Container starten
docker run -p 8080:8080 zurich-opendata-mcp
```

Der Server ist dann unter `http://localhost:8080/sse` erreichbar.

---

## In Claude.ai einbinden

Sobald der Server läuft:

1. Öffne [claude.ai](https://claude.ai) im Browser.
2. Gehe zu **Settings** (Zahnrad-Icon unten links).
3. Navigiere zu **«Integrations»**.
4. Klicke auf **«Add More»** → **«Add custom integration»**.
5. Gib einen Namen ein, z. B. `Zürich Open Data`.
6. Trage die **SSE-URL** ein, z. B.:
   - Render: `https://zurich-opendata-mcp.onrender.com/sse`
   - Railway: `https://zurich-opendata-mcp-production.up.railway.app/sse`
7. Speichere und aktiviere die Integration.

**Fertig!** Du kannst nun in einem neuen Chat auf claude.ai Fragen wie diese stellen:

- *«Welche Datensätze gibt es zum Thema Schule in Zürich?»*
- *«Zeig mir die Schulanlagen im Kreis 4.»*
- *«Was sagt der Gemeinderat zum Thema Digitalisierung?»*

---

## Hinweise zur Sicherheit

- Der Server greift ausschliesslich auf **öffentliche Open Data** zu (CC0-Lizenz).
- Es werden **keine personenbezogenen Daten** verarbeitet.
- Für eine produktive Nutzung empfehlen wir eine Bereitstellung auf städtischer Infrastruktur.
- Die SSE-URL sollte bei einer produktiven Nutzung mit einem API-Key geschützt werden.

---

## Fehlerbehebung

| Problem | Lösung |
|---|---|
| Server startet nicht | Prüfe, ob `MCP_TRANSPORT=sse` gesetzt ist |
| «Connection refused» in Claude.ai | Stelle sicher, dass die URL mit `/sse` endet |
| Render zeigt «Suspended» | Kostenloser Plan schläft nach 15 Min. Inaktivität ein – einfach neu aufrufen |
| Tools erscheinen nicht | Starte einen **neuen Chat** nach dem Hinzufügen der Integration |
