import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_d = tempfile.mkdtemp()
os.environ.update(CHEMIN_BD=f"{_d}/test.db", MODE_DEMO="1", SECRET_KEY="test",
                  STRIPE_SECRET_KEY="sk_test_x", STRIPE_WEBHOOK_SECRET="whsec_test",
                  CREDITS_GRATUITS="2", ANTHROPIC_API_KEY="")
