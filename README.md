# 🔧 MCP Server Tools

Serveur MCP (Model Context Protocol) complet avec outils Git/GitHub, FileSystem, PDF et base SQLite, plus une interface de contrôle web.

## ✨ Fonctionnalités

- **🐙 Git & GitHub** : Opérations locales (clone) + API GitHub (repos, users, fichiers)
- **📁 FileSystem** : Gestion des fichiers (workspace intelligent)
- **📄 PDF** : Recherche plein texte et extraction par pages (pypdf)
- **🗄️ SQLite** : Bases de données locales isolées dans un répertoire dédié
- **🎛️ Interface Web** : Dashboard de contrôle avec exécution des outils en temps réel
- **🔌 Architecture modulaire** : Ajout facile de nouveaux outils
- **🔄 Hot Reload** : Rechargement automatique des outils

## 🚀 Installation rapide

```bash
# Cloner le repository
git clone https://github.com/FranckDubray/mcp-server-tools.git
cd mcp-server-tools

# Installer les dépendances
pip install -e .

# Lancer en mode développement
./scripts/dev.sh  # Linux/Mac
# ou
./scripts/dev.ps1  # Windows
```

Le script dev.sh vérifie/installe pypdf (support PDF) automatiquement.

## 🎯 Usage

### Interface Web
Accédez à http://localhost:8000/control pour l'interface de contrôle complète.

- Onglet “Secrets & Tokens” pour saisir et enregistrer:
  - GITHUB_TOKEN
  - AI_PORTAL_TOKEN
  - LLM_ENDPOINT
  Ces valeurs sont persistées dans un fichier .env local (ajout automatique dans .gitignore) et appliquées à chaud (sans redémarrage).

### API Endpoints
- `GET /tools` - Liste des outils disponibles
- `POST /execute` - Exécution d'un outil
- `GET /control` - Interface web de contrôle
- `GET /config` / `POST /config` - Lire/écrire la configuration (tokens/env)

## 🛠️ Outils disponibles

### Git & GitHub (`git_github`)
- **Git Local** : `clone`
- **GitHub API** : `create_repo`, `get_user`, `list_repos`, `add_file`, `add_multiple_files`, `delete_file`, `delete_multiple_files`, `get_repo_contents`, `create_branch`, `get_commits`, `diff`
- **Authentification** : Variable d'environnement `GITHUB_TOKEN`

### PDF

- `pdf2text` — Extraction de texte par pages
  - Entrées:
    - `path` (string) : chemin vers le PDF (relatif à la racine du projet ou absolu)
    - `pages` (string, optionnel) : sélection de pages 1-based, ex: `"1-3,5,10"`
  - Sortie:
    - `text` : texte concaténé de toutes les pages demandées
    - `by_page` : tableau `{page, text}` pour chaque page (idéal pour envoyer au LLM)
  - Exemple:
    ```json
    {
      "tool_reg": "pdf2text",
      "params": {"path": "docs/mon_doc.pdf", "pages": "1-3"}
    }
    ```

- `pdf_search` — Recherche plein texte dans un ou plusieurs PDF
  - Entrées (principales):
    - `path` (fichier ou dossier) ou `paths` (liste)
    - `query` (string) : texte à rechercher
    - Options : `regex` (bool), `case_sensitive` (bool), `pages` (string 1-based), `recursive` (bool), `max_results` (int), `context` (int)
  - Sortie:
    - `results` : liste des occurrences `{file, page, start, end, match, snippet}`
    - `per_file` : récap par fichier, `errors` : erreurs rencontrées
  - Exemple:
    ```json
    {
      "tool_reg": "pdf_search",
      "params": {
        "operation": "search",
        "path": "docs/pdfs",
        "query": "Invoice",
        "recursive": true,
        "max_results": 100
      }
    }
    ```

