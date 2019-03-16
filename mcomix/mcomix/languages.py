import operator

# For new language, add ('language name in this language', 'language code')
# to the languages list.

# Source:
# https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
# https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2

languages = sorted([
    ('Català', 'ca'),  # Catalan
    ('čeština', 'cs'),  # Czech
    ('Deutsch', 'de'),  # German
    ('ελληνικά', 'el'),  # Greek
    ('English', 'en'),  # English
    ('Español', 'es'),  # Spanish
    ('فارسی', 'fa'),  # Persian
    ('Français', 'fr'),  # French
    ('Galego', 'gl'),  # Galician
    ('עברית', 'he'),  # Hebrew
    ('Hrvatski jezik', 'hr'),  # Croatian
    ('Magyar', 'hu'),  # Hungarian
    ('Bahasa Indonesia', 'id'),  # Indonesian
    ('Italiano', 'it'),  # Italian
    ('日本語', 'ja'),  # Japanese
    ('한국어', 'ko'),  # Korean
    ('Nederlands', 'nl'),  # Dutch
    ('Język polski', 'pl'),  # Polish
    ('Português', 'pt_BR'),  # Portuguese
    ('pусский язык', 'ru'),  # Russian
    ('Svenska', 'sv'),  # Swedish
    ('українська мова', 'uk'),  # Ukrainian
    ('简体中文', 'zh_CN'),  # Chinese (simplified)
    ('正體中文', 'zh_TW'),  # Chinese (traditional)
], key=operator.itemgetter(1))
