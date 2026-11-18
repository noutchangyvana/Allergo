"""Ce que veut dire un code d'allergène : sa source (nom courant et latin), sa catégorie, et la famille de protéine.

Ce fichier n'est pas un outil : c'est une table, écrite par l'équipe d'après la
nomenclature OMS/IUIS des allergènes (www.allergen.org). Le dictionnaire officiel
du jeu de données ne donne pas ces noms. Un code absent de la table n'a simplement
pas de nom connu ici : on ne devine pas.

Lecture d'un code : Ara_h_2 = Arachis hypogaea (arachide), composant n°2.
Les deux premiers morceaux désignent l'espèce, le reste le composant.
"""

# Espèce -> (nom courant, nom latin, catégorie)
SOURCES = {
    "Aca_s": ("Acarien de stockage", "Acarus siro", "Acariens"),
    "Ach_d": ("Grillon domestique", "Acheta domesticus", "Aliments d'origine animale"),
    "Act_d": ("Kiwi", "Actinidia deliciosa", "Aliments végétaux"),
    "Ail_a": ("Ailante", "Ailanthus altissima", "Pollens d'arbres"),
    "All_c": ("Oignon", "Allium cepa", "Aliments végétaux"),
    "All_s": ("Ail", "Allium sativum", "Aliments végétaux"),
    "Aln_g": ("Aulne", "Alnus glutinosa", "Pollens d'arbres"),
    "Alpha-Gal": ("Alpha-gal (viande de mammifère)", "galactose-alpha-1,3-galactose", "Aliments d'origine animale"),
    "Alt_a": ("Alternaria", "Alternaria alternata", "Moisissures et levures"),
    "Ama_r": ("Amarante", "Amaranthus retroflexus", "Pollens d'herbacées"),
    "Amb_a": ("Ambroisie", "Ambrosia artemisiifolia", "Pollens d'herbacées"),
    "Ana_o": ("Noix de cajou", "Anacardium occidentale", "Aliments végétaux"),
    "Ani_s": ("Anisakis", "Anisakis simplex", "Aliments d'origine animale"),
    "Api_g": ("Céleri", "Apium graveolens", "Aliments végétaux"),
    "Api_m": ("Abeille (venin)", "Apis mellifera", "Venins d'hyménoptères"),
    "Ara_h": ("Arachide", "Arachis hypogaea", "Aliments végétaux"),
    "Arg_r": ("Tique du pigeon", "Argas reflexus", "Insectes et arthropodes"),
    "Art_v": ("Armoise", "Artemisia vulgaris", "Pollens d'herbacées"),
    "Asp_f": ("Aspergillus", "Aspergillus fumigatus", "Moisissures et levures"),
    "Ave_s": ("Avoine", "Avena sativa", "Aliments végétaux"),
    "Ber_e": ("Noix du Brésil", "Bertholletia excelsa", "Aliments végétaux"),
    "Bet_v": ("Bouleau", "Betula verrucosa", "Pollens d'arbres"),
    "Bla_g": ("Blatte germanique", "Blattella germanica", "Insectes et arthropodes"),
    "Blo_t": ("Acarien tropical", "Blomia tropicalis", "Acariens"),
    "Bos_d": ("Vache (lait, viande)", "Bos domesticus", "Aliments d'origine animale"),
    "Cam_d": ("Dromadaire", "Camelus dromedarius", "Animaux"),
    "Can_f": ("Chien", "Canis familiaris", "Animaux"),
    "Can_s": ("Chanvre", "Cannabis sativa", "Aliments végétaux"),
    "Cap_a": ("Poivron", "Capsicum annuum", "Aliments végétaux"),
    "Cap_h": ("Chèvre (lait, épithélium)", "Capra hircus", "Animaux"),
    "Car_i": ("Noix de pécan", "Carya illinoinensis", "Aliments végétaux"),
    "Car_p": ("Papaye", "Carica papaya", "Aliments végétaux"),
    "Cav_p": ("Cobaye", "Cavia porcellus", "Animaux"),
    "Che_a": ("Chénopode", "Chenopodium album", "Pollens d'herbacées"),
    "Che_q": ("Quinoa", "Chenopodium quinoa", "Aliments végétaux"),
    "Chi_spp.": ("Chironome", "Chironomus spp.", "Insectes et arthropodes"),
    "Cic_a": ("Pois chiche", "Cicer arietinum", "Aliments végétaux"),
    "Cit_s": ("Orange", "Citrus sinensis", "Aliments végétaux"),
    "Cla_h": ("Cladosporium", "Cladosporium herbarum", "Moisissures et levures"),
    "Clu_h": ("Hareng", "Clupea harengus", "Aliments d'origine animale"),
    "Cor_a": ("Noisetier (pollen, noisette)", "Corylus avellana", None),  # pollen ou fruit : décidé code par code, voir PRECISIONS
    "Cra_c": ("Crevette grise", "Crangon crangon", "Aliments d'origine animale"),
    "Cry_j": ("Cèdre du Japon", "Cryptomeria japonica", "Pollens d'arbres"),
    "Cuc_m": ("Melon", "Cucumis melo", "Aliments végétaux"),
    "Cuc_p": ("Courge", "Cucurbita pepo", "Aliments végétaux"),
    "Cup_a": ("Cyprès de l'Arizona", "Cupressus arizonica", "Pollens d'arbres"),
    "Cup_s": ("Cyprès", "Cupressus sempervirens", "Pollens d'arbres"),
    "Cyn_d": ("Chiendent", "Cynodon dactylon", "Pollens de graminées"),
    "Cyp_c": ("Carpe", "Cyprinus carpio", "Aliments d'origine animale"),
    "Dau_c": ("Carotte", "Daucus carota", "Aliments végétaux"),
    "Der_f": ("Acarien D. farinae", "Dermatophagoides farinae", "Acariens"),
    "Der_p": ("Acarien D. pteronyssinus", "Dermatophagoides pteronyssinus", "Acariens"),
    "Dol_spp": ("Guêpe Dolichovespula (venin)", "Dolichovespula spp.", "Venins d'hyménoptères"),
    "Equ_c": ("Cheval", "Equus caballus", "Animaux"),
    "Fag_e": ("Sarrasin", "Fagopyrum esculentum", "Aliments végétaux"),
    "Fag_s": ("Hêtre", "Fagus sylvatica", "Pollens d'arbres"),
    "Fel_d": ("Chat", "Felis domesticus", "Animaux"),
    "Fic_b": ("Ficus (plante d'intérieur)", "Ficus benjamina", "Autres"),
    "Fic_c": ("Figue", "Ficus carica", "Aliments végétaux"),
    "Fra_a": ("Fraise", "Fragaria ananassa", "Aliments végétaux"),
    "Fra_e": ("Frêne", "Fraxinus excelsior", "Pollens d'arbres"),
    "Gad_c": ("Morue", "Gadus callarias", "Aliments d'origine animale"),
    "Gad_m": ("Cabillaud", "Gadus morhua", "Aliments d'origine animale"),
    "Gal_d": ("Poule (œuf, viande)", "Gallus domesticus", "Aliments d'origine animale"),
    "Gly_d": ("Acarien de stockage", "Glycyphagus domesticus", "Acariens"),
    "Gly_m": ("Soja", "Glycine max", "Aliments végétaux"),
    "Hel_a": ("Tournesol", "Helianthus annuus", "Aliments végétaux"),
    "Hev_b": ("Latex", "Hevea brasiliensis", "Latex"),
    "Hom_g": ("Homard", "Homarus gammarus", "Aliments d'origine animale"),
    "Hom_s": ("Lactoferrine humaine", "Homo sapiens", "Autres"),
    "Hor_v": ("Orge", "Hordeum vulgare", "Aliments végétaux"),
    "Jug_r": ("Noix (noyer)", "Juglans regia", "Aliments végétaux"),
    "Jun_a": ("Genévrier", "Juniperus ashei", "Pollens d'arbres"),
    "Len_c": ("Lentille", "Lens culinaris", "Aliments végétaux"),
    "Lep_d": ("Acarien de stockage", "Lepidoglyphus destructor", "Acariens"),
    "Lit_s": ("Litchi", "Litchi chinensis", "Aliments végétaux"),
    "Loc_m": ("Criquet migrateur", "Locusta migratoria", "Aliments d'origine animale"),
    "Lol_p": ("Ray-grass", "Lolium perenne", "Pollens de graminées"),
    "Lol_spp.": ("Ray-grass", "Lolium spp.", "Pollens de graminées"),
    "Lup_a": ("Lupin", "Lupinus albus", "Aliments végétaux"),
    "MUXF3": ("Marqueur glucidique CCD", "MUXF3", "Marqueurs"),
    "Mac_i": ("Noix de macadamia", "Macadamia integrifolia", "Aliments végétaux"),
    "Mac_inte": ("Noix de macadamia", "Macadamia integrifolia", "Aliments végétaux"),
    "Mal_d": ("Pomme", "Malus domestica", "Aliments végétaux"),
    "Mala_s": ("Malassezia", "Malassezia sympodialis", "Moisissures et levures"),
    "Man_i": ("Mangue", "Mangifera indica", "Aliments végétaux"),
    "Mel_g": ("Dinde", "Meleagris gallopavo", "Aliments d'origine animale"),
    "Mer_a": ("Mercuriale", "Mercurialis annua", "Pollens d'herbacées"),
    "Mus_a": ("Banane", "Musa acuminata", "Aliments végétaux"),
    "Mus_m": ("Souris", "Mus musculus", "Animaux"),
    "Myt_e": ("Moule", "Mytilus edulis", "Aliments d'origine animale"),
    "Ole_e": ("Olivier", "Olea europaea", "Pollens d'arbres"),
    "Ori_v": ("Origan", "Origanum vulgare", "Aliments végétaux"),
    "Ory_c": ("Lapin", "Oryctolagus cuniculus", "Animaux"),
    "Par_j": ("Pariétaire", "Parietaria judaica", "Pollens d'herbacées"),
    "Pen_m": ("Crevette", "Penaeus monodon", "Aliments d'origine animale"),
    "Phl_p": ("Fléole", "Phleum pratense", "Pollens de graminées"),
    "Pla_a": ("Platane", "Platanus acerifolia", "Pollens d'arbres"),
    "Pla_l": ("Plantain", "Plantago lanceolata", "Pollens d'herbacées"),
    "Pol_d": ("Guêpe Polistes (venin)", "Polistes dominula", "Venins d'hyménoptères"),
    "Pru_p": ("Pêche", "Prunus persica", "Aliments végétaux"),
    "Sal_k": ("Soude (salsola)", "Salsola kali", "Pollens d'herbacées"),
    "Ses_i": ("Sésame", "Sesamum indicum", "Aliments végétaux"),
    "Tri_a": ("Blé", "Triticum aestivum", "Aliments végétaux"),
    "Ves_v": ("Guêpe Vespula (venin)", "Vespula vulgaris", "Venins d'hyménoptères"),
}

