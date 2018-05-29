import os
import re
import logging
from argparse import ArgumentParser

import numpy as np
import matplotlib

# Fix to use matplotlib on Linux and Mac.
if os.name == 'posix':
    matplotlib.use('TkAgg')

# En python, les chemins de fichier sont relatifs au répertoire courant
# du shell qui appelle le script. Donc on cherche toujours à retrouver le
# chemin absolu du script et son répertoire.
CURRENT_FOLDER = os.path.dirname(__file__)

# On repère les listes de mots.
WORDS_FR_PATH = os.path.join(CURRENT_FOLDER, 'assets', 'wordsFR.txt')
WORDS_EN_PATH = os.path.join(CURRENT_FOLDER, 'assets', 'wordsEN.txt')
WORDS_ES_PATH = os.path.join(CURRENT_FOLDER, 'assets', 'wordsES.txt')

# On définit des constantes pour identifier les langues.
LANG_UNKNOWN = 0
LANG_FR = 1
LANG_EN = 2
LANG_ES = 3
ALL_LANGS = [LANG_UNKNOWN, LANG_FR, LANG_EN, LANG_ES]

# On associe chaque liste de mots à sa langue.
MAP_LANGUAGE_WORDS = {
    LANG_FR: WORDS_FR_PATH,
    LANG_EN: WORDS_EN_PATH,
    LANG_ES: WORDS_ES_PATH
}


def parse_args():
    """Lis les paramètres d'entrée de l'application."""
    parser = ArgumentParser(description='Détection de langue - S. BENKACEM')
    parser.add_argument("-f", "--file", dest="file", type=str,
                        help='Fichier pour lequel détecter la langue.')
    parser.add_argument("-t", "--text", dest="text", type=str,
                        help='Un texte pour lequel détecter la langue. '
                             'Incompatible avec --file')
    args, _ = parser.parse_known_args()
    if args.text and args.file:
        logging.error('--file est incompatible avec --text')
        return '', ''
    return args.text, args.file


def get_text_to_translate(input_text, input_file):
    """En fonction des paramètres d'entrée fournis, retourne le texte à
    traduire.
    """
    # Si fichier fourni, extraire son contenu.
    if input_file:
        try:
            with open(input_file, 'r') as fd:
                input_text = fd.read()
        except IOError:
            logging.error("Le fichier fourni n'existe pas ou n'est pas"
                          "lisible.")
            return ''

    # Si toujours rien dans input_text, lire la console.
    return input_text or input('Tapez un texte à traduire:')


def load_words_from_file(words_file_path):
    """Charge les mots d'une langue à partir d'un fichier. Chaque mot doit
    être sur sa propre ligne.
    """
    with open(words_file_path, 'rt', encoding="utf-8") as fd:
        return [
            word.strip('\n').lower()  # lower() pour comparer sans casse.
            for line_num, word in enumerate(fd.readlines())
            if line_num > 0  # On évite la première ligne (le nombre de mots).
        ]


def load_language_dictionary(list_words_path, language):
    """Retourne un dictionnaire ou chaque mot est associé à la langue en
    paramètre."""
    return {word: [language] for word in load_words_from_file(list_words_path)}


def prepare_word_for_transition_check(word):
    """Retourne les index numériques pour chaque caractère du mot. A utiliser
    pour manipuler une matrice de transition.
    """
    # Parce que chaque langue a ses caractères spéciaux mais qu'on ne
    # s'intéresse qu'aux "basiques" (0-255), on cappe à 256, avec le caractère
    # 256 considéré comme "autre"
    return [min(ord(char), 256) for char in word]


def load_transition_matrice(list_words_path):
    """Charge une matrice de transition à partir d'un fichier contenant une
    liste de mots."""
    # On crée une matrice de 0s: (0-256)*(0-256)
    matrix = np.zeros((257, 257), dtype='float')

    # On compte combien de transition on évalue.
    total_transitions = 0
    for word in load_words_from_file(list_words_path):
        chars_ords = prepare_word_for_transition_check(word)
        # Pour chaque mot, on évalue chaque transition de lettre pour remplir
        # la matrice.
        for ord_index in range(len(chars_ords) - 1):
            matrix[chars_ords[ord_index], chars_ords[ord_index + 1]] += 1
            total_transitions += 1

    # On divise chaque cellule par le total pour normaliser la matrice. De
    # cette façon, peu importe le nombre de mots évalués pour construire la
    # matrice, le poids de chaque matrice sera équivalent (chaque case
    # représentant une fréquence de transition générale d'un caractère à
    # l'autre)
    matrix /= total_transitions
    return matrix


