"""Fabrique l'URL d'une AuthnRequest SAML (binding HTTP-Redirect)."""
import base64, sys, urllib.parse, uuid, zlib
from datetime import datetime, timezone

issuer, acs = sys.argv[1], sys.argv[2]
idp = "http://localhost:8080/realms/lab/protocol/saml"
xml = f"""<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_{uuid.uuid4().hex}" Version="2.0" IssueInstant="{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}" Destination="{idp}" ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" AssertionConsumerServiceURL="{acs}"><saml:Issuer>{issuer}</saml:Issuer></samlp:AuthnRequest>"""
raw = zlib.compress(xml.encode())[2:-4]  # DEFLATE brut, sans en-tête zlib
q = urllib.parse.urlencode({"SAMLRequest": base64.b64encode(raw).decode(), "RelayState": "retour"})
print(f"{idp}?{q}")
