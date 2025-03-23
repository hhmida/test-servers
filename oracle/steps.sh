docker pull container-registry.oracle.com/database/express:latest

docker network create ords-database-network


docker run -d --name testapex --hostname database --network=ords-database-network -p 1521:1521 container-registry.oracle.com/database/express:latest

docker exec -it -u oracle testapex sqlplus / as sysdba

# With the “show pdbs” command you will check the status of your pdbs

docker exec testapex ./setPassword.sh Welcome1##

docker pull container-registry.oracle.com/database/ords:latest

mkdir ~/APEX

echo ‘CONN_STRING=sys/Welcome1##@database:1521/XEPDB1’ > ~/APEX/conn_string.txt


docker run --rm --name apex -v /Users/lbindi_it/APEX:/opt/oracle/variables --network=ords-database-network -p 8181:8181 container-registry.oracle.com/database/ords:latest

sqlplus sys/Welcome1##@//localhost:1521/XEPDB1 as sysdba


alter user APEX_PUBLIC_USER identified by Welcome1##;

#to connect at Apex use this http://localhost:8181/ords


#use this information to log-in an internal workspace

#- Workspace: internal
#- User: ADMIN
#- Password: Welcome1##
