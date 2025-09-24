# 🔧 MCP Server Tools

Serveur MCP (Model Context Protocol) complet avec outils Git/GitHub, FileSystem et interface de contrôle web.

## ✨ Fonctionnalités

- **🐙 Git & GitHub** : Opérations locales (clone, commit, push, pull) + API GitHub (repos, users)
- **📁 FileSystem** : Gestion complète des fichiers avec workspace intelligent
- **🎛 Interface Web** : Dashboard de contrôle avec exécution des outils en temps réel
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

## 🎯 Usage

### Interface Web
Accédez à http://localhost:8000/control pour l'interface de contrôle complète.

### API Endpoints
- `GET /tools` - Liste des outils disponibles
- `POST /execute` - Exécution d'un outil
- `GET /control` - Interface web de contrôle

## 🛠 Outils disponibles

### Git & GitHub (`git_github`)
- **Git Local** : clone, status, add, commit, push, pull, branch, checkout, log, diff
- **GitHub API** : create_repo, get_user, list_repos
- **Authentification** : Variable d'environnement `GITHUB_TOKEN`

### FileSystem (`FileSystemNG`)
- Gestion de workspace (limite 500KB)
- Opérations : load_file, writeFile, list, search, createDirectory
- Support PDF avec sélection de pages

### Calculs
- `add` : Addition de deux nombres
- `multiply` : Multiplication
- `square` : Puissance au carré

## ⚙️ Configuration

Variables d'environnement :
- `MCP_HOST=127.0.0.1` (par défaut)
- `MCP_PORT=8000` (par défaut)
- `LOG_LEVEL=INFO`
- `GITHUB_TOKEN` (requis pour GitHub API)
- `RELOAD=1` (rechargement automatique)

## 🏗 Architecture

```
src/add_mcp_server/
├── server.py          # Serveur principal FastAPI
├── __init__.py
└── tools/             # Outils modulaires
    ├── __init__.py
    ├── git_github.py   # Git + GitHub
    ├── add.py          # Addition
    ├── multiply.py     # Multiplication
    └── square.py       # Puissance
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

2. Redémarrer le serveur → l'outil est automatiquement découvert !

### Hot Reload
- Modification d'un outil → rechargement automatique
- `GET /tools?reload=1` → rechargement forcé
- Variable `RELOAD=1` → rechargement continu

## 📋 Points techniques

- **Découverte automatique** : Utilise `pkgutil.iter_modules()`
- **ETag** : Cache intelligent pour `/tools`
- **CORS** : Support complet pour interface web
- **Timeout** : 30s par défaut pour l'exécution
- **Validation** : Pydantic pour les requêtes

## 🎛 Interface de contrôle

L'interface web (`/control`) permet :
- ✅ Visualisation de tous les outils
- ⚡ Exécution en temps réel
- 📝 Formulaires dynamiques avec validation
- 🔄 Rechargement avec préservation des valeurs
- 📊 Affichage des résultats formatés

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