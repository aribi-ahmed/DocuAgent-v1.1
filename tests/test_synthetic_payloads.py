import unittest
from src.agent import DocuAgentEngine

class TestDocuAgent(unittest.TestCase):
    def test_synthesis_logic(self):
        engine = DocuAgentEngine()
        mock_logs = [{"id": "1", "user": "dev", "text": "Resolution: Increase heap size."}]
        
        result = engine.process_ticket_resolution("TEST-123", mock_logs)
        
        # Verify the structure matches our enterprise requirements
        self.assertIsNotNone(result.faq_payload.article_title)
        self.assertGreater(result.explainability_layer.confidence_score, 0.5)

if __name__ == '__main__':
    unittest.main()