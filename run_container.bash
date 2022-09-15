#!/bin/bash
image=tm95mon/jupyter:w_pandas

name=my_container

NAS_address_from_local=10.79.0.165
NAS_address_from_PolimiNW=10.75.4.20

#get_credentials
user=monopoli
pass='9SuRh2:c.c!T8rf'

docker run \
--rm -d \
--cap-add SYS_ADMIN --cap-add DAC_READ_SEARCH \
--name $name \
-p ${1:-8888}:8888 \
-v $(pwd):/workspace \
-e password=$pass \
-e username=$user \
$image 

docker exec -d $name bash -c 'printf "username=$username\npassword=$password" > /credentials.txt'
docker exec -d $name bash -c "mount -t cifs //$NAS_address_from_local/monopoli /NAS --verbose -o credentials=/credentials.txt"

