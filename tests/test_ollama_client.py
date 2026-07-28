import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from recruiting_ai.ollama_client import embed


class OllamaClientTests(unittest.TestCase):
    @patch("recruiting_ai.ollama_client._post_json")
    def test_embed_uses_current_endpoint_and_response_shape(self, mock_post):
        mock_post.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

        vector = embed("hello", model="nomic-embed-text", base_url="http://ollama")

        self.assertEqual(vector, [0.1, 0.2, 0.3])
        self.assertEqual(mock_post.call_args.args[0], "http://ollama/api/embed")
        self.assertEqual(mock_post.call_args.args[1], {"model": "nomic-embed-text", "input": "hello"})

    @patch("recruiting_ai.ollama_client._post_json")
    def test_embed_accepts_legacy_response_shape(self, mock_post):
        mock_post.return_value = {"embedding": [0.1, 0.2]}

        vector = embed("hello", model="nomic-embed-text", base_url="http://ollama")

        self.assertEqual(vector, [0.1, 0.2])


if __name__ == "__main__":
    unittest.main()
