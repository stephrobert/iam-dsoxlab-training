#!/usr/bin/env bash
set -u
which jq
KC=http://localhost:8080/realms/lab/protocol/openid-connect
echo "== discovery"
curl -s http://localhost:8080/realms/lab/.well-known/openid-configuration | jq '{end_session_endpoint, revocation_endpoint, introspection_endpoint, backchannel_logout_supported, backchannel_logout_session_supported, frontchannel_logout_supported, frontchannel_logout_session_supported, dpop_signing_alg_values_supported, tls_client_certificate_bound_access_tokens, grant_types_supported}'
echo "== realm settings"
docker exec kc-jetons /opt/keycloak/bin/kcadm.sh get realms/lab --fields accessTokenLifespan,ssoSessionIdleTimeout,ssoSessionMaxLifespan,revokeRefreshToken,refreshTokenMaxReuse
echo "== token"
RESP=$(curl -s -X POST $KC/token -d grant_type=password -d client_id=cli-observation -d username=alice -d password='Alice-lab-2026' -d scope=openid)
echo "$RESP" | jq 'del(.access_token,.id_token,.refresh_token)'
dec() { local s; s=$(cut -d. -f2 <<<"$1" | tr '_-' '/+'); while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done; base64 -d <<<"$s"; }
AT=$(jq -r .access_token <<<"$RESP"); RT=$(jq -r .refresh_token <<<"$RESP"); IDT=$(jq -r .id_token <<<"$RESP")
echo "-- access"; dec "$AT" | jq '{typ,azp,sid,iat,exp,ttl:(.exp-.iat),aud,scope}'
echo "-- id"; dec "$IDT" | jq '{typ,azp,sid,ttl:(.exp-.iat),aud}'
echo "-- refresh"; dec "$RT" | jq '{typ,azp,sid,ttl:(.exp-.iat)}'
echo "== refresh x2 with same RT (rotation off)"
R1=$(curl -s -X POST $KC/token -d grant_type=refresh_token -d client_id=cli-observation -d refresh_token="$RT")
echo "$R1" | jq 'del(.access_token,.id_token,.refresh_token)'
RT1=$(jq -r .refresh_token <<<"$R1")
[ "$RT1" = "$RT" ] && echo "refresh token IDENTIQUE" || echo "refresh token NOUVEAU"
R2=$(curl -s -X POST $KC/token -d grant_type=refresh_token -d client_id=cli-observation -d refresh_token="$RT")
echo "reuse old RT:"; echo "$R2" | jq 'del(.access_token,.id_token,.refresh_token)'
echo "$RT" > /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-jetons/rt.txt