### SQLite local (`sqlite3`)
- Répertoire des bases: `<racine_projet>/sqlite3` (créé automatiquement)
- Opérations:
  - `ensure_dir` — crée le dossier si besoin
  - `list_dbs` — liste des bases disponibles
  - `create_db` — crée une base (optionnel: `schema` SQL d'init)
  - `delete_db` — supprime une base
  - `get_tables` — liste des tables
  - `describe` — colonnes d'une table
  - `execute`/`exec`/`query` — exécute une requête (params/many/return_rows)
  - `executescript` — exécute un script SQL multi-instructions
- Exemples:
  - Créer une base et une table:
    ```json
    {
      "tool_reg": "sqlite3",
      "params": {
        "operation": "create_db",
        "name": "mydb",
        "schema": "CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, text TEXT);"
      }
    }
    ```
  - Insérer une ligne:
    ```json
    {
      "tool_reg": "sqlite3",
      "params": {
        "operation": "execute",
        "db": "mydb",
        "query": "INSERT INTO notes(text) VALUES(?)",
        "params": ["hello world"]
      }
    }
    ```
  - Sélectionner:
    ```json
    {
      "tool_reg": "sqlite3",
      "params": {
        "operation": "execute",
        "db": "mydb",
        "query": "SELECT * FROM notes"
      }
    }
    ```

### Calculs
- `add` : Addition de deux nombres (entrées: 2 strings décimales signées; sortie: string; précision arbitraire; virgule/point acceptés)
- `multiply` : Multiplication (mêmes conventions qu'au-dessus)

## ⚙️ Configuration

Variables d'environnement :
- `MCP_HOST=127.0.0.1` (par défaut)
- `MCP_PORT=8000` (par défaut)
- `LOG_LEVEL=INFO`
- `GITHUB_TOKEN` (requis pour GitHub API)
- `AI_PORTAL_TOKEN` (requis pour le tool call_llm)
- `LLM_ENDPOINT` (optionnel)
- `RELOAD=1` (rechargement automatique)
- `AUTO_RELOAD_TOOLS=1` (auto-détection des nouveaux tools)
- `EXECUTE_TIMEOUT_SEC=30`

Les tokens peuvent être saisis via l'interface `/control` et sont persistés dans `.env` (non versionné).

## 🏗️ Architecture

```
src/add_mcp_server/
├── server.py          # Lanceur (uvicorn)
├── app_factory.py     # Création de l'app, endpoints, discovery des tools
├── config.py          # Gestion .env / racine projet / masquage
├── ui_html.py         # HTML de l'interface /control
├── ui_js.py           # JS de l'interface /control
└── tools/             # Outils modulaires
    ├── git_github.py
    ├── pdf2text.py
    ├── pdf_search.py
    ├── sqlite_db.py
    ├── add.py
    └── multiply.py
```

## 🔄 Développement

### Ajouter un nouvel outil

1. Créer `tools/mon_outil.py` :
```python
def run(param1: str, param2: int):
    """Fonction principale de l'outil"""
    return {"result": f"Traité {param1} avec {param2}"}

def spec():
    """Spécification OpenAI/Anthropic"""
    return {
        "type": "function", 
        "function": {
            "name": "mon_outil",
            "description": "Description de mon outil",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                    "param2": {"type": "number"}
                },
                "required": ["param1", "param2"]
            }
        }
    }
```

2. Recharger le serveur → l'outil est automatiquement découvert !

### Hot Reload
- Modification d'un outil → rechargement automatique
- `GET /tools?reload=1` → rechargement forcé
- Variable `RELOAD=1` → rechargement continu

## 📋 Points techniques

- **Découverte automatique** : `pkgutil.iter_modules()`
- **ETag** : Cache intelligent pour `/tools`
- **CORS** : Support complet pour interface web
- **Timeout** : 30s par défaut pour l'exécution
- **Validation** : Pydantic pour les requêtes
- **PDF** : pypdf (installé via script `dev.sh`)
- **SQLite** : Python stdlib `sqlite3`, bases stockées dans `./sqlite3`

## 🎛️ Interface de contrôle

L'interface web (`/control`) permet :
- ✅ Visualisation de tous les outils
- ⚡ Exécution en temps réel
- 📝 Formulaires dynamiques avec validation
- 🔄 Rechargement avec préservation des valeurs
- 📊 Affichage des résultats formatés
- 🔑 Gestion des tokens (config) avec persistance `.env`

## 🤝 Contribution

1. Fork du projet
2. Branche feature (`git checkout -b feature/nouvel-outil`)
3. Commit (`git commit -am 'Ajout nouvel outil'`)
4. Push (`git push origin feature/nouvel-outil`)
5. Pull Request

## 📝 License

MIT - Voir le fichier LICENSE

## 📚 Documentation complète

Consultez `mcp_server_min_playbook.md` pour le guide complet de développement.
