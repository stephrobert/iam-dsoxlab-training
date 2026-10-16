#!/usr/bin/env bash
set -u
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/lib.sh
echo "-- configuration injectee dans la console (adresse d'administration)"
cadm $ADM/admin/master/console/ | grep -o -E '"(authUrl|authServerUrl|serverBaseUrl|adminBaseUrl|resourceUrl|realm|loginRealm)": ?"[^"]*"|&quot;(authUrl|authServerUrl|serverBaseUrl|adminBaseUrl)&quot;:&quot;[^&]*&quot;' | sort -u
echo "-- page de connexion master servie par l'adresse d'administration"
cadm -o /dev/null -w 'auth master via admin: %{http_code}\n' "$ADM/realms/master/protocol/openid-connect/auth?client_id=security-admin-console&redirect_uri=https%3A%2F%2Fadmin.lab.test%3A19443%2Fadmin%2Fmaster%2Fconsole%2F&response_type=code&scope=openid"
echo "-- jeton administrateur via l'adresse d'administration (password grant sur admin-cli)"
cadm -o /dev/null -w 'token master via admin: %{http_code}\n' -X POST $ADM/realms/master/protocol/openid-connect/token -d grant_type=password -d client_id=admin-cli -d username=nobody -d password=x
echo "-- meme appel via l'adresse publique"
cpub -o /dev/null -w 'token master via public: %{http_code}\n' -X POST $PUB/realms/master/protocol/openid-connect/token -d grant_type=password -d client_id=admin-cli -d username=nobody -d password=x
echo "-- API d'administration via adresse publique / admin"
cpub -o /dev/null -w 'public /admin/realms: %{http_code}\n' $PUB/admin/realms
cadm -o /dev/null -w 'admin /admin/realms (sans jeton): %{http_code}\n' $ADM/admin/realms
