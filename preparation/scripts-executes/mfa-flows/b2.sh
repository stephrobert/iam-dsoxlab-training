kcadm update realms/lab -s 'passwordPolicy=length(15) and notUsername'
kcadm get realms/lab --fields passwordPolicy
kcadm set-password -r lab --username bruno --new-password 'Ab1!court'
kcadm set-password -r lab --username bruno --new-password 'abcdefghijklmnopqrstuvwxyz'
kcadm set-password -r lab --username bruno --new-password "$(python3 -c 'print("a-b"*30)')"
kcadm set-password -r lab --username bruno --new-password 'phrase-de-passe-longue-2026'
