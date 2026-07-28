import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from recruiting_ai.rag import search_memory


class RagTests(unittest.TestCase):
    def test_empty_query_does_not_contact_services(self):
        self.assertEqual(search_memory(""), {"matches": [], "reason": "empty query"})

    @patch("recruiting_ai.rag._collection_exists", return_value=False)
    @patch("recruiting_ai.rag.ensure_collection")
    @patch("recruiting_ai.rag.urllib.request.urlopen")
    @patch("recruiting_ai.rag.embed", return_value=[0.1, 0.2, 0.3])
    def test_search_creates_missing_collection_and_uses_query_endpoint(
        self,
        mock_embed,
        mock_urlopen,
        mock_ensure_collection,
        mock_collection_exists,
    ):
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"result":{"points":[]}}'

        result = search_memory("data scientist", limit=3)

        self.assertEqual(result, {"matches": []})
        mock_collection_exists.assert_called_once()
        mock_ensure_collection.assert_called_once_with(
            collection="recruiting_memory",
            dimension=3,
            base_url="http://localhost:6333",
        )
        request = mock_urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/collections/recruiting_memory/points/query"))
        self.assertEqual(request.get_method(), "POST")
        self.assertIn(b'"query"', request.data)
        self.assertNotIn(b'"vector"', request.data)


if __name__ == "__main__":
    unittest.main()