# Composant -> famille de protéine, pour les composants les mieux établis seulement.
FAMILLES = {
    "Bet_v_1": "PR-10", "Aln_g_1": "PR-10", "Cor_a_1.0101": "PR-10", "Cor_a_1.0103": "PR-10", "Cor_a_1.0401": "PR-10",
    "Fag_s_1": "PR-10", "Mal_d_1": "PR-10", "Pru_p_1": "PR-10", "Ara_h_8": "PR-10", "Gly_m_4": "PR-10", "Act_d_8": "PR-10",
    "Api_g_1": "PR-10", "Dau_c_1": "PR-10",
    "Ara_h_9": "LTP", "Cor_a_8": "LTP", "Pru_p_3": "LTP", "Mal_d_3": "LTP", "Jug_r_3": "LTP", "Tri_a_14": "LTP",
    "Art_v_3": "LTP", "Par_j_2": "LTP", "Pla_a_3": "LTP", "Ole_e_7": "LTP", "Act_d_10": "LTP", "Api_g_2": "LTP", "Can_s_3": "LTP",
    "Ara_h_2": "Albumine 2S (stockage)", "Ara_h_6": "Albumine 2S (stockage)", "Cor_a_14": "Albumine 2S (stockage)",
    "Ana_o_3": "Albumine 2S (stockage)", "Jug_r_1": "Albumine 2S (stockage)", "Ber_e_1": "Albumine 2S (stockage)",
    "Ses_i_1": "Albumine 2S (stockage)", "Fag_e_2": "Albumine 2S (stockage)",
    "Ara_h_1": "Vicilline 7S (stockage)", "Gly_m_5": "Vicilline 7S (stockage)", "Jug_r_2": "Vicilline 7S (stockage)",
    "Ara_h_3": "Légumine 11S (stockage)", "Gly_m_6": "Légumine 11S (stockage)", "Cor_a_9": "Légumine 11S (stockage)",
    "Ana_o_2": "Légumine 11S (stockage)", "Jug_r_4": "Légumine 11S (stockage)",
    "Bet_v_2": "Profiline", "Phl_p_12": "Profiline", "Hev_b_8": "Profiline", "Mer_a_1": "Profiline",
    "Bet_v_4": "Polcalcine", "Phl_p_7": "Polcalcine",
    "Der_p_10": "Tropomyosine", "Pen_m_1": "Tropomyosine", "Bla_g_7": "Tropomyosine", "Ani_s_3": "Tropomyosine",
    "Fel_d_2": "Albumine sérique", "Can_f_3": "Albumine sérique", "Equ_c_3": "Albumine sérique", "Bos_d_6": "Albumine sérique",
    "Gal_d_5": "Albumine sérique",
    "Can_f_1": "Lipocaline", "Can_f_2": "Lipocaline", "Can_f_4": "Lipocaline", "Can_f_6": "Lipocaline", "Fel_d_4": "Lipocaline",
    "Equ_c_1": "Lipocaline", "Mus_m_1": "Lipocaline", "Bos_d_5": "Lipocaline (bêta-lactoglobuline)",
    "Fel_d_1": "Sécrétoglobine (allergène majeur du chat)", "Can_f_5": "Kallicréine prostatique",
    "Gad_c_1": "Parvalbumine", "Gad_m_1": "Parvalbumine", "Cyp_c_1": "Parvalbumine", "Clu_h_1": "Parvalbumine",
    "Bos_d_8": "Caséine", "Bos_d_4": "Alpha-lactalbumine",
    "Gal_d_1": "Ovomucoïde", "Gal_d_2": "Ovalbumine", "Gal_d_3": "Ovotransferrine",
    "Der_p_1": "Cystéine protéase (allergène majeur)", "Der_f_1": "Cystéine protéase (allergène majeur)",
    "Der_p_2": "NPC2 (allergène majeur)", "Der_f_2": "NPC2 (allergène majeur)",
    "Phl_p_1": "Expansine (allergène majeur des graminées)", "Phl_p_5": "Allergène majeur des graminées",
    "Lol_p_1": "Expansine (allergène majeur des graminées)", "Cyn_d_1": "Expansine (allergène majeur des graminées)",
    "Amb_a_1": "Pectate lyase (allergène majeur)", "Art_v_1": "Défensine (allergène majeur)",
    "Ole_e_1": "Allergène majeur de l'olivier", "Pla_l_1": "Allergène majeur du plantain", "Sal_k_1": "Pectine méthylestérase",
    "Alt_a_1": "Allergène majeur d'Alternaria", "Api_m_1": "Phospholipase A2", "Ves_v_5": "Antigène 5", "Pol_d_5": "Antigène 5",
    "Tri_a_19.0101": "Oméga-5 gliadine", "Hev_b_6.01": "Prohéveine", "Hev_b_6.02": "Héveine", "Act_d_1": "Actinidine",
    "MUXF3": "Déterminant glucidique (CCD)",
}


