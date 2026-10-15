printf 'bonjour' | openssl dgst -sha256
printf 'bonjour' | openssl dgst -sha256 -hmac 'secret-partage'

mkdir -p jwt-lab && cd jwt-lab

# texte vers base64url (sans remplissage), et l'inverse
b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
unb64url() {
  s=$(printf '%s' "$1" | tr '_-' '/+')
  while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done
  printf '%s' "$s" | base64 -d
}

openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out private.pem
openssl pkey -in private.pem -pubout -out public.pem

HEADER=$(printf '{"alg":"RS256","typ":"JWT","kid":"cle-2026-10"}' | b64url)
PAYLOAD=$(printf '{"iss":"https://idp.example.test","sub":"alice","aud":"mon-app","exp":1893456000}' | b64url)

printf '%s.%s' "$HEADER" "$PAYLOAD" > signing_input.txt
openssl dgst -sha256 -sign private.pem -out sig.bin signing_input.txt
JWT="$HEADER.$PAYLOAD.$(b64url < sig.bin)"
echo "$JWT"

unb64url "$(printf '%s' "$JWT" | cut -d. -f1)"; echo
unb64url "$(printf '%s' "$JWT" | cut -d. -f2)"; echo

unb64url "$(printf '%s' "$JWT" | cut -d. -f3)" > sig_recue.bin
printf '%s' "$(printf '%s' "$JWT" | cut -d. -f1-2)" > input_recu.txt
openssl dgst -sha256 -verify public.pem -signature sig_recue.bin input_recu.txt

P2=$(printf '{"iss":"https://idp.example.test","sub":"mallory","aud":"mon-app","exp":1893456000}' | b64url)
printf '%s.%s' "$HEADER" "$P2" > input_falsifie.txt
openssl dgst -sha256 -verify public.pem -signature sig_recue.bin input_falsifie.txt

N=$(openssl rsa -pubin -in public.pem -noout -modulus | cut -d= -f2 | xxd -r -p | b64url)
printf '{"keys":[{"kty":"RSA","use":"sig","alg":"RS256","kid":"cle-2026-10","n":"%s","e":"AQAB"}]}\n' "$N"

openssl req -x509 -newkey rsa:2048 -nodes -keyout k.pem -out cert.pem -days 30 -subj "/CN=idp.example.test"
openssl x509 -in cert.pem -noout -subject -issuer -dates

openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.pem -days 30 -subj "/CN=Mon AC de lab"
openssl req -newkey rsa:2048 -nodes -keyout leaf.key -out leaf.csr -subj "/CN=idp.example.test"
openssl x509 -req -in leaf.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out leaf.pem -days 30
openssl verify -CAfile ca.pem leaf.pem
openssl verify -CAfile cert.pem leaf.pem

H0=$(printf '{"alg":"none","typ":"JWT"}' | b64url)
echo "$H0.$P2."

