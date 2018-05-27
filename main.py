import re
from datetime import datetime
import logging
from argparse import ArgumentParser

import os

# En python, les chemins de fichier sont relatifs au répertoire courant
# du shell qui appelle le script. Donc on cherche toujours à retrouver le
# chemin absolu du script et son répertoire.
CURRENT_FOLDER = os.path.dirname(__file__)
DICT_FR_PATH = os.path.join(CURRENT_FOLDER, 'assets', 'wordsFR.txt')
DICT_EN_PATH = os.path.join(CURRENT_FOLDER, 'assets', 'wordsEN.txt')
DICT_ES_PATH = os.path.join(CURRENT_FOLDER, 'assets', 'wordsES.txt')

# On définit des constantes pour identifier les langues.
LANG_UNKNOWN = 0
LANG_FR = 1
LANG_EN = 2
LANG_ES = 3


def parse_args():
    """Lis les paramètres d'entrée de l'application."""
    parser = ArgumentParser(description='Détection de langue - S. BENKACEM')
    parser.add_argument("-f", "--file", dest="file", type=str,
                        help='Fichier pour lequel détecter la langue.')
    parser.add_argument("-t", "--text", dest="text", type=str,
                        help='Un texte pour lequel détecter la langue. '
                             'Incompatible avec --file')
    args, _ = parser.parse_known_args()
    return args.text, args.file


def get_text_to_translate(input_text, input_file):
    # Un seul paramètre autorisé.
    if input_file and input_text:
        logging.error('--file ne peut pas être utilisé en même temps que text')
        return ''

    # Si fichier fourni, extraire son contenu.
    if input_file:
        try:
            with open(input_file, 'r') as fd:
                input_text = fd.read()
        except IOError:
            logging.error("Le fichier fourni n'existe pas.")
            return ''

    # Si toujours rien dans input_text, lire la console.
    input_text = input_text or input('Tapez un texte à traduire:')

    # Si l'utilisateur ne rentre rien, tant pis...
    if not input_text:
        return ''

    # On enregistre l'input, pour vérification...
    fname = os.path.join(CURRENT_FOLDER, 'text_{}'.format(datetime.now()))
    with open(fname, "w") as fd:
        fd.write(input_text)

    return input_text


def load_language_dictionary(dict_path, language):
    with open(dict_path, 'rt', encoding="utf-8") as fd:
        return {
            word.strip(' \n\t').lower(): [language]
            for line_num, word in enumerate(fd.readlines())
            if line_num > 0  # La première ligne est le nombre de mots.
        }


def load_universal_dictionary():
    # On charge les dictionaires.
    dict_fr = load_language_dictionary(DICT_FR_PATH, LANG_FR)
    dict_en = load_language_dictionary(DICT_EN_PATH, LANG_EN)
    dict_es = load_language_dictionary(DICT_ES_PATH, LANG_ES)

    # On crée un super dictionnaire avec toutes les entrées. Attention :
    # certains mots sont valides dans plusieurs langues. C'est pris en charge.
    dict_all = {}
    for dct in (dict_fr, dict_es, dict_en):
        for key, value in dct.items():
            if key in dict_all:
                dict_all[key] += value
            else:
                dict_all[key] = value
    return dict_all


def compute_scores_with_dictionary(text, dct):
    scores = {LANG_FR: 0, LANG_EN: 0, LANG_ES: 0, LANG_UNKNOWN: 0}
    words = re.split('\s+', text)
    for word in words:
        languages = dct.get(word.lower(), [])
        for language in languages:
            scores[language] += 1

    # on normalise...
    total_score = sum(score for score in scores.values())
    if total_score > 0:
        for language in scores:
            scores[language] /= total_score

    return scores


def main(input_text, input_file):
    text = get_text_to_translate(input_text, input_file)
    if not text:
        return

    dict_universe = load_universal_dictionary()
    scores = compute_scores_with_dictionary(text, dict_universe)
    logging.info("Ce texte a l'air:")
    logging.info("   - {:.2f}% français".format(scores[LANG_FR] * 100))
    logging.info("   - {:.2f}% anglais".format(scores[LANG_EN] * 100))
    logging.info("   - {:.2f}% espagnol".format(scores[LANG_ES] * 100))
    logging.info("   - {:.2f}% non reconnu".format(scores[LANG_UNKNOWN] * 100))


if __name__ == '__main__':
    """Point d'entrée de l'application lorsque le script est executé
    directement.
    """
    logging.basicConfig(level=logging.INFO)
    arg_text, arg_file = parse_args()
    main(arg_text, arg_file)
    if os.name == 'Windows':
        os.system("pause")  # Pour Windows, évite que la fenêtre se ferme.
