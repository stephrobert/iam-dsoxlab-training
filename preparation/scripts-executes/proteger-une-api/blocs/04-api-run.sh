python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
ISSUER=http://localhost:8080/realms/lab AUDIENCE=notes-api .venv/bin/python api.py &