def load_universal_dictionary():
    """Charge un dictionnaire qui associe un mot à toutes les langues possible
    pour ce mot."""
    # On charge les dictionaires.
    language_dicts = [
        load_language_dictionary(words_file_path, lang)
        for lang, words_file_path in MAP_LANGUAGE_WORDS.items()
    ]

    # On crée un super dictionnaire avec toutes les entrées. Attention :
    # certains mots sont valides dans plusieurs langues. C'est pris en charge.
    dict_all = {}
    for dct in language_dicts:
        for key, value in dct.items():
            if key in dict_all:
                dict_all[key] += value
            else:
                dict_all[key] = value
    return dict_all


def normalise_scores(scores):
    """Normalise les scores"""
    total_score = sum(score for score in scores.values())
    if total_score > 0:
        for language in scores:
            scores[language] /= total_score

    return scores


def compute_scores_with_dictionary(text):
    """Calcule les scores d'appartenance à chaque langue pour un texte avec une
    méthode de dictionnaire."""
    dict_universe = load_universal_dictionary()
    scores = {lang: 0 for lang in ALL_LANGS}

    # Pour chaque mot...
    for word in re.split('\s+', text):
        # Trouver la liste des langues associées, ou "inconnu" si langue non
        # trouvée.
        languages = dict_universe.get(word.lower(), [LANG_UNKNOWN])
        for language in languages:
            scores[language] += 1

    # on normalise...
    return normalise_scores(scores)


def compute_score_matrix(text, matrix):
    """Calcule les scores d'appartenance à une langue pour un texte avec une
    méthode de matrices."""
    score = 0
    words = re.split('\s+', text)
    for word in words:
        chars_ords = prepare_word_for_transition_check(word)
        # Pour chaque mot, on évalue chaque transition de lettre pour remplir
        # la matrice.
        for ord_index in range(len(chars_ords) - 1):
            score += matrix[chars_ords[ord_index], chars_ords[ord_index + 1]]
    return score


def compute_scores_with_matrices(text):
    """Calcule les scores d'appartenance à chaque langue pour un texte avec une
        méthode de dictionnaire."""

    # Pour chaque langue, on charge la matrice et on calcule son score sur le
    # texte.
    scores = {
        lang: compute_score_matrix(text, load_transition_matrice(words_path))
        for lang, words_path in MAP_LANGUAGE_WORDS.items()
    }
    return normalise_scores(scores)


def main(input_text, input_file):
    """Point d'entrée."""
    text = get_text_to_translate(input_text, input_file)
    if not text:
        return

    scores = compute_scores_with_dictionary(text)
    logging.info("Avec des dictionnaires, ce texte a l'air:")
    logging.info("   - {:.2f}% français".format(scores[LANG_FR] * 100))
    logging.info("   - {:.2f}% anglais".format(scores[LANG_EN] * 100))
    logging.info("   - {:.2f}% espagnol".format(scores[LANG_ES] * 100))
    logging.info(
        "   - {:.2f}% non reconnus".format(scores[LANG_UNKNOWN] * 100))

    scores = compute_scores_with_matrices(text)
    logging.info("")
    logging.info("Avec des matrices, ce texte a l'air:")
    logging.info("   - {:.2f}% français".format(scores[LANG_FR] * 100))
    logging.info("   - {:.2f}% anglais".format(scores[LANG_EN] * 100))
    logging.info("   - {:.2f}% espagnol".format(scores[LANG_ES] * 100))


if __name__ == '__main__':
    """Point d'entrée de l'application lorsque le script est executé
    directement.
    """
    logging.basicConfig(level=logging.INFO)
    arg_text, arg_file = parse_args()
    main(arg_text, arg_file)
    if os.name == 'Windows':
        os.system("pause")  # Pour Windows, évite que la fenêtre se ferme.
