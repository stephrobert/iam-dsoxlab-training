#!/usr/bin/env bash
# Arrête ce qui écoute sur un port, et attend que le port soit VRAIMENT libre.
#
#   arreter-temoin.sh 9080
#
# POURQUOI PAR LE PORT, ET NON PAR LA LIGNE DE COMMANDE
#
# Mesuré le 2026-10-16, et cela a fait échouer un setup : un `pkill -f
# /opt/iam-lab/appli-temoin/appli.py` ne trouve rien quand le témoin a été
# lancé depuis son répertoire, car sa ligne de commande est alors
# `./.venv/bin/python appli.py`. L'apprenant le lance comme il veut, et il a
# raison : rien ne lui impose un chemin absolu.
#
# Le port, lui, est l'état réel. C'est lui qui fera échouer le démarrage
# suivant sur un « address already in use », et c'est donc lui qu'il faut
# libérer. Un contrôle qui porte sur le moyen plutôt que sur l'état finit
# toujours par passer à côté.
#
# Sort en 0 quand le port est libre, en 1 s'il reste occupé après les tentatives.
set -uo pipefail

PORT=${1:?usage: arreter-temoin.sh <port>}

pids_sur_le_port() {
  # `ss -ltnpH` donne les processus en écoute ; le motif `pid=<n>` est la seule
  # forme stable de sa sortie, qui varie sinon d'une version à l'autre.
  ss -ltnpH "sport = :$PORT" 2>/dev/null \
    | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u
}

port_libre() {
  [ -z "$(pids_sur_le_port)" ]
}

if port_libre; then
  echo "port $PORT déjà libre"
  exit 0
fi

# TERM d'abord : un serveur HTTP ferme proprement ses connexions, et un KILL
# immédiat laisse le port en TIME_WAIT plus longtemps.
for pid in $(pids_sur_le_port); do
  kill "$pid" 2>/dev/null || true
done

for _ in $(seq 1 15); do
  port_libre && break
  sleep 1
done

# KILL en dernier recours, pour un processus qui ignore TERM.
if ! port_libre; then
  for pid in $(pids_sur_le_port); do
    kill -9 "$pid" 2>/dev/null || true
  done
  for _ in $(seq 1 10); do
    port_libre && break
    sleep 1
  done
fi

if port_libre; then
  echo "port $PORT libéré"
  exit 0
fi

echo "ÉCHEC : le port $PORT reste occupé par $(pids_sur_le_port | tr '\n' ' ')" >&2
ss -ltnp "sport = :$PORT" >&2
exit 1
