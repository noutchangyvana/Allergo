"""Point d'entrée de l'API pour un hébergeur (Vercel) : il expose l'objet `app`.

L'API du moteur, plus la page web de l'équipe à l'adresse « / ».
En local :  uv run uvicorn app:app --port 8000   puis ouvrir http://127.0.0.1:8000
"""

import os
import sys
import tempfile
from pathlib import Path

# Le code est dans src/ : le rendre importable même si le projet n'est pas installé.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# Sur Vercel, seul le dossier temporaire est accessible en écriture : le cache SQLite y va.
if os.getenv("VERCEL"):
    os.environ.setdefault("ALLERGOLAB_RUNTIME", str(Path(tempfile.gettempdir()) / "allergolab"))

from allergolab.api import creer_application  # noqa: E402
from allergolab.configuration import Configuration  # noqa: E402
from allergolab.service import Service  # noqa: E402
from allergolab.vitrine.routes import ajouter_page  # noqa: E402

service = Service(Configuration.environnement())
app = creer_application(service=service)
# L'hébergeur peut ne pas déclencher le démarrage de FastAPI : le service est déjà prêt.
app.state.service = service
# La page web de l'équipe (Assistant, Explorer, Méthode) à l'adresse « / ».
ajouter_page(app, service)
