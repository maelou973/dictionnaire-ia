from sources import (
    academie_fr,
    antonyme,
    crisco,
    larousse,
    littre,
    robert,
    synonymo,
    wikidata,
    wiktionary,
)

INFORMATIONS_SOURCES = {
    "wiktionary": {
        "module": wiktionary,
        "nom": "Wiktionary",
        "active_par_defaut": True,
    },

    "academie_fr": {
        "module": academie_fr,
        "nom": "Académie française",
        "active_par_defaut": True,
    },

    "larousse": {
        "module": larousse,
        "nom": "Larousse",
        "active_par_defaut": True,
    },

    "robert": {
        "module": robert,
        "nom": "Le Robert",
        "active_par_defaut": True,
    },

    "littre": {
        "module": littre,
        "nom": "Littré",
        "active_par_defaut": True,
    },

    "crisco": {
        "module": crisco,
        "nom": "Crisco",
        "active_par_defaut": True,
    },

    "synonymo": {
        "module": synonymo,
        "nom": "Synonymo",
        "active_par_defaut": True,
    },

    "antonyme": {
        "module": antonyme,
        "nom": "Antonyme",
        "active_par_defaut": True,
    },

    "wikidata": {
        "module": wikidata,
        "nom": "Wikidata",
        "active_par_defaut": False,
    },
}