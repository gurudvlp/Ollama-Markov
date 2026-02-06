"""
Flask HTTP server for Ollama-compatible API endpoints.
"""

from typing import Dict
from flask import Flask, request, jsonify


class OllamaServer:
    """Flask HTTP server providing Ollama-compatible API endpoints."""

    def __init__(self, generator, config: Dict):
        """
        Initialize Flask app with routes.

        Args:
            generator: Generator instance
            config: Configuration dictionary
        """
        self.generator = generator
        self.config = config
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Register API routes."""
        self.app.add_url_rule('/api/generate', 'generate', self.handle_generate, methods=['POST'])
        self.app.add_url_rule('/api/chat', 'chat', self.handle_chat, methods=['POST'])
        self.app.add_url_rule('/health', 'health', self.health_check, methods=['GET'])

    def start(self, host: str = "0.0.0.0", port: int = 11434) -> None:
        """
        Start Flask server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        # Use single-threaded mode for SQLite compatibility
        self.app.run(host=host, port=port, debug=False, threaded=False)

    def handle_generate(self):
        """
        Handle /api/generate endpoint.

        Expected input:
        {
            "model": "string",
            "prompt": "string",
            "stream": bool,
            "options": {...}
        }
        """
        from . import handlers

        try:
            data = request.get_json()
            if data is None:
                error_response, code = handlers.handle_error(ValueError("Invalid JSON"), 400)
                return jsonify(error_response), code

            is_valid, error_msg = handlers.validate_request(data, "generate")
            if not is_valid:
                error_response, code = handlers.handle_error(ValueError(error_msg), 400)
                return jsonify(error_response), code

            prompt = data['prompt']
            options = data.get('options', {})
            stream = data.get('stream', False)

            response_text = self.generator.generate_from_prompt(prompt, options)
            response = handlers.format_response(response_text, "generate", stream)

            return jsonify(response)

        except Exception as e:
            error_response, code = handlers.handle_error(e)
            return jsonify(error_response), code

    def handle_chat(self):
        """
        Handle /api/chat endpoint.

        Expected input:
        {
            "model": "string",
            "messages": [{"role": "string", "content": "string"}],
            "stream": bool,
            "options": {...}
        }
        """
        from . import handlers

        try:
            data = request.get_json()
            if data is None:
                error_response, code = handlers.handle_error(ValueError("Invalid JSON"), 400)
                return jsonify(error_response), code

            is_valid, error_msg = handlers.validate_request(data, "chat")
            if not is_valid:
                error_response, code = handlers.handle_error(ValueError(error_msg), 400)
                return jsonify(error_response), code

            messages = data['messages']
            options = data.get('options', {})
            stream = data.get('stream', False)

            response_text = self.generator.generate_from_messages(messages, options)
            response = handlers.format_response(response_text, "chat", stream)

            return jsonify(response)

        except Exception as e:
            error_response, code = handlers.handle_error(e)
            return jsonify(error_response), code

    def health_check(self):
        """Health check endpoint."""
        return jsonify({"status": "ok"})
