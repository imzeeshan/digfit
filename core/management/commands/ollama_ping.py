from django.conf import settings
from django.core.management.base import BaseCommand

from core.ollama_client import chat


class Command(BaseCommand):
    help = 'Verify Ollama is reachable and the configured model responds.'

    def handle(self, *args, **options):
        self.stdout.write(f'Ollama host: {settings.OLLAMA_HOST}')
        self.stdout.write(f'Model: {settings.OLLAMA_MODEL}')
        try:
            response = chat(
                [{'role': 'user', 'content': 'Reply with exactly: ok'}],
                stream=False,
            )
            msg = getattr(response, 'message', None)
            text = getattr(msg, 'content', '') if msg is not None else ''
            self.stdout.write(self.style.SUCCESS(f'Response: {text!r}'))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'Ollama error: {exc}'))
            raise SystemExit(1) from exc
