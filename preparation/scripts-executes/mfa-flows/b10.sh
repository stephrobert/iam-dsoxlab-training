AID=$(kcadm get users -r lab -q username=alice --fields id --format csv --noquotes)
kcadm get users/$AID/credentials -r lab | jq -r '.[]|[.id,.type,.userLabel]|@tsv'
kcadm delete users/$AID/credentials/<id-du-facteur-otp> -r lab
