"""Les chemins du projet ne dépendent ni du compte utilisateur ni du dossier courant."""

from pathlib import Path

from allergolab.configuration import DOSSIER, NOM_DONNEES, Configuration


def test_chemins_par_defaut_dans_projet():
    configuration = Configuration()
    assert configuration.donnees == DOSSIER / "donnees" / NOM_DONNEES
    assert configuration.reglages == DOSSIER / "configuration" / "modeles.toml"
    assert configuration.runtime == DOSSIER / "runtime"


def test_chemin_relatif_independant_du_dossier_courant(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ALLERGOLAB_DONNEES", "donnees/ma cohorte.csv")
    monkeypatch.setenv("ALLERGOLAB_REGLAGES", "configuration/modeles.toml")
    configuration = Configuration.environnement()
    assert configuration.donnees == (DOSSIER / "donnees" / "ma cohorte.csv").resolve()
    assert configuration.reglages == (DOSSIER / "configuration" / "modeles.toml").resolve()


def test_chemin_absolu_personnalise(tmp_path, monkeypatch):
    chemin = tmp_path / "autre emplacement" / "cohorte.csv"
    monkeypatch.setenv("ALLERGOLAB_DONNEES", str(chemin))
    assert Configuration.environnement().donnees == chemin.resolve()


def test_chemins_fournis_present_dans_dossier():
    configuration = Configuration()
    assert configuration.donnees.is_file()
    assert configuration.reglages.is_file()
    assert configuration.donnees.is_relative_to(DOSSIER)
    assert configuration.reglages.is_relative_to(DOSSIER)
    assert Path(configuration.reglages).read_text(encoding="utf-8")
