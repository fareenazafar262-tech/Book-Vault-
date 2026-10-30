"""
schema.py - columns of our dataset, shared by every other file.

One record = one book from Project Gutenberg. We keep 14 attributes
(the project needs at least 8).
"""

FIELDS = [
    "ebook_no", "title", "author", "language", "loc_class", "subjects",
    "subject_count", "category", "release_date", "release_year",
    "last_update", "copyright", "downloads_30d", "reading_ease",
]

# nicer names for the table header
HEADERS = {
    "ebook_no": "eBook #",
    "title": "Title",
    "author": "Author",
    "language": "Language",
    "loc_class": "LoC Class",
    "subjects": "Subjects",
    "subject_count": "Subjects #",
    "category": "Category",
    "release_date": "Release Date",
    "release_year": "Release Year",
    "last_update": "Last Update",
    "copyright": "Copyright",
    "downloads_30d": "Downloads (30d)",
    "reading_ease": "Reading Ease",
}

# these columns hold numbers, everything else is text
NUMERIC_FIELDS = {"ebook_no", "subject_count", "release_year",
                  "downloads_30d", "reading_ease"}


def get_key(row, col):
    """Value that sorting / searching compares for this row and column.

    numbers -> float (missing number becomes -1 so it sorts first)
    text    -> lowercase string, so 'Zola' and 'austen' compare fairly
    """
    value = row.get(col, "")
    if col in NUMERIC_FIELDS:
        try:
            return float(value)
        except (TypeError, ValueError):
            return -1.0
    return str(value).lower()