# Quand une même espèce donne un pollen ET un aliment, la catégorie se lit code par code (OMS/IUIS) :
# Cor a 1.01 vient du pollen de noisetier, Cor a 1.04, 8, 9, 11, 12 et 14 de la noisette.
# Code -> (nom courant, catégorie). Un code de ces espèces absent d'ici n'a pas de catégorie : on ne devine pas.
PRECISIONS = {
    "Cor_a_pollen": ("Noisetier (pollen)", "Pollens d'arbres"),
    "Cor_a_1.0101": ("Noisetier (pollen)", "Pollens d'arbres"),
    "Cor_a_1.0103": ("Noisetier (pollen)", "Pollens d'arbres"),
    "Cor_a_1.0401": ("Noisette", "Aliments végétaux"),
    "Cor_a_8": ("Noisette", "Aliments végétaux"),
    "Cor_a_9": ("Noisette", "Aliments végétaux"),
    "Cor_a_11": ("Noisette", "Aliments végétaux"),
    "Cor_a_12_RUO": ("Noisette", "Aliments végétaux"),
    "Cor_a_14": ("Noisette", "Aliments végétaux"),
}


def espece(code):
    """L'espèce d'un code : « Ara_h_2 » -> « Ara_h » ; « Alpha-Gal » et « MUXF3 » sont leur propre espèce."""
    if code in SOURCES:
        return code
    morceaux = code.split("_")
    return "_".join(morceaux[:2]) if len(morceaux) >= 2 else code


def decrire(code):
    """Ce qu'on sait d'un code : nom courant, nom latin, catégorie, famille. Vide si on ne sait pas."""
    source = SOURCES.get(espece(code))
    if source is None:
        return {}
    nom, latin, categorie = source
    if code in PRECISIONS:
        nom, categorie = PRECISIONS[code]
    fiche = {"source": nom, "latin": latin}
    if categorie:  # pas de catégorie validée : la clé est absente, jamais devinée
        fiche["categorie"] = categorie
    if code in FAMILLES:
        fiche["famille"] = FAMILLES[code]
    return fiche
