import unittest

from search import index, paging, rank

ARTICLES = {
    "doc-1": {"id": "doc-1", "title": "Garden hose", "body": "hose for the garden"},
    "doc-2": {"id": "doc-2", "title": "Patio", "body": "garden patio"},
}


class SearchTest(unittest.TestCase):
    def test_title_matches_count_double(self):
        hits = rank.ranked(index.build(ARTICLES.values()), ARTICLES, "garden")
        self.assertEqual(hits[0], ("doc-1", 3))

    def test_page_slices(self):
        self.assertEqual(paging.page(list(range(10)), 2, 3), [3, 4, 5])


if __name__ == "__main__":
    unittest.main()
