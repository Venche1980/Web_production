export PGPASSWORD=secret
psql --host 127.0.0.1 -p 5431 -U swapi -d postgres -c "drop database swapi"
psql --host 127.0.0.1 -p 5431 -U swapi -d postgres -c "create database swapi"