"""
Flask HTTP server for Ollama-compatible API endpoints.
"""

from typing import Dict
from flask import Flask, request, jsonify
from flask_cors import CORS


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
        CORS(self.app)
        self._setup_routes()

    def _setup_routes(self):
        """Register API routes."""
        # Ollama-compatible routes
        self.app.add_url_rule('/api/generate', 'generate', self.handle_generate, methods=['POST'])
        self.app.add_url_rule('/api/chat', 'chat', self.handle_chat, methods=['POST'])
        self.app.add_url_rule('/api/tags', 'tags', self.handle_tags, methods=['GET'])

        # OpenAI-compatible routes
        self.app.add_url_rule('/v1/models', 'models', self.handle_models, methods=['GET'])
        self.app.add_url_rule('/v1/chat/completions', 'completions', self.handle_completions, methods=['POST'])

        # Health check
        self.app.add_url_rule('/health', 'health', self.health_check, methods=['GET'])

    def start(self, host: str = "0.0.0.0", port: int = 11434, ssl_cert: str = None, ssl_key: str = None) -> None:
        """
        Start Flask server.

        Args:
            host: Host to bind to
            port: Port to listen on
            ssl_cert: Path to SSL certificate file (optional, for HTTPS)
            ssl_key: Path to SSL key file (optional, for HTTPS)
        """
        # Setup SSL context if certificates provided
        ssl_context = None
        if ssl_cert and ssl_key:
            ssl_context = (ssl_cert, ssl_key)
        elif ssl_cert == 'adhoc':
            # Use ad-hoc self-signed certificate (requires pyOpenSSL)
            ssl_context = 'adhoc'

        # Use single-threaded mode for SQLite compatibility
        self.app.run(host=host, port=port, debug=False, threaded=False, ssl_context=ssl_context)

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

    def handle_tags(self):
        """
        Handle /api/tags endpoint (Ollama-compatible).

        Returns list of available models.
        """
        from . import handlers

        response = handlers.format_ollama_tags()
        return jsonify(response)

    def handle_models(self):
        """
        Handle /v1/models endpoint (OpenAI-compatible).

        Returns list of available models.
        """
        from . import handlers

        response = handlers.format_openai_models()
        return jsonify(response)

    def handle_completions(self):
        """
        Handle /v1/chat/completions endpoint (OpenAI-compatible).

        Expected input:
        {
            "model": "string",
            "messages": [{"role": "string", "content": "string"}],
            "temperature": float,
            "max_tokens": int,
            ...
        }
        """
        from . import handlers

        try:
            data = request.get_json()
            if data is None:
                error_response, code = handlers.handle_error(ValueError("Invalid JSON"), 400)
                return jsonify(error_response), code

            is_valid, error_msg = handlers.validate_openai_request(data)
            if not is_valid:
                error_response, code = handlers.handle_error(ValueError(error_msg), 400)
                return jsonify(error_response), code

            messages = data['messages']
            model = data.get('model', 'ollama-markov')

            # Normalize message content (handle both string and list formats)
            normalized_messages = []
            for msg in messages:
                content = msg.get('content', '')

                # Handle list format (array of content parts)
                if isinstance(content, list):
                    # Extract text from content parts
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get('type') == 'text':
                            text_parts.append(part.get('text', ''))
                        elif isinstance(part, str):
                            text_parts.append(part)
                    content = ' '.join(text_parts)
                elif not isinstance(content, str):
                    content = str(content)

                normalized_messages.append({
                    'role': msg.get('role'),
                    'content': content
                })

            # Map OpenAI parameters to internal options
            options = {}
            if 'temperature' in data:
                options['temperature'] = data['temperature']
            if 'max_tokens' in data:
                options['num_predict'] = data['max_tokens']
            if 'top_k' in data:
                options['top_k'] = data['top_k']

            response_text = self.generator.generate_from_messages(normalized_messages, options)

            # Check if streaming is requested
            stream = data.get('stream', False)
            if stream:
                stream_response = handlers.format_openai_stream(response_text, model)
                return (stream_response, 200, {'Content-Type': 'text/event-stream'})
            else:
                response = handlers.format_openai_response(response_text, model)
                return jsonify(response)

        except Exception as e:
            error_response, code = handlers.handle_error(e)
            return jsonify(error_response), code

    def health_check(self):
        """Health check endpoint."""
        return jsonify({"status": "ok"})
