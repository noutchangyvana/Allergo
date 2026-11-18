"""Point d'entrée de l'API pour un hébergeur (Vercel) : il expose l'objet `app`.

En local, préférer `uv run allergolab servir`, qui fait la même chose.
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

service = Service(Configuration.environnement())
app = creer_application(service=service)
# L'hébergeur peut ne pas déclencher le démarrage de FastAPI : le service est déjà prêt.
app.state.service = service
