"""Parcourt une intégration de bout en bout, en partant de l'application.

`navigateur.py` part du point d'autorisation de Keycloak : il éprouve le client
OIDC. Cet outil part de l'APPLICATION, suit tout ce qu'un navigateur suivrait,
et rend où il est arrivé. C'est ce qu'il faut pour juger une intégration : une
application correctement branchée emmène l'utilisateur chez le fournisseur
d'identité, le ramène, et affiche son nom.

Il suit les redirections, tient les cookies, remplit le formulaire de connexion
quand il le rencontre, et reposte les formulaires auto-soumis, que SAML utilise
pour traverser le navigateur sans redirection HTTP. Il s'arrête quand plus rien
n'est à suivre, ou au bout de `--tours`.

Il écrit un objet JSON sur la sortie standard et sort en 0, même quand le
parcours échoue : c'est au test de juger. Une panne de l'outil sort en 2, pour
qu'un test ne confonde jamais « l'intégration est cassée » avec « la mesure n'a
pas eu lieu ».

    python3 parcours.py --depart http://127.0.0.1:9080/connexion \
        --utilisateur alice --mot-de-passe '...'
"""

from __future__ import annotations

import argparse
import contextlib
import html
import http.cookiejar
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ERREUR_OUTIL = 2
REDIRECTIONS = (301, 302, 303, 307, 308)


class SansRedirection(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def ouvrir() -> urllib.request.OpenerDirector:
    politique = http.cookiejar.DefaultCookiePolicy(secure_protocols=("http", "https"))
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar(politique)),
        SansRedirection,
    )


def appeler(
    navigateur: urllib.request.OpenerDirector,
    url: str,
    donnees: dict[str, str] | None = None,
) -> tuple[int, str | None, str]:
    corps = urllib.parse.urlencode(donnees).encode() if donnees else None
    try:
        # URL issue du parcours lui-même, à partir de l'adresse de départ
        # que le test donne : le schéma est toujours http ou https.
        requete = urllib.request.Request(url, data=corps)  # noqa: S310
        reponse = navigateur.open(requete)
        return reponse.status, reponse.headers.get("Location"), reponse.read().decode(
            "utf-8", "replace"
        )
    except urllib.error.HTTPError as erreur:
        return erreur.code, erreur.headers.get("Location"), erreur.read().decode(
            "utf-8", "replace"
        )


def absolu(base: str, lieu: str) -> str:
    return urllib.parse.urljoin(base, lieu)


def formulaires(page: str) -> list[tuple[str, str, dict[str, str]]]:
    """Les formulaires de la page, avec leur méthode et leurs champs cachés."""
    trouves = []
    for bloc in re.findall(r"<form\b.*?</form>", page, re.S | re.I):
        action = re.search(r'action="([^"]*)"', bloc, re.I)
        methode = re.search(r'method="([^"]*)"', bloc, re.I)
        champs = {
            nom: html.unescape(valeur)
            for nom, valeur in re.findall(
                r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', bloc, re.I
            )
        }
        trouves.append(
            (
                html.unescape(action.group(1)) if action else "",
                (methode.group(1) if methode else "get").lower(),
                champs,
            )
        )
    return trouves


def est_formulaire_de_connexion(page: str) -> bool:
    """Reconnaît la page de connexion à ses champs, non à son allure.

    Le thème d'un realm peut être changé, et les libellés traduits. Ce qui ne
    change pas, c'est qu'un formulaire de connexion par mot de passe porte un
    champ de nom d'utilisateur et un champ de mot de passe.
    """
    return bool(
        re.search(r'name="password"', page, re.I)
        and re.search(r'name="(username|email)"', page, re.I)
    )


def texte_visible(page: str) -> str:
    sans_script = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", sans_script))).strip()


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--depart", required=True)
    analyseur.add_argument("--utilisateur")
    analyseur.add_argument("--mot-de-passe")
    analyseur.add_argument("--tours", type=int, default=15)
    analyseur.add_argument("--attendre-texte", default=None,
                           help="texte cherché dans la page finale ; le "
                                "résultat porte `texte_trouve`")
    args = analyseur.parse_args()

    navigateur = ouvrir()
    etapes: list[dict[str, object]] = []
    connexion_posee = False

    url = args.depart
    try:
        code_http, lieu, page = appeler(navigateur, url)
        etapes.append({"url": url, "http": code_http})

        for _ in range(args.tours):
            if code_http in REDIRECTIONS and lieu:
                url = absolu(url, lieu)
                code_http, lieu, page = appeler(navigateur, url)
                etapes.append({"url": url.split("?")[0], "http": code_http})
                continue

            # Le formulaire de connexion : on le remplit une fois. Le remplir
            # deux fois voudrait dire que Keycloak l'a redemandé, donc que les
            # identifiants sont refusés, et boucler masquerait ce refus.
            if (
                est_formulaire_de_connexion(page)
                and args.utilisateur
                and not connexion_posee
            ):
                action, methode, champs = formulaires(page)[0]
                champs.update(
                    {
                        "username": args.utilisateur,
                        "password": args.mot_de_passe or "",
                        "credentialId": "",
                    }
                )
                cible = absolu(url, action) if action else url
                code_http, lieu, page = appeler(
                    navigateur, cible, champs if methode == "post" else None
                )
                url = cible
                connexion_posee = True
                etapes.append({"url": "connexion", "http": code_http})
                continue

            # Formulaire auto-soumis : c'est ainsi que SAML traverse le
            # navigateur, sans redirection HTTP. Un test qui ne le reposterait
            # pas conclurait que l'intégration s'arrête là.
            auto = [f for f in formulaires(page) if f[1] == "post" and f[2]]
            if auto and re.search(r"\.submit\(\)", page):
                action, _, champs = auto[0]
                cible = absolu(url, action) if action else url
                code_http, lieu, page = appeler(navigateur, cible, champs)
                url = cible
                etapes.append({"url": "formulaire auto-soumis", "http": code_http})
                continue

            break
        else:
            raise RuntimeError(
                f"parcours non terminé en {args.tours} tours : boucle probable"
            )

    except urllib.error.URLError as erreur:
        print(json.dumps({"erreur_outil": f"injoignable : {erreur}"},
                         ensure_ascii=False), file=sys.stderr)
        return ERREUR_OUTIL
    except RuntimeError as erreur:
        print(json.dumps({"erreur_outil": str(erreur)}, ensure_ascii=False),
              file=sys.stderr)
        return ERREUR_OUTIL

    visible = texte_visible(page)
    resultat: dict[str, object] = {
        "arrivee": url.split("?")[0],
        "http": code_http,
        "etapes": etapes,
        "connexion_posee": connexion_posee,
        "texte": visible[:1500],
    }
    # Une page qui n'est pas du JSON est le cas NORMAL : la plupart des
    # arrivées sont du HTML. On l'ajoute quand il y en a, sans en faire une
    # condition.
    with contextlib.suppress(json.JSONDecodeError, ValueError):
        resultat["json"] = json.loads(page)
    if args.attendre_texte:
        resultat["texte_trouve"] = args.attendre_texte in visible

    print(json.dumps(resultat, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
